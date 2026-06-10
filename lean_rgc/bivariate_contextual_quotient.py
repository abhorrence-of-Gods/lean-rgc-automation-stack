from __future__ import annotations

from collections import defaultdict, deque
from pathlib import Path
from typing import Any
import json

from .contextual_congruence import IDENTITY_CONTEXT_ID
from .premise_contextual_quotient import (
    _action_id,
    _baseline_action,
    _contextual_premise_action,
    _instantiation,
    _json_dump,
    _load_actions,
)
from .premise_response import extract_premise_name, infer_use_mode, premise_use_id
from .schemas import read_jsonl, stable_hash, write_jsonl


SCHEMA_PREMISE_USE_ROW = "lean-rgc-premise-use-row-v51.0"
SCHEMA_SEPARATOR_CONTEXT = "lean-rgc-separator-context-v51.0"
SCHEMA_BIVARIATE_CANDIDATES = "lean-rgc-bivariate-contextual-candidates-v51.0"
SCHEMA_BIVARIATE_SCHEDULE = "lean-rgc-bivariate-contextual-schedule-v51.0"
SCHEMA_REPAIR_FACE_LEDGER = "lean-rgc-repair-face-ledger-v51.0"


def _metadata(row: dict[str, Any]) -> dict[str, Any]:
    return row.get("metadata") if isinstance(row.get("metadata"), dict) else {}


def _role(row: dict[str, Any]) -> str:
    meta = _metadata(row)
    return str(row.get("role") or meta.get("role") or "")


def _is_separator_context(row: dict[str, Any]) -> bool:
    meta = _metadata(row)
    if _role(row) == "separator_context":
        return True
    if row.get("context_kind") or meta.get("context_kind") or row.get("position_allowed") or meta.get("position_allowed"):
        return True
    aid = str(row.get("action_id") or row.get("id") or "")
    return aid.startswith("ctx_") or aid == IDENTITY_CONTEXT_ID


def _premise_action_from_row(row: dict[str, Any]) -> dict[str, Any]:
    meta = dict(_metadata(row))
    source_action = meta.get("source_action") if isinstance(meta.get("source_action"), dict) else {}
    source_meta = source_action.get("metadata") if isinstance(source_action.get("metadata"), dict) else {}
    task_id = row.get("task_id") or meta.get("task_id") or source_action.get("task_id") or source_meta.get("task_id")
    uid = str(row.get("premise_use_row_id") or row.get("premise_use_id") or meta.get("premise_use_id") or premise_use_id(row))
    premise_id = str(row.get("premise_id") or meta.get("premise_id") or extract_premise_name(row))
    tactic = str(row.get("tactic") or "")
    use_mode = str(row.get("use_mode") or meta.get("use_mode") or row.get("tactic_class") or infer_use_mode(tactic))
    inst = row.get("instantiation_chart") if isinstance(row.get("instantiation_chart"), dict) else meta.get("instantiation")
    if not isinstance(inst, dict):
        inst = _instantiation(row)
    action = {
        "action_id": str(row.get("source_action_id") or row.get("action_id") or uid),
        "tactic": tactic,
        "tactic_class": str(row.get("tactic_class") or use_mode),
        "carrier_tags": list(row.get("carrier_tags") or []),
        "cost_estimate": float(row.get("cost_estimate") or 1.0),
        "metadata": {
            **meta,
            "source": "premise_use_row_v51",
            **({"task_id": str(task_id)} if task_id else {}),
            "premise_use_id": uid,
            "premise_id": premise_id,
            "use_mode": use_mode,
            "instantiation": inst,
            "premise_use_row_id": uid,
        },
    }
    if task_id:
        action["task_id"] = str(task_id)
    return action


def _action_chart(row: dict[str, Any]) -> dict[str, Any]:
    meta = dict(_metadata(row))
    out = {
        "action_id": str(row.get("action_id") or row.get("id") or stable_hash(row, 10)),
        "tactic": str(row.get("tactic") or ""),
        "tactic_class": str(row.get("tactic_class") or row.get("class") or row.get("context_kind") or "unknown"),
        "carrier_tags": list(row.get("carrier_tags") or []),
        "cost_estimate": float(row.get("cost_estimate") or 0.0),
        "metadata": meta,
    }
    for key in ["context_id", "context_kind", "position_allowed", "coverage_tags", "premise_id", "use_mode"]:
        if key in row:
            out[key] = row.get(key)
    return out


