# U-prime / ODLRQ U2--U4 development R2 exact-admission integration amendment

Date: 2026-07-13 (Asia/Tokyo)

Status: **FROZEN ONLY AFTER THIS DOCUMENT IS COMMITTED, PUSHED, AND GREEN ON
BOTH ITS CANDIDATE REF AND THE ACCEPTED BRANCH**

Sole parent: accepted R1 failure closeout
`1d448a2322b639b462d8cda8d20b4aaa55be232f`.

That parent passed candidate CI run `29227460562`, job `86744492071`, and the
exact same commit passed distinct accepted CI run `29227618311`, job
`86744954748`.

### 2026-07-13 red-CI clarification for future readers

The immutable U05 result-publication commit
`cc91a4181a9f87ec10f11727ed787eb7149f955a` has red Actions run `29166670576`
(job `86580832840`).  Dated audits found an identity-guard shallow-history
design omission, not a probe, prerequisite, artifact-integrity, or scientific
failure.  The exact scientific candidate
`3bb3408afc50a08307cff2c9b1906a299739dfb5` had green run `29166073728` (job
`86579287017`).  The red result badge must not be read as a failed scientific
execution.  R2 neither rewrites nor reruns that consumed endpoint.

## 1. Purpose and prior verdict

R1 stopped before E0 source construction with
`U24_EXACT_ADMISSION_BLOCKED`.  Original section 8 froze four fixture frame
strings that the only strict exact-admission validator rejects, while the E0
path set excluded that validator.  Two independent read-only audits and one
executable witness confirmed that no strict path satisfied both authorities.
R1 therefore closed without creating a fixture, generator, or mathematical
artifact.

R2 repairs only that pre-existing integration defect and completes E0 wire
details that the blocker review found under-specified.  It does not reopen the
2026-07-10 adversarial review of the upper mathematics, change
`Delta_a=P_a-I`, tune a result, inspect a protected endpoint, or redesign the
shared admission substrate.  The exact quotient remains before the positive
envelope; the envelope remains before MaxEnt; MaxEnt remains model selection,
not safety; and global similarity remains downstream of those typed stages.

## 2. Inherited authority and exact supersession

The original construction authority is commit
`14234e209229931c00615d4b171620ec6d1bbbf5`, document
`docs/experiments/uprime_odlrq_u2_u4_development_construction_bundle_amendment_2026-07-13.md`,
blob `bd3ef021dff5cb5e3a28c1d2a79b0379e5615835`.  R1 reconstruction authority
is commit `7377119962e07c9062ba46c2c0c2f0eb479060ef`.  Accepted B0R is
`48c9127b0cc6122af203869c656a78b9f2160293`; its candidate CI
`29226777052` and accepted CI `29226930116` were green with exactly `2581
passed, 8 skipped, 161 deselected`.

Inherited byte-for-byte are all original E0--I0 mathematical formulas,
schemas, tier boundaries, caps, fixed transition tables, stage path sets,
runtime identities, lane walls, memory/output limits, artifact rules,
endpoints, nonclaims, and post-success order, except for the clauses listed
below.  B0R's guard, workflow, runner, control schema, setup-residue contract,
and denial roots are accepted ancestors and are not reconstructed.

R2 supersedes only:

1. original/R1 ref, build-order, commit-budget, correction-quota, and closeout
   clauses solely as restated here; in particular R2 receives exactly one
   fresh R2-wide correction, while historical corrections `7ca946e...` and
   `48c9127...` remain consumed and are not reopened or counted as R2 work;
2. original section 8's four fixture `ObservationFrameId` strings, replacing
   them with the already admitted strict factory values in section 3 below;
3. original section 8's displayed state/action labels, by the one exact full-ID
   expansion and payload rule in section 3 below;
4. the whole-module reading of original section 8's no-nominal ordering
   regression, restricting it to the newly added E0 API, wire, and dependency
   surface; the inherited `NominalOperator` tier-firewall API remains intact;
