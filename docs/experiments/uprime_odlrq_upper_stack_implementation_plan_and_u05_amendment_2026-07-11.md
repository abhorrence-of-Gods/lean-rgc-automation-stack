# U' / ODLRQ upper-stack implementation plan and U'0.5 scheduling amendment

Date: 2026-07-11

Status: FROZEN IMPLEMENTATION-PLAN AND SCHEDULING AMENDMENT. The Git commit
containing this document is the temporal anchor. This is not Amendment A, not a
new theory freeze, and not a second review of the upper-stack mathematical
proposal. It converts the already adjudicated surviving program into bounded
software work packages and moves three development-only kill probes ahead of
nonessential metrology and infrastructure work.

## 1. Authority, scope, and sealed predecessor

The reviewed theory inputs are fixed as follows:

- the UTF-8 integrated TeX has SHA-256
  `7E24F7D444A263792A3A717B1C26807D0A15626C2A11D8F38A1DCCB7DE69CD87`;
- the UTF-8 S'1m-to-ODLRQ proposal transcript has SHA-256
  `855F49956CABAE786FA221B4D7D38E95630147687A79941FB17F0C0D1137E9AB`;
- the registered theory/adversarial disposition is
  `docs/experiments/uprime_odlrq_adversarial_review_2026-07-10.md`;
- the executable mathematical repairs are
  `docs/experiments/uprime_odlrq_theory_errata_2026-07-10.md`, whose T0 result
  is `T0_PASS`.

The theory verdict is an input to this plan: freeze was rejected as written,
but consistent weighted domination, finite-horizon memory control,
hard/robust/nominal separation, bounded action-word response closure, and
Lean-oracle counterexample refinement survived after the registered errata.
This document reviews implementation completeness, feasibility, governance,
and endpoints only. It does not use implementation difficulty to reopen the
theory verdict, and it does not use the theory verdict to assume that an
implementation exists.

This amendment seals the completed Phase 2b2f result:

```text
result commit  df38daea2139b67d9935408c82bfb3297efd9536
sole parent    0a6eb4a92edc1061773c175975f986f0c5ea5a3c
result doc     2013c1fec71dd51bfabcb369a2f1844966786d88
litmus         58ea51e44acca2cf2ec86a640e218db5c7c6e095
rerun test     8966af27c07f97b0fff85fb2229f577142e9db7f
CI run/job     29154121499 / 86548332796
CI headSha     df38daea2139b67d9935408c82bfb3297efd9536
CI conclusion  success
CI result      2253 passed, 4 skipped, 163 deselected in 57.91s
```

The historical result changed exactly these three regular files:

```text
docs/experiments/uprime_odlrq_u1_evidence_milestone_2b_phase2b2f_execution_2026-07-11.md
lean_rgc/evals/uprime_rpc_litmus.py
tests/test_uprime_rerun_license.py
```

Each historical tree entry has mode `100644 blob`. The rerun-registry blob is
`13ffca6de484effc66f0e628d2e46823277271c6` and remains empty and
default-deny.

The Phase 2b2f protected filesystem digest remains
`2F69E3E119CBED3116CAB8FDB4B3CE22DB2D7CEFA3A0970CC616378E6C8A191B`,
and its tracked and runtime exposure-marker inventories were empty. These facts
authenticate the predecessor only; they do not repair Lean replay, heartbeat
telemetry, delta accounting, tail-goal sweeping, target routing, or any
scientific endpoint.

## 2. Narrow supersession of the old schedule

For the development-only U'0.5 lane, this document supersedes only the
following scheduling clauses:

1. the requirement in the v0 preregistration that every U'1 repair precede all
   K-series work;
2. the execution-log queue that placed M3/M4 and full telemetry before drafting
   any probe apparatus;
3. the Phase 2b M2b stop rule that barred U'0.5 until the entire publication
   writer stack was complete; and
4. the Phase 2b2f amendment's original restriction to Phase 2c registration.

Phase 2b2f is the terminal point of synthetic evidence-ledger expansion.
Phase 2c implementation is not the next step and is not licensed here.

The revised order is:

```text
T0 mathematical errata                                  DONE
-> minimum U'0/U'1 metrology needed by the probes       BOUNDED REPAIR
-> U'1.5 deterministic measurement apparatus            BUILD
-> U05-KP1/KP2/KP3 on local development fixtures        ONE EXECUTION
-> portfolio stop/survival decision                     RECORDED
-> U'CPU-survivor implementation bundle amendment       DRAFT/FREEZE
-> only surviving exact/locality substrate (WP4/WP6)    FUTURE BUILD
-> development-only upper-operator bundle (WP7--WP10)   DRAFT/FREEZE
-> synthetic/development U'2--U'4 construction           FUTURE BUILD
-> complete CPU candidate + development calibration     FUTURE PILOT
-> filled Amendment A                                   FUTURE FREEZE
-> protected K1--K4                                     ONE LOOK
-> protected deployment / any authorized GPU work       FUTURE BUILD
-> U'5 paired sealed evaluation                         LAST
```

`U'0.5` names the early decision lane. `U'1.5` names the apparatus that makes
that decision measurable. The numerical labels are not a claim that apparatus
can precede its minimum U'1 dependencies.

Only WP0--WP3 are licensed by this document. WP4--WP12 below are a dependency
and resource roadmap, not execution authority. U05 survival licenses only the
drafting of the next phase-bundle amendment; it does not itself license source
edits, pilot reads, U'2 construction, or learner training.

This supersession does **not**:

- mark F0--F3 or M0--M4 green;
- rename U05-KP1/KP2/KP3 as protected K1/K2/K3;
- license the canonical RPC diagnostic or a registered-run rerun;
- license reserved/valid-split reads, U'2--U'5 claims, GPU construction,
  experimental network/SSH use, or remote persistence; the sole network
  exception is the governance control plane frozen in WP3 (Git push plus
  read-only upstream/hosted-CI verification before matrix open);
- relax the all-task paired denominator required for U'5; or
- allow a failed instrument prerequisite to be reported as a negative theory
  or model result.

## 3. Engineering objective and non-objectives

The engineering objective is to implement the following controlled pipeline:

```text
strict semantic identity
-> kernel-exact, site-targeted local transition events
-> task-seeded prefix-closed reachable chart
-> exact response table and behavioral refinement
-> exact / interval / nominal quotient operators
-> weighted worst-case positive envelope
-> MaxEnt/KL nominal lifting inside that envelope
-> nested local representations and global node/edge measures
-> separate predictive and positive-safety similarity
-> typed finite-horizon certificate
-> lexicographic reject / fallback / utility selection
```

The Lean oracle supplies exact transition counterexamples and exact event
semantics. A learner may propose locality coordinates, partitions, query
priorities, and nominal laws. It may not invent kernel transitions, match
multiplicities, frame transports, hard bounds, or evidence status.

The following are non-objectives of the first implementation series:

- unrestricted Lean proof search or an infinite-state quotient;
- proof soundness certification beyond Lean's kernel;
- occurrence-targeted `rw`, unrestricted `simp`, `aesop`, or `omega` as
  decomposed primitive events;
- a claim that MaxEnt creates stability;
- a claim that a learned predictive metric is a safety metric;
- replacement of every historical quotient implementation; or
- construction of another evidence-ledger, CAS, recovery, or publication
  subsystem.

## 4. Semantic contracts that precede operators

New U' paths use strict, versioned records. They do not pass through the legacy
`from_dict` behavior that moves unknown fields into `metadata.extra`.

### 4.1 Immutable identifiers

```text
ObservationFrameId =
  environment_content_digest
  x source_lane
  x granularity
  x coordinate_schema_digest
  x normalization_id
  x extractor_version

TransitionSemanticsId =
  compiler_build_digest
  x dependency_import_digest
  x action_grammar_digest
  x target_site_convention
  x premise_simp_typeclass_whitelist_digest
  x transparency_options_digest
  x per_action_budget
  x episode_budget
  x cache_policy

PolicySemanticsId =
  proposer_kind
  x model_weights_digest
  x tokenizer_digest
  x server_runtime_digest
  x quantization_digest
  x prompt_template_digest
  x sampler_and_seed_policy
  x batching_concurrency_policy
```

U05 freezes the three environment digests rather than inheriting path-dependent
tool labels. Let `LP(b)` be the eight-byte big-endian byte length of `b` followed
by `b`. Then:

```text
compiler_build_digest = SHA256(
  LP(UTF8("u05-compiler-build-v1"))
  || LP(UTF8(exact_lean_version_line))
  || LP(bytes.fromhex(compiler_runtime_manifest_digest)))

compiler_runtime_manifest_digest = MerkleSHA256(
  "u05-compiler-runtime-manifest-v1", compiler_runtime_leaves)
compiler_runtime_leaf = SHA256(canonical_json([
  scope, normalized_relative_path, file_type, content_sha256
]))

dependency_import_digest = MerkleSHA256("u05-dependency-import-v1", leaves)
leaf = SHA256(canonical_json([
  relative_toolchain_library_path, file_type, content_sha256
]))

environment_content_digest = SHA256(
  LP(UTF8("u05-environment-content-v1"))
  || LP(bytes.fromhex(compiler_build_digest))
  || LP(bytes.fromhex(dependency_import_digest))
  || LP(bytes.fromhex(worker_source_sha256)))
```

`MerkleSHA256` first replaces each leaf by `SHA256(0x00 || leaf)`, then repeatedly
hashes adjacent nodes as `SHA256(0x01 || left || right)`, duplicating the final
node at an odd-width level, and finally returns
`SHA256(0x02 || LP(UTF8(schema_tag)) || LP(root_node) || LP(uint64be(leaf_count)))`.
Before leaf hashing, records are sorted by their complete UTF-8 canonical-JSON
bytes in ascending byte order; filesystem/API enumeration order is ignored.
An empty leaf set or duplicate canonical `(scope, normalized_relative_path,
file_type)` key is invalid rather than assigned a conventional root.

