from __future__ import annotations

from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Iterable
import csv
import json
import math
import re

import numpy as np

from .schemas import read_jsonl, write_jsonl, stable_hash, TacticAction

SCHEMA_VERSION = "lean-rgc-arithmetic-teacher-v41.0"


@dataclass
class ArithmeticIdentity:
    identity_id: str
    kind: str
    name: str
    lhs_pattern: str
    rhs_pattern: str
    domain: str = "arith"
    theorem_names: list[str] = field(default_factory=list)
    direction_modes: list[str] = field(default_factory=lambda: ["forward", "backward"])
    teacher_role: str = "structure_preserving_goal_state_transform"
    canonical_status: str = "arithmetic_teacher_constraint_not_canonical"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def default_arithmetic_identities() -> list[ArithmeticIdentity]:
    """Small conservative seed set.

    These are *teacher constraints*, not canonical facts.  The theorem names are
    intentionally best-effort aliases used only for candidate tactics when a Lean
    environment provides the corresponding lemma.
    """
    return [
        ArithmeticIdentity("add_zero_right", "identity", "x + 0 = x", "x + 0", "x", "additive", ["Nat.add_zero", "add_zero"], ["simplify"]),
        ArithmeticIdentity("zero_add_left", "identity", "0 + x = x", "0 + x", "x", "additive", ["Nat.zero_add", "zero_add"], ["simplify"]),
        ArithmeticIdentity("mul_one_right", "identity", "x * 1 = x", "x * 1", "x", "multiplicative", ["Nat.mul_one", "mul_one"], ["simplify"]),
        ArithmeticIdentity("one_mul_left", "identity", "1 * x = x", "1 * x", "x", "multiplicative", ["Nat.one_mul", "one_mul"], ["simplify"]),
        ArithmeticIdentity("add_assoc", "associativity", "(x + y) + z = x + (y + z)", "(x + y) + z", "x + (y + z)", "additive", ["Nat.add_assoc", "add_assoc"], ["forward", "backward"]),
        ArithmeticIdentity("mul_assoc", "associativity", "(x * y) * z = x * (y * z)", "(x * y) * z", "x * (y * z)", "multiplicative", ["Nat.mul_assoc", "mul_assoc"], ["forward", "backward"]),
        ArithmeticIdentity("left_distrib", "distributivity", "x * (y + z) = x*y + x*z", "x * (y + z)", "x*y + x*z", "semiring", ["Nat.left_distrib", "left_distrib", "mul_add"], ["expand", "factor"]),
        ArithmeticIdentity("right_distrib", "distributivity", "(x + y) * z = x*z + y*z", "(x + y) * z", "x*z + y*z", "semiring", ["Nat.right_distrib", "right_distrib", "add_mul"], ["expand", "factor"]),
        ArithmeticIdentity("add_comm", "commutativity", "x + y = y + x", "x + y", "y + x", "additive", ["Nat.add_comm", "add_comm"], ["swap"]),
        ArithmeticIdentity("mul_comm", "commutativity", "x * y = y * x", "x * y", "y * x", "multiplicative", ["Nat.mul_comm", "mul_comm"], ["swap"]),
        ArithmeticIdentity("division_carrier", "division_invariant", "n = q*d + r", "q*d + r", "n", "division", ["Nat.mod_add_div", "Nat.div_add_mod"], ["carrier"]),
    ]


def _read_json(path: str | Path | None) -> Any:
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def _write_json(path: str | Path, obj: Any) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def _load_identities(path: str | Path | None = None) -> list[dict[str, Any]]:
    if path and Path(path).exists():
        if str(path).endswith(".jsonl"):
            rows = read_jsonl(path)
        else:
            obj = _read_json(path)
            rows = obj.get("identities", obj) if isinstance(obj, dict) else obj
        out: list[dict[str, Any]] = []
        for r in rows or []:
            if isinstance(r, ArithmeticIdentity):
                out.append(r.to_dict())
            elif isinstance(r, dict):
                d = dict(r)
                d.setdefault("canonical_status", "arithmetic_teacher_constraint_not_canonical")
                out.append(d)
        return out
    return [x.to_dict() for x in default_arithmetic_identities()]


