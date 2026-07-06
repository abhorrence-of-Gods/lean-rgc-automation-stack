"""Merge S'0 isolated re-audit verdicts back onto the historical row stores.

Joins verdicts_shard*.json (task_id, script, src, status) against every
row store on (task_id, action.tactic) and emits:
  - runs/s0_reaudit/corrected_labels.jsonl  (one line per historical row)
  - runs/s0_reaudit/reaudit_summary.json    (per-store mislabel accounting)

The verdicts come from a batch=1 bulk-lane run (isolated by construction;
note bulk_executor skips the isolation_confirmed flag at batch_size=1 —
provenance is carried by this file's `verdict_source` field instead).
"""
from __future__ import annotations

import argparse
import collections
import json
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# (store name, path, kind). Tarballs are scanned for member jsonl files.
ROW_STORES = [
    ("pilot", ROOT / "runs/vast_transitions/pilot_waves_backup.tar.gz", "tar:micro_audit.jsonl"),
    ("g1_prod_train", ROOT / "runs/g1_prod_train/extracted/wave_rows.jsonl", "jsonl"),
    ("g1_eval_C", ROOT / "runs/g1_eval_C/extracted/wave_rows.jsonl", "jsonl"),
    ("g1_eval_T", ROOT / "runs/g1_eval_T/extracted/wave_rows.jsonl", "jsonl"),
    ("g1re3_eval_C", ROOT / "runs/g1re3_eval_C/wave_rows_archive.tar.gz", "tar:wave_rows.jsonl"),
    ("g1re3_eval_T", ROOT / "runs/g1re3_eval_T/wave_rows_archive.tar.gz", "tar:wave_rows.jsonl"),
    ("g1re3_train", ROOT / "runs/g1re3_train/wave_rows_archive.tar.gz", "tar:wave_rows.jsonl"),
]


def iter_rows(path: Path, kind: str):
    if kind == "jsonl":
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    yield json.loads(line)
        return
    suffix = kind.split(":", 1)[1]
    with tarfile.open(path) as tar:
        for member in tar.getmembers():
            if member.isfile() and member.name.endswith(suffix):
                fh = tar.extractfile(member)
                for line in fh:
                    line = line.strip()
                    if line:
                        yield json.loads(line)


def pair_key(task_id: str, tactic: str) -> tuple[str, str]:
    return (task_id, (tactic or "").strip())


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verdicts", default=str(ROOT / "runs/s0_reaudit"),
                    help="dir containing verdicts_shard*.json")
    ap.add_argument("--out-dir", default=str(ROOT / "runs/s0_reaudit"))
    args = ap.parse_args()

    verdict_dir = Path(args.verdicts)
    shard_files = sorted(verdict_dir.glob("verdicts_shard*.json"))
    if not shard_files:
        raise SystemExit(f"no verdicts_shard*.json under {verdict_dir}")

    verdicts: dict[tuple[str, str], dict] = {}
    for sf in shard_files:
        for v in json.loads(sf.read_text(encoding="utf-8")):
            verdicts[pair_key(v["task_id"], v["script"])] = v
    print(f"verdict pairs: {len(verdicts)} from {len(shard_files)} shards")

    # Defect #6 (2026-07-06): the classifier passed sorry-holed scripts as
    # success in both lanes; demotions carry the Lean warning evidence.
    demo_path = verdict_dir / "defect6_demotions.json"
    if demo_path.exists():
        n_over = 0
        for d in json.loads(demo_path.read_text(encoding="utf-8")):
            key = pair_key(d["task_id"], d["script"])
            if key in verdicts:
                verdicts[key] = dict(verdicts[key], status="unsafe")
            else:
                verdicts[key] = {"task_id": d["task_id"], "script": d["script"],
                                 "src": d.get("src", "?"), "status": "unsafe"}
            n_over += 1
        print(f"defect #6 demotions applied: {n_over}")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    summary: dict[str, dict] = {}
    status_moves = collections.Counter()

    with open(out_dir / "corrected_labels.jsonl", "w", encoding="utf-8") as out:
        for store, path, kind in ROW_STORES:
            if not path.exists():
                summary[store] = {"skipped": f"missing {path.name}"}
                continue
            acc = collections.Counter()
            for row in iter_rows(path, kind):
                tactic = (row.get("action") or {}).get("tactic", "")
                key = pair_key(row["task_id"], tactic)
                v = verdicts.get(key)
                acc["rows"] += 1
                old = row.get("status")
                if v is None:
                    acc["unjoined"] += 1
                    continue
                new = v["status"]
                acc["joined"] += 1
                acc[f"old_{old}"] += 1
                if (old == "success") != (new == "success"):
                    acc["false_success" if old == "success" else "false_failure"] += 1
                status_moves[(old, new)] += 1
                out.write(json.dumps({
                    "store": store,
                    "task_id": row["task_id"],
                    "action_id": row.get("action_id"),
                    "state_id": row.get("state_id"),
                    "old_status": old,
                    "new_status": new,
                    "verdict_source": "s0_reaudit_batch1_isolated",
                }, ensure_ascii=False) + "\n")
            summary[store] = dict(acc)

    summary["status_moves"] = {f"{o}->{n}": c for (o, n), c in status_moves.most_common()}
    (out_dir / "reaudit_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
