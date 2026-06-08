from __future__ import annotations

from pathlib import Path
from typing import Any
import json

from .schemas import read_jsonl


def summarize_carrier_acceptance(path: str | Path) -> dict[str, Any]:
    rows = read_jsonl(path)
    n = len(rows)
    accepted = [r for r in rows if r.get("accepted")]
    by_kind: dict[str, dict[str, Any]] = {}
    for r in rows:
        k = str(r.get("context_kind", "unknown"))
        d = by_kind.setdefault(k, {"n": 0, "accepted": 0, "mean_margin": 0.0, "mean_delta": 0.0})
        d["n"] += 1
        d["accepted"] += int(bool(r.get("accepted")))
        d["mean_margin"] += float(r.get("coker_margin_proxy", 0.0))
        d["mean_delta"] += float(r.get("carrier_delta_l1", 0.0))
    for d in by_kind.values():
        if d["n"]:
            d["mean_margin"] /= d["n"]
            d["mean_delta"] /= d["n"]
            d["accept_rate"] = d["accepted"] / d["n"]
    return {
        "n": n,
        "accepted": len(accepted),
        "accept_rate": len(accepted) / max(1, n),
        "mean_margin": sum(float(r.get("coker_margin_proxy", 0.0)) for r in rows) / max(1, n),
        "mean_delta": sum(float(r.get("carrier_delta_l1", 0.0)) for r in rows) / max(1, n),
        "by_kind": by_kind,
    }


def write_carrier_acceptance_summary(path: str | Path, out: str | Path) -> dict[str, Any]:
    rep = summarize_carrier_acceptance(path)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")
    return rep