5. otherwise unspecified E0 field sets, member-witness digest precursor,
   source-seal precursor, and work-unit formula, completed exactly in section
   4 below; and
6. R1's terminal parent rules only as restated in section 8 below.

An unlisted conflict resolves in favor of the original authority.  In
particular, R2 does not change a later-stage fixture coefficient, tolerance,
formula, path set, wall, cap, endpoint, protected-read boundary, or success
disposition.

At the sole parent, the three E0 base blobs are:

```text
lean_rgc/odlrq/quotient_generator.py       e8d95082d2e47f0829d960321cc1d62bc686d7ac
lean_rgc/odlrq/__init__.py                 866df99205f5073335ea7304b0cc160ab657e8f5
tests/test_odlrq_quotient_generator.py     d014b0c9555ac5932827d86b6b92420849ed4973
```

No E0 source exists before this A2 document is accepted.

## 3. Total E0 fixture grammar

The fixture frame is created only by the existing
`make_synthetic_observation_frame_id`.  Its exact strings are:

```text
source_lane       = synthetic_development
granularity       = synthetic_totalized_state
normalization_id  = exact_rational_decimal_v1
extractor_version = cpu_survivor_synthetic_v1
```

For every displayed state atom `x`, the full state ID is exactly
`unit_cpu_survivor_` concatenated with `x`.  For every displayed action atom
`x`, the full action ID is the same concatenation.  Fixture names are not part
of those IDs; the environment digest separates fixtures.  Payloads are:

```json
{"kind":"u24_state","name":"unit_cpu_survivor_<x>"}
{"kind":"u24_action","name":"unit_cpu_survivor_<x>"}
```

Thus, for example, `s0` and `a` denote full IDs
`unit_cpu_survivor_s0` and `unit_cpu_survivor_a`.  `O0`, `O1`, and `O2` are
semantic response labels, not canonical certificate block indices.

The response vocabulary remains `("block_index",)`.  Its frozen digests are:

```text
coordinate_schema_digest = 9D1F0F6B52CF84E26705C68607405DC1EDEAEA5EBE29D878FD4FEAA5AECD5485
vocabulary_digest        = 3820F0BB274E5EC04F20F014462FBD7CF1D16614B0EE7A85A6E47F6E97743AEF
```

Open response coordinate `Oi` is `i/1`; CLOSED is `100/1`; SINK is `101/1`.
Every open state is a seed.  Expansion is `SEALED`, `boundary_complete=true`,
`truncated=false`, live handles and transition censors are `NOT_APPLICABLE`,
and the evidence profile is the strict default.

Each environment digest is uppercase SHA-256 of strict canonical JSON
`{"bundle":"u24","fixture":name}`:

| fixture | environment digest |
|---|---|
| `g0-self` | `283B385D4C4B94CCC95D78F3C00011A9A346D5849B672D9CE0EF573B6F355976` |
| `g0-move` | `93FF6D36128B71981E15328394F7F6A6BAB0ACACF61AD097FBBD30E2F22BADEF` |
| `g0-diamond` | `B1A382AE41D20CED55868F93EB6B08B1C9E977D2A63C8935C6264A3CEBFC991D` |
| `g0-members` | `58BE31966AFBDA28404F72F125CD293C6798E786070F8526051CAAF6C07FD3DA` |

After strict admission and exact refinement, canonical block/action/transition
tables are fixed as follows.  The atoms in these tables expand by the full-ID
rule above.

