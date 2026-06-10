# Lean-RGC v36: Cost-aware Active Audit Scheduler

v36 adds a cost-aware active audit scheduling layer.

The scheduler is not a canonical selector. It is a finite audit chart that decides which candidate actions are worth spending Lean audit budget on, using historical response/carrier/audit data and candidate-local coker proxies.

## Commands

Standalone scheduler:

```bash
lean-rgc audit-schedule \
  --candidates candidates.jsonl \
  --db run/audit.db \
  --out scheduled_actions.jsonl \
  --out-rows schedule_rows.jsonl \
  --report-out schedule_report.json \
  --top-k 32
```

Existing active scheduler command remains available:

```bash
lean-rgc active-audit-schedule \
  --candidates candidates.jsonl \
  --db run/audit.db \
  --out-actions scheduled_actions.jsonl \
  --out-schedule schedule_rows.jsonl \
  --out-report schedule_report.json
```

## Pipeline / iterate integration

Use:

```bash
lean-rgc pipeline \
  --tasks examples/minimal_theorems.jsonl \
  --actions examples/core_tactics.jsonl \
  --out runs/scheduled \
  --dry-run \
  --audit-scheduler \
  --audit-db
```

and in iteration:

```bash
lean-rgc iterate \
  --tasks examples/minimal_theorems.jsonl \
  --actions examples/core_tactics.jsonl \
  --out runs/scheduled_iter \
  --dry-run \
  --rounds 2 \
  --audit-scheduler \
  --audit-db
```

The pipeline writes stage-local scheduler artifacts such as:

```text
audit/audit_scheduler/scheduled_actions.jsonl
audit/audit_scheduler/audit_schedule_rows.jsonl
audit/audit_scheduler/audit_schedule_report.json
```

Candidate stages, such as registry audit, qgen audit, carrier quotient audit, premise response audit, and contextual probe audit, pass through the same `_pipeline_audit` hook, so scheduler gating can apply uniformly.

## Score components

The scheduler combines finite-chart proxies:

- expected coker margin / response score,
- carrier need / carrier gain,
- uncertainty reduction,
- lineage/source novelty,
- prior success,
- estimated audit cost,
- timeout risk.

These are recorded under `metadata.active_audit_scheduler` for scheduled actions.

## Status

All scheduler outputs have chart status only:

```text
active_audit_schedule_chart_not_canonical
```

They are audit-budget allocation witnesses, not canonical proof objects. Canonical promotion still requires parent non-payment, dual certificate, and least repair.