def build_premise_use_rows(
    actions_path: str | Path,
    out: str | Path,
    *,
    summary_out: str | Path | None = None,
    max_rows: int | None = None,
    include_context_actions: bool = False,
) -> dict[str, Any]:
    """Build the row universe U_t from candidate actions.

    This is intentionally a chart-level extractor.  It separates premise-use
    rows from separator contexts and records the missing kernel-normal fields in
    ``premise_use_nf`` so later kernel RPC passes can fill them.
    """

    rows: list[dict[str, Any]] = []
    skipped_context = 0
    seen: set[str] = set()
    for action in _load_actions(actions_path):
        if not include_context_actions and _is_separator_context(action):
            skipped_context += 1
            continue
        tactic = str(action.get("tactic") or "")
        if not tactic.strip():
            continue
        meta = _metadata(action)
        uid = str(meta.get("premise_use_id") or premise_use_id(action))
        if uid in seen:
            continue
        seen.add(uid)
        premise_id = str(meta.get("premise_id") or extract_premise_name(action))
        use_mode = str(meta.get("use_mode") or action.get("tactic_class") or infer_use_mode(tactic))
        source_meta = action.get("metadata") if isinstance(action.get("metadata"), dict) else {}
        task_id = action.get("task_id") or source_meta.get("task_id")
        row = {
            "schema_version": SCHEMA_PREMISE_USE_ROW,
            "premise_use_row_id": uid,
            "premise_use_id": uid,
            "source_action_id": str(action.get("action_id")),
            "premise_id": premise_id,
            "use_mode": use_mode,
            "tactic": tactic,
            "tactic_class": str(action.get("tactic_class") or use_mode),
            "instantiation_chart": _instantiation(action),
            "premise_use_nf": {
                "nf_status": "textual_stub",
                "elaborated_expr_hash": None,
                "implicit_args_hash": None,
                "typeclass_instances_hash": None,
                "coercions_hash": None,
                "universe_levels_hash": None,
                "local_context_deps_hash": None,
            },
            "carrier_tags": list(action.get("carrier_tags") or []),
            "cost_estimate": float(action.get("cost_estimate") or 1.0),
            "metadata": {
                "source": "premise_use_row_extractor_v51",
                "source_action": action,
                "role": "premise_use_row",
                **({"task_id": str(task_id)} if task_id else {}),
            },
            "canonical_status": "premise_use_row_chart_not_canonical",
        }
        if task_id:
            row["task_id"] = str(task_id)
        rows.append(row)
        if max_rows is not None and len(rows) >= int(max_rows):
            break
    write_jsonl(out, rows)
    summary = {
        "schema_version": SCHEMA_PREMISE_USE_ROW,
        "actions": str(actions_path),
        "out": str(out),
        "n_rows": len(rows),
        "n_unique_premise_ids": len({str(r.get("premise_id")) for r in rows}),
        "n_unique_use_modes": len({str(r.get("use_mode")) for r in rows}),
        "skipped_context_actions": skipped_context,
        "row_degenerate": len(rows) < 2,
        "canonical_status": "premise_use_row_universe_chart_not_canonical",
    }
    if summary_out:
        _json_dump(summary, summary_out)
    return summary


