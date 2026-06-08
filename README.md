# Lean-RGC Automation Stack v0.4

This package is a small, dependency-light scaffold for **Lean-RGC**:
Response--Gamma--Carrier automation for Lean tactic experiments.

It treats tactic labels, goal strings, and proof paths as **charts**. The main
objects are proof-state defect vectors, tactic response vectors, carrier defects,
Gamma tail audits, and response quotient components.

## What v0.2 includes

- File-based Lean micro-audit harness with optional cache.
- Dry-run mode for Colab / CI without Lean installed.
- Textual proof-state defect extraction.
- Batch micro-audit with worker pool.
- Prototype response model from micro-audit responses.
- RGC-guided minimal tactic trajectory runner.
- Carrier defect analyzer and carrier context generator.
- Carrier coker projection proxy.
- Gamma trajectory audit.
- Response quotient discovery.
- Minimal Lake project template generator.

## Quick dry-run

```bash
python -m pip install -e .
lean-rgc audit \
  --tasks examples/minimal_theorems.jsonl \
  --actions examples/tactic_templates.jsonl \
  --out runs/dry_audit \
  --dry-run

lean-rgc train-response \
  --responses runs/dry_audit/responses.jsonl \
  --actions examples/tactic_templates.jsonl \
  --out runs/response_model.json

lean-rgc run-search \
  --tasks examples/minimal_theorems.jsonl \
  --response-model runs/response_model.json \
  --out runs/dry_search \
  --dry-run
```

## Real Lean / Lake use

Generate a minimal Lake project:

```bash
lean-rgc init-lake --out lean_playground --no-mathlib
```

With an existing Lake project:

```bash
lean-rgc batch-audit \
  --tasks examples/minimal_theorems.jsonl \
  --actions examples/tactic_templates.jsonl \
  --out runs/lean_audit \
  --workdir /path/to/lake/project \
  --lean-cmd "lake env lean" \
  --jobs 4 \
  --cache-dir runs/cache
```

## Main commands

```text
lean-rgc audit              # sequential tactic micro-audit
lean-rgc batch-audit        # parallel micro-audit
lean-rgc train-response     # fit response chart model
lean-rgc predict-response   # predict action responses
lean-rgc quotient           # response quotient clustering
lean-rgc carrier-generate   # propose carrier contexts from carrier residuals
lean-rgc carrier-coker      # finite carrier coker proxy
lean-rgc gamma-audit        # Gamma cocycle/tail audit on trajectories
lean-rgc run-search         # minimal RGC tactic trajectory runner
lean-rgc init-lake          # create Lean/Lake template
```

## Current limitations

- File-mode state parsing is a chart; persistent Lean server integration is still needed for structured proof states.
- Carrier generator proposes contexts, but coker-margin acceptance is still a proxy.
- Gamma is audit-only; do not use it for tactic control until it beats persistence on held-out trajectories.
- The trajectory runner is minimal and conservative; it is meant to test the R+Carrier loop, not to replace mature proof search.

## v0.3 additions

This package now includes larger-experiment utilities:

- `candidates`: state-dependent tactic candidate export.
- `make-transitions`: response rows to Gamma transition rows.
- `dataset-summary` and `split`: dataset hygiene.
- `carrier-accept`: micro-audit generated carrier contexts and accept by coker-margin proxy.
- `pipeline`: audit → response model → quotient → carrier generator in one command.
- `report`: aggregate run artifacts.

See `LEAN_RGC_V3_NOTES.md` for details.


## v0.4 additions

This release focuses on real Lean pilot stability:

- `pipeline` now supports `--lean-cmd`, `--workdir`, `--timeout-s`, `--cache-dir`, `--trace-state`, `--import-mode`, `--resume`, and `--flush-every`.
- The Lake template writes both a root module and a submodule and has a safer no-Mathlib mode.
- Task imports can be normalized with `--import-mode core|mathlib|auto|preserve`.
- `batch-audit` supports resume and periodic flush for 1k--10k audit pilots.
- Pipeline now also creates transitions and Gamma audit reports.

See `LEAN_RGC_V4_NOTES.md` for recommended commands.

## v0.5: Focused Carrier Exposure and AutoDefectMiner

v0.5 adds a carrier-normalizing frontend and automatic defect atom mining.

### Focused carrier exposure

`TacticCandidateGenerator` now creates state-dependent tactics by composing
structural exposure prefixes with core tactics. For example, a goal such as

```lean
⊢ ∀ n : Nat, n = n
```

will generate candidates such as

```lean
intros
rfl
```

with metadata separating the exposure prefix from the core action. The exposure
prefix is treated as a carrier chart, not as a primitive tactic component.

To inspect candidates:

```bash
lean-rgc candidates \
  --tasks examples/core_theorems.jsonl \
  --out runs/candidates.jsonl \
  --max-candidates 32
```

### Auto defect mining

Seed and mined defect atom registries can now be written and applied:

```bash
lean-rgc seed-defect-registry --out runs/defect_seed.json

lean-rgc mine-defects \
  --audits runs/audit/micro_audit.jsonl \
  --responses runs/audit/responses.jsonl \
  --out runs/defect_registry.json \
  --scores-out runs/defect_atom_scores.jsonl

lean-rgc auto-defects \
  --registry runs/defect_registry.json \
  --tasks examples/core_theorems.jsonl \
  --out runs/auto_defects.jsonl
```

The pipeline can run mining automatically:

```bash
lean-rgc pipeline \
  --tasks examples/core_theorems.jsonl \
  --out runs/core_pipeline_v5 \
  --dry-run \
  --import-mode core \
  --mine-defects
```


## v0.8 iterative loop

Generate a Lean-core pilot benchmark:

```bash
lean-rgc make-corebench --out runs/corebench_tasks.jsonl --n-nat 50 --n-prop 50 --n-bool 20 --n-eq 20 --import-mode core
```

Run a small self-improvement loop:

```bash
lean-rgc iterate --tasks runs/corebench_tasks.jsonl --out runs/iter_v8 --rounds 2 --dry-run --jobs 2 --max-actions 16 --candidate-mode state --fit-gamma
```

The loop performs audit → response model → defect mining → registry candidates → registry audit/acceptance → next-round action merge. It is finite-chart evidence and should be followed by real Lean audit before any claims about proof performance.

## Lean-RGC v0.8: iterative pilot loop

Generate a larger core Lean benchmark without Mathlib:

```bash
lean-rgc make-corebench --out runs/corebench.jsonl --n-nat 20 --n-prop 20 --n-bool 10 --n-eq 10 --import-mode core
```

Run a closed-loop dry pilot:

```bash
lean-rgc iterate --tasks runs/corebench.jsonl --out runs/iter_core_dry --dry-run --rounds 2 --jobs 2 --max-actions 12 --import-mode core --fit-gamma
```

