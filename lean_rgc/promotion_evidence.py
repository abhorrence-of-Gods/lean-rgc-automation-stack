from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable
import csv
import json

from .schemas import read_jsonl, write_jsonl, stable_hash

SCHEMA_VERSION = "lean-rgc-promotion-evidence-v38.0"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _as_float(v: Any, default: float = 0.0) -> float:
    try:
        if v is None or v == "":
            return default
        return float(v)
    except Exception:
        return default


def _as_bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    if isinstance(v, str):
        return v.strip().lower() in {"1", "true", "yes", "y", "pass", "passed", "accepted"}
    return False


def _action(row: dict[str, Any]) -> dict[str, Any]:
    if isinstance(row.get("action"), dict):
        return dict(row["action"])
    if isinstance(row.get("patch"), dict):
        return dict(row["patch"])
    meta = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
    if isinstance(meta.get("action"), dict):
        return dict(meta["action"])
    return row


def _action_id(row: dict[str, Any]) -> str:
    a = _action(row)
    return str(row.get("action_id") or a.get("action_id") or a.get("id") or "")


def _tactic(row: dict[str, Any]) -> str:
    a = _action(row)
    return str(row.get("tactic") or a.get("tactic") or a.get("full_tactic") or "")


def _carrier_atom(row: dict[str, Any]) -> str:
    p = row.get("patch") if isinstance(row.get("patch"), dict) else {}
    return str(row.get("carrier_atom") or p.get("carrier_atom") or row.get("carrier_key") or row.get("atom") or "")


def _parent_residual_keys(row: dict[str, Any]) -> list[str]:
    keys: list[str] = []
    a = _action(row)
    meta = a.get("metadata") if isinstance(a.get("metadata"), dict) else {}
    qgen = meta.get("qgen") if isinstance(meta.get("qgen"), dict) else {}
    for source in (row, meta, qgen):
        if not isinstance(source, dict):
            continue
        for fld in ("parent_residual_keys", "residual_keys", "source_residual_keys"):
            vals = source.get(fld)
            if isinstance(vals, list):
                for k in vals:
                    if k is not None:
                        keys.append(str(k))
        for fld in ("residual_key", "parent_residual_key", "coordinate_id", "carrier_atom"):
            v = source.get(fld)
            if v is not None and v != "":
                keys.append(str(v))
        for c in source.get("top_coordinate_contributions") or source.get("top_loadings") or []:
            if isinstance(c, dict):
                k = c.get("key") or c.get("residual_key") or c.get("coordinate") or c.get("carrier_key")
                if k is not None:
                    keys.append(str(k))
    return sorted(set(keys))


def _iter_existing(paths: Iterable[Path]) -> Iterable[Path]:
    seen: set[Path] = set()
    for p in paths:
        if p.exists() and p not in seen:
            seen.add(p)
            yield p


def _round_dirs(root: Path) -> list[Path]:
    rds = sorted([p for p in root.glob("round_*") if p.is_dir()])
    return rds if rds else [root]


def _known_acceptance_paths(root: Path) -> list[Path]:
    names = [
        "qgen_acceptance_rows.jsonl", "qgen_robust_acceptance_rows.jsonl",
        "qgen_registry_acceptance_rows.jsonl", "qgen_registry_robust_acceptance_rows.jsonl",
        "action_geometry_acceptance_rows.jsonl", "action_geometry_robust_acceptance_rows.jsonl",
        "quotient_coordinate_acceptance_rows.jsonl", "quotient_coordinate_robust_acceptance_rows.jsonl",
        "carrier_quotient_acceptance_rows.jsonl", "carrier_quotient_robust_acceptance_rows.jsonl",
        "contextual_probe_acceptance_rows.jsonl", "contextual_probe_robust_acceptance_rows.jsonl",
        "premise_response_acceptance_rows.jsonl", "premise_response_robust_acceptance_rows.jsonl",
        "source_budget_acceptance_rows.jsonl", "registry_acceptance_rows.jsonl",
        "failure_signature_acceptance_rows.jsonl", "ir_acceptance_rows.jsonl",
    ]
    out: list[Path] = []
    for r in _round_dirs(root):
        for n in names:
            out.append(r / n)
        # Fallback: any file with acceptance rows in the name.
        out.extend(r.glob("**/*acceptance_rows.jsonl"))
    return list(_iter_existing(out))


def _known_poms_status_paths(root: Path) -> list[Path]:
    return list(_iter_existing([root / "poms_status_rows.jsonl"] + [r / "poms_status_rows.jsonl" for r in _round_dirs(root)]))