BUILTIN_SEPARATOR_CONTEXTS: list[dict[str, Any]] = [
    {"action_id": IDENTITY_CONTEXT_ID, "tactic": "skip", "context_kind": "identity", "position_allowed": ["pre", "post"], "coverage_tags": [], "cost_estimate": 0.0},
    {"action_id": "ctx_intro", "tactic": "intro", "context_kind": "intro", "position_allowed": ["pre"], "coverage_tags": ["unintroduced_forall", "unintroduced_imp"], "cost_estimate": 0.25},
    {"action_id": "ctx_intros", "tactic": "intros", "context_kind": "intro", "position_allowed": ["pre"], "coverage_tags": ["unintroduced_forall", "unintroduced_imp"], "cost_estimate": 0.25},
    {"action_id": "ctx_constructor", "tactic": "constructor", "context_kind": "constructor", "position_allowed": ["pre"], "coverage_tags": ["unsplit_and_target", "constructor_branch_debt"], "cost_estimate": 0.25},
    {"action_id": "ctx_simp_pre", "tactic": "simp", "context_kind": "simp", "position_allowed": ["pre"], "coverage_tags": ["missing_simp_lemma", "list_simp_goal"], "cost_estimate": 0.25},
    {"action_id": "ctx_assumption", "tactic": "assumption", "context_kind": "close_by_hyp", "position_allowed": ["post"], "coverage_tags": ["missing_premise_family"], "cost_estimate": 0.25},
    {"action_id": "ctx_rfl", "tactic": "rfl", "context_kind": "reflexive_close", "position_allowed": ["post"], "coverage_tags": ["eq_reflexive_goal"], "cost_estimate": 0.25},
    {"action_id": "ctx_exact_rfl", "tactic": "exact rfl", "context_kind": "reflexive_close", "position_allowed": ["post"], "coverage_tags": ["eq_reflexive_goal"], "cost_estimate": 0.25},
    {"action_id": "ctx_simp", "tactic": "simp", "context_kind": "simp", "position_allowed": ["post"], "coverage_tags": ["missing_simp_lemma", "list_simp_goal"], "cost_estimate": 0.25},
    {"action_id": "ctx_simp_all", "tactic": "simp_all", "context_kind": "simp_all", "position_allowed": ["post"], "coverage_tags": ["missing_simp_lemma", "missing_premise_family"], "cost_estimate": 0.35},
    {"action_id": "ctx_constructor_assumption", "tactic": "constructor <;> assumption", "context_kind": "constructor_close", "position_allowed": ["post"], "coverage_tags": ["unsplit_and_target", "constructor_branch_debt"], "cost_estimate": 0.5},
    {"action_id": "ctx_norm_num", "tactic": "norm_num", "context_kind": "arith", "position_allowed": ["post"], "coverage_tags": ["nat_arith_goal"], "cost_estimate": 0.5},
    {"action_id": "ctx_decide", "tactic": "decide", "context_kind": "decidable_close", "position_allowed": ["post"], "coverage_tags": ["decidable_goal"], "cost_estimate": 0.5},
]


def _normalize_context(row: dict[str, Any]) -> dict[str, Any]:
    meta = dict(_metadata(row))
    pos = row.get("position_allowed") or meta.get("position_allowed") or ["pre", "post"]
    if isinstance(pos, str):
        pos = [pos]
    tags = row.get("coverage_tags") or meta.get("coverage_tags") or row.get("carrier_tags") or []
    if isinstance(tags, str):
        tags = [tags]
    kind = str(row.get("context_kind") or meta.get("context_kind") or row.get("tactic_class") or "unknown")
    aid = str(row.get("action_id") or row.get("id") or "ctx_" + stable_hash(row, 10))
    out = {
        "schema_version": SCHEMA_SEPARATOR_CONTEXT,
        "action_id": aid,
        "context_id": aid,
        "tactic": str(row.get("tactic") or ""),
        "tactic_class": str(row.get("tactic_class") or kind),
        "context_kind": kind,
        "position_allowed": [str(x) for x in pos],
        "coverage_tags": [str(x) for x in tags],
        "carrier_tags": [str(x) for x in tags],
        "cost_estimate": float(row.get("cost_estimate") or 0.25),
        "metadata": {
            **meta,
            "role": "separator_context",
            "context_kind": kind,
            "position_allowed": [str(x) for x in pos],
            "coverage_tags": [str(x) for x in tags],
        },
        "canonical_status": "separator_context_chart_not_canonical",
    }
    return out


def write_separator_contexts(
    out: str | Path,
    *,
    templates: str = "builtin_core",
    summary_out: str | Path | None = None,
) -> dict[str, Any]:
    if templates not in {"builtin_core", "core"}:
        raise ValueError(f"unknown separator context template set: {templates}")
    rows = [_normalize_context(r) for r in BUILTIN_SEPARATOR_CONTEXTS]
    write_jsonl(out, rows)
    summary = {
        "schema_version": SCHEMA_SEPARATOR_CONTEXT,
        "templates": templates,
        "out": str(out),
        "n_contexts": len(rows),
        "pre_contexts": sum(1 for r in rows if "pre" in r.get("position_allowed", [])),
        "post_contexts": sum(1 for r in rows if "post" in r.get("position_allowed", [])),
        "context_kinds": sorted({str(r.get("context_kind")) for r in rows}),
        "canonical_status": "separator_context_basis_chart_not_canonical",
    }
    if summary_out:
        _json_dump(summary, summary_out)
    return summary


def _load_contexts(path: str | Path) -> list[dict[str, Any]]:
    return [_normalize_context(r) for r in read_jsonl(path) if isinstance(r, dict)]