```text
g0-self:
  blocks 0=[c0], 1=[k0], 2=[s0]
  actions [a]; seeds [s0]
  c0-a->c0, k0-a->k0, s0-a->s0

g0-move:
  blocks 0=[c0], 1=[k0], 2=[s0], 3=[s1]
  actions [a]; seeds [s0,s1]
  c0-a->c0, k0-a->k0, s0-a->s1, s1-a->s1

g0-diamond:
  blocks 0=[c0], 1=[k0], 2=[s0], 3=[s1], 4=[s2]
  actions [a,b]; seeds [s0,s1,s2]
  c0-a->c0, c0-b->c0, k0-a->k0, k0-b->k0,
  s0-a->s1, s0-b->s2,
  s1-a->c0, s1-b->c0, s2-a->c0, s2-b->c0

g0-members:
  blocks 0=[c0], 1=[k0], 2=[s0,s1], 3=[s2]
  actions [a]; seeds [s0,s1,s2]
  c0-a->c0, k0-a->k0, s0-a->s2, s1-a->s2, s2-a->s2
```

The independent nonzero-delta oracle is also literal.  Omitted rows below are
self-loops with empty terms; displayed term pairs are
`(target_block_index, coefficient)` in canonical increasing target order:

```text
g0-self:
  no nonzero rows

g0-move:
  (2,a)->3: [(2,-1/1),(3,+1/1)]

g0-diamond:
  (2,a)->3: [(2,-1/1),(3,+1/1)]
  (2,b)->4: [(2,-1/1),(4,+1/1)]
  (3,a)->0: [(0,+1/1),(3,-1/1)]
  (3,b)->0: [(0,+1/1),(3,-1/1)]
  (4,a)->0: [(0,+1/1),(4,-1/1)]
  (4,b)->0: [(0,+1/1),(4,-1/1)]

g0-members:
  (2,a)->3: [(2,-1/1),(3,+1/1)]
  member_transition_count=2; coefficients are not doubled
```

The corresponding frozen counts are:

| fixture | rows `R` | member/action witnesses `W` | terms `T` | work `R+W+T` |
|---|---:|---:|---:|---:|
| `g0-self` | 3 | 3 | 0 | 6 |
| `g0-move` | 4 | 4 | 2 | 10 |
| `g0-diamond` | 10 | 10 | 12 | 32 |
| `g0-members` | 4 | 5 | 2 | 11 |

The source goldens, computed before E0 implementation from those literals and
the accepted strict substrate, are:

| fixture | frame digest | snapshot SHA-256 | ExactFiniteOperator SHA-256 |
|---|---|---|---|
| `g0-self` | `7F6A76BD673572C9F1888230220557D845B21AC80AAE54BC2CBD10490215F82C` | `9E0694A572EEFBF5C94EA2728C5C8CB5098BAB7048770D3F436FD4DD4F128E19` | `7153EDD8ADEC236FFBA616AFA60FF71EA70D173A9E655B1EB917FED262EA60D7` |
| `g0-move` | `A5E11715182E1CD275ADAE0CC3C77456B73618EB08E4C2E5826861AF82AEC119` | `5FCD68AE8156442DA6B10B25B2C9D7A4687735AEBF90E71234C3CA285D09638E` | `6E2B32C950467EDDC9DDD269BF17457584689E32B08DF3AA051DCD188D2EB646` |
| `g0-diamond` | `7093C282CE605CA5D7B40E16D5ED19D283E251F4E80FCD6ED7A05F91019E5E98` | `DC4564C17FE33DFBC119B9DC841DEB36FE9DB5C0AF83BFF397B2B23637408ED5` | `E4128213F843BA492E9B3A67D3B71CFF1A4229491A1DF84984BFFE2F2D77E02D` |
| `g0-members` | `71847DA839E836027AFB1EB1F3EB89DB3ECB6382FC2F5ED3C814DD50F605EE0D` | `81C9582E8AAD94F3FB4F817C92D603A20D393B1BFFCCB82EC3AD6F935D98BD27` | `29D5E0CCC3254BF5B70EB56D033AAE71140B90B418FB3E2C1D43D71C8B06797A` |

These source goldens are not E0 result values.  A generator full-wire digest
is not predicted here; it is recorded only after the frozen independent
oracle passes.

## 4. E0 exact wire completion

E0 still changes exactly:

```text
lean_rgc/odlrq/quotient_generator.py
lean_rgc/odlrq/__init__.py
tests/test_odlrq_quotient_generator.py
```

It adds only `ExactQuotientCoordinateTerm`,
`ExactQuotientTransferRow`, `ExactQuotientCoordinateGenerator`, and
`build_exact_quotient_coordinate_generator(source: VerifiedExactPartition)`
to both the module and package `__all__` surfaces.  Schema identifiers,
convention literals, the source-seal version, and cap values are module-private
constants rather than additional public exports.  No later-tier constructor
is accepted as a source.

The exact parsing/digest API is:

```text
ExactQuotientCoordinateTerm.from_dict(value)
ExactQuotientTransferRow.from_dict(value)
ExactQuotientCoordinateGenerator.from_dict(
    value, source: VerifiedExactPartition)
ExactQuotientCoordinateGenerator.generator_sha256
```

`generator_sha256` is uppercase SHA-256 of strict canonical bytes of
`self.to_dict()`.  The builder and generator parser check
`type(source) is VerifiedExactPartition` before any attribute access.  A
generator retains the exact supplied source object privately; every use
freshly rederives an equivalent authority from it and detects later mutation.

Before construction and on every generator serialization, the implementation
runs this complete chain:

```text
ExactAdmissionCompletionGate.admit(source.admitted.snapshot)
  -> canonical-byte equality with retained admitted source
  -> verify_exact_partition(fresh_admitted, source.certificate)
  -> canonical-byte equality with supplied VerifiedExactPartition
  -> dimension/cap preflight from the freshly verified source
  -> export_exact_finite_operator(fresh_verified)
```

Any failure exposes no generator.  The generator also retains a private
construction seal; direct construction and subclasses fail.

Every term, row, and generator wire has exact non-erasable fields
`evidence_scope="synthetic_development"` and
`domain_scope="declared_finite_totalized_snapshot_only"`.

The term wire has exactly:

```text
schema_version,evidence_scope,domain_scope,target_block_index,coefficient
```

`coefficient` is a strict reduced nonzero `ExactRational`.  The row wire has
exactly:

```text
schema_version,evidence_scope,domain_scope,
source_block_index,action_id,action_sha256,
structural_target_block_index,member_transition_count,
member_transition_sha256,terms
```

For one existing exact-operator row, the
`member_transition_sha256` precursor is exactly this six-field object, with
the existing values and ordered member list:

```text
source_block_index,action_id,action_sha256,target_block_index,
member_transition_count,member_transitions
```

The digest is uppercase SHA-256 of its strict canonical bytes.  Each
`member_transitions` entry retains the existing four fields
`source_state_id,source_state_sha256,target_state_id,target_state_sha256`.
Hashing the complete row, rather than only the member array, also binds its
action, structural target, and count.  No fourth public witness schema is
introduced.

The generator wire has exactly these fields:

```text
schema_version,evidence_scope,domain_scope,
basis_convention,generator_convention,
admission_report_sha256,snapshot_sha256,environment_digest,
reachable_domain_sha256,domain_payload_digest,seed_set_digest,
observation_frame_digest,transition_semantics_digest,
response_vocabulary_digest,action_alphabet_digest,
synthetic_evidence_profile_sha256,verified_partition_sha256,
exact_operator_sha256,canonical_block_order_sha256,
canonical_action_order_sha256,source_seal_sha256,
totalized_state_count,block_count,action_count,
canonical_block_indices,canonical_action_ids,
row_count,term_count,member_action_witness_count,work_units,rows
```

The fixed literals are:

```text
basis_convention     = block_basis_column_source_v1
generator_convention = P_action_minus_identity_v1
```

Digest precursors are strict typed values retained by the fresh chain:

```text
admission_report_sha256          = SHA256(admission_report.to_dict())
reachable_domain_sha256          = SHA256(snapshot.domain_id.to_dict())
synthetic_evidence_profile_sha256= SHA256(snapshot.evidence_profile.to_dict())
verified_partition_sha256        = SHA256(fresh_verified.to_dict())
exact_operator_sha256            = SHA256(fresh_exact_operator.to_dict())
canonical_block_order_sha256     = SHA256({"blocks": exact_wire["blocks"]})
canonical_action_order_sha256    = SHA256({"actions": exact_wire["actions"]})
```

Every remaining scalar/order field also has one frozen source:

```text
snapshot_sha256             = fresh exact wire snapshot_sha256
                            = fresh admission-report snapshot_sha256
environment_digest          = fresh snapshot.domain_id.environment_digest
domain_payload_digest       = fresh exact wire domain_payload_digest
                            = fresh snapshot.domain_id.domain_payload_digest
seed_set_digest             = fresh snapshot.domain_id.seed_set_digest
observation_frame_digest    = fresh exact wire observation_frame_digest
                            = fresh snapshot.domain_id.frame_digest
transition_semantics_digest = fresh exact wire transition_semantics_digest
                            = fresh snapshot.domain_id.transition_semantics_digest
response_vocabulary_digest  = fresh exact wire response_vocabulary_digest
                            = fresh snapshot.response_vocabulary_id.vocabulary_digest
action_alphabet_digest      = fresh exact wire action_alphabet_digest
                            = fresh snapshot.domain_id.action_alphabet_digest
totalized_state_count       = fresh exact wire totalized_state_count = N
block_count                 = fresh exact wire block_count = B
action_count                = fresh exact wire action_count = A
canonical_block_indices     = [0,1,...,B-1], equal to exact block order
canonical_action_ids        = fresh certificate canonical_action_ids,
                              equal to exact action order
```

Every displayed equality is checked.  `row_count`, `term_count`,
`member_action_witness_count`, and `work_units` have the count sources frozen
below; none is accepted from a caller.

The evidence-profile digest binds target, delta, replay, cap, M3, and locality
semantics, including their required `NOT_APPLICABLE`/false values.  Transition
and domain digests bind censor, terminal totalization, closure, boundary,
membership, environment, frame, action, and complete-domain semantics.  R2
does not invent substitute Lean digests for fields that are inapplicable to
synthetic development.

The source-seal precursor is exactly:

```json
{
  "seal_version":"odlrq_exact_quotient_coordinate_source_seal_v1",
  "admission_report_sha256":"<derived>",
  "verified_partition_sha256":"<derived>",
  "exact_operator_sha256":"<derived>",
  "canonical_block_order_sha256":"<derived>",
  "canonical_action_order_sha256":"<derived>"
}
```

`source_seal_sha256` is its uppercase strict-canonical SHA-256.  Serialization
rederives and compares it; it is not a caller assertion.

For `N` totalized states, `B` final blocks, `A` canonical actions,
`R=B*A`, `W=N*A`, and `T=2` times the number of non-self-loop rows, E0 checks,
before any new row/term/member-digest proportional allocation:

```text
N <= 128
B <= 128
A <= 16
R <= 2048
W <= 2048
2*R <= 4096
R + W + 2*R <= 250000
```

After fresh exact export it checks `len(rows)=R`, the sum of
`member_transition_count` is `W`, and the actual nonzero term count is `T`.
The wire stores:

```text
row_count = R
member_action_witness_count = W
term_count = T
work_units = R + W + T
```

The existing 8192-bit pre-reduction rational cap remains mandatory.  E0's
constructed coefficients are only reduced `-1/1` and `+1/1`.

Rows are block-major/action-minor.  Terms are in increasing target-block
order.  A self-loop has no terms.  Otherwise the unique terms are `-1` at the
source and `+1` at the structural target.  Member count is coverage evidence
only and never scales a coefficient.

