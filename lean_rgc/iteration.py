from __future__ import annotations

from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Iterable
import json
import shutil

from .schemas import read_jsonl, write_jsonl, TacticAction


def _row_key(row: dict[str, Any]) -> str:
    meta = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
    task_id = str(row.get("task_id") or meta.get("task_id") or "")
    tactic = str(row.get("tactic") or row.get("full_tactic") or "")
    # Prefer tactic+task keyed dedup because many generated actions have fresh ids.
    if tactic:
        return f"{task_id}\u241f{tactic}"
    return f"id\u241f{row.get('action_id','')}"


def _normalize_action_row(row: dict[str, Any], *, source: str | None = None) -> dict[str, Any]:
    """Return a TacticAction-compatible row while preserving task_id metadata."""
    row = dict(row)
    # Some acceptance rows wrap the action under metadata.action or action.
    if "tactic" not in row:
        action = row.get("action") if isinstance(row.get("action"), dict) else None
        if action is None:
            meta = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
            action = meta.get("action") if isinstance(meta.get("action"), dict) else None
        if action is not None:
            base = dict(action)
            # Promote task_id from acceptance row if present.
            if row.get("task_id") and not base.get("task_id"):
                base["task_id"] = row.get("task_id")
                base.setdefault("metadata", {})["task_id"] = row.get("task_id")
            row = base
    row.setdefault("action_id", row.get("id") or str(abs(hash(row.get("tactic", json.dumps(row, sort_keys=True))))))
    row.setdefault("tactic", row.get("full_tactic", ""))
    row.setdefault("tactic_class", row.get("class", "generated"))
    row.setdefault("carrier_tags", row.get("carrier_tags", []))
    row.setdefault("cost_estimate", row.get("cost", 1.0))
    row.setdefault("metadata", {})
    if source:
        row["metadata"].setdefault("merged_from", []).append(source)
    # Validate lightly through TacticAction dataclass conversion.
    try:
        return TacticAction.from_dict(row).to_dict()
    except Exception:
        # Keep best effort. Downstream loader will fail loudly if invalid.
        return row


def merge_action_files(inputs: Iterable[str | Path], out: str | Path, *, max_actions: int | None = None) -> dict[str, Any]:
    """Merge action jsonl files, deduplicating by task_id+tactic.

    This is intentionally chart-level: it does not claim actions are canonical,
    it only prepares the next round's candidate universe.
    """
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    stats: dict[str, int] = {}
    for path in inputs:
        if not path:
            continue
        p = Path(path)
        if not p.exists():
            continue
        rows = read_jsonl(p)
        stats[str(p)] = len(rows)
        for r in rows:
            nr = _normalize_action_row(r, source=p.name)
            k = _row_key(nr)
            if k in seen:
                continue
            seen.add(k)
            merged.append(nr)
            if max_actions is not None and len(merged) >= max_actions:
                break
        if max_actions is not None and len(merged) >= max_actions:
            break
    write_jsonl(out, merged)
    return {"out": str(out), "n_actions": len(merged), "sources": stats}


@dataclass
class RoundSummary:
    round: int
    run_dir: str
    actions_in: str | None
    actions_out: str | None
    n_actions_next: int = 0
    pipeline_summary: dict[str, Any] = field(default_factory=dict)
    merged_sources: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def summarize_pipeline_dir(run_dir: str | Path) -> dict[str, Any]:
    rd = Path(run_dir)
    summary = _load_json(rd / "pipeline_summary.json")
    audit = _load_json(rd / "audit" / "summary.json")
    gamma_rows = read_jsonl(rd / "gamma_audit.jsonl") if (rd / "gamma_audit.jsonl").exists() else []
    gamma = gamma_rows[-1] if gamma_rows else {}
    reg_acc = _load_json(rd / "registry_acceptance_report.json")
    carr_acc = _load_json(rd / "carrier_acceptance_summary.json")
    return {
        "run_dir": str(rd),
        "audit_n": audit.get("n") or (audit.get("responses") or {}).get("n_responses"),
        "audit_success_rate": (audit.get("statuses", {}).get("success", 0) / max(1, audit.get("n", 0))) if isinstance(audit.get("statuses"), dict) else audit.get("success_rate"),
        "mean_response_norm": audit.get("mean_response_norm"),
        "mean_carrier_delta": audit.get("mean_carrier_delta"),
        "gamma_cocycle_rel": gamma.get("cocycle_resid_rel"),
        "gamma_vs_persistence": gamma.get("gamma_vs_persistence_improvement"),
        "registry_accept_n": reg_acc.get("accepted") or reg_acc.get("n_accepted"),
        "registry_accept_mean_margin": reg_acc.get("mean_margin"),
        "carrier_accept_n": carr_acc.get("accepted") or carr_acc.get("n_accepted"),
        "pipeline_files": summary.get("pipeline_files", {}),
    }


def compare_pipeline_dirs(run_dirs: Iterable[str | Path], out_json: str | Path | None = None, out_csv: str | Path | None = None) -> list[dict[str, Any]]:
    rows = [summarize_pipeline_dir(p) for p in run_dirs]
    if out_json:
        Path(out_json).parent.mkdir(parents=True, exist_ok=True)
        Path(out_json).write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    if out_csv:
        import csv
        Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
        keys: list[str] = []
        for r in rows:
            for k in r:
                if k not in keys and k != "pipeline_files":
                    keys.append(k)
        with Path(out_csv).open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=keys)
            w.writeheader()
            for r in rows:
                w.writerow({k: r.get(k) for k in keys})
    return rows


__all__ = ["merge_action_files", "compare_pipeline_dirs", "summarize_pipeline_dir", "RoundSummary"]
