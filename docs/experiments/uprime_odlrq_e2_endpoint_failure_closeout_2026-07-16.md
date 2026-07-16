# U-prime / ODLRQ exact E2 endpoint failure closeout

Date: 2026-07-16 (Asia/Tokyo)

Status: `U24_E2_RUNNER_BLOCKED`

This is the sole terminal document licensed by the fresh E2 authority after a
post-commit, pre-marker runner failure. It is a control-plane closeout, not a
scientific E2 result. No source, test, manifest, workflow, runner, or accepted-E1
byte is corrected by this commit.

## Frozen identities

```text
accepted E1 commit       6fb35aa229fc60e2220cbb68c1e7fff2ce64f199
accepted E1 tree         b3fc7f21b6420e718eb954be0c1b5affca65d263
authority commit         28c5a29000dddadcaf3e9ad9dd5534554dd67f32
authority tree           1a71fc6ff774dd0bcf7e4ab551bd737a7a9dab14
authority document blob  139a5992a38269974068858ef00f47f43ef5fca4
semantic commit          6998f2f9ec430881df50e6790ef9a8f13b1b7857
semantic tree            3512b6bc2e7e357544f87f2e7e05e8868b26d658
certificates Git blob    8d995768e93da62829035a1ff187a74e3ea8a378
selection Git blob       b856555271bdea8eb9f9f05e41b4aa52cab9c95d
endpoint-test Git blob   e22223008cab410dd99f953806ce18d38db854f6
tier-manifest Git blob   c649f7f3d74b8a08ea880e250fc8583a21eef790
runner carrier commit    bad1114174c05dba24311e7be219bb11692e61c1
runner carrier tree      842be61fa705ed38cd830c0516aacb12202a20a9
runner ordered parents   28c5a29000dddadcaf3e9ad9dd5534554dd67f32 6998f2f9ec430881df50e6790ef9a8f13b1b7857
runner Git blob          e6402459055dbb013ae780de3bea92f0daf3d54b
runner checkout SHA-256  8053976101E051663BBE13BE929D6BF67A33CD1AC692A335EDB659CAF284FBD2
```

The carrier tree is the authority tree plus only
`tools/run_uprime_e2_endpoint_tests.ps1`; it contains none of the three E2
source/test files and retains the accepted-E1 tier manifest.
The four semantic blobs above therefore remained unmaterialized and were not
runner-verified: the pre-run manifest never completed.

## Runner-control publication gate

The runner-control ref was published once at the exact carrier commit. Its
natural push CI, with no rerun or manual dispatch, was:

```text
ref             codex/uprime-e2-endpoint-runner-control
workflow        CI
event           push
run attempt     1
run ID          29499108625
job ID          87623235019
head SHA        bad1114174c05dba24311e7be219bb11692e61c1
conclusion      failure (the preregistered control-red)
failed node     tests/test_uprime_u2_u4_development.py::test_u24_b0_anchor_contiguous_budget_and_terminal_topology
summary         1 failed, 2599 passed, 8 skipped, 161 deselected
E2 module hits  0
E2 node hits    0
```

Only the `Test` step failed; setup, checkout, install, runtime-boundary, and
dead-candidate checks passed. This exactly satisfied the authority's
runner-control gate and licensed one cold argumentless Windows invocation.

## Sole Windows invocation and reached phase

The exact clean carrier worktree was invoked once with
`& .\tools\run_uprime_e2_endpoint_tests.ps1` under the frozen Windows
PowerShell 5.1 executable. The runner failed during its first bounded Git
preflight process, before topology observation completed.

```text
operator runner invocations       1
windows_attempt_count             0
pre-run manifest completed        false
attempt-marker write started      false
marker_present                    false
Python child started              false
E2 import count                   0
E2 collection count               0
E2 executed-node count            0
child receipt created             false
outer execution report created    false
protected endpoint/data read      false
```

`windows_attempt_count=0` uses the authority's durable-marker definition for a
post-commit pre-marker failure. It does not erase the fact that the operator
invoked the runner exactly once. No second invocation is licensed or performed.

