from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from ..schemas import stable_hash, write_jsonl
from .common import (
    SCHEMA_PRIMITIVE_OBSERVABLE,
    SCHEMA_BOUNDED_TRANSCRIPT,
    SCHEMA_FEATURE_CLOSURE,
    SCHEMA_FEATURE_VALUE,
    SCHEMA_FEATURE_SELECTION,
    SCHEMA_AUTO_PLAN,
    SCHEMA_DOST_AUDIT,
    DEFAULT_PRIMITIVE_OBSERVABLES,
    _json_dump,
    _json_load,
    _read_rows,
    _safe_float,
    _as_list,
    _path_if_exists,
    _first_existing,
    _ratio,
    _score_avg,
    _json_bytes,
    _row_identity,
    _status_counter,
    _class_member_count,
    _row_tactic_text,
    _is_macro_policy_row,
    _is_structural_row,
    _nf_status,
    _is_typed_nf_status,
    _matrix_metrics,
)



def primitive_observable_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in DEFAULT_PRIMITIVE_OBSERVABLES:
        obs = dict(row)
        obs.update(
            {
                "schema_version": SCHEMA_PRIMITIVE_OBSERVABLE,
                "bounded": True,
                "cost": {
                    "cpu": "low",
                    "json_bytes": "low",
                    "rss": "low",
                },
                "safety": {
                    "requires_full_expr_graph": False,
                    "requires_pretty_printing": False,
                },
                "canonical_status": "primitive_observable_not_canonical",
            }
        )
        rows.append(obs)
    return rows


def write_primitive_observables(out: str | Path, *, report_out: str | Path | None = None) -> dict[str, Any]:
    rows = primitive_observable_rows()
    write_jsonl(out, rows)
    report = {
        "schema_version": SCHEMA_PRIMITIVE_OBSERVABLE,
        "out": str(out),
        "n_observables": len(rows),
        "observable_ids": [str(r["observable_id"]) for r in rows],
        "canonical_status": "primitive_observable_ledger_not_canonical",
    }
    if report_out:
        _json_dump(report, report_out)
    return report


def _dominant_status(counts: dict[str, Any]) -> str:
    if not counts:
        return "unknown"
    return str(max(counts.items(), key=lambda kv: _safe_float(kv[1]))[0])


def _merge_set_values(*values: Any) -> list[str]:
    out: set[str] = set()
    for value in values:
        for item in _as_list(value):
            if item is not None and str(item):
                out.add(str(item))
    return sorted(out)


def _feature_observables_from_state(prefix: str, obs: dict[str, Any], raw: dict[str, Any]) -> None:
    if not isinstance(obs, dict):
        return
    for key in [
        "goal_count",
        "local_context_count",
        "local_instance_count",
        "metavariable_count",
        "open_mvar_count",
        "typeclass_obligation_count",
        "open_typeclass_obligation_count",
        "target_hash",
        "target_head",
        "target_relation",
        "state_hash_norm",
        "json_bytes",
    ]:
        if key in obs:
            raw[f"{prefix}_{key}"] = obs.get(key)
    if "domain_tags" in obs:
        raw[f"{prefix}_domain_tags"] = _merge_set_values(obs.get("domain_tags"))
    if "carrier_atoms" in obs:
        raw[f"{prefix}_carrier_atoms"] = _merge_set_values(obs.get("carrier_atoms"))


