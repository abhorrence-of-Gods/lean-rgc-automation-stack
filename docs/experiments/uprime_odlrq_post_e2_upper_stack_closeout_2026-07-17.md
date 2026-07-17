# U-prime / ODLRQ post-E2 upper-stack artifact closeout

Date: 2026-07-17 (Asia/Tokyo)

Status: `CPU_SYNTHETIC_U2_U4_ARTIFACTS_EMITTED`

This sidecar closes the finite public-synthetic E0--E2--ME0--S0--I0 upper-stack
construction authorized by
`uprime_odlrq_post_me0_s0_i0_authority_2026-07-17.md`.  It records an accepted
typed hard pipeline, its nominal MaxEnt diagnostic, and seven source-commit-bound
artifacts.  The sidecar is a direct child of the accepted I0 semantic commit and
is never merged into the accepted semantic line.

## 1. Accepted I0 identity and green gates

```text
accepted_i0_commit_sha = f1df8dd5d92706d907091e6add463fb6c9ca7130
accepted_i0_tree_sha   = c15e50c683263b50c8ddf371938785d03353b1fc
candidate_ref          = codex/uprime-i0-candidate
accepted_ref           = codex/uprime-odlrq-plan
```

The candidate ref and accepted ref are byte-identical.  They passed distinct
natural CI runs with the frozen exact count:

```text
candidate CI  29569429286 / 87849472845
accepted CI   29569953649 / 87851123891
result        2638 passed, 8 skipped, 161 deselected
```

The semantic candidate changes exactly the four authorized paths:

```text
lean_rgc/odlrq/certificates.py
lean_rgc/odlrq/__init__.py
lean_rgc/evals/uprime_u2_u4_development.py
tests/test_uprime_u2_u4_development.py
```

Its frozen nine-node I0 qualification passed `9 passed`; the UTF-8 LF-joined
node-list SHA-256 is
`96B64CFFB67EDB061ED68DFCEFADDC5E84B5190CB6E488878BC7CB1E6D96973C`.
The full local Windows suite had one transient pre-existing Lean RPC process
timeout; that same node passed alone in 32.41 seconds.  All changed-area and
predecessor regressions passed.

## 2. Authority, activation, correction, and red-badge interpretation

The controlling document identities are:

| role | commit | natural CI run/job | registered result |
|---|---|---|---|
| combined S0/I0 authority | `48e8aa4b2a50d93367027d3c924944c160ef806a` | `29557149691 / 87811636093` | `1 failed, 2618 passed, 8 skipped, 161 deselected` |
| mechanical I0 activation | `2e6d0b64a88877dd1f1bd87718186c3ac040c2a4` | `29561412405 / 87824486788` | `10 failed, 2619 passed, 8 skipped, 161 deselected` |
| activation correction | `6975c0a52cd64ff468614184adbdf6eafdc7e546` | `29562169223 / 87826792439` | `10 failed, 2619 passed, 8 skipped, 161 deselected` |

The authority's sole failure is the registered sidecar-topology control.  For
the activation and correction, one failure is that same control and nine are a
single nominal/runtime cause: Linux LAPACK re-solving the MaxEnt fixture did
not reproduce the frozen 4,177-byte Windows wire.  No exact rational, positive
operator, coverage, morphism, transport, finite-remainder, or hard-channel
check failed independently.  I0 therefore strict-parsed, reserialized, hashed,
and publicly verified the frozen Windows wire; it did not re-solve it.

As of 2026-07-17, the earlier result commit's CI is also red because its guard
omitted shallow-history handling, a cause with an explicit audit
classification.  Candidate CI `29166073728` was green.  Future readers must
not interpret that red badge, the authority/activation/correction badges, or
the registered closeout badge below as a scientific failure.

## 3. One-shot Windows emission

Emission ran only after both I0 green gates.  A fresh clean clone checked out
the non-detached accepted branch `codex/uprime-odlrq-plan`.  Immediately before
the child process, the parent fresh-fetched and verified:

- clean status and exact branch/HEAD/tree;
- accepted HEAD equal to the accepted remote and the sole immutable I0
  candidate ref;
- the exact authority, activation, and correction refs above;
- absence of the fixed closeout ref and official artifact root; and
- `source_tree = tree(source_commit)`.

