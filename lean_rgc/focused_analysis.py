from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
import json
import math

import numpy as np

from .schemas import read_jsonl


@dataclass
class ExposureBucket:
    key: str
    n: int = 0
    success: int = 0
    partial: int = 0
    fail: int = 0
    response_norm_sum: float = 0.0
    goal_response_sum: float = 0.0
    carrier_delta_sum: float = 0.0
    tactics: list[str] = field(default_factory=list)

    def update(self, row: dict[str, Any]) -> None:
        self.n += 1
        status = str(row.get("audit_status", row.get("status", "unknown")))
        if status == "success":
            self.success += 1
        elif status == "partial":
            self.partial += 1
        else:
            self.fail += 1
        rf = np.asarray(row.get("response_flat", []), dtype=float)
        self.response_norm_sum += float(np.linalg.norm(rf)) if rf.size else 0.0
        resp = row.get("response", {}) or {}
        self.goal_response_sum += sum(float(v) for k, v in resp.items() if str(k).startswith("goal."))
        self.carrier_delta_sum += sum(float(v) for v in (row.get("carrier_delta", {}) or {}).values())
        act = row.get("action", {}) or {}
        tactic = str(act.get("tactic", row.get("tactic", "")))
        if tactic and len(self.tactics) < 8 and tactic not in self.tactics:
            self.tactics.append(tactic)

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "n": self.n,
            "success": self.success,
            "partial": self.partial,
            "fail": self.fail,
            "success_rate": self.success / max(1, self.n),
            "partial_rate": self.partial / max(1, self.n),
            "mean_response_norm": self.response_norm_sum / max(1, self.n),
            "mean_goal_response": self.goal_response_sum / max(1, self.n),
            "mean_carrier_delta": self.carrier_delta_sum / max(1, self.n),
            "example_tactics": self.tactics,
        }


def _meta(row: dict[str, Any]) -> dict[str, Any]:
    return ((row.get("action") or {}).get("metadata") or {}) if isinstance(row.get("action"), dict) else {}


def exposure_key(row: dict[str, Any]) -> str:
    meta = _meta(row)
    prefix = str(meta.get("prefix_kind") or meta.get("prefix_id") or "identity")
    return prefix or "identity"


def core_key(row: dict[str, Any]) -> str:
    meta = _meta(row)
    return str(meta.get("core_tactic") or ((row.get("action") or {}).get("tactic")) or row.get("action_id") or "unknown")


def carrier_tags_key(row: dict[str, Any]) -> str:
    act = row.get("action") or {}
    tags = act.get("carrier_tags") or []
    if not tags:
        return "none"
    return ",".join(sorted(map(str, tags)))


def summarize_exposures(responses_path: str | Path, out: str | Path | None = None) -> dict[str, Any]:
    rows = read_jsonl(responses_path)
    by_prefix: dict[str, ExposureBucket] = {}
    by_core: dict[str, ExposureBucket] = {}
    by_tags: dict[str, ExposureBucket] = {}
    for r in rows:
        for table, key in [(by_prefix, exposure_key(r)), (by_core, core_key(r)), (by_tags, carrier_tags_key(r))]:
            table.setdefault(key, ExposureBucket(key)).update(r)
    report = {
        "n_rows": len(rows),
        "by_exposure_prefix": sorted([b.to_dict() for b in by_prefix.values()], key=lambda x: (-x["n"], x["key"])),
        "by_core_tactic": sorted([b.to_dict() for b in by_core.values()], key=lambda x: (-x["n"], x["key"])),
        "by_carrier_tags": sorted([b.to_dict() for b in by_tags.values()], key=lambda x: (-x["n"], x["key"])),
    }
    if out:
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report
