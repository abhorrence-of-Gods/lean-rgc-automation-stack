# Lean-RGC v24: Audit Database

v24 adds a SQLite-backed queryable mirror of Lean-RGC JSON/JSONL artifacts.

The JSONL artifacts remain the source files used by existing commands.  The
SQLite database is a structured audit substrate for scalable inspection,
lineage joins, response/carrier queries, and future scheduler logic.

## Commands

Build a database from a run directory:

```bash
lean-rgc audit-db-build \
  --run-dir runs/my_run \
  --db runs/my_run/audit.db
```

Query it:

```bash
lean-rgc audit-db-query \
  --db runs/my_run/audit.db \
  --sql "SELECT response_key, AVG(value) AS avg_v FROM response_values GROUP BY response_key" \
  --out-json runs/my_run/response_key_summary.json \
  --out-csv runs/my_run/response_key_summary.csv
```

Pipeline / iterate integration:

```bash
lean-rgc pipeline ... --audit-db
lean-rgc iterate ... --audit-db
```

Optional:

```bash
--audit-db-path path/to/audit.db
--audit-db-append
```

## Tables

The schema is intentionally simple and stable:

- `artifacts`
- `audit_rows`
- `response_rows`
- `response_values`
- `carrier_values`
- `action_rows`
- `acceptance_rows`
- `poms_rows`
- `lineage_nodes`
- `lineage_edges`
- `json_reports`

All source rows keep their raw JSON payload, so future schema migrations can
re-index without losing information.

## Status

The database is not a canonical quotient.  It is a queryable artifact chart over
finite audits.  Canonical promotion still requires the usual POMS conditions:
parent non-paid, dual certificate, and least repair.