def _known_residual_paths(root: Path) -> list[Path]:
    paths: list[Path] = []
    for r in _round_dirs(root):
        paths += [
            r / "quotient_coordinates" / "state_coker_normals.jsonl",
            r / "quotient_coordinates" / "quotient_coordinates.jsonl",
            r / "carrier_quotient" / "carrier_state_coker_normals.jsonl",
            r / "carrier_quotient" / "carrier_quotient_coordinates.jsonl",
            r / "qgen" / "qgen_defect_atoms.jsonl",
            r / "qgen" / "qgen_report.json",
        ]
    return list(_iter_existing(paths))


def _known_validation_paths(root: Path) -> list[Path]:
    paths: list[Path] = []
    for r in _round_dirs(root):
        paths += [
            r / "quotient_coordinates" / "quotient_coordinate_validation_rows.jsonl",
            r / "carrier_quotient" / "carrier_quotient_validation_rows.jsonl",
            r / "qgen_robust_acceptance_rows.jsonl",
            r / "qgen_registry_robust_acceptance_rows.jsonl",
        ]
    return list(_iter_existing(paths))


@dataclass
class PromotionEvidenceRow:
    id: str
    evidence_kind: str
    residual_key: str = ""
    parent_residual_keys: list[str] | None = None
    action_id: str = ""
    tactic: str = ""
    carrier_atom: str = ""
    source: str = ""
    parent_obstruction: str = ""
    parent_nonpaid: bool = False
    dual_certificate: bool = False
    least_repair: bool = False
    parent_paid: bool = False
    modality: str = "audit"
    confidence: float = 0.0
    score: float = 0.0
    margin: float = 0.0
    robust_margin: float = 0.0
    residual_norm: float = 0.0
    relative_residual: float = 0.0
    support_count: int = 0
    reason: str = ""
    canonical_status: str = "promotion_evidence_candidate_not_canonical"
    provenance: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if d["parent_residual_keys"] is None:
            d["parent_residual_keys"] = []
        if d["provenance"] is None:
            d["provenance"] = {}
        return d


def _row_id(prefix: str, row: dict[str, Any]) -> str:
    return prefix + "_" + stable_hash(row, 12)


def _residual_keys_from_normal_row(row: dict[str, Any]) -> list[str]:
    keys: list[str] = []
    for tl in row.get("top_loadings") or row.get("top_coordinate_contributions") or []:
        if isinstance(tl, dict):
            k = tl.get("key") or tl.get("residual_key") or tl.get("carrier_key") or tl.get("coordinate")
            if k is not None:
                keys.append(str(k))
    for k in row.get("response_keys") or row.get("carrier_keys") or []:
        # Include all keys only if no top loadings exist.
        if not keys and k is not None:
            keys.append(str(k))
    for fld in ("residual_key", "coordinate_id", "carrier_atom", "parent_residual_key"):
        v = row.get(fld)
        if v is not None and v != "":
            keys.append(str(v))
    return sorted(set(keys))


def _collect_parent_nonpaid_evidence(
    root: Path,
    *,
    min_relative_residual: float,
    min_residual_norm: float,
    min_support_count: int,
) -> tuple[list[PromotionEvidenceRow], dict[str, PromotionEvidenceRow]]:
    out: list[PromotionEvidenceRow] = []
    best: dict[str, PromotionEvidenceRow] = {}
    for path in _known_residual_paths(root):
        rows: list[dict[str, Any]] = []
        if path.suffix == ".jsonl":
            rows = read_jsonl(path)
        else:
            data = _read_json(path)
            if isinstance(data.get("defect_atoms"), list):
                rows.extend([r for r in data["defect_atoms"] if isinstance(r, dict)])
            if isinstance(data.get("rows"), list):
                rows.extend([r for r in data["rows"] if isinstance(r, dict)])
        for row in rows:
            residual_norm = _as_float(row.get("residual_norm") or row.get("norm") or row.get("weight") or row.get("score"))
            relative = _as_float(row.get("relative_residual") or row.get("relative_norm") or row.get("normalized_residual") or row.get("support_value"))
            support = int(_as_float(row.get("support_count") or row.get("n_states") or len(row.get("support_state_ids") or []), 0))
            keys = _residual_keys_from_normal_row(row)
            if not keys:
                continue
            parent_ok = (relative >= min_relative_residual or residual_norm >= min_residual_norm) and support >= min_support_count
            for k in keys:
                ev = PromotionEvidenceRow(
                    id=_row_id("parent_nonpaid", {"path": str(path), "key": k, "row": row}),
                    evidence_kind="parent_nonpaid_residual",
                    residual_key=k,
                    parent_residual_keys=[k],
                    parent_obstruction=f"parent_residual::{k}",
                    parent_nonpaid=parent_ok,
                    confidence=max(relative, residual_norm),
                    residual_norm=residual_norm,
                    relative_residual=relative,
                    support_count=support,
                    reason=("residual_norm_or_relative_residual_exceeds_threshold" if parent_ok else "residual_evidence_below_threshold"),
                    provenance={"path": str(path), "row": row},
                )
                out.append(ev)
                if parent_ok and (k not in best or ev.confidence > best[k].confidence):
                    best[k] = ev
    return out, best