def _select_separator_contexts(contexts: list[dict[str, Any]], side: str, max_n: int) -> list[dict[str, Any]]:
    eligible = [c for c in contexts if side in c.get("position_allowed", ["pre", "post"])]
    identity = [c for c in eligible if _action_id(c) == IDENTITY_CONTEXT_ID]
    by_kind: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for c in eligible:
        if _action_id(c) == IDENTITY_CONTEXT_ID:
            continue
        by_kind[str(c.get("context_kind") or "unknown")].append(c)

    selected: list[dict[str, Any]] = []
    if identity:
        selected.append(identity[0])

    covered_tags: set[str] = set()
    selected_kinds: set[str] = set()

    def choose_best(*, only_new_kind: bool) -> dict[str, Any] | None:
        best: dict[str, Any] | None = None
        best_score: tuple[float, float, str] | None = None
        for kind, rows in by_kind.items():
            if only_new_kind and kind in selected_kinds:
                continue
            if not rows:
                continue
            rows.sort(key=lambda r: (float(r.get("cost_estimate") or 1.0), str(r.get("action_id"))))
            cand = rows[0]
            tags = {str(t) for t in cand.get("coverage_tags") or []}
            novelty = len(tags - covered_tags)
            score = (-float(novelty), float(cand.get("cost_estimate") or 1.0), kind)
            if best_score is None or score < best_score:
                best = cand
                best_score = score
        return best

    # First cover context kinds, then spend remaining budget on second
    # representatives.  This prevents tiny duplicate bases such as two
    # reflexivity closers from hiding simp_all/arith/decide separators.
    while len(selected) < max_n:
        best = choose_best(only_new_kind=True)
        if best is None:
            break
        selected.append(best)
        selected_kinds.add(str(best.get("context_kind") or "unknown"))
        covered_tags.update(str(t) for t in best.get("coverage_tags") or [])
        by_kind[str(best.get("context_kind") or "unknown")].remove(best)

    while len(selected) < max_n:
        best = choose_best(only_new_kind=False)
        if best is None:
            break
        selected.append(best)
        covered_tags.update(str(t) for t in best.get("coverage_tags") or [])
        by_kind[str(best.get("context_kind") or "unknown")].remove(best)
    return selected[:max_n]


def generate_bivariate_contextual_candidates(
    premise_rows_path: str | Path,
    contexts_path: str | Path,
    out: str | Path,
    *,
    summary_out: str | Path | None = None,
    max_rows: int | None = None,
    max_pre: int = 8,
    max_post: int = 8,
    max_candidates: int | None = None,
    include_baselines: bool = True,
    separator: str = "\n",
) -> dict[str, Any]:
    premise_rows = [r for r in read_jsonl(premise_rows_path) if isinstance(r, dict)]
    if max_rows is not None:
        premise_rows = premise_rows[: int(max_rows)]
    premise_actions = [_premise_action_from_row(r) for r in premise_rows]
    contexts = _load_contexts(contexts_path)
    pre_contexts = _select_separator_contexts(contexts, "pre", int(max_pre))
    post_contexts = _select_separator_contexts(contexts, "post", int(max_post))

    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    baseline_by_pair: dict[str, str] = {}

    if include_baselines:
        for pre in pre_contexts:
            for post in post_contexts:
                row = _baseline_action(pre, post, separator=separator)
                meta = dict(row.get("metadata") or {})
                pair = str(meta.get("context_pair"))
                meta.update({
                    "source": "bivariate_contextual_baseline_v51",
                    "bivariate_contextual": True,
                    "pre_context_action": _action_chart(pre),
                    "post_context_action": _action_chart(post),
                    "premise_core_action": None,
                    "pre_context_kind": pre.get("context_kind"),
                    "post_context_kind": post.get("context_kind"),
                    "pre_position_allowed": pre.get("position_allowed"),
                    "post_position_allowed": post.get("position_allowed"),
                })
                row["metadata"] = meta
                aid = str(row["action_id"])
                baseline_by_pair[pair] = aid
                if aid not in seen:
                    seen.add(aid)
                    rows.append(row)
                    if max_candidates is not None and len(rows) >= int(max_candidates):
                        break

    for action in premise_actions:
        for pre in pre_contexts:
            for post in post_contexts:
                row = _contextual_premise_action(action, pre, post, separator=separator)
                meta = dict(row.get("metadata") or {})
                pair = str(meta.get("context_pair"))
                meta.update({
                    "source": "bivariate_contextual_probe_v51",
                    "bivariate_contextual": True,
                    "premise_use_row_id": meta.get("premise_use_id"),
                    "baseline_action_id": baseline_by_pair.get(pair),
                    "pre_context_action": _action_chart(pre),
                    "post_context_action": _action_chart(post),
                    "pre_context_kind": pre.get("context_kind"),
                    "post_context_kind": post.get("context_kind"),
                    "pre_position_allowed": pre.get("position_allowed"),
                    "post_position_allowed": post.get("position_allowed"),
                })
                row["metadata"] = meta
                aid = str(row["action_id"])
                if aid in seen:
                    continue
                seen.add(aid)
                rows.append(row)
                if max_candidates is not None and len(rows) >= int(max_candidates):
                    write_jsonl(out, rows)
                    summary = _candidate_summary(premise_rows_path, contexts_path, out, rows, premise_actions, pre_contexts, post_contexts, True)
                    if summary_out:
                        _json_dump(summary, summary_out)
                    return summary

    write_jsonl(out, rows)
    summary = _candidate_summary(premise_rows_path, contexts_path, out, rows, premise_actions, pre_contexts, post_contexts, False)
    if summary_out:
        _json_dump(summary, summary_out)
    return summary