def _goal_rows_from_structured_state(row: dict[str, Any]) -> list[dict[str, Any]]:
    goals = row.get("goals") or []
    out = []
    for i, g in enumerate(goals):
        if not isinstance(g, dict):
            continue
        target = str(g.get("target_text") or g.get("pretty") or g.get("text") or "")
        out.append({
            "goal_index": i,
            "goal_id": str(g.get("goal_id") or g.get("mvar_id") or f"g{i}"),
            "mvar_id": str(g.get("mvar_id") or ""),
            "target_text": target,
            "target_head": str(g.get("target_head") or g.get("head") or ""),
            "domain_tags": list(g.get("domain_tags") or []),
            "carrier_atoms": list(g.get("carrier_atoms") or g.get("carrier_atoms_readout") or []),
            "local_deps": list(g.get("local_deps") or []),
            "expr_json": g.get("expr_json") or {},
            "kernel_hash": str(g.get("kernel_hash") or ""),
        })
    return out


def _mvar_measure(state: dict[str, Any]) -> dict[str, float]:
    mv = state.get("metavars") or {}
    goals = state.get("goals") or []
    if not isinstance(mv, dict):
        mv = {}
    entries = mv.get("entries") or []
    open_mvars = float(len(mv.get("metavariables") or []) or mv.get("unsolved_goal_count") or len(goals))
    synthetic = float(mv.get("synthetic_mvar_count") or 0)
    typeclasses = state.get("typeclasses") or {}
    n_tc = float((typeclasses or {}).get("n_obligations") or len((typeclasses or {}).get("obligations") or [])) if isinstance(typeclasses, dict) else 0.0
    # A cheap depth chart from explicit edges if present.
    edges = mv.get("edges") or []
    depth = 0.0
    if isinstance(edges, list) and edges:
        depth = min(8.0, float(len(edges)))
    measure = open_mvars + 0.5 * synthetic + 0.75 * n_tc + 0.1 * depth
    return {"open_mvars": open_mvars, "synthetic_mvars": synthetic, "typeclass_obligations": n_tc, "edge_depth_proxy": depth, "measure": float(measure)}


def _contains_arith(target: str, tags: Iterable[str] = ()) -> bool:
    t = target or ""
    if any(x in t for x in ["+", "*", "-", "≤", "≥", "<", ">", "Nat", "Int", "ℕ", "ℤ"]):
        return True
    return bool(set(tags) & {"Nat", "Int", "Rat", "Real", "Arith"})


def _replace_once(target: str, old: str, new: str) -> str | None:
    if old in target:
        return target.replace(old, new, 1)
    return None


