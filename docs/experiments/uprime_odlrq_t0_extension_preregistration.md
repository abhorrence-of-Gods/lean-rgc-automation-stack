# U' T0 extension preregistration

Status: FROZEN BEFORE FIRST EXECUTION. This file, the theory errata, executable,
and tests must be committed and pushed together before the command below is
run. The anchoring commit is recorded afterward without changing these gates.

## Purpose and evidence class

T0 checks whether the seven deterministic counterexamples and repaired formulas
in `uprime_odlrq_theory_errata_2026-07-10.md` are encoded without silently
promoting empirical absence of violations. All inputs are synthetic and
development-public. T0 is a deterministic regression gate, not statistical or
confirmatory evidence.

## Frozen probes

- `T0-W`: weighted compression/lifting mismatch and repaired coordinates.
- `T0-P`: coordinate-kernel factorization, written contextual identity,
  Markov refusal, and nested positive fixture.
- `T0-C`: correlated full covariance and independent zero-cross-term fixture.
- `T0-S`: projected-similarity false merge and residual transport.
- `T0-J`: untransported error addition and typed operator telescoping.
  Its positive provenance record is the committed synthetic artifact
  `docs/experiments/fixtures/uprime_t0_model_bound_fixture.json`; the probe
  verifies its actual bytes, digest, schema, domain, norm, and bound.
- `T0-ME`: moment non-identification, residual-span bound, feasibility,
  boundary, and minimal-family checks.
- `T0-H`: finite-horizon memory bound, infinite-horizon refusal, and nilpotent
  transient growth.

## Frozen decision rule

Each probe returns these booleans:

```text
legacy_counterexample_detected
amended_negative_handled
amended_positive_fixture_passed
```

`T0_PASS` requires all three booleans for all seven probes. Missing fields,
non-finite computed quantities, a failed positive fixture, or an unrefused
negative fixture yields `T0_FAIL`. There is no tolerance tuning after the
anchor. The only floating computation is `T0-H`; it uses the predeclared
absolute tolerance `1e-12` for direct evaluation of the same analytic formula.

The output always keeps `licenses_later_stage=false`. A `T0_PASS` removes only
the theory-errata blocker and licenses the next registered U'0/U'1 repair.

## Frozen command and artifacts

After the anchor is pushed, substitute its 12-character commit prefix:

```powershell
python -m lean_rgc.evals.uprime_t0 `
  --repo-root . `
  --anchor <ANCHOR12> `
  --out runs/uprime_t0_20260710/theory_errata_<ANCHOR12>.json
```

The output is never overwritten. A publication-safe derivative and raw/public
hash manifest are committed after execution.

The anchor push may trigger default CI. The T0 pytest file is therefore
fail-closed skipped unless `UPRIME_T0_ANCHORED_EXECUTION=1`; CI collection or
skip is not a T0 execution. The command above is the first anchored probe run.
Only after its artifact is closed may the local replay test run:

```powershell
$env:UPRIME_T0_ANCHORED_EXECUTION='1'
python -m pytest -q tests/test_uprime_t0_errata.py
```

The executable additionally requires every anchor input to match `HEAD` and
requires `HEAD` to be an ancestor of its configured upstream remote-tracking
branch. Thus an unpushed or locally edited anchor is rejected before probes are
constructed.

## Failure and amendment rule

- Any probe failure leaves T0 blocked; repair requires a new code revision and
  a dated result, preserving the failed artifact.
- The seven fixture definitions and `1e-12` tolerance cannot be changed after
  the anchor to turn a failure into a pass.
- A mathematical correction discovered after anchoring creates errata v2 and
  a new preregistration; it does not rewrite v1.
- K1--K4, U'2--U'5, protected evaluation, and GPU construction remain barred
  regardless of T0 until their own upstream gates pass.
