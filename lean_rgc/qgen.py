from __future__ import annotations

from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any
import json
import re

import numpy as np

from .schemas import read_jsonl, write_jsonl, TacticAction, stable_hash
from .coker import project_onto_response_cone, ConeProjectionReport
from .defect_registry import DefectAtom, DefectRegistry
from .carrier import CarrierGenerator
from .failure_signatures import FailureSignatureMiner


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return float(default)


def _sanitize_atom_id(s: str) -> str:
    s = s.strip().replace(".", "_").replace("/", "_").replace("-", "_")
    s = re.sub(r"[^A-Za-z0-9_]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "residual"


def _response_keys(row: dict[str, Any]) -> list[str]:
    if isinstance(row.get("response_keys"), list) and row["response_keys"]:
        return [str(k) for k in row["response_keys"]]
    if isinstance(row.get("response"), dict):
        return sorted(str(k) for k in row["response"])
    rf = row.get("response_flat") or []
    return [f"coord_{i}" for i in range(len(rf))]


def _response_vec(row: dict[str, Any], keys: list[str] | None = None) -> np.ndarray:
    if isinstance(row.get("response_flat"), list):
        return np.asarray([_safe_float(v) for v in row.get("response_flat", [])], dtype=float)
    resp = row.get("response") or {}
    if isinstance(resp, dict):
        keys = keys or sorted(str(k) for k in resp)
        return np.asarray([_safe_float(resp.get(k, 0.0)) for k in keys], dtype=float)
    return np.zeros(0, dtype=float)


def _defect_vec(row: dict[str, Any], keys: list[str] | None = None) -> tuple[np.ndarray, list[str]]:
    db = row.get("defect_before") or row.get("defect") or {}
    if isinstance(db, dict):
        if isinstance(db.get("flat"), list):
            k = [str(x) for x in db.get("flat_keys") or keys or [f"coord_{i}" for i in range(len(db.get("flat", [])))]]
            return np.asarray([_safe_float(v) for v in db.get("flat", [])], dtype=float), k
        vals: list[float] = []
        ks: list[str] = []
        for block in ("goal", "type", "search", "carrier", "audit"):
            sub = db.get(block)
            if isinstance(sub, dict):
                for name in sorted(sub):
                    ks.append(f"{block}.{name}")
                    vals.append(_safe_float(sub.get(name, 0.0)))
        if vals:
            return np.asarray(vals, dtype=float), ks
    # Some flattened defect rows store blocks at top level.
    vals = []
    ks = []
    for block in ("goal", "type", "search", "carrier", "audit"):
        sub = row.get(block)
        if isinstance(sub, dict):
            for name in sorted(sub):
                ks.append(f"{block}.{name}")
                vals.append(_safe_float(sub.get(name, 0.0)))
    if vals:
        return np.asarray(vals, dtype=float), ks
    return np.zeros(0, dtype=float), list(keys or [])


def _carrier_delta(row: dict[str, Any]) -> dict[str, float]:
    cd = row.get("carrier_delta") or {}
    if isinstance(cd, dict) and cd:
        return {str(k): _safe_float(v) for k, v in cd.items()}
    resp = row.get("response") or {}
    if isinstance(resp, dict):
        out: dict[str, float] = {}
        for k, v in resp.items():
            sk = str(k)
            if sk.startswith("carrier."):
                out[sk.split(".", 1)[1]] = _safe_float(v)
        return out
    return {}


def _top_coordinate_contribs(keys: list[str], phi: np.ndarray, rv: np.ndarray, residual: np.ndarray | None = None, k: int = 6) -> list[dict[str, Any]]:
    n = min(len(keys), int(phi.size), int(rv.size))
    if n <= 0:
        return []
    vals = phi[:n] * rv[:n]
    order = np.argsort(-np.abs(vals))[: max(0, k)]
    out: list[dict[str, Any]] = []
    for i in order:
        d: dict[str, Any] = {
            "key": keys[int(i)] if int(i) < len(keys) else f"coord_{int(i)}",
            "phi": float(phi[int(i)]),
            "response": float(rv[int(i)]),
            "contribution": float(vals[int(i)]),
        }
        if residual is not None and int(i) < int(residual.size):
            d["residual"] = float(residual[int(i)])
        out.append(d)
    return out


def _action_from_row(row: dict[str, Any]) -> dict[str, Any]:
    a = row.get("action")
    if isinstance(a, dict):
        return dict(a)
    aid = str(row.get("action_id") or row.get("tactic") or stable_hash(row, 8))
    tactic = str(row.get("tactic") or aid)
    return {"action_id": aid, "tactic": tactic, "tactic_class": str(row.get("tactic_class") or "unknown"), "carrier_tags": [], "cost_estimate": 1.0, "metadata": {}}


def _status(row: dict[str, Any]) -> str:
    return str(row.get("audit_status") or row.get("status") or "unknown")


def _audit_penalty(row: dict[str, Any], audit_penalty: float) -> float:
    return float(audit_penalty if _status(row) in {"timeout", "unsafe", "elab_error"} else 0.0)


def _action_cost(row: dict[str, Any]) -> float:
    a = _action_from_row(row)
    return _safe_float(a.get("cost_estimate", 1.0), 1.0)


@dataclass
class GeneratedDefectProposal:
    atom: dict[str, Any]
    residual_key: str
    residual_value: float
    normal_value: float
    support_value: float
    suggested_contexts: list[dict[str, Any]] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CarrierIncidenceProposal:
    action_id: str
    carrier_atom: str
    mean_delta: float
    count: int
    safe_direction: bool
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ContextProposal:
    action: dict[str, Any]
    coker_score: float
    response_score: float
    support_value: float
    carrier_gain: float
    carrier_violation: float
    cost: float
    audit_penalty: float
    accepted: bool
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class QGenReport:
    projection: dict[str, Any]
    response_keys: list[str]
    generated_defect_atoms: list[dict[str, Any]] = field(default_factory=list)
    carrier_incidence: list[dict[str, Any]] = field(default_factory=list)
    context_candidates: list[dict[str, Any]] = field(default_factory=list)
    failure_signatures: list[dict[str, Any]] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class CokerDrivenGenerator:
    """Generate chart updates from a finite response coker normal.

    This is deliberately conservative: all outputs are marked as candidates / charts.
    Nothing here promotes a defect, carrier, or context to canonical status.  Promotion
    remains a POMS decision requiring parent non-payment, dual evidence, and least repair.
    """

    def __init__(self, *, ridge: float = 1e-4, max_mass: float | None = 1.0, max_iter: int = 500):
        self.ridge = float(ridge)
        self.max_mass = max_mass
        self.max_iter = int(max_iter)

    def _align_rows(self, response_rows: list[dict[str, Any]]) -> tuple[np.ndarray, np.ndarray, list[str], list[dict[str, Any]]]:
        if not response_rows:
            return np.zeros(0), np.zeros((0, 0)), [], []
        keys = _response_keys(response_rows[0])
        R_list: list[np.ndarray] = []
        D_list: list[np.ndarray] = []
        valid_rows: list[dict[str, Any]] = []
        for r in response_rows:
            rv = _response_vec(r, keys)
            dv, dkeys = _defect_vec(r, keys)
            # Most v11 rows use same flat keys for response and defect. If not, keep
            # the common leading dimension and report it in metadata.
            n = min(rv.size, dv.size, len(keys))
            if n <= 0:
                continue
            if len(keys) != n:
                keys = keys[:n]
            R_list.append(rv[:n])
            D_list.append(dv[:n])
            valid_rows.append(r)
        if not R_list:
            return np.zeros(0), np.zeros((0, 0)), keys, []
        R = np.vstack(R_list)
        # Use mean positive defect as the current finite chart defect target.
        D = np.maximum(np.mean(np.vstack(D_list), axis=0), 0.0)
        return D, R, keys, valid_rows

    def project(self, response_rows: list[dict[str, Any]]) -> tuple[ConeProjectionReport, np.ndarray, np.ndarray, list[str], list[dict[str, Any]]]:
        D, R, keys, rows = self._align_rows(response_rows)
        if D.size == 0 or R.size == 0:
            rep = project_onto_response_cone(np.zeros(0), np.zeros((0, 0)), ridge=self.ridge, max_mass=self.max_mass, max_iter=self.max_iter)
            return rep, D, R, keys, rows
        rep = project_onto_response_cone(D, R, ridge=self.ridge, max_mass=self.max_mass, max_iter=self.max_iter)
        return rep, D, R, keys, rows

    def propose_defect_atoms(self, projection: ConeProjectionReport, keys: list[str], *, top_k: int = 16, min_residual: float = 1e-8) -> list[GeneratedDefectProposal]:
        residual = np.asarray(projection.residual, dtype=float)
        normal = np.asarray(projection.normal, dtype=float)
        order = np.argsort(-np.maximum(residual, 0.0))[: max(0, top_k)]
        carrier_gen = CarrierGenerator()
        out: list[GeneratedDefectProposal] = []
        for i in order:
            val = float(residual[i]) if i < residual.size else 0.0
            if val <= min_residual:
                continue
            key = keys[i] if i < len(keys) else f"coord_{i}"
            atom_id = "qgen_residual_" + _sanitize_atom_id(key)
            group = key.split(".", 1)[0] if "." in key else "qgen"
            base_atom = key.split(".", 1)[1] if key.startswith("carrier.") else key
            suggestions = carrier_gen.generate([base_atom], key)
            atom = DefectAtom(
                atom_id=atom_id,
                group=group,
                detector="qgen_coker_residual",
                intervention_templates=[s for ctx in suggestions for s in ctx.get("suggestions", [])] if suggestions else [],
                status="candidate",
                description=f"Coker residual coordinate discovered from finite response chart: {key}",
                evidence={
                    "source": "qgen_coker_residual",
                    "residual_key": key,
                    "residual_value": val,
                    "normal_value": float(normal[i]) if i < normal.size else val,
                    "support_value": projection.support_value,
                    "canonical_status": "witness_until_parent_forced_least_repair",
                    "lineage_id": "qgen_defect_" + stable_hash({"key": key, "residual_value": val}, 12),
                },
            ).to_dict()
            out.append(GeneratedDefectProposal(atom=atom, residual_key=key, residual_value=val, normal_value=float(normal[i]) if i < normal.size else val, support_value=projection.support_value, suggested_contexts=suggestions, evidence=atom["evidence"]))
        return out

    def propose_contexts(self, projection: ConeProjectionReport, R: np.ndarray, rows: list[dict[str, Any]], keys: list[str] | None = None, *, top_k: int = 32, margin_threshold: float = 0.0, cost_weight: float = 0.05, carrier_weight: float = 0.25, audit_penalty: float = 1.0) -> list[ContextProposal]:
        if R.size == 0 or not rows:
            return []
        phi = np.asarray(projection.normal, dtype=float).reshape(-1)
        residual = np.asarray(projection.residual, dtype=float).reshape(-1)
        support = float(projection.support_value)
        out: list[ContextProposal] = []
        for idx, row in enumerate(rows):
            rv = R[idx, : min(R.shape[1], phi.size)]
            ph = phi[: rv.size]
            response_score = float(np.dot(ph, rv)) if rv.size else 0.0
            cd = _carrier_delta(row)
            carrier_gain = float(sum(max(0.0, v) for v in cd.values()))
            carrier_violation = float(sum(max(0.0, -v) for v in cd.values()))
            cost = _action_cost(row)
            penalty = _audit_penalty(row, audit_penalty)
            score = response_score - support + carrier_weight * carrier_gain - carrier_weight * carrier_violation - cost_weight * cost - penalty
            accepted = bool(score > margin_threshold and _status(row) not in {"timeout", "unsafe", "elab_error"})
            action = _action_from_row(row)
            contribs = _top_coordinate_contribs(keys, phi, rv, residual=residual, k=6)
            lineage_payload = {
                "row_index": idx,
                "action_id": str(action.get("action_id") or row.get("action_id") or ""),
                "top_coordinates": [(c.get("key"), round(float(c.get("contribution", 0.0)), 8)) for c in contribs],
                "support_value": round(support, 8),
                "relative_residual": round(float(projection.relative_residual), 8),
            }
            lineage_id = "qgen_" + stable_hash(lineage_payload, 14)
            meta = dict(action.get("metadata") or {})
            meta["qgen"] = {
                "generated_by": "qgen_coker_normal",
                "lineage_id": lineage_id,
                "coker_score": score,
                "response_score": response_score,
                "support_value": support,
                "carrier_gain": carrier_gain,
                "carrier_violation": carrier_violation,
                "status": _status(row),
                "top_coordinate_contributions": contribs,
                "parent_residual_keys": [str(c.get("key")) for c in contribs if c.get("key") is not None],
                "projection": {
                    "residual_norm": float(projection.residual_norm),
                    "relative_residual": float(projection.relative_residual),
                    "support_value": support,
                },
                "canonical_status": "context_witness_until_audited_and_promoted",
                "provenance": {"response_row_index": idx, "support_value": support},
            }
            action["metadata"] = meta
            out.append(ContextProposal(action=action, coker_score=score, response_score=response_score, support_value=support, carrier_gain=carrier_gain, carrier_violation=carrier_violation, cost=cost, audit_penalty=penalty, accepted=accepted, evidence={"row_index": idx, "status": _status(row), "lineage_id": lineage_id, "top_coordinate_contributions": contribs}))
        out.sort(key=lambda x: x.coker_score, reverse=True)
        return out[: max(0, top_k)]

    def propose_carrier_incidence(self, rows: list[dict[str, Any]], *, top_k: int = 64, min_count: int = 1) -> list[CarrierIncidenceProposal]:
        acc: dict[tuple[str, str], list[float]] = {}
        for r in rows:
            aid = str(r.get("action_id") or _action_from_row(r).get("action_id") or "")
            if not aid:
                continue
            for atom, delta in _carrier_delta(r).items():
                acc.setdefault((aid, atom), []).append(float(delta))
        out: list[CarrierIncidenceProposal] = []
        for (aid, atom), vals in acc.items():
            if len(vals) < min_count:
                continue
            mean = float(np.mean(vals)) if vals else 0.0
            out.append(CarrierIncidenceProposal(action_id=aid, carrier_atom=atom, mean_delta=mean, count=len(vals), safe_direction=mean >= 0.0, evidence={"meaning": "positive delta reduces carrier defect; negative delta is carrier violation"}))
        out.sort(key=lambda x: (abs(x.mean_delta), x.count), reverse=True)
        return out[: max(0, top_k)]

    def mine_failure_charts(self, audit_rows: list[dict[str, Any]], response_rows: list[dict[str, Any]], *, min_support: int = 1, top_k: int = 32) -> list[dict[str, Any]]:
        if not audit_rows:
            return []
        miner = FailureSignatureMiner(min_support=min_support)
        result = miner.mine(audit_rows, response_rows)
        sigs = [s.to_dict() for s in result.signatures]
        sigs.sort(key=lambda d: (float(d.get("mean_response_norm", 0.0)), int(d.get("support", 0))), reverse=True)
        for s in sigs:
            s.setdefault("evidence", {})["canonical_status"] = "failure_chart_until_response_quotient_validated"
        return sigs[: max(0, top_k)]

    def run(self, response_rows: list[dict[str, Any]], *, audit_rows: list[dict[str, Any]] | None = None, top_defects: int = 16, top_contexts: int = 32, top_carriers: int = 64, top_failures: int = 32, margin_threshold: float = 0.0, cost_weight: float = 0.05, carrier_weight: float = 0.25, audit_penalty: float = 1.0) -> QGenReport:
        projection, D, R, keys, rows = self.project(response_rows)
        defects = self.propose_defect_atoms(projection, keys, top_k=top_defects)
        contexts = self.propose_contexts(projection, R, rows, keys, top_k=top_contexts, margin_threshold=margin_threshold, cost_weight=cost_weight, carrier_weight=carrier_weight, audit_penalty=audit_penalty)
        carriers = self.propose_carrier_incidence(rows, top_k=top_carriers)
        failures = self.mine_failure_charts(audit_rows or [], response_rows, top_k=top_failures)
        summary = {
            "n_response_rows": len(response_rows),
            "n_aligned_rows": len(rows),
            "defect_dim": int(D.size),
            "response_rows_dim": list(R.shape) if R.size else [0, 0],
            "residual_norm": projection.residual_norm,
            "relative_residual": projection.relative_residual,
            "support_value": projection.support_value,
            "n_defect_proposals": len(defects),
            "n_context_proposals": len(contexts),
            "n_context_accepted": sum(1 for c in contexts if c.accepted),
            "n_carrier_incidence": len(carriers),
            "n_failure_charts": len(failures),
            "status": "chart_generation_only_not_canonical",
        }
        return QGenReport(
            projection=projection.to_dict(),
            response_keys=keys,
            generated_defect_atoms=[p.to_dict() for p in defects],
            carrier_incidence=[p.to_dict() for p in carriers],
            context_candidates=[p.to_dict() for p in contexts],
            failure_signatures=failures,
            summary=summary,
        )


def qgen_from_files(
    responses: str | Path,
    *,
    audits: str | Path | None = None,
    out_dir: str | Path | None = None,
    ridge: float = 1e-4,
    max_mass: float | None = 1.0,
    top_defects: int = 16,
    top_contexts: int = 32,
    top_carriers: int = 64,
    top_failures: int = 32,
    margin_threshold: float = 0.0,
    cost_weight: float = 0.05,
    carrier_weight: float = 0.25,
    audit_penalty: float = 1.0,
) -> QGenReport:
    response_rows = read_jsonl(responses)
    audit_rows = read_jsonl(audits) if audits else []
    gen = CokerDrivenGenerator(ridge=ridge, max_mass=max_mass)
    rep = gen.run(response_rows, audit_rows=audit_rows, top_defects=top_defects, top_contexts=top_contexts, top_carriers=top_carriers, top_failures=top_failures, margin_threshold=margin_threshold, cost_weight=cost_weight, carrier_weight=carrier_weight, audit_penalty=audit_penalty)
    if out_dir:
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / "qgen_report.json").write_text(json.dumps(rep.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        write_jsonl(out / "qgen_defect_atoms.jsonl", [p["atom"] for p in rep.generated_defect_atoms])
        write_jsonl(out / "qgen_context_candidates.jsonl", [p["action"] for p in rep.context_candidates])
        write_jsonl(out / "qgen_context_acceptance.jsonl", rep.context_candidates)
        write_jsonl(out / "qgen_accepted_actions.jsonl", [p["action"] for p in rep.context_candidates if bool(p.get("accepted"))])
        write_jsonl(out / "qgen_carrier_incidence.jsonl", rep.carrier_incidence)
        write_jsonl(out / "qgen_failure_signatures.jsonl", rep.failure_signatures)
        # Registry-compatible candidate defect registry.
        atoms = [DefectAtom(**p["atom"]) for p in rep.generated_defect_atoms]
        DefectRegistry(atoms=atoms, version="lean-rgc-qgen-defect-registry-v0.1", metadata={"source": "qgen", "canonical_status": "candidate_chart"}).save(out / "qgen_defect_registry.json")
    return rep


__all__ = [
    "GeneratedDefectProposal",
    "CarrierIncidenceProposal",
    "ContextProposal",
    "QGenReport",
    "CokerDrivenGenerator",
    "qgen_from_files",
]
