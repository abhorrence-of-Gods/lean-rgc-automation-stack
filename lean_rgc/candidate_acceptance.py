from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
import json

import numpy as np

from .schemas import read_jsonl, write_jsonl
from .defect_registry import DefectRegistry, DefectAtom


def _as_vec(x: Any) -> np.ndarray:
    try:
        return np.asarray(x or [], dtype=float)
    except Exception:
        return np.zeros(0, dtype=float)


def _dot_aligned(a: np.ndarray, b: np.ndarray) -> float:
    n = min(int(a.size), int(b.size))
    if n <= 0:
        return 0.0
    return float(np.dot(a[:n], b[:n]))


def _defect_vec(row: dict[str, Any]) -> np.ndarray:
    db = row.get("defect_before") or row.get("defect") or {}
    if isinstance(db, dict):
        if isinstance(db.get("flat"), list):
            return _as_vec(db.get("flat"))
        vals: list[float] = []
        for block in ("goal", "type", "search", "carrier", "audit"):
            if isinstance(db.get(block), dict):
                for k in sorted(db[block]):
                    try:
                        vals.append(float(db[block][k]))
                    except Exception:
                        pass
        return _as_vec(vals)
    return np.zeros(0, dtype=float)


def _response_vec(row: dict[str, Any]) -> np.ndarray:
    if isinstance(row.get("response_flat"), list):
        return _as_vec(row.get("response_flat"))
    if isinstance(row.get("response"), dict):
        return _as_vec([row["response"][k] for k in sorted(row["response"])])
    return np.zeros(0, dtype=float)


def _carrier_gain(row: dict[str, Any], atoms: set[str] | None = None) -> float:
    cd = row.get("carrier_delta") or {}
    if not isinstance(cd, dict):
        return 0.0
    if atoms:
        return float(sum(max(0.0, float(cd.get(a, 0.0))) for a in atoms))
    return float(sum(max(0.0, float(v)) for v in cd.values()))


def _status(row: dict[str, Any]) -> str:
    return str(row.get("audit_status") or row.get("status") or "unknown")


def _action(row: dict[str, Any]) -> dict[str, Any]:
    a = row.get("action")
    return a if isinstance(a, dict) else {}


def _metadata(row: dict[str, Any]) -> dict[str, Any]:
    a = _action(row)
    m = a.get("metadata")
    return m if isinstance(m, dict) else {}


def addressed_atoms(row: dict[str, Any]) -> set[str]:
    atoms: set[str] = set()
    a = _action(row)
    atoms.update(map(str, a.get("carrier_tags") or []))
    m = _metadata(row)
    atoms.update(map(str, m.get("active_registry_atoms") or []))
    ctx = m.get("carrier_context")
    if isinstance(ctx, dict):
        if ctx.get("carrier_atom"):
            atoms.add(str(ctx.get("carrier_atom")))
        atoms.update(map(str, ctx.get("residual_atoms") or []))
    exp = m.get("exposure")
    if isinstance(exp, dict):
        atoms.update(map(str, exp.get("carrier_atoms") or []))
        if isinstance(exp.get("expected_carrier_delta"), dict):
            atoms.update(map(str, exp.get("expected_carrier_delta", {}).keys()))
    return atoms


def generated_source(row: dict[str, Any]) -> str:
    m = _metadata(row)
    if m.get("generated_by"):
        return str(m.get("generated_by"))
    exp = m.get("exposure")
    if isinstance(exp, dict) and exp.get("prefix_id") and exp.get("prefix_id") != "id":
        return "carrier_exposure"
    return "unknown"


@dataclass
class CandidateAcceptance:
    state_id: str
    task_id: str
    action_id: str
    tactic: str
    status: str
    generated_by: str
    addressed_atoms: list[str]
    response_score: float
    base_support: float
    carrier_gain: float
    response_norm: float
    defect_norm: float
    cost: float
    audit_penalty: float
    coker_margin_proxy: float
    accepted: bool
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CandidateAcceptanceSummary:
    n: int
    accepted: int
    mean_margin: float
    max_margin: float
    accepted_by_source: dict[str, int] = field(default_factory=dict)
    accepted_by_atom: dict[str, int] = field(default_factory=dict)
    status_counts: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def base_support_by_state(base_rows: list[dict[str, Any]]) -> dict[str, float]:
    support: dict[str, float] = {}
    for r in base_rows:
        sid = str(r.get("state_id", ""))
        score = _dot_aligned(_response_vec(r), _defect_vec(r))
        support[sid] = max(support.get(sid, float("-inf")), score)
    return {k: (0.0 if v == float("-inf") else float(v)) for k, v in support.items()}