This performs audit, response learning, defect mining, registry-guided candidate generation, registry-candidate audit, and accepted-action feedback into the next round.

## v0.9: Frontier-normalized focused carrier exposure

Use `--frontier-normalize` in `lean-rgc pipeline` or the standalone `lean-rgc expose-frontiers` command to audit structural exposure prefixes such as `intros` and materialize carrier-exposed frontier tasks.  This lets the response learner operate on core tactics after structural carrier exposure, rather than treating intro-like moves as ordinary ranked actions.

## v0.9 bulk audit bridge

For larger real-Lean pilots, use `bulk-audit` or `pipeline --audit-mode bulk` to compile many theorem/action probes in a single Lean file per batch.  This is faster than one process per probe and preserves the usual `micro_audit.jsonl`, `responses.jsonl`, and `defects.jsonl` outputs.

```bash
lean-rgc pipeline \
  --tasks examples/core_theorems.jsonl \
  --out runs/v9_core_bulk \
  --lean-cmd "lake env lean" \
  --workdir /path/to/lean/project \
  --import-mode core \
  --audit-mode bulk \
  --bulk-batch-size 64 \
  --candidate-mode state \
  --max-actions 32
```


## v13 QGEN-in-the-loop iteration

`lean-rgc iterate --qgen` now runs quotient-first generation after each round's base audit. With `--qgen-merge-actions`, coker-positive QGEN actions are merged into the next round's candidate universe. QGEN outputs remain witness/chart candidates until separately audited and promoted by POMS. See `LEAN_RGC_V13_QGEN_ITERATE_NOTES.md`.


## v14: qgen closure hooks

v14 connects qgen outputs back into the loop more tightly:

- `--qgen-registry-candidates` uses `qgen/qgen_defect_registry.json` as a registry for another candidate-generation stage.
- `--audit-qgen-registry-candidates` audits those candidates.
- `--qgen-registry-accept-coker` coker-accepts audited qgen-registry actions.
- `--carrier-matrix-merge-qgen` merges `qgen/qgen_carrier_incidence.jsonl` into the empirical carrier matrix before carrier-safe action filtering.

Example:

```bash
lean-rgc iterate   --tasks examples/minimal_theorems.jsonl   --actions examples/core_tactics.jsonl   --out runs/v14_qgen_closure   --dry-run   --rounds 2   --max-actions 8   --import-mode core   --qgen   --qgen-registry-candidates   --audit-qgen-registry-candidates   --qgen-registry-accept-coker   --carrier-matrix   --carrier-matrix-merge-qgen   --qgen-merge-actions
```

The new generated registry candidates and carrier-matrix patches remain chart/witness candidates, not canonical proof objects.

## v15 robust coker acceptance

Use `robust-coker-accept` to accept generated candidates with a held-out support
check instead of a single finite coker-margin proxy:

```bash
lean-rgc robust-coker-accept \
  --base-responses runs/round_00/audit/responses.jsonl \
  --candidate-responses runs/round_00/qgen_audit/responses.jsonl \
  --out-report runs/round_00/qgen_robust_acceptance_report.json \
  --out-actions runs/round_00/qgen_robust_accepted_actions.jsonl \
  --out-rows runs/round_00/qgen_robust_acceptance_rows.jsonl
```

The robust margin uses the train coker normal but charges the larger of train and
held-out support, plus uncertainty, cost, audit, and carrier penalties.  Outputs are
candidate witnesses, not canonical observables.


## v15: Robust QGEN acceptance and lineage

QGEN candidates now carry lineage metadata linking them back to coker residual coordinates.  A standalone robust acceptance command is available:

```bash
lean-rgc robust-accept-candidates \
  --base-responses audit/responses.jsonl \
  --candidate-responses qgen_audit/responses.jsonl \
  --shadow-responses heldout_qgen_audit/responses.jsonl \
  --out robust_rows.jsonl \
  --accepted-actions-out robust_actions.jsonl \
  --summary-out robust_summary.json
```

Pipeline-level `--qgen-robust-accept` uses repeated candidate audits and accepts by a lower-confidence-bound margin.  These are robust witness filters, not canonical promotion rules.


## v15 robust qgen acceptance

v15 adds a robust acceptance hook for qgen-generated candidates.  Use:

```bash
lean-rgc pipeline \
  --tasks examples/minimal_theorems.jsonl \
  --actions examples/core_tactics.jsonl \
  --out runs/v15_robust_qgen \
  --dry-run \
  --qgen \
  --audit-qgen-candidates \
  --qgen-accept-coker \
  --qgen-robust-accept
```

Standalone robust acceptance is available as:

```bash
lean-rgc robust-accept \
  --base-responses audit/responses.jsonl \
  --candidate-responses qgen_audit/responses.jsonl \
  --out qgen_robust_acceptance_rows.jsonl \
  --report-out qgen_acceptance_report.json \
  --accepted-actions-out qgen_accepted_actions.jsonl
```

The robust layer is still a witness/chart acceptance layer, not canonical promotion.


## v16 robust qgen loop

The qgen loop can now use held-out robust coker acceptance inside `pipeline` and `iterate`:

```bash
lean-rgc iterate \
  --tasks examples/minimal_theorems.jsonl \
  --actions examples/core_tactics.jsonl \
  --out runs/v16_qgen_robust \
  --dry-run \
  --rounds 2 \
  --qgen \
  --audit-qgen-candidates \
  --qgen-accept-coker \
  --qgen-robust-coker-accept
```

This writes `qgen_robust_accepted_actions.jsonl` and merges it into the next round before ordinary qgen accepted actions. Registry-derived qgen candidates support the analogous `--qgen-registry-robust-coker-accept` flag. Robust qgen acceptance is still a finite witness/chart acceptance, not canonical promotion.


### v16 qgen acceptance lineage

After qgen candidate audit and coker/robust-coker acceptance, the pipeline now writes an acceptance provenance chart:

```text
qgen_acceptance_lineage.json
```

Standalone command:

```bash
lean-rgc qgen-acceptance-lineage \
  --qgen-dir runs/round_00/qgen \
  --audit-responses runs/round_00/qgen_audit/responses.jsonl \
  --acceptance-rows runs/round_00/qgen_acceptance_rows.jsonl \
  --accepted-actions runs/round_00/qgen_accepted_actions.jsonl \
  --out runs/round_00/qgen_acceptance_lineage.json
```

The lineage graph connects coker residual coordinates to qgen contexts, micro-audit rows, acceptance records, and accepted actions. It is a provenance chart/witness, not a canonical proof object.

## v17 qgen realized-response and carrier-patch audit

v17 adds two closure diagnostics for qgen-generated witnesses.

First, `iterate` now writes a run-level qgen realized-response calibration chart when `--qgen` is enabled:

```text
qgen_realized_calibration.json
qgen_realized_calibration.csv
```