The compiler runtime manifest contains (1) the executed `lean.exe`, (2) every
regular `.exe` and `.dll` below the resolved toolchain prefix's `bin` directory
as a conservative superset, and (3) the complete recursively parsed PE import
closure of the executed binary and each imported toolchain-local DLL. A
toolchain leaf has `scope=toolchain` and a slash-normalized path relative to the
toolchain prefix. An imported module resolved below the canonical Windows
system roots has `scope=windows_system`, a slash-normalized system-root-relative
path, and its exact bytes hashed; the Windows product/build identifier and the
resolved API-set provider mapping are separate metadata leaves. File paths use
Unicode NFC, slash separators, and invariant case-folding; any normalization
collision blocks preflight. Absolute paths never enter identity.

The metadata leaves use the same four-field record without implementation
choice: Windows build has `scope=metadata`, pseudo-path
`windows/product_build`, `file_type=canonical_json`, and `content_sha256` of the
canonical JSON array `[product_name,display_version,current_build_number,ubr,
installation_type,native_architecture]` (all values exact strings). The API-set
leaf uses `scope=metadata`, pseudo-path `windows/api_set_map`,
`file_type=canonical_json`, and hashes the canonical JSON array of
`[contract_name_casefolded,provider_system_relative_path_casefolded,
provider_content_sha256]` rows sorted by their complete canonical row bytes.
The loaded-module inventory is encoded analogously at pseudo-path
`windows/loaded_module_inventory` as sorted
`[scope,normalized_relative_path,content_sha256]` rows. The canonical payload
bytes, their hashes, and the resulting four-field leaf records are all preserved
in the attempt receipt.

PE resolution runs under a sanitized search path containing only the toolchain
`bin` and canonical Windows system directories. Every non-API-set dependency
must resolve uniquely inside the toolchain prefix or an allowed Windows system
root. A missing/ambiguous import, a dependency in any other directory, an
unresolved API-set provider, or a loaded-module inventory differing from the
parsed closure blocks preflight. Thus replacing `libleanshared*.dll`, another
toolchain-local runtime, or a resolved system provider changes
`compiler_build_digest`.

The dependency leaves are every regular file below the resolved Lean prefix's
`lib/lean` tree, sorted by slash-normalized relative path; absolute paths are
excluded. `file_type` is the lowercase final suffix or `no_suffix`.
`worker_source_sha256` hashes the exact worktree bytes of
`lean_rgc/native_lean/RGCKernelRPC.lean`. A symlink/reparse-point escape, unreadable
file, duplicate normalized path, or file size/mtime/content mutation between the
pre- and post-hash stat pass blocks preflight. The resulting leaf count, Merkle
root, compiler digest, environment digest, and all defining schema tags are
written to the attempt receipt.

Read/burn status is mutable and remains in the EvidenceLedger. It is not a
FrameId field. A fixed logged action can be replayed without a
PolicySemanticsId; a proposer-performance or U'5 claim cannot.

### 4.2 State and observation identity

`StateIdentityKey` and `BehavioralObservationKey` are distinct types.

For U05, `StateIdentityKey` is exact relative to the frozen U05 action grammar.
It contains reachable ordered goals; reachable mvar declarations, types,
assignments and structured universes; local-declaration type/value,
binder/instance information and occurrence order; the environment digest; and
baseline semantic options. First-occurrence normalization follows the reachable
ordered graph. Process state IDs, raw generated names, name-generator counters,
messages/info trees, caches, and unreachable assigned history are excluded.
Hashes are indices only: equality always performs a full canonical-byte
comparison after a hash match.

`BehavioralObservationKey` contains a named typed observation projection plus
its `ObservationFrameId`. It may intentionally merge different concrete states,
but only a behavioral witness can promote that merge.

Two observation records may be aligned only when their keys and frames are
identical or when a registered `FrameMorphism` supplies both a transport bound
and a naturality/commutation bound. New U' paths raise on mismatch. They never
truncate, pad, or use the first row's key set.

`ActionSymbol` stores only a fixed tactic opcode, symbolic target selector,
symbolic premise-slot rule ID, frozen opaque-hyperedge digest when applicable,
and cap-profile ID. The rule ID may carry a frozen expected ordinal and
normalized-type pattern, but never a state-resolved declaration or type hash.
`BoundAction` stores the state-resolved canonical target/premise ordinals, type
hashes, and runtime MVarId/FVar names used to render Lean syntax. Raw rendered
tactic text and raw binder names are not semantic action identity. Alpha-renamed
states therefore share an action symbol while binding to their own runtime
names.

### 4.3 Exact transition admission

An `ExactOracleTransition` may be constructed only when all of the following
are present:

- explicit source state identity;
- explicit target mvar/site;
- action grammar and explicit premise/simp/typeclass inputs;
- identical explicit per-action heartbeat cap and cache bypass;
- exact before/after assigned-mvar difference and all-goal sweep;
- independent replay from an immutable before-state with exact post-state and
  response match;
- nontruncated hard-tier state, support, and boundary fields; and
- total semantic status in `{open, closed, ordinary_failure, sink}` with any
  resource/transport censor represented outside the transition algebra.

Missing or truncated evidence yields `INSTRUMENT_INCOMPLETE`, never an exact
transition with a warning attached.

WP1--WP3 do not yet satisfy the M3 read/boundary completeness condition.
Therefore WP1 first defines `ExactKernelTransitionCore`, exact only for its
versioned U05 response schema, and `U05ProbeTransition`, which wraps that core.
The core contains source/target full state identities, bound target/action/cap,
raw and totalized status, before/after goal and mvar sets,
newly-assigned/closed/new sets, frozen debt readout, and an independent replay
comparison. Optional locality read/support/boundary annotations carry a separate
`FieldCoverage`; the U05 wrapper fixes `m3_read_set_complete=false`, has no
hard-tier locality constructor or serializer, and cannot be promoted or passed
to WP4--WP12. A later `LocalityAnnotatedTransition` requires complete,
nontruncated M3 fields before it can construct an `ExactOracleTransition`.

`ReplayComparableResponse` contains only semantic raw/totalized status,
canonical after-state bytes, canonical newly-assigned/closed/new-goal/new-mvar
delta, `ActionSymbol`, canonical target/premise bindings, and normalized
ordinary-failure class. It excludes elapsed time, request/process state IDs,
transport/publication fields, and measured heartbeat consumption. Effective cap
semantics are compared separately and exactly.

A concrete Lean attempt returns `open`, `closed`, `ordinary_failure`, or a
censor. Ordinary inapplicability/failure enters the distinguished absorbing
`SINK`; `CLOSED` and `SINK` are absorbing under every symbolic action. Only
concrete Lean attempts require independent replay. Derived terminal loops carry
the totalization-rule digest and provenance of the concrete entry event.
Heartbeat exhaustion, wall timeout, process crash, transport failure, malformed
response, truncation of a required U05 field, or replay mismatch is a censor and
blocks the affected probe; it creates no Hankel cell.

## 5. Current code disposition

| Current substrate | Disposition in the new program |
|---|---|
| `lean_rgc/native_lean/RGCKernelRPC.lean` | Reuse Core/Meta/Term state, graphs, branch/rollback, and kernel execution after target, delta, replay, identity, and resource repairs. |
| `lean_rgc/lean/kernel_state.py` | Reuse graph extraction and bounded observations as adapters. Do not reuse its present normalized hash as state identity. |
| `lean_rgc/lean/goal_state_dynamics.py` | Reuse typed graph measures after exact before/after delta semantics are established. |
| `lean_rgc/audit_result_cache.py` | Reuse content-sensitive build fingerprint ingredients. `make_audit_cache_key` is not a FrameId. U05 bypasses the cache. |
| `lean_rgc/evals/uprime_t0.py` | Reuse E1--E7 negative/positive fixtures as operator golden tests. |
| `lean_rgc/contextual_congruence.py` | Legacy finite-cosine baseline and input adapter only. It is not behavioral equivalence. |
| `lean_rgc/response_quotient.py` | Legacy representative-action baseline only. Representative substitution is forbidden in the hard envelope. |
| `lean_rgc/gamma_transition_learner.py` | Nominal affine baseline only. It is not an envelope and cannot set exact coefficients. |
| `lean_rgc/action_geometry.py` | Utility/ranking baseline only. Its additive score and nonbinding `accepted` field are not the new selector. |
| `lean_rgc/quotient*.py`, `carrier_quotient.py`, premise/bivariate quotient modules | Quarantined chart implementations. They may be compared through adapters but are not extended into the ODLRQ hard path. |
| `lean_rgc/qgen.py` and other `zip`/`min` aligners | Legacy-only. New strict records reject coordinate mismatch before these functions. |
| current evidence-ledger/CAS/recovery modules | Frozen historical governance substrate. No new module or phase is authorized here. |

The implementation is placed under one package rather than adding another set
of unrelated top-level quotient modules:

```text
lean_rgc/odlrq/
  contracts.py
  adapters.py
  local_region.py
  rule_algebra.py
  reachable_chart.py
  behavioral_partition.py
  hankel.py
  quotient_generator.py
  envelope.py
  maxent.py
  similarity.py
  locality_cegar.py
  certificates.py
  selection.py
  runner.py
```

No existing production pipeline imports this package until the independent
runner and its gates are complete. Integration is a final thin adapter, not an
incremental rewrite of `action_geometry.py` or the existing quotient family.

## 6. Mathematics-to-code traceability matrix