def accept_candidate_rows(
    base_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
    *,
    margin_threshold: float = 0.0,
    cost_weight: float = 0.05,
    carrier_weight: float = 0.25,
    audit_penalty: float = 1.0,
    require_success: bool = False,
) -> list[CandidateAcceptance]:
    support = base_support_by_state(base_rows)
    out: list[CandidateAcceptance] = []
    for r in candidate_rows:
        sid = str(r.get("state_id", ""))
        tid = str(r.get("task_id", ""))
        a = _action(r)
        atoms = addressed_atoms(r)
        rv = _response_vec(r)
        dv = _defect_vec(r)
        response_score = _dot_aligned(rv, dv)
        base = float(support.get(sid, 0.0))
        carrier = _carrier_gain(r, atoms)
        status = _status(r)
        cost = float(a.get("cost_estimate", 1.0) or 1.0)
        penalty = float(audit_penalty if status in {"timeout", "unsafe", "elab_error"} else 0.0)
        margin = float(response_score - base + carrier_weight * carrier - cost_weight * cost - penalty)
        ok_status = status in {"success", "partial", "dry_run"} if require_success else status not in {"timeout", "unsafe", "elab_error"}
        accepted = bool(ok_status and margin > margin_threshold)
        out.append(CandidateAcceptance(
            state_id=sid,
            task_id=tid,
            action_id=str(r.get("action_id") or a.get("action_id") or ""),
            tactic=str(a.get("tactic") or r.get("tactic") or ""),
            status=status,
            generated_by=generated_source(r),
            addressed_atoms=sorted(atoms),
            response_score=float(response_score),
            base_support=base,
            carrier_gain=float(carrier),
            response_norm=float(np.linalg.norm(rv)) if rv.size else 0.0,
            defect_norm=float(np.linalg.norm(dv)) if dv.size else 0.0,
            cost=cost,
            audit_penalty=penalty,
            coker_margin_proxy=margin,
            accepted=accepted,
            metadata={"action": a, "raw_row_keys": sorted(r.keys())},
        ))
    return out


def summarize_acceptance(records: list[CandidateAcceptance]) -> CandidateAcceptanceSummary:
    if not records:
        return CandidateAcceptanceSummary(n=0, accepted=0, mean_margin=0.0, max_margin=0.0)
    accepted = [r for r in records if r.accepted]
    by_source: dict[str, int] = {}
    by_atom: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    for r in records:
        status_counts[r.status] = status_counts.get(r.status, 0) + 1
        if r.accepted:
            by_source[r.generated_by] = by_source.get(r.generated_by, 0) + 1
            for a in r.addressed_atoms:
                by_atom[a] = by_atom.get(a, 0) + 1
    margins = [r.coker_margin_proxy for r in records]
    return CandidateAcceptanceSummary(
        n=len(records),
        accepted=len(accepted),
        mean_margin=float(np.mean(margins)),
        max_margin=float(np.max(margins)),
        accepted_by_source=by_source,
        accepted_by_atom=by_atom,
        status_counts=status_counts,
    )


def accept_candidates_file(base_responses: str | Path, candidate_responses: str | Path, out: str | Path, *, summary_out: str | Path | None = None, **kwargs: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    base = read_jsonl(base_responses)
    cand = read_jsonl(candidate_responses)
    records = accept_candidate_rows(base, cand, **kwargs)
    rows = [r.to_dict() for r in records]
    write_jsonl(out, rows)
    summary = summarize_acceptance(records).to_dict()
    if summary_out:
        Path(summary_out).parent.mkdir(parents=True, exist_ok=True)
        Path(summary_out).write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return rows, summary


def promote_registry_from_acceptance(registry_path: str | Path, acceptance_path: str | Path, out: str | Path, *, min_accepted: int = 1, min_mean_margin: float = 0.0) -> DefectRegistry:
    reg = DefectRegistry.load(registry_path)
    acc_rows = read_jsonl(acceptance_path)
    by_atom: dict[str, list[dict[str, Any]]] = {}
    for r in acc_rows:
        if not r.get("accepted"):
            continue
        for atom in r.get("addressed_atoms") or []:
            by_atom.setdefault(str(atom), []).append(r)
    new_atoms: list[DefectAtom] = []
    for atom in reg.atoms:
        rows = by_atom.get(atom.atom_id, [])
        margins = [float(r.get("coker_margin_proxy", 0.0)) for r in rows]
        mean_margin = float(np.mean(margins)) if margins else 0.0
        d = atom.to_dict()
        ev = dict(d.get("evidence") or {})
        ev["candidate_acceptance"] = {
            "accepted_count": len(rows),
            "mean_margin": mean_margin,
            "max_margin": float(np.max(margins)) if margins else 0.0,
        }
        d["evidence"] = ev
        if len(rows) >= min_accepted and mean_margin >= min_mean_margin:
            d["status"] = "accepted"
        new_atoms.append(DefectAtom(**d))
    out_reg = DefectRegistry(atoms=new_atoms, version="lean-rgc-defect-registry-v0.7", metadata={**reg.metadata, "promoted_from_acceptance": str(acceptance_path)})
    out_reg.save(out)
    return out_reg