This compares qgen accepted actions from round `r` against base audit responses in round `r+1`.  It reports whether accepted qgen witnesses are re-audited and whether they still have positive goal / carrier response.  This is a finite realized-response chart, not a canonical promotion rule.

Standalone command:

```bash
lean-rgc qgen-realized-calibration \
  --run-dir runs/qgen_loop \
  --out-json runs/qgen_loop/qgen_realized_calibration.json \
  --out-csv runs/qgen_loop/qgen_realized_calibration.csv
```

Second, qgen carrier-incidence patches can now be audited against actual carrier deltas before being merged into a carrier matrix:

```bash
lean-rgc carrier-patch-audit \
  --patches runs/round_00/qgen/qgen_carrier_incidence.jsonl \
  --responses runs/round_00/qgen_audit/responses.jsonl \
  --out-report runs/round_00/qgen_carrier_patch_audit_report.json \
  --out-patches runs/round_00/qgen_carrier_incidence_audited.jsonl
```

Pipeline/iterate can use this audit before `--carrier-matrix-merge-qgen`:

```bash
--carrier-matrix \
--carrier-matrix-merge-qgen \
--carrier-matrix-qgen-audit-patches
```

This makes qgen carrier patches safer, but they remain carrier-incidence witnesses until promoted by the usual parent-non-paid / dual-certificate / least-repair logic.


### v18: POMS status and held-out carrier patch audit

- Added `lean-rgc poms-status` to classify qgen artifacts as witness / accepted witness / paid witness / carrier patch witness without promoting them to canonical objects.
- Added held-out split support to `carrier-patch-audit` via `--holdout-fraction` and `--require-heldout`.
- Added qgen realized-response and carrier-patch audit thresholds to `quality-gates`.
- `iterate` now writes `poms_status_report.json`, `poms_status_rows.jsonl`, and `poms_status_rows.csv` when qgen provenance exists.


### v19: POMS promotion calculus and qgen merge policy

v19 adds a conservative promotion calculus over the POMS status ledger.

```bash
lean-rgc poms-promote \
  --run-dir runs/qgen_loop \
  --evidence parent_evidence.jsonl \
  --out-json runs/qgen_loop/poms_promotion_report.json \
  --out-jsonl runs/qgen_loop/poms_promotion_rows.jsonl \
  --out-promoted-actions runs/qgen_loop/poms_promoted_actions.jsonl
```

Promotion requires explicit evidence for all three gates:

1. parent obstruction non-paid;
2. dual certificate;
3. least repair.

Without those, accepted qgen actions remain witness / paid-witness / open/forced candidates, not canonical objects.  Even when all three gates are present, the default output is `canonical_candidate`; `--declare-canonical` is required to label a row as a declared canonical observable.

`iterate` also supports qgen merge policy:

```bash
--qgen-merge-policy all          # default: robust + ordinary accepted qgen actions
--qgen-merge-policy robust-only  # only robust-coker accepted qgen actions
--qgen-merge-policy accepted-only
```

This lets a run keep ordinary finite-coker qgen actions as audit witnesses while only robust accepted candidates enter the next round.


## v20 Action Geometry Registry

v20 adds a finite action-geometry chart. Instead of searching only by tactic labels, audited actions can be embedded as

```text
E(a) = (response_embedding, gamma_embedding, carrier_embedding, cost, uncertainty)
```

Build the registry:

```bash
lean-rgc action-geometry-registry   --responses runs/round_00/audit/responses.jsonl   --actions examples/core_tactics.jsonl   --transitions runs/round_00/transitions.jsonl   --out runs/round_00/action_geometry.jsonl   --summary-out runs/round_00/action_geometry_summary.json
```

Retrieve by coker / carrier normals:

```bash
lean-rgc action-geometry-retrieve   --registry runs/round_00/action_geometry.jsonl   --response-normal '{"goal.eq": 1.0}'   --carrier-normal '{"missing_simp_lemma": 0.5}'   --out runs/round_00/action_geometry_selected.jsonl
```

Audit finite cocycle constraints:

```bash
lean-rgc action-cocycle-audit   --registry runs/round_00/action_geometry.jsonl   --compositions compositions.jsonl   --out runs/round_00/action_cocycles.jsonl
```

These outputs are chart/witness artifacts, not canonical actions. POMS promotion is still required for canonical status.

## v21 Lean Server Adapter

v21 adds a server-shaped adapter API for Lean audits.  The current built-in backends are `dry` and `file`.
The `file` backend keeps a persistent Python worker/session and project fingerprint, while delegating tactic execution to the existing file-based executor.  It is **not** yet a true Lean RPC server; it provides the stable contract needed for one.

```bash
lean-rgc lean-server-health --dry-run --lean-server-backend dry

lean-rgc audit \
  --tasks examples/minimal_theorems.jsonl \
  --actions examples/core_tactics.jsonl \
  --out runs/v21_server_audit \
  --dry-run \
  --lean-server \
  --lean-server-backend dry
```

See `LEAN_RGC_V21_LEAN_SERVER_ADAPTER_NOTES.md`.


## v21: Lean Server Adapter

Persistent-worker shaped audit bridge.  The current backends are `dry_run`, `file_fallback`, and a JSONL protocol wrapper for a future external Lean worker.  It writes standard audit artifacts plus `structured_states.jsonl` and `server_summary.json`.

```bash
lean-rgc lean-server-audit \
  --tasks examples/minimal_theorems.jsonl \
  --actions examples/core_tactics.jsonl \
  --out runs/server_audit \
  --dry-run \
  --import-mode core

lean-rgc pipeline \
  --tasks examples/minimal_theorems.jsonl \
  --actions examples/core_tactics.jsonl \
  --out runs/server_pipeline \
  --dry-run \
  --audit-mode server \
  --import-mode core
```

See `LEAN_RGC_V21_LEAN_SERVER_NOTES.md`.


### v22: Structured State Extraction

v22 adds `lean_rgc/structured_state.py` and a `structured-state-extract` CLI.  The server audit path now emits `structured_states.jsonl` in a stable schema with `GoalASTNode`, `LocalContextGraph`, `MetaVarGraph`, and `TypeclassObligationGraph` fields.  This remains a chart (`canonical_status = structured_state_chart_only_not_canonical`) until a kernel-backed Lean worker supplies real Expr/local-context data.

```bash
lean-rgc structured-state-extract   --tasks examples/minimal_theorems.jsonl   --audits runs/server_audit/micro_audit.jsonl   --out runs/server_audit/structured_states_v22.jsonl   --summary-out runs/server_audit/structured_state_summary.json
```


## v23: Action Geometry Integrated Retrieval

v23 connects the Action Geometry Registry to `pipeline` and `iterate`. The loop can now build an audited action-geometry chart, extract response/carrier normals from qgen, retrieve candidate actions by geometry score, audit them, and optionally run coker or robust-coker acceptance.

