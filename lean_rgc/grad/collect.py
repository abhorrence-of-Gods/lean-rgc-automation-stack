"""Aggregate and archive per-wave audit rows for a grad or eval run.

The pilots only preserved episode summaries off-pod; the per-candidate
micro_audit rows survived by accident (a manual tarball). Wave rows are the
training table for every learned factor downstream (twist/PRM, RFT trace
mining, difficulty), so preservation is enforced here in code: the grad loop
calls ``collect_wave_rows`` + ``archive_run_artifacts`` at the end of every
run, and ``grad-collect`` exposes the same for eval-harness run dirs.

Torch-free by design: runs in the default CI tier.
"""

from __future__ import annotations

import json
import re
import tarfile
from pathlib import Path
from typing import Any

from ..schemas import read_jsonl, write_jsonl

SCHEMA_WAVE_ROWS = "lean-rgc-wave-rows-collect-v97.0"

_WAVE_DIR_RE = re.compile(r"^wave_(\d+|control)$")

# Run-level artifacts worth carrying into the archive when present.
_RUN_LEVEL_FILES = (
    "boundaries.jsonl",
    "llm_calls.jsonl",
    "episodes.jsonl",
    "grad_run.jsonl",
    "rft_traces.jsonl",
    "grad_summary.json",
)


def _wave_dirs(run_dir: Path) -> list[tuple[str, Path]]:
    out: list[tuple[str, Path]] = []
    for child in sorted(run_dir.iterdir()):
        if child.is_dir():
            m = _WAVE_DIR_RE.match(child.name)
            if m:
                out.append((m.group(1), child))
    # Numeric waves in order, wave_control last.
    out.sort(key=lambda kv: (kv[0] == "control", int(kv[0]) if kv[0].isdigit() else 0))
    return out


def collect_wave_rows(run_dir: str | Path, out_path: str | Path | None = None) -> dict[str, Any]:
    """Fold every wave_*/micro_audit.jsonl under ``run_dir`` into one table.

    Each row is annotated with ``wave_index`` (int, or -1 for wave_control)
    and ``wave_source`` (path relative to the run dir) so the aggregate stays
    joinable back to the raw artifacts. Returns a summary dict; the aggregate
    JSONL lands at ``out_path`` (default: ``<run_dir>/wave_rows.jsonl``).
    """
    run = Path(run_dir)
    out = Path(out_path) if out_path is not None else run / "wave_rows.jsonl"
    rows_out: list[dict[str, Any]] = []
    per_wave: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    for wave_key, wave_dir in _wave_dirs(run):
        micro = wave_dir / "micro_audit.jsonl"
        if not micro.exists():
            continue
        wave_index = int(wave_key) if wave_key.isdigit() else -1
        n = 0
        for row in read_jsonl(micro):
            if not isinstance(row, dict):
                continue
            annotated = dict(row)
            annotated["wave_index"] = wave_index
            annotated["wave_source"] = micro.relative_to(run).as_posix()
            rows_out.append(annotated)
            status = str(row.get("status") or "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
            n += 1
        per_wave[wave_dir.name] = n
    write_jsonl(out, rows_out)
    summary = {
        "schema_version": SCHEMA_WAVE_ROWS,
        "run_dir": str(run),
        "out": str(out),
        "n_rows": len(rows_out),
        "n_waves": len(per_wave),
        "per_wave": per_wave,
        "status_counts": status_counts,
        "canonical_status": "wave_rows_aggregate_witness_not_canonical",
    }
    return summary


def archive_run_artifacts(run_dir: str | Path, archive_path: str | Path | None = None) -> dict[str, Any]:
    """Tar wave dirs + run-level JSONL artifacts so one file leaves the pod.

    Includes every ``wave_*``/``wave_control`` directory's ``*.jsonl`` plus
    the run-level files in ``_RUN_LEVEL_FILES`` and ``wave_rows.jsonl`` when
    present. Returns a summary with the member list.
    """
    run = Path(run_dir)
    archive = Path(archive_path) if archive_path is not None else run / "wave_rows_archive.tar.gz"
    members: list[str] = []
    with tarfile.open(archive, "w:gz") as tf:
        for _, wave_dir in _wave_dirs(run):
            for f in sorted(wave_dir.glob("*.jsonl")):
                arcname = f.relative_to(run).as_posix()
                tf.add(f, arcname=arcname)
                members.append(arcname)
        for name in _RUN_LEVEL_FILES + ("wave_rows.jsonl",):
            f = run / name
            if f.exists():
                tf.add(f, arcname=name)
                members.append(name)
    return {
        "schema_version": SCHEMA_WAVE_ROWS,
        "archive": str(archive),
        "n_members": len(members),
        "members": members,
    }


def preserve_wave_rows(run_dir: str | Path) -> dict[str, Any]:
    """Collect + archive in one call; never raises.

    Used at the end of run_grad_loop: an archiver failure must not destroy
    the run summary, but it must be visible in it, so errors are returned as
    data instead of raised.
    """
    result: dict[str, Any] = {}
    try:
        result["collect"] = collect_wave_rows(run_dir)
    except Exception as e:  # pragma: no cover - defensive
        result["collect_error"] = f"{type(e).__name__}: {e}"
    try:
        result["archive"] = archive_run_artifacts(run_dir)
    except Exception as e:  # pragma: no cover - defensive
        result["archive_error"] = f"{type(e).__name__}: {e}"
    return result


def dump_summary(summary: dict[str, Any]) -> str:
    return json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True)


__all__ = [
    "SCHEMA_WAVE_ROWS",
    "archive_run_artifacts",
    "collect_wave_rows",
    "dump_summary",
    "preserve_wave_rows",
]