| Registered mathematical object | Concrete implementation | Required executable witness |
|---|---|---|
| frame transport/naturality | `contracts.FrameMorphism`, `adapters.apply_frame_morphism` | schema/key mismatch hard-fails; registered transport carries an error and commutator bound in the same norm |
| bounded concrete domain/fiber completeness | `contracts.ReachableDomainId`, `FiberCompletenessWitness`, `DomainMembershipWitness` | hard domain is a complete frozen `X_Lambda` enumeration or an independently certified upper superset; outside-domain state rejects |
| action map `tau_a` with failure/closed states and external censors | `contracts.ActionSymbol`, `rule_algebra.OracleEvent`, RPC target routing | ordinary actions totalize to normal/closed/sink; resource/transport censors block cells; same concrete before/action/semantics replays identically |
| exact match/history multiplicity | `rule_algebra.MatchWitness`, `HistoryCoefficient` | site/action histories are counted without learner input; independent orders aggregate only after equal full successor identity |
| discrete fiber closure `F_N = sigma(E o tau_w)` | `reachable_chart.ActionWord`, task-seeded BFS, `hankel.ResponseChannel` | prefix closure, deterministic word ordering, exact depth/state/query caps |
| difference-jet theorem | `rule_algebra.DifferenceJet` | direct response and ordered finite-difference expansion agree on finite fixtures |
| minimal response congruence / finite partition termination | `behavioral_partition.refine` | blocks split monotonically, terminate on a finite chart, and are stable under every frozen action |
| contextual quotient universal property | `local_region.ClosingContext`, boundary-decorated local regions | any admitted merge has equal registered contextual responses or an explicit bounded defect |
| locality defect `||RK-K_RR||` | `locality_cegar.LocalityWitness` | global-then-restrict versus restrict-then-local-action discrepancy with exact provenance |
| lumpability defect `||K_RJ-J Kbar||` | `behavioral_partition.LumpabilityWitness` | within-class successor interval or exact equality for every frozen action |
| return-memory `sum ||BD^jC||` | `certificates.ReturnMemoryBound` | finite episode horizon, typed blocks, and independently bounded products; no infinite-horizon inference |
| weighted compression/lifting erratum E1 | `quotient_generator.WeightedCompression`, `WeightedLifting` | `C_omega L_mu,omega = I` and `|K_mu z| <= M|z|` on T0-W plus randomized finite fixtures |
| exact / interval / nominal quotient tiers | `quotient_generator.{ExactFinite,CertifiedInterval,ObservedInterval,Nominal}Operator` | tier/conversions are encoded; observed intervals cannot enter a hard envelope or absence-of-counterexample promotion |
| positive envelope / transfer theorem | `envelope.FiberEnvelope`, `CocycleCertificate` | accepts only exact finite or certified-upper operators; fiber extension is monotone; missing extremizer and nilpotent transient fixtures fail shortcuts |
| first/second-moment pressure | `envelope.PressureCertificate` | separate branching-adjusted `p1/p2` products and a two-threshold regression |
| MaxEnt existence, orbit law and E6 operator scope | `maxent.FiniteFiberLaw`, `OrbitReferenceLaw`, `MaxEntResult`, `OperatorSpanResidual` | distinguish interior, boundary, outside hull, singular statistics, and numeric failure; verify orbit correction and operator residual |
| nested local representation | `similarity.LocalTower` | deterministic restriction map `Z_(R+1)->Z_R` and measured inter-radius commutator/residual |
| node/edge global representation | `similarity.GlobalMeasure` | retain `M1,rho1,M2,rho2`; path residual is explicit when edge additivity is insufficient |
| R/N/G finite-approximation transport | `similarity.ApproximationLevelId`, `RadiusMorphism`, `WordDepthMorphism`, `GranularityMorphism` | node/edge mass transport, coverage transport, commutator bound and `d_coarse(Px,Py) <= d_fine(x,y)+e_level` |
| conditional information tail | `certificates.ConditionalInformationTail` | declared estimator/tier, held-out grouping and finite-sample bound; never hard from a point estimate |
| cross-covariance inflation | `certificates.CrossCovarianceBudget` | correlated fixture recovers off-diagonal contribution; independence fixture reduces to diagonal |
| predictive/safety metric split | `similarity.PredictiveDistance`, `PositiveDistance` | types cannot be substituted; only a certified `L_+` and coverage object construct a safety majorant |
| true-target transport erratum E4 | `similarity.TargetResidualBound` | `|V_true-U(q_R)| <= e_R` with hard/statistical tier and coverage explicitly stored |
| typed telescoping erratum E5 | `certificates.TypedPipelineBound` | every stage declares domain, codomain, norm, transport constants, and an independently bounded residual |
| active CEGAR | `locality_cegar.Query`, `Counterexample`, `split` | exact Lean counterexamples split classes; no-counterexample results remain statistical unless witness-complete is proved |
| fail-closed selector | `selection.CertificateToken`, `LexicographicSelector` | utility ranking is unreachable without a valid hard/robust policy token; rejection/abstention remain in evaluation denominator |

## 7. Work packages, dependencies, and exit gates

### WP0 -- plan, governance, and strict boundary

Deliverables:

- this document and its exact Git/CI anchor;
- strict semantic record definitions and legacy-adapter policy;
- one work-package board whose statuses are `not_started`, `active`, `passed`,
  `blocked`, `killed`, or `deferred`;
- no apparatus source in the plan commit.

Exit: the exact three-path amendment commit is pushed and green.

### WP1 -- minimum U'0/U'1 repair for the probes

Commit budget: at most three pushed implementation commits.

1. Path-invariant `StateIdentityKey`, first-occurrence normalization, complete
   reachable local-context/universe/assignment coverage, and full compare after
   hash. Process-local state IDs and unreachable historical mctx declarations
   are excluded from the canonical signature.
2. Explicit target routing, exact before/after assigned-mvar difference,
   closed/new goal sets, all-goal side-effect sweep, and a checked state-discard
   operation so an insert-only worker cannot grow with every attempted edge.
3. Independent replay from immutable before-state with exact response/post-state
   comparison.

WP1 also introduces the strict raw RPC client and core contracts before the
runner exists:

```text
lean_rgc/lean/kernel_rpc_client.py
lean_rgc/lean/kernel_state_identity.py
lean_rgc/odlrq/__init__.py
lean_rgc/odlrq/contracts.py
```

`contracts.py` owns the semantics/frame/domain IDs, `StateIdentityKey`,
`ActionSymbol`, `BoundAction`, `ReplayComparableResponse`,
`ExactKernelTransitionCore`, `U05ProbeTransition`, coverage and censor types.
The client returns strict raw RPC records and never routes them through
`AuditRecord.from_dict`. To remain inside the frozen four-commit path allowlist,
the legacy `rpc_protocol_version=v2` and kernel-state response schema `v3`
remain byte-compatible and unchanged. U05 adds separately versioned
`u05_semantics_version=v1` and `state_identity_schema=u05-state-identity-v1`
records, and bumps only `KERNEL_RPC_WORKER_VERSION`. Any change requiring the
legacy protocol/state-schema literals or their out-of-allowlist tests blocks
this phase; it cannot be smuggled in as a U05 version bump.

Every transition supplies the same explicit heartbeat cap and bypasses all
audit/result caches. Consumption telemetry, episode telemetry, M3 read-set
completeness, and full M4 transport recovery remain unresolved if not needed by
the three probes; their absence is recorded and cannot support later stages.
`init_state` applies the same task/prefix cap to each prefix tactic; apply and
replay echo requested and effective option/counter units with source
`explicit_action`. Prefix/action cap mismatch or a missing effective-cap echo is
`U05_PREREQUISITE_BLOCKED`. The episode-heartbeat value is the typed sentinel
`NOT_ENFORCED_DEVELOPMENT_ONLY`, never a hard-tier budget.

Ordinary failure does not retain a child KState. After immediate replay and
canonicalization, duplicate/nonfrontier children are released. Each task uses a
fresh worker; after a state's complete fixed-alphabet transition row is sealed,
the parent is released. The worker bound is frozen as

```text
n_states <= live_unexpanded_frontier_count + 1 transient child.
```

Only queued/unexpanded entries require a live RPC state. Replay reuses the one
transient-child slot sequentially; there is no unspecified overhead.

Exit:

- commuting-path equality and different-response inequality identity tests;
- non-head target is actually changed while the head remains unchanged;
- cumulative assignments fail the delta test and true differences pass;
- a side-effect-assigned tail goal is removed from the open queue;
- replay uses a second execution, not serialization of the first result;
- alpha-renaming, structured universe, assignment-history, and forced-hash-
  collision fixtures preserve full-compare identity semantics;
- truncated graph/support input is rejected for every field required by the
  U05 response schema;
- equal identities produce identical five-coordinate debt readouts; and
- ordinary failure enters an absorbing sink while wall/transport/resource
  censors produce no transition.

Any missing exit condition yields `U05_PREREQUISITE_BLOCKED`.

### WP2 -- U'1.5 deterministic measurement apparatus

Commit budget: one pushed implementation commit after WP1.

Deliverables:

```text
lean_rgc/odlrq/rule_algebra.py
lean_rgc/odlrq/reachable_chart.py
lean_rgc/odlrq/hankel.py
lean_rgc/evals/uprime_u05_kill_probes.py
tests/test_uprime_u05_identity.py
tests/test_uprime_u05_kill_probes.py
tests/tier_manifest.json
```

The ODLRQ core implements action words, totalization, task-seeded reachability,
the three-table representation below, and exact rational Hankel rank. The U05
module is a thin preflight/orchestration/reporting runner over that core; WP4
hardens rather than replaces these semantics. It uses an exact input allowlist,
numeric conditioning, deterministic ordering, and a single atomic JSON result.
It never globs the repository root and does not import any legacy quotient or
evidence-ledger implementation.

```text
state_table:
  full StateIdentityKey -> {
    full_signature,
    expansion_status in {queued, expanded},
    live_rpc_state_id: optional
  }
transition_table:
  (StateIdentityKey, fixed ActionSymbol) -> one replayed concrete/derived event
word_table:
  (task seed, exact symbolic word) -> StateIdentityKey | CLOSED | SINK
```

State-table deduplication never deletes action-word occurrences. Concrete
state/action pairs execute once; the word table is completed by bounded dynamic
programming. Only queued/unexpanded entries hold a live RPC state. Expanded
entries retain their full signature and sealed transition row but no live state
ID; a later word occurrence consults the sealed row and never resurrects or
reexecutes it.

Unit/property tests use only disjoint `unit_u05_*` toy statements, hand-built
transition graphs, and hand-built matrices. They install open/import sentinels
for the five production task IDs, the production matrix evaluator, and all four
excluded root files. Tests may verify the frozen matrix's literal digest without
enumerating it, but may not compute KP1--KP3 on it. The production entrypoint
must refuse before task access unless `UPRIME_U05_EXECUTE=1`, a full anchor, and
the exclusive reservation preflight are all present.

Exit: synthetic unit/property tests pass locally and in CI, the implementation
head is pushed and green, and the four-commit WP1+WP2 budget has not been
exceeded. Budget exhaustion yields one consolidated
`U05_PREREQUISITE_BLOCKED` result and ends this phase.

### WP3 -- one development-only U'0.5 execution