def _collect_dual_evidence(
    root: Path,
    *,
    min_margin: float,
    min_robust_margin: float,
) -> tuple[list[PromotionEvidenceRow], dict[str, PromotionEvidenceRow]]:
    out: list[PromotionEvidenceRow] = []
    best_by_action: dict[str, PromotionEvidenceRow] = {}
    for path in _known_acceptance_paths(root):
        for row in read_jsonl(path):
            aid = _action_id(row)
            tactic = _tactic(row)
            accepted = _as_bool(row.get("accepted")) or _as_bool(row.get("accepted_by_coker")) or _as_bool(row.get("accepted_by_robust_coker")) or _as_bool(row.get("accepted_by"))
            margin = _as_float(row.get("margin") or row.get("coker_margin_proxy") or row.get("coker_surplus") or row.get("score"))
            robust = _as_float(row.get("robust_margin") or row.get("lcb_margin") or row.get("heldout_margin"), margin)
            is_robust_file = "robust" in path.name
            dual_ok = accepted and ((is_robust_file and robust >= min_robust_margin) or margin >= min_margin)
            keys = _parent_residual_keys(row)
            if not keys:
                keys = [str(row.get("residual_key") or row.get("coordinate_id") or row.get("carrier_atom") or "")]
                keys = [k for k in keys if k]
            ev = PromotionEvidenceRow(
                id=_row_id("dual", {"path": str(path), "row": row}),
                evidence_kind="dual_coker_certificate",
                residual_key=keys[0] if keys else "",
                parent_residual_keys=keys,
                action_id=aid,
                tactic=tactic,
                carrier_atom=_carrier_atom(row),
                source=str(row.get("source") or path.stem),
                dual_certificate=dual_ok,
                confidence=max(margin, robust),
                score=_as_float(row.get("score"), max(margin, robust)),
                margin=margin,
                robust_margin=robust,
                reason=("accepted_with_positive_coker_or_robust_margin" if dual_ok else "no_positive_coker_margin"),
                provenance={"path": str(path), "row": row},
            )
            out.append(ev)
            if aid and dual_ok and (aid not in best_by_action or ev.confidence > best_by_action[aid].confidence):
                best_by_action[aid] = ev
    return out, best_by_action


def _collect_patch_dual_evidence(root: Path, *, min_delta: float = 0.0) -> tuple[list[PromotionEvidenceRow], dict[tuple[str, str], PromotionEvidenceRow]]:
    out: list[PromotionEvidenceRow] = []
    best: dict[tuple[str, str], PromotionEvidenceRow] = {}
    patch_paths: list[Path] = []
    for r in _round_dirs(root):
        patch_paths += [
            r / "qgen_carrier_incidence_audited.jsonl",
            r / "carrier_quotient" / "carrier_quotient_incidence_patches.jsonl",
            r / "qgen" / "qgen_carrier_incidence.jsonl",
        ]
    for path in _iter_existing(patch_paths):
        for row in read_jsonl(path):
            aid = str(row.get("action_id") or row.get("action") or "")
            atom = _carrier_atom(row)
            if not aid and isinstance(row.get("action"), dict):
                aid = _action_id(row["action"])
            observed = _as_float(row.get("holdout_observed_mean_delta") if row.get("holdout_observed_mean_delta") is not None else row.get("observed_mean_delta") or row.get("mean_delta"))
            accepted = _as_bool(row.get("accepted_by_patch_audit")) or _as_bool(row.get("accepted_by_heldout_patch_audit")) or observed >= min_delta
            ev = PromotionEvidenceRow(
                id=_row_id("carrier_dual", {"path": str(path), "row": row}),
                evidence_kind="carrier_patch_dual_certificate",
                residual_key=atom,
                parent_residual_keys=[atom] if atom else [],
                action_id=aid,
                carrier_atom=atom,
                source=str(row.get("source") or path.stem),
                dual_certificate=accepted,
                confidence=observed,
                score=observed,
                margin=observed,
                robust_margin=observed,
                reason=("carrier_patch_has_positive_observed_delta" if accepted else "carrier_patch_delta_below_threshold"),
                provenance={"path": str(path), "row": row},
            )
            out.append(ev)
            key = (aid, atom)
            if accepted and (key not in best or ev.confidence > best[key].confidence):
                best[key] = ev
    return out, best


