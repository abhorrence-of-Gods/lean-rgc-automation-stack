from __future__ import annotations

from pathlib import Path
from typing import Any
import csv
import json

from .schemas import read_jsonl, write_jsonl


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _action(row: dict[str, Any]) -> dict[str, Any]:
    if isinstance(row.get("action"), dict):
        return dict(row["action"])
    if isinstance(row.get("metadata"), dict) and isinstance(row["metadata"].get("action"), dict):
        return dict(row["metadata"]["action"])
    return row


def _action_id(row: dict[str, Any]) -> str:
    a = _action(row)
    return str(a.get("action_id") or a.get("id") or row.get("action_id") or a.get("tactic") or row.get("tactic") or "")


def _tactic(row: dict[str, Any]) -> str:
    a = _action(row)
    return str(a.get("tactic") or a.get("full_tactic") or row.get("tactic") or "")


def _task_id(row: dict[str, Any]) -> str:
    a = _action(row)
    meta = a.get("metadata") if isinstance(a.get("metadata"), dict) else {}
    return str(row.get("task_id") or row.get("state_id") or meta.get("task_id") or meta.get("state_id") or "")


def _keys(row: dict[str, Any]) -> set[str]:
    aid = _action_id(row)
    tac = _tactic(row)
    task = _task_id(row)
    ks: set[str] = set()
    if aid:
        ks.add("id:" + aid)
        if task:
            ks.add("task_id:" + task + "\t" + aid)
    if tac:
        ks.add("tactic:" + tac)
        if task:
            ks.add("task_tactic:" + task + "\t" + tac)
    return ks


def _index_realized_rows(run_dir: Path) -> dict[str, list[dict[str, Any]]]:
    rep = _read_json(run_dir / "qgen_realized_calibration.json")
    idx: dict[str, list[dict[str, Any]]] = {}
    for row in rep.get("rows", []) if isinstance(rep.get("rows"), list) else []:
        action = row.get("action") if isinstance(row.get("action"), dict) else row
        for k in _keys(action):
            idx.setdefault(k, []).append(row)
    return idx


def _has_realized_positive(rows: list[dict[str, Any]], *, min_goal_response: float, require_success: bool) -> bool:
    if not rows:
        return False
    for r in rows:
        try:
            gr = float(r.get("goal_response_next", 0.0) or 0.0)
        except Exception:
            gr = 0.0
        ok = bool(r.get("success_next")) if require_success else True
        if ok and gr >= min_goal_response:
            return True
    return False


def _accepted_sources(rdir: Path) -> list[tuple[str, Path]]:
    return [
        ("qgen_robust", rdir / "qgen_robust_accepted_actions.jsonl"),
        ("qgen", rdir / "qgen_accepted_actions.jsonl"),
        ("qgen_registry_robust", rdir / "qgen_registry_robust_accepted_actions.jsonl"),
        ("qgen_registry", rdir / "qgen_registry_accepted_actions.jsonl"),
    ]


def _candidate_sources(rdir: Path) -> list[tuple[str, Path]]:
    return [
        ("qgen_context", rdir / "qgen" / "qgen_context_candidates.jsonl"),
        ("qgen_registry", rdir / "qgen_registry_candidates.jsonl"),
    ]


def _patch_sources(rdir: Path) -> list[tuple[str, Path]]:
    return [
        ("qgen_carrier_patch_audited", rdir / "qgen_carrier_incidence_audited.jsonl"),
        ("qgen_carrier_patch_raw", rdir / "qgen" / "qgen_carrier_incidence.jsonl"),
    ]