The frozen one-look U05 development execution occurs once on local Windows CPU
after WP2 is pushed and green. It reads only the inline task/action grammar
frozen below. It is not a canonical RPC diagnostic rerun and is not run in CI.
Deterministic unit tests may be rerun freely only on disjoint toy fixtures; they
may not invoke the production runner, production U05 task IDs, or the frozen
task/action matrix. No component receives a separate preregistration/result
triplet.

The only network authority in this phase is a pre-matrix governance control
plane: pushing `refs/heads/codex/uprime-odlrq-plan` and read-only verification of
`refs/remotes/origin/codex/uprime-odlrq-plan` plus hosted workflow
`.github/workflows/ci.yml` (`name: CI`, job key `pytest`). The accepted conclusion
is exactly `success` for a `push` run whose head SHA is the candidate and whose
workflow blob is the candidate's blob. The attempt receipt freezes branch/ref,
workflow path/blob, run ID, job ID, head SHA, event, and conclusion. The U05
outer launcher's pre-receipt preflight is the only Python actor allowed to query
that control plane. It derives the fields by read-only `gh api` queries to the
`origin` repository's Actions workflow-runs and selected run's jobs endpoints;
caller-supplied run/job fields are never trusted. After validation it strips
`GH_TOKEN`, `GITHUB_TOKEN`, proxy variables, `SSH_AUTH_SOCK`, repository URL, and
all control-plane arguments before spawning the same module in guarded
`--measurement-child` mode. That measurement child, its Lean child, task code,
and the measurement phase receive no endpoint or credential and may initiate no
network access. The exception covers no model, task, remote host, experimental
data, or post-matrix query.

The exact command shape is:

```powershell
$sourceRoot = (git rev-parse --show-toplevel).Trim()
$anchor = (git rev-parse HEAD).Trim()
$runRoot = Join-Path $env:TEMP "uprime_u05_$($anchor.Substring(0,12))"
git worktree add --detach $runRoot $anchor
Set-Location -LiteralPath $runRoot
$receipt = "runs/uprime_u05_20260711/attempt_receipt_$($anchor.Substring(0,12)).json"
$raw = "runs/uprime_u05_20260711/runner_raw_$($anchor.Substring(0,12)).json"
$artifact = "docs/experiments/artifacts/uprime_u05_20260711/u05_kill_probes.json"
$env:UPRIME_U05_EXECUTE = '1'
$env:PYTHONNOUSERSITE = '1'
python -m lean_rgc.evals.uprime_u05_kill_probes `
  --repo-root . `
  --anchor $anchor `
  --upstream refs/remotes/origin/codex/uprime-odlrq-plan `
  --ci-workflow .github/workflows/ci.yml `
  --ci-job pytest `
  --accepted-ci-conclusion success `
  --attempt-receipt $receipt `
  --raw-output $raw `
  --artifact $artifact
```

Preflight requires a disposable detached worktree with empty porcelain status,
a full 40-hex `HEAD`, upstream ancestry, and the unique successful `push` CI
run/job derived by the named outer-launcher query at that exact head. The local
workflow Git blob must match the candidate; a zero/multiple-match query blocks.
Preflight also requires absence of receipt/raw/artifact/matrix-open marker,
empty formal rerun registry, and byte equality for every amendment/input anchor.
It freezes
the repo-root
`lean-toolchain` presence/absence and blob when present, resolved Lean
version/build, executed Lean binary SHA-256, Python executable,
and the resolved `lean_rgc` import path under this worktree. User-site and import
shadowing are forbidden.

The outer launcher first writes canonical schema
`lean-rgc-uprime-u05-attempt-receipt-v1.0` by exclusive create, before matrix
open. The immutable receipt binds the candidate, task and action matrix digests,
all semantic/environment digests, exact command/environment, control-plane CI
receipt, and the three output paths. Immediately before the first production
task record is materialized, it exclusive-creates a canonical matrix-open marker
whose SHA-256 is also bound by the final envelope. Exit `0` means a complete
valid development result, `2` means prerequisite-blocked, `3` means invalid or
already consumed, and `4` means partial/internal failure.

The tracked artifact is always canonical schema
`lean-rgc-uprime-u05-attempt-envelope-v1.0`, serialized as UTF-8
`json.dumps(..., sort_keys=True, separators=(",", ":"), ensure_ascii=False)`
plus one LF. Its tagged union member is one of `runner_complete`,
`runner_prerequisite_blocked`, `runner_partial`, or `launcher_recovery`. Every
member contains the exact receipt bytes as base64 plus length/SHA-256, candidate
and matrix digests, matrix-marker presence/bytes/hash, `look_consumed`, process
exit/termination and exception class/message, and raw-child-output
presence/length/SHA-256/base64. Probe fields are admitted only for a complete,
schema-valid raw child result. Thus raw bytes are preserved without parsing or
reserialization even when the child result is partial.

The launcher writes this envelope directly to the future tracked artifact path
inside the detached worktree by same-directory temporary file, flush/fsync, and
atomic replace; no later byte-copy publisher is allowed. If the launcher is
interrupted after receipt creation, the only permitted follow-up is the same
entrypoint with `--recover-only`: it may read receipt, matrix marker, and partial
raw bytes and emit `launcher_recovery`, but its task/matrix-open function is
hard-disabled. It cannot authorize or perform another attempt. A receipt with no
matrix marker yields `look_consumed=false` and ends this phase as prerequisite-
blocked; a present marker always yields `look_consumed=true`.

Any attempt that opens the matrix consumes the one look, including a crash,
timeout, partial artifact, or nonzero exit. Every consumed outcome must produce
the tracked envelope and consolidated result without rerunning at the candidate
head. A control-plane/preflight failure before receipt creation does not consume
the look; after receipt creation, recovery/result publication ends the phase.
This runner does not call or activate the formal canonical RPC registry/claim
system.

This one-look rule is a procedural single-researcher scheduling commitment, not
cross-machine or protected attestation: deleting the disposable worktree or
running the candidate elsewhere could evade the local guard. Any known second
matrix-open event invalidates scheduling inference from both attempts; neither
result may license a survivor amendment. The receipt and marker evidence are
embedded in the tracked envelope/result so ordinary cleanup cannot erase the
only recorded consumption evidence.

One consolidated execution record reports all prerequisites, U05-KP1/KP2/KP3,
costs, failures, and disposition. A result commit follows the last allowed
implementation commit as sole parent. Its exact result paths are:

```text
docs/experiments/uprime_odlrq_u05_execution_2026-07-11.md
docs/experiments/artifacts/uprime_u05_20260711/u05_kill_probes.json
lean_rgc/evals/uprime_rpc_litmus.py
tests/test_uprime_rerun_license.py
```

The tracked JSON is the byte-exact complete canonical outer envelope described
above; the result document reports its SHA-256 and Git blob and reports the
embedded raw-child hash rather than selecting only favorable fields.

### WP4 -- exact local event calculus and bounded ground truth (roadmap only)

Begins only for branches that survive WP3 and only after a separate, pushed,
green `U'CPU-survivor implementation bundle amendment` names its capability-
selected paths, inputs, budgets, and nonclaim endpoints.

Before WP4 emits any exact artifact, an `ExactAdmissionCompletionGate` must name
and pass every consumer field: target/delta/replay/cap/censor semantics;
nontruncated local region and boundary interface; M3 read/support coverage when
the artifact makes a locality claim; environment identity; and strict domain
membership. Skeleton code may exist under the future bundle, but no incomplete
record is serialized as exact.

- strict contracts and legacy adapters: 3--5 engineer-days;
- rule algebra and task-seeded reachability: 5--8 days;
- behavioral refinement and exact/interval response signatures: 5--7 days;
- Hankel ground truth hardening: 5--8 days.
- tier core types and prohibited-conversion tests are completed before the first
  learner output: `ExactFiniteOperator`, `CertifiedIntervalOperator`,
  `ObservedIntervalOperator`, `NominalOperator`, and
  `ProposedNominalPartition`.

Exit: finite charts terminate, every exact block has full action closure, all
interval blocks contain their concrete transitions, and no hard record is
truncated.

### WP5 -- Lean-oracle locality CEGAR (roadmap only)

Estimated 15--25 engineer-days after WP4.

The learner receives before-only local open-graph features. It may propose
merge/split candidates, boundary variables, radius, causal memory, and the next
query. Query families are congruence, identification, memory, and safety. Exact
Lean counterexamples split a class. Successful minimal proof support is a
positive label only when it is nontruncated; failed/partial actions retain only
the boundary/read evidence actually observed.

Validation splits by task/state family, not random rows. Inputs may not contain
outcome-side `audit_status`, `carrier_delta`, or future state features. Query
budget, seed, tie-break, cache policy, and timeout are fixed before the pilot.

Every learner merge is a `ProposedNominalPartition`. A Lean counterexample may
force a split, but no successful/failed search promotes a merge to exact. The
first learner MVP is limited to congruence-separator queries; identification,
memory, and safety acquisition are later named substages.

The future U'1.5-L amendment freezes the paired task/query matrix, prediction
target, proper loss, query-cost denominator, coverage/abstention, baseline,
seed/tie-break, confidence interval, and oracle censor policy. Exit requires a
paired held-out curve, not an unqualified “beats baseline” statement, while
every exact counterexample remains preserved. This licenses no hard claim from
counterexample absence.

### WP6 -- tiered quotient generator (roadmap only)

Estimated 7--10 engineer-days.

- exact tier: identical match/action successor signatures with witnesses;
- certified interval tier: an independent upperness witness contains the full
  declared concrete domain;
- observed interval tier: contains only observed/constructed events and remains
  empirical/statistical;
- nominal tier: learned or MaxEnt conditional law with support and uncertainty.

`FiberEnvelope` accepts only `ExactFiniteOperator` or
`CertifiedIntervalOperator`. There is no conversion from observed/nominal to
exact/certified. Exit: allowed-conversion and forbidden-conversion tests, tier
monotonicity, representative-action substitution kill test, interval
undercoverage kill fixture, and strict round trips.

### WP7 -- U'2 worst-case envelope and lexicographic gate (roadmap only)

Estimated 8--12 engineer-days.