Example:

```bash
lean-rgc iterate   --tasks examples/minimal_theorems.jsonl   --actions examples/core_tactics.jsonl   --out runs/v23_action_geometry   --dry-run   --rounds 1   --max-actions 4   --import-mode core   --qgen   --action-geometry   --action-geometry-retrieve   --action-geometry-use-qgen-normals   --audit-action-geometry-candidates   --action-geometry-accept-coker   --action-geometry-robust-coker-accept   --action-geometry-merge-actions
```

Main artifacts include `action_geometry/action_geometry.jsonl`, `action_geometry/action_geometry_candidates.jsonl`, `action_geometry_audit/responses.jsonl`, and `action_geometry_robust_accepted_actions.jsonl`. These are finite-chart witnesses, not canonical proof objects.


## v23 Action Geometry integrated retrieval

The v20 Action Geometry Registry is now wired into `pipeline` and `iterate`.  Use:

```bash
lean-rgc pipeline \
  --tasks examples/minimal_theorems.jsonl \
  --actions examples/core_tactics.jsonl \
  --out runs/v23_action_geometry \
  --dry-run \
  --qgen \
  --action-geometry \
  --action-geometry-retrieve \
  --action-geometry-use-qgen-normals \
  --audit-action-geometry-candidates \
  --action-geometry-accept-coker \
  --action-geometry-robust-coker-accept
```

This builds `action_geometry/action_geometry.jsonl`, retrieves candidates using qgen/coker normals, audits them, and optionally applies coker / robust-coker acceptance.  In `iterate`, `--action-geometry-merge-actions` and `--action-geometry-merge-policy` control whether retrieved/accepted actions are fed into the next round.

These artifacts remain finite response-chart witnesses, not canonical objects.


## v23: Action Geometry integrated retrieval

v23 connects the Action Geometry Registry to the qgen / pipeline / iterate loop.
It builds an audited action embedding registry and retrieves actions using qgen
coker normals rather than only tactic labels.

Example:

```bash
lean-rgc iterate   --tasks examples/minimal_theorems.jsonl   --actions examples/core_tactics.jsonl   --out runs/v23_action_geometry   --dry-run   --rounds 1   --qgen   --action-geometry   --action-geometry-use-qgen-normals   --audit-action-geometry-candidates   --action-geometry-accept-coker   --action-geometry-merge-actions   --action-geometry-merge-policy all
```

Main artifacts include `action_geometry/action_geometry.jsonl`,
`action_geometry/action_geometry_candidates.jsonl`, and
`action_geometry_audit/responses.jsonl`.  These are finite response-chart
witnesses, not canonical proof objects.


## v24 Audit database

Build a queryable SQLite mirror of a Lean-RGC run:

```bash
lean-rgc audit-db-build \
  --run-dir runs/my_run \
  --db runs/my_run/audit.db
```

Run SQL queries over response/carrier/audit/POMS/lineage artifacts:

```bash
lean-rgc audit-db-query \
  --db runs/my_run/audit.db \
  --sql "SELECT response_key, AVG(value) AS avg_value FROM response_values GROUP BY response_key"
```

`pipeline` and `iterate` can build this database automatically with `--audit-db`.
The database is a queryable finite-audit chart, not a canonical quotient object.


### v25: Quotient-coordinate generation

Generate finite quotient-coordinate candidates directly from state-level coker normals, instead of only emitting residual label charts.

```bash
lean-rgc quotient-coordinates \
  --responses runs/round_00/audit/responses.jsonl \
  --out runs/round_00/quotient_coordinates
```

This writes `state_coker_normals.jsonl`, `quotient_coordinates.jsonl`, and `quotient_coordinate_action_scores.jsonl`.  The generated coordinates are linear functionals `q_phi(d)=dot(phi,d)` on the finite response quotient chart; they are not canonical observables unless later promoted by POMS.

### v26: Quotient Coordinate Loop

Generate finite quotient-coordinate candidates directly from coker residual normals and feed them back into qgen / registry / action-geometry loops.

```bash
lean-rgc pipeline \
  --tasks examples/minimal_theorems.jsonl \
  --actions examples/core_tactics.jsonl \
  --out runs/v26_qcoord \
  --dry-run \
  --qgen \
  --quotient-coordinates \
  --quotient-coordinate-validate \
  --audit-quotient-coordinate-candidates \
  --quotient-coordinate-accept-coker \
  --action-geometry \
  --action-geometry-use-quotient-normals
```

Main artifacts live under `quotient_coordinates/` and include `quotient_coordinates.jsonl`, `quotient_coordinate_defect_registry.json`, `quotient_coordinate_candidates.jsonl`, and `quotient_coordinate_validation_report.json`.  These are finite quotient-coordinate candidates, not canonical observables.

## v27: Persistent Lean Worker MVP

v27 adds a persistent JSONL worker with state ids, branch/rollback/get-state, and
a stable `apply_tactic` protocol.  It can be used via:

```bash
lean-rgc lean-worker --dry-run
lean-rgc lean-server-audit --tasks examples/minimal_theorems.jsonl --actions examples/core_tactics.jsonl --out runs/v27 --dry-run --server-backend persistent
```

The worker is persistent at the process/protocol/state-registry layer.  In file
mode it still delegates proof checking to `LeanExecutor`; a future Lean
kernel-native worker can implement the same JSONL protocol.


## v27 persistent Lean worker

The v27 stack adds a stateful proof-state worker protocol.  It supports server-side state ids, branch/rollback, tactic application, and structured-state chart output.

```bash
lean-rgc lean-persistent-probe --dry-run --out probe.json

lean-rgc persistent-worker --backend dry_run
```

`LeanServerAdapter(backend="persistent")` starts the worker and can be used by server-mode audit.  The in-tree backend is stateful at the RGC layer and replays proof prefixes through the dry-run or file executor; it is a migration substrate for a future kernel-resident Lean RPC worker.

All persistent worker states remain chart/witness artifacts, not canonical proof observables.


## v28: Kernel-backed Structured State Extraction

The structured-state layer now accepts Lean-kernel/proof-state JSON payloads and normalizes them into `lean-rgc-structured-state-v28.0`.

```bash
lean-rgc structured-state-extract \
  --kernel-jsonl kernel_states.jsonl \
  --out structured_states.jsonl \
  --summary-out structured_state_summary.json
```

The persistent worker also exposes a `kernel_state` JSONL command.  The in-tree dry-run/file worker returns a kernel-shaped compatibility payload; a future native Lean RPC worker can return true kernel `Expr` / local-context / metavariable JSON through the same protocol.

These states remain finite proof-state charts, not canonical observables.


## v29: Native Lean-side Worker MVP

