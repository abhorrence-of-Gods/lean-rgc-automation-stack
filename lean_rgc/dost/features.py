from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import json

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


__all__ = [
    "build_feature_closure",
]
