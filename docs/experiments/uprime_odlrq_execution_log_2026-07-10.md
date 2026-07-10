# U' / ODLRQ execution log (2026-07-10)

Status: APPEND-ONLY PUBLIC EXECUTION RECORD under
`uprime_odlrq_repair_preregistration.md`. This file reports observations and
repairs; it does not broaden the v0 license or change a frozen threshold.
Because the preregistration and K0 result receive their first public Git anchor
in the same milestone, K0 is classified as an unanchored development pilot.
Future amendments must be committed and pushed before execution.

## Registered inputs

- Review record: `uprime_odlrq_adversarial_review_2026-07-10.md`.
- Frozen preregistration SHA-256:
  `888CE640A731A4D153C87C0E5F3EFD879C5073365B027902C73D465AA9CB98B2`.
- TeX SHA-256:
  `7E24F7D444A263792A3A717B1C26807D0A15626C2A11D8F38A1DCCB7DE69CD87`.
- External review evidence SHA-256:
  - `parsed_review.json`:
    `BC16EBA1502BFB8DB98FC22C0191BA55DBD6043C28A521E7C23B3C264A2894BB`;
  - `workflow_raw_output.json`:
    `75F64E783FF280E8C6EFC8E5BE6B9C2805E120D093C1896C1D3FD8F4A73DE9E5`;
  - `review_brief.md`:
    `2281479B63A4760D564DC59A3ACF12EB931084E2CE8A4D11FA03BB147A18B753`.

The public, path-pseudonymized derivatives are
`docs/external/uprime_odlrq_adversarial_review_2026-07-10/parsed_review.public.json`
(SHA-256 `059EF044B963DB3DD10AC9745D389D11188191C5F4E44F87C3A8124E271FEEB7`)
and `review_brief.public.md` (SHA-256
`602F8BA25825320E40A9C5DF7744E7C565AE08810BDFB8D84DC88A07CC2DD266`).
The raw workflow output remains local-only because it contains workstation
paths.

## K0 initial run on Windows CPU

Runtime: Python 3.13.7; Lean 4.31.0 Windows release, commit
`68218e876d2a38b1985b8590fff244a83c321783`; repository HEAD
`b4b81be91166ee3dcc7161c55730ac377174eb24` with the disclosed dirty
worktree.

The first invocation of the frozen command stopped before writing an artifact
because the probe producer used a plural key while the integrated consumer
used the registered singular key. This was recorded as attempt 0. The repair
renamed that key and added an integrated regression test; no probe input,
threshold, or verdict condition changed.

Attempt 1 completed with verdict `BLOCKED_AS_WRITTEN`. It found:

- all three registered finite mathematical counterexamples;
- an unchanged audit-cache fingerprint after a same-path `.olean` byte change;
- replay still `pending`, heartbeat telemetry null, cumulative rather than
  differenced assigned-mvar reporting, no all-tail-goal sweep, and divergent
  runtime/cache heartbeat semantics.

Original investigator-local artifacts are immutable:

- `runs/uprime_k0_20260710/foundation_probe.json`, SHA-256
  `F84E0E05067E5889B8146A5B6BB5273BF471B7C68A7CF750104857AA1BF4ECBA`;
- `runs/uprime_k0_20260710/environment_fingerprint.json`, SHA-256
  `5EA713BECE662B7A6E08C6B0953A68A5F266B13C2CF5631DCD853A27062DEA29`;
- `runs/uprime_k0_20260710/initial_artifact_manifest.json`, SHA-256
  `52CDE9E961AF14869D8CF71B0E714693FA59D01551A4E4BA1844578A592AB48A`.

Clone-resolvable, path-pseudonymized derivatives are tracked under
`docs/experiments/artifacts/uprime_k0_20260710/`. Their raw/derivative hash
mapping and transformation are frozen in `PUBLICATION_MANIFEST.json`. The
initial producer revision was never committed, so these first outputs are
preserved evidence rather than a reproducible Git revision.

Adversarial audit of the executable found two overclaim risks before repair:
K0-R is a source-pattern smoke check rather than a live RPC behavioral test,
and F1--F3/M3--M4 are not covered. In addition, detecting the TeX
counterexamples cannot itself satisfy T0. These facts are now explicit in the
report schema; a clean source smoke result can never license a later stage.

## First repair: F0a local build/cache content digest

The first bounded repair changed only the audit-result-cache workdir
fingerprint substrate:

1. an explicit content-algorithm salt isolates all legacy cache rows, including
   rows written with no build directory;
2. every `.olean` below the selected local build library is traversed
   recursively and hashed as sorted relative path plus streaming SHA-256 bytes;