The stack now includes an in-tree Lean-side JSONL worker scaffold. Use `lean-rgc lean-native-worker --print-source` to inspect the Lean source, and `--server-backend native` to request the native worker behind `lean-server-audit` / server-mode pipelines. This is a native protocol MVP and still returns finite proof-state charts, not canonical proof quotients. If Lean is unavailable, the adapter can fall back to the existing file executor.

See `LEAN_RGC_V29_NATIVE_LEAN_WORKER_NOTES.md` for native-worker protocol details.


## v29: Native Lean-side Kernel Worker MVP

The stack now includes a packaged Lean-side JSONL worker (`lean_rgc/native_lean/RGCKernelWorker.lean`) and a native worker launcher. Use `lean-rgc lean-native-worker --print-source` to inspect the Lean worker, and `--server-backend native` to request it behind server-mode audits. The v29 worker is a native Lean process and returns kernel-shaped structured-state payloads compatible with v28. It remains an MVP protocol layer, not a full TacticM/MVar RPC backend yet.


## v30 Native Source-Check Execution Path

v30 extends the packaged native Lean-side JSONL worker with a `source_check` execution mode.  In this mode, `apply_tactic` renders the current task/state/action as a temporary Lean theorem source and asks the project Lean executable to check it, returning stdout/stderr, proof-source hash/path, status, and a kernel-shaped payload.  This is still an MVP and not a full in-memory `MVarId` RPC, but it is the first native Lean-side checked execution path behind the stable server protocol.

Example:

```bash
lean-rgc lean-server-audit \
  --tasks examples/minimal_theorems.jsonl \
  --actions examples/core_tactics.jsonl \
  --out runs/native_source_check \
  --server-backend native \
  --native-exec-mode source_check
```

For protocol-only CI behavior:

```bash
lean-rgc lean-server-audit \
  --tasks examples/minimal_theorems.jsonl \
  --actions examples/core_tactics.jsonl \
  --out runs/native_heuristic \
  --server-backend native \
  --native-exec-mode heuristic
```

## v31: Contextual Response Congruence Mining

v31 adds finite contextual response fingerprints and action response quotient-class candidates.
Use `contextual-candidates` to generate finite `pre ; core ; post` probe actions, audit them, then
run `contextual-congruence` to mine candidate action classes.  This approximates the theoretical
operation-stable congruence `R(A ∘ C1 ∘ B) = R(A ∘ C2 ∘ B)` over a finite safe context family.
The result is a quotient chart / witness, not a canonical object.

## v31: Contextual Response Congruence Proxy

v31 adds a finite sampled approximation to operation-stable response congruence. It generates contextual probe actions of the form `left; core; right`, audits them, and clusters core actions by contextual response fingerprints.

```bash
lean-rgc contextual-candidates \
  --actions examples/core_tactics.jsonl \
  --out runs/ctx/contextual_candidates.jsonl

lean-rgc batch-audit \
  --tasks examples/minimal_theorems.jsonl \
  --actions runs/ctx/contextual_candidates.jsonl \
  --out runs/ctx/contextual_audit \
  --dry-run

lean-rgc contextual-congruence \
  --responses runs/ctx/contextual_audit/responses.jsonl \
  --actions runs/ctx/contextual_candidates.jsonl \
  --out runs/ctx/contextual_congruence
```

This is a finite chart/witness for the theoretical congruence
`C1 ~ C2 iff R(A ∘ C1 ∘ B) = R(A ∘ C2 ∘ B) for all safe A,B`; it is not a canonical quotient by itself.

## v31: Contextual Response Congruence Proxy

v31 adds a finite proxy for the operation-stable response congruence

```text
C1 ~ C2 iff R(A ∘ C1 ∘ B) = R(A ∘ C2 ∘ B) for all safe A,B.
```

The implemented object is not the full universal congruence; it is a finite contextual chart built from audited response rows.

Standalone:

```bash
lean-rgc contextual-response-congruence \
  --responses runs/round_00/audit/responses.jsonl \
  --out runs/round_00/contextual_congruence
```

Pipeline / iterate:

```bash
lean-rgc pipeline ... --contextual-congruence
lean-rgc iterate ... --contextual-congruence
```

Outputs:

```text
contextual_response_congruence_report.json
contextual_fingerprints.jsonl
response_congruence_classes.jsonl
response_congruence_representatives.jsonl
```

The output classes are finite response-quotient candidates / witnesses, not canonical observables.

## v32 Contextual probe generation

`lean-rgc pipeline` and `lean-rgc iterate` now support finite contextual probe generation for approximating operation-stable response congruence.

Example:

```bash
lean-rgc iterate \
  --tasks examples/minimal_theorems.jsonl \
  --actions examples/core_tactics.jsonl \
  --out runs/v32_contextual \
  --dry-run \
  --rounds 2 \
  --contextual-probes \
  --audit-contextual-probe-candidates \
  --contextual-probe-congruence \
  --contextual-probe-accept-coker \
  --contextual-probe-robust-coker-accept \
  --contextual-probe-merge-actions
```

This generates `A∘C∘B`-style contextual probe actions, audits them, mines finite contextual fingerprints, and optionally accepts / merges the resulting actions. The output is a finite chart/witness for response congruence, not a canonical quotient.


## v33 Response Quotient Registry

Builds a finite response-quotient registry from contextual congruence classes and optionally projects action pools to class representatives. This is a sampled chart of `Q^R = Act/sim_R`, not a canonical quotient by itself.

```bash
lean-rgc response-quotient-registry \
  --congruence-dir runs/round_00/contextual_probes/contextual_probe_congruence \
  --actions examples/core_tactics.jsonl \
  --out runs/round_00/response_quotient

lean-rgc response-quotient-project-actions \
  --actions examples/core_tactics.jsonl \
  --registry runs/round_00/response_quotient/response_quotient_registry.json \
  --out runs/round_00/response_quotient_projected_actions.jsonl
```

Use with pipeline / iterate via `--response-quotient-registry` and `--response-quotient-project-actions`.


## v33: Response Quotient Registry

V33 adds `response-quotient-registry`, which turns finite contextual response-congruence classes into an explicit action-to-class-to-representative registry.  It connects to `pipeline` / `iterate` through `--response-quotient-registry`, `--response-quotient-project-actions`, and `--response-quotient-merge-actions`.  This is a finite sampled chart of the operation-stable response quotient, not a canonical quotient by itself.


## v34: Carrier Quotient Mining

Carrier algebra auto-generation now has a finite-chart implementation via `lean-rgc carrier-quotient`. It mines carrier coker residuals into carrier quotient coordinate candidates `q^C_phi(c)=<phi,c>`, emits candidate actions, incidence patches, and a defect-registry readout. These are witness charts, not canonical observables.

## v34: Carrier Quotient Mining