def _apply_identity_text(target: str, identity: dict[str, Any]) -> list[dict[str, Any]]:
    """Return text-chart transformations induced by a seed identity.

    This is deliberately conservative and marked as a chart.  The schema is meant
    to be replaced by a kernel Expr rewrite backend later.
    """
    tid = str(identity.get("identity_id") or identity.get("id") or "identity")
    kind = str(identity.get("kind") or "identity")
    target0 = target or ""
    rows: list[dict[str, Any]] = []

    def add(direction: str, before: str, after: str, rule: str, confidence: float = 0.4):
        if after and after != before:
            rows.append({
                "identity_id": tid,
                "kind": kind,
                "direction": direction,
                "before_target_text": before,
                "after_target_text": after,
                "rewrite_rule": rule,
                "chart_confidence": float(confidence),
            })

    # Direct literal patterns from identity if possible.
    lhs = str(identity.get("lhs_pattern") or "")
    rhs = str(identity.get("rhs_pattern") or "")
    if lhs and rhs:
        out = _replace_once(target0, lhs, rhs)
        if out:
            add("forward", target0, out, f"literal:{lhs}->{rhs}", 0.25)
        out = _replace_once(target0, rhs, lhs)
        if out and "backward" in (identity.get("direction_modes") or ["backward"]):
            add("backward", target0, out, f"literal:{rhs}->{lhs}", 0.20)

    # Regex / arithmetic schemas.
    if tid in {"add_zero_right"}:
        add("simplify", target0, re.sub(r"\b([A-Za-z_][\w']*)\s*\+\s*0\b", r"\1", target0, count=1), "regex:add_zero_right", 0.55)
    elif tid in {"zero_add_left"}:
        add("simplify", target0, re.sub(r"\b0\s*\+\s*([A-Za-z_][\w']*)\b", r"\1", target0, count=1), "regex:zero_add_left", 0.55)
    elif tid in {"mul_one_right"}:
        add("simplify", target0, re.sub(r"\b([A-Za-z_][\w']*)\s*\*\s*1\b", r"\1", target0, count=1), "regex:mul_one_right", 0.55)
    elif tid in {"one_mul_left"}:
        add("simplify", target0, re.sub(r"\b1\s*\*\s*([A-Za-z_][\w']*)\b", r"\1", target0, count=1), "regex:one_mul_left", 0.55)
    elif tid == "left_distrib":
        m = re.search(r"\b([A-Za-z_][\w']*)\s*\*\s*\(\s*([A-Za-z_][\w']*)\s*\+\s*([A-Za-z_][\w']*)\s*\)", target0)
        if m:
            a, b, c = m.groups(); repl = f"{a} * {b} + {a} * {c}"
            add("expand", target0, target0[:m.start()] + repl + target0[m.end():], "regex:left_distrib_expand", 0.75)
        m = re.search(r"\b([A-Za-z_][\w']*)\s*\*\s*([A-Za-z_][\w']*)\s*\+\s*\1\s*\*\s*([A-Za-z_][\w']*)", target0)
        if m:
            a, b, c = m.groups(); repl = f"{a} * ({b} + {c})"
            add("factor", target0, target0[:m.start()] + repl + target0[m.end():], "regex:left_distrib_factor", 0.65)
    elif tid == "right_distrib":
        m = re.search(r"\(\s*([A-Za-z_][\w']*)\s*\+\s*([A-Za-z_][\w']*)\s*\)\s*\*\s*([A-Za-z_][\w']*)", target0)
        if m:
            a, b, c = m.groups(); repl = f"{a} * {c} + {b} * {c}"
            add("expand", target0, target0[:m.start()] + repl + target0[m.end():], "regex:right_distrib_expand", 0.75)
    elif tid == "add_assoc":
        m = re.search(r"\(\s*([A-Za-z_][\w']*)\s*\+\s*([A-Za-z_][\w']*)\s*\)\s*\+\s*([A-Za-z_][\w']*)", target0)
        if m:
            a, b, c = m.groups(); repl = f"{a} + ({b} + {c})"
            add("forward", target0, target0[:m.start()] + repl + target0[m.end():], "regex:add_assoc", 0.65)
    elif tid == "mul_assoc":
        m = re.search(r"\(\s*([A-Za-z_][\w']*)\s*\*\s*([A-Za-z_][\w']*)\s*\)\s*\*\s*([A-Za-z_][\w']*)", target0)
        if m:
            a, b, c = m.groups(); repl = f"{a} * ({b} * {c})"
            add("forward", target0, target0[:m.start()] + repl + target0[m.end():], "regex:mul_assoc", 0.65)
    elif tid == "add_comm":
        m = re.search(r"\b([A-Za-z_][\w']*)\s*\+\s*([A-Za-z_][\w']*)\b", target0)
        if m:
            a, b = m.groups(); add("swap", target0, target0[:m.start()] + f"{b} + {a}" + target0[m.end():], "regex:add_comm", 0.35)
    elif tid == "mul_comm":
        m = re.search(r"\b([A-Za-z_][\w']*)\s*\*\s*([A-Za-z_][\w']*)\b", target0)
        if m:
            a, b = m.groups(); add("swap", target0, target0[:m.start()] + f"{b} * {a}" + target0[m.end():], "regex:mul_comm", 0.35)
    elif tid == "division_carrier":
        if re.search(r"\b[a-zA-Z_][\w']*\s*\*\s*[a-zA-Z_][\w']*\s*\+\s*[a-zA-Z_][\w']*", target0):
            add("carrier", target0, target0, "division_carrier_invariant", 0.30)

    # Remove accidental no-ops from regex substitutions.
    out_rows = []
    seen = set()
    for r in rows:
        if r["after_target_text"] == r["before_target_text"]:
            continue
        key = (r["identity_id"], r["direction"], r["after_target_text"])
        if key in seen:
            continue
        seen.add(key); out_rows.append(r)
    return out_rows


