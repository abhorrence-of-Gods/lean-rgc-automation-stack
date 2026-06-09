from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import json
import math

from .schemas import read_jsonl, stable_hash, write_jsonl


SCHEMA_PRIMITIVE_OBSERVABLE = "lean-rgc-primitive-observable-v55.0"
SCHEMA_BOUNDED_TRANSCRIPT = "lean-rgc-bounded-feature-transcript-v55.0"
SCHEMA_FEATURE_CLOSURE = "lean-rgc-feature-closure-v56.0"
SCHEMA_FEATURE_VALUE = "lean-rgc-generated-feature-values-v56.0"
SCHEMA_FEATURE_SELECTION = "lean-rgc-feature-selection-v56.0"
SCHEMA_AUTO_PLAN = "lean-rgc-dost-auto-plan-v57.0"
SCHEMA_DOST_AUDIT = "lean-rgc-dost-audit-reports-v57.0"


DEFAULT_PRIMITIVE_OBSERVABLES: list[dict[str, Any]] = [
    {"observable_id": "status", "sort": "categorical", "source": "kernel_transition"},
    {"observable_id": "goal_count", "sort": "integer", "source": "kernel_state"},
    {"observable_id": "goal_count_before", "sort": "integer", "source": "kernel_transition"},
    {"observable_id": "goal_count_after", "sort": "integer", "source": "kernel_transition"},
    {"observable_id": "goal_count_delta", "sort": "integer", "source": "kernel_transition"},
    {"observable_id": "closed_goal_delta", "sort": "integer", "source": "kernel_transition"},
    {"observable_id": "new_goal_count", "sort": "integer", "source": "kernel_transition"},
    {"observable_id": "new_mvar_count", "sort": "integer", "source": "kernel_transition"},
    {"observable_id": "typeclass_obligation_count", "sort": "integer", "source": "kernel_state"},
    {"observable_id": "typeclass_obligation_delta", "sort": "integer", "source": "kernel_transition"},
    {"observable_id": "local_context_count", "sort": "integer", "source": "kernel_state"},
    {"observable_id": "local_instance_count", "sort": "integer", "source": "kernel_state"},
    {"observable_id": "target_hash", "sort": "hash", "source": "kernel_state"},
    {"observable_id": "target_head", "sort": "categorical", "source": "kernel_state"},
    {"observable_id": "target_relation", "sort": "categorical", "source": "kernel_state"},
    {"observable_id": "domain_tags", "sort": "set[categorical]", "source": "kernel_state"},
    {"observable_id": "carrier_atoms", "sort": "set[categorical]", "source": "kernel_state"},
    {"observable_id": "error_signature", "sort": "categorical?", "source": "runtime"},
    {"observable_id": "elapsed_ms", "sort": "real", "source": "runtime"},
    {"observable_id": "json_bytes", "sort": "integer", "source": "runtime"},
    {"observable_id": "rss_mb", "sort": "real?", "source": "runtime"},
    {"observable_id": "replay_status", "sort": "categorical", "source": "runtime"},
]


def _json_dump(obj: dict[str, Any], path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def _json_load(path: str | Path | None) -> dict[str, Any]:
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _read_rows(path: str | Path | None) -> list[dict[str, Any]]:
    if not path:
        return []
    p = Path(path)
    if not p.exists():
        return []
    return [r for r in read_jsonl(p) if isinstance(r, dict)]


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        if isinstance(value, bool):
            return 1.0 if value else 0.0
        out = float(value)
    except Exception:
        return default
    if math.isnan(out) or math.isinf(out):
        return default
    return out


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, set):
        return list(value)
    return [value]


def _path_if_exists(path: str | Path | None) -> Path | None:
    if not path:
        return None
    p = Path(path)
    return p if p.exists() else None


def _first_existing(*paths: str | Path | None) -> Path | None:
    for path in paths:
        p = _path_if_exists(path)
        if p is not None:
            return p
    return None


def _ratio(num: float, den: float) -> float:
    if den <= 0:
        return 0.0
    return max(0.0, min(1.0, float(num) / float(den)))


def _score_avg(values: list[float]) -> float:
    vals = [max(0.0, min(1.0, _safe_float(v))) for v in values]
    return round(sum(vals) / len(vals), 4) if vals else 0.0