v34 adds a finite carrier-coker mining layer.  Instead of treating the hand-written
carrier atoms as primitive, it mines state-level carrier coker normals and creates
carrier quotient coordinate candidates `q_phi^C(c)=dot(phi,c)`.

```bash
lean-rgc carrier-quotient \
  --responses runs/round_00/audit/responses.jsonl \
  --out runs/round_00/carrier_quotient \
  --validate
```

Pipeline integration:

```bash
lean-rgc pipeline \
  --tasks examples/minimal_theorems.jsonl \
  --actions examples/core_tactics.jsonl \
  --out runs/v34_carrier_quotient \
  --dry-run \
  --carrier-quotient \
  --carrier-quotient-validate
```

The generated `carrier_quotient_coordinates.jsonl`, `carrier_quotient_defect_registry.json`,
`carrier_quotient_candidates.jsonl`, and `carrier_quotient_incidence_patches.jsonl` are
finite carrier-quotient charts/witnesses, not canonical observables.

## v34: Carrier Quotient Mining

v34 adds carrier algebra auto-generation at the finite-chart level.  It mines carrier coker residuals from `carrier_delta` / `defect_before.carrier` rows and generates carrier quotient-coordinate candidates:

```bash
lean-rgc carrier-quotient \
  --responses runs/round_00/audit/responses.jsonl \
  --out runs/round_00/carrier_quotient \
  --validate
```

`pipeline` also supports:

```bash
--carrier-quotient
--carrier-quotient-validate
--audit-carrier-quotient-candidates
--carrier-quotient-accept-coker
--carrier-quotient-robust-coker-accept
```

The output includes `carrier_quotient_coordinates.jsonl`, `carrier_quotient_defect_registry.json`, and `carrier_quotient_incidence_patches.jsonl`.  These are candidate charts / witnesses, not canonical carrier observables.


## v34 Carrier Quotient Mining

Carrier algebra auto-generation begins with `lean-rgc carrier-quotient`.  It mines carrier coker normals from audited carrier responses and emits finite carrier quotient-coordinate candidates, defect-registry candidates, incidence patches, and action candidates.  Pipeline/iterate flags include `--carrier-quotient`, `--audit-carrier-quotient-candidates`, `--carrier-quotient-accept-coker`, `--carrier-quotient-robust-coker-accept`, and `--carrier-quotient-merge-actions`.  Outputs remain witness/chart candidates, not canonical observables.

## v35: Premise Response Quotient Retrieval

v35 adds response-based premise retrieval.  Lexical/semantic premise search remains
only a candidate generator; the selector is an audited premise-use response class.

Build a premise response registry after premise candidate audit:

```bash
lean-rgc premise-response-registry \
  --responses runs/round_00/premise_audit/responses.jsonl \
  --actions runs/round_00/premise_actions.jsonl \
  --out runs/round_00/premise_response/premise_response_registry.jsonl
```

Retrieve premise-use actions by response/carrier normals:

```bash
lean-rgc premise-response-retrieve \
  --registry runs/round_00/premise_response/premise_response_registry.jsonl \
  --response-normal '{"goal.eq": 1.0}' \
  --out runs/round_00/premise_response_retrieved.jsonl \
  --out-actions runs/round_00/premise_response_actions.jsonl
```

Mine finite premise response quotient classes:

```bash
lean-rgc premise-quotient-mine \
  --registry runs/round_00/premise_response/premise_response_registry.jsonl \
  --out runs/round_00/premise_response/premise_quotient
```

Pipeline hook:

```bash
lean-rgc pipeline ... \
  --premise-index \
  --audit-premise-candidates \
  --premise-response-registry \
  --premise-response-retrieve \
  --premise-quotient-mine \
  --audit-premise-response-candidates
```

The v35 premise registry is a finite response chart, not a canonical premise quotient.


## v36: Cost-aware Active Audit Scheduler

Adds `audit-schedule` and `active-audit-schedule` commands for prioritizing candidate actions before micro-audit using expected coker margin, carrier need, uncertainty reduction, lineage novelty, prior success, and audit cost. Scheduler outputs are finite charts/witnesses and are not canonical contexts until audited and promoted by POMS.


`pipeline --audit-scheduler` and `iterate --audit-scheduler` route candidate action files through the scheduler before each audit stage.

## v36: Cost-aware Active Audit Scheduler

v36 adds `audit-schedule` and `active-audit-schedule` for prioritizing candidate actions before micro-audit.  The scheduler uses expected coker margin, carrier need, uncertainty, lineage/source novelty, prior success, timeout risk, and audit cost.  `pipeline` and `iterate` can route candidate action files through the scheduler with `--audit-scheduler` before audit stages.  Outputs remain finite chart/witness artifacts, not canonical contexts.

Example:

```bash
lean-rgc iterate \
  --tasks examples/minimal_theorems.jsonl \
  --actions examples/core_tactics.jsonl \
  --out runs/v36_sched \
  --dry-run \
  --rounds 1 \
  --audit-scheduler \
  --audit-scheduler-budget 16
```

### v36: Cost-aware Active Audit Scheduler

v36 adds an active audit scheduling layer. It ranks candidate actions before Lean audit by expected coker margin, carrier need, uncertainty reduction, novelty, historical success, audit cost, and timeout risk.

Standalone:

```bash
lean-rgc audit-schedule \
  --candidates candidates.jsonl \
  --db run/audit.db \
  --out scheduled_actions.jsonl \
  --out-rows schedule_rows.jsonl \
  --report-out schedule_report.json \
  --top-k 32
```

Pipeline / iterate:

```bash
lean-rgc iterate \
  --tasks examples/minimal_theorems.jsonl \
  --actions examples/core_tactics.jsonl \
  --out runs/v36_sched \
  --dry-run \
  --rounds 2 \
  --audit-scheduler \
  --audit-db
```

The scheduler is a finite audit-budget chart, not a canonical selector.


## v37: Source-budget active audit scheduler

V37 adds a cross-source audit scheduler.  It allocates a fixed audit budget
across qgen, action-geometry, quotient-coordinate, carrier-quotient,
contextual-probe, registry, premise-response, IR, and other candidate sources.
The scheduler scores expected coker margin, carrier need, uncertainty, novelty,
prior success, timeout risk, and audit cost, then emits a selected audit batch.

Standalone:

```bash
lean-rgc source-budget-schedule \
  --run-dir runs/round_00 \
  --out-actions runs/round_00/source_budget/source_budget_actions.jsonl \
  --out-rows runs/round_00/source_budget/source_budget_rows.jsonl \
  --out-report runs/round_00/source_budget/source_budget_report.json \
  --budget 64
```

Pipeline:

```bash
lean-rgc pipeline \
  --tasks examples/minimal_theorems.jsonl \
  --actions examples/core_tactics.jsonl \
  --out runs/v37_source_budget \
  --dry-run \
  --qgen \
  --source-budget \
  --audit-source-budget-candidates \
  --source-budget-budget 32
```