def generate_arithmetic_teacher_graph(
    structured_states_path: str | Path,
    out_dir: str | Path,
    *,
    identities_path: str | Path | None = None,
    actions_path: str | Path | None = None,
    responses_path: str | Path | None = None,
    max_transforms_per_state: int = 32,
    emit_candidate_actions: bool = True,
) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    states = read_jsonl(structured_states_path)
    identities = _load_identities(identities_path)
    write_jsonl(out / "arithmetic_teacher_identities.jsonl", identities)

    transformations: list[dict[str, Any]] = []
    audits: list[dict[str, Any]] = []
    candidate_actions: list[dict[str, Any]] = []

    for st in states:
        sid = str(st.get("state_id") or stable_hash(st))
        tid = str(st.get("task_id") or "")
        m_before = _mvar_measure(st)
        goals = _goal_rows_from_structured_state(st)
        count_for_state = 0
        for g in goals:
            target = g.get("target_text", "")
            if not _contains_arith(target, g.get("domain_tags") or []):
                continue
            for ident in identities:
                if count_for_state >= int(max_transforms_per_state):
                    break
                trs = _apply_identity_text(target, ident)
                for tr in trs:
                    if count_for_state >= int(max_transforms_per_state):
                        break
                    trans_id = "arith_tau_" + stable_hash({"sid": sid, "goal": g.get("goal_id"), "tr": tr})
                    # Chart-level transformed state hash; true Lean state created later by worker/backend.
                    transformed_state_hash = stable_hash({"state": sid, "target": tr["after_target_text"], "identity": tr["identity_id"], "direction": tr["direction"]})
                    row = {
                        "schema_version": SCHEMA_VERSION,
                        "transition_id": trans_id,
                        "identity_id": tr["identity_id"],
                        "identity_kind": tr["kind"],
                        "direction": tr["direction"],
                        "state_id": sid,
                        "task_id": tid,
                        "goal_id": g.get("goal_id"),
                        "mvar_id": g.get("mvar_id"),
                        "before_target_text": tr["before_target_text"],
                        "after_target_text": tr["after_target_text"],
                        "rewrite_rule": tr["rewrite_rule"],
                        "state_transform": {
                            "kind": "target_expr_rewrite_chart",
                            "before_state_id": sid,
                            "after_state_hash": transformed_state_hash,
                            "requires_kernel_rewrite_audit": True,
                        },
                        "mvar_measure_before": m_before,
                        "mvar_effect_proxy": {
                            "measure_delta_pred": 0.0 if tr["direction"] in {"swap", "carrier"} else -0.05,
                            "decomposition_aware": True,
                            "status": "teacher_transform_chart_pending_audit",
                        },
                        "carrier_invariance_claim": {
                            "status": "candidate_teacher_invariance_not_verified",
                            "carrier_atoms_readout": g.get("carrier_atoms") or [],
                        },
                        "response_invariance_claim": {
                            "status": "candidate_teacher_invariance_not_verified",
                            "chart_confidence": tr.get("chart_confidence", 0.0),
                        },
                        "canonical_status": "arithmetic_goal_state_transform_chart_not_canonical",
                    }
                    transformations.append(row)
                    audits.append({
                        "schema_version": SCHEMA_VERSION,
                        "transition_id": trans_id,
                        "identity_id": tr["identity_id"],
                        "state_id": sid,
                        "task_id": tid,
                        "response_invariance_error": None,
                        "carrier_invariance_error": None,
                        "gamma_cocycle_error": None,
                        "mvar_monotonicity_proxy": row["mvar_effect_proxy"],
                        "audit_safe": False,
                        "status": "pending_kernel_transition_audit",
                        "canonical_status": "arithmetic_teacher_audit_witness_not_canonical",
                    })
                    if emit_candidate_actions:
                        theorem_names = []
                        for ident2 in identities:
                            if ident2.get("identity_id") == tr["identity_id"]:
                                theorem_names = list(ident2.get("theorem_names") or [])
                                break
                        tactic = "simp"
                        if theorem_names:
                            th = theorem_names[0]
                            if tr["direction"] in {"expand", "factor", "forward", "backward", "swap"}:
                                tactic = f"rw [{th}]"
                            elif tr["direction"] == "simplify":
                                tactic = f"simp [{th}]"
                            else:
                                tactic = f"simp [{th}]"
                        aid = "arith_teacher_" + stable_hash({"transition_id": trans_id, "tactic": tactic})
                        candidate_actions.append({
                            "action_id": aid,
                            "tactic": tactic,
                            "tactic_class": "arithmetic_teacher",
                            "carrier_tags": ["arithmetic_teacher", "goal_state_transform", str(tr["kind"])],
                            "cost_estimate": 0.8,
                            "metadata": {
                                "source": "arithmetic_teacher_graph_v41",
                                "identity_id": tr["identity_id"],
                                "identity_kind": tr["kind"],
                                "direction": tr["direction"],
                                "parent_transition_id": trans_id,
                                "state_id": sid,
                                "goal_id": g.get("goal_id"),
                                "before_target_text": tr["before_target_text"],
                                "after_target_text": tr["after_target_text"],
                                "canonical_status": "arithmetic_teacher_candidate_action_not_canonical",
                            },
                        })
                    count_for_state += 1

    write_jsonl(out / "arithmetic_teacher_transformations.jsonl", transformations)
    write_jsonl(out / "arithmetic_teacher_audits.jsonl", audits)
    if emit_candidate_actions:
        # Deduplicate by tactic/state/identity.
        seen = set(); dedup = []
        for a in candidate_actions:
            key = (a.get("tactic"), (a.get("metadata") or {}).get("state_id"), (a.get("metadata") or {}).get("identity_id"))
            if key in seen:
                continue
            seen.add(key); dedup.append(a)
        candidate_actions = dedup
        write_jsonl(out / "arithmetic_teacher_actions.jsonl", candidate_actions)

    # If action geometry exists, emit composition constraints from arithmetic metadata too.
    teacher_constraints: list[dict[str, Any]] = []
    if actions_path and Path(actions_path).exists():
        for row in read_jsonl(actions_path):
            meta = row.get("metadata") or {}
            ar = meta.get("arith") or meta.get("arithmetic") or {}
            if ar or "teacher_equiv" in meta:
                teacher_constraints.append({
                    "schema_version": SCHEMA_VERSION,
                    "constraint_id": "arith_teacher_constraint_" + stable_hash(row),
                    "action_id": row.get("action_id") or row.get("id") or row.get("tactic"),
                    "kind": "action_metadata_teacher_constraint",
                    "expr": ar.get("expr") or meta.get("teacher_expr"),
                    "teacher_equiv": meta.get("teacher_equiv") or ar.get("equiv") or [],
                    "canonical_status": "arithmetic_teacher_action_constraint_not_canonical",
                })
    # Also turn each transformation into a self-supervised state transform constraint.
    for tr in transformations:
        teacher_constraints.append({
            "schema_version": SCHEMA_VERSION,
            "constraint_id": "arith_teacher_state_constraint_" + stable_hash(tr),
            "kind": "goal_state_transform_constraint",
            "identity_id": tr.get("identity_id"),
            "transition_id": tr.get("transition_id"),
            "state_id": tr.get("state_id"),
            "constraint_terms": ["response_invariance", "carrier_invariance", "mvar_decomposition", "kernel_rewrite_audit"],
            "canonical_status": "arithmetic_teacher_constraint_not_canonical",
        })
    write_jsonl(out / "arithmetic_teacher_constraints.jsonl", teacher_constraints)

    # Optional response summaries: attach observed response/carrier for matching generated actions if already audited.
    resp_summary = {"n_response_rows": 0, "matched_generated_actions": 0}
    if responses_path and Path(responses_path).exists() and emit_candidate_actions:
        resp_rows = read_jsonl(responses_path)
        resp_summary["n_response_rows"] = len(resp_rows)
        generated_ids = {str(a.get("action_id")) for a in candidate_actions}
        resp_summary["matched_generated_actions"] = sum(1 for r in resp_rows if str(r.get("action_id")) in generated_ids)

    report = {
        "schema_version": SCHEMA_VERSION,
        "n_states": len(states),
        "n_identities": len(identities),
        "n_transformations": len(transformations),
        "n_audits": len(audits),
        "n_candidate_actions": len(candidate_actions) if emit_candidate_actions else 0,
        "n_teacher_constraints": len(teacher_constraints),
        "response_summary": resp_summary,
        "outputs": {
            "identities": str(out / "arithmetic_teacher_identities.jsonl"),
            "transformations": str(out / "arithmetic_teacher_transformations.jsonl"),
            "audits": str(out / "arithmetic_teacher_audits.jsonl"),
            "constraints": str(out / "arithmetic_teacher_constraints.jsonl"),
            "actions": str(out / "arithmetic_teacher_actions.jsonl") if emit_candidate_actions else None,
        },
        "canonical_status": "arithmetic_teacher_graph_chart_not_canonical",
    }
    _write_json(out / "arithmetic_teacher_report.json", report)
    return report