Strict parsing proceeds in this order: exact external source-type check; raw
top-level/row/term/rational length and type preflight without sorting, sets, or
hashing; fresh authority rederivation and cap preflight; typed parsing and
canonical roundtrip; then canonical-byte equality with the fully rederived
expected wire.  Row arrays are capped at 2048, each raw term array at two,
cumulative terms at 4096, and rational decimal length before integer
conversion.  Block indices and counts are exact nonnegative signed-64 integers
before the tighter `B`/count checks.  It does not sort or deduplicate a
supplied wire into validity.
Missing/unknown fields, tuple/list substitution, bool, float, duplicate,
reordered, lowercase/noncanonical digest, unreduced rational, subclass, stale
source, mutated member/target/count/digest, or mismatched authority fails.
Finally the supplied canonical bytes must equal a fully rederived expected
wire.

The independent test oracle hard-codes section 3's source digests,
block/action/target tables, and source/target coefficient pairs.  It never
derives expected deltas from `ExactFiniteOperator.rows` or the production
generator helper.  It separately proves the fresh certificate matches the
literal block table, computes deltas from the literal target map, recomputes
the six-field member digest precursor without sharing a production helper,
and checks permutation, roundtrip, cancellation, terminal rows, member-count
non-scaling, caps, mutations, and rejection of exact-operator,
certified/observed/nominal sources.

The no-nominal ordering regression examines only the four new `__all__` names,
their annotations, direct callable `co_names`, and the recursive keys/string
tokens in freshly serialized E0 wires.  It does not perform a whole-module or
transitive generic-helper scan.  That mechanically bounded surface may contain
no `FiberEnvelope`, positive-majorant, rate, probability, fiber-law, nominal,
learner-score, or `alpha` symbol/field.  Forbidden identifiers are compared as
exact tokens, never substrings; the legitimate field
`action_alphabet_digest` therefore does not match `alpha`.  The regression
does not remove or relabel the
inherited structural tier-firewall classes already in `quotient_generator.py`
and package exports.

E0 success remains
`CPU_SYNTHETIC_QUOTIENT_COORDINATE_GENERATOR_VERIFIED`.

## 5. Refs, ancestry, and stage gates

The only R2 refs are:

```text
A2       codex/uprime-u2-u4-development-r2-a0
build    codex/uprime-u2-u4-development-r2-build
closeout codex/uprime-u2-u4-development-r2-closeout
failure  codex/uprime-u2-u4-development-r2-failure-closeout
accepted codex/uprime-odlrq-plan
```

A2 is exactly one commit adding only this document to sole parent `1d448a2...`.
No E0 source may exist until A2 passes candidate CI, is fast-forwarded exactly
to the accepted branch, and passes a distinct accepted CI on the identical
SHA/tree.

The build ref then starts from accepted A2.  It has no new B0 stage:

```text
E0 -> E1 -> E2 -> ME0 -> S0 -> I0
```

There are at most six named single-parent stage commits and one fresh
bundle-wide R2 correction commit, hence at most seven build commits.  R1's
consumed B0R correction remains historical and is not reopened.  History is
append-only: no amend, reset, rebase, merge, replacement ref, deletion,
force-push, or same-SHA CI rerun as repair.

Before every stage commit, deterministic dirty-worktree iteration and one
blocker-only adversarial review must pass on the intended bytes.  The stage is
then committed.  Its registered clean Windows lane and required residue probes
must pass on that exact commit before push.  It then requires green candidate
CI, exact fast-forward of the identical SHA/tree to accepted, and distinct
green accepted CI.  No next-stage source exists before both runs are green.

The sole R2 correction becomes available only after a committed stage fails
its registered local lane or a pushed candidate/accepted CI.  It is a
single-parent child and may touch only that failed stage's original frozen path
set.  It may not change A2, B0R, a fixture byte, source golden, formula,
endpoint, tolerance, wall, cap, allowlist, or protected boundary.  A correction
failure, second correction, unexpected setup path, or eighth build commit
closes R2.  An accepted red commit is never rewound.

