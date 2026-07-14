# U-prime / ODLRQ U2--U4 R7 failure closeout

Registered document/filename date: 2026-07-14

Official execution observation: `2026-07-14T15:08:45.719Z`, equal to
`2026-07-15T00:08:45.719+09:00` (Asia/Tokyo)

Status: `U24_R7_B0_CONTROL_BLOCKED`

R7 bootstrap disposition: `NOT_COMMITTED / NOT_PUSHED / NOT_ACCEPTED`

Scientific interpretation: `NON_MATHEMATICAL_CONTROL_ATTESTATION_SCHEMA_FAILURE`

R7 stops at its sole official dirty B0 invocation.  The failure occurred in
the control-plane anchor attestation before any E2 scientific source existed
or any E2 execution was licensed.

## 1. Immutable anchor and failed exact4

The failed R7 worktree remained at the immutable F6 anchor:

```text
commit 03f7b81fed7cb1f65f35cbccfab9c110cc544e39
tree   61a9170555fd4b7861e620fc4ca13c2cd89fd5eb
```

No R7 bootstrap commit or tree was created.  Its exact uncommitted registered
four-path state was:

| status | bytes | raw SHA-256 | Git blob | path |
|---|---:|---|---|---|
| untracked | 103563 | `887A13C25C78E84C90F87A1D767849F6BCAA02C6905293F4F8229904D1A353B1` | `392d046cec12417a14896b292b991566620334c4` | `docs/experiments/uprime_odlrq_u2_u4_development_r7_e2_typed_reentry_amendment_2026-07-14.md` |
| modified | 121521 | `AA6B3EC9CF7093426DCE15CEC12515BA7A0A86EC11727AFFD6C04957AB0C4054` | `ecfb1805e2e70b67df124e3911017059e159ef85` | `tests/test_uprime_u2_u4_development.py` |
| modified | 65768 | `B7485BED025DC6EE54B8D3EDA74788F349C9E8FB41CF996EF8483998093B6BAC` | `2265fe2b241eeae96d4e508ce30c16a12bcc57af` | `tests/uprime_u24_guard.py` |
| modified | 166354 | `425E2316D842D1FE7D21A1CA2157338DFBFB1AEBE3EFE71025296B9D3BD01120` | `3805620e5c4d0bb0d508e4bcba75c13e6ec8f59a` | `tools/run_uprime_u2_u4_development_tests.ps1` |

The failed files encoded this exact mutual-identity closure:

```text
identity BOOTSTRAP_DOCUMENT_SHA256  887A13C25C78E84C90F87A1D767849F6BCAA02C6905293F4F8229904D1A353B1
identity BOOTSTRAP_DOCUMENT_BLOB    392d046cec12417a14896b292b991566620334c4
identity canonical core SHA-256     B9CC653B271B09D90E4F69A3E539D66E0AA65A3AA7E3CCFA2E88A58353BB39EF
guard FROZEN_IDENTITY_CORE_SHA256   B9CC653B271B09D90E4F69A3E539D66E0AA65A3AA7E3CCFA2E88A58353BB39EF
guard FROZEN_RUNNER_SHA256          425E2316D842D1FE7D21A1CA2157338DFBFB1AEBE3EFE71025296B9D3BD01120
runner ExpectedGuardCoreSha256      858420F0A824E6C396878029A40F69714C11D40CAF82EF6CC221A96A59BA52DA
guard canonical core SHA-256        858420F0A824E6C396878029A40F69714C11D40CAF82EF6CC221A96A59BA52DA
```

These identities record the failed bytes; they do not convert the failed B0
into a pass or authorize editing that exact4 in place.

## 2. Sole official dirty B0 observation

R7 made exactly one official dirty invocation:

```powershell
& .\tools\run_uprime_u2_u4_development_tests.ps1 -Lane B0
```

The process exited `1`.  No qualifying success marker or `tests_passed` lane
receipt was produced; the observed terminal output was the traceback below.
The bootstrap registered five functions, completed zero, and never reached
receipt writing.  The tool observed an initial `30.0089264s` yield followed by
the immediate final poll; because no runner receipt was produced, this is
recorded only as `>=30.0089s` tool-observed, not as an exact runner wall time.

