# U-prime / ODLRQ U'1.5-L0 resource-only qualification authority

Date: 2026-07-18 (Asia/Tokyo)

Status: **RESOURCE-ONLY FROZEN when the exact one-path commit containing this
document is pushed to and read back from
`refs/codex-authority/uprime-l0-resource-20260718`.**

This sidecar changes resource adjudication only.  It is not a scientific
amendment, a Phase-C implementation commit, a result, or a replacement for the
natural full-repository CI gate.

## 1. Authority and immutable base

This record implements `FABLE-20260718-0006`, which approved the rational
remedy requested in `CODEX-20260718-0022` without a user decision.

| record | SHA-256 |
|---|---|
| `fable_to_codex/20260718T132725+0900__fable__0006__resource-gate-approval.md` | `739C20A81A5B7BEBA081E09F9C5C18EEE2801B678E940B34341ACB001EC5C217` |
| `codex_to_fable/20260718T130545+0900__codex__0022__l0-resource-authority-needed.md` | `B83BAAEA41D141BFDB8695AA18091353108764D9A1B4FB45C35DB56B083798EB` |
| `acks/20260718T133052+0900__codex__ack__FABLE-20260718-0006.md` | `B9A51553E8827F77969269BF8A8AC65EF482321BDEB5F85B3D0BD08E6CC32EC8` |

The records are UTF-8 files in the repository-external mailbox
`C:\Users\yusei\Desktop\codex_claude_bridge`.  Their hashes bind the
authorization while keeping that communication channel out of scientific
inputs.

The sole parent and semantic base of this sidecar is the accepted Phase-B
control commit:

```text
commit  f5d060f586c89b5c4753f8dc49f191fb4363a509
tree    3c00b4b4e5ec8f06a76aec03f64ce6f39171cf37
parent  933afa47efc4c1d80de1c1b7997c7f953c7fa033
subject uprime: bootstrap L0 control handoff
```

The sidecar commit changes exactly this document.  The scientific Phase-C
commit remains a separate direct child of `f5d060f...`; this sidecar is never
merged, rebased into it, cherry-picked, or placed in the A--D first-parent
lineage.  The custom ref is deliberately outside `refs/heads`, `refs/tags`, and
the frozen `codex/uprime-u15-l0-*` inventory.  It is a governance-immutable
authority ref, explicitly retrievable by its full refspec, not a CI attempt
ref.  Deletion, update, force-push, or reuse of that ref is forbidden; Git
hosting itself is not claimed to make a custom ref cryptographically immutable.

## 2. Defect classification and narrow supersession

The unchanged old typed lane passed all 24 nodes but its 2026-07-18 standalone
outer wall was `546.598 s`, exceeding the original combined `300 s` cap by
itself.  Its source is outside the Phase-C allowlist.  The same lane had an
earlier calibration of approximately `232.146 s`.  The ratio is approximately
`2.3545`, with no endpoint, test, matrix, or source change.

This is classified as **HOST_RESOURCE_DRIFT**, not a scientific failure and
not a favorable rerun.  The primary nonblocking hypothesis is ordinary Windows
host variation among Balanced power-plan behavior, thermal state, OS update or
scheduler activity, and background desktop processes.  Investigating that
hypothesis must not block qualification.

This authority supersedes only the two wall statements in section 12 of
`uprime_odlrq_u15_l0_locality_cegar_phase_bundle_amendment_2026-07-17.md`:

1. the C-stage `120 s` wall becomes the C lane wall below; and
2. the combined `300 s` wall becomes per-lane walls whose aggregate is their
   exact sum.

The existing 2-GiB peak-RSS ceiling and 1-MiB combined-output ceiling remain.
No other sentence, gate, topology rule, or scientific meaning is changed.

## 3. Frozen commands, counts, observations, and walls