## Exact terminal diagnostic

The terminal capture was complete and untruncated. It contained only this exact
emitted diagnostic record:

```text
U24_E2_RUNNER_DIAGNOSTIC_JSON={"schema_version":"u24-e2-runner-diagnostic-v1","lane":"U24_E2_ENDPOINT","authority_commit":"28c5a29000dddadcaf3e9ad9dd5534554dd67f32","source_commit":"6998f2f9ec430881df50e6790ef9a8f13b1b7857","runner_commit":null,"runner_tree":null,"pre_run_manifest_sha256":null,"attempt_marker_present":null,"child_started":false,"run_root_preserved":false,"run_root":null,"attempt_marker_path":null,"outer_report_preserved":false,"outer_report_path":null,"outer_report_byte_length":null,"outer_report_sha256":null,"existing_marker_evidence":null,"control_pipe_escape":false,"error_type":"System.Management.Automation.MethodInvocationException","error_message":"Exception calling \""StartSuspended\"" with \""10\"" argument(s): \""Unable to find an entry point named 'CloseHandleNative' in DLL 'kernel32.dll'.\"" | recovery: frozen final-state/EOF prerequisites were not established | frozen child receipt identities are unavailable","disposition":"U24_E2_RUNNER_BLOCKED"}
U24_E2_RUNNER_DIAGNOSTIC_BYTE_LENGTH=959
U24_E2_RUNNER_DIAGNOSTIC_SHA256=C3A062AFF29CA43FC7FDB28E3412E5276F8856C54DD647BB00098A8D4E6C19E3
```

Despite the `_JSON` label, those 959 bytes are not valid JSON. The frozen
serializer emitted each embedded quote as backslash-plus-quote-plus-quote;
strict parsing therefore fails. The byte length and SHA-256 bind the malformed
record exactly, while its visible fields report the runner-blocked disposition.
This serializer defect is control-plane evidence only and is not corrected here.

The emitted field `attempt_marker_present=null` means the runner's frozen
recovery path did not establish its internal marker adjudication. The table's
`marker_present=false` is a separate immediate post-exit observation (the latch
root was absent), not a rewrite of the emitted diagnostic.

The operator shell reported a nonzero process result. No scientific or node
outcome is inferred from that control failure.

## Forensic cause and cleanup observation

The embedded helper declares the managed method `CloseHandleNative` with
`DllImport("kernel32.dll")` but without `EntryPoint="CloseHandle"`. The CLR
therefore searched for a kernel export literally named `CloseHandleNative` and
the first native handle-close attempt failed during suspended Git setup, after
process creation and Job assignment but before `Resume`. No Git command ran.
Static review found the same missing-`EntryPoint` pattern on six other native
declarations, none of which this attempt reached or adjudicated. This is an
implementation-defect class in the immutable runner, not a failure of the E2
mathematical endpoint, and the closeout does not reduce it to a one-symbol fix.

After the parent PowerShell process exited, read-only inspection found:

```text
matching residual git.exe processes       0
matching lean-rgc-u24-e2-* temp roots     0
uprime-e2-attempts latch root present     false
runner carrier worktree/index dirty       false
```

These are post-exit observations only; they are not promoted to a universal
containment claim.

## Disposition and stopping rule

The terminal disposition is `U24_E2_RUNNER_BLOCKED`. Because no E2 node was
imported, collected, or executed, this closeout supplies no evidence for or
against the exact envelope, selection gate, MaxEnt, similarity, or locality
theory. Accepted E1 remains unchanged and valid at its existing scope.

The frozen zero-correction rule now prohibits a runner correction, another
semantic or runner-control commit, a second Windows invocation, build/accepted
publication, or any dependent ME0/MaxEnt/similarity/learner/GPU/SSH/LLM action
under this authority. The only remaining action in this phase is publication
of this one document-only failure closeout, observation of its preregistered
control-red CI, and creation of the single section-3 terminal observation.