Development-only implementation is barred until a separate, committed, pushed,
and green `U'2--U'4 development construction bundle amendment` fixes the source
and test allowlist, commit/resource budget, synthetic or already-contaminated
development inputs, calibration endpoints, and no-protected-read/no-scientific-
claim boundary. It may build WP7--WP10 only after the surviving WP4/WP6
substrate exists. Protected inputs, protected K-series execution, deployment,
and scientific claims remain barred until a filled Amendment A is committed,
pushed, and green.

Implement the corrected weighted coordinates, finite-horizon layer products,
fiber upper construction, first- and second-moment channels, return-memory
bracket, and a checker for `M_n^T w_(n+1) <= theta_n w_n`. Spectral radius is an
auxiliary stationary diagnostic only.

A hard `FiberEnvelope` is constructed only from (1) a complete frozen
`X_Lambda` fiber carrying `FiberCompletenessWitness`, or (2) an independently
verified upper-superset construction. A task-seeded sample maximum is never a
hard supremum. Runtime states require `DomainMembershipWitness`; an
outside-domain state rejects/abstains. Adding a concrete fiber element may leave
the envelope unchanged or increase it, never decrease it.

The online decision is lexicographic:

```text
semantic/frame mismatch
  -> reject
hard envelope/domain failure
  -> reject / rollback / abstain
certified interval or certificate-required support failure
  -> reject / abstain
nominal model unavailable/fails while CertificateToken remains valid
  -> fixed utility fallback over already-certified candidates only
all required certificate layers pass
  -> utility ranking
```

`ObservedIntervalOperator` and `NominalOperator` cannot construct a
`CertificateToken`. Nominal fallback can change only utility within the set that
already passed every required hard/certified constraint; it cannot replace a
hard envelope, domain witness, robust-support token, or finite-depth gate.

Exit: missing-extremizer, fiber-extension monotonicity, nilpotent/nonnormal
transient-gain, and weighted-coordinate T0 fixtures pass; the gate is reachable
in both directions, rejects some but not all
candidates on a frozen development fixture, and demonstrably changes at least
one ranking. Otherwise it is nonbinding and U'2 deployment is killed.

### WP8 -- U'3 MaxEnt nominal lifting (roadmap only)

Estimated 5--8 engineer-days.

Implement a finite-fiber, log-sum-exp stabilized solver and a checker returning
one of:

```text
INTERIOR_SOLVED
BOUNDARY_NO_FINITE_PARAMETER
OUTSIDE_HULL
SINGULAR_STATISTICS
NUMERIC_FAILURE
```

The reference law, automorphism/orbit correction, sufficient statistics,
moment target, support, and KL radius are artifacts. MaxEnt may choose a nominal
lifting only after the hard envelope domain is fixed. Its evaluation uses a
proper prediction/risk endpoint and a baseline, not safety pass rate.

Exit: T0-ME fixtures, operator-span residual bound, moment residual, simplex,
support, and KL-robust row-load checks pass.

### WP9 -- U'4 finite-approximation-stable global similarity (roadmap only)

Estimated 10--15 engineer-days.

Implement nested local states, deterministic fine-to-coarse restriction,
forward/backward-weighted node and edge measures, total masses, separate
predictive and positive distances, and a true-target residual channel. Radius
and action-word depth are independent; action granularity is a third axis.

`ApproximationLevelId=(ObservationFrameId,ReachableDomainId,R,N,G)` owns three
typed maps: `RadiusMorphism`, `WordDepthMorphism`, and
`GranularityMorphism`. Each map carries node/edge mass and coverage transport,
an operator commutator bound, and a residual satisfying a frozen inequality of
the form `d_coarse(Px,Py) <= d_fine(x,y)+e_level`. Residual curves must admit a
registered Cauchy/remainder majorant before “finite-approximation-stable” is
used.

Required artifacts are `local_tower.json`, `global_measure.json`,
`level_transport.json`, and `similarity_certificate.json`.

Each `(R,N,G)` result reports:

```text
frame defect
locality/naturality defect
lumpability defect
finite-horizon return-memory mass
conditional information tail
Hankel rank and conditioning
support/coverage
first- and second-moment pressure
envelope contraction
true-target residual and tier
inter-radius / local-global commutator
```

Exit: restriction consistency, finite-radius remainder, node-only versus
node+edge aliasing, cross-covariance inflation, coverage, and target-residual
tests pass across all three morphism types. A hard `SafetyMajorant` constructor
requires a hard `L_+`, hard true-target residual, and coverage witness. A learned
`L_+` or zero sample violations remains nominal/statistical-only.

### WP10 -- integrated runner and CPU pilot (roadmap only)

Estimated 5--8 engineer-days after WP9.

The new runner remains independent of the existing selector until it can emit
one typed end-to-end telescoping certificate. Any CPU pilot beyond U05 requires
the development-construction bundle authority above. On synthetic or already-
contaminated inputs, development K-series calibration fixes a complete CPU
candidate and fills the Amendment A skeleton without looking at reserved
outcomes. No protected K-series execution occurs in this construction phase.

### WP11 -- Amendment A and protected/GPU stage (roadmap only)

No protected K1--K4 execution, protected-data U'2--U'4 construction, deployment
or claim, remote build, model download, or GPU training occurs until a filled
Amendment A is committed, pushed, and green. The only earlier U'2--U'4 work is
the separately authorized CPU development construction described above.
Large learned graph representation and acquisition models are the only expected
GPU work. Every hard certificate is rechecked by the CPU reference
implementation.

### WP12 -- U'5 paired sealed evaluation (roadmap only)

U'5 is last and requires its own complete sealed-evaluation authorization. The
primary endpoint is paired solve rate on the identical full task set under equal
global budgets. Abstentions and zero-action tasks remain in the denominator;
coverage, certificate failures, heartbeats, wall time, LLM calls, and cost are
co-primary/co-reported as previously registered.

The four-commit U05 budget is a deliberate prerequisite kill budget, not a
completion-time estimate. If the screen survives, the roadmap through an
independent CPU MVP is approximately 12--18 engineer-weeks; hardening the full
upper stack is approximately 4--6 solo engineer-months. Occurrence-targeted
`rw`, macro decomposition, and sealed proposer construction are outside that
estimate.

### Mandatory regression families

WP1/WP2 must cover alpha-renaming, structured universes, assignment-history
commutation, truncated required fields, forced hash collision/full compare,
fixed action alphabet when first/last bind the same goal, sink absorption,
closed-at-depth-one extension exclusion from every KP1 compression numerator,
wall/transport censoring, worker-state bounds, word-occurrence preservation,
Hankel row/column permutation invariance, and known exact rational-rank
fixtures.

Future bundle/Amendment A tests must additionally cover interval
undercoverage, fiber-extension envelope monotonicity, a missing extremizer,
nilpotent/nonnormal transient gain, MaxEnt primal/dual residual and orbit
correction, boundary/outside/singular MaxEnt states, all R/N/G transport
commutators, node-only aliasing, cross covariance, outcome-side feature leakage,
CEGAR counterexample preservation/no-counterexample nonpromotion, and the type
rule that utility ranking cannot run without a valid certificate token. They
also require a negative regression proving that a failed certified-support
token cannot be bypassed by any nominal fallback.

## 8. Frozen U'0.5 development universe

The U05 runner uses no task file from the repository root. Its source contains
the following exact JSON records. The matrix digest is computed from the array
under UTF-8 `json.dumps(records, sort_keys=True, separators=(",", ":"),
ensure_ascii=False)` and is frozen by the plan-commit test.

```json
[
  {"task_id":"u05_identity","statement":"forall P : Prop, P -> P","imports":["Lean"],"prefix":"intro P\nintro h","max_heartbeats":20000},
  {"task_id":"u05_pair","statement":"forall P Q : Prop, P -> Q -> P /\\ Q","imports":["Lean"],"prefix":"intro P\nintro Q\nintro hP\nintro hQ","max_heartbeats":20000},
  {"task_id":"u05_split","statement":"True /\\ True","imports":["Lean"],"prefix":"","max_heartbeats":20000},
  {"task_id":"u05_nested_split","statement":"(True /\\ True) /\\ True","imports":["Lean"],"prefix":"","max_heartbeats":20000},
  {"task_id":"u05_nat_zero","statement":"forall n : Nat, n + 0 = n","imports":["Lean"],"prefix":"intro n","max_heartbeats":20000}
]
```

The canonical task-matrix SHA-256 is
`C86569C9C5A793C842BD3F4D7E5795A16C5B6C0B8F6E806F3D30D6A8B571E0E3`.

The action alphabet is the following exact canonical JSON array. Its digest uses
the same UTF-8 canonicalization as the task array. `FVAR_TYPE(local:i)` means the
canonicalized type is the local declaration at zero-based canonical local index
`i`; the runtime binder must match both the frozen declaration ordinal and this
normalized signature. No readable binder name is used to infer a selector.

