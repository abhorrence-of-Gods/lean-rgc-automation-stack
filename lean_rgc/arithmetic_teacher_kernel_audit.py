from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import math

from .schemas import LeanTask, ProofState, TacticAction, read_jsonl, write_jsonl, stable_hash
from .defects import ProofDefectExtractor
from .lean.server import LeanServerAdapter, LeanServerConfig
from .lean.structured_state import extract_structured_state
from .arithmetic_teacher import default_arithmetic_identities

SCHEMA_VERSION = "lean-rgc-arithmetic-teacher-kernel-audit-v42.0"


def _write_json(path: str | Path, obj: Any) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        v = float(x)
        if math.isnan(v) or math.isinf(v):
            return default
        return v
    except Exception:
        return default


def _load_identities(path: str | Path | None = None) -> dict[str, dict[str, Any]]:
    rows: list[dict[str, Any]]
    if path and Path(path).exists():
        p = Path(path)
        if p.suffix == ".jsonl":
            rows = read_jsonl(p)
        else:
            obj = json.loads(p.read_text(encoding="utf-8"))
            rows = obj.get("identities", obj) if isinstance(obj, dict) else obj
    else:
        rows = [x.to_dict() for x in default_arithmetic_identities()]
    out: dict[str, dict[str, Any]] = {}
    for r in rows or []:
        if isinstance(r, dict):
            iid = str(r.get("identity_id") or r.get("id") or r.get("name") or "")
            if iid:
                out[iid] = dict(r)
    return out


def _action_for_transformation(tr: dict[str, Any], identities: dict[str, dict[str, Any]]) -> dict[str, Any]:
    iid = str(tr.get("identity_id") or "arith_identity")
    ident = identities.get(iid, {})
    theorem_names = list(ident.get("theorem_names") or [])
    direction = str(tr.get("direction") or "forward")
    th = theorem_names[0] if theorem_names else None
    if th:
        if direction in {"simplify", "carrier"}:
            tactic = f"simp [{th}]"
        elif direction in {"backward", "factor"}:
            tactic = f"rw [← {th}]"
        elif direction in {"swap"}:
            tactic = f"rw [{th}]"
        else:
            tactic = f"rw [{th}]"
    else:
        tactic = "simp"
    tid = str(tr.get("transition_id") or stable_hash(tr))
    aid = "arith_kernel_" + stable_hash({"transition_id": tid, "tactic": tactic}, n=16)
    return {
        "action_id": aid,
        "tactic": tactic,
        "tactic_class": "arithmetic_teacher_kernel_transition",
        "carrier_tags": ["arithmetic_teacher", "kernel_transition", str(tr.get("identity_kind") or tr.get("kind") or "arith")],
        "cost_estimate": 1.0,
        "metadata": {
            "source": "arithmetic_teacher_kernel_audit_v42",
            "parent_transition_id": tid,
            "identity_id": iid,
            "identity_kind": tr.get("identity_kind") or tr.get("kind"),
            "direction": direction,
            "state_id": tr.get("state_id"),
            "task_id": tr.get("task_id"),
            "goal_id": tr.get("goal_id"),
            "before_target_text": tr.get("before_target_text"),
            "expected_after_target_text": tr.get("after_target_text"),
            "canonical_status": "arithmetic_teacher_kernel_action_chart_not_canonical",
        },
    }


def _mvar_measure_from_structured_state(st: dict[str, Any] | None) -> dict[str, float]:
    if not isinstance(st, dict):
        return {"open_mvars": 0.0, "synthetic_mvars": 0.0, "typeclass_obligations": 0.0, "edge_depth_proxy": 0.0, "measure": 0.0}
    goals = st.get("goals") or []
    mv = st.get("metavars") or {}
    if not isinstance(mv, dict):
        mv = {}
    tc = st.get("typeclasses") or {}
    if not isinstance(tc, dict):
        tc = {}
    open_mvars = _safe_float(mv.get("unsolved_goal_count"), float(len(goals)))
    if open_mvars <= 0 and goals:
        open_mvars = float(len(goals))
    synthetic = _safe_float(mv.get("synthetic_mvar_count"), 0.0)
    n_tc = _safe_float(tc.get("n_obligations"), float(len(tc.get("obligations") or [])))
    edges = mv.get("edges") or []
    depth = min(8.0, float(len(edges))) if isinstance(edges, list) else 0.0
    measure = open_mvars + 0.5 * synthetic + 0.75 * n_tc + 0.1 * depth
    return {"open_mvars": open_mvars, "synthetic_mvars": synthetic, "typeclass_obligations": n_tc, "edge_depth_proxy": depth, "measure": float(measure)}


def _goal_targets(st: dict[str, Any] | None) -> list[str]:
    out: list[str] = []
    if not isinstance(st, dict):
        return out
    for g in st.get("goals") or []:
        if isinstance(g, dict):
            txt = str(g.get("target_text") or g.get("pretty") or g.get("text") or "")
            if txt:
                out.append(txt)
    return out