def raw_observables_from_row(row: dict[str, Any]) -> dict[str, Any]:
    raw: dict[str, Any] = {}
    if isinstance(row.get("raw_observables"), dict):
        raw.update(dict(row.get("raw_observables") or {}))

    status = row.get("status") or row.get("audit_status")
    if status is not None:
        raw["status"] = str(status)
    counts = row.get("status_counts") if isinstance(row.get("status_counts"), dict) else {}
    if counts:
        raw["status"] = _dominant_status(counts)
        for key, value in counts.items():
            raw[f"status_count.{key}"] = _safe_float(value)

    state_delta = row.get("state_delta") if isinstance(row.get("state_delta"), dict) else {}
    for key in [
        "goal_count_before",
        "goal_count_after",
        "goal_count_delta",
        "closed_goal_delta",
        "new_goal_count",
        "new_mvar_count",
        "typeclass_obligation_delta",
        "mvar_response",
        "typeclass_open_before",
        "typeclass_open_after",
    ]:
        if key in state_delta:
            raw[key] = state_delta.get(key)
    if "goal_count_delta" not in raw and "goal_count_before" in raw and "goal_count_after" in raw:
        raw["goal_count_delta"] = _safe_float(raw["goal_count_after"]) - _safe_float(raw["goal_count_before"])

    before_obs = row.get("before_observation") if isinstance(row.get("before_observation"), dict) else row.get("kernel_state_before") if isinstance(row.get("kernel_state_before"), dict) else {}
    after_obs = row.get("after_observation") if isinstance(row.get("after_observation"), dict) else row.get("kernel_state_after") if isinstance(row.get("kernel_state_after"), dict) else {}
    _feature_observables_from_state("before", before_obs if isinstance(before_obs, dict) else {}, raw)
    _feature_observables_from_state("after", after_obs if isinstance(after_obs, dict) else {}, raw)
    if "goal_count_before" not in raw and isinstance(before_obs, dict) and "goal_count" in before_obs:
        raw["goal_count_before"] = before_obs.get("goal_count")
    if "goal_count_after" not in raw and isinstance(after_obs, dict) and "goal_count" in after_obs:
        raw["goal_count_after"] = after_obs.get("goal_count")
    if "target_head" not in raw:
        raw["target_head"] = (before_obs or {}).get("target_head") if isinstance(before_obs, dict) else None
    if "target_hash" not in raw:
        raw["target_hash"] = (before_obs or {}).get("target_hash") if isinstance(before_obs, dict) else None
    if "target_relation" not in raw:
        raw["target_relation"] = (before_obs or {}).get("target_relation") if isinstance(before_obs, dict) else None
    if "domain_tags" not in raw:
        raw["domain_tags"] = _merge_set_values(
            before_obs.get("domain_tags") if isinstance(before_obs, dict) else None,
            after_obs.get("domain_tags") if isinstance(after_obs, dict) else None,
            row.get("domain_support"),
        )
    if "carrier_atoms" not in raw:
        raw["carrier_atoms"] = _merge_set_values(
            before_obs.get("carrier_atoms") if isinstance(before_obs, dict) else None,
            after_obs.get("carrier_atoms") if isinstance(after_obs, dict) else None,
            row.get("carrier_tags"),
        )

    transition_features = row.get("transition_features") if isinstance(row.get("transition_features"), dict) else {}
    for key in ["domain_ok", "carrier_safe", "error_signature", "elapsed_ms", "json_bytes", "rss_mb"]:
        if key in transition_features:
            raw[key] = transition_features.get(key)
    if row.get("elapsed_ms") is not None:
        raw["elapsed_ms"] = row.get("elapsed_ms")
    if row.get("heartbeats") is not None:
        raw["heartbeats"] = row.get("heartbeats")
    raw.setdefault("json_bytes", _json_bytes(row))

    replay = row.get("replay") if isinstance(row.get("replay"), dict) else {}
    if replay.get("replay_status") is not None:
        raw["replay_status"] = replay.get("replay_status")
    if raw.get("error_signature") is None:
        messages = row.get("messages") or []
        stderr = row.get("stderr") or ""
        if status and str(status) not in {"success", "partial", "dry_run"}:
            raw["error_signature"] = stable_hash({"messages": messages, "stderr": stderr}, 12)

    for prefix, field in [
        ("response", "response_summary"),
        ("carrier", "carrier_summary"),
        ("gamma", "gamma_summary"),
        ("cost", "cost_summary"),
        ("audit", "audit_summary"),
    ]:
        obj = row.get(field) if isinstance(row.get(field), dict) else {}
        for key, value in obj.items():
            raw[f"{prefix}.{key}"] = _safe_float(value)
    if "elapsed_ms" not in raw and isinstance(row.get("cost_summary"), dict):
        if row["cost_summary"].get("elapsed_ms") is not None:
            raw["elapsed_ms"] = row["cost_summary"].get("elapsed_ms")
    return {k: v for k, v in raw.items() if v is not None}


def build_bounded_transcripts(
    input_path: str | Path,
    out: str | Path,
    *,
    primitive_observables_out: str | Path | None = None,
    summary_out: str | Path | None = None,
    kernel_state_mode: str = "features",
) -> dict[str, Any]:
    rows = _read_rows(input_path)
    out_rows: list[dict[str, Any]] = []
    for row in rows:
        transcript_id, object_id, context_id = _row_identity(row)
        raw = raw_observables_from_row(row)
        status = str(raw.get("status") or row.get("status") or row.get("audit_status") or "unknown")
        cost = {
            "elapsed_ms": _safe_float(raw.get("elapsed_ms")),
            "json_bytes": _safe_float(raw.get("json_bytes")),
            "rss_mb": _safe_float(raw.get("rss_mb")),
        }
        out_rows.append(
            {
                "schema_version": SCHEMA_BOUNDED_TRANSCRIPT,
                "transcript_id": transcript_id,
                "object_id": object_id,
                "source_row_id": object_id,
                "context_id": context_id,
                "baseline_complete": bool(row.get("baseline_complete", True)),
                "kernel_backed": bool(row.get("kernel_backed", row.get("before_observation") is not None or row.get("kernel_state_before") is not None)),
                "kernel_state_mode": kernel_state_mode,
                "raw_observables": raw,
                "generated_features": {},
                "selected_features": {},
                "response": row.get("response_summary") if isinstance(row.get("response_summary"), dict) else row.get("response") if isinstance(row.get("response"), dict) else {},
                "carrier": row.get("carrier_summary") if isinstance(row.get("carrier_summary"), dict) else row.get("carrier_delta") if isinstance(row.get("carrier_delta"), dict) else {},
                "gamma": row.get("gamma_summary") if isinstance(row.get("gamma_summary"), dict) else row.get("gamma_delta") if isinstance(row.get("gamma_delta"), dict) else {},
                "domain": {"domain_tags": _merge_set_values(raw.get("domain_tags"), raw.get("before_domain_tags"), raw.get("after_domain_tags"))},
                "cost": cost,
                "status": status,
                "canonical_status": "finite_transcript_cell_not_canonical",
            }
        )
    write_jsonl(out, out_rows)
    if primitive_observables_out:
        write_primitive_observables(primitive_observables_out)
    status_counts = Counter(str(r.get("status")) for r in out_rows)
    report = {
        "schema_version": SCHEMA_BOUNDED_TRANSCRIPT,
        "input": str(input_path),
        "out": str(out),
        "primitive_observables": str(primitive_observables_out) if primitive_observables_out else None,
        "n_input_rows": len(rows),
        "n_transcripts": len(out_rows),
        "status_counts": dict(sorted(status_counts.items())),
        "kernel_state_mode": kernel_state_mode,
        "canonical_status": "bounded_transcript_ledger_not_canonical",
    }
    if summary_out:
        _json_dump(report, summary_out)
    return report


__all__ = [
    "primitive_observable_rows",
    "write_primitive_observables",
    "raw_observables_from_row",
    "build_bounded_transcripts",
]