```json
[
  {"action_id":"a00_constructor_first","opcode":"constructor","target_selector":"first","premise_slot_rule_id":null,"premise_selector_ordinal":null,"expected_normalized_type_signature":null,"global_constant":null,"opaque_hyperedge_source":null,"opaque_hyperedge_digest":null,"max_heartbeats":20000},
  {"action_id":"a01_constructor_last","opcode":"constructor","target_selector":"last","premise_slot_rule_id":null,"premise_selector_ordinal":null,"expected_normalized_type_signature":null,"global_constant":null,"opaque_hyperedge_source":null,"opaque_hyperedge_digest":null,"max_heartbeats":20000},
  {"action_id":"a02_exact_h_first","opcode":"exact_local","target_selector":"first","premise_slot_rule_id":"local_decl_1_type_local_0","premise_selector_ordinal":1,"expected_normalized_type_signature":"FVAR_TYPE(local:0)","global_constant":null,"opaque_hyperedge_source":null,"opaque_hyperedge_digest":null,"max_heartbeats":20000},
  {"action_id":"a03_exact_h_last","opcode":"exact_local","target_selector":"last","premise_slot_rule_id":"local_decl_1_type_local_0","premise_selector_ordinal":1,"expected_normalized_type_signature":"FVAR_TYPE(local:0)","global_constant":null,"opaque_hyperedge_source":null,"opaque_hyperedge_digest":null,"max_heartbeats":20000},
  {"action_id":"a04_exact_hP_first","opcode":"exact_local","target_selector":"first","premise_slot_rule_id":"local_decl_2_type_local_0","premise_selector_ordinal":2,"expected_normalized_type_signature":"FVAR_TYPE(local:0)","global_constant":null,"opaque_hyperedge_source":null,"opaque_hyperedge_digest":null,"max_heartbeats":20000},
  {"action_id":"a05_exact_hP_last","opcode":"exact_local","target_selector":"last","premise_slot_rule_id":"local_decl_2_type_local_0","premise_selector_ordinal":2,"expected_normalized_type_signature":"FVAR_TYPE(local:0)","global_constant":null,"opaque_hyperedge_source":null,"opaque_hyperedge_digest":null,"max_heartbeats":20000},
  {"action_id":"a06_exact_hQ_first","opcode":"exact_local","target_selector":"first","premise_slot_rule_id":"local_decl_3_type_local_1","premise_selector_ordinal":3,"expected_normalized_type_signature":"FVAR_TYPE(local:1)","global_constant":null,"opaque_hyperedge_source":null,"opaque_hyperedge_digest":null,"max_heartbeats":20000},
  {"action_id":"a07_exact_hQ_last","opcode":"exact_local","target_selector":"last","premise_slot_rule_id":"local_decl_3_type_local_1","premise_selector_ordinal":3,"expected_normalized_type_signature":"FVAR_TYPE(local:1)","global_constant":null,"opaque_hyperedge_source":null,"opaque_hyperedge_digest":null,"max_heartbeats":20000},
  {"action_id":"a08_exact_True_intro_first","opcode":"exact_const","target_selector":"first","premise_slot_rule_id":null,"premise_selector_ordinal":null,"expected_normalized_type_signature":"CONST(True)","global_constant":"True.intro","opaque_hyperedge_source":null,"opaque_hyperedge_digest":null,"max_heartbeats":20000},
  {"action_id":"a09_exact_True_intro_last","opcode":"exact_const","target_selector":"last","premise_slot_rule_id":null,"premise_selector_ordinal":null,"expected_normalized_type_signature":"CONST(True)","global_constant":"True.intro","opaque_hyperedge_source":null,"opaque_hyperedge_digest":null,"max_heartbeats":20000},
  {"action_id":"a10_simp_Nat_add_zero_first","opcode":"opaque_tactic","target_selector":"first","premise_slot_rule_id":null,"premise_selector_ordinal":null,"expected_normalized_type_signature":null,"global_constant":null,"opaque_hyperedge_source":"simp only [Nat.add_zero]","opaque_hyperedge_digest":"CE264CA0DB8A2B6CD05AFAB00A3C4E3572BB83007BA043E8331ECC681400380D","max_heartbeats":20000},
  {"action_id":"a11_simp_Nat_add_zero_last","opcode":"opaque_tactic","target_selector":"last","premise_slot_rule_id":null,"premise_selector_ordinal":null,"expected_normalized_type_signature":null,"global_constant":null,"opaque_hyperedge_source":"simp only [Nat.add_zero]","opaque_hyperedge_digest":"CE264CA0DB8A2B6CD05AFAB00A3C4E3572BB83007BA043E8331ECC681400380D","max_heartbeats":20000}
]
```

The canonical action-matrix SHA-256 is
`6EA21704F48153362504D4AC7F753C30B8EF6FBDFB0FD98B15A37E56120D393D`.
Word order is `action_id` lexicographic over these frozen IDs. The alphabet has
exactly 12 `ActionSymbol` values on every state. `first` and `last` remain
distinct symbols and Hankel columns when they bind the same goal. Missing target,
local selector, signature match, or constant enters the typed sink. Task prefix
bytes and their digest are part of `TransitionSemanticsId`. The two `simp`
records are frozen kernel-audited opaque hyperedges, not decomposed traces.

Frozen limits:

```text
maximum symbolic word depth      3
maximum unique states per task   256
maximum unique states total      1024
maximum primary state/action attempts 12288
maximum replay reexecutions      12288
maximum prefix tactic executions 7
maximum total Lean tactic executions 24583
maximum symbolic word occurrences 15000
maximum Hankel cells              100000
task/prefix maxHeartbeats option   20000
per-action maxHeartbeats option  20000
episode heartbeat budget         NOT_ENFORCED_DEVELOPMENT_ONLY
episode telemetry coverage       false
per-action wall timeout           30 seconds
whole-run wall limit              30 minutes
cache policy                      bypass
repo-root lean-toolchain status  absent_by_design
expected Lean version prefix     Lean (version 4.31.0,
executed Lean binary SHA-256     9B216DEB50D37C32C829D1EFAAA5BAFD5560417D382DF35A815489E31A31593F
word order                        length, then action-id lexicographic
state tie-break                   full StateIdentityKey bytes
look count                        one
```

The execution counters include every concrete primary and replay attempt.
Derived `CLOSED`/`SINK` absorbing extensions use sealed rows and enter none of
the primary, replay, prefix, or total Lean tactic-execution counters.

Reaching a state/query/wall/resource cap is `U05_PREREQUISITE_BLOCKED`, not
evidence that rank, quotient index, or envelope behavior failed.

## 9. U05-KP1 -- exact identity/compression screen

At cumulative depths `<= 1`, `<= 2`, and `<= 3` report:

```text
N_occ_open(<=d) eligible nonempty action-word occurrences ending OPEN
N_id_open(<=d)  distinct full StateIdentityKey values among those occurrences
C_id_open(<=d)  N_occ_open(<=d) / N_id_open(<=d)
N_obs_open(<=d) distinct BehavioralObservationKey values among those
                 occurrences under
                 BehavioralResponseProjectionId=u05_current_observation_v1
C_obs_open(<=d) N_occ_open(<=d) / N_obs_open(<=d)
P_raw_open(<=d) mismatching unordered occurrence pairs / all unordered
                 occurrence pairs inside equal-full-identity OPEN classes
```

`u05_current_observation_v1` is the canonical tuple `(totalized status,
open-goal count, reachable open-mvar count, reachable pending-typeclass count,
carrier multiplicity count, reachable Expr-node count)`. Future-continuation
behavior is not claimed here; KP3 owns that question.

The primary KP1 denominator contains only nonterminal `OPEN` occurrences.
`CLOSED` and `SINK` occurrences are excluded from every primary count and KP1
disposition. A nontrivial identity class must have `totalized_status=open`,
contain two different nonempty action words, and pass full-signature comparison.
The empty word and repeated serialization of one occurrence are excluded.
First-entry close words, first-entry ordinary-failure/sink words, derived closed
extensions, derived sink extensions, censors, and eligible-open coverage are
reported as separate terminal diagnostics. In particular, extending a word
whose proper prefix is `CLOSED` or `SINK` cannot increase any KP1 compression
numerator.

Disposition:

- at least two nontrivial open identity classes spanning two task IDs, with
  `C_id_open(<=3) >= 1.10`, is `U05_KP1_SCALE_READY`;
- one or more nontrivial open identity classes below that scale threshold is
  `U05_KP1_EXISTENCE_ONLY` and licenses only an exact-partition hardening draft;
- no open identity compression at any cutoff, but
  `N_obs_open(<=d) < N_id_open(<=d)` at one or more cutoffs, is
  `U05_KP1_OBSERVATION_ALIAS_ONLY`;
- `N_occ_open(<=d)=N_id_open(<=d)=N_obs_open(<=d)` at all cutoffs is
  `U05_KP1_NO_IDENTITY_COMPRESSION`;
- a valid result with an undefined required ratio or insufficient eligible-open
  support for the preceding exhaustive cases is `U05_KP1_INCONCLUSIVE`;
- missing identity/replay/prefix-closure evidence is
  `U05_PREREQUISITE_BLOCKED`.

`U05_KP1_EXISTENCE_ONLY` is not scale readiness. `N_obs_open` and
`C_obs_open` are descriptive diagnostics; observation aliasing never satisfies
the exact-identity compression gate. `U05_KP1_NO_IDENTITY_COMPRESSION` kills
investment in exact discrete compression on this frozen open-state fragment,
but does not alone kill a low-rank predictive representation.

## 10. U05-KP2 -- successful-trajectory noncontractivity screen

For each transition use the exact typed debt vector

```text
D(s) = (
  open goal count,
  open unassigned mvar count,
  pending typeclass count,
  carrier-atom count,
  expression-node count
)
```

Every coordinate is computed from the reachable canonical state signature, not
from the legacy chart normalizers: ordered open goals; reachable unassigned
mvars; reachable pending class-mvars; the multiplicity-preserving frozen
per-goal carrier extractor; and the reachable canonical Expr DAG. Carrier
extractor version and multiplicity rule belong to `ObservationFrameId`.

A step is componentwise contractive when `D(after) <= D(before)` in every
coordinate and at least one inequality is strict. All other successful/partial
steps are noncontractive. A successful trajectory is an action word that ends
in `closed` without sink or censor. The decision denominator contains only
replay-verified `open -> open` transitions lying on at least one eventually
closed trajectory; the terminal `open -> closed` transition is reported
separately and cannot create a survival window by itself. Report the one-step
noncontractive fraction, each coordinate's increase fraction, longest
noncontractive run, and existence of a block of length 1, 2, or 3 satisfying

```text
block_contracts(t,k) iff
  D(s_(t+k)) <= D(s_t) componentwise
  and D(s_(t+k)) != D(s_t),
```

with both endpoints open.

Disposition:

- at least one valid successful trajectory and one contractive block is
  `U05_KP2_EVENTUAL_WINDOW`;
- every eligible open-to-open block is noncontractive and no block of length at
  most 3 contracts is
  `U05_KP2_NO_COMPONENTWISE_WINDOW_ON_FRAGMENT`;
- no eligible open-to-open block is `U05_KP2_FRAGMENT_INCONCLUSIVE`;
- inexact delta or a censor is
  `U05_PREREQUISITE_BLOCKED`.

This probe screens only the componentwise debt gate on this fragment.
Componentwise contraction is sufficient, not necessary, for a positive
weighted Lyapunov contraction. Therefore a no-window result does not kill a
weighted or finite-horizon envelope. It does not establish the protected K2
reachability, non-vacuity, or ranking-effect endpoint.