def collect_poms_status(
    run_dir: str | Path,
    *,
    out_json: str | Path | None = None,
    out_jsonl: str | Path | None = None,
    out_csv: str | Path | None = None,
    min_realized_goal_response: float = 0.0,
    require_realized_success: bool = False,
) -> dict[str, Any]:
    """Build a minimal POMS status ledger for qgen-generated artifacts.

    This is intentionally conservative: accepted qgen objects are classified as
    witnesses or paid candidates, not canonical objects.  Canonical promotion still
    requires parent-non-paid + dual certificate + least-repair evidence.
    """
    root = Path(run_dir)
    round_dirs = sorted([p for p in root.glob("round_*") if p.is_dir()])
    realized_idx = _index_realized_rows(root)
    rows: list[dict[str, Any]] = []

    for ri, rdir in enumerate(round_dirs):
        accepted_ids: set[str] = set()
        for source, path in _accepted_sources(rdir):
            if not path.exists():
                continue
            for row in read_jsonl(path):
                aid = _action_id(row)
                accepted_ids.add(aid)
                rrows: list[dict[str, Any]] = []
                for k in _keys(row):
                    rrows.extend(realized_idx.get(k, []))
                realized = _has_realized_positive(rrows, min_goal_response=min_realized_goal_response, require_success=require_realized_success)
                status = "paid_witness" if realized else "accepted_witness"
                reason = "accepted_and_realized_positive" if realized else "accepted_but_no_positive_next_round_realization"
                rows.append({
                    "kind": "context_action",
                    "round": ri,
                    "source": source,
                    "action_id": aid,
                    "tactic": _tactic(row),
                    "poms_status": status,
                    "canonical_status": "not_canonical_parent_nonpaid_least_repair_required",
                    "reason": reason,
                    "n_realized_rows": len(rrows),
                    "parent_nonpaid": False,
                    "dual_certificate": False,
                    "least_repair": False,
                    "action": _action(row),
                })
        # Raw qgen candidates not accepted remain witness/open candidates.
        for source, path in _candidate_sources(rdir):
            if not path.exists():
                continue
            for row in read_jsonl(path):
                aid = _action_id(row)
                if aid in accepted_ids:
                    continue
                rows.append({
                    "kind": "context_action",
                    "round": ri,
                    "source": source,
                    "action_id": aid,
                    "tactic": _tactic(row),
                    "poms_status": "witness_candidate",
                    "canonical_status": "not_canonical_candidate_chart_only",
                    "reason": "generated_but_not_coker_accepted",
                    "parent_nonpaid": False,
                    "dual_certificate": False,
                    "least_repair": False,
                    "action": _action(row),
                })
        # Carrier patch statuses.
        seen_patches: set[tuple[str, str]] = set()
        for source, path in _patch_sources(rdir):
            if not path.exists():
                continue
            for p in read_jsonl(path):
                aid = str(p.get("action_id") or p.get("action") or "")
                atom = str(p.get("carrier_atom") or p.get("atom") or "")
                key = (aid, atom)
                if key in seen_patches:
                    continue
                seen_patches.add(key)
                accepted = bool(p.get("accepted_by_patch_audit"))
                holdout_ok = bool(p.get("holdout_patch_audit_pass")) if "holdout_patch_audit_pass" in p else None
                if accepted and holdout_ok:
                    status = "paid_carrier_patch_witness"
                    reason = "carrier_patch_audited_and_holdout_passed"
                elif accepted:
                    status = "carrier_patch_witness"
                    reason = "carrier_patch_audited_without_required_holdout"
                else:
                    status = "open_carrier_patch_candidate"
                    reason = "carrier_patch_unaccepted_or_raw"
                rows.append({
                    "kind": "carrier_incidence_patch",
                    "round": ri,
                    "source": source,
                    "action_id": aid,
                    "carrier_atom": atom,
                    "poms_status": status,
                    "canonical_status": "not_canonical_carrier_patch_witness_only",
                    "reason": reason,
                    "observed_mean_delta": p.get("observed_mean_delta"),
                    "holdout_observed_mean_delta": p.get("holdout_observed_mean_delta"),
                    "parent_nonpaid": False,
                    "dual_certificate": False,
                    "least_repair": False,
                    "patch": p,
                })

    by_status: dict[str, int] = {}
    by_kind: dict[str, int] = {}
    for r in rows:
        by_status[str(r.get("poms_status"))] = by_status.get(str(r.get("poms_status")), 0) + 1
        by_kind[str(r.get("kind"))] = by_kind.get(str(r.get("kind")), 0) + 1
    summary = {
        "run_dir": str(root),
        "canonical_status": "poms_status_chart_only_no_canonical_promotion",
        "n_records": len(rows),
        "by_status": by_status,
        "by_kind": by_kind,
        "promotion_rule": "canonical_only_if_parent_nonpaid_and_dual_certificate_and_least_repair",
        "settings": {"min_realized_goal_response": min_realized_goal_response, "require_realized_success": require_realized_success},
    }
    rep = {"summary": summary, "rows": rows}
    if out_json:
        p = Path(out_json); p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")
    if out_jsonl:
        write_jsonl(out_jsonl, rows)
    if out_csv:
        p = Path(out_csv); p.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = ["kind", "round", "source", "action_id", "tactic", "carrier_atom", "poms_status", "reason", "canonical_status", "n_realized_rows", "observed_mean_delta", "holdout_observed_mean_delta"]
        with p.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for r in rows:
                w.writerow({k: r.get(k) for k in fieldnames})
    return rep


__all__ = ["collect_poms_status"]