def _candidate_summary(
    premise_rows_path: str | Path,
    contexts_path: str | Path,
    out: str | Path,
    rows: list[dict[str, Any]],
    premise_actions: list[dict[str, Any]],
    pre_contexts: list[dict[str, Any]],
    post_contexts: list[dict[str, Any]],
    truncated: bool,
) -> dict[str, Any]:
    n_baselines = sum(1 for r in rows if (_metadata(r)).get("is_contextual_baseline"))
    context_pairs = {
        str((_metadata(r)).get("context_pair"))
        for r in rows
        if (_metadata(r)).get("context_pair")
    }
    return {
        "schema_version": SCHEMA_BIVARIATE_CANDIDATES,
        "premise_rows": str(premise_rows_path),
        "contexts": str(contexts_path),
        "out": str(out),
        "n_actions": len(rows),
        "n_premise_contextual_actions": len(rows) - n_baselines,
        "n_baseline_actions": n_baselines,
        "n_premise_use_rows": len(premise_actions),
        "n_pre_contexts": len(pre_contexts),
        "n_post_contexts": len(post_contexts),
        "n_context_pairs": len(context_pairs),
        "pre_context_ids": [_action_id(c) for c in pre_contexts],
        "post_context_ids": [_action_id(c) for c in post_contexts],
        "row_degenerate": len(premise_actions) < 2,
        "column_degenerate": len(context_pairs) < 2,
        "truncated": bool(truncated),
        "canonical_status": "bivariate_contextual_candidates_are_probe_charts_not_canonical",
    }


