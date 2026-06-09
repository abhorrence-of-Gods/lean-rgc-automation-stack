from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import math

import numpy as np

from .schemas import read_jsonl, stable_hash


SCHEMA_RESPONSE_COMPLETION = "lean-rgc-response-completion-v58.0"


def _json_dump(obj: dict[str, Any], path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def _read_rows(path: str | Path | None) -> list[dict[str, Any]]:
    if not path:
        return []
    p = Path(path)
    if not p.exists():
        return []
    return [r for r in read_jsonl(p) if isinstance(r, dict)]


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        out = float(value)
    except Exception:
        return float(default)
    if math.isnan(out) or math.isinf(out):
        return float(default)
    return out


def _normalize_key(kind: str, metric: str) -> str:
    kind = str(kind or "").strip()
    metric = str(metric or "").strip()
    if not metric:
        return kind
    if kind in {"resp", "response"}:
        return metric
    if kind in {"carrier", "gamma", "cost", "audit", "goal", "type", "search"}:
        return f"{kind}.{metric}" if not metric.startswith(f"{kind}.") else metric
    return metric


def _fingerprint_key_to_response_key(key: str) -> str | None:
    parts = str(key).split("::")
    if len(parts) >= 3:
        return _normalize_key(parts[-2], parts[-1])
    if len(parts) == 2:
        return _normalize_key(parts[0], parts[1])
    return None


def response_map_from_row(row: dict[str, Any]) -> dict[str, float]:
    """Extract a response-like map from common Lean-RGC finite chart rows."""

    out: dict[str, float] = {}
    resp = row.get("response")
    if isinstance(resp, dict):
        for key, value in resp.items():
            out[str(key)] = _safe_float(value)
    flat = row.get("response_flat")
    keys = row.get("response_keys")
    if isinstance(flat, list) and isinstance(keys, list):
        for key, value in zip(keys, flat):
            out[str(key)] = _safe_float(value)
    for prefix, field in [
        ("carrier", "carrier_delta"),
        ("response", "response_embedding"),
        ("carrier", "carrier_embedding"),
        ("gamma", "gamma_embedding"),
    ]:
        obj = row.get(field)
        if isinstance(obj, dict):
            for key, value in obj.items():
                nkey = str(key) if prefix == "response" else _normalize_key(prefix, str(key))
                out[nkey] = _safe_float(value)
    for field, prefix in [
        ("response_summary", "response"),
        ("carrier_summary", "carrier"),
        ("gamma_summary", "gamma"),
        ("cost_summary", "cost"),
        ("audit_summary", "audit"),
    ]:
        obj = row.get(field)
        if isinstance(obj, dict):
            for key, value in obj.items():
                nkey = str(key) if prefix == "response" else _normalize_key(prefix, str(key))
                out[nkey] = _safe_float(value)
    fp = row.get("fingerprint")
    if isinstance(fp, dict):
        for key, value in fp.items():
            nkey = _fingerprint_key_to_response_key(str(key))
            if nkey:
                out[nkey] = _safe_float(value)
    return out


def _collect_rows(
    *,
    responses_path: str | Path | None = None,
    fingerprints_path: str | Path | None = None,
    action_geometry_path: str | Path | None = None,
    premise_registry_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in [responses_path, fingerprints_path, action_geometry_path, premise_registry_path]:
        rows.extend(_read_rows(path))
    return rows


def _parse_weights(weights: dict[str, Any] | str | Path | None, keys: list[str]) -> dict[str, float]:
    if weights is None:
        return {key: 1.0 for key in keys}
    obj: Any = weights
    if isinstance(weights, (str, Path)):
        text = str(weights)
        p = Path(text)
        obj = json.loads(p.read_text(encoding="utf-8")) if p.exists() else json.loads(text)
    if isinstance(obj, dict) and "weights" in obj and isinstance(obj["weights"], dict):
        obj = obj["weights"]
    if not isinstance(obj, dict):
        return {key: 1.0 for key in keys}
    return {key: _safe_float(obj.get(key), 1.0) for key in keys}


def build_response_completion(
    *,
    out: str | Path,
    responses_path: str | Path | None = None,
    fingerprints_path: str | Path | None = None,
    action_geometry_path: str | Path | None = None,
    premise_registry_path: str | Path | None = None,
    weights: dict[str, Any] | str | Path | None = None,
    topology: str = "weighted_projective",
    paid_cone_keys: list[str] | None = None,
    probe_family_id: str | None = None,
) -> dict[str, Any]:
    rows = _collect_rows(
        responses_path=responses_path,
        fingerprints_path=fingerprints_path,
        action_geometry_path=action_geometry_path,
        premise_registry_path=premise_registry_path,
    )
    maps = [response_map_from_row(row) for row in rows]
    keys = sorted({key for mp in maps for key in mp})
    key_weights = _parse_weights(weights, keys)
    paid = sorted(set(str(k) for k in (paid_cone_keys or []) if str(k) in set(keys)))
    if not paid:
        paid = sorted(k for k in keys if k.startswith("audit.") or k.startswith("cost."))
    norms = [float(np.linalg.norm(np.asarray([mp.get(k, 0.0) for k in keys], dtype=float))) for mp in maps] if keys else []
    completion = {
        "schema_version": SCHEMA_RESPONSE_COMPLETION,
        "probe_family_id": probe_family_id or "respcomp_" + stable_hash(
            {
                "responses": str(responses_path),
                "fingerprints": str(fingerprints_path),
                "action_geometry": str(action_geometry_path),
                "premise_registry": str(premise_registry_path),
                "keys": keys,
            },
            14,
        ),
        "response_keys": keys,
        "weights": key_weights,
        "topology": topology,
        "paid_cone_keys": paid,
        "n_source_rows": len(rows),
        "source_paths": {
            "responses": str(responses_path) if responses_path else None,
            "fingerprints": str(fingerprints_path) if fingerprints_path else None,
            "action_geometry": str(action_geometry_path) if action_geometry_path else None,
            "premise_registry": str(premise_registry_path) if premise_registry_path else None,
        },
        "finite_response_norm_summary": {
            "mean_l2": float(np.mean(norms)) if norms else 0.0,
            "max_l2": float(np.max(norms)) if norms else 0.0,
        },
        "canonical_status": "response_completion_is_weighted_projective_chart_not_canonical",
    }
    _json_dump(completion, out)
    return completion


def load_completion(path: str | Path | None) -> dict[str, Any]:
    if not path or not Path(path).exists():
        return {
            "schema_version": SCHEMA_RESPONSE_COMPLETION,
            "response_keys": [],
            "weights": {},
            "paid_cone_keys": [],
            "topology": "finite",
            "canonical_status": "implicit_empty_response_completion_chart_not_canonical",
        }
    return json.loads(Path(path).read_text(encoding="utf-8"))


__all__ = [
    "SCHEMA_RESPONSE_COMPLETION",
    "build_response_completion",
    "load_completion",
    "response_map_from_row",
]