The output is a finite audit-budget chart, not a canonical selector.


## v38: Promotion Evidence Generator

v38 adds a finite-chart promotion evidence generator.  It mines coker residual normals, robust acceptance rows, carrier patch audits, and POMS status rows to produce evidence rows consumable by the existing POMS promotion calculus.

```bash
lean-rgc poms-evidence   --run-dir runs/my_run   --out-json runs/my_run/promotion_evidence_report.json   --out-jsonl runs/my_run/promotion_evidence_rows.jsonl   --out-poms runs/my_run/promotion_evidence_for_poms.jsonl

lean-rgc poms-promote   --run-dir runs/my_run   --evidence runs/my_run/promotion_evidence_for_poms.jsonl
```

`iterate` can run this automatically:

```bash
lean-rgc iterate ... --poms-generate-evidence --poms-promote
```

The evidence rows are not canonical declarations.  They are finite audit/coker evidence for `parent_nonpaid`, `dual_certificate`, and `least_repair`, and they remain subject to the no-premature-refinement rule.


## v39: Defect Ontology Reconciliation

`lean-rgc defect-ontology-reconcile` compares mined qgen / quotient-coordinate / carrier-quotient atoms against an existing defect registry and emits merge / shadow / novel / open classifications, split suggestions, and a reconciled registry. Outputs are finite chart witnesses, not canonical ontology decisions.

Example:

```bash
lean-rgc defect-ontology-reconcile --run-dir runs/my_run --out runs/my_run/defect_ontology
```


## v40: Defect Ontology Lifecycle

V40 adds a lifecycle manager for mined defect atoms.  It consumes defect ontology reconciliation rows, promotion evidence, validation rows, and split suggestions, then emits lifecycle statuses such as `merge_validated`, `validated_novel_atom`, `shadow_pending`, `open_pending`, and `split_validated`.

```bash
lean-rgc defect-ontology-lifecycle \
  --run-dir runs/my_run \
  --out runs/my_run/defect_ontology_lifecycle
```

The output is a finite audit/provenance chart, not a canonical ontology decision.


## v41: Arithmetic Teacher Graph

v41 adds `arithmetic-teacher-graph`, a first goal-state-dynamics implementation of arithmetic teacher constraints.  It reads `StructuredProofState` rows and emits arithmetic identity transformations, teacher constraints, pending transition audits, and optional candidate actions.

```bash
lean-rgc arithmetic-teacher-graph   --structured-states runs/round_00/audit/structured_states.jsonl   --out runs/round_00/arithmetic_teacher
```

This is not a theorem-text curriculum.  It is a finite chart for partial goal-state transformations `g -> tau_I(g)` and is explicitly not canonical until POMS evidence establishes parent non-payment, dual certificate, and least repair.


## v43: Arithmetic Teacher Cocycle Audit Loop

v43 adds a finite cocycle audit layer for arithmetic teacher transitions.  It aggregates
`arithmetic_teacher_kernel_audit_rows.jsonl` into identity/direction transition geometries and
checks finite constraints such as `Gamma_{J∘I} ≈ Gamma_J Gamma_I` and
`b_{J∘I} ≈ Gamma_J b_I + b_J`.

Example:

```bash
lean-rgc pipeline \
  --tasks examples/minimal_theorems.jsonl \
  --actions examples/core_tactics.jsonl \
  --out runs/v43_arith_cocycle \
  --dry-run \
  --arithmetic-teacher-graph \
  --arithmetic-teacher-kernel-audit \
  --arithmetic-teacher-cocycle-audit \
  --arithmetic-teacher-cocycle-max-auto-pairs 8
```

See `LEAN_RGC_V43_ARITHMETIC_TEACHER_COCYCLE_NOTES.md`.

## v42: Arithmetic Teacher Kernel Transition Audit

v42 adds a server-backed audit path for arithmetic teacher transformations.  It turns v41 `g -> tau_I(g)` transformation rows into concrete proof actions, runs them through `LeanServerAdapter`, and records response, carrier delta, structured after-state, kernel-state side channels when available, and MVar-measure deltas.

```bash
lean-rgc arithmetic-teacher-kernel-audit \
  --transformations runs/round_00/arithmetic_teacher/arithmetic_teacher_transformations.jsonl \
  --tasks examples/minimal_theorems.jsonl \
  --structured-states runs/round_00/audit/structured_states.jsonl \
  --out runs/round_00/arithmetic_teacher/kernel_transition_audit \
  --dry-run \
  --server-backend dry_run
```

Pipeline integration:

```bash
lean-rgc pipeline \
  --tasks examples/minimal_theorems.jsonl \
  --actions examples/core_tactics.jsonl \
  --out runs/v42_arith_kernel \
  --dry-run \
  --arithmetic-teacher-graph \
  --arithmetic-teacher-kernel-audit
```

The outputs are finite goal-state transition witnesses, not canonical objects.


## v44: Gamma Transition Learner

The v44 stack adds an action-dependent finite-chart Gamma learner.  It fits

```text
next_defect ≈ Gamma(action) @ (defect - response) + affine_bias(action)
```

from `transitions.jsonl`, optionally using arithmetic teacher cocycle constraints
as a weak regularizer.

```bash
lean-rgc gamma-transition-learner \
  --transitions runs/round_00/transitions.jsonl \
  --teacher-constraints runs/round_00/arithmetic_teacher/cocycle_audit/arithmetic_teacher_gamma_constraints.jsonl \
  --out runs/round_00/gamma_transition
```

Pipeline integration:

```bash
lean-rgc pipeline \
  --tasks examples/minimal_theorems.jsonl \
  --actions examples/core_tactics.jsonl \
  --out runs/v44_gamma \
  --dry-run \
  --gamma-transition-learner
```

Outputs include `gamma_transition_actions.jsonl`,
`gamma_transition_audit_rows.jsonl`, and
`gamma_transition_action_geometry_patches.jsonl`.  These are finite propagation
charts, not canonical Gamma operators.

## v45: Gamma-aware Action Geometry Retrieval

v45 lets action-geometry retrieval use the learned finite-chart Gamma transition
model.  Instead of scoring only the local response `r(a)`, retrieval can score a
finite-horizon tail value:

```text
Q_Gamma,H(a) = sum_{k=0}^H Gamma(a)^k r(a)
```

Example:

```bash
lean-rgc pipeline \
  --tasks examples/minimal_theorems.jsonl \
  --actions examples/core_tactics.jsonl \
  --out runs/v45_gamma_ag \
  --dry-run \
  --qgen \
  --action-geometry \
  --action-geometry-retrieve \
  --action-geometry-use-qgen-normals \
  --action-geometry-use-gamma-transition \
  --action-geometry-gamma-value-mode finite_horizon \
  --action-geometry-gamma-horizon 4
```