3. identical bytes and artifact creation order are stable, while changed bytes,
   nested changes, and module-set changes invalidate the fingerprint;
4. a cache row stored before a same-name content change is a miss afterward.

Validation: 21 focused cache/K0 regressions passed, followed by 11 tier-manifest
and neighboring unit regressions. The tier manifest also lacked the already
tracked v100/v101 tests; their pure tests were registered as `unit` and passed.

The post-repair run remained `BLOCKED_AS_WRITTEN`, as required. F0a passed and
dropped from the blocker list; three T0 theory blockers and five U'1 source
contract blockers remain. Artifacts:

- `foundation_probe_after_f0a.json`, SHA-256
  `238C8C0D5AB2FABEC00213E5A4B34D5D6F3EEB0C8EA5D48C985DE3343A69B148`;
- `environment_fingerprint_after_f0a.json`, SHA-256
  `4F2306EC344B3A324D09461805937C6C15799B8239ADAEFE275F94DEF17044F6`;
- `f0a_repair_manifest.json` records code/test hashes and non-claims.

F0a is not full F0. It does not yet unify the audit queue, Lean server,
persistent worker, or kernel-state identities; hash the actual dependency
import closure/local sources/plugins; prevent fingerprint/audit TOCTOU; or
satisfy F1--F3.

A same-stage hardening revision then expanded the exposed fingerprint to the
full 64-hex SHA-256 and made any unreadable manifest/toolchain/build artifact
produce a fresh cache-bypass nonce rather than a reusable `unreadable`
identity. The expanded focused suite passed 27 tests. The preserved v2 outputs
are `foundation_probe_after_f0a_v2.json` (SHA-256
`CC7944D902ECE351251BB653477D36E24A79630D7892EC74000F1226751C63E4`) and
`environment_fingerprint_after_f0a_v2.json` (SHA-256
`1FB65D5A253246A20C9CCED510ACDDE87BA731BBB2B995780AB7E062D0BB5809`).
They retain the same `BLOCKED_AS_WRITTEN` verdict. The exact revision is in
`f0a_repair_manifest_v2.json`.

The final pre-commit v3 hardening hashes manifest/toolchain bytes without UTF-8
replacement, distinguishes absence from stat/permission failure, and removes
the suppressing `exists/is_dir/is_file` checks from the content path. Thirty
focused tests passed. The raw v3 output SHA-256 is
`77B5CC99B3218A71134D9093B9EE8D6EF105DBB070EF96B1DEF0E93554D19382`;
its tracked public derivative is
`docs/experiments/artifacts/uprime_k0_20260710/foundation_probe_after_f0a_v3.json`.
`f0a_repair_manifest_v3.json` hashes the code and tests in this milestone, so
v3—not the uncommitted initial/intermediate producers—is the reproducible
anchor. Its verdict remains `BLOCKED_AS_WRITTEN`.

## Remote GPU fingerprint; construction not fired

The authorized read-only check of private alias `UPRIME_GPU_HOST` found Ubuntu
24.04.4, an idle RTX 4090 24 GB, driver 580.159.04, CUDA/nvcc 13.0, 80 logical
CPUs, 251 GiB RAM, and about 24 GB usable overlay free space. `/workspace` has
no repository checkout. A reserved listener already serves Jupyter, so it is
the user's tunnel target rather than a build-service endpoint.

The observed host key is not out-of-band verified and is therefore not yet a
hard provenance anchor; its value and all network coordinates are withheld
from Git. The tracked capacity-only derivative is
`docs/experiments/artifacts/uprime_k0_20260710/remote_gpu_fingerprint.public.json`,
SHA-256 `E8FACC2A91D2E4C8E67F28377015D4655723B77558F144DD46A78DF2FE96E182`.

No remote file, known-hosts state, package, repository, model, service, or
process was changed. The GPU build was not fired because T0/F0--F3/M0--M4 have
not passed and v0 explicitly bars it.

## Next authorized work

The repair queue remains:

1. write and hash the U'-1 errata for weighted lifting, contextual projections,
   full covariance, true-target transport, typed telescoping, and MaxEnt scope;
2. replace K0-R source-pattern checks with live behavioral budget/delta litmus
   tests and align runtime/cache semantics;
3. build the shared content digest and full local-context state signature for
   F0--F3;
4. implement before/after delta and all-goal sweeping, then heartbeat telemetry;
5. implement independent replay only after signature, budget, and delta
   semantics are stable;
6. add M3/M4 tests, then and only then draft Amendment A for development-only
   K1--K4 calibration. GPU construction remains downstream of that amendment.