def _norm_dict(d: dict[str, Any] | None) -> float:
    if not isinstance(d, dict):
        return 0.0
    return math.sqrt(sum(_safe_float(v) ** 2 for v in d.values()))


def audit_arithmetic_teacher_kernel_transitions(
    transformations_path: str | Path,
    tasks_path: str | Path,
    out_dir: str | Path,
    *,
    identities_path: str | Path | None = None,
    structured_states_path: str | Path | None = None,
    server_config: LeanServerConfig | None = None,
    max_transitions: int | None = None,
) -> dict[str, Any]:
    """Audit arithmetic teacher transformations through the Lean server adapter.

    This v42 audit turns each transformation tau_I into a concrete proof action and
    measures the resulting goal-state transition via the available server backend.
    With a true kernel worker, audit flags carry kernel_state payloads; with dry-run
    or file fallback this remains a source-check/chart audit.  In all cases the
    output rows are finite transition witnesses, not canonical objects.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    transformations = read_jsonl(transformations_path)
    if max_transitions is not None:
        transformations = transformations[: int(max_transitions)]
    tasks = [LeanTask.from_dict(x) for x in read_jsonl(tasks_path)]
    task_by_id = {t.task_id: t for t in tasks}
    identities = _load_identities(identities_path)
    extractor = ProofDefectExtractor()

    state_chart_by_id: dict[str, dict[str, Any]] = {}
    if structured_states_path and Path(structured_states_path).exists():
        for st in read_jsonl(structured_states_path):
            sid = str(st.get("state_id") or "")
            if sid:
                state_chart_by_id.setdefault(sid, st)

    actions: list[dict[str, Any]] = []
    audit_records: list[dict[str, Any]] = []
    response_rows: list[dict[str, Any]] = []
    structured_rows: list[dict[str, Any]] = []
    kernel_rows: list[dict[str, Any]] = []
    transition_rows: list[dict[str, Any]] = []

    server_config = server_config or LeanServerConfig(dry_run=True, backend="dry_run")
    with LeanServerAdapter(server_config) as server:
        load_report = server.load_project()
        for tr in transformations:
            tid = str(tr.get("transition_id") or stable_hash(tr))
            task_id = str(tr.get("task_id") or "")
            task = task_by_id.get(task_id)
            if task is None and tasks:
                # Fall back for hand-authored transformations without task_id.
                task = tasks[0]
            action_dict = _action_for_transformation(tr, identities)
            actions.append(action_dict)
            action = TacticAction.from_dict(action_dict)
            if task is None:
                transition_rows.append({
                    "schema_version": SCHEMA_VERSION,
                    "transition_id": tid,
                    "identity_id": tr.get("identity_id"),
                    "status": "missing_task_for_kernel_audit",
                    "kernel_transition_verified": False,
                    "canonical_status": "arithmetic_teacher_kernel_transition_audit_not_canonical",
                })
                continue
            state_id = str(tr.get("state_id") or stable_hash({"task": task.task_id, "target": tr.get("before_target_text")}))
            state = ProofState(
                state_id=state_id,
                task_id=task.task_id,
                target=str(tr.get("before_target_text") or task.statement),
                goals_text="⊢ " + str(tr.get("before_target_text") or task.statement),
                raw_messages=[],
            )
            before_defect = extractor.extract(state)
            rec = server.apply_tactic(task, action, state)
            after_state = rec.after_state or state
            after_defect = extractor.extract(after_state, rec)
            resp, resp_flat, resp_keys = extractor.response(before_defect, after_defect)
            rec.defect_before = before_defect.to_dict()
            rec.defect_after = after_defect.to_dict()
            rec.response = resp
            rec.carrier_delta = {k: before_defect.carrier.get(k, 0.0) - after_defect.carrier.get(k, 0.0) for k in sorted(set(before_defect.carrier) | set(after_defect.carrier))}
            rec.audit_flags = dict(rec.audit_flags or {})
            rec.audit_flags.update({
                "arithmetic_teacher_kernel_audit": True,
                "parent_transition_id": tid,
                "identity_id": tr.get("identity_id"),
                "expected_after_target_text": tr.get("after_target_text"),
                "canonical_status": "arithmetic_teacher_kernel_audit_chart_not_canonical",
            })
            audit_dict = rec.to_dict()
            audit_dict["action"] = action.to_dict()
            audit_dict["task_id"] = task.task_id
            audit_dict["target"] = task.statement
            audit_records.append(audit_dict)
            response_rows.append({
                "state_id": state.state_id,
                "task_id": task.task_id,
                "action_id": action.action_id,
                "target": task.statement,
                "action": action.to_dict(),
                "response": resp,
                "response_flat": resp_flat,
                "response_keys": resp_keys,
                "defect_before": before_defect.to_dict(),
                "defect_after": after_defect.to_dict(),
                "audit_status": rec.status,
                "carrier_delta": rec.carrier_delta,
                "audit_flags": dict(rec.audit_flags or {}),
            })
            try:
                st_after = server.structured_state(task, after_state, rec)
            except Exception:
                st_after = extract_structured_state(task=task, state=after_state, audit=rec, backend="arithmetic_teacher_kernel_audit_fallback").to_dict()
            structured_rows.append(st_after)
            kernel_state = (rec.audit_flags or {}).get("kernel_state")
            if isinstance(kernel_state, dict):
                kr = dict(kernel_state)
                kr["transition_id"] = tid
                kr["action_id"] = action.action_id
                kernel_rows.append(kr)

            expected = str(tr.get("after_target_text") or "")
            after_targets = _goal_targets(st_after)
            expected_match = bool(expected and expected in after_targets)
            closed = rec.status == "success" or len(after_targets) == 0
            verified = bool(closed or expected_match)
            before_measure = tr.get("mvar_measure_before") or _mvar_measure_from_structured_state(state_chart_by_id.get(state_id))
            after_measure = _mvar_measure_from_structured_state(st_after)
            row = {
                "schema_version": SCHEMA_VERSION,
                "transition_id": tid,
                "identity_id": tr.get("identity_id"),
                "identity_kind": tr.get("identity_kind"),
                "direction": tr.get("direction"),
                "task_id": task.task_id,
                "state_id": state.state_id,
                "action_id": action.action_id,
                "tactic": action.tactic,
                "audit_status": rec.status,
                "expected_after_target_text": expected,
                "after_targets": after_targets[:8],
                "expected_target_match": expected_match,
                "goal_closed": closed,
                "kernel_transition_verified": verified,
                "kernel_state_hash": (rec.audit_flags or {}).get("kernel_state_hash"),
                "structured_state_backend": (rec.audit_flags or {}).get("structured_state_backend") or st_after.get("extraction_backend"),
                "mvar_measure_before": before_measure,
                "mvar_measure_after": after_measure,
                "mvar_response": _safe_float((before_measure or {}).get("measure")) - _safe_float((after_measure or {}).get("measure")),
                "response_norm": _norm_dict(resp),
                "carrier_response_norm": _norm_dict(rec.carrier_delta),
                "response": resp,
                "carrier_delta": rec.carrier_delta,
                "response_invariance_error": 0.0 if expected_match else None,
                "carrier_invariance_error": None,
                "audit_safe": verified and rec.status in {"success", "partial", "dry_run"},
                "status": "kernel_closed_goal" if closed else ("kernel_expected_target_match" if expected_match else "kernel_transition_open"),
                "canonical_status": "arithmetic_teacher_kernel_transition_audit_witness_not_canonical",
            }
            transition_rows.append(row)

    write_jsonl(out / "arithmetic_teacher_kernel_actions.jsonl", actions)
    write_jsonl(out / "arithmetic_teacher_kernel_micro_audit.jsonl", audit_records)
    write_jsonl(out / "arithmetic_teacher_kernel_responses.jsonl", response_rows)
    write_jsonl(out / "arithmetic_teacher_kernel_structured_states.jsonl", structured_rows)
    if kernel_rows:
        write_jsonl(out / "arithmetic_teacher_kernel_states.jsonl", kernel_rows)
    write_jsonl(out / "arithmetic_teacher_kernel_audit_rows.jsonl", transition_rows)
    verified_n = sum(1 for r in transition_rows if r.get("kernel_transition_verified"))
    closed_n = sum(1 for r in transition_rows if r.get("goal_closed"))
    report = {
        "schema_version": SCHEMA_VERSION,
        "n_transformations": len(transformations),
        "n_actions": len(actions),
        "n_audits": len(audit_records),
        "n_verified_transitions": verified_n,
        "n_closed_goals": closed_n,
        "verification_rate": verified_n / len(transition_rows) if transition_rows else 0.0,
        "server_backend": server_config.backend,
        "native_exec_mode": getattr(server_config, "native_exec_mode", None),
        "load_report": load_report,
        "outputs": {
            "actions": str(out / "arithmetic_teacher_kernel_actions.jsonl"),
            "micro_audit": str(out / "arithmetic_teacher_kernel_micro_audit.jsonl"),
            "responses": str(out / "arithmetic_teacher_kernel_responses.jsonl"),
            "structured_states": str(out / "arithmetic_teacher_kernel_structured_states.jsonl"),
            "kernel_states": str(out / "arithmetic_teacher_kernel_states.jsonl") if kernel_rows else None,
            "audit_rows": str(out / "arithmetic_teacher_kernel_audit_rows.jsonl"),
        },
        "canonical_status": "arithmetic_teacher_kernel_transition_audit_report_not_canonical",
    }
    _write_json(out / "arithmetic_teacher_kernel_audit_report.json", report)
    return report


__all__ = [
    "audit_arithmetic_teacher_kernel_transitions",
]