def _json_bytes(obj: Any) -> int:
    try:
        return len(json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8"))
    except Exception:
        return 0


def _row_identity(row: dict[str, Any]) -> tuple[str, str, str]:
    meta = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
    object_id = str(
        row.get("object_id")
        or row.get("premise_use_id")
        or row.get("premise_use_row_id")
        or meta.get("premise_use_id")
        or row.get("action_id")
        or row.get("before_state_id")
        or row.get("state_id")
        or stable_hash(row, 14)
    )
    context_id = str(
        row.get("context_id")
        or meta.get("context_id")
        or meta.get("context_pair")
        or row.get("context")
        or "__aggregate__"
    )
    transcript_id = str(row.get("transcript_id") or "btr_" + stable_hash({"object": object_id, "context": context_id, "row": row}, 14))
    return transcript_id, object_id, context_id


def _status_counter(rows: list[dict[str, Any]]) -> Counter:
    counts: Counter = Counter()
    for row in rows:
        status = (
            row.get("validation_status")
            or row.get("status")
            or ((row.get("validation") or {}) if isinstance(row.get("validation"), dict) else {}).get("status")
            or "unknown"
        )
        counts[str(status)] += 1
    return counts


def _class_member_count(row: dict[str, Any]) -> int:
    for key in ("member_count", "n_members", "support", "size"):
        if row.get(key) is not None:
            return max(0, int(_safe_float(row.get(key), 0.0)))
    for key in ("members", "premise_use_ids", "row_ids", "repair_object_ids"):
        values = row.get(key)
        if isinstance(values, list):
            return len(values)
    if isinstance(row.get("representatives"), list):
        return len(row["representatives"])
    return 1


def _row_tactic_text(row: dict[str, Any]) -> str:
    chunks: list[str] = []
    for key in ("tactic", "use_mode", "premise_id", "action_id", "representative_action_id", "premise_use_id", "text"):
        if row.get(key) is not None:
            chunks.append(str(row.get(key)))
    nf = row.get("premise_use_nf")
    if isinstance(nf, dict):
        for key in ("tactic", "text", "nf_text", "use_mode", "const_name", "nf_status"):
            if nf.get(key) is not None:
                chunks.append(str(nf.get(key)))
    return " ".join(chunks).lower()


def _is_macro_policy_row(row: dict[str, Any]) -> bool:
    text = _row_tactic_text(row)
    return any(tok in text for tok in ("simp", "omega", "aesop", "norm_num", "linarith", "ring", "nlinarith", "decide"))


def _is_structural_row(row: dict[str, Any]) -> bool:
    text = _row_tactic_text(row)
    return any(tok in text for tok in ("rfl", "intro", "constructor", "assumption", "trivial", "cases", "split", "exact"))


def _nf_status(row: dict[str, Any]) -> str:
    nf = row.get("premise_use_nf")
    if isinstance(nf, dict):
        return str(nf.get("nf_status") or nf.get("status") or "unknown")
    return str(row.get("nf_status") or "unknown")


def _is_typed_nf_status(status: str) -> bool:
    s = status.lower()
    if not s or s in {"unknown", "textual_stub", "text_stub", "raw_text", "tactic_text"}:
        return False
    return any(tok in s for tok in ("typed", "elaborated", "kernel", "instantiation", "const"))


def _matrix_metrics(fingerprint_rows: list[dict[str, Any]]) -> dict[str, Any]:
    keys = sorted(
        {
            str(k)
            for row in fingerprint_rows
            for k, v in ((row.get("fingerprint") or {}) if isinstance(row.get("fingerprint"), dict) else {}).items()
            if isinstance(v, (int, float)) and not isinstance(v, bool)
        }
    )
    if not fingerprint_rows or not keys:
        return {
            "effective_rank": None,
            "top_singular_value_ratio": None,
            "row_entropy": None,
            "column_entropy": None,
            "n_numeric_columns": len(keys),
            "status": "insufficient_numeric_fingerprint",
        }
    try:
        import numpy as np
    except Exception as exc:  # pragma: no cover - optional dependency guard
        return {
            "effective_rank": None,
            "top_singular_value_ratio": None,
            "row_entropy": None,
            "column_entropy": None,
            "n_numeric_columns": len(keys),
            "status": f"numpy_unavailable:{exc.__class__.__name__}",
        }
    mat = np.array(
        [
            [_safe_float(((row.get("fingerprint") or {}) if isinstance(row.get("fingerprint"), dict) else {}).get(k)) for k in keys]
            for row in fingerprint_rows
        ],
        dtype=float,
    )
    if mat.size == 0 or not np.any(mat):
        return {
            "effective_rank": 0.0,
            "top_singular_value_ratio": None,
            "row_entropy": 0.0,
            "column_entropy": 0.0,
            "n_numeric_columns": len(keys),
            "status": "zero_matrix",
        }
    sigma = np.linalg.svd(mat, full_matrices=False, compute_uv=False)
    energy = sigma * sigma
    total = float(np.sum(energy))
    if total <= 0:
        effective_rank = 0.0
        top_ratio = None
    else:
        p = energy / total
        entropy = float(-np.sum([x * math.log(x) for x in p if x > 0]))
        effective_rank = float(math.exp(entropy))
        top_ratio = float(np.max(energy) / total)
    row_energy = np.sum(mat * mat, axis=1)
    col_energy = np.sum(mat * mat, axis=0)

    def entropy_of(values: Any) -> float:
        total_v = float(np.sum(values))
        if total_v <= 0:
            return 0.0
        probs = values / total_v
        return float(-np.sum([x * math.log(x) for x in probs if x > 0]))

    return {
        "effective_rank": round(effective_rank, 6),
        "top_singular_value_ratio": round(top_ratio, 6) if top_ratio is not None else None,
        "row_entropy": round(entropy_of(row_energy), 6),
        "column_entropy": round(entropy_of(col_energy), 6),
        "n_numeric_columns": len(keys),
        "status": "ok",
    }


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


def _observable_kind(values: list[Any]) -> str:
    non_null = [v for v in values if v is not None]
    if not non_null:
        return "empty"
    if all(isinstance(v, bool) for v in non_null):
        return "boolean"
    if all(isinstance(v, (int, float, bool)) and not isinstance(v, str) for v in non_null):
        return "numeric"
    if any(isinstance(v, (list, tuple, set)) for v in non_null):
        return "set"
    return "categorical"


def _sanitize_id(text: Any, *, max_len: int = 80) -> str:
    s = "".join(ch if ch.isalnum() or ch in "._:-" else "_" for ch in str(text or "unknown"))
    while "__" in s:
        s = s.replace("__", "_")
    return s[:max_len].strip("_") or "unknown"


def _make_feature(definition: dict[str, Any], *, sort: str = "boolean") -> dict[str, Any]:
    fid = "feat_" + stable_hash(definition, 16)
    return {
        "schema_version": SCHEMA_FEATURE_CLOSURE,
        "feature_id": fid,
        "definition": definition,
        "sort": sort,
        "cost": {
            "compute": 0.1,
            "json_bytes": 0,
            "requires_full_state": False,
        },
        "support": {
            "n_rows": 0,
            "n_contexts": 0,
        },
        "canonical_status": "generated_feature_chart_not_canonical",
    }


def _eval_feature(defn: dict[str, Any], obs: dict[str, Any], cache: dict[str, float] | None = None) -> float:
    op = str(defn.get("op") or "")
    if op == "identity":
        value = obs.get(str(defn.get("observable")))
        return _safe_float(value)
    if op == "sign":
        value = _safe_float(obs.get(str(defn.get("observable"))))
        return 1.0 if value > 0 else (-1.0 if value < 0 else 0.0)
    if op == "threshold":
        value = _safe_float(obs.get(str(defn.get("observable"))))
        relation = str(defn.get("relation") or ">")
        target = _safe_float(defn.get("value"))
        ok = {
            ">": value > target,
            ">=": value >= target,
            "<": value < target,
            "<=": value <= target,
            "==": value == target,
            "!=": value != target,
        }.get(relation, False)
        return 1.0 if ok else 0.0
    if op == "bucket":
        value = _safe_float(obs.get(str(defn.get("observable"))))
        bucket = str(defn.get("bucket") or "")
        if bucket == "zero":
            return 1.0 if value == 0 else 0.0
        if bucket == "low":
            return 1.0 if 0 < value <= _safe_float(defn.get("upper"), 1.0) else 0.0
        if bucket == "high":
            return 1.0 if value > _safe_float(defn.get("lower"), 1.0) else 0.0
        if bucket == "negative":
            return 1.0 if value < 0 else 0.0
        return 0.0
    if op == "onehot":
        return 1.0 if str(obs.get(str(defn.get("observable")))) == str(defn.get("value")) else 0.0
    if op == "contains":
        values = {str(x) for x in _as_list(obs.get(str(defn.get("observable"))))}
        return 1.0 if str(defn.get("value")) in values else 0.0
    if op == "count":
        return float(len(_as_list(obs.get(str(defn.get("observable"))))))
    if op in {"conjunction", "interaction"}:
        vals = []
        for arg in defn.get("args") or []:
            if isinstance(arg, dict):
                vals.append(_eval_feature(arg, obs, cache=cache))
            elif cache is not None:
                vals.append(_safe_float(cache.get(str(arg))))
        if not vals:
            return 0.0
        if op == "conjunction":
            return 1.0 if all(v > 0 for v in vals) else 0.0
        prod = 1.0
        for v in vals:
            prod *= v
        return prod
    if op == "cost_normalize":
        numerator = _safe_float(obs.get(str(defn.get("observable"))))
        denom = max(1e-9, _safe_float(obs.get(str(defn.get("cost_observable") or "elapsed_ms")), 1.0))
        return numerator / denom
    return 0.0


def _feature_support(feature: dict[str, Any], transcripts: list[dict[str, Any]]) -> tuple[int, int]:
    contexts: set[str] = set()
    n = 0
    defn = feature.get("definition") if isinstance(feature.get("definition"), dict) else {}
    for tr in transcripts:
        obs = tr.get("raw_observables") if isinstance(tr.get("raw_observables"), dict) else {}
        value = _eval_feature(defn, obs)
        if abs(value) > 1e-15:
            n += 1
            contexts.add(str(tr.get("context_id") or "__aggregate__"))
    return n, len(contexts)


def build_feature_closure(
    transcripts_path: str | Path,
    out: str | Path,
    *,
    values_out: str | Path | None = None,
    report_out: str | Path | None = None,
    max_features: int = 512,
    max_category_values: int = 16,
    max_interaction_features: int = 24,
) -> dict[str, Any]:
    transcripts = _read_rows(transcripts_path)
    values_by_obs: dict[str, list[Any]] = defaultdict(list)
    for tr in transcripts:
        obs = tr.get("raw_observables") if isinstance(tr.get("raw_observables"), dict) else raw_observables_from_row(tr)
        for key, value in obs.items():
            values_by_obs[str(key)].append(value)

    features: list[dict[str, Any]] = []
    seen_defs: set[str] = set()

    def add_feature(definition: dict[str, Any], *, sort: str = "boolean") -> None:
        key = json.dumps(definition, sort_keys=True, ensure_ascii=False, default=str)
        if key in seen_defs:
            return
        seen_defs.add(key)
        features.append(_make_feature(definition, sort=sort))

    for obs_key in sorted(values_by_obs):
        values = values_by_obs[obs_key]
        kind = _observable_kind(values)
        if kind in {"empty"}:
            continue
        if kind == "numeric":
            add_feature({"op": "identity", "observable": obs_key}, sort="real")
            add_feature({"op": "sign", "observable": obs_key})
            add_feature({"op": "threshold", "observable": obs_key, "relation": ">", "value": 0})
            add_feature({"op": "threshold", "observable": obs_key, "relation": "<", "value": 0})
            add_feature({"op": "threshold", "observable": obs_key, "relation": "==", "value": 0})
            add_feature({"op": "bucket", "observable": obs_key, "bucket": "low", "upper": 10.0})
            add_feature({"op": "bucket", "observable": obs_key, "bucket": "high", "lower": 10.0})
        elif kind == "boolean":
            add_feature({"op": "threshold", "observable": obs_key, "relation": ">", "value": 0})
        elif kind == "set":
            add_feature({"op": "count", "observable": obs_key}, sort="integer")
            counts = Counter(str(x) for value in values for x in _as_list(value))
            for item, _ in counts.most_common(max_category_values):
                add_feature({"op": "contains", "observable": obs_key, "value": item})
        else:
            counts = Counter(str(v) for v in values if v is not None)
            for item, _ in counts.most_common(max_category_values):
                add_feature({"op": "onehot", "observable": obs_key, "value": item})

    for feature in features:
        n_rows, n_contexts = _feature_support(feature, transcripts)
        feature["support"] = {"n_rows": n_rows, "n_contexts": n_contexts}

    n_transcripts = max(1, len(transcripts))
    bool_features = [
        f
        for f in features
        if f.get("sort") == "boolean" and 0 < int((f.get("support") or {}).get("n_rows") or 0) < n_transcripts
    ]
    bool_features.sort(key=lambda f: (abs((int((f.get("support") or {}).get("n_rows") or 0) / n_transcripts) - 0.5), str(f.get("feature_id"))))
    for left_i, left in enumerate(bool_features[:max_interaction_features]):
        for right in bool_features[left_i + 1 : max_interaction_features]:
            add_feature({"op": "conjunction", "args": [left["definition"], right["definition"]]})
            if len(features) >= max_features:
                break
        if len(features) >= max_features:
            break

    for feature in features:
        if not (feature.get("support") or {}).get("n_rows"):
            n_rows, n_contexts = _feature_support(feature, transcripts)
            feature["support"] = {"n_rows": n_rows, "n_contexts": n_contexts}

    features = [
        f
        for f in features
        if int((f.get("support") or {}).get("n_rows") or 0) > 0
    ]
    features.sort(key=lambda f: (-int((f.get("support") or {}).get("n_rows") or 0), str(f.get("feature_id"))))
    features = features[: max(0, int(max_features))]
    write_jsonl(out, features)

    value_rows: list[dict[str, Any]] = []
    for tr in transcripts:
        obs = tr.get("raw_observables") if isinstance(tr.get("raw_observables"), dict) else raw_observables_from_row(tr)
        vals: dict[str, float] = {}
        for feature in features:
            defn = feature.get("definition") if isinstance(feature.get("definition"), dict) else {}
            vals[str(feature["feature_id"])] = _eval_feature(defn, obs, cache=vals)
        value_rows.append(
            {
                "schema_version": SCHEMA_FEATURE_VALUE,
                "transcript_id": tr.get("transcript_id"),
                "object_id": tr.get("object_id") or tr.get("source_row_id"),
                "source_row_id": tr.get("source_row_id") or tr.get("object_id"),
                "context_id": tr.get("context_id"),
                "raw_observables": obs,
                "generated_features": vals,
                "status": tr.get("status"),
                "canonical_status": "generated_feature_values_not_canonical",
            }
        )
    if values_out:
        write_jsonl(values_out, value_rows)

    report = {
        "schema_version": SCHEMA_FEATURE_CLOSURE,
        "transcripts": str(transcripts_path),
        "out": str(out),
        "values_out": str(values_out) if values_out else None,
        "n_transcripts": len(transcripts),
        "n_observable_keys": len(values_by_obs),
        "n_features": len(features),
        "max_features": max_features,
        "canonical_status": "feature_closure_is_generated_chart_not_canonical",
    }
    if report_out:
        _json_dump(report, report_out)
    return report


def _feature_values_by_object(value_rows: list[dict[str, Any]]) -> dict[str, dict[str, list[float]]]:
    out: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for row in value_rows:
        oid = str(row.get("object_id") or row.get("source_row_id") or "")
        if oid.startswith("obj_row_"):
            oid = oid[len("obj_row_") :]
        vals = row.get("generated_features") if isinstance(row.get("generated_features"), dict) else {}
        for fid, value in vals.items():
            out[oid][str(fid)].append(_safe_float(value))
    return out


def _taxonomy_duals(taxonomy_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for face in taxonomy_rows:
        support = (face.get("minimal_support") or {}).get("rows") if isinstance(face.get("minimal_support"), dict) else []
        out.append(
            {
                "dual_component_id": str(face.get("dual_component_id") or "xi_" + stable_hash(face, 12)),
                "target_face_id": str(face.get("taxonomy_face_id") or face.get("face_id") or stable_hash(face, 12)),
                "support_rows": [str(x) for x in _as_list(support)],
                "dual_source": str(face.get("dual_source") or "row_coker"),
                "retrieval_blockers": (face.get("status") or {}).get("retrieval_blockers") if isinstance(face.get("status"), dict) else [],
            }
        )
    return out


def select_features_for_dual_obstructions(
    feature_closure_path: str | Path,
    feature_values_path: str | Path,
    out: str | Path,
    *,
    report_out: str | Path | None = None,
    taxonomy_path: str | Path | None = None,
    max_selected_per_dual: int = 8,
    cost_weight: float = 0.05,
    mem_weight: float = 0.10,
    unsafe_weight: float = 0.25,
) -> dict[str, Any]:
    features = _read_rows(feature_closure_path)
    value_rows = _read_rows(feature_values_path)
    taxonomy_rows = _read_rows(taxonomy_path)
    by_object = _feature_values_by_object(value_rows)
    all_objects = set(by_object)
    duals = _taxonomy_duals(taxonomy_rows)
    if not duals:
        duals = [{"dual_component_id": "xi_global_feature_variance", "target_face_id": None, "support_rows": sorted(all_objects), "dual_source": "global_variance", "retrieval_blockers": []}]

    feature_by_id = {str(f.get("feature_id")): f for f in features}
    selected: list[dict[str, Any]] = []
    for dual in duals:
        face_objects = {str(x) for x in dual.get("support_rows") or []}
        face_objects |= {"obj_row_" + x for x in list(face_objects)}
        normalized_face = {x[len("obj_row_") :] if x.startswith("obj_row_") else x for x in face_objects}
        off_objects = all_objects - normalized_face
        scored: list[dict[str, Any]] = []
        for fid, feature in feature_by_id.items():
            face_vals = [
                _safe_float(v)
                for oid in normalized_face
                for v in by_object.get(oid, {}).get(fid, [])
            ]
            off_vals = [
                _safe_float(v)
                for oid in off_objects
                for v in by_object.get(oid, {}).get(fid, [])
            ]
            all_vals = face_vals + off_vals
            if not all_vals:
                continue
            if face_vals and off_vals:
                dual_support = abs(sum(face_vals) / len(face_vals) - sum(off_vals) / len(off_vals))
            else:
                mean = sum(all_vals) / len(all_vals)
                dual_support = sum((x - mean) ** 2 for x in all_vals) / max(1, len(all_vals))
            cost = _safe_float((feature.get("cost") or {}).get("compute"), 0.1)
            mem_risk = 1.0 if (feature.get("cost") or {}).get("requires_full_state") else 0.0
            unsafe_risk = 0.25 if "unsafe" in json.dumps(feature.get("definition"), sort_keys=True, default=str).lower() else 0.0
            score = dual_support - cost_weight * cost - mem_weight * mem_risk - unsafe_weight * unsafe_risk
            scored.append(
                {
                    "feature_id": fid,
                    "dual_support": float(dual_support),
                    "cost": float(cost),
                    "mem_risk": float(mem_risk),
                    "unsafe_risk": float(unsafe_risk),
                    "score": float(score),
                }
            )
        scored.sort(key=lambda r: (-_safe_float(r.get("score")), str(r.get("feature_id"))))
        for item in scored[: max(0, int(max_selected_per_dual))]:
            selected.append(
                {
                    "schema_version": SCHEMA_FEATURE_SELECTION,
                    "selected_feature_id": item["feature_id"],
                    "dual_component_id": dual["dual_component_id"],
                    "target_face_id": dual.get("target_face_id"),
                    "selection_reason": "max_dual_support_per_cost",
                    "dual_support": item["dual_support"],
                    "cost": item["cost"],
                    "score": item["score"],
                    "mem_risk": item["mem_risk"],
                    "unsafe_risk": item["unsafe_risk"],
                    "blocked": False,
                    "feature_definition": feature_by_id[item["feature_id"]].get("definition"),
                    "dual_source": dual.get("dual_source"),
                    "canonical_status": "selected_feature_witness_not_canonical",
                }
            )

    write_jsonl(out, selected)
    by_dual = Counter(str(r.get("dual_component_id")) for r in selected)
    report = {
        "schema_version": SCHEMA_FEATURE_SELECTION,
        "feature_closure": str(feature_closure_path),
        "feature_values": str(feature_values_path),
        "taxonomy": str(taxonomy_path) if taxonomy_path else None,
        "out": str(out),
        "n_features": len(features),
        "n_feature_value_rows": len(value_rows),
        "n_dual_components": len(duals),
        "n_selected": len(selected),
        "selected_by_dual": dict(sorted(by_dual.items())),
        "canonical_status": "feature_selection_report_not_canonical",
    }
    if report_out:
        _json_dump(report, report_out)
    return report


def _tower_action_candidate(row: dict[str, Any]) -> dict[str, Any]:
    kind = str(row.get("action_kind") or "")
    mapped = {
        "hard_split_face": "hard_split_carrier",
        "generate_context": "generate_separator_contexts",
        "generate_object": "generate_tower_object",
        "resolve_boundary": "generate_tower_object",
        "promote_face": "run_ablation",
        "block_retrieval": "block_retrieval",
    }.get(kind, kind or "inspect_tower")
    priority = _safe_float(row.get("priority"), 0.5)
    return {
        "action_kind": mapped,
        "target_face_id": row.get("target_face_id"),
        "target_dual_component_id": row.get("target_dual_component_id"),
        "reason": row.get("reason") or kind,
        "score": priority,
        "source_action_id": row.get("action_id"),
        "payload": row.get("payload") if isinstance(row.get("payload"), dict) else {},
    }


def build_dost_auto_plan(
    out: str | Path,
    *,
    selected_features_path: str | Path | None = None,
    taxonomy_path: str | Path | None = None,
    tower_next_actions_path: str | Path | None = None,
    tower_summary_path: str | Path | None = None,
    invariant_ledger_path: str | Path | None = None,
    cost_model_path: str | Path | None = None,
    compiled_experiment_out: str | Path | None = None,
    notebook_out: str | Path | None = None,
    max_actions: int = 12,
    kernel_state_mode: str = "features",
) -> dict[str, Any]:
    selected = _read_rows(selected_features_path)
    taxonomy = _read_rows(taxonomy_path)
    tower_actions = _read_rows(tower_next_actions_path)
    tower_summary = {}
    if tower_summary_path and Path(tower_summary_path).exists():
        tower_summary = json.loads(Path(tower_summary_path).read_text(encoding="utf-8"))

    candidates: list[dict[str, Any]] = [
        {
            "action_kind": "set_observation_policy",
            "kernel_state_mode": kernel_state_mode,
            "reason": "bounded_feature_transcript_default",
            "score": 0.94,
            "cost_canonical_claim": {
                "candidate_set": ["summary", "features", "full"],
                "chosen_min_cost_sufficient": kernel_state_mode == "features",
            },
        }
    ]
    if selected:
        best_support = max(_safe_float(r.get("dual_support")) for r in selected)
        candidates.append(
            {
                "action_kind": "generate_features",
                "reason": "selected_low_cost_dual_separators",
                "score": 0.65 + min(0.25, best_support),
                "payload": {"n_selected_features": len(selected)},
            }
        )
    for row in tower_actions:
        candidates.append(_tower_action_candidate(row))
    for face in taxonomy:
        status = face.get("status") if isinstance(face.get("status"), dict) else {}
        if status.get("retrieval_allowed"):
            candidates.append(
                {
                    "action_kind": "allow_retrieval",
                    "target_face_id": face.get("taxonomy_face_id"),
                    "target_dual_component_id": face.get("dual_component_id"),
                    "reason": "face_retrieval_gate_open",
                    "score": 0.52,
                }
            )

    candidates.sort(key=lambda r: (-_safe_float(r.get("score")), str(r.get("action_kind")), str(r.get("target_face_id"))))
    selected_actions = candidates[: max(1, int(max_actions))]
    blocked_actions = [
        {
            "action_kind": "full_kernel_state_in_apply",
            "reason": "memory_risk",
        }
    ]
    if any((face.get("status") or {}).get("retrieval_blockers") for face in taxonomy if isinstance(face.get("status"), dict)):
        blocked_actions.append({"action_kind": "retrieval_from_bad_faces", "reason": "retrieval_blockers_present"})

    plan = {
        "schema_version": SCHEMA_AUTO_PLAN,
        "plan_id": "plan_" + stable_hash(
            {
                "selected_features": selected_features_path,
                "taxonomy": taxonomy_path,
                "tower_next_actions": tower_next_actions_path,
                "kernel_state_mode": kernel_state_mode,
            },
            14,
        ),
        "inputs": {
            "selected_features": str(selected_features_path) if selected_features_path else None,
            "taxonomy": str(taxonomy_path) if taxonomy_path else None,
            "tower_next_actions": str(tower_next_actions_path) if tower_next_actions_path else None,
            "tower_summary": str(tower_summary_path) if tower_summary_path else None,
            "invariant_ledger": str(invariant_ledger_path) if invariant_ledger_path else None,
            "cost_model": str(cost_model_path) if cost_model_path else None,
        },
        "selected_actions": selected_actions,
        "blocked_actions": blocked_actions,
        "constraints": {
            "carrier_safe": True,
            "memory_budget": "bounded",
            "timeout_budget": "bounded",
            "no_full_state_unless_debug": True,
            "no_retrieval_from_bad_faces": True,
        },
        "tower_summary": {
            "n_faces": tower_summary.get("n_faces"),
            "n_next_actions": tower_summary.get("n_next_actions"),
        },
        "canonical_status": "dost_auto_plan_finite_chart_not_canonical",
    }
    _json_dump(plan, out)
    if compiled_experiment_out:
        compile_experiment_from_auto_plan(out, compiled_experiment_out, notebook_out=notebook_out)
    return plan


def compile_experiment_from_auto_plan(
    auto_plan_path: str | Path,
    out: str | Path,
    *,
    notebook_out: str | Path | None = None,
    base_command: str = "lean-rgc pipeline",
) -> dict[str, Any]:
    plan = json.loads(Path(auto_plan_path).read_text(encoding="utf-8"))
    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "",
        "# Generated from a finite DOST auto-plan chart.",
    ]
    cells: list[dict[str, Any]] = []

    def add_cmd(cmd: str) -> None:
        lines.append(cmd)
        cells.append({"cell_type": "code", "metadata": {}, "source": [cmd + "\n"], "outputs": [], "execution_count": None})

    for action in plan.get("selected_actions") or []:
        kind = str(action.get("action_kind") or "")
        if kind == "set_observation_policy":
            mode = str(action.get("kernel_state_mode") or "features")
            add_cmd(f"{base_command} --kernel-state-mode {mode} --dost-automation")
        elif kind == "generate_features":
            add_cmd("lean-rgc dost-feature-closure --transcripts bounded_transcripts.jsonl --out feature_closure.jsonl --values-out bounded_feature_transcripts.jsonl")
        elif kind == "generate_separator_contexts":
            add_cmd("lean-rgc separator-contexts --out separator_contexts.jsonl")
        elif kind == "generate_tower_object":
            add_cmd("lean-rgc obstruction-tower --out obstruction_tower --taxonomy-dir face_taxonomy --fingerprints bounded_feature_transcripts.jsonl")
        elif kind == "hard_split_carrier":
            face = action.get("target_face_id") or "unknown_face"
            add_cmd(f"# hard_split_carrier target_face_id={face}")
        elif kind == "block_retrieval":
            face = action.get("target_face_id") or "unknown_face"
            add_cmd(f"# block_retrieval target_face_id={face}")
        elif kind == "allow_retrieval":
            face = action.get("target_face_id") or "unknown_face"
            add_cmd(f"# allow face-mediated retrieval target_face_id={face}")
        elif kind == "run_ablation":
            face = action.get("target_face_id") or "unknown_face"
            add_cmd(f"# run_ablation target_face_id={face}")
        else:
            add_cmd(f"# inspect action_kind={kind}")

    p = Path(out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if notebook_out:
        nb = {
            "cells": cells,
            "metadata": {
                "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                "language_info": {"name": "python"},
            },
            "nbformat": 4,
            "nbformat_minor": 5,
        }
        Path(notebook_out).parent.mkdir(parents=True, exist_ok=True)
        Path(notebook_out).write_text(json.dumps(nb, indent=2, ensure_ascii=False), encoding="utf-8")
    return {
        "schema_version": SCHEMA_AUTO_PLAN,
        "auto_plan": str(auto_plan_path),
        "out": str(out),
        "notebook_out": str(notebook_out) if notebook_out else None,
        "n_commands": len(cells),
        "canonical_status": "compiled_experiment_is_plan_chart_not_canonical",
    }


def _discover_audit_inputs(
    run_dir: str | Path | None = None,
    **overrides: str | Path | None,
) -> dict[str, Path | None]:
    root = Path(run_dir) if run_dir else None
    pc = root / "premise_contextual" if root else None
    pca = root / "premise_contextual_audit" if root else None
    audit = root / "audit" if root else None
    taxonomy_dir = pc / "face_taxonomy" if pc else None
    tower_dir = pc / "obstruction_tower" if pc else None
    dost_dir = pc / "dost" if pc else None
    return {
        "server_summary_path": _first_existing(overrides.get("server_summary_path"), pca / "server_summary.json" if pca else None, pca / "summary.json" if pca else None, audit / "summary.json" if audit else None),
        "fingerprint_report_path": _first_existing(overrides.get("fingerprint_report_path"), pc / "premise_contextual_fingerprint_report.json" if pc else None),
        "fingerprints_path": _first_existing(overrides.get("fingerprints_path"), pc / "premise_contextual_fingerprints.jsonl" if pc else None),
        "premise_use_rows_path": _first_existing(overrides.get("premise_use_rows_path"), pc / "premise_use_rows.jsonl" if pc else None),
        "classes_path": _first_existing(overrides.get("classes_path"), pc / "premise_quotient_classes.jsonl" if pc else None),
        "validation_rows_path": _first_existing(overrides.get("validation_rows_path"), pc / "premise_quotient_validation_rows.jsonl" if pc else None),
        "validation_report_path": _first_existing(overrides.get("validation_report_path"), pc / "premise_quotient_validation_report.json" if pc else None),
        "taxonomy_path": _first_existing(overrides.get("taxonomy_path"), taxonomy_dir / "dual_face_taxonomy.jsonl" if taxonomy_dir else None),
        "taxonomy_report_path": _first_existing(overrides.get("taxonomy_report_path"), taxonomy_dir / "dual_face_taxonomy_report.json" if taxonomy_dir else None),
        "retrieval_faces_path": _first_existing(overrides.get("retrieval_faces_path"), taxonomy_dir / "retrieval_allowed_faces.jsonl" if taxonomy_dir else None),
        "tower_summary_path": _first_existing(overrides.get("tower_summary_path"), tower_dir / "tower_summary.json" if tower_dir else None),
        "tower_next_actions_path": _first_existing(overrides.get("tower_next_actions_path"), tower_dir / "tower_next_actions.jsonl" if tower_dir else None),
        "dost_report_path": _first_existing(overrides.get("dost_report_path"), dost_dir / "dost_obstruction_report.json" if dost_dir else None),
        "feature_selection_report_path": _first_existing(overrides.get("feature_selection_report_path"), dost_dir / "feature_selection_report.json" if dost_dir else None),
        "selected_features_path": _first_existing(overrides.get("selected_features_path"), dost_dir / "selected_features.jsonl" if dost_dir else None),
        "responses_path": _first_existing(overrides.get("responses_path"), pca / "responses.jsonl" if pca else None, audit / "responses.jsonl" if audit else None),
        "actions_path": _first_existing(overrides.get("actions_path"), root / "actions.jsonl" if root else None),
    }


def _server_summary_metrics(summary: dict[str, Any]) -> dict[str, Any]:
    n_responses = int(_safe_float(summary.get("n_responses") or summary.get("responses") or 0))
    n_failures = int(_safe_float(summary.get("n_failures") or summary.get("failures") or 0))
    timeout_count = int(_safe_float(summary.get("timeout_count") or summary.get("timeouts") or 0))
    timeout_rate = _safe_float(summary.get("timeout_rate"), _ratio(timeout_count, n_responses))
    cache_hits = int(_safe_float(summary.get("context_cache_hits") or summary.get("kernel_context_cache_hits") or 0))
    kernel_cache = bool(summary.get("kernel_context_cache") or summary.get("context_cache_enabled") or cache_hits > 0)
    baseline_missing = int(_safe_float(summary.get("baseline_missing") or summary.get("n_baseline_missing") or 0))
    source_check_calls = int(_safe_float(summary.get("source_check_calls") or summary.get("source_checks") or 0))
    return {
        "stateful_kernel_rpc": bool(summary.get("stateful_kernel_rpc_audit") or summary.get("kernel_rpc_enabled") or summary.get("kernel_rpc") or kernel_cache),
        "kernel_context_cache": kernel_cache,
        "context_cache_hits": cache_hits,
        "baseline_missing": baseline_missing,
        "timeout_rate": round(timeout_rate, 6),
        "n_responses": n_responses,
        "n_failures": n_failures,
        "source_check_calls": source_check_calls,
        "score": "green_pilot_yellow_certificate" if baseline_missing == 0 and timeout_rate <= 0.02 and n_failures == 0 else "yellow_or_red_substrate",
    }


def _proof_effect_from_responses(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "prove_rate": None,
            "partial_progress_rate": None,
            "fail_rate": None,
            "retrieved_success_rate": None,
            "oracle_topk_coverage": None,
            "cost_per_success": None,
        }
    success = 0
    partial = 0
    fail = 0
    total_cost = 0.0
    for row in rows:
        response = row.get("response") if isinstance(row.get("response"), dict) else {}
        cost = row.get("cost") if isinstance(row.get("cost"), dict) else {}
        status = str(row.get("status") or row.get("result_status") or response.get("status") or "").lower()
        if status == "success" or bool(row.get("success")):
            success += 1
        elif status == "partial":
            partial += 1
        elif status in {"fail", "failure", "timeout", "error"}:
            fail += 1
        total_cost += _safe_float(row.get("elapsed_ms") or cost.get("elapsed_ms"))
    n = len(rows)
    return {
        "prove_rate": round(success / n, 6),
        "partial_progress_rate": round(partial / n, 6),
        "fail_rate": round(fail / n, 6),
        "retrieved_success_rate": None,
        "oracle_topk_coverage": None,
        "cost_per_success": round(total_cost / success, 6) if success else None,
    }


def _failure_attributions(
    responses: list[dict[str, Any]],
    *,
    typed_nf_rate: float,
    retrieval_allowed_count: int,
    tower_next_actions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not responses:
        return []
    by_task: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in responses:
        task_id = str(row.get("task_id") or row.get("goal_state_id") or row.get("state_id") or row.get("candidate_id") or "unknown")
        by_task[task_id].append(row)
    action_kinds = Counter(str(r.get("action_kind") or r.get("next_action_kind") or r.get("kind") or "unknown") for r in tower_next_actions)
    out: list[dict[str, Any]] = []
    for task_id, task_rows in sorted(by_task.items()):
        has_success = any(str(r.get("status") or "").lower() == "success" or bool(r.get("success")) for r in task_rows)
        if has_success:
            failure_kind = "not_failed_or_oracle_success_exists"
            suspected_order = None
            suspected_face = None
        elif retrieval_allowed_count <= 0:
            failure_kind = "retrieval_blocked_no_safe_face"
            suspected_order = 0 if typed_nf_rate < 0.2 else 1
            suspected_face = "validated_retrieval_face_missing"
        elif typed_nf_rate < 0.2:
            failure_kind = "action_universe_poverty"
            suspected_order = 1
            suspected_face = "typed_premise_use_missing"
        else:
            failure_kind = "retrieval_or_scheduling_failure"
            suspected_order = None
            suspected_face = "face_matching_or_budget_issue"
        out.append(
            {
                "schema_version": SCHEMA_DOST_AUDIT,
                "task_id": task_id,
                "failed": not has_success,
                "oracle_success_exists": has_success,
                "retrieved_success_exists": None,
                "failure_kind": failure_kind,
                "suspected_missing_order": suspected_order,
                "suspected_missing_face": suspected_face,
                "evidence": {
                    "typed_nf_rate": round(typed_nf_rate, 6),
                    "retrieval_allowed_faces": retrieval_allowed_count,
                    "tower_next_action_counts": dict(sorted(action_kinds.items())),
                },
                "canonical_status": "finite_failure_attribution_chart_not_canonical",
            }
        )
    return out


def build_dost_audit_reports(
    out_dir: str | Path,
    *,
    run_dir: str | Path | None = None,
    server_summary_path: str | Path | None = None,
    fingerprint_report_path: str | Path | None = None,
    fingerprints_path: str | Path | None = None,
    premise_use_rows_path: str | Path | None = None,
    classes_path: str | Path | None = None,
    validation_rows_path: str | Path | None = None,
    validation_report_path: str | Path | None = None,
    taxonomy_path: str | Path | None = None,
    taxonomy_report_path: str | Path | None = None,
    retrieval_faces_path: str | Path | None = None,
    tower_summary_path: str | Path | None = None,
    tower_next_actions_path: str | Path | None = None,
    dost_report_path: str | Path | None = None,
    feature_selection_report_path: str | Path | None = None,
    selected_features_path: str | Path | None = None,
    responses_path: str | Path | None = None,
    actions_path: str | Path | None = None,
) -> dict[str, Any]:
    """Build finite DOST audit ledgers from existing run artifacts."""
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    inputs = _discover_audit_inputs(
        run_dir,
        server_summary_path=server_summary_path,
        fingerprint_report_path=fingerprint_report_path,
        fingerprints_path=fingerprints_path,
        premise_use_rows_path=premise_use_rows_path,
        classes_path=classes_path,
        validation_rows_path=validation_rows_path,
        validation_report_path=validation_report_path,
        taxonomy_path=taxonomy_path,
        taxonomy_report_path=taxonomy_report_path,
        retrieval_faces_path=retrieval_faces_path,
        tower_summary_path=tower_summary_path,
        tower_next_actions_path=tower_next_actions_path,
        dost_report_path=dost_report_path,
        feature_selection_report_path=feature_selection_report_path,
        selected_features_path=selected_features_path,
        responses_path=responses_path,
        actions_path=actions_path,
    )
    server_summary = _json_load(inputs["server_summary_path"])
    fingerprint_report = _json_load(inputs["fingerprint_report_path"])
    validation_report = _json_load(inputs["validation_report_path"])
    taxonomy_report = _json_load(inputs["taxonomy_report_path"])
    tower_summary = _json_load(inputs["tower_summary_path"])
    dost_report = _json_load(inputs["dost_report_path"])
    feature_selection_report = _json_load(inputs["feature_selection_report_path"])

    fingerprints = _read_rows(inputs["fingerprints_path"])
    premise_rows = _read_rows(inputs["premise_use_rows_path"])
    actions = _read_rows(inputs["actions_path"])
    row_universe = premise_rows if premise_rows else actions
    classes = _read_rows(inputs["classes_path"])
    validation_rows = _read_rows(inputs["validation_rows_path"])
    taxonomy = _read_rows(inputs["taxonomy_path"])
    retrieval_faces = _read_rows(inputs["retrieval_faces_path"])
    tower_next_actions = _read_rows(inputs["tower_next_actions_path"])
    selected_features = _read_rows(inputs["selected_features_path"])
    responses = _read_rows(inputs["responses_path"])

    kernel = _server_summary_metrics(server_summary)
    matrix_metrics = _matrix_metrics(fingerprints)
    validation_counts = Counter(validation_report.get("validation_status_counts") or {})
    validation_counts.update(_status_counter(validation_rows))
    class_sizes = [_class_member_count(row) for row in classes]
    n_classes = len(classes) or int(_safe_float(validation_report.get("n_classes") or taxonomy_report.get("n_classes") or 0))
    singleton_count = sum(1 for x in class_sizes if x <= 1)
    if not classes and validation_counts.get("singleton_vacuously_stable_not_informative"):
        singleton_count = int(validation_counts.get("singleton_vacuously_stable_not_informative"))
    split_count = int(validation_counts.get("split_suggested", 0))
    carrier_mixed_count = int(validation_counts.get("carrier_unsafe_mixed_class", 0))
    heldout_validated_count = int(validation_counts.get("heldout_validated_premise_class", 0))
    multi_member_classes = sum(1 for x in class_sizes if x > 1)
    validated_multi_member_rate = _ratio(heldout_validated_count, max(1, multi_member_classes))

    n_rows = len(fingerprints) or int(_safe_float(fingerprint_report.get("n_fingerprints") or fingerprint_report.get("n_rows") or 0))
    n_context_pairs = int(
        _safe_float(
            fingerprint_report.get("n_unique_context_pairs")
            or fingerprint_report.get("context_pairs")
            or fingerprint_report.get("n_context_pairs")
            or 0
        )
    )
    row_degenerate = bool(fingerprint_report.get("row_degenerate", False))
    column_degenerate = bool(fingerprint_report.get("column_degenerate", False))

    nf_statuses = Counter(_nf_status(row) for row in row_universe)
    typed_rows = sum(1 for row in row_universe if _is_typed_nf_status(_nf_status(row)))
    kernel_observed_rows = sum(1 for row in row_universe if "kernel" in _nf_status(row).lower())
    macro_rows = sum(1 for row in row_universe if _is_macro_policy_row(row))
    structural_rows = sum(1 for row in row_universe if _is_structural_row(row))
    n_row_universe = len(row_universe)
    typed_nf_rate = _ratio(typed_rows, n_row_universe)
    kernel_observed_nf_rate = _ratio(kernel_observed_rows, n_row_universe)
    macro_policy_fraction = _ratio(macro_rows, n_row_universe)
    structural_tactic_fraction = _ratio(structural_rows, n_row_universe)

    retrieval_allowed_count = len(retrieval_faces) or int(_safe_float(taxonomy_report.get("n_retrieval_allowed_faces") or 0))
    retrieval_blocker_counts = Counter(taxonomy_report.get("retrieval_blocker_counts") or {})
    dual_source_counts = Counter(taxonomy_report.get("dual_source_counts") or {})
    allowed_with_blockers = 0
    carrier_safe_allowed = 0
    for face in retrieval_faces:
        status = face.get("status") if isinstance(face.get("status"), dict) else {}
        blockers = _as_list(status.get("retrieval_blockers"))
        if blockers:
            allowed_with_blockers += 1
        if status.get("carrier_safe", False):
            carrier_safe_allowed += 1
    carrier_safe_retrieval_rate = _ratio(carrier_safe_allowed, len(retrieval_faces)) if retrieval_faces else 0.0

    tower_action_counts = Counter(str(row.get("action_kind") or row.get("next_action_kind") or row.get("kind") or "unknown") for row in tower_next_actions)
    tower_reason_counts = Counter(str(row.get("reason") or row.get("selection_reason") or row.get("next_reason") or "unknown") for row in tower_next_actions)
    promotion_counts = Counter(tower_summary.get("promotion_level_counts") or {})
    boundary_counts = Counter(tower_summary.get("boundary_status_counts") or {})
    proof_effect = _proof_effect_from_responses(responses)

    kernel_score = _score_avg(
        [
            1.0 if kernel["baseline_missing"] == 0 else 0.0,
            1.0 if kernel["timeout_rate"] <= 0.02 else 0.0,
            1.0 if kernel["n_failures"] == 0 else 0.0,
            1.0 if kernel["kernel_context_cache"] or kernel["stateful_kernel_rpc"] else 0.0,
        ]
    )
    typed_object_score = round(min(1.0, 0.7 * typed_nf_rate + 0.3 * kernel_observed_nf_rate), 4)
    quotient_quality_score = _score_avg(
        [
            validated_multi_member_rate,
            1.0 - _ratio(split_count, max(1, n_classes)),
            1.0 - _ratio(carrier_mixed_count, max(1, n_classes)),
            1.0 - _ratio(singleton_count, max(1, n_classes)),
            1.0 if retrieval_allowed_count > 0 else 0.0,
        ]
    )
    retrieval_safety_score = (
        _score_avg([1.0 if allowed_with_blockers == 0 else 0.0, carrier_safe_retrieval_rate, 1.0 if retrieval_allowed_count > 0 else 0.0])
        if retrieval_allowed_count > 0
        else 0.05
    )
    action_family_entropy = 0.0
    if n_row_universe:
        family_counts = [macro_rows, structural_rows, max(0, n_row_universe - macro_rows - structural_rows)]
        total = sum(family_counts)
        if total:
            probs = [c / total for c in family_counts if c > 0]
            action_family_entropy = -sum(p * math.log(p) for p in probs) / math.log(3)
    expressivity_score = round(min(1.0, 0.45 * typed_nf_rate + 0.25 * action_family_entropy + 0.30 * _ratio(retrieval_allowed_count, max(1, n_classes))), 4)
    boundary_resolved_rate = _ratio(boundary_counts.get("resolved", 0), sum(boundary_counts.values()))
    tower_score = round(min(1.0, 0.6 * boundary_resolved_rate + 0.4 * _ratio(sum(promotion_counts.values()), max(1, len(taxonomy)))), 4)
    btr_score = round(
        0.20 * kernel_score
        + 0.20 * typed_object_score
        + 0.20 * quotient_quality_score
        + 0.15 * retrieval_safety_score
        + 0.15 * expressivity_score
        + 0.10 * tower_score,
        4,
    )
    overall = "not_big_theorem_ready" if btr_score < 0.35 else ("pilot_ready_not_canonical" if btr_score < 0.65 else "candidate_ready_requires_replay")

    invariant_ledger = {
        "schema_version": SCHEMA_DOST_AUDIT,
        "kernel_substrate": kernel,
        "bivariate_matrix": {
            "n_rows": n_rows,
            "n_context_pairs": n_context_pairs,
            "row_degenerate": row_degenerate,
            "column_degenerate": column_degenerate,
            "effective_rank": matrix_metrics.get("effective_rank"),
            "top_singular_value_ratio": matrix_metrics.get("top_singular_value_ratio"),
            "row_entropy": matrix_metrics.get("row_entropy"),
            "column_entropy": matrix_metrics.get("column_entropy"),
            "score": "green_substrate" if n_rows and not row_degenerate and not column_degenerate else "yellow_or_red_substrate",
        },
        "class_quality": {
            "n_classes": n_classes,
            "split_suggested": split_count,
            "carrier_unsafe_mixed": carrier_mixed_count,
            "singleton_vacuous": singleton_count,
            "heldout_validated_multi_member": heldout_validated_count,
            "strict_retrieval_ready": retrieval_allowed_count > 0 and allowed_with_blockers == 0,
            "score": "green" if quotient_quality_score >= 0.7 else ("yellow" if quotient_quality_score >= 0.4 else "red"),
        },
        "canonical_status": "dost_audit_invariant_ledger_finite_chart_not_canonical",
    }

    blockers: list[dict[str, Any]] = []
    if carrier_mixed_count:
        blockers.append({"blocker": "carrier_unsafe_mixed_class", "count": carrier_mixed_count, "reason": "carrier safety is not yet a hard enough quotient constraint", "effect_on_proof": "unsafe or debt-producing actions can be retrieved as if equivalent", "next_action": "hard_split_carrier"})
    if split_count:
        blockers.append({"blocker": "split_suggested_overmerge", "count": split_count, "reason": "finite chart merges rows with heldout response diameter above threshold", "effect_on_proof": "representative retrieval becomes unstable across contexts", "next_action": "generate_separator_contexts"})
    if n_classes and _ratio(singleton_count, n_classes) >= 0.4:
        blockers.append({"blocker": "singleton_vacuous_classes", "count": singleton_count, "reason": "member_count=1 gives vacuous stability rather than class-level robustness", "effect_on_proof": "retrieval has witness actions but little generalization evidence", "next_action": "generate_face_neighbor_rows"})
    if typed_nf_rate < 0.3:
        blockers.append({"blocker": "textual_row_universe", "count": n_row_universe - typed_rows, "reason": "premise-use rows are not mostly typed/kernel-elaborated premise-use objects", "effect_on_proof": "the action universe remains local tactic pilot rather than theorem-indexed Mathlib proof search", "next_action": "generate_typed_premise_rows"})
    if retrieval_allowed_count <= 0:
        blockers.append({"blocker": "no_strict_retrieval_faces", "count": 0, "reason": "no heldout-validated carrier-safe faces passed the strict retrieval gate", "effect_on_proof": "face-mediated retrieval should remain blocked", "next_action": "block_retrieval"})
    if kernel.get("source_check_calls", 0) <= 0:
        blockers.append({"blocker": "proof_certificate_weak", "count": 0, "reason": "kernel-backed audit is present but source/replay certificate calls are absent or unknown", "effect_on_proof": "pilot observations should not be treated as final proof certificates", "next_action": "run_replay_certificate_audit"})

    proof_blocker_report = {
        "schema_version": SCHEMA_DOST_AUDIT,
        "primary_blockers": blockers,
        "blocker_counts": dict(sorted(Counter(b["blocker"] for b in blockers).items())),
        "canonical_status": "proof_blocker_report_finite_chart_not_canonical",
    }
    action_poverty_report = {
        "schema_version": SCHEMA_DOST_AUDIT,
        "row_universe": {
            "n_rows": n_row_universe,
            "nf_status_counts": dict(sorted(nf_statuses.items())),
            "macro_policy_fraction": round(macro_policy_fraction, 6),
            "structural_tactic_fraction": round(structural_tactic_fraction, 6),
            "typed_premise_use_fraction": round(typed_nf_rate, 6),
            "kernel_elaborated_instantiation_rate": round(kernel_observed_nf_rate, 6),
        },
        "tier_scores": {
            "tier0_local_close": None,
            "tier1_typed_premise": None,
            "tier2_lemma_like": None,
            "tier3_plan_like": None,
            "tier4_transfer_like": None,
        },
        "diagnosis": "action_universe_is_local_tactic_pilot_not_big_theorem_ready" if typed_nf_rate < 0.3 else "typed_action_universe_present_but_requires_tiered_benchmark",
        "canonical_status": "action_poverty_report_finite_chart_not_canonical",
    }
    retrieval_safety_report = {
        "schema_version": SCHEMA_DOST_AUDIT,
        "retrieval_allowed_faces": retrieval_allowed_count,
        "retrieval_used_bad_class_count": None,
        "retrieval_allowed_with_blockers": allowed_with_blockers,
        "carrier_safe_retrieval_rate": round(carrier_safe_retrieval_rate, 6),
        "retrieval_blocker_counts": dict(sorted(retrieval_blocker_counts.items())),
        "bad_class_retrieval_should_be_zero": True,
        "diagnosis": "retrieval_not_ready" if retrieval_allowed_count <= 0 else "retrieval_gate_has_candidate_faces",
        "canonical_status": "retrieval_safety_report_finite_chart_not_canonical",
    }
    big_theorem_readiness = {
        "schema_version": SCHEMA_DOST_AUDIT,
        "kernel_substrate_score": kernel_score,
        "typed_object_score": typed_object_score,
        "quotient_quality_score": quotient_quality_score,
        "retrieval_safety_score": round(retrieval_safety_score, 4),
        "expressivity_score": expressivity_score,
        "tower_score": tower_score,
        "weighted_score": btr_score,
        "overall": overall,
        "reason": [b["blocker"] for b in blockers],
        "canonical_status": "big_theorem_readiness_score_is_audit_heuristic_not_canonical",
    }

    diagnosis: list[str] = []
    if kernel_score >= 0.75:
        diagnosis.append("substrate_ok")
    if n_rows and not row_degenerate and not column_degenerate:
        diagnosis.append("row_universe_non_degenerate_but_sparse" if n_rows < 50 else "row_universe_non_degenerate")
    if typed_nf_rate < 0.3:
        diagnosis.append("typed_premise_use_missing")
    if carrier_mixed_count:
        diagnosis.append("carrier_safe_gate_needed")
    if retrieval_allowed_count <= 0:
        diagnosis.append("retrieval_not_ready")
    if overall == "not_big_theorem_ready":
        diagnosis.append("not_big_theorem_ready")

    audit_dashboard = {
        "schema_version": SCHEMA_DOST_AUDIT,
        "run_id": stable_hash({k: str(v) if v else None for k, v in inputs.items()}, 12),
        "substrate": {"kernel_rpc": kernel["stateful_kernel_rpc"], "baseline_missing": kernel["baseline_missing"], "timeout_rate": kernel["timeout_rate"], "cache_hits": kernel["context_cache_hits"], "replay_pass_rate": None},
        "row_universe": {"n_rows": n_rows, "typed_row_ratio": round(typed_nf_rate, 6), "singleton_rate": round(_ratio(singleton_count, max(1, n_classes)), 6), "row_rank": matrix_metrics.get("effective_rank"), "macro_policy_ratio": round(macro_policy_fraction, 6)},
        "context_universe": {"n_contexts": int(_safe_float(fingerprint_report.get("n_contexts") or 0)), "n_context_pairs": n_context_pairs, "split_suggested": split_count, "avg_sep_gain": None},
        "quotient_quality": {"n_classes": n_classes, "heldout_validated": heldout_validated_count, "split_suggested": split_count, "carrier_unsafe_mixed": carrier_mixed_count, "singleton_vacuous": singleton_count, "retrieval_allowed_classes": retrieval_allowed_count},
        "dost": {"n_faces": len(taxonomy) or int(_safe_float(taxonomy_report.get("n_taxonomy_faces") or 0)), "dual_source_counts": dict(sorted(dual_source_counts.items())), "tower_next_action_counts": dict(sorted(tower_action_counts.items())), "tower_next_reason_counts": dict(sorted(tower_reason_counts.items())), "retrieval_allowed_faces": retrieval_allowed_count, "promotion_levels": dict(sorted(promotion_counts.items()))},
        "proof_effect": proof_effect,
        "feature_selection": {"n_selected_features": len(selected_features) or int(_safe_float(feature_selection_report.get("n_selected") or 0)), "report": str(inputs["feature_selection_report_path"]) if inputs["feature_selection_report_path"] else None},
        "diagnosis": diagnosis,
        "canonical_status": "audit_dashboard_finite_chart_not_canonical",
    }
    failure_rows = _failure_attributions(responses, typed_nf_rate=typed_nf_rate, retrieval_allowed_count=retrieval_allowed_count, tower_next_actions=tower_next_actions)

    artifacts = {
        "invariant_ledger": out_path / "invariant_ledger.json",
        "proof_blocker_report": out_path / "proof_blocker_report.json",
        "action_poverty_report": out_path / "action_poverty_report.json",
        "big_theorem_readiness": out_path / "big_theorem_readiness.json",
        "dost_obstruction_report": out_path / "dost_obstruction_report.json",
        "retrieval_safety_report": out_path / "retrieval_safety_report.json",
        "audit_dashboard": out_path / "audit_dashboard.json",
        "failure_attribution": out_path / "failure_attribution.jsonl",
    }
    _json_dump(invariant_ledger, artifacts["invariant_ledger"])
    _json_dump(proof_blocker_report, artifacts["proof_blocker_report"])
    _json_dump(action_poverty_report, artifacts["action_poverty_report"])
    _json_dump(big_theorem_readiness, artifacts["big_theorem_readiness"])
    _json_dump(retrieval_safety_report, artifacts["retrieval_safety_report"])
    _json_dump(audit_dashboard, artifacts["audit_dashboard"])
    write_jsonl(artifacts["failure_attribution"], failure_rows)

    obstruction_report = {
        "schema_version": SCHEMA_DOST_AUDIT,
        "source_dost_report": dost_report,
        "primary_blockers": blockers,
        "dual_source_counts": dict(sorted(dual_source_counts.items())),
        "tower_next_action_counts": dict(sorted(tower_action_counts.items())),
        "selected_feature_count": len(selected_features) or int(_safe_float(feature_selection_report.get("n_selected") or 0)),
        "diagnosis": diagnosis,
        "canonical_status": "dost_obstruction_audit_report_finite_chart_not_canonical",
    }
    _json_dump(obstruction_report, artifacts["dost_obstruction_report"])
    summary = {
        "schema_version": SCHEMA_DOST_AUDIT,
        "out_dir": str(out_path),
        "inputs": {k: str(v) if v else None for k, v in inputs.items()},
        "n_blockers": len(blockers),
        "big_theorem_readiness": overall,
        "weighted_score": btr_score,
        "artifacts": {k: str(v) for k, v in artifacts.items()},
        "canonical_status": "dost_audit_report_bundle_finite_chart_not_canonical",
    }
    _json_dump(summary, out_path / "audit_report_summary.json")
    return summary


def run_dost_automation_stack(
    input_path: str | Path,
    out_dir: str | Path,
    *,
    taxonomy_path: str | Path | None = None,
    tower_next_actions_path: str | Path | None = None,
    tower_summary_path: str | Path | None = None,
    max_features: int = 512,
    max_selected_per_dual: int = 8,
    kernel_state_mode: str = "features",
) -> dict[str, Any]:
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    primitive_path = out_path / "primitive_observables.jsonl"
    transcripts_path = out_path / "bounded_transcripts.jsonl"
    feature_closure_path = out_path / "feature_closure.jsonl"
    feature_values_path = out_path / "bounded_feature_transcripts.jsonl"
    selected_path = out_path / "selected_features.jsonl"
    feature_report_path = out_path / "feature_selection_report.json"
    auto_plan_path = out_path / "auto_plan.json"
    compiled_path = out_path / "compiled_experiment.sh"
    notebook_path = out_path / "compiled_notebook_cells.ipynb"

    write_primitive_observables(primitive_path)
    bounded_report = build_bounded_transcripts(
        input_path,
        transcripts_path,
        primitive_observables_out=None,
        summary_out=out_path / "bounded_transcripts_report.json",
        kernel_state_mode=kernel_state_mode,
    )
    closure_report = build_feature_closure(
        transcripts_path,
        feature_closure_path,
        values_out=feature_values_path,
        report_out=out_path / "feature_closure_report.json",
        max_features=max_features,
    )
    selection_report = select_features_for_dual_obstructions(
        feature_closure_path,
        feature_values_path,
        selected_path,
        report_out=feature_report_path,
        taxonomy_path=taxonomy_path,
        max_selected_per_dual=max_selected_per_dual,
    )
    auto_plan = build_dost_auto_plan(
        auto_plan_path,
        selected_features_path=selected_path,
        taxonomy_path=taxonomy_path,
        tower_next_actions_path=tower_next_actions_path,
        tower_summary_path=tower_summary_path,
        compiled_experiment_out=compiled_path,
        notebook_out=notebook_path,
        kernel_state_mode=kernel_state_mode,
    )
    report = {
        "schema_version": "lean-rgc-dost-automation-stack-v57.0",
        "input": str(input_path),
        "out_dir": str(out_path),
        "n_transcripts": bounded_report.get("n_transcripts"),
        "n_features": closure_report.get("n_features"),
        "n_selected_features": selection_report.get("n_selected"),
        "n_auto_plan_actions": len(auto_plan.get("selected_actions") or []),
        "artifacts": {
            "primitive_observables": str(primitive_path),
            "bounded_transcripts": str(transcripts_path),
            "feature_closure": str(feature_closure_path),
            "feature_values": str(feature_values_path),
            "selected_features": str(selected_path),
            "feature_selection_report": str(feature_report_path),
            "auto_plan": str(auto_plan_path),
            "compiled_experiment": str(compiled_path),
            "compiled_notebook_cells": str(notebook_path),
        },
        "canonical_status": "dost_automation_stack_is_finite_chart_not_canonical",
    }
    _json_dump(report, out_path / "dost_obstruction_report.json")
    audit_summary = build_dost_audit_reports(
        out_path / "audit",
        fingerprints_path=input_path,
        taxonomy_path=taxonomy_path,
        tower_next_actions_path=tower_next_actions_path,
        tower_summary_path=tower_summary_path,
        dost_report_path=out_path / "dost_obstruction_report.json",
        feature_selection_report_path=feature_report_path,
        selected_features_path=selected_path,
    )
    report["artifacts"]["audit"] = str(out_path / "audit")
    report["artifacts"]["audit_dashboard"] = audit_summary["artifacts"]["audit_dashboard"]
    report["artifacts"]["big_theorem_readiness"] = audit_summary["artifacts"]["big_theorem_readiness"]
    _json_dump(report, out_path / "dost_obstruction_report.json")
    return report


__all__ = [
    "write_primitive_observables",
    "build_bounded_transcripts",
    "build_feature_closure",
    "select_features_for_dual_obstructions",
    "build_dost_auto_plan",
    "compile_experiment_from_auto_plan",
    "build_dost_audit_reports",
    "run_dost_automation_stack",
    "raw_observables_from_row",
]