def _collect_poms_rows(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for p in _known_poms_status_paths(root):
        rows.extend(read_jsonl(p))
    return rows


def _repair_group_key(row: dict[str, Any]) -> str:
    keys = _parent_residual_keys(row)
    if keys:
        return keys[0]
    atom = _carrier_atom(row)
    if atom:
        return atom
    return str(row.get("residual_key") or row.get("source") or row.get("kind") or "unknown")


def _candidate_effect_score(row: dict[str, Any], duals: dict[str, PromotionEvidenceRow], carrier_duals: dict[tuple[str, str], PromotionEvidenceRow]) -> float:
    aid = _action_id(row)
    atom = _carrier_atom(row)
    if aid in duals:
        return duals[aid].confidence
    if (aid, atom) in carrier_duals:
        return carrier_duals[(aid, atom)].confidence
    # POMS status fallback.
    status = str(row.get("poms_status") or "")
    base = {"paid_witness": 1.0, "accepted_witness": 0.5, "paid_carrier_patch_witness": 1.0, "carrier_patch_witness": 0.5}.get(status, 0.0)
    return base


def _candidate_cost(row: dict[str, Any]) -> float:
    a = _action(row)
    meta = a.get("metadata") if isinstance(a.get("metadata"), dict) else {}
    for obj in (row, a, meta):
        if not isinstance(obj, dict):
            continue
        for k in ("cost", "cost_estimate", "audit_cost", "import_cost"):
            if k in obj:
                return max(_as_float(obj.get(k), 1.0), 1e-9)
    return 1.0


def _least_repair_actions(
    poms_rows: list[dict[str, Any]],
    duals: dict[str, PromotionEvidenceRow],
    carrier_duals: dict[tuple[str, str], PromotionEvidenceRow],
    *,
    least_repair_epsilon: float,
) -> set[str]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for r in poms_rows:
        aid = _action_id(r)
        if not aid:
            continue
        groups.setdefault(_repair_group_key(r), []).append(r)
    least: set[str] = set()
    for _g, rows in groups.items():
        scored: list[tuple[float, float, str, dict[str, Any]]] = []
        for r in rows:
            aid = _action_id(r)
            eff = _candidate_effect_score(r, duals, carrier_duals)
            cost = _candidate_cost(r)
            score = eff / max(cost, 1e-9)
            scored.append((score, eff, aid, r))
        if not scored:
            continue
        scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
        best_score = scored[0][0]
        for score, eff, aid, _r in scored:
            if best_score - score <= least_repair_epsilon and eff > 0:
                least.add(aid)
    return least


def generate_promotion_evidence(
    run_dir: str | Path,
    *,
    out_json: str | Path | None = None,
    out_jsonl: str | Path | None = None,
    out_poms: str | Path | None = None,
    out_csv: str | Path | None = None,
    min_relative_residual: float = 0.05,
    min_residual_norm: float = 1e-6,
    min_support_count: int = 1,
    min_margin: float = 0.0,
    min_robust_margin: float = 0.0,
    least_repair_epsilon: float = 1e-9,
) -> dict[str, Any]:
    """Generate finite POMS promotion evidence from existing RGC audit artifacts.

    The generated rows are conservative chart-level evidence.  They are designed
    to be directly consumable by ``poms-promote --evidence`` and are not canonical
    declarations by themselves.
    """
    root = Path(run_dir)
    parent_rows, parent_by_key = _collect_parent_nonpaid_evidence(
        root,
        min_relative_residual=min_relative_residual,
        min_residual_norm=min_residual_norm,
        min_support_count=min_support_count,
    )
    dual_rows, dual_by_action = _collect_dual_evidence(root, min_margin=min_margin, min_robust_margin=min_robust_margin)
    carrier_rows, carrier_duals = _collect_patch_dual_evidence(root)
    poms_rows = _collect_poms_rows(root)
    least_actions = _least_repair_actions(poms_rows, dual_by_action, carrier_duals, least_repair_epsilon=least_repair_epsilon)

    combined: list[PromotionEvidenceRow] = []
    combined.extend(parent_rows)
    combined.extend(dual_rows)
    combined.extend(carrier_rows)

    # Compose action-level POMS-ready evidence by joining parent residual, dual
    # certificate, and least-repair proxies.
    poms_ready: list[dict[str, Any]] = []
    for row in poms_rows:
        aid = _action_id(row)
        tactic = _tactic(row)
        atom = _carrier_atom(row)
        keys = _parent_residual_keys(row)
        if atom and atom not in keys:
            keys.append(atom)
        parent_ok = any(k in parent_by_key and parent_by_key[k].parent_nonpaid for k in keys)
        dual_ok = (aid in dual_by_action and dual_by_action[aid].dual_certificate) or ((aid, atom) in carrier_duals and carrier_duals[(aid, atom)].dual_certificate)
        least_ok = aid in least_actions
        confs = []
        confs.extend([parent_by_key[k].confidence for k in keys if k in parent_by_key])
        if aid in dual_by_action:
            confs.append(dual_by_action[aid].confidence)
        if (aid, atom) in carrier_duals:
            confs.append(carrier_duals[(aid, atom)].confidence)
        confidence = max(confs) if confs else 0.0
        ev = PromotionEvidenceRow(
            id=_row_id("poms_ready", {"action_id": aid, "keys": keys, "status": row.get("poms_status")}),
            evidence_kind="poms_ready_joined_evidence",
            # POMS-ready rows are action-scoped evidence.  Keep residual keys
            # in provenance, not in top-level matching fields, otherwise a
            # least-repair certificate for one action would match every action
            # sharing the same parent residual key in poms_promotion.
            residual_key="",
            parent_residual_keys=[],
            action_id=aid,
            tactic=tactic,
            carrier_atom=atom,
            # Keep top-level source non-matching; poms_promotion treats source
            # as a broad match key, while this evidence is action-scoped.
            source="promotion_evidence",
            parent_obstruction=(f"parent_residual::{keys[0]}" if keys else "parent_obstruction_unknown"),
            parent_nonpaid=parent_ok,
            dual_certificate=dual_ok,
            least_repair=least_ok,
            modality=str(row.get("modality") or "audit"),
            confidence=confidence,
            score=_candidate_effect_score(row, dual_by_action, carrier_duals),
            reason="joined_parent_nonpaid_dual_and_least_repair_from_finite_audits",
            canonical_status="promotion_evidence_for_poms_not_canonical",
            provenance={"poms_row": row, "parent_keys": keys, "least_repair_actions": sorted(least_actions)},
        )
        combined.append(ev)
        poms_ready.append(ev.to_dict())

    rows = [r.to_dict() for r in combined]
    by_kind: dict[str, int] = {}
    for r in rows:
        by_kind[str(r.get("evidence_kind"))] = by_kind.get(str(r.get("evidence_kind")), 0) + 1
    summary = {
        "schema_version": SCHEMA_VERSION,
        "run_dir": str(root),
        "canonical_status": "promotion_evidence_chart_not_canonical",
        "n_evidence_rows": len(rows),
        "n_poms_ready_rows": len(poms_ready),
        "by_kind": by_kind,
        "n_parent_nonpaid_keys": len(parent_by_key),
        "n_dual_actions": len(dual_by_action),
        "n_carrier_dual_patches": len(carrier_duals),
        "n_least_repair_actions": len(least_actions),
        "thresholds": {
            "min_relative_residual": min_relative_residual,
            "min_residual_norm": min_residual_norm,
            "min_support_count": min_support_count,
            "min_margin": min_margin,
            "min_robust_margin": min_robust_margin,
            "least_repair_epsilon": least_repair_epsilon,
        },
        "notes": [
            "Generated evidence is finite audit/coker evidence, not a canonical proof.",
            "Rows in promotion_evidence_for_poms.jsonl are consumable by poms-promote --evidence.",
            "Canonical promotion still requires doctrine review unless explicitly declared downstream.",
        ],
    }
    rep = {"summary": summary, "rows": rows, "poms_ready_rows": poms_ready}
    if out_json:
        p = Path(out_json); p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")
    if out_jsonl:
        write_jsonl(out_jsonl, rows)
    if out_poms:
        write_jsonl(out_poms, poms_ready)
    if out_csv:
        p = Path(out_csv); p.parent.mkdir(parents=True, exist_ok=True)
        fields = ["id", "evidence_kind", "residual_key", "action_id", "tactic", "carrier_atom", "parent_nonpaid", "dual_certificate", "least_repair", "confidence", "reason", "canonical_status"]
        with p.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
            for r in rows:
                w.writerow({k: r.get(k) for k in fields})
    return rep


__all__ = ["generate_promotion_evidence", "PromotionEvidenceRow"]
