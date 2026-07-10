# U' T0 anchored execution record (2026-07-10)

Status: CLOSED DETERMINISTIC DEVELOPMENT GATE.

## Temporal anchor

The complete rule bundle was committed as
`638d0329af4991caa23b4e527bece7bb567900d4` and pushed to
`origin/codex/uprime-odlrq-plan` before execution. The executable independently
verified that all five anchor inputs matched `HEAD` and that `HEAD` was an
ancestor of the configured upstream. Default CI had the T0 pytest replay
disabled by its registered environment gate, so collection/skip could not
precede the canonical probe.

The anchor CI run `29092441393` completed successfully before this result was
closed: `308 passed, 4 skipped, 163 deselected`. CI did not set the registered
T0 execution environment variable; the T0 replay therefore remained skipped.

## Canonical Windows CPU execution

```powershell
python -m lean_rgc.evals.uprime_t0 `
  --repo-root . `
  --anchor 638d0329af49 `
  --out runs/uprime_t0_20260710/theory_errata_638d0329af49.json
```

Result:

- verdict: `T0_PASS`;
- failures: `[]`;
- every `T0-W/P/C/S/J/ME/H` legacy counterexample detected;
- every amended negative fixture handled;
- every amended positive fixture passed;
- every reported numeric value finite under the frozen rule;
- `licenses_next_repair_stage=true`;
- `licenses_later_stage=false`.

The ignored raw artifact SHA-256 is
`35ED33AC4E3F246EFBF53A0532F836937C8C5768CAF78D4A3DCCFFF05CFF4A1B`.
Its tracked normalized derivative is
`docs/experiments/artifacts/uprime_t0_20260710/theory_errata_638d0329af49.json`,
SHA-256 `09B515E757D25F5E127CF2FB8DFD2DBBC0862A2C9C462BB2EED1F31E682B3DE5`.

## Post-artifact replay

Only after the canonical artifact was written, the registered pytest gate was
opened:

```powershell
$env:UPRIME_T0_ANCHORED_EXECUTION='1'
python -m pytest -q `
  tests/test_uprime_t0_errata.py `
  tests/test_v74_test_tier_manifest.py
```

Result: `7 passed in 8.59s`.

## Disposition

The three K0 T0 blockers are removed by errata v1, and the additional
similarity/telescoping/MaxEnt/finite-horizon obligations are now executable
regressions. This is not a theory-program freeze and does not repair full F0 or
M0--M4. The next licensed action is the pre-anchored U'1 live RPC litmus and
metrology repair. GPU construction remains barred.
