from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable
import json
import math

import numpy as np

from .contextual_congruence import IDENTITY_CONTEXT_ID, compose_tactics
from .premise_response import (
    _cosine,
    _distance,
    _dot_map,
    _mean,
    _parse_json_or_file,
    _safe_float,
    extract_premise_name,
    infer_use_mode,
    premise_use_id,
)
from .schemas import read_jsonl, stable_hash, write_jsonl


SCHEMA_CANDIDATES = "lean-rgc-premise-contextual-candidates-v50.0"
SCHEMA_FINGERPRINT = "lean-rgc-premise-contextual-fingerprint-v50.0"
SCHEMA_QUOTIENT = "lean-rgc-premise-contextual-quotient-v50.0"
SCHEMA_VALIDATION = "lean-rgc-premise-contextual-validation-v50.0"
SCHEMA_RETRIEVAL = "lean-rgc-premise-contextual-retrieval-v50.0"


def _json_dump(obj: Any, path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def _load_actions(path: str | Path | None) -> list[dict[str, Any]]:
    if not path:
        return []
    rows: list[dict[str, Any]] = []
    for row in read_jsonl(path):
        if not isinstance(row, dict):
            continue
        action = dict(row)
        action.setdefault("metadata", {})
        aid = str(action.get("action_id") or action.get("id") or stable_hash(action, 14))
        action["action_id"] = aid
        action.setdefault("tactic", "")
        action.setdefault("tactic_class", action.get("class") or infer_use_mode(action.get("tactic", "")))
        action.setdefault("carrier_tags", [])
        action.setdefault("cost_estimate", 1.0)
        rows.append(action)
    return rows


def _identity_action() -> dict[str, Any]:
    return {
        "action_id": IDENTITY_CONTEXT_ID,
        "tactic": "",
        "tactic_class": "identity_context",
        "carrier_tags": [],
        "cost_estimate": 0.0,
        "metadata": {"source": "identity_context"},
    }


def _action_id(action: dict[str, Any] | None) -> str:
    if not action:
        return IDENTITY_CONTEXT_ID
    return str(action.get("action_id") or action.get("id") or IDENTITY_CONTEXT_ID)


def _tactic(action: dict[str, Any] | None) -> str:
    if not action or _action_id(action) == IDENTITY_CONTEXT_ID:
        return ""
    return str(action.get("tactic") or "").strip()


def _context_pool(actions: list[dict[str, Any]], *, include_identity: bool) -> list[dict[str, Any]]:
    return ([_identity_action()] if include_identity else []) + list(actions)


def _instantiation(action: dict[str, Any]) -> dict[str, Any]:
    meta = action.get("metadata") if isinstance(action.get("metadata"), dict) else {}
    inst = meta.get("instantiation")
    if isinstance(inst, dict):
        return dict(inst)
    premise = meta.get("premise")
    direction = None
    if isinstance(premise, dict):
        direction = premise.get("direction") or premise.get("rw_direction")
    tactic = str(action.get("tactic") or "")
    return {
        "direction": direction or ("reverse" if "<-" in tactic else "forward"),
        "tactic_class": action.get("tactic_class") or action.get("class") or infer_use_mode(tactic),
    }


def _premise_metadata(action: dict[str, Any]) -> dict[str, Any]:
    prem = extract_premise_name(action)
    mode = infer_use_mode(action.get("tactic", ""))
    inst = _instantiation(action)
    return {
        "premise_use_id": premise_use_id(action),
        "premise_id": prem,
        "use_mode": mode,
        "instantiation": inst,
    }


def _context_probe_id(state_id: str | None, pre_id: str, post_id: str) -> str:
    s = str(state_id or "global")
    return f"ctx:{s}|pre:{pre_id}|post:{post_id}"


def _baseline_action(pre: dict[str, Any], post: dict[str, Any], *, separator: str = "\n") -> dict[str, Any]:
    pre_id = _action_id(pre)
    post_id = _action_id(post)
    tactic = compose_tactics(_tactic(pre), "", _tactic(post), separator=separator)
    h = stable_hash({"baseline": True, "pre": pre_id, "post": post_id, "tactic": tactic}, 12)
    action_id = f"premctx_base_{pre_id}_{post_id}_{h}".replace(" ", "_")
    carrier_tags = sorted(set(list(pre.get("carrier_tags") or []) + list(post.get("carrier_tags") or [])))
    depth = int(pre_id != IDENTITY_CONTEXT_ID) + int(post_id != IDENTITY_CONTEXT_ID)
    return {
        "action_id": action_id,
        "tactic": tactic,
        "tactic_class": "premise_contextual_baseline",
        "class": "premise_contextual_baseline",
        "carrier_tags": carrier_tags,
        "cost_estimate": 0.25 * depth,
        "metadata": {
            "source": "premise_contextual_baseline_v50",
            "is_contextual_baseline": True,
            "pre_context_id": pre_id,
            "post_context_id": post_id,
            "left_context_id": pre_id,
            "right_context_id": post_id,
            "context_pair": f"{pre_id}::{post_id}",
            "baseline_context_pair": f"{pre_id}::{post_id}",
            "context_formula": "pre; post",
            "context_depth": depth,
            "canonical_status": "premise_contextual_baseline_chart_not_canonical",
        },
    }


def _contextual_premise_action(
    premise_action: dict[str, Any],
    pre: dict[str, Any],
    post: dict[str, Any],
    *,
    separator: str = "\n",
) -> dict[str, Any]:
    pre_id = _action_id(pre)
    post_id = _action_id(post)
    core_id = _action_id(premise_action)
    pmeta = _premise_metadata(premise_action)
    tactic = compose_tactics(_tactic(pre), _tactic(premise_action), _tactic(post), separator=separator)
    h = stable_hash({"premise_use": pmeta["premise_use_id"], "pre": pre_id, "post": post_id, "tactic": tactic}, 12)
    action_id = f"premctx_{core_id}_{pre_id}_{post_id}_{h}".replace(" ", "_")
    core_meta = dict(premise_action.get("metadata") or {})
    core_meta.update(
        {
            "source": "premise_contextual_quotient_probe_v50",
            "premise_contextual_probe": True,
            "core_action_id": core_id,
            "base_action_id": core_id,
            "pre_context_id": pre_id,
            "post_context_id": post_id,
            "left_context_id": pre_id,
            "right_context_id": post_id,
            "context_pair": f"{pre_id}::{post_id}",
            "context_formula": "pre; premise_use; post",
            "context_order": "g -> pre_context(B) -> premise_use(u) -> post_context(A)",
            "context_depth": int(pre_id != IDENTITY_CONTEXT_ID) + int(post_id != IDENTITY_CONTEXT_ID),
            "baseline_required_for_incremental_response": True,
            "premise_core_action": {
                "action_id": premise_action.get("action_id"),
                "tactic": premise_action.get("tactic", ""),
                "tactic_class": premise_action.get("tactic_class") or premise_action.get("class") or pmeta["use_mode"],
                "carrier_tags": list(premise_action.get("carrier_tags") or []),
                "cost_estimate": _safe_float(premise_action.get("cost_estimate"), 1.0),
                "max_heartbeats": premise_action.get("max_heartbeats"),
                "metadata": dict(premise_action.get("metadata") or {}),
            },
            "canonical_status": "premise_contextual_probe_action_chart_not_canonical",
            **pmeta,
        }
    )
    carrier_tags = sorted(
        set(
            list(premise_action.get("carrier_tags") or [])
            + list(pre.get("carrier_tags") or [])
            + list(post.get("carrier_tags") or [])
            + ["premise_contextual"]
        )
    )
    return {
        "action_id": action_id,
        "tactic": tactic,
        "tactic_class": "premise_contextual_probe",
        "class": "premise_contextual_probe",
        "carrier_tags": carrier_tags,
        "cost_estimate": _safe_float(premise_action.get("cost_estimate"), 1.0) + 0.25 * core_meta["context_depth"],
        "metadata": core_meta,
    }


def generate_premise_contextual_candidates(
    premise_actions_path: str | Path,
    out: str | Path,
    *,
    contexts_path: str | Path | None = None,
    max_premises: int | None = None,
    max_left: int = 4,
    max_right: int = 4,
    max_candidates: int | None = None,
    include_identity: bool = True,
    include_baselines: bool = True,
    separator: str = "\n",
) -> dict[str, Any]:
    """Generate B;u;A premise probes plus B;A baseline probes.

    Existing contextual helper names use left/right.  This module uses
    pre/post aliases so the audited action text matches g -> B -> u -> A.
    """

    premises = _load_actions(premise_actions_path)
    contexts = _load_actions(contexts_path) if contexts_path else list(premises)
    if max_premises is not None:
        premises = premises[: max(0, int(max_premises))]
    pool = _context_pool(contexts, include_identity=include_identity)
    pre_contexts = pool[: max(0, int(max_left) + int(include_identity))]
    post_contexts = pool[: max(0, int(max_right) + int(include_identity))]

    rows: list[dict[str, Any]] = []
    seen: set[str] = set()

    if include_baselines:
        for pre in pre_contexts:
            for post in post_contexts:
                row = _baseline_action(pre, post, separator=separator)
                aid = str(row["action_id"])
                if aid not in seen:
                    seen.add(aid)
                    rows.append(row)
                    if max_candidates is not None and len(rows) >= int(max_candidates):
                        write_jsonl(out, rows)
                        return _candidate_summary(premise_actions_path, contexts_path, out, rows, premises, pre_contexts, post_contexts, True)

    for action in premises:
        for pre in pre_contexts:
            for post in post_contexts:
                row = _contextual_premise_action(action, pre, post, separator=separator)
                aid = str(row["action_id"])
                if aid in seen:
                    continue
                seen.add(aid)
                rows.append(row)
                if max_candidates is not None and len(rows) >= int(max_candidates):
                    write_jsonl(out, rows)
                    return _candidate_summary(premise_actions_path, contexts_path, out, rows, premises, pre_contexts, post_contexts, True)

    write_jsonl(out, rows)
    return _candidate_summary(premise_actions_path, contexts_path, out, rows, premises, pre_contexts, post_contexts, False)


def _candidate_summary(
    premise_actions_path: str | Path,
    contexts_path: str | Path | None,
    out: str | Path,
    rows: list[dict[str, Any]],
    premises: list[dict[str, Any]],
    pre_contexts: list[dict[str, Any]],
    post_contexts: list[dict[str, Any]],
    truncated: bool,
) -> dict[str, Any]:
    n_baselines = sum(1 for r in rows if (r.get("metadata") or {}).get("is_contextual_baseline"))
    return {
        "schema_version": SCHEMA_CANDIDATES,
        "premise_actions": str(premise_actions_path),
        "contexts": str(contexts_path) if contexts_path else str(premise_actions_path),
        "out": str(out),
        "n_actions": len(rows),
        "n_premise_contextual_actions": len(rows) - n_baselines,
        "n_baseline_actions": n_baselines,
        "n_premises": len(premises),
        "n_pre_contexts": len(pre_contexts),
        "n_post_contexts": len(post_contexts),
        "truncated": bool(truncated),
        "canonical_status": "premise_contextual_candidates_are_probe_charts_not_canonical",
    }


def _load_action_map(actions_path: str | Path | None) -> dict[str, dict[str, Any]]:
    return {str(a.get("action_id")): a for a in _load_actions(actions_path)}


def _row_action(row: dict[str, Any], action_map: dict[str, dict[str, Any]]) -> dict[str, Any]:
    aid = str(row.get("action_id") or row.get("selected_action_id") or "")
    action = action_map.get(aid)
    if action:
        return action
    embedded = row.get("action")
    if isinstance(embedded, dict):
        return dict(embedded)
    return {
        "action_id": aid,
        "tactic": row.get("tactic", ""),
        "metadata": row.get("metadata", {}) if isinstance(row.get("metadata"), dict) else {},
    }


def _response_map(row: dict[str, Any]) -> dict[str, float]:
    resp = row.get("response")
    if isinstance(resp, dict):
        return {str(k): _safe_float(v) for k, v in resp.items()}
    keys = row.get("response_keys") or []
    vals = row.get("response_flat") or []
    return {str(k): _safe_float(vals[i]) for i, k in enumerate(keys[: len(vals)])}


def _carrier_map(row: dict[str, Any]) -> dict[str, float]:
    carrier = row.get("carrier_delta")
    if isinstance(carrier, dict):
        return {str(k): _safe_float(v) for k, v in carrier.items()}
    return {}


def _gamma_map(row: dict[str, Any]) -> dict[str, float]:
    for key in ("gamma_delta", "gamma", "gamma_response"):
        obj = row.get(key)
        if isinstance(obj, dict):
            return {str(k): _safe_float(v) for k, v in obj.items()}
    return {}


def _status(row: dict[str, Any]) -> str:
    return str(row.get("audit_status") or row.get("status") or "unknown").lower()


def _row_state(row: dict[str, Any]) -> str:
    return str(row.get("state_id") or row.get("task_id") or "global")


def _context_from_action(action: dict[str, Any]) -> tuple[str, str]:
    meta = action.get("metadata") if isinstance(action.get("metadata"), dict) else {}
    pre = str(meta.get("pre_context_id") or meta.get("left_context_id") or row_default_context_id(meta, "pre"))
    post = str(meta.get("post_context_id") or meta.get("right_context_id") or row_default_context_id(meta, "post"))
    return pre, post


def row_default_context_id(meta: dict[str, Any], key: str) -> str:
    pair = str(meta.get("context_pair") or "")
    if "::" in pair:
        left, right = pair.split("::", 1)
        return left if key == "pre" else right
    return IDENTITY_CONTEXT_ID


def _vector_sub(a: dict[str, float], b: dict[str, float]) -> dict[str, float]:
    keys = set(a) | set(b)
    return {k: _safe_float(a.get(k)) - _safe_float(b.get(k)) for k in keys if abs(_safe_float(a.get(k)) - _safe_float(b.get(k))) > 1e-15}


def _row_cost(row: dict[str, Any], action: dict[str, Any]) -> dict[str, float]:
    return {
        "elapsed_ms": _safe_float(row.get("elapsed_ms"), 0.0),
        "heartbeats": _safe_float(row.get("heartbeats"), 0.0),
        "cost_estimate": _safe_float(action.get("cost_estimate"), 1.0),
        "generated_goals": _safe_float((row.get("state_delta") or {}).get("generated_goals") if isinstance(row.get("state_delta"), dict) else None, 0.0),
    }


def _row_audit(row: dict[str, Any]) -> dict[str, float]:
    st = _status(row)
    return {
        "success": 1.0 if st == "success" else 0.0,
        "partial": 1.0 if st == "partial" else 0.0,
        "failure": 1.0 if st in {"fail", "failure", "elab_error"} else 0.0,
        "timeout": 1.0 if st == "timeout" else 0.0,
        "unsafe": 1.0 if st == "unsafe" else 0.0,
    }


def _mean_map(rows: Iterable[dict[str, float]]) -> dict[str, float]:
    vals: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        for k, v in row.items():
            vals[str(k)].append(_safe_float(v))
    return {k: _mean(vs) for k, vs in sorted(vals.items())}


def build_premise_contextual_fingerprints(
    *,
    responses_path: str | Path,
    out: str | Path,
    actions_path: str | Path | None = None,
    summary_out: str | Path | None = None,
    min_contexts: int = 1,
    include_carrier: bool = True,
    include_gamma: bool = True,
    include_cost: bool = True,
    include_audit: bool = True,
    baseline_required: bool = False,
) -> dict[str, Any]:
    action_map = _load_action_map(actions_path)
    baseline_rows: dict[tuple[str, str, str], dict[str, Any]] = {}
    premise_rows: list[tuple[dict[str, Any], dict[str, Any]]] = []

    n_rows = 0
    for row in read_jsonl(responses_path):
        if not isinstance(row, dict):
            continue
        n_rows += 1
        action = _row_action(row, action_map)
        meta = action.get("metadata") if isinstance(action.get("metadata"), dict) else {}
        pre, post = _context_from_action(action)
        key = (_row_state(row), pre, post)
        row_norm = {
            **row,
            "action_id": str(row.get("action_id") or row.get("selected_action_id") or action.get("action_id") or ""),
            "response": _response_map(row),
            "carrier_delta": _carrier_map(row),
        }
        if meta.get("is_contextual_baseline") or str(meta.get("source") or "").startswith("premise_contextual_baseline"):
            baseline_rows[key] = row_norm
            continue
        if meta.get("premise_contextual_probe") or meta.get("premise_use_id") or str(meta.get("source") or "").startswith("premise_contextual_quotient_probe"):
            premise_rows.append((row_norm, action))

    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    action_for_uid: dict[str, dict[str, Any]] = {}
    baseline_missing = 0
    baseline_present = 0
    skipped_missing_baseline = 0

    for row, action in premise_rows:
        meta = action.get("metadata") if isinstance(action.get("metadata"), dict) else {}
        pmeta = {
            "premise_use_id": str(meta.get("premise_use_id") or premise_use_id(action)),
            "premise_id": str(meta.get("premise_id") or extract_premise_name(action)),
            "use_mode": str(meta.get("use_mode") or infer_use_mode(action.get("tactic", ""))),
            "instantiation": meta.get("instantiation") if isinstance(meta.get("instantiation"), dict) else _instantiation(action),
        }
        pre, post = _context_from_action(action)
        state = _row_state(row)
        base = baseline_rows.get((state, pre, post))
        if base is None:
            baseline_missing += 1
            if baseline_required:
                skipped_missing_baseline += 1
                continue
            resp_inc = dict(row.get("response") or {})
            carrier_inc = dict(row.get("carrier_delta") or {})
            gamma_inc = _gamma_map(row)
            base_status = "missing_chart_fallback"
        else:
            baseline_present += 1
            resp_inc = _vector_sub(row.get("response") or {}, base.get("response") or {})
            carrier_inc = _vector_sub(row.get("carrier_delta") or {}, base.get("carrier_delta") or {})
            gamma_inc = _vector_sub(_gamma_map(row), _gamma_map(base))
            base_status = "baseline_subtracted"

        h = _context_probe_id(state, pre, post)
        probe = {
            "context_id": h,
            "state_id": state,
            "pre_context_id": pre,
            "post_context_id": post,
            "action_id": row.get("action_id"),
            "status": _status(row),
            "baseline_status": base_status,
            "response_increment": resp_inc,
            "carrier_increment": carrier_inc,
            "gamma_increment": gamma_inc,
            "cost": _row_cost(row, action),
            "audit": _row_audit(row),
            **pmeta,
        }
        uid = pmeta["premise_use_id"]
        groups[uid].append(probe)
        action_for_uid.setdefault(uid, action)

    out_rows: list[dict[str, Any]] = []
    for uid, probes in sorted(groups.items()):
        contexts = sorted({str(p["context_id"]) for p in probes})
        if len(contexts) < int(min_contexts):
            continue
        action = action_for_uid[uid]
        premise_id = str(probes[0].get("premise_id") or extract_premise_name(action))
        use_mode = str(probes[0].get("use_mode") or infer_use_mode(action.get("tactic", "")))
        status_counts: dict[str, int] = defaultdict(int)
        fingerprint: dict[str, float | str] = {}
        response_maps = []
        carrier_maps = []
        gamma_maps = []
        cost_maps = []
        audit_maps = []
        domain_support = []
        baseline_counts: dict[str, int] = defaultdict(int)

        for p in probes:
            ctx = str(p["context_id"])
            st = str(p["status"])
            status_counts[st] += 1
            baseline_counts[str(p.get("baseline_status") or "unknown")] += 1
            fingerprint[f"{ctx}::status::{st}"] = 1.0
            domain_support.append(ctx)
            resp = {str(k): _safe_float(v) for k, v in (p.get("response_increment") or {}).items()}
            response_maps.append(resp)
            for k, v in resp.items():
                fingerprint[f"{ctx}::resp::{k}"] = v
            if include_carrier:
                car = {str(k): _safe_float(v) for k, v in (p.get("carrier_increment") or {}).items()}
                carrier_maps.append(car)
                for k, v in car.items():
                    fingerprint[f"{ctx}::carrier::{k}"] = v
            if include_gamma:
                gam = {str(k): _safe_float(v) for k, v in (p.get("gamma_increment") or {}).items()}
                gamma_maps.append(gam)
                for k, v in gam.items():
                    fingerprint[f"{ctx}::gamma::{k}"] = v
            if include_cost:
                cost = {str(k): _safe_float(v) for k, v in (p.get("cost") or {}).items()}
                cost_maps.append(cost)
                for k, v in cost.items():
                    fingerprint[f"{ctx}::cost::{k}"] = v
            if include_audit:
                audit = {str(k): _safe_float(v) for k, v in (p.get("audit") or {}).items()}
                audit_maps.append(audit)
                for k, v in audit.items():
                    fingerprint[f"{ctx}::audit::{k}"] = v

        action_meta = action.get("metadata") if isinstance(action.get("metadata"), dict) else {}
        representative_action = dict(action_meta.get("premise_core_action") or action)
        representative_action.setdefault("metadata", {})
        representative_action["metadata"] = dict(representative_action.get("metadata") or {})
        representative_action["metadata"].update(
            {
                "source": "premise_contextual_fingerprint_representative_v50",
                "premise_use_id": uid,
                "premise_id": premise_id,
                "use_mode": use_mode,
            }
        )
        out_rows.append(
            {
                "schema_version": SCHEMA_FINGERPRINT,
                "premise_use_id": uid,
                "premise_id": premise_id,
                "use_mode": use_mode,
                "instantiation": probes[0].get("instantiation") or {},
                "representative_action_id": representative_action.get("action_id"),
                "representative_action": representative_action,
                "fingerprint": dict(sorted(fingerprint.items())),
                "domain_support": sorted(set(domain_support)),
                "n_contexts": len(set(domain_support)),
                "n_rows": len(probes),
                "status_counts": dict(sorted(status_counts.items())),
                "response_summary": _mean_map(response_maps),
                "carrier_summary": _mean_map(carrier_maps),
                "gamma_summary": _mean_map(gamma_maps),
                "cost_summary": _mean_map(cost_maps),
                "audit_summary": _mean_map(audit_maps),
                "baseline_coverage": dict(sorted(baseline_counts.items())),
                "canonical_status": "finite_premise_contextual_fingerprint_chart_not_canonical",
            }
        )

    out_rows.sort(key=lambda r: (-int(r.get("n_contexts") or 0), str(r.get("premise_id")), str(r.get("use_mode"))))
    write_jsonl(out, out_rows)
    unique_contexts = sorted({str(ctx) for row in out_rows for ctx in (row.get("domain_support") or [])})
    summary = {
        "schema_version": SCHEMA_FINGERPRINT,
        "responses": str(responses_path),
        "actions": str(actions_path) if actions_path else None,
        "out": str(out),
        "n_response_rows": n_rows,
        "n_premise_probe_rows": len(premise_rows),
        "n_fingerprints": len(out_rows),
        "n_baseline_rows": len(baseline_rows),
        "baseline_present": baseline_present,
        "baseline_missing": baseline_missing,
        "skipped_missing_baseline": skipped_missing_baseline,
        "n_unique_premise_use_ids": len({str(r.get("premise_use_id")) for r in out_rows}),
        "n_unique_premise_ids": len({str(r.get("premise_id")) for r in out_rows}),
        "n_unique_use_modes": len({str(r.get("use_mode")) for r in out_rows}),
        "n_unique_context_pairs": len(unique_contexts),
        "row_degenerate": len(out_rows) < 2,
        "column_degenerate": len(unique_contexts) < 2,
        "degeneracy_status": "row_degenerate_fingerprint_universe" if len(out_rows) < 2 else ("column_degenerate_context_universe" if len(unique_contexts) < 2 else "nondegenerate_finite_chart"),
        "min_contexts": int(min_contexts),
        "baseline_required": bool(baseline_required),
        "canonical_status": "premise_contextual_fingerprints_are_finite_charts_not_canonical",
    }
    if summary_out:
        _json_dump(summary, summary_out)
    return summary


def _domain(row: dict[str, Any]) -> set[str]:
    return {str(x) for x in row.get("domain_support") or []}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / max(1, len(a | b))


def _typed_vector(row: dict[str, Any], prefixes: set[str] | None = None) -> dict[str, float]:
    fp = row.get("fingerprint") if isinstance(row.get("fingerprint"), dict) else {}
    out: dict[str, float] = {}
    for k, v in fp.items():
        ks = str(k)
        if prefixes and not any(f"::{prefix}::" in ks for prefix in prefixes):
            continue
        if isinstance(v, (int, float)):
            out[ks] = _safe_float(v)
    return out


def _weighted_distance(
    a: dict[str, Any],
    b: dict[str, Any],
    *,
    weights: dict[str, float],
) -> dict[str, float]:
    parts = {
        "response": _distance(_typed_vector(a, {"resp"}), _typed_vector(b, {"resp"})),
        "carrier": _distance(_typed_vector(a, {"carrier"}), _typed_vector(b, {"carrier"})),
        "gamma": _distance(_typed_vector(a, {"gamma"}), _typed_vector(b, {"gamma"})),
        "cost": _distance(_typed_vector(a, {"cost"}), _typed_vector(b, {"cost"})),
        "audit": _distance(_typed_vector(a, {"audit", "status"}), _typed_vector(b, {"audit", "status"})),
        "domain": 1.0 - _jaccard(_domain(a), _domain(b)),
    }
    parts["total"] = float(sum(_safe_float(weights.get(k), 0.0) * v for k, v in parts.items()))
    return parts


def _centroid(rows: list[dict[str, Any]], key: str = "fingerprint") -> dict[str, float]:
    vals: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        obj = row.get(key) if isinstance(row.get(key), dict) else {}
        for k, v in obj.items():
            if isinstance(v, (int, float)):
                vals[str(k)].append(_safe_float(v))
    return {k: _mean(vs) for k, vs in sorted(vals.items())}


def _summary_centroid(rows: list[dict[str, Any]], key: str) -> dict[str, float]:
    vals: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        obj = row.get(key) if isinstance(row.get(key), dict) else {}
        for k, v in obj.items():
            vals[str(k)].append(_safe_float(v))
    return {k: _mean(vs) for k, vs in sorted(vals.items())}


def _status_for_class(rows: list[dict[str, Any]], domain_jaccard_min: float) -> str:
    carrier_safe = []
    for row in rows:
        audit = row.get("audit_summary") if isinstance(row.get("audit_summary"), dict) else {}
        carrier = row.get("carrier_summary") if isinstance(row.get("carrier_summary"), dict) else {}
        carrier_safe.append(_safe_float(audit.get("unsafe")) <= 1e-12 and all(v >= -1e-12 for v in carrier.values()))
    if carrier_safe and any(carrier_safe) and not all(carrier_safe):
        return "carrier_unsafe_mixed_class"
    if len(rows) > 1:
        domains = [_domain(r) for r in rows]
        min_j = min(_jaccard(domains[i], domains[j]) for i in range(len(domains)) for j in range(i + 1, len(domains)))
        if min_j < domain_jaccard_min:
            return "domain_unstable_class"
    return "premise_class_candidate"


def mine_premise_contextual_quotient(
    *,
    fingerprints_path: str | Path,
    out_dir: str | Path,
    epsilon: float = 0.25,
    cosine_threshold: float = 0.95,
    domain_jaccard_threshold: float = 0.0,
    response_weight: float = 1.0,
    carrier_weight: float = 1.0,
    gamma_weight: float = 0.25,
    domain_weight: float = 1.0,
    cost_weight: float = 0.05,
    uncertainty_weight: float = 0.10,
) -> dict[str, Any]:
    rows = [r for r in read_jsonl(fingerprints_path) if isinstance(r, dict)]
    n = len(rows)
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    if n < 2:
        write_jsonl(out_path / "premise_quotient_classes.jsonl", [])
        write_jsonl(out_path / "premise_quotient_members.jsonl", [])
        write_jsonl(out_path / "premise_quotient_representatives.jsonl", [])
        write_jsonl(out_path / "premise_quotient_distance_rows.jsonl", [])
        summary = {
            "schema_version": SCHEMA_QUOTIENT,
            "fingerprints": str(fingerprints_path),
            "n_premise_use_rows": n,
            "n_classes": 0,
            "quotient_status": "skipped_or_vacuous_row_universe",
            "reason": "n_fingerprints_lt_2",
            "epsilon": epsilon,
            "cosine_threshold": cosine_threshold,
            "domain_jaccard_threshold": domain_jaccard_threshold,
            "artifacts": {
                "classes": str(out_path / "premise_quotient_classes.jsonl"),
                "members": str(out_path / "premise_quotient_members.jsonl"),
                "representatives": str(out_path / "premise_quotient_representatives.jsonl"),
                "distances": str(out_path / "premise_quotient_distance_rows.jsonl"),
            },
            "canonical_status": "vacuous_premise_contextual_quotient_chart_not_canonical",
        }
        _json_dump(summary, out_path / "premise_quotient_report.json")
        _json_dump(summary, out_path / "premise_contextual_quotient_report.json")
        return summary
    parent = list(range(n))
    weights = {
        "response": response_weight,
        "carrier": carrier_weight,
        "gamma": gamma_weight,
        "domain": domain_weight,
        "cost": cost_weight,
        "audit": uncertainty_weight,
    }

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    vectors = [_typed_vector(r, {"resp", "carrier", "gamma"}) for r in rows]
    pair_rows: list[dict[str, Any]] = []
    for i in range(n):
        for j in range(i + 1, n):
            dom_j = _jaccard(_domain(rows[i]), _domain(rows[j]))
            parts = _weighted_distance(rows[i], rows[j], weights=weights)
            cos = _cosine(vectors[i], vectors[j])
            same = dom_j >= domain_jaccard_threshold and (cos >= cosine_threshold or parts["total"] <= epsilon)
            if same:
                union(i, j)
            pair_rows.append(
                {
                    "u": rows[i].get("premise_use_id"),
                    "v": rows[j].get("premise_use_id"),
                    "cosine": cos,
                    "domain_jaccard": dom_j,
                    "distance": parts,
                    "merged": bool(same),
                }
            )

    groups: dict[int, list[int]] = defaultdict(list)
    for i in range(n):
        groups[find(i)].append(i)
    classes: list[dict[str, Any]] = []
    members: list[dict[str, Any]] = []
    reps: list[dict[str, Any]] = []
    for idxs in sorted(groups.values(), key=lambda x: (-len(x), x[0])):
        cls_rows = [rows[i] for i in idxs]
        rep_idx = max(idxs, key=lambda i: (int(rows[i].get("n_contexts") or 0), int(rows[i].get("n_rows") or 0), -i))
        rep = rows[rep_idx]
        cid = "qpremctx_" + stable_hash([rows[i].get("premise_use_id") for i in idxs], 14)
        domain_union = sorted(set().union(*(_domain(r) for r in cls_rows)))
        cl = {
            "schema_version": SCHEMA_QUOTIENT,
            "premise_class_id": cid,
            "class_id": cid,
            "representative_premise_use_id": rep.get("premise_use_id"),
            "representative_action_id": rep.get("representative_action_id"),
            "representative_action": rep.get("representative_action"),
            "member_premise_use_ids": [r.get("premise_use_id") for r in cls_rows],
            "premise_ids": sorted({str(r.get("premise_id")) for r in cls_rows}),
            "use_modes": sorted({str(r.get("use_mode")) for r in cls_rows}),
            "member_count": len(cls_rows),
            "n_members": len(cls_rows),
            "fingerprint_centroid": _centroid(cls_rows),
            "domain_support": domain_union,
            "response_summary": _summary_centroid(cls_rows, "response_summary"),
            "carrier_summary": _summary_centroid(cls_rows, "carrier_summary"),
            "gamma_summary": _summary_centroid(cls_rows, "gamma_summary"),
            "cost_summary": _summary_centroid(cls_rows, "cost_summary"),
            "audit_summary": _summary_centroid(cls_rows, "audit_summary"),
            "class_status": _status_for_class(cls_rows, domain_jaccard_threshold),
            "canonical_status": "not_canonical_parent_nonpaid_least_repair_required",
        }
        classes.append(cl)
        reps.append({**rep, "premise_class_id": cid, "class_id": cid, "class_status": cl["class_status"]})
        for r in cls_rows:
            members.append(
                {
                    "schema_version": SCHEMA_QUOTIENT,
                    "premise_class_id": cid,
                    "class_id": cid,
                    "premise_use_id": r.get("premise_use_id"),
                    "premise_id": r.get("premise_id"),
                    "use_mode": r.get("use_mode"),
                    "representative": r.get("premise_use_id") == rep.get("premise_use_id"),
                }
            )

    write_jsonl(out_path / "premise_quotient_classes.jsonl", classes)
    write_jsonl(out_path / "premise_quotient_members.jsonl", members)
    write_jsonl(out_path / "premise_quotient_representatives.jsonl", reps)
    write_jsonl(out_path / "premise_quotient_distance_rows.jsonl", pair_rows)
    summary = {
        "schema_version": SCHEMA_QUOTIENT,
        "fingerprints": str(fingerprints_path),
        "n_premise_use_rows": n,
        "n_classes": len(classes),
        "epsilon": epsilon,
        "cosine_threshold": cosine_threshold,
        "domain_jaccard_threshold": domain_jaccard_threshold,
        "weights": weights,
        "artifacts": {
            "classes": str(out_path / "premise_quotient_classes.jsonl"),
            "members": str(out_path / "premise_quotient_members.jsonl"),
            "representatives": str(out_path / "premise_quotient_representatives.jsonl"),
            "distances": str(out_path / "premise_quotient_distance_rows.jsonl"),
        },
        "canonical_status": "finite_premise_contextual_quotient_candidate_not_canonical",
    }
    _json_dump(summary, out_path / "premise_quotient_report.json")
    _json_dump(summary, out_path / "premise_contextual_quotient_report.json")
    return summary


def _context_keys(row: dict[str, Any]) -> set[str]:
    keys: set[str] = set()
    for k in (row.get("fingerprint") or {}).keys():
        ks = str(k)
        if "::" in ks:
            keys.add(ks.split("::", 1)[0])
    return keys or _domain(row)


def _project_contexts(row: dict[str, Any], contexts: set[str]) -> dict[str, Any]:
    out = dict(row)
    fp = row.get("fingerprint") if isinstance(row.get("fingerprint"), dict) else {}
    out["fingerprint"] = {k: v for k, v in fp.items() if str(k).split("::", 1)[0] in contexts}
    out["domain_support"] = sorted(_domain(row) & contexts)
    return out


def validate_premise_contextual_quotient(
    *,
    fingerprints_path: str | Path,
    classes_path: str | Path,
    out_rows: str | Path,
    out_report: str | Path,
    holdout_fraction: float = 0.35,
    epsilon_holdout: float = 0.35,
    separation_delta: float = 0.10,
    domain_jaccard_min: float = 0.0,
    carrier_mixed_threshold: float = 0.05,
) -> dict[str, Any]:
    fps = {str(r.get("premise_use_id")): r for r in read_jsonl(fingerprints_path) if isinstance(r, dict)}
    classes = [r for r in read_jsonl(classes_path) if isinstance(r, dict)]
    rows: list[dict[str, Any]] = []
    centroids: list[tuple[str, dict[str, float]]] = []

    for cl in classes:
        cid = str(cl.get("premise_class_id") or cl.get("class_id"))
        uids = [str(u) for u in cl.get("member_premise_use_ids") or [] if str(u) in fps]
        members = [fps[u] for u in uids]
        all_contexts = sorted(set().union(*(_context_keys(m) for m in members))) if members else []
        holdout_n = max(1, int(math.ceil(len(all_contexts) * holdout_fraction))) if all_contexts else 0
        holdout = {c for c in all_contexts if int(stable_hash({"ctx": c}, 8), 16) % max(1, len(all_contexts)) < holdout_n}
        if not holdout and all_contexts:
            holdout = {all_contexts[-1]}
        projected = [_project_contexts(m, holdout) for m in members] if holdout else members
        diam = 0.0
        min_dom_j = 1.0
        max_carrier = 0.0
        for i in range(len(projected)):
            for j in range(i + 1, len(projected)):
                parts = _weighted_distance(
                    projected[i],
                    projected[j],
                    weights={"response": 1.0, "carrier": 1.0, "gamma": 0.25, "domain": 1.0, "cost": 0.05, "audit": 0.10},
                )
                diam = max(diam, parts["total"])
                min_dom_j = min(min_dom_j, _jaccard(_domain(projected[i]), _domain(projected[j])))
                max_carrier = max(max_carrier, parts["carrier"])
        centroid = _centroid(members)
        centroids.append((cid, centroid))
        status = "singleton_vacuously_stable_not_informative" if len(members) <= 1 else "heldout_validated_premise_class"
        if len(members) > 1 and diam > epsilon_holdout:
            status = "split_suggested"
        if min_dom_j < domain_jaccard_min:
            status = "domain_unstable_class"
        if max_carrier > carrier_mixed_threshold:
            status = "carrier_unsafe_mixed_class"
        rows.append(
            {
                "schema_version": SCHEMA_VALIDATION,
                "premise_class_id": cid,
                "member_count": len(members),
                "holdout_context_count": len(holdout),
                "holdout_diameter": diam,
                "domain_jaccard_min": min_dom_j,
                "carrier_dispersion": max_carrier,
                "validation_status": status,
            }
        )

    nearest: dict[str, float] = {}
    for i in range(len(centroids)):
        cid_i, vec_i = centroids[i]
        best = math.inf
        for j in range(len(centroids)):
            if i == j:
                continue
            best = min(best, _distance(vec_i, centroids[j][1]))
        if math.isinf(best):
            best = 0.0
        nearest[cid_i] = best
    for row in rows:
        sep = nearest.get(str(row.get("premise_class_id")), 0.0)
        row["nearest_between_class_distance"] = sep
        if row["validation_status"] == "heldout_validated_premise_class" and sep < separation_delta and len(rows) > 1:
            row["validation_status"] = "merge_suggested"

    write_jsonl(out_rows, rows)
    status_counts: dict[str, int] = defaultdict(int)
    for row in rows:
        status_counts[str(row.get("validation_status"))] += 1
    report = {
        "schema_version": SCHEMA_VALIDATION,
        "fingerprints": str(fingerprints_path),
        "classes": str(classes_path),
        "out_rows": str(out_rows),
        "n_classes": len(classes),
        "status_counts": dict(sorted(status_counts.items())),
        "holdout_fraction": holdout_fraction,
        "epsilon_holdout": epsilon_holdout,
        "separation_delta": separation_delta,
        "domain_jaccard_min": domain_jaccard_min,
        "canonical_status": "validation_is_finite_probe_evidence_not_canonical_certificate",
    }
    _json_dump(report, out_report)
    return report


def _class_candidate_action(row: dict[str, Any]) -> dict[str, Any]:
    action = dict(row.get("representative_action") or {})
    if not action:
        rep = str(row.get("representative_premise_use_id") or row.get("premise_class_id") or "unknown")
        action = {
            "action_id": "premqrep_" + stable_hash(rep, 12),
            "tactic": "skip",
            "tactic_class": "premise_quotient_representative",
            "carrier_tags": ["premise_contextual_quotient"],
            "cost_estimate": 1.0,
            "metadata": {},
        }
    action.setdefault("metadata", {})
    return action


def retrieve_premise_quotient_classes(
    *,
    classes_path: str | Path,
    out: str | Path,
    summary_out: str | Path | None = None,
    response_normal: dict[str, float] | None = None,
    carrier_normal: dict[str, float] | None = None,
    top_k: int | None = None,
    gamma_weight: float = 0.10,
    cost_weight: float = 0.05,
    uncertainty_weight: float = 0.10,
    import_cost_weight: float = 0.05,
    require_validated: bool = False,
) -> dict[str, Any]:
    rows = [r for r in read_jsonl(classes_path) if isinstance(r, dict)]
    response_normal = response_normal or {}
    carrier_normal = carrier_normal or {}
    scored: list[dict[str, Any]] = []
    for row in rows:
        if require_validated and str(row.get("class_status")) != "heldout_validated_premise_class":
            continue
        resp = {str(k): _safe_float(v) for k, v in (row.get("response_summary") or {}).items()}
        carrier = {str(k): _safe_float(v) for k, v in (row.get("carrier_summary") or {}).items()}
        gamma = {str(k): abs(_safe_float(v)) for k, v in (row.get("gamma_summary") or {}).items()}
        cost = row.get("cost_summary") if isinstance(row.get("cost_summary"), dict) else {}
        audit = row.get("audit_summary") if isinstance(row.get("audit_summary"), dict) else {}
        response_score = _dot_map(response_normal, resp)
        carrier_score = _dot_map(carrier_normal, carrier)
        tail_risk = float(sum(gamma.values()))
        cost_val = _safe_float(cost.get("elapsed_ms"), 0.0) / 1000.0 + _safe_float(cost.get("heartbeats"), 0.0) / 100000.0 + _safe_float(cost.get("cost_estimate"), 1.0)
        import_cost = _safe_float(cost.get("import_cost"), 0.0)
        uncertainty = 1.0 - _safe_float(audit.get("success"), 0.0)
        score = response_score + carrier_score - gamma_weight * tail_risk - cost_weight * cost_val - uncertainty_weight * uncertainty - import_cost_weight * import_cost
        action = _class_candidate_action(row)
        meta = dict(action.get("metadata") or {})
        meta.update(
            {
                "source": "premise_contextual_quotient_retrieval",
                "premise_class_id": row.get("premise_class_id") or row.get("class_id"),
                "representative_premise_use_id": row.get("representative_premise_use_id"),
                "member_count": row.get("member_count") or row.get("n_members"),
                "score_terms": {
                    "response_score": response_score,
                    "carrier_score": carrier_score,
                    "tail_risk_penalty": gamma_weight * tail_risk,
                    "cost_penalty": cost_weight * cost_val,
                    "uncertainty_penalty": uncertainty_weight * uncertainty,
                    "import_cost_penalty": import_cost_weight * import_cost,
                },
                "canonical_status": "premise_quotient_retrieval_candidate_not_canonical",
            }
        )
        action["metadata"] = meta
        scored.append(
            {
                **row,
                "score": float(score),
                "score_terms": meta["score_terms"],
                "candidate_action": action,
            }
        )

    scored.sort(key=lambda r: (-_safe_float(r.get("score")), str(r.get("premise_class_id") or r.get("class_id"))))
    if top_k is not None and top_k > 0:
        scored = scored[: int(top_k)]
    write_jsonl(out, scored)
    summary = {
        "schema_version": SCHEMA_RETRIEVAL,
        "classes": str(classes_path),
        "out": str(out),
        "n_selected": len(scored),
        "response_normal_keys": sorted(response_normal.keys()),
        "carrier_normal_keys": sorted(carrier_normal.keys()),
        "require_validated": bool(require_validated),
        "canonical_status": "premise_contextual_quotient_retrieval_is_coker_chart_not_canonical",
    }
    if summary_out:
        _json_dump(summary, summary_out)
    return summary


def premise_quotient_retrieved_actions(*, retrieved_path: str | Path, out: str | Path) -> dict[str, Any]:
    actions: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in read_jsonl(retrieved_path):
        action = row.get("candidate_action") if isinstance(row.get("candidate_action"), dict) else None
        if not action:
            continue
        aid = str(action.get("action_id") or stable_hash(action, 14))
        if aid in seen:
            continue
        seen.add(aid)
        actions.append(action)
    write_jsonl(out, actions)
    return {"n_actions": len(actions), "out": str(out)}


__all__ = [
    "generate_premise_contextual_candidates",
    "build_premise_contextual_fingerprints",
    "mine_premise_contextual_quotient",
    "validate_premise_contextual_quotient",
    "retrieve_premise_quotient_classes",
    "premise_quotient_retrieved_actions",
    "_parse_json_or_file",
]
