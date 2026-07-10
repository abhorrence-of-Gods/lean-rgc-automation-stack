# U'1 repair milestone 1: response envelope and cache default identity

Status: IMPLEMENTED FOR UNIT AND WINDOWS CPU FIXTURE VERIFICATION; FROZEN BEFORE
ANY POST-REPAIR CANONICAL LIVE DIAGNOSTIC.

## Evidence boundary

The immutable diagnostic anchored at
`4ba370f543c82f4e8edef92b587645aec7674349` evaluated all eleven contracts and
closed as `U1_DIAGNOSTIC_BLOCKED`. This repair record responds only to two
independent, directly observed causes:

- every one of the 23 worker responses lacked the request ID and
  `rpc_protocol_version`, failing R0;
- the Python audit-cache key represented an omitted task/action heartbeat cap
  as the empty string rather than the runtime default `200000`, failing B4.

The publication-safe evidence is
`docs/experiments/artifacts/uprime_u1_rpc_20260710/rpc_diagnostic_4ba370f543c8.public.json`,
SHA-256
`7E6FE9DC6101CA02A06C9D3A18EFC5FFA4C129F1FB6170126FAEC041F590D80F`,
committed in `768e6d08b1a6e031e595be3d980bf01e8c950878`.

The repair is result-aware. It is not a new blinded experiment, and no
canonical artifact is consumed by this milestone.

## Frozen scope

### R0 response envelope

The native RPC adds `rpc_protocol_version = lean-rgc-jsonl-rpc-v2` and the raw
request `id` at the single JSONL output boundary after `handle` returns. This
one boundary covers success, ordinary error, unknown command, and shutdown
responses. It overwrites any same-named handler payload fields so the envelope
cannot be spoofed by a branch.

A malformed JSON line has no recoverable request object and therefore returns
`id = null` with the protocol version and parse error. A missing or non-string
ID is echoed as its raw JSON value; the frozen U'1 sequence supplies 23 string
IDs. Unexpected IO exceptions remain governed by the pre-existing outer loop
behavior and are outside this milestone.

R0 also fails closed unless request and response labels equal the fixed
23-label registry and all 23 generated request IDs are nonempty and unique.

### B4 omitted default

The cache resolver retains exact action-over-task precedence and explicit zero
semantics. Only the terminal case where both values are absent changes from
the empty string to `200000`. The runtime default remains independently frozen
in the diagnostic oracle; the cache implementation does not import the oracle
constant.

Adversarial review found that the source-check single-file and bulk renderers
used truthiness fallback, so action value `0` executed with the task cap while
its cache key used `0`. Both renderers now use the same explicit-None
precedence as the key. This closes a pre-existing false-hit route required for
B4 soundness; it does not enable the hard-disabled stateful kernel-RPC cache.

An explicit-null task value is normalized to the same default in the task
schema, and direct task objects with null are rendered as `200000`. Because the
cache/execution identity changes without a DDL change, the audit-cache schema
label advances from v102.0 to v103.0 and the cache key gains a v103 semantics
salt. All pre-v103 rows, including rows previously labeled explicit zero, are
therefore unreachable safe misses; no result produced under the truthiness bug
can be reused. Stateful kernel-RPC cache lookup and storage remain
hard-disabled.

## Explicit exclusions

This milestone does not change task/action budget propagation, heartbeat or
episode telemetry, timeout classification, target routing, delta accounting,
all-goal sweep, replay, shutdown latency, or the diagnostic verdict. It also
does not backfill full responses into any earlier artifact.

The forward-only full-frame ledger is a separate evidence milestone. Before a
future canonical run it must have its own amendment, bundle reservation,
hash-chain verifier, privacy scanner, and publication rule.

## Verification and decision rule

Required pre-commit checks are:

1. the ordinary unit/cache suites show action zero, task fallback, explicit
   override, omitted default, explicit-null normalization, single/bulk renderer
   alignment, omitted/explicit-default key identity, and a cache miss for a
   pre-v103 explicit-zero row under the new semantics salt;
2. a CI-visible source invariant confirms that the worker has one enveloped
   stdout write boundary;
3. one Windows CPU Lean process receives malformed JSON, an unknown command,
   load/init/tactic success responses, and shutdown; parse error must use a
   null ID, and every valid request response must echo its exact ID and protocol;
4. removing the shutdown protocol field from an otherwise all-clear synthetic
   fixture makes only R0 false.

The explicit live-fixture command is
`python -m pytest -q -o addopts='' tests/test_v49_kernel_rpc_worker.py`; this
test is in the legacy tier and is not exercised by ordinary default CI.

Passing these checks closes only the two local repair items. It does not license
a canonical U'1 rerun, U'0.5 kill probes, later U' stages, or GPU construction.
The next canonical diagnostic remains reserved until the remaining repair
fixtures form a full CLEAR candidate. A machine-enforced forward-only rerun
license is still a MUST-CLOSE governance item before any such diagnostic; the
current reservation mechanism alone does not prevent premature runs on new
anchors.

This milestone does not claim whole-cache soundness. In particular,
`extra_set_options`, wall-clock timeout, and backend differences remain outside
the B4 frozen payload and require separate cache-governance review if those
dimensions become reusable.

## Pre-commit evidence

- focused U'1/cache tests: 50 passed;
- explicit Windows Lean legacy fixture: 2 passed in 30.07 seconds;
- default full suite: 354 passed, 3 skipped, 163 deselected;
- adversarial protocol, cache, and governance re-reviews: no release blocker;
- `git diff --check`: clean.

These are fixture results, not a canonical post-repair U'1 verdict.