def audit_arithmetic_teacher_transitions(
    transformations_path: str | Path,
    structured_states_path: str | Path,
    out_rows: str | Path,
    *,
    report_out: str | Path | None = None,
) -> dict[str, Any]:
    """Chart-level teacher audit against available structured states.

    If a transformed target already appears as another structured state target, the
    row receives a weak held-out witness.  A real kernel transition audit should
    replace this when a tactic-state backend is available.
    """
    transformations = read_jsonl(transformations_path)
    states = read_jsonl(structured_states_path)
    target_index: dict[str, list[dict[str, Any]]] = {}
    for st in states:
        for g in _goal_rows_from_structured_state(st):
            target_index.setdefault(str(g.get("target_text") or ""), []).append({"state": st, "goal": g})
    rows: list[dict[str, Any]] = []
    for tr in transformations:
        after = str(tr.get("after_target_text") or "")
        matches = target_index.get(after, [])
        verified = bool(matches)
        mb = tr.get("mvar_measure_before") or {}
        # Text chart can only assert zero or pending invariance error if a target match exists.
        row = {
            "schema_version": SCHEMA_VERSION,
            "transition_id": tr.get("transition_id"),
            "identity_id": tr.get("identity_id"),
            "state_id": tr.get("state_id"),
            "matched_state_ids": [m["state"].get("state_id") for m in matches[:8]],
            "heldout_target_match": verified,
            "response_invariance_error": 0.0 if verified else None,
            "carrier_invariance_error": 0.0 if verified else None,
            "mvar_measure_before": mb,
            "mvar_measure_after_chart": _mvar_measure(matches[0]["state"]) if matches else None,
            "audit_safe": verified,
            "status": "text_chart_verified_target_match" if verified else "pending_kernel_transition_audit",
            "canonical_status": "arithmetic_teacher_transition_audit_chart_not_canonical",
        }
        rows.append(row)
    write_jsonl(out_rows, rows)
    report = {
        "schema_version": SCHEMA_VERSION,
        "n_transformations": len(transformations),
        "n_verified_target_matches": sum(1 for r in rows if r.get("heldout_target_match")),
        "verification_rate": (sum(1 for r in rows if r.get("heldout_target_match")) / len(rows)) if rows else 0.0,
        "canonical_status": "arithmetic_teacher_transition_audit_report_not_canonical",
    }
    if report_out:
        _write_json(report_out, report)
    return report


__all__ = [
    "ArithmeticIdentity",
    "default_arithmetic_identities",
    "generate_arithmetic_teacher_graph",
    "audit_arithmetic_teacher_transitions",
]