B0R's `.github/workflows/ci.yml`, identity core, guard, and B0 semantics are
immutable.  Later overlap with `tier_manifest.json`, the existing runner, or
the existing identity test is licensed only where the original E1--I0 path
sets already license it; it may not create new B0 work.

## 6. Anti-fractal and resource budget

The combined A1/R1/R2 deadline is not reset.  It remains
2026-07-20 13:58:33 JST, seven days after A1 accepted CI completion.  R2 has at
most 32 additional active engineer-hours, and combined A1/R1/R2 active work
must remain within the original 40-hour cap.

R2 adds no runner, guard, workflow, ledger, CAS, publisher, recovery framework,
generated-file registry, per-stage prereg/result triplet, or recursive repair
phase.  It reuses the one accepted runner.  Each original lane wall retains
the rule `wall >= 3 * isolated measured lane time`; a wall-design failure is
not repaired by adding a second runner.

Semantic development and experiments are local Windows CPU only.  Registered
Git/Actions control-plane pushes remain required, but semantic children may
not use network, native Lean/RPC, official transport, SSH, remote CPU, GPU,
CUDA, model servers, deployment, or LLMs.  No protected K1--K4 result may be
read.

LLM proposal and knowledge distillation remain last: they require the
theory-driven generator and exact/certified upper pipeline to work
independently, followed by separate registration and adequate resources.  R2
does not create an LLM input, model identity, sampler, or result.

The earlier root-level names `llm_local.json`, `pilot_tasks.json`,
`fake_lean_smoke.py`, and `smoke_tasks_local.jsonl` are absent at the accepted
R2 parent and are not recreated or imported.  If any appears, it is
unregistered dirt and blocks rather than being silently consumed.

The investigator's existing uncommitted `docs/external/` changes are user
property and outside every R2 input, allowlist, artifact, and commit.  In
particular R2 does not stage, move, delete, hash, import, enumerate as semantic
data, or hide:

```text
docs/external/SHA256SUMS
docs/external/response_quotient_common_theory_autoproving_phases_v0_1_jp.docx
docs/external/uprime_odlrq_adversarial_review_2026-07-10/parsed_review.json
docs/external/uprime_odlrq_adversarial_review_2026-07-10/review_brief.md
docs/external/uprime_odlrq_adversarial_review_2026-07-10/workflow_raw_output.json
```

Dedicated clean worktrees keep those files physically outside registered R2
execution.

## 7. Outcomes and nonclaims

The consolidated closeout filenames are:

```text
docs/experiments/uprime_odlrq_u2_u4_development_r2_closeout_2026-07-13.md
docs/experiments/uprime_odlrq_u2_u4_development_r2_failure_closeout_2026-07-13.md
```

Success otherwise inherits original section 13 exactly.  Failure reuses the
closed terminal labels in original section 14 without relabelling.  A failure
closeout is a single-parent child of the current accepted tip when closure is
declared and adds only the R2 failure document.  A success closeout similarly
adds only the registered closeout payload/artifact files.  Closeout candidate
and accepted CI are distinct; closeout-CI failure stops without repair or
recursion.

No R2 failure is evidence that the upper mathematical program is impossible.
No outcome here claims protected K1--K4 performance, same-family D4 rank,
production Lean locality, complete all-germ quotient, production hard
envelope, MaxEnt safety, global Lean similarity, learner improvement, solve
rate, deployment, remote/GPU benefit, or LLM benefit.

After a successful I0 closeout, the inherited order remains:

```text
synthetic U'1.5-L0 registration may proceed independently
one final bounded public-synthetic official-transport qualification
  -> filled Amendment A for the exact CPU candidate
  -> protected K-series only if Amendment A is pushed and green
  -> native Lean-oracle U'1.5-L1 registration
  -> optional GPU learned representation
  -> optional LLM knowledge distillation last
```

Until the separate transport qualification succeeds, Amendment A's
environment/transport fields remain `UNFILLABLE / UNFREEZABLE`.
