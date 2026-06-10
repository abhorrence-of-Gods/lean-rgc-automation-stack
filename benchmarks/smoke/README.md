# Smoke Benchmark

This corpus is the production smoke tier for Lean-RGC. It is intentionally tiny:
six Lean tasks and six core tactics that can run in dry-run CI and can later be
used with a real Lean backend.

Run it with:

```bash
lean-rgc benchmark smoke --out runs/benchmark_smoke --dry-run --run-db
```

The command runs the standard pipeline against `tasks.jsonl` and `actions.jsonl`,
builds `runs.db` when `--run-db` is set, and checks the run DB invariants.