The terminal traceback was:

```text
File ...\lean-rgc-u24-3eb1c28b990341438cdac6074c7b01bd\bootstrap.py,
  line 1041, in <module>
    if function() is not None
File ...\tests\test_uprime_u2_u4_development.py, line 1735,
  in test_u24_a0_anchor_authorities_and_nonexistence_are_frozen
    blobs = _blobs(anchor)
File ...\tests\test_uprime_u2_u4_development.py, line 587, in _blobs
    assert set(value) == set(TRACKED_PATHS)
AssertionError
```

The exact root cause is a path-universe split: the runner's control-attestation
`tracked` tuple had `54` paths while the identity module's `TRACKED_PATHS` had
`53`.  Their exact set difference was:

```text
runner-only:
  docs/experiments/uprime_odlrq_u2_u4_development_r6_failure_closeout_2026-07-14.md
identity-only:
  (empty)
```

Both future-absent sets had `17` paths and were equal.  The E2 source-freeze
and result paths were present consistently and did not cause the failure.  The
runner-keyed anchor `tree_blobs` map therefore failed the identity module's
exact 53-key assertion before the corresponding `worktree_modes` contract
could be qualified.  This is a control-attestation schema wiring failure, not
a failed envelope inequality, restriction replay, cocycle, return-memory
bound, candidate gate, or other scientific endpoint.

## 3. Scientific and capability boundary

At the stop:

- `lean_rgc/odlrq/certificates.py`, `lean_rgc/odlrq/selection.py`, and
  `tests/test_odlrq_selection.py` did not exist;
- no E2 suffix, manifest edit, source-freeze record, result record, or E2
  artifact existed;
- no E2 target was imported, compiled, collected, or executed by pytest;
- no E2 runner receipt, candidate commit, GitHub CI, accepted CI, or accepted
  ref movement existed; and
- this sole B0 invocation used no native Lean/Lake/RPC, SSH, remote CPU,
  GPU/CUDA, model server, LLM proposer, model weights, or knowledge
  distillation.

Thus R7 produced no evidence for or against the finite-horizon upper-stack
theory.  The source-freeze scientific specification, independently rederived
goldens, endpoint ordering, and finite synthetic scope were not exercised.

## 4. Stop and sole R8 continuation

R7's stopping rule requires dirty B0 to pass before a bootstrap commit.  It
does register `MAX_BOOTSTRAP_CORRECTIONS = 1`, but that correction is eligible
only for an otherwise qualifying, locally green, committed B7 bootstrap whose
repository CI is red.  This dirty B0 exited `1` before any commit, so the
correction is ineligible and remains unused.  The failed exact4 above remains
uncommitted and byte-for-byte preserved.  No clean B0, staging, R7 bootstrap
commit, push, candidate CI, accepted fast-forward, E2 source creation, or R7
success closeout is licensed.

The only continuation is a separately dated R8 authority.  R8 may repair only
the control-attestation tracked-path/`worktree_modes` schema by defining one
canonical `54`-path authority shared without duplication by guard, identity,
and runner.  Before child creation, it must require every revision and
worktree blob/mode key set to equal that authority, and every `changed_paths`
set to be its subset, reporting explicit missing and extra rows on failure.

R8 must add a positive static probe for the exact anchor and all registered
future-absent paths, plus negative probes for one missing and one extra
blob/mode/path row.  It may additionally freeze the audited canonical JSON
serialization of the 54-path authority after stating its exact UTF-8,
ordering, whitespace, and final-newline convention; that candidate has
`3660` bytes and SHA-256
`20B3CEFBCBAEE97770B7C7F26E4F776DEB46F55B69612E7FF83D3E2BE72FC452`.

R8 must preserve the R7 source-freeze scientific specification, formulas,
goldens, APIs, caps, first-execution CI rule, one-shot Windows replication,
and no-post-anchor-correction rule.  It may not weaken the path/mode contract,
change an E2 endpoint, or create E2 source before its own registered B0
qualifies.  This closeout records the control blocker; it does not repair it.