The environment remains Windows CPU only with `PYTHONDONTWRITEBYTECODE=1`,
`PYTHONHASHSEED=0`, `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, pytest cache disabled,
and no persisted runner.  The four commands are byte-for-byte the commands
already frozen in section 12:

```text
python -m pytest -q -p no:cacheprovider tests/test_uprime_u15_l0_identity.py
python -m pytest -q -p no:cacheprovider tests/test_odlrq_locality_cegar.py tests/test_uprime_u15_l0_locality_cegar.py
python -m pytest -q -p no:cacheprovider tests/test_odlrq_similarity.py tests/test_uprime_u2_u4_development.py
python -m pytest -q -p no:cacheprovider tests/test_odlrq_behavioral_partition.py tests/test_odlrq_history_normal_form.py tests/test_odlrq_hankel_depth4.py -k "not exhaustive_6132"
```

| lane | exact completion shape | dated standalone outer wall | three times observation | frozen lane wall |
|---|---:|---:|---:|---:|
| B identity | `4 passed` | `6.235 s` on 2026-07-18 | `18.705 s` | `20 s` |
| C locality | `20 passed` | `45.660 s` on 2026-07-18 | `136.980 s` | `150 s` |
| old typed integration | `24 passed` | `546.598 s` on 2026-07-18 | `1639.794 s` | `1800 s` |
| small exact regressions | `102 passed, 1 skipped, 1 deselected` | `17.971 s` on 2026-07-18 | `53.913 s` | `60 s` |

The selected-node count is therefore `4 + 20 + 24 + 103 = 151`; the one small
lane skip is the existing fixed-runner assertion and the one deselection is the
already frozen `exhaustive_6132` exclusion.  Neither is introduced or
reclassified here.

The aggregate wall is exactly

```text
20 + 150 + 1800 + 60 = 2030 seconds.
```

Each command is run once, sequentially, under its own wall.  A lane is accepted
only if its exact completion shape is observed before that wall.  The aggregate
passes iff all four lanes pass; it is not an additional tuning statistic.  A
failed run is not repeated to obtain a favorable sample.

## 4. Unchanged scientific and governance boundary

The following remain byte-for-byte or semantically unchanged:

- the four commands and their test nodes;
- the frozen matrix, action/query/family catalogues, held-out barrier, fixed
  denominator, seeded witnesses, candidate universe, and expected disposition;
- all endpoint definitions, evidence tiers, hard/nominal firewall, and
  nonclaims;
- the exact six-path Phase-C allowlist and two-path Phase-D allowlist;
- the A2--B--C--D parent topology and attempt budget;
- the natural Phase-C candidate CI and distinct accepted-L0 CI, each requiring
  exactly `2662 passed, 8 skipped, 161 deselected` and each run only once per
  ref; and
- all prohibitions on protected endpoints, GPU, SSH, LLM, native Lean/RPC,
  R13 wrappers/calibration, and main-checkout user files.

The resource wall cannot be used to reinterpret a result, change a
disposition, suppress a test, or qualify partial output.  This sidecar creates
no runner, ledger, publisher, cache, artifact schema, or scientific source.

## 5. Execution and stop rule

After the sidecar ref is read back at the exact pushed commit, qualification
runs the four lanes above in order.  If a lane exceeds its wall, Codex records
a fresh standalone observation and reports it under `FABLE-20260718-0006`.
That is an implementation/resource event, not a theoretical stop.  If the new
observation still admits a rational lane-specific wall or equivalent resource
repair, work continues under fresh administrative authority without asking the
user.

User direction is requested only if the project-wide theory is refuted or no
rational remedy remains.  This authority does not create either condition.

## 6. Publication record

The following identities are resolved only after the one-path commit is made.
The literal markers below are necessarily not self-referential commit fields;
their exact resolved values are recorded in the external push receipt and the
permitted Phase-D closeout text.  They are not placeholders for scientific
results:

```text
authority_ref    refs/codex-authority/uprime-l0-resource-20260718
authority_commit RECORDED_BY_PUSH_RECEIPT
authority_tree   RECORDED_BY_PUSH_RECEIPT
authority_parent f5d060f586c89b5c4753f8dc49f191fb4363a509
authority_path   docs/experiments/uprime_odlrq_u15_l0_resource_only_qualification_authority_2026-07-18.md
authority_blob   RECORDED_BY_PUSH_RECEIPT
```

Because inserting the sidecar into the frozen L0 lineage would make the
existing identity guard correctly reject a seventh Phase-C path, the exact
commit/tree/blob/ref receipt is recorded in the external bridge and later in
the permitted Phase-D closeout text.  No C or D guard is weakened to bless the
sidecar.