The gamma-aware score remains a finite audit chart / witness, not a canonical
propagation operator.

## v45: Gamma-aware Action Geometry Retrieval

v45 connects learned finite-chart Gamma transition models to Action Geometry retrieval.

```bash
lean-rgc pipeline \
  --tasks examples/minimal_theorems.jsonl \
  --actions examples/core_tactics.jsonl \
  --out runs/v45_gamma_aware \
  --dry-run \
  --action-geometry \
  --action-geometry-use-qgen-normals \
  --action-geometry-use-gamma-transition \
  --action-geometry-gamma-value-mode finite_horizon \
  --action-geometry-gamma-horizon 4 \
  --audit-action-geometry-candidates
```

The Action Geometry score may now use a finite-horizon tail-native value

```text
Q_{Gamma,H}(r) = sum_{k=0}^H Gamma(a)^k r
```

and a learned Gamma stability penalty.  Outputs remain finite chart / witness artifacts, not canonical propagation operators.

## v46: Gamma-aware Source Budget Scheduler

v46 lets the source-budget scheduler use learned finite-chart Gamma information
when allocating audit budget across candidate families.  Candidate metadata from
gamma-aware Action Geometry retrieval can now influence source-level selection:

```text
Delta score = gamma_value_weight * gamma_tail_value_gain
              - gamma_tail_risk_weight * gamma_tail_risk
```

Example:

```bash
lean-rgc pipeline \
  --tasks examples/minimal_theorems.jsonl \
  --actions examples/core_tactics.jsonl \
  --out runs/v46_gamma_source_budget \
  --dry-run \
  --qgen \
  --action-geometry \
  --action-geometry-retrieve \
  --action-geometry-use-qgen-normals \
  --action-geometry-use-gamma-transition \
  --action-geometry-gamma-aware \
  --source-budget \
  --source-budget-gamma-aware \
  --audit-source-budget-candidates
```

The output remains a finite audit-budget chart, not a canonical propagation
operator.

## v47: Goal-State Dynamics Substrate

v47 adds a first-class `g --a--> g'` transition chart.  Server/persistent audit records now preserve `kernel_state_before`, `kernel_state_after`, and `state_delta` when available.  New commands:

```bash
lean-rgc goal-state-transitions --audits audit/micro_audit.jsonl --out goal_state_transitions.jsonl
lean-rgc kernel-state-graphs --kernel-jsonl kernel_states.jsonl --out goal_state_graphs.jsonl
```

The schema includes ExprGraph, LocalDeclGraph, MetavariableGraph, TypeclassGraph, state hashes, and MVar progress response.  It remains a finite chart, not a canonical quotient.

## v48: Kernel Goal-State Server Schema

v48 adds the strict `lean-rgc-kernel-state-v1` envelope and an in-process
`KernelGoalStateServer` facade for `state_id, action -> state_id', transition`.
The payload includes raw and quotient-safe normalized hashes, ExprGraph,
LocalContextGraph, MetavariableGraph, TypeclassGraph, replay metadata, and
structured safety checks.

```bash
lean-rgc kernel-state-normalize --kernel-jsonl kernel_states.jsonl --out strict_kernel_states.jsonl
lean-rgc kernel-state-probe --task-json task.json --action-json action.json --backend dry_run --out probe.json
```

The packaged Lean source-check worker now emits the v1 envelope.  Fields that
are not yet native kernel objects are exposed through `object_coverage`, so RGC
can distinguish kernel-backed data from compatibility charts.

## v49: In-Memory Lean Kernel RPC Worker

v49 adds `lean_rgc/native_lean/RGCKernelRPC.lean`, a true in-memory Lean
JSONL worker.  It stores real `Core.State`, `Meta.State`, `Term.State`, and
open `MVarId`s behind process-local `state_id`s, applies tactics with
`Lean.Elab.runTactic`, and returns before/after `lean-rgc-kernel-state-v1`
payloads with Expr DAGs, local declaration graphs, metavariable graphs,
typeclass-obligation readouts, persistent branch/rollback ids, and transition
deltas.

Use it through the native worker launcher:

```bash
lean-rgc lean-native-worker --exec-mode kernel_rpc --print-command
lean-rgc lean-server-apply --lean-server-backend native --native-exec-mode kernel_rpc \
  --task-json task.json --action-json action.json --out audit.json
```

Lean itself is installed by elan under the user toolchain directory; the repo
only carries the small worker source file, not a vendored Lean distribution or
Mathlib checkout.

## v50: Premise Contextual Quotient

v50 extends the v35 Premise Response Registry from identity-context premise
response to finite contextual premise-use fingerprints.  A premise-use context
`u = (premise, use_mode, instantiation)` is audited inside safe pre/post
contexts, with the incremental response computed as:

```text
R^{A,B}(u; g) = response(B; u; A) - response(B; A)
```

This subtracts the surrounding context baseline, so the premise quotient is
mined from what `u` adds in that context, not from the context itself.

Standalone commands:

```bash
lean-rgc premise-contextual-generate --premise-actions premise_actions.jsonl \
  --contexts context_actions.jsonl --out premise_contextual_candidates.jsonl
lean-rgc premise-contextual-fingerprints --responses premise_contextual_audit/responses.jsonl \
  --actions premise_contextual_candidates.jsonl --out premise_contextual_fingerprints.jsonl
lean-rgc premise-contextual-mine --fingerprints premise_contextual_fingerprints.jsonl --out premise_contextual
lean-rgc premise-contextual-validate --fingerprints premise_contextual_fingerprints.jsonl \
  --classes premise_contextual/premise_quotient_classes.jsonl \
  --out-rows premise_contextual/premise_quotient_validation_rows.jsonl \
  --out-report premise_contextual/premise_quotient_validation_report.json
lean-rgc premise-quotient-retrieve --classes premise_contextual/premise_quotient_classes.jsonl \
  --response-normal '{"goal.eq": 1.0}' --out premise_contextual/premise_quotient_retrieved_actions.jsonl
```

Pipeline flags:

```bash
lean-rgc pipeline --tasks tasks.jsonl --actions actions.jsonl --out runs/v50 \
  --premise-contextual-quotient \
  --premise-quotient-retrieve
```

Artifacts include `premise_contextual_candidates.jsonl`,
`premise_contextual_audit/responses.jsonl`,
`premise_contextual_fingerprints.jsonl`, `premise_quotient_classes.jsonl`,
`premise_quotient_members.jsonl`, `premise_quotient_representatives.jsonl`,
`premise_quotient_validation_rows.jsonl`,
`premise_quotient_validation_report.json`, and
`premise_quotient_retrieved_actions.jsonl`.  These are finite probe charts and
validation witnesses, not canonical premise classes until POMS promotion
conditions are supplied.