The child used `C:\Python313\python.exe`, an unpersisted inline
`System.Diagnostics.Process`, inherited non-redirected streams, a 1,200-second
wall, 2-GiB RSS cap, 100-ms refreshed polling, and the frozen eight environment
overrides.  It used no external capture wrapper, retry, alternate runner,
network, protected endpoint, GPU, SSH, LLM, or native Lean oracle.  The
registered threat model is exclusive single-writer Windows execution; this
closeout makes no hostile same-privilege filesystem-race claim.

The emitter returned zero after in-memory construction and strict verification,
exclusive staging, one-shot file creation, reread verification, exact-seven-set
checking, and one atomic directory rename.  No staging directory remains.  The
fixed official root is:

```text
docs/experiments/artifacts/uprime_odlrq_post_e2_upper_stack_20260717/
```

The child emitted its compact receipt to inherited stdout as specified.  The
execution host did not retain inherited child stdout in its API result, and no
receipt file was permitted.  The following exact receipt content was therefore
mechanically reconstructed from the accepted source commit/tree and the seven
published bytes without rerunning or modifying the emitter:

```json
{"schema_version":"u24_artifact_emission_receipt_v1","source_commit":"f1df8dd5d92706d907091e6add463fb6c9ca7130","source_tree":"c15e50c683263b50c8ddf371938785d03353b1fc","ordered_artifacts":[["envelope_core.json",40309,"67E901DFB555967D1E956C1114F29559A6D4FAEC1E6F99A65F49D365AE004813"],["maxent_fixture.json",6081,"E1284764B1A19DD98E3E70AFB3D7BB9E918A2B28C5DBF0B5603E6BAADE7BCF49"],["local_tower.json",12327,"78D72578676C6619C05A55AE6F9E3AC594CEC78B76293E74A843215C25D4FDF6"],["global_measure.json",67747,"B879BCB6A486A4DC385381121C322364C3DD8475B013E0F2C4A0B8E324404D42"],["level_transport.json",12290,"F7C16A6B2021E3E31C446E9CE51957FD6A66B94E06949B09E421875C0F40079F"],["similarity_certificate.json",33897,"3422896A00FDD60EC0F5D5079BA6A8A8B5D8427A425AC2BC3B96C51BD6B9A460"],["integrated_certificate.json",13934,"0C0C00B39663008658E6B40E826DD08F22B2EFA2FAD68121135DB60436CA6D53"]],"disposition":"CPU_SYNTHETIC_U2_U4_ARTIFACTS_EMITTED"}
```

`source_tree` occurs in this receipt and was checked on every builder/verifier
API call.  The unchanged artifact wrapper schema contains `source_commit` only;
the parent proof that the commit binds the tree is the controlling correction.

## 4. Published artifact ledger

All SHA-256 values below were independently recomputed from the published
files after the atomic rename.  `S0RT` is
`88FE6E69BB6B0E7BFE2C1C6EB220F420ECA0BE25826D48A90BD318641F3E89C9`;
`FULLRT` is
`F20A2C1A6556EAAC5371C7438A5F588A3F7E5A76282E2F500614B2E43FF6C05A`.

