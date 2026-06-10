from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import json
import math

from ..schemas import read_jsonl, stable_hash


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


__all__ = [
    "SCHEMA_PRIMITIVE_OBSERVABLE",
    "SCHEMA_BOUNDED_TRANSCRIPT",
    "SCHEMA_FEATURE_CLOSURE",
    "SCHEMA_FEATURE_VALUE",
    "SCHEMA_FEATURE_SELECTION",
    "SCHEMA_AUTO_PLAN",
    "SCHEMA_DOST_AUDIT",
    "DEFAULT_PRIMITIVE_OBSERVABLES",
    "_json_dump",
    "_json_load",
    "_read_rows",
    "_safe_float",
    "_as_list",
    "_path_if_exists",
    "_first_existing",
    "_ratio",
    "_score_avg",
    "_json_bytes",
    "_row_identity",
    "_status_counter",
    "_class_member_count",
    "_row_tactic_text",
    "_is_macro_policy_row",
    "_is_structural_row",
    "_nf_status",
    "_is_typed_nf_status",
    "_matrix_metrics",
]