## 11. U05-KP3 -- prefix-closed response Hankel screen

For total cutoff `d in {1,2,3}`, define

```text
P_d = {p : |p| <= floor(d/2)}
S_d = {s : |s| <= ceil(d/2)}
H_d[(task,p),(s,channel)] = channel(tau_(p.s)(seed_task)).
```

The row/column families are nested, `|p.s| <= d`, and the depth-3 execution
budget suffices. The maximum dimensions and cell count are checked before any
matrix construction. At `d=3` they are exactly 65 task-prefix rows, 157
suffixes, 7 response channels, and `65 * 157 * 7 = 71,435` cells, below the
100,000-cell cap. All 12 fixed symbols remain suffix coordinates even when two
symbols have the same bound target/successor. Ordinary inapplicability yields
the typed absorbing sink; a censor blocks the probe and creates no cell.

Exact integer response channels are:

```text
closed indicator
sink indicator
open goal count
open unassigned mvar count
pending typeclass count
carrier-atom count
expression-node count
```

These seven channels are functions only of the final totalized state, so
absorbing `SINK`/`CLOSED` extensions have identical responses. Ordinary-failure
entry counts are reported as auxiliary transition diagnostics and are not a
Hankel channel.

Report exact rational rank `r_d`, row/column/cell counts, their actual growth,
non-sink prefix/suffix coverage, per-channel scales, incremental rank, singular
values of the float copy, and
`inverse_condition_ratio_d = sigma_(r_d) / sigma_1`. Exact rank never uses a
floating tolerance; the inverse ratio is not named a condition number.

Disposition:

- `r_3 == r_2`, both nonzero, the matrix dimensions increased, and
  `inverse_condition_ratio_3 >= 1e-8` is
  `U05_KP3_PLATEAU_AT_D3`;
- strict rank growth at every cutoff with
  `r_3 / min(n_rows,n_cols) >= 0.8` is
  `U05_KP3_NO_LOW_RANK_WINDOW_ON_FROZEN_FAMILY`;
- prefix-closure, cap, replay, or response-cell failure is
  `U05_PREREQUISITE_BLOCKED`;
- every other valid result is `U05_KP3_INCONCLUSIVE`.

The `1e-8` and `0.8` values are development scheduling thresholds. A one-step
plateau licenses only a predictive-hardening proposal; it is not a stable-rank
claim. Neither label is a protected K3 threshold or confirmation.

## 12. Capability decision and licenses

U05 does not collapse independent hypotheses into one scalar portfolio pass.
It reports the following candidate capabilities for deciding what a future
`U'CPU-survivor implementation bundle amendment` may name:

| candidate capability | U05 prerequisite | current consequence |
|---|---|---|
| `candidate_exact_partition` | `U05_KP1_EXISTENCE_ONLY` or `U05_KP1_SCALE_READY`; scale work requires the latter | may draft exact-partition hardening only |
| `candidate_hankel_predictive_model` | KP3 plateau-at-D3 | may draft Hankel/predictive hardening only |
| `candidate_componentwise_window` | KP2 eventual window | may retain the componentwise diagnostic; no weighted-envelope claim |
| `candidate_finite_horizon_envelope` | not decided by U05; later complete-fiber or certified-upper witness required | remains false/pending |
| `candidate_maxent_nominal` | later hard envelope plus operator-scope endpoint | remains false/pending |
| `candidate_predictive_similarity` | later predictive model plus target/residual endpoint | remains false/pending |
| `candidate_positive_similarity` | later hard `L_+`, hard target residual and coverage witness | remains false/pending |

Any prerequisite blocker ends this phase as `U05_PREREQUISITE_BLOCKED` without
a larger repair budget. KP1 no-identity-compression kills exact discrete compression on
this fragment but not a predictive model. KP3 no-low-rank-window kills the
frozen low-rank family but not exact partitioning. KP2
`NO_COMPONENTWISE_WINDOW_ON_FRAGMENT` rejects only that componentwise screen;
it does not kill a weighted or finite-horizon envelope. No U05 outcome licenses
implementation: it may only determine the contents of a future amendment.

Every U05 result, including survival, carries:

```text
licenses_k1_k4 = false
licenses_u2_u5_claims = false
licenses_wp4_wp12_implementation = false
licenses_gpu = false
licenses_canonical_rpc_rerun = false
licenses_reserved_data_read = false
```

## 13. Amendment A skeleton

The actual Amendment A is not created by this commit. After a separately
licensed development-calibration phase it must fill every field below without
wildcards and without reading a reserved outcome first.

### A. Candidate and provenance

- exact candidate commit/tree and clean-worktree rule;
- all source, task, grammar, schema, toolchain, model, and environment digests;
- ObservationFrameId, TransitionSemanticsId, and PolicySemanticsId;
- evidence-class table and exposure/read-ledger snapshot;
- exact exclusions for previously burned tasks and proposer contamination.

### B. Protected estimands and gates

- K1 exact compression/index estimand, denominator, cutoff schedule, and gate;
- K2 finite-horizon envelope reachability, non-vacuity, ranking-effect,
  productive-trajectory definition, baseline, and gate;
- K3 prefix/suffix language, response channels, rank arithmetic/tolerance,
  conditioning gate, and stabilization rule;
- K4 frozen true target, target-residual bound/tier, cross-covariance inflation,
  node/edge/path representation, support and coverage gate;
- sample sizes, strata, exclusions, uncertainty intervals, and one-look rule;
- alpha/confidence level, multiplicity control, power/minimum detectable effect,
  missing/censored-data rules, and exact task-allocation/split commitments;
- incumbent scalar-score and registered ablation baselines;
- coverage, abstention, and rejected-action counterfactual performance;
- zero-violation interpretation, including the rule-of-three upper bound when
  applicable, with no empirical zero promoted to a hard certificate;
- all kill, fallback, abstention, and inconclusive branches.

### C. Refinement and learner

- task-seeded reachable-set construction and `Lambda/R/N/G` schedule;
- state, transition, action-word, query, and oracle-time budgets;
- learner hypothesis class, before-only feature grammar, loss, seeds,
  deterministic tie-breaks, split/merge policy, and baselines;
- witness-completeness status; absent proof forces statistical-only labels;
- MaxEnt reference law, sufficient statistics, targets, support, KL radius,
  operator residual endpoint, and proper-score baseline;
- envelope profiles, weights, horizon, upper construction, and tier labels;
- similarity kernels/metrics, `d_pred`/`d_+`, `L_+` provenance, residual, and
  coverage.

### D. Resource and protected-read protocol

- exact CPU/GPU command, seed set, batching/concurrency policy;
- wall, heartbeat, RAM, VRAM, disk, and retry/stop limits;
- Python/CUDA/PyTorch/model/tokenizer/weights digests;
- artifact destination and checkpoint cadence outside ephemeral storage;
- encrypted per-task result store, one-shot decrypting scorer, append-only read
  ledger, and adjudication protocol;
- scorer-key custody, one-shot claim/receipt semantics, external commitment or
  ruleset identity, owner/admin bypass treatment, independent adjudication, or
  an explicit single-researcher limitation when independence is unavailable;
- out-of-band remote host-key verification, clean checkout provenance,
  persistent-storage/disk preflight, and occupied-listener avoidance;
- equal-budget accounting and the U'5 paired all-task endpoint.

Only a filled, committed, pushed, and green Amendment A can license protected
K1--K4, protected-data U'2--U'4 execution, deployment, or any explicitly named
GPU construction. It freezes the exact CPU candidate produced by the earlier
development-only construction bundle. U'5 still requires its sealed runner and
all-task endpoint authorization.

## 14. Learner and deferred-item registration routes

To avoid both silent scope growth and one-document-per-unit-test bureaucracy:

1. this amendment covers WP1, WP2, and the single U05 execution;
2. one `U'CPU-survivor implementation bundle amendment` uses the U05 capability
   matrix to name only surviving WP4/WP6 development paths, their source/test
   allowlist, commit/resource budget, development inputs, and nonclaim endpoint;
3. a separate `U'1.5-L` phase-bundle amendment is required before a locality
   learner first consumes a frozen task/query matrix or any WP4--WP6 source,
   fixture, query, or pilot owned by the learner is created/executed;
4. after surviving WP4/WP6 substrate exists, one `U'2--U'4 development
   construction bundle amendment` may license WP7--WP10 on only synthetic or
   already-contaminated inputs, with a frozen source/test allowlist, bounded
   commit/resources, calibration endpoints, and no protected read or scientific
   claim; its complete CPU candidate and calibration fill Amendment A;
5. Amendment A freezes that exact candidate and covers the protected K-series
   plus only the protected/deployment/GPU work explicitly named in it;
6. occurrence-targeted `rw` receives a separate grammar/site amendment only
   after target routing, occurrence identity, read/write support, and F2
   response-separation tests exist;
7. unrestricted `simp`, `aesop`, and `omega` remain kernel-audited opaque
   hyperedges until a macro-trace amendment freezes decomposition semantics;
8. proposer-driven evaluation is barred until PolicySemanticsId and
   pretraining-contamination strata are registered.

Deterministic implementation tests inside one future work package are covered
by its bundle amendment and CI. A new amendment is required before beginning
any work package not explicitly licensed by the current amendment, and whenever
a protected input is read, a frozen endpoint/budget changes, or action/learner
semantics expand.

## 15. Contamination and currently untracked files

The current 103 score-side tasks and phi/alpha remain
`development_contaminated`. miniF2F-valid remains reserved except for its
already recorded three-row exposure. Public-benchmark pretraining contamination
is not cured by a repository read ledger.

The following present worktree files are classified but are not read, imported,
staged, moved, deleted, or hashed into U05:

| path | frozen classification |
|---|---|
| `llm_local.json` | unsealed development proposer configuration; excluded from U05 and not a PolicySemanticsId |
| `pilot_tasks.json` | public/pretraining-contamination-unresolved task material; ineligible for reserved/U'5 evidence |
| `fake_lean_smoke.py` | local scratch harness; noncanonical and never imported/executed |
| `smoke_tasks_local.jsonl` | local scratch tasks; not a registered task source |

