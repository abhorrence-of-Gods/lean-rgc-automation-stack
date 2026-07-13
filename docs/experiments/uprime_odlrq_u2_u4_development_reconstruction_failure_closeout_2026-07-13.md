# U-prime / ODLRQ U2--U4 development reconstruction failure closeout

Date: 2026-07-13 (Asia/Tokyo)

Status: `U24_EXACT_ADMISSION_BLOCKED`

E0 generator disposition: `NOT_CONSTRUCTED / NOT_EMITTED`

Fixture digest: `NOT_CREATED / NOT_APPLICABLE`

Cause: `FROZEN_FIXTURE_FRAME_CONFLICT / pre-source exact-admission
incompatibility`

Authority:
`docs/experiments/uprime_odlrq_u2_u4_development_reconstruction_amendment_2026-07-13.md`
at accepted A1 commit `7377119962e07c9062ba46c2c0c2f0eb479060ef`,
inheriting section 8 of the original construction authority at
`14234e209229931c00615d4b171620ec6d1bbbf5`.

Parent: accepted B0R correction commit
`48c9127b0cc6122af203869c656a78b9f2160293`.

## Accepted B0R predecessor

The R1 build ref preserves the initial B0R commit
`7083e766acd2ba09b45ba3f47f65dc0b34317bd3` and its sole bundle-wide
correction `48c9127b0cc6122af203869c656a78b9f2160293`.  The initial candidate
failed CI run `29226375952` because the test fixture's POSIX temporary-
directory cleanup crossed the registered read-denial boundary.  The sole
correction changed only that fixture cleanup and its frozen identity hash.

The corrected B0R candidate passed CI run `29226777052`; the exact same commit
was fast-forwarded to the accepted branch and passed distinct accepted CI run
`29226930116`.  Both runs reported exactly:

```text
2581 passed, 8 skipped, 161 deselected
```

The registered Windows B0 runner also passed all five contracts with
disposition `CPU_U24_IDENTITY_AND_RUNNER_GATE_VERIFIED`.  B0R therefore
remains an accepted engineering predecessor.  The present failure neither
relabels nor weakens that result.

## Pre-source E0 blocker

The mandatory dirty-worktree review was performed before any E0 source was
written.  Original section 8 freezes the four fixture `ObservationFrameId`
strings as:

```text
source_lane       = u24_synthetic
granularity       = exact_block_member
normalization_id  = generation_time_exact_v1
extractor_version = u24_fixture_v1
```

The only public exact-admission path instead constructs and validates:

```text
source_lane       = synthetic_development
granularity       = synthetic_totalized_state
normalization_id  = exact_rational_decimal_v1
extractor_version = cpu_survivor_synthetic_v1
```

`make_synthetic_observation_frame_id` fixes the latter values, and
`validate_synthetic_finite_snapshot` rejects every deviation before
`ExactAdmissionCompletionGate.admit` can return an admitted source.  Manual
construction is not an alternative: the same validator is called by the gate
and again by `AdmittedExactFiniteSnapshot.__post_init__`; exact types and
subclasses are enforced.

An independent read-only executable witness rebuilt a complete synthetic
snapshot with the section-8 frame, rebound its state and reachable-domain
digests, and invoked the mandatory gate.  It deterministically failed with:

```text
StrictContractError: typed observation frame is not bound to the response schema
```

E0 may change only:

```text
lean_rgc/odlrq/quotient_generator.py
lean_rgc/odlrq/__init__.py
tests/test_odlrq_quotient_generator.py
```

The fixed frame constants and validator live in `contracts.py` and
`adapters.py`, outside that path set.  Thus no implementation restricted to
the frozen E0 paths can both reproduce the frozen fixture bytes and rerun the
mandatory exact-admission gate.

Two secondary integration defects were recorded but were not needed to reach
the terminal verdict.  The validator requires every state and action ID to
start with `unit_cpu_survivor_`, whereas section 8 does not freeze an exact
expansion of the displayed `s0`/`a` labels.  Also, the whole-module reading of
the ordering regression (no nominal import or export) conflicts with the
pre-existing public `NominalOperator` and nominal-tier symbols in the same
module.  Neither ambiguity was silently resolved.

## Frozen adjudication

R1 permits no alteration of an E0 fixture, formula, path set, or inherited
constructor grammar.  Its sole correction was already consumed by B0R, and a
correction could not in any case change these frozen terms.  The registered
rule therefore requires immediate failure closure at
`U24_EXACT_ADMISSION_BLOCKED` rather than an unregistered adapter change, a
mocked gate, or an outcome-dependent fixture substitution.

No E0 source, candidate commit, generator, fixture digest, or artifact was
created.  E1, E2, ME0, S0, I0, EMIT, and CLOSEOUT were not executed.  No
protected K1--K4 result was read.  No native Lean/RPC, official transport,
remote CPU, SSH, GPU, LLM, deployment, MaxEnt fit, global-similarity
certificate, or locality learner was run.

A replacement authority may resolve the pre-existing integration defects
without using protected outcomes.  The smallest registered repair is to keep
the three-file E0 implementation scope, bind fixtures to the already admitted
strict frame constants, freeze full `unit_cpu_survivor_` state/action IDs and
payload names, and scope the no-nominal regression to the newly added E0 API,
wire, and dependency surface.  Redesigning the shared admission profile would
be a larger alternative and is not authorized by this closeout.

This closeout is evidence only that the frozen E0 fixture grammar and current
exact-admission substrate are incompatible.  It is not evidence that exact
quotient coordinates or the upper mathematical program are impossible, and
it claims no protected K1--K4 performance, same-family D4 rank, production
Lean locality, complete all-germ quotient, production hard envelope, MaxEnt
safety, global Lean similarity, learner improvement, solve rate, deployment,
remote/GPU benefit, or LLM benefit.