def schedule_bivariate_candidates(
    candidates_path: str | Path,
    out: str | Path,
    *,
    budget: int,
    report_out: str | Path | None = None,
    require_baseline_pairs: bool = True,
) -> dict[str, Any]:
    rows = [r for r in read_jsonl(candidates_path) if isinstance(r, dict)]
    baselines: dict[str, dict[str, Any]] = {}
    probes: list[dict[str, Any]] = []
    for row in rows:
        meta = _metadata(row)
        aid = str(row.get("action_id"))
        if meta.get("is_contextual_baseline"):
            baselines[aid] = row
        else:
            probes.append(row)

    buckets: dict[tuple[str, str, str, str], deque[dict[str, Any]]] = defaultdict(deque)
    for row in probes:
        meta = _metadata(row)
        key = (
            str(meta.get("premise_use_id") or meta.get("premise_use_row_id") or ""),
            str(meta.get("pre_context_kind") or meta.get("pre_context_id") or ""),
            str(meta.get("post_context_kind") or meta.get("post_context_id") or ""),
            str(meta.get("task_id") or "global"),
        )
        buckets[key].append(row)

    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    baseline_missing = 0
    keys = list(sorted(buckets.keys()))
    keys_by_uid: dict[str, deque[tuple[str, str, str, str]]] = defaultdict(deque)
    for key in keys:
        keys_by_uid[key[0]].append(key)
    uid_order = list(sorted(keys_by_uid))
    budget = max(0, int(budget))
    while len(selected) < budget and any(buckets.values()):
        progressed = False
        for uid in uid_order:
            if len(selected) >= budget:
                break
            key_queue = keys_by_uid[uid]
            probe: dict[str, Any] | None = None
            key: tuple[str, str, str, str] | None = None
            for _ in range(len(key_queue)):
                candidate_key = key_queue.popleft()
                if buckets[candidate_key]:
                    key = candidate_key
                    probe = buckets[candidate_key].popleft()
                    if buckets[candidate_key]:
                        key_queue.append(candidate_key)
                    break
            if probe is None or key is None:
                continue
            meta = _metadata(probe)
            baseline_id = str(meta.get("baseline_action_id") or "")
            baseline = baselines.get(baseline_id)
            if require_baseline_pairs and baseline_id and baseline is None:
                baseline_missing += 1
                continue
            if baseline and baseline_id not in selected_ids:
                needed = 2 if require_baseline_pairs else 1
                if len(selected) + needed > budget:
                    buckets[key].appendleft(probe)
                    key_queue.appendleft(key)
                    continue
                selected.append(baseline)
                selected_ids.add(baseline_id)
            aid = str(probe.get("action_id"))
            if aid not in selected_ids and len(selected) < budget:
                selected.append(probe)
                selected_ids.add(aid)
                progressed = True
        if not progressed:
            break

    write_jsonl(out, selected)
    selected_baselines = sum(1 for r in selected if _metadata(r).get("is_contextual_baseline"))
    summary = {
        "schema_version": SCHEMA_BIVARIATE_SCHEDULE,
        "candidates": str(candidates_path),
        "out": str(out),
        "budget": budget,
        "n_input": len(rows),
        "n_probes_input": len(probes),
        "n_baselines_input": len(baselines),
        "n_selected": len(selected),
        "n_selected_probes": len(selected) - selected_baselines,
        "n_selected_baselines": selected_baselines,
        "baseline_missing": baseline_missing,
        "require_baseline_pairs": bool(require_baseline_pairs),
        "n_strata": len(keys),
        "canonical_status": "bivariate_audit_schedule_chart_not_canonical",
    }
    if report_out:
        _json_dump(summary, report_out)
    return summary


def build_repair_face_ledger(
    *,
    fingerprints_path: str | Path,
    classes_path: str | Path,
    out: str | Path,
    report_out: str | Path | None = None,
    validation_rows_path: str | Path | None = None,
) -> dict[str, Any]:
    classes = [r for r in read_jsonl(classes_path) if isinstance(r, dict)]
    validations = {}
    if validation_rows_path and Path(validation_rows_path).exists():
        validations = {str(r.get("premise_class_id")): r for r in read_jsonl(validation_rows_path) if isinstance(r, dict)}
    rows: list[dict[str, Any]] = []
    for cl in classes:
        cid = str(cl.get("premise_class_id") or cl.get("class_id"))
        val = validations.get(cid, {})
        face_id = "face_" + stable_hash({"class": cid, "members": cl.get("member_premise_use_ids")}, 14)
        rows.append({
            "schema_version": SCHEMA_REPAIR_FACE_LEDGER,
            "face_id": face_id,
            "source_class_id": cid,
            "premise_use_ids": list(cl.get("member_premise_use_ids") or []),
            "positive_response_face": cl.get("response_summary") or {},
            "carrier_face": cl.get("carrier_summary") or {},
            "gamma_face": cl.get("gamma_summary") or {},
            "domain_face": {"domain_support": list(cl.get("domain_support") or [])},
            "cost_face": cl.get("cost_summary") or {},
            "class_status": cl.get("class_status"),
            "validation_status": val.get("validation_status"),
            "poms_status": "pending",
            "canonical_status": "finite_repair_face_chart_not_canonical",
        })
    write_jsonl(out, rows)
    summary = {
        "schema_version": SCHEMA_REPAIR_FACE_LEDGER,
        "fingerprints": str(fingerprints_path),
        "classes": str(classes_path),
        "validation_rows": str(validation_rows_path) if validation_rows_path else None,
        "out": str(out),
        "n_faces": len(rows),
        "canonical_status": "repair_face_ledger_is_finite_chart_not_canonical",
    }
    if report_out:
        _json_dump(summary, report_out)
    return summary


__all__ = [
    "build_premise_use_rows",
    "write_separator_contexts",
    "generate_bivariate_contextual_candidates",
    "schedule_bivariate_candidates",
    "build_repair_face_ledger",
]
