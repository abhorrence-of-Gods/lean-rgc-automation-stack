# U-prime / ODLRQ U'1.5-L0 locality CEGAR closeout

Date: 2026-07-18 (Asia/Tokyo)

Status: **CLOSED — `L0_SYNTHETIC_CEGAR_DEGRADED`**

This is the single two-path Phase-D closeout licensed by
`uprime_odlrq_u15_l0_locality_cegar_phase_bundle_amendment_2026-07-17.md`.
It records a public-synthetic nominal diagnostic, not hard Lean evidence, and
does not reopen any protected endpoint.

## 1. Accepted source, matrix, and result identity

- accepted_c_commit: `8d46c513848a1b7b73cd91d19e58291864eef8ff`
- accepted_c_tree: `3445fdc829586357918cdc0f153f3df4d298d979`
- matrix_blob: `91af3d8e95714a043e2ab0f1f564d7f4d1014dec`
- matrix_sha256: `5CC24CF1F298A7BE4598C754973B307D78CA211CAC89287444B29E49391BDE5B`
- matrix_bytes: `73723`
- result_sha256: `B22815277CCEC10F181959BA013787D6F03A9F7A0FDB234F8D8FEB62466B82A2`
- result_git_blob: `09a0be882af00a9a8e9a7f4509a15bf894dff55a`
- result_bytes: `293930`
- disposition: `L0_SYNTHETIC_CEGAR_DEGRADED`
- heldout_fixed_denominator: `16`
- p0_sealed_instance_count: `16`
- execution_lane: `WINDOWS_CPU_ONLY`

The artifact is the unmodified canonical byte output of
`build_u15_l0_result_bytes()`.  Before publication it passed
`verify_u15_l0_result_bytes()` against a fresh matrix read, fresh admitted
snapshots, freshly verified exact partitions, and fresh public-report replay.
The artifact directory contains no other file.

## 2. Frozen resource authority and local qualification

The resource-only correction was frozen outside the scientific A--D ancestry
and read back from its full custom refspec before qualification:

```text
resource_authority_ref    refs/codex-authority/uprime-l0-resource-20260718
resource_authority_commit 804623fea79eb9f1fdcc12a413f97e7d1227a16b
resource_authority_tree   063caad3f4fb34159e4a7ea6bcfbae2ec977d1ee
resource_authority_parent f5d060f586c89b5c4753f8dc49f191fb4363a509
resource_authority_path   docs/experiments/uprime_odlrq_u15_l0_resource_only_qualification_authority_2026-07-18.md
resource_authority_blob   0617b0203cca4cd03a3a064e9be7ea17258f2cbb
```

It changed only lane walls.  Commands, tests, matrix, endpoint, expected
disposition, evidence tier, source allowlists, and natural CI gates remained
unchanged.  The old-typed `232.146 s` versus `546.598 s` observations remain
classified as host-resource drift, never as a favorable rerun.

| frozen lane | exact qualification result | outer wall | frozen wall |
|---|---:|---:|---:|
| B identity | `4 passed in 4.36 s` | `5.351 s` | `20 s` |
| C locality | `20 passed in 38.90 s` | `40.163 s` | `150 s` |
| old typed integration | `24 passed in 440.13 s` | `441.506 s` | `1800 s` |
| small exact regressions | `102 passed, 1 skipped, 1 deselected in 16.37 s` | `17.639 s` | `60 s` |

The observed outer-wall sum was `504.659 s` against the frozen aggregate
`2030 s`.  Every lane passed on its one qualification execution after the
resource authority freeze.

## 3. Hosted Phase-C acceptance

The candidate and accepted refs independently ran natural full-repository CI
on the byte-identical accepted C commit:

| ref | run / job | exact full-suite result |
|---|---|---|
| `codex/uprime-u15-l0-candidate` | `29631619019` / `88046222964` | `2662 passed, 8 skipped, 161 deselected in 491.78 s` |
| `codex/uprime-u15-l0-plan` | `29631931649` / `88047235262` | `2662 passed, 8 skipped, 161 deselected in 487.15 s` |

The accepted ref moved by ordinary fast-forward only.  No failed run was
rerun, no branch was force-pushed, and no candidate byte changed between the
two runs.  A later local monitoring-client connection delay occurred after the
second run had completed; direct run, job, and log reads verified its success
and exact count.

## 4. Result and deterministic gate

Coverage stayed `16/16` with zero abstentions and zero censors at every
checkpoint.  Locality had lower trace loss than the lexicographic baseline at
`t = 1,2,3,4`, but higher loss at every `t = 5..16`.  The frozen AULC summary
difference `baseline - locality` was exactly `-86333/6773760`; therefore the
paired primary endpoint did not support a global gain claim.

The seeded-witness audit also retained two operative misses, both in the
`separator_rank2` held-out family:

1. `heldout_alpha`, pair `sr2_zero/sr2_one`, query `q_b_a`;
2. `heldout_beta`, pair `sr2_zero/sr2_one`, query
   `q_ghost_store_reveal`.

Under the preregistered precedence rule, any worse frozen checkpoint or any
available seeded pair still co-blocked at `t = 16` forces `DEGRADED`.  The
reported disposition is therefore deterministic; it was not selected from the
bootstrap diagnostic or changed after seeing the result.

Section 14 of the frozen amendment had already predicted this exact
`DEGRADED` disposition and the same two rank-two-separator misses before Phase
C source existed.  Phase D is therefore deterministic recomputation and
serialization conformance, not a new blind empirical look.

## 5. Interpretation and next boundary

This result rejects promotion of this exact finite feature/query design to a
native Lean-oracle L1 phase.  It does **not** refute the upper-stack theory,
the accepted I0 development construction and its tier-bounded
quotient/envelope/MaxEnt/similarity artifacts, or the general idea of learning
generator locality.  The observation is specific: under the frozen schedule,
the current before-state features and query ordering have lower loss at
`t = 1..4`, higher loss at `t = 5..16`, and two rank-two-separator witness
misses.

A rational successor may be drafted only under a fresh authority.  It must
preserve paired fixed-denominator evaluation and the no-merge/tier firewall,
while predeclaring a different design such as separator-rank-aware candidate
features, a train-only early-stop/plateau rule derived and frozen without these
held-out outcomes, or a low-rank separator correction tested on new
public-synthetic carriers.  In particular, the observed `t = 4` boundary may
not be reused as a threshold.  A successor may not tune on these 16 held-out
outcomes, reuse their exact response tables as training data, or relabel this
result as gain.

Any such successor is a fresh public-synthetic design authority, not a native
Lean-oracle L1 authority.  Native L1 remains unlicensed by this result.

No GPU, SSH, LLM proposer, native Lean/RPC, production selector, protected
task, new ledger/CAS/publisher, or main-checkout user file was used.  LLM
distillation remains last, after the theoretical generator and hard upper
objects work independently and a separate authority registers that question.