| artifact | bytes / SHA-256 | schema; tier; runtime | coverage; disposition | hard use |
|---|---|---|---|---|
| `envelope_core.json` | 40309 / `67E901DFB555967D1E956C1114F29559A6D4FAEC1E6F99A65F49D365AE004813` | `u24_envelope_core_v1`; `EXACT_DECLARED_SYNTHETIC`; S0RT | `E2_M0_SOURCE_BLOCKS` 4/4 complete; `CPU_SYNTHETIC_FIBER_ENVELOPE_CORE_VERIFIED` | wrapper hard-eligible |
| `maxent_fixture.json` | 6081 / `E1284764B1A19DD98E3E70AFB3D7BB9E918A2B28C5DBF0B5603E6BAADE7BCF49` | `u24_maxent_fixture_v1`; `NOMINAL_DIAGNOSTIC_ONLY`; FULLRT | `E2_CANDIDATE_UNIVERSE_SUPPORT` 2/3 incomplete; `CPU_SYNTHETIC_MAXENT_CORE_VERIFIED` | not hard |
| `local_tower.json` | 12327 / `78D72578676C6619C05A55AE6F9E3AC594CEC78B76293E74A843215C25D4FDF6` | `u24_local_tower_v1`; `CERTIFIED_SYNTHETIC`; S0RT | `S0_DECLARED_SIMILARITY_DOMAIN` 4/4 complete; `FINITE_LEVEL_MORPHISM_VERIFIED` | wrapper hard-eligible |
| `global_measure.json` | 67747 / `B879BCB6A486A4DC385381121C322364C3DD8475B013E0F2C4A0B8E324404D42` | `u24_global_measure_v1`; `TYPED_MIXED_CONTAINER_NOT_HARD_ELIGIBLE`; FULLRT | `S0_DECLARED_SIMILARITY_DOMAIN` 4/4 complete; `CPU_SYNTHETIC_GLOBAL_MEASURE_CONTAINER_VERIFIED` | not hard |
| `level_transport.json` | 12290 / `F7C16A6B2021E3E31C446E9CE51957FD6A66B94E06949B09E421875C0F40079F` | `u24_level_transport_v1`; `CERTIFIED_SYNTHETIC`; S0RT | `S0_DECLARED_SIMILARITY_DOMAIN` 4/4 complete; `FINITE_LEVEL_MORPHISM_VERIFIED` | wrapper hard-eligible |
| `similarity_certificate.json` | 33897 / `3422896A00FDD60EC0F5D5079BA6A8A8B5D8427A425AC2BC3B96C51BD6B9A460` | `u24_similarity_certificate_v1`; `TYPED_HARD_WITH_PREDICTIVE_SIDECAR`; FULLRT | `S0_DECLARED_SIMILARITY_DOMAIN` 4/4 complete; `CPU_SYNTHETIC_TYPED_SIMILARITY_CORE_VERIFIED` | wrapper mixed; positive core separately hard |
| `integrated_certificate.json` | 13934 / `0C0C00B39663008658E6B40E826DD08F22B2EFA2FAD68121135DB60436CA6D53` | `u24_integrated_certificate_v1`; `TYPED_HARD_WITH_NOMINAL_DIAGNOSTIC`; FULLRT | `I0_HARD_DOMAIN_CHAIN` 4/4 complete; `CPU_SYNTHETIC_U2_U4_CANDIDATE_CONSTRUCTED` | wrapper mixed; hard sub-bound separately hard |

Every artifact binds the accepted I0 `source_commit`, has an empty censor list,
and reports strict live verification of its ordered predecessor objects.  The
seven operator-projection SHA-256 values are, in frozen order:

```text
30A1C493B24251549D93CA6081C0347CD32E0F104DC5BB8B00739A07738E7527
70EA19011BF12A54CA7258282A671C7E8322078945E87FB1144E08BC3EB709AD
D5E0370024160F33106C1B3CADDD869B7AA40E722C3B81DAEFE3BCACBE9D48B4
2D0D449C47B2D677B7346FDE1EA75B6CB38B488DA81F3423DC68537E265BFDB8
0C0127FDB47F77EC7E8A7AD70104F517198ED9471323671C604B0EF1175F281E
041577116A7A97F8BDD3462F86E0668E64EB16BD6DF7250A62891930F872C127
0C951B83C7CAE0C9D219E7041AAEF43C197DDFDCC9B7D03CE8929CBEE13CEEEE
```

## 5. Scientific disposition and boundary

The hard chain `E0 -> E1 -> E2 -> S0` has complete 4/4 declared-synthetic
coverage.  Exact rational propagation gives hard bound `3/4` against the frozen
threshold `3/4`, hence `PASS`.  The ME0 contribution is an explicitly
non-hard nominal diagnostic with incomplete 2/3 support; it yields diagnostic
total `17/20` but cannot enter, scale, or promote the hard channel.

This closes a finite public-synthetic construction only.  It supports the
surviving order:

```text
exact quotient -> positive worst-case envelope -> fixed-support MaxEnt
              -> finite-level global similarity -> typed integrated bound
```

It does not claim production Lean locality, a native-oracle learner, protected
solve-rate improvement, complete all-germ enumeration, an infinite-cutoff
limit, learned hard weights, GPU/remote performance, or LLM benefit.  The next
licensed planning target remains synthetic `U'1.5-L0` locality CEGAR; protected
K-series, native Lean, GPU, SSH, and LLM work require separate authority.

## 6. Registered closeout CI shape

This commit changes exactly this document and the seven artifact files.  Its
natural CI is expected to be red with exactly:

```text
1 failed, 2637 passed, 8 skipped, 161 deselected
```

The sole expected failure is the pre-registered topology guard: the inherited
identity core cannot know these future terminal paths without changing the
guard/runner outside the eight-path closeout allowlist.  That red badge is a
control-topology result, not artifact validation and not a scientific failure.
Any other failure signature is an engineering or governance defect to be
diagnosed; it is not a theoretical stop condition.