They are excluded from every WP1--WP12 input and evidence path unless a future
amendment explicitly registers a replacement role; `pilot_tasks.json` remains
permanently ineligible for U'5. Their unrelated presence in the source worktree
does not enter the disposable U05 worktree. A test or runner that globs, imports,
or opens them fails. The inline synthetic U05 tasks create no EvidenceLedger
entry and no exposure marker, so the protected exposure inventory stays
unchanged. Any protected-task read stops this phase.

## 16. Resource placement

This section is a resource-placement forecast, not independent execution
authority. Under this amendment, local Windows CPU authority ends with WP3:
planning, strict-contract/RPC tests on disjoint toy fixtures, the frozen small
task-seeded U05 chart, and preregistration/result generation. Later exact
algorithms, MaxEnt/similarity fixtures, learners, and pilots require the future
amendments named above and remain planned for Windows CPU where feasible.

Remote GPU use remains blocked until Amendment A. Public records use only the
private endpoint alias; they never contain host coordinates or host keys. GPU is
for large learned representation/acquisition models, not for defining or
validating the hard certificate. The CPU reference checker must accept every
GPU-produced candidate before it can enter an evaluation.

## 17. Anti-fractal governance and commit topology

The next sequence is exactly:

```text
one three-path plan/amendment commit
-> one contiguous interval of at most four pushed WP1/WP2 commits
-> one final green candidate head
-> one local U05 execution
-> one four-path consolidated result commit
```

No component-level freeze/amendment/execution triplets are permitted. No new
evidence-ledger, CAS, publisher, recovery, or cleanup module is in the future
implementation allowlist. Governance work in WP1/WP2 is limited to direct
preflight and result-integrity checks required by this exact run.

The plan/amendment commit changes exactly:

```text
docs/experiments/uprime_odlrq_upper_stack_implementation_plan_and_u05_amendment_2026-07-11.md
lean_rgc/evals/uprime_rpc_litmus.py
tests/test_uprime_rerun_license.py
```

It has `df38daea2139b67d9935408c82bfb3297efd9536` as sole parent, adds this
document exactly once to `ANCHOR_PATHS`, preserves the empty rerun registry,
contains no apparatus implementation, and is pushed and green before WP1.

The union allowlist for the four WP1/WP2 implementation commits is:

```text
lean_rgc/native_lean/RGCKernelRPC.lean
lean_rgc/lean/kernel_state_identity.py
lean_rgc/lean/kernel_rpc_client.py
lean_rgc/lean/native_worker.py
lean_rgc/odlrq/__init__.py
lean_rgc/odlrq/contracts.py
lean_rgc/odlrq/rule_algebra.py
lean_rgc/odlrq/reachable_chart.py
lean_rgc/odlrq/hankel.py
lean_rgc/evals/uprime_u05_kill_probes.py
tests/test_v49_kernel_rpc_worker.py
tests/test_uprime_u05_identity.py
tests/test_uprime_u05_kill_probes.py
tests/tier_manifest.json
```

Let `A` be the amendment commit and `C` the final candidate. The complete
contiguous first-parent interval `A..C` contains between one and four commits
after `A`; every one is single-parent, non-merge, changes only a subset of this
union allowlist, and preserves the exact amendment document blob. No unrelated
or intervening commit is permitted. The first implementation commit freezes
`A` and the three plan-commit blobs in a test. After the attempt starts, this
lineage is immutable: no amend, rebase, reset, replacement ref, or force rewrite
may create a cleaner second candidate.

If a fifth commit or an additional path is needed, the implementation stops,
records one consolidated `U05_PREREQUISITE_BLOCKED` result, and this phase ends;
no component-level extension is pre-authorized.

The consolidated result commit changes exactly the result document, complete
canonical JSON artifact, minimal litmus result anchor, and rerun-test result
guard named in WP3. It records exact parent/diff/blobs, Windows command and
environment, CI head, all probe values, all nonclaims, and the only next
amendment that may be drafted.

## 18. Adversarial implementation-plan review

This section is completed before the plan commit. Reviewers inspect this
document, the current code, and the registered review/errata, but do not
re-adjudicate the theory itself.

Required lenses:

1. **math-to-code completeness:** every surviving definition, erratum, theorem
   obligation, and certificate has a code owner and executable witness;
2. **feasibility and dependency:** no work package consumes a field that an
   earlier package cannot produce; complexity is bounded by task-seeded
   reachability rather than all-germ enumeration;
3. **endpoint/governance:** development probes cannot be mistaken for protected
   K-series results, selective evaluation is impossible, and protected inputs,
   GPU, and reruns remain barred;
4. **learner/locality:** exact and learned layers cannot silently exchange tier,
   no outcome-side feature leakage exists, and counterexample absence is not
   promoted to a hard statement.

### Review workflow and identities

Three independent agents reviewed the plan against the current repository,
the two hashed theory inputs, the registered 2026-07-10 adjudication/errata, and
the sealed Phase 2b2f result. They did not re-adjudicate the mathematical theory
and did not open a protected task or run the frozen U05 matrix.

| Reviewer | Lens |
|---|---|
| `upper_stack_substrate_rpc` | Lean RPC semantics, state identity, replay, resource bounds, worker lifecycle, probe computability |
| `upper_stack_substrate_models` | quotient/operator/MaxEnt/similarity dependencies, learner tiers, endpoints, math-to-code completeness |
| `upper_stack_governance_map` | authority, contamination, one-look/result publication, CPU/GPU boundary, commit topology |

The first draft round was rejected. Repairs were made in this document, each
reviewer attacked the repaired candidate again, and a final narrow re-review was
required for the Windows runtime digest and CI-control-plane actor. Reviewers
made no repository edits; the primary agent incorporated the repairs.

### Confirmed attacks and adopted repairs

| Confirmed implementation-plan defect | Adopted repair |
|---|---|
| Post-U05 authority was overbroad and Amendment A depended cyclically on an unbuilt candidate. | Only WP0--WP3 are licensed here. Surviving WP4/WP6 substrate, a separate development-only WP7--WP10 construction bundle, complete CPU candidate/calibration, Amendment A, protected K1--K4, deployment/GPU, and U'5 now form a noncyclic sequence. |
| The first exact-transition type silently required unavailable M3 locality coverage; action/site identity and replay fields were underspecified. | `ExactKernelTransitionCore`, nonpromotable `U05ProbeTransition`, later `ExactOracleTransition`, fixed `ActionSymbol` versus state-resolved `BoundAction`, and `ReplayComparableResponse` now have explicit constructor boundaries. |
| Primary/replay execution counts, worker-state release, action-word multiplicity, and protocol-version changes were not jointly bounded. | Primary and replay caps are separate and complete; expanded states retain sealed rows without live IDs; the worker bound is frontier plus one child; word occurrences survive state deduplication; legacy RPC v2/state v3 remain compatible while U05 schemas are separate. |
| A path-dependent/incomplete environment ID could ignore Lean runtime DLL replacement. | Compiler identity now covers a deterministic canonical manifest of the executable, toolchain PE superset, transitive imports, system providers/API-set mapping, loaded inventory, OS build, `lib/lean`, and worker source; ambiguous/out-of-root/runtime mutation blocks preflight. |
| `CLOSED` absorption could manufacture KP1 compression, the KP2 terminal close could manufacture contraction, and a history-dependent fail-entry channel violated KP3 state-response semantics. | KP1 uses only open nonterminal occurrences and reports terminal diagnostics separately; KP2's decision denominator is replayed open-to-open steps on eventually closed paths; KP3 uses seven final-state channels and has an exact 71,435-cell maximum. |
| Probe thresholds could collapse independent hypotheses into a single survival scalar or turn missing evidence/censors into theory failure. | A capability matrix licenses only matching future drafts; prerequisite/censor failures block; KP1 identity, KP2 componentwise-window, and KP3 predictive-rank consequences remain independent and development-only. |
| Sample maxima or observed intervals could leak into hard fiber envelopes, and nominal fallback could bypass a failed certificate. | Exact/certified/observed/nominal constructors are disjoint; hard envelopes require fiber/domain completeness; only already-certified candidates may use a fixed utility fallback when the nominal model fails. |
| Global similarity, locality learning, and deferred grammar work lacked typed transport and registration routes. | R/N/G morphisms, residual/coverage certificates, before-only CEGAR features, counterexample-only promotion, `U'1.5-L`, development construction, occurrence-site, opaque-macro, and proposer amendments are explicit. |
| A consumed crash could lack a result artifact; CI verification conflicted with the network ban; local one-look could be evaded; repair could extend through a small amendment. | An outer receipt, matrix marker, canonical union envelope, recovery-only publisher path, explicit pre-receipt Actions actor, credential stripping, procedural-attestation limitation, second-open invalidation, and unconditional allowlist/commit-budget phase stop are frozen. |

### Final dispositions

- `upper_stack_substrate_rpc`: **APPROVE** -- no remaining RPC/U05 substrate
  pre-freeze blocker.
- `upper_stack_substrate_models`: **APPROVE** -- no remaining operator,
  learner, endpoint, or math-to-code pre-freeze blocker.
- `upper_stack_governance_map`: **APPROVE** -- no remaining authority,
  contamination, publication, or topology pre-freeze blocker.

**Final disposition: APPROVE for the exact three-path plan freeze and its
machine wiring.** This is not approval to execute WP4--WP12, protected K1--K4,
GPU work, a canonical RPC rerun, or U'5. The registered 2026-07-10 theory
verdict remains unchanged.

## 19. Stop rule

Work stops immediately when any of the following occurs:

- the plan commit is not the exact pushed/green three-path child described
  above;
- the contiguous four-commit WP1/WP2 budget is exhausted;
- a runner would need an unregistered input, root glob, cache reuse, protected
  task, network beyond the frozen pre-matrix control-plane exception, any
  network at/after matrix open, GPU, or canonical rerun;
- exact state, delta, target, replay, prefix closure, or cap evidence is absent;
- an implementation requires any path outside the allowlist; the only in-phase
  action is the consolidated blocked result, and any later user-authorized
  replan is a new phase rather than an extension of this one; or
- a U05 capability disposition excludes the corresponding future work package.

Stopping is a successful fail-closed outcome. It does not authorize additional
ledger infrastructure or a larger repair budget.
