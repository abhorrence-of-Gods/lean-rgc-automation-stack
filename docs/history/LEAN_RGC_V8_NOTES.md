# Lean-RGC v0.8 notes

This release adds the first production-data ingress layer for larger Lean-RGC runs.

## New commands

### `lean-rgc harvest-project`

Scans a Lean/Lake project and extracts simple `theorem`, `lemma`, and `example` declarations into JSONL task and premise files.

```bash
lean-rgc harvest-project \
  --root /path/to/lean/project \
  --out-tasks runs/harvest/tasks.jsonl \
  --out-premises runs/harvest/premises.jsonl \
  --max-decls 1000
```

This is a heuristic declaration harvester, not a Lean kernel parser.  It is intended to bootstrap micro-audit tasks and a lexical premise index.  Every harvested task/action must still pass Lean replay/audit.

### `lean-rgc shard-jsonl`

Splits JSONL data into stable shards for Vast/cluster jobs.

```bash
lean-rgc shard-jsonl \
  --input runs/harvest/tasks.jsonl \
  --out-dir runs/shards/tasks \
  --shards 16 \
  --key task_id
```

### `lean-rgc merge-jsonl`

Merges JSONL shards after distributed runs.

```bash
lean-rgc merge-jsonl \
  --inputs runs/shard_outputs/*/responses.jsonl \
  --out runs/merged/responses.jsonl \
  --dedup-key state_id
```

## Purpose

v8 is not a new tactic-selection algorithm.  It supports the next scale step:

1. harvest small/medium Lean projects into tasks/premises;
2. shard the harvested tasks;
3. run `lean-rgc pipeline` per shard with resume/cache;
4. merge responses/defects/audits;
5. train response/defect/carrier layers on the merged data.

The harvester deliberately treats declarations as charts.  Harvested task rows and premise rows are not canonical proof objects; they are entry points for micro-audit, response quotient discovery, and carrier generator tests.
