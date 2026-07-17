# U-prime / ODLRQ post-ME0 S0--I0 authority amendment

Date: 2026-07-17 (Asia/Tokyo)

Status: **FROZEN ONLY AFTER THIS EXACT DOCUMENT-ONLY COMMIT IS COMMITTED,
PUSHED ON THE NEW AUTHORITY REF, AND ITS NATURAL CI HAS THE EXACT
CONTROL-RED SHAPE REGISTERED BELOW.**

This is the post-ME0 phase authority required by section 8 of
`uprime_odlrq_post_e2_me0_s0_i0_continuation_amendment_2026-07-17.md`.
It freezes the complete S0 and I0 implementation contract before S0 source
exists.  It licenses S0 source and qualification only.  I0 remains frozen but
unlicensed until the mechanical activation sidecar in section 3.3 is published
after a green accepted S0.

This amendment does not re-review the upper-stack theory adjudicated on
2026-07-10.  It turns the surviving theory into code contracts: exact quotient
and worst-case envelope first, MaxEnt only on immutable support, finite-level
global similarity with explicit remainder, then a typed hard/nominal pipeline
bound.  Implementation, Windows, CI, or publication-topology mistakes are
repairable engineering defects, not mathematical stop conditions.

## 1. Accepted base and pre-freeze evidence

The sole scientific parent is accepted ME0:

```text
commit  28749bf2f0fc67bc55a24e9e07fc03ad6c66b98d
tree    a3b3513ca93430c9f15e5bd90888e81b0af1ff9c
subject uprime: implement fixed-support ME0 core
ref     codex/uprime-odlrq-plan
```

The ME0 candidate ref `codex/uprime-me0-candidate` and accepted ref are
byte-identical at that commit.  Candidate CI run/job
`29553331893 / 87800308340` and distinct accepted CI run/job
`29553637917 / 87801208543` were both green with exactly:

```text
2619 passed, 8 skipped, 161 deselected
```

The accepted ME0 commit changed exactly:

```text
lean_rgc/odlrq/__init__.py       blob 49505764ba834b4aa3c38295f06289369e242413
lean_rgc/odlrq/maxent.py         blob 6e1a97cd9aa9dcf823e3d703a7e5c3a7c7b5afe1
tests/test_odlrq_maxent.py       blob b768f59c4e3cccb97bddc421e70e77d2f8439863
tests/tier_manifest.json         blob 2fbeb53b598dbd4757365a676a0d9d8b5afeb1f7
```

Its registered nine-node Windows qualification passed `9 passed`; the exact
node-list SHA-256 was
`0B29C6C862B586A88BECCB49F97688CCE4998D949F49DBDC0FC3A3829D7E0D3F`.
ME0 is nominal model selection inside accepted E2 support and exposes no safety
constructor.

### 1.1 One deterministic public-synthetic extraction

Before this freeze, the accepted public-synthetic constructors were evaluated
once only to bind immutable predecessor bytes.  No protected endpoint, reserved
task, GPU, SSH, LLM, or native Lean oracle was read.

```text
accepted E1 commit/tree
  6fb35aa229fc60e2220cbb68c1e7fff2ce64f199
  b3fc7f21b6420e718eb954be0c1b5affca65d263

accepted E2 commit/tree
  7a8b28872439dd61d40174c2500c5990790002be
  d54ed9fab52da4929843fabdeb3c1e1920994f6a

E2 M0 pipeline source generator SHA-256
  5C920F94FA38B6F116526D0BC00340882DE5C1288A8BAE0857F54EB727A3D262
E2 M0 pipeline target generator SHA-256
  7281601FA840B29AC3F97AB4E2D5953163706E9C2CEEC8EE3855A8FB9807161C

accepted-E1 qualification envelope bytes/SHA-256
  16351
  D959B07CEF0A79A9478FAB99D3329D39DFF215A183FCD564B2547DBBE7EBD0C6
accepted-E1 embedded envelope SHA-256
  D959B07CEF0A79A9478FAB99D3329D39DFF215A183FCD564B2547DBBE7EBD0C6

E2 M0 pipeline parent envelope bytes/SHA-256
  16578
  9BA692E8A14C5C56BCDE6D565082300A9D0BB7A888DE5533F31DC1896E9B157C
E2 M0 embedded envelope SHA-256
  9BA692E8A14C5C56BCDE6D565082300A9D0BB7A888DE5533F31DC1896E9B157C

S0-selected ME0 nontrivial-orbit problem bytes/full SHA-256/core SHA-256
  3308
  F055C10309DB4AFCA1A140ECFE3FAAF3AF2BF11F7B25F6366F92667446899B7B
  20A376AD298A285949284B19D8589AD190054D870B6A7341D598D59F7EBFAF8C
S0-selected ME0 nontrivial-orbit result bytes/Windows-artifact SHA-256
  4177
  DCA363A6C8CC15ED13C4182DE7BFD2F68293E83C1766419B439C1AE8309C42E3
ME0 nontrivial row-table SHA-256
  75FFB3222E1CA31CF4F558F1955D18B74C62B6D622DE862820173FE329526A76
ME0 status/support/disposition
  INTERIOR_SOLVED
  ["c0","c2"]
  CPU_SYNTHETIC_MAXENT_CORE_VERIFIED

accepted-ME0 primary audit anchor:
  problem bytes/full SHA/core SHA
    3308
    36F09B22E4C11864F1DCBE129C15E5B0A9CDA2E86556E70F211B296144A05AAB
    6E3635F9FCA64D4223BD0D558790F00A1AFDCB9DDE41E7E4C4FF6632ADF0413C
  result bytes/Windows-artifact SHA
    3946
    A29268DC8D548A9D2E7AA18255EB887034CC79D23026159D5B5ED68050DE5465
  row-table SHA
    631C60547417A62758DC4C0A47E65618F0200543BD8C501915A07B84F5BDC8CC
```

The exact canonical accepted-E1 qualification envelope wire is:

```json
{"basis_convention":"target_row_source_column_v1","block_pair_count":16,"candidate_load_count":20,"cells":[{"absolute_compressed_coefficient":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"candidate_loads":[{"load":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"source_member_id":"unit_cpu_survivor_e1_source_CLOSED","source_member_sha256":"09507066A38911C0B887834B8F530CE118323F11CD298A65D76F878DB769E5E8","target_member_count":1,"work_count":1}],"compressed_coefficient":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"majorant":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"maximizing_source_member_id":"unit_cpu_survivor_e1_source_CLOSED","maximizing_source_member_sha256":"09507066A38911C0B887834B8F530CE118323F11CD298A65D76F878DB769E5E8","member_count":1,"source_block_index":0,"target_block_index":0,"work_count":1},{"absolute_compressed_coefficient":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"candidate_loads":[{"load":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"source_member_id":"unit_cpu_survivor_e1_source_SINK","source_member_sha256":"3A1D386248AF98930FAA4AB3C6DA71B0641CE033BDF190FE0F05BE4E5A48D407","target_member_count":1,"work_count":1}],"compressed_coefficient":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"majorant":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"maximizing_source_member_id":"unit_cpu_survivor_e1_source_SINK","maximizing_source_member_sha256":"3A1D386248AF98930FAA4AB3C6DA71B0641CE033BDF190FE0F05BE4E5A48D407","member_count":1,"source_block_index":1,"target_block_index":0,"work_count":1},{"absolute_compressed_coefficient":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"candidate_loads":[{"load":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"source_member_id":"unit_cpu_survivor_e1_source_s0","source_member_sha256":"38C2CAD3AD950A0049AC24156C1AA4C093A068D60483DFCEF5FB5430D2A0E04A","target_member_count":1,"work_count":1},{"load":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"source_member_id":"unit_cpu_survivor_e1_source_s1","source_member_sha256":"3D4E9628E8144000E1CA755E3EED85FBC3FCD0C831608A913A7AB4EEC550810D","target_member_count":1,"work_count":1}],"compressed_coefficient":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"majorant":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"maximizing_source_member_id":"unit_cpu_survivor_e1_source_s0","maximizing_source_member_sha256":"38C2CAD3AD950A0049AC24156C1AA4C093A068D60483DFCEF5FB5430D2A0E04A","member_count":2,"source_block_index":2,"target_block_index":0,"work_count":2},{"absolute_compressed_coefficient":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"candidate_loads":[{"load":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"source_member_id":"unit_cpu_survivor_e1_source_s2","source_member_sha256":"31078ED4A12167921E30359DF4ECA507BA2E8302F671586E9C020883C59BA38A","target_member_count":1,"work_count":1}],"compressed_coefficient":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"majorant":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"maximizing_source_member_id":"unit_cpu_survivor_e1_source_s2","maximizing_source_member_sha256":"31078ED4A12167921E30359DF4ECA507BA2E8302F671586E9C020883C59BA38A","member_count":1,"source_block_index":3,"target_block_index":0,"work_count":1},{"absolute_compressed_coefficient":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"candidate_loads":[{"load":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"source_member_id":"unit_cpu_survivor_e1_source_CLOSED","source_member_sha256":"09507066A38911C0B887834B8F530CE118323F11CD298A65D76F878DB769E5E8","target_member_count":1,"work_count":1}],"compressed_coefficient":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"majorant":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"maximizing_source_member_id":"unit_cpu_survivor_e1_source_CLOSED","maximizing_source_member_sha256":"09507066A38911C0B887834B8F530CE118323F11CD298A65D76F878DB769E5E8","member_count":1,"source_block_index":0,"target_block_index":1,"work_count":1},{"absolute_compressed_coefficient":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"candidate_loads":[{"load":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"source_member_id":"unit_cpu_survivor_e1_source_SINK","source_member_sha256":"3A1D386248AF98930FAA4AB3C6DA71B0641CE033BDF190FE0F05BE4E5A48D407","target_member_count":1,"work_count":1}],"compressed_coefficient":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"majorant":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"maximizing_source_member_id":"unit_cpu_survivor_e1_source_SINK","maximizing_source_member_sha256":"3A1D386248AF98930FAA4AB3C6DA71B0641CE033BDF190FE0F05BE4E5A48D407","member_count":1,"source_block_index":1,"target_block_index":1,"work_count":1},{"absolute_compressed_coefficient":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"candidate_loads":[{"load":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"source_member_id":"unit_cpu_survivor_e1_source_s0","source_member_sha256":"38C2CAD3AD950A0049AC24156C1AA4C093A068D60483DFCEF5FB5430D2A0E04A","target_member_count":1,"work_count":1},{"load":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"source_member_id":"unit_cpu_survivor_e1_source_s1","source_member_sha256":"3D4E9628E8144000E1CA755E3EED85FBC3FCD0C831608A913A7AB4EEC550810D","target_member_count":1,"work_count":1}],"compressed_coefficient":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"majorant":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"maximizing_source_member_id":"unit_cpu_survivor_e1_source_s0","maximizing_source_member_sha256":"38C2CAD3AD950A0049AC24156C1AA4C093A068D60483DFCEF5FB5430D2A0E04A","member_count":2,"source_block_index":2,"target_block_index":1,"work_count":2},{"absolute_compressed_coefficient":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"candidate_loads":[{"load":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"source_member_id":"unit_cpu_survivor_e1_source_s2","source_member_sha256":"31078ED4A12167921E30359DF4ECA507BA2E8302F671586E9C020883C59BA38A","target_member_count":1,"work_count":1}],"compressed_coefficient":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"majorant":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"maximizing_source_member_id":"unit_cpu_survivor_e1_source_s2","maximizing_source_member_sha256":"31078ED4A12167921E30359DF4ECA507BA2E8302F671586E9C020883C59BA38A","member_count":1,"source_block_index":3,"target_block_index":1,"work_count":1},{"absolute_compressed_coefficient":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"candidate_loads":[{"load":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"source_member_id":"unit_cpu_survivor_e1_source_CLOSED","source_member_sha256":"09507066A38911C0B887834B8F530CE118323F11CD298A65D76F878DB769E5E8","target_member_count":2,"work_count":2}],"compressed_coefficient":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"majorant":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"maximizing_source_member_id":"unit_cpu_survivor_e1_source_CLOSED","maximizing_source_member_sha256":"09507066A38911C0B887834B8F530CE118323F11CD298A65D76F878DB769E5E8","member_count":1,"source_block_index":0,"target_block_index":2,"work_count":2},{"absolute_compressed_coefficient":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"candidate_loads":[{"load":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"source_member_id":"unit_cpu_survivor_e1_source_SINK","source_member_sha256":"3A1D386248AF98930FAA4AB3C6DA71B0641CE033BDF190FE0F05BE4E5A48D407","target_member_count":2,"work_count":2}],"compressed_coefficient":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"majorant":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"maximizing_source_member_id":"unit_cpu_survivor_e1_source_SINK","maximizing_source_member_sha256":"3A1D386248AF98930FAA4AB3C6DA71B0641CE033BDF190FE0F05BE4E5A48D407","member_count":1,"source_block_index":1,"target_block_index":2,"work_count":2},{"absolute_compressed_coefficient":{"denominator":"3","numerator":"1","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"candidate_loads":[{"load":{"denominator":"1","numerator":"2","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"source_member_id":"unit_cpu_survivor_e1_source_s0","source_member_sha256":"38C2CAD3AD950A0049AC24156C1AA4C093A068D60483DFCEF5FB5430D2A0E04A","target_member_count":2,"work_count":2},{"load":{"denominator":"2","numerator":"5","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"source_member_id":"unit_cpu_survivor_e1_source_s1","source_member_sha256":"3D4E9628E8144000E1CA755E3EED85FBC3FCD0C831608A913A7AB4EEC550810D","target_member_count":2,"work_count":2}],"compressed_coefficient":{"denominator":"3","numerator":"-1","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"majorant":{"denominator":"2","numerator":"5","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"maximizing_source_member_id":"unit_cpu_survivor_e1_source_s1","maximizing_source_member_sha256":"3D4E9628E8144000E1CA755E3EED85FBC3FCD0C831608A913A7AB4EEC550810D","member_count":2,"source_block_index":2,"target_block_index":2,"work_count":4},{"absolute_compressed_coefficient":{"denominator":"2","numerator":"1","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"candidate_loads":[{"load":{"denominator":"2","numerator":"1","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"source_member_id":"unit_cpu_survivor_e1_source_s2","source_member_sha256":"31078ED4A12167921E30359DF4ECA507BA2E8302F671586E9C020883C59BA38A","target_member_count":2,"work_count":2}],"compressed_coefficient":{"denominator":"2","numerator":"1","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"majorant":{"denominator":"2","numerator":"1","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"maximizing_source_member_id":"unit_cpu_survivor_e1_source_s2","maximizing_source_member_sha256":"31078ED4A12167921E30359DF4ECA507BA2E8302F671586E9C020883C59BA38A","member_count":1,"source_block_index":3,"target_block_index":2,"work_count":2},{"absolute_compressed_coefficient":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"candidate_loads":[{"load":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"source_member_id":"unit_cpu_survivor_e1_source_CLOSED","source_member_sha256":"09507066A38911C0B887834B8F530CE118323F11CD298A65D76F878DB769E5E8","target_member_count":1,"work_count":1}],"compressed_coefficient":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"majorant":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"maximizing_source_member_id":"unit_cpu_survivor_e1_source_CLOSED","maximizing_source_member_sha256":"09507066A38911C0B887834B8F530CE118323F11CD298A65D76F878DB769E5E8","member_count":1,"source_block_index":0,"target_block_index":3,"work_count":1},{"absolute_compressed_coefficient":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"candidate_loads":[{"load":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"source_member_id":"unit_cpu_survivor_e1_source_SINK","source_member_sha256":"3A1D386248AF98930FAA4AB3C6DA71B0641CE033BDF190FE0F05BE4E5A48D407","target_member_count":1,"work_count":1}],"compressed_coefficient":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"majorant":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"maximizing_source_member_id":"unit_cpu_survivor_e1_source_SINK","maximizing_source_member_sha256":"3A1D386248AF98930FAA4AB3C6DA71B0641CE033BDF190FE0F05BE4E5A48D407","member_count":1,"source_block_index":1,"target_block_index":3,"work_count":1},{"absolute_compressed_coefficient":{"denominator":"1","numerator":"3","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"candidate_loads":[{"load":{"denominator":"1","numerator":"9","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"source_member_id":"unit_cpu_survivor_e1_source_s0","source_member_sha256":"38C2CAD3AD950A0049AC24156C1AA4C093A068D60483DFCEF5FB5430D2A0E04A","target_member_count":1,"work_count":1},{"load":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"source_member_id":"unit_cpu_survivor_e1_source_s1","source_member_sha256":"3D4E9628E8144000E1CA755E3EED85FBC3FCD0C831608A913A7AB4EEC550810D","target_member_count":1,"work_count":1}],"compressed_coefficient":{"denominator":"1","numerator":"3","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"majorant":{"denominator":"1","numerator":"9","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"maximizing_source_member_id":"unit_cpu_survivor_e1_source_s0","maximizing_source_member_sha256":"38C2CAD3AD950A0049AC24156C1AA4C093A068D60483DFCEF5FB5430D2A0E04A","member_count":2,"source_block_index":2,"target_block_index":3,"work_count":2},{"absolute_compressed_coefficient":{"denominator":"1","numerator":"3","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"candidate_loads":[{"load":{"denominator":"1","numerator":"3","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"source_member_id":"unit_cpu_survivor_e1_source_s2","source_member_sha256":"31078ED4A12167921E30359DF4ECA507BA2E8302F671586E9C020883C59BA38A","target_member_count":1,"work_count":1}],"compressed_coefficient":{"denominator":"1","numerator":"-3","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"majorant":{"denominator":"1","numerator":"3","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"maximizing_source_member_id":"unit_cpu_survivor_e1_source_s2","maximizing_source_member_sha256":"31078ED4A12167921E30359DF4ECA507BA2E8302F671586E9C020883C59BA38A","member_count":1,"source_block_index":3,"target_block_index":3,"work_count":1}],"coefficient_authority":"DECLARED_SYNTHETIC_FIXTURE","evidence_scope":"synthetic_development","hard_scope":"complete_declared_finite_synthetic_rectangle_only","layer_sha256":"2F4BC65BCC05A9BAD714EAEC54FEC8FF6C1DAAABBEB504019C27BBADAB17F851","schema_version":"odlrq_fiber_envelope_v1","source_block_count":4,"source_completeness_sha256":"7D49D0737A3C08128ABABE9745FED7214BCE9D5ADB6D65454617DB16C6973DC1","source_generator_sha256":"A6C3AD7B1E955577DE8909A935856FC8FDCFCE10A9C5D5A4A16633450F4F0522","source_law_sha256":"F2576FA430DF163A3456C7CD370ACAE92E5530B3A53DF2111F0B83230DCFF0FC","source_weights_sha256":"FEFD531244EACDF19DB7CBF48311ACFF807C58E6B0278ECB8D5A8F8117784390","target_block_count":4,"target_completeness_sha256":"6E20F50EA483179FD96364B13EF1EA84E6DAC5A028215B33B8B864A603C647F3","target_generator_sha256":"84DCACB9677C4272D90EBAE1B569B16D6D09376BA80EBA1D47AEE097E00865F1","target_weights_sha256":"837753176E3D00556407862BFC54DCD71342F848024D8B0F81F390456831A9CA","verification_disposition":"CPU_SYNTHETIC_FIBER_ENVELOPE_CORE_VERIFIED","work_count":25}
```

The exact canonical E2 M0 pipeline parent envelope wire is:

```json
{"basis_convention":"target_row_source_column_v1","block_pair_count":16,"candidate_load_count":20,"cells":[{"absolute_compressed_coefficient":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"candidate_loads":[{"load":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"source_member_id":"unit_cpu_survivor_u24_e2_source_closed","source_member_sha256":"4C9E9E56B27CBC0D78EDC03B102FF8D0EC751F007A80541CFD9C1C8072FBE7AB","target_member_count":1,"work_count":1}],"compressed_coefficient":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"majorant":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"maximizing_source_member_id":"unit_cpu_survivor_u24_e2_source_closed","maximizing_source_member_sha256":"4C9E9E56B27CBC0D78EDC03B102FF8D0EC751F007A80541CFD9C1C8072FBE7AB","member_count":1,"source_block_index":0,"target_block_index":0,"work_count":1},{"absolute_compressed_coefficient":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"candidate_loads":[{"load":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"source_member_id":"unit_cpu_survivor_u24_e2_source_open0_a","source_member_sha256":"5F390B7BEAF07F0D2C352968B161815640F89ABBEC0BFFD91B077581540B477F","target_member_count":1,"work_count":1},{"load":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"source_member_id":"unit_cpu_survivor_u24_e2_source_open0_b","source_member_sha256":"F28452C1BFA77F7177ED29C805B433A8A0DDFF05F6A6BD371EF1866657BEF02E","target_member_count":1,"work_count":1}],"compressed_coefficient":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"majorant":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"maximizing_source_member_id":"unit_cpu_survivor_u24_e2_source_open0_a","maximizing_source_member_sha256":"5F390B7BEAF07F0D2C352968B161815640F89ABBEC0BFFD91B077581540B477F","member_count":2,"source_block_index":1,"target_block_index":0,"work_count":2},{"absolute_compressed_coefficient":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"candidate_loads":[{"load":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"source_member_id":"unit_cpu_survivor_u24_e2_source_open1","source_member_sha256":"EF8631595FE7EBE1A83C3F41D8B0B5CFBA776C6A2255A94C28C7D810C505C688","target_member_count":1,"work_count":1}],"compressed_coefficient":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"majorant":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"maximizing_source_member_id":"unit_cpu_survivor_u24_e2_source_open1","maximizing_source_member_sha256":"EF8631595FE7EBE1A83C3F41D8B0B5CFBA776C6A2255A94C28C7D810C505C688","member_count":1,"source_block_index":2,"target_block_index":0,"work_count":1},{"absolute_compressed_coefficient":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"candidate_loads":[{"load":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"source_member_id":"unit_cpu_survivor_u24_e2_source_sink","source_member_sha256":"BCA11D0EC82388DD4EAF50804E80EA32666D1F4DECFB88D80AEDEE50AE4D5F1A","target_member_count":1,"work_count":1}],"compressed_coefficient":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"majorant":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"maximizing_source_member_id":"unit_cpu_survivor_u24_e2_source_sink","maximizing_source_member_sha256":"BCA11D0EC82388DD4EAF50804E80EA32666D1F4DECFB88D80AEDEE50AE4D5F1A","member_count":1,"source_block_index":3,"target_block_index":0,"work_count":1},{"absolute_compressed_coefficient":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"candidate_loads":[{"load":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"source_member_id":"unit_cpu_survivor_u24_e2_source_closed","source_member_sha256":"4C9E9E56B27CBC0D78EDC03B102FF8D0EC751F007A80541CFD9C1C8072FBE7AB","target_member_count":1,"work_count":1}],"compressed_coefficient":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"majorant":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"maximizing_source_member_id":"unit_cpu_survivor_u24_e2_source_closed","maximizing_source_member_sha256":"4C9E9E56B27CBC0D78EDC03B102FF8D0EC751F007A80541CFD9C1C8072FBE7AB","member_count":1,"source_block_index":0,"target_block_index":1,"work_count":1},{"absolute_compressed_coefficient":{"denominator":"3","numerator":"1","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"candidate_loads":[{"load":{"denominator":"1","numerator":"1","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"source_member_id":"unit_cpu_survivor_u24_e2_source_open0_a","source_member_sha256":"5F390B7BEAF07F0D2C352968B161815640F89ABBEC0BFFD91B077581540B477F","target_member_count":1,"work_count":1},{"load":{"denominator":"1","numerator":"1","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"source_member_id":"unit_cpu_survivor_u24_e2_source_open0_b","source_member_sha256":"F28452C1BFA77F7177ED29C805B433A8A0DDFF05F6A6BD371EF1866657BEF02E","target_member_count":1,"work_count":1}],"compressed_coefficient":{"denominator":"3","numerator":"-1","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"majorant":{"denominator":"1","numerator":"1","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"maximizing_source_member_id":"unit_cpu_survivor_u24_e2_source_open0_a","maximizing_source_member_sha256":"5F390B7BEAF07F0D2C352968B161815640F89ABBEC0BFFD91B077581540B477F","member_count":2,"source_block_index":1,"target_block_index":1,"work_count":2},{"absolute_compressed_coefficient":{"denominator":"1","numerator":"2","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"candidate_loads":[{"load":{"denominator":"1","numerator":"2","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"source_member_id":"unit_cpu_survivor_u24_e2_source_open1","source_member_sha256":"EF8631595FE7EBE1A83C3F41D8B0B5CFBA776C6A2255A94C28C7D810C505C688","target_member_count":1,"work_count":1}],"compressed_coefficient":{"denominator":"1","numerator":"2","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"majorant":{"denominator":"1","numerator":"2","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"maximizing_source_member_id":"unit_cpu_survivor_u24_e2_source_open1","maximizing_source_member_sha256":"EF8631595FE7EBE1A83C3F41D8B0B5CFBA776C6A2255A94C28C7D810C505C688","member_count":1,"source_block_index":2,"target_block_index":1,"work_count":1},{"absolute_compressed_coefficient":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"candidate_loads":[{"load":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"source_member_id":"unit_cpu_survivor_u24_e2_source_sink","source_member_sha256":"BCA11D0EC82388DD4EAF50804E80EA32666D1F4DECFB88D80AEDEE50AE4D5F1A","target_member_count":1,"work_count":1}],"compressed_coefficient":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"majorant":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"maximizing_source_member_id":"unit_cpu_survivor_u24_e2_source_sink","maximizing_source_member_sha256":"BCA11D0EC82388DD4EAF50804E80EA32666D1F4DECFB88D80AEDEE50AE4D5F1A","member_count":1,"source_block_index":3,"target_block_index":1,"work_count":1},{"absolute_compressed_coefficient":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"candidate_loads":[{"load":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"source_member_id":"unit_cpu_survivor_u24_e2_source_closed","source_member_sha256":"4C9E9E56B27CBC0D78EDC03B102FF8D0EC751F007A80541CFD9C1C8072FBE7AB","target_member_count":1,"work_count":1}],"compressed_coefficient":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"majorant":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"maximizing_source_member_id":"unit_cpu_survivor_u24_e2_source_closed","maximizing_source_member_sha256":"4C9E9E56B27CBC0D78EDC03B102FF8D0EC751F007A80541CFD9C1C8072FBE7AB","member_count":1,"source_block_index":0,"target_block_index":2,"work_count":1},{"absolute_compressed_coefficient":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"candidate_loads":[{"load":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"source_member_id":"unit_cpu_survivor_u24_e2_source_open0_a","source_member_sha256":"5F390B7BEAF07F0D2C352968B161815640F89ABBEC0BFFD91B077581540B477F","target_member_count":1,"work_count":1},{"load":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"source_member_id":"unit_cpu_survivor_u24_e2_source_open0_b","source_member_sha256":"F28452C1BFA77F7177ED29C805B433A8A0DDFF05F6A6BD371EF1866657BEF02E","target_member_count":1,"work_count":1}],"compressed_coefficient":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"majorant":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"maximizing_source_member_id":"unit_cpu_survivor_u24_e2_source_open0_a","maximizing_source_member_sha256":"5F390B7BEAF07F0D2C352968B161815640F89ABBEC0BFFD91B077581540B477F","member_count":2,"source_block_index":1,"target_block_index":2,"work_count":2},{"absolute_compressed_coefficient":{"denominator":"2","numerator":"1","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"candidate_loads":[{"load":{"denominator":"2","numerator":"1","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"source_member_id":"unit_cpu_survivor_u24_e2_source_open1","source_member_sha256":"EF8631595FE7EBE1A83C3F41D8B0B5CFBA776C6A2255A94C28C7D810C505C688","target_member_count":1,"work_count":1}],"compressed_coefficient":{"denominator":"2","numerator":"1","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"majorant":{"denominator":"2","numerator":"1","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"maximizing_source_member_id":"unit_cpu_survivor_u24_e2_source_open1","maximizing_source_member_sha256":"EF8631595FE7EBE1A83C3F41D8B0B5CFBA776C6A2255A94C28C7D810C505C688","member_count":1,"source_block_index":2,"target_block_index":2,"work_count":1},{"absolute_compressed_coefficient":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"candidate_loads":[{"load":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"source_member_id":"unit_cpu_survivor_u24_e2_source_sink","source_member_sha256":"BCA11D0EC82388DD4EAF50804E80EA32666D1F4DECFB88D80AEDEE50AE4D5F1A","target_member_count":1,"work_count":1}],"compressed_coefficient":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"majorant":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"maximizing_source_member_id":"unit_cpu_survivor_u24_e2_source_sink","maximizing_source_member_sha256":"BCA11D0EC82388DD4EAF50804E80EA32666D1F4DECFB88D80AEDEE50AE4D5F1A","member_count":1,"source_block_index":3,"target_block_index":2,"work_count":1},{"absolute_compressed_coefficient":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"candidate_loads":[{"load":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"source_member_id":"unit_cpu_survivor_u24_e2_source_closed","source_member_sha256":"4C9E9E56B27CBC0D78EDC03B102FF8D0EC751F007A80541CFD9C1C8072FBE7AB","target_member_count":1,"work_count":1}],"compressed_coefficient":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"majorant":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"maximizing_source_member_id":"unit_cpu_survivor_u24_e2_source_closed","maximizing_source_member_sha256":"4C9E9E56B27CBC0D78EDC03B102FF8D0EC751F007A80541CFD9C1C8072FBE7AB","member_count":1,"source_block_index":0,"target_block_index":3,"work_count":1},{"absolute_compressed_coefficient":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"candidate_loads":[{"load":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"source_member_id":"unit_cpu_survivor_u24_e2_source_open0_a","source_member_sha256":"5F390B7BEAF07F0D2C352968B161815640F89ABBEC0BFFD91B077581540B477F","target_member_count":1,"work_count":1},{"load":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"source_member_id":"unit_cpu_survivor_u24_e2_source_open0_b","source_member_sha256":"F28452C1BFA77F7177ED29C805B433A8A0DDFF05F6A6BD371EF1866657BEF02E","target_member_count":1,"work_count":1}],"compressed_coefficient":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"majorant":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"maximizing_source_member_id":"unit_cpu_survivor_u24_e2_source_open0_a","maximizing_source_member_sha256":"5F390B7BEAF07F0D2C352968B161815640F89ABBEC0BFFD91B077581540B477F","member_count":2,"source_block_index":1,"target_block_index":3,"work_count":2},{"absolute_compressed_coefficient":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"candidate_loads":[{"load":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"source_member_id":"unit_cpu_survivor_u24_e2_source_open1","source_member_sha256":"EF8631595FE7EBE1A83C3F41D8B0B5CFBA776C6A2255A94C28C7D810C505C688","target_member_count":1,"work_count":1}],"compressed_coefficient":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"majorant":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"maximizing_source_member_id":"unit_cpu_survivor_u24_e2_source_open1","maximizing_source_member_sha256":"EF8631595FE7EBE1A83C3F41D8B0B5CFBA776C6A2255A94C28C7D810C505C688","member_count":1,"source_block_index":2,"target_block_index":3,"work_count":1},{"absolute_compressed_coefficient":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"candidate_loads":[{"load":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"source_member_id":"unit_cpu_survivor_u24_e2_source_sink","source_member_sha256":"BCA11D0EC82388DD4EAF50804E80EA32666D1F4DECFB88D80AEDEE50AE4D5F1A","target_member_count":1,"work_count":1}],"compressed_coefficient":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"majorant":{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"maximizing_source_member_id":"unit_cpu_survivor_u24_e2_source_sink","maximizing_source_member_sha256":"BCA11D0EC82388DD4EAF50804E80EA32666D1F4DECFB88D80AEDEE50AE4D5F1A","member_count":1,"source_block_index":3,"target_block_index":3,"work_count":1}],"coefficient_authority":"DECLARED_SYNTHETIC_FIXTURE","evidence_scope":"synthetic_development","hard_scope":"complete_declared_finite_synthetic_rectangle_only","layer_sha256":"9CC1CD10134B48AC034073FB018791112F5B2EBC6BCF92CF832BF828C2D89D0D","schema_version":"odlrq_fiber_envelope_v1","source_block_count":4,"source_completeness_sha256":"6AAC693691E44367284BE449E3A9DAE8D54A45592CF59EEE2E02A020859506F7","source_generator_sha256":"5C920F94FA38B6F116526D0BC00340882DE5C1288A8BAE0857F54EB727A3D262","source_law_sha256":"9313D11B85B32AFDA39EFCD5B1836324B12B40BC2BC1D1CC04520BCE6FB54048","source_weights_sha256":"4BC2181F6941D557E918CF9D0CCC2B4BCCAE83E16F794C647C0AC2E87443C155","target_block_count":4,"target_completeness_sha256":"386269DAE2C24381D0BAA88780EEEBD2338AB29CE3778F1D724808ADBE90AA4D","target_generator_sha256":"7281601FA840B29AC3F97AB4E2D5953163706E9C2CEEC8EE3855A8FB9807161C","target_weights_sha256":"68A3EA513967E7F8295203A37AA1EEDE97FAC535EC984622D7C3DA54217660C7","verification_disposition":"CPU_SYNTHETIC_FIBER_ENVELOPE_CORE_VERIFIED","work_count":20}
```

The exact canonical S0-selected ME0 nontrivial-orbit problem wire is:

```json
{"exact_rule_column_ids":["g0"],"exact_rule_rows":[{"candidate_id":"c0","value":[{"denominator":"1","numerator":"1","schema_version":"lean-rgc-odlrq-exact-rational-v1"}]},{"candidate_id":"c2","value":[{"denominator":"1","numerator":"2","schema_version":"lean-rgc-odlrq-exact-rational-v1"}]}],"kl_radius":{"denominator":"20","numerator":"1","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"me0_authority_ci_job_id":"87793466452","me0_authority_ci_run_id":"29551068987","me0_authority_commit_sha":"0ff63861a2957b53f4c0b5f2948d561d936337ca","me0_authority_document_blob_sha":"831c226a2b25ae367b288a8fb18d7cb7afb42124","me0_authority_document_path":"docs/experiments/uprime_odlrq_post_e2_me0_s0_i0_continuation_amendment_2026-07-17.md","me0_authority_parent_sha":"7a8b28872439dd61d40174c2500c5990790002be","nominal_operator_rows":[{"candidate_id":"c0","value":{"denominator":"1","numerator":"2","schema_version":"lean-rgc-odlrq-exact-rational-v1"}},{"candidate_id":"c2","value":{"denominator":"1","numerator":"4","schema_version":"lean-rgc-odlrq-exact-rational-v1"}}],"orbit_size_rows":[{"candidate_id":"c0","value":1},{"candidate_id":"c2","value":2}],"problem_sha256":"20A376AD298A285949284B19D8589AD190054D870B6A7341D598D59F7EBFAF8C","reference_mass_rows":[{"candidate_id":"c0","value":{"denominator":"2","numerator":"1","schema_version":"lean-rgc-odlrq-exact-rational-v1"}},{"candidate_id":"c2","value":{"denominator":"2","numerator":"1","schema_version":"lean-rgc-odlrq-exact-rational-v1"}}],"row_load_rows":[{"candidate_id":"c0","value":{"denominator":"1","numerator":"1","schema_version":"lean-rgc-odlrq-exact-rational-v1"}},{"candidate_id":"c2","value":{"denominator":"1","numerator":"3","schema_version":"lean-rgc-odlrq-exact-rational-v1"}}],"row_table_sha256":"75FFB3222E1CA31CF4F558F1955D18B74C62B6D622DE862820173FE329526A76","runtime_manifest_sha256":"F20A2C1A6556EAAC5371C7438A5F588A3F7E5A76282E2F500614B2E43FF6C05A","schema_version":"odlrq.me0.maxent-problem.v1","statistic_rows":[{"candidate_id":"c0","value":[{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"}]},{"candidate_id":"c2","value":[{"denominator":"1","numerator":"2","schema_version":"lean-rgc-odlrq-exact-rational-v1"}]}],"support_candidate_ids":["c0","c2"],"support_reference":{"accepted_e2_commit_sha":"7a8b28872439dd61d40174c2500c5990790002be","accepted_e2_tree_sha":"d54ed9fab52da4929843fabdeb3c1e1920994f6a","certified_support_token_sha256":"D01170427E717D543D941740881C937EF5B535E357D67EEFDBF62773AFD6E660","me0_authority_ci_job_id":"87793466452","me0_authority_ci_run_id":"29551068987","me0_authority_commit_sha":"0ff63861a2957b53f4c0b5f2948d561d936337ca","me0_authority_document_blob_sha":"831c226a2b25ae367b288a8fb18d7cb7afb42124","me0_authority_document_path":"docs/experiments/uprime_odlrq_post_e2_me0_s0_i0_continuation_amendment_2026-07-17.md","me0_authority_parent_sha":"7a8b28872439dd61d40174c2500c5990790002be","runtime_manifest_sha256":"F20A2C1A6556EAAC5371C7438A5F588A3F7E5A76282E2F500614B2E43FF6C05A","schema_version":"odlrq.me0.declared-e2-support-reference.v1","support_candidate_ids":["c0","c2"],"tier":"NOMINAL_MODEL_SELECTION_ONLY"},"target":[{"denominator":"5","numerator":"4","schema_version":"lean-rgc-odlrq-exact-rational-v1"}],"tier":"NOMINAL_MODEL_SELECTION_ONLY"}
```

The exact canonical S0-selected ME0 nontrivial-orbit Windows result wire is:

```json
{"certified_support_token_sha256":"D01170427E717D543D941740881C937EF5B535E357D67EEFDBF62773AFD6E660","dual_parameter":["0.14384103623693401"],"dual_residual_inf":"1.0601741706750545e-11","expected_row_load":"1.8000000000106016","fallback_candidate_id":null,"fallback_used":false,"fitted_expected_load":"1.8000000000106016","geometry":{"affine_rank":1,"declared_dimension":1,"membership_subset_indices":[0,1],"membership_weights":[{"denominator":"5","numerator":"3","schema_version":"lean-rgc-odlrq-exact-rational-v1"},{"denominator":"5","numerator":"2","schema_version":"lean-rgc-odlrq-exact-rational-v1"}],"schema_version":"odlrq.me0.moment-geometry.v1","status":"INTERIOR_SOLVED","subset_work_bound":3,"supporting_face_indices":[],"tier":"NOMINAL_MODEL_SELECTION_ONLY"},"kl_divergence":"0.0097123133244110954","kl_radius":{"denominator":"20","numerator":"1","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"kl_within_radius":true,"log_partition":"0.1053605156666611","me0_authority_ci_job_id":"87793466452","me0_authority_ci_run_id":"29551068987","me0_authority_commit_sha":"0ff63861a2957b53f4c0b5f2948d561d936337ca","me0_authority_document_blob_sha":"831c226a2b25ae367b288a8fb18d7cb7afb42124","me0_authority_document_path":"docs/experiments/uprime_odlrq_post_e2_me0_s0_i0_continuation_amendment_2026-07-17.md","me0_authority_parent_sha":"7a8b28872439dd61d40174c2500c5990790002be","moment_residual_inf":"1.0601741706750545e-11","operator_span":{"coefficients":["1.9999999999999996"],"column_ids":["g0"],"residual_l2":"9.9301366129890925e-16","schema_version":"odlrq.me0.operator-span-residual.v1","tier":"NOMINAL_MODEL_SELECTION_ONLY","tolerance":"1e-10","within_tolerance":true},"operator_span_residual":"9.9301366129890925e-16","operator_tier":"NOMINAL_MODEL_SELECTION_ONLY","orbit_expected_row_load":"1.6666666666666665","orbit_reference":{"normalization":{"denominator":"4","numerator":"3","schema_version":"lean-rgc-odlrq-exact-rational-v1"},"probabilities":[{"denominator":"3","numerator":"2","schema_version":"lean-rgc-odlrq-exact-rational-v1"},{"denominator":"3","numerator":"1","schema_version":"lean-rgc-odlrq-exact-rational-v1"}],"schema_version":"odlrq.me0.orbit-reference-law.v1","support_candidate_ids":["c0","c2"],"tier":"NOMINAL_MODEL_SELECTION_ONLY","unnormalized_mass":[{"denominator":"2","numerator":"1","schema_version":"lean-rgc-odlrq-exact-rational-v1"},{"denominator":"4","numerator":"1","schema_version":"lean-rgc-odlrq-exact-rational-v1"}]},"orbit_reference_probabilities":["0.66666666666666663","0.33333333333333331"],"pinsker_rhs":"1.9828944326835045","pinsker_upper":"1.9828944326835045","probabilities":["0.59999999999469911","0.40000000000530089"],"problem_sha256":"20A376AD298A285949284B19D8589AD190054D870B6A7341D598D59F7EBFAF8C","reference_expected_load":"1.6666666666666665","row_table_sha256":"75FFB3222E1CA31CF4F558F1955D18B74C62B6D622DE862820173FE329526A76","runtime_manifest_sha256":"F20A2C1A6556EAAC5371C7438A5F588A3F7E5A76282E2F500614B2E43FF6C05A","schema_version":"odlrq.me0.maxent-result.v1","selected_candidate_id":"c0","simplex_error":"0","simplex_residual":"0","status":"INTERIOR_SOLVED","support_candidate_ids":["c0","c2"],"support_reference":{"accepted_e2_commit_sha":"7a8b28872439dd61d40174c2500c5990790002be","accepted_e2_tree_sha":"d54ed9fab52da4929843fabdeb3c1e1920994f6a","certified_support_token_sha256":"D01170427E717D543D941740881C937EF5B535E357D67EEFDBF62773AFD6E660","me0_authority_ci_job_id":"87793466452","me0_authority_ci_run_id":"29551068987","me0_authority_commit_sha":"0ff63861a2957b53f4c0b5f2948d561d936337ca","me0_authority_document_blob_sha":"831c226a2b25ae367b288a8fb18d7cb7afb42124","me0_authority_document_path":"docs/experiments/uprime_odlrq_post_e2_me0_s0_i0_continuation_amendment_2026-07-17.md","me0_authority_parent_sha":"7a8b28872439dd61d40174c2500c5990790002be","runtime_manifest_sha256":"F20A2C1A6556EAAC5371C7438A5F588A3F7E5A76282E2F500614B2E43FF6C05A","schema_version":"odlrq.me0.declared-e2-support-reference.v1","support_candidate_ids":["c0","c2"],"tier":"NOMINAL_MODEL_SELECTION_ONLY"},"tier":"NOMINAL_MODEL_SELECTION_ONLY","verification_disposition":"CPU_SYNTHETIC_MAXENT_CORE_VERIFIED"}
```

The two envelope and problem digests are portable exact identities under
`canonical_contract_bytes`.  The nontrivial result digest is explicitly a
Windows-runtime artifact identity; natural Linux CI verifies its strict wire,
support, equations, and registered tolerances but does not claim bit-identical
LAPACK intermediates.  S0 and I0 must parse, reserialize, rehash, and
semantically verify every object before using it.  A digest-only object cannot
satisfy a live binding.  The accepted-E1 qualification envelope and the E2 M0
pipeline parent envelope are different valid fixtures and must never be
substituted or called by one generic name.

### 1.2 Dated red-CI clarification

On 2026-07-17, the immutable U05 result commit
`cc91a4181a9f87ec10f11727ed787eb7149f955a` still has red CI run/job
`29166670576 / 86580832840`.  The registered audit identified a
shallow-history omission in the guard, not a scientific failure; the exact
candidate commit `3bb3408afc50a08307cff2c9b1906a299739dfb5` passed green CI
run/job `29166073728 / 86579287017`.  Future readers must not interpret the
red result badge as a failed kill probe.  The authority, activation, and
closeout sidecars below likewise have an intentionally registered single
topology-control failure; only the S0 and I0 semantic candidate/accepted
commits are scientific green gates.

### 1.3 Narrow precedence over the inherited roadmap

The inherited normative blob
`bd3ef021dff5cb5e3a28c1d2a79b0379e5615835` remains controlling except for the
following explicit refinements, which this later authority was required to
freeze before S0 source exists:

- the eight inherited S0 cases retain their exact values and order, and the
  sole new ninth audit case `s-numeric` is appended to trip the previously
  unisolated numeric-residual term;
- the inherited six-role I0 digest tuple is refined into the twelve named,
  typed, source-commit-bound authorities in section 8 to prevent envelope,
  cocycle, positive/predictive, and sidecar splicing;
- the seven inherited artifact schemas, common fields, and outer payload key
  orders remain unchanged.  Positive/predictive core hashes are carried by the
  strict similarity `verification_report`, not added as outer payload keys;
  section 9 supplies the previously absent operator-projection and nested-report
  semantics; and
- the exact S0/I0 allowlists, commands, bounds, refs, and the mechanically
  infeasible old green-closeout clause are governed by sections 3--4.

No existing case value, hard equation, artifact schema name, common field, or
payload order is silently changed.  These refinements repair endpoint and
governance under-specification; they do not promote MaxEnt or predictive data
to safety evidence.

## 2. Frozen hard and nominal authorities

S0 positive safety binds the following ordered hard authority tuple and no
other predecessor.  Its canonical wire is 1254 bytes and has SHA-256
`840B46E6743EF531DC3C7266CEA3BE3D2A731959A8F9E808207372E17CCC97F0`.

```json
{"accepted_e1_commit_sha":"6fb35aa229fc60e2220cbb68c1e7fff2ce64f199","accepted_e1_qualification_envelope_sha256":"D959B07CEF0A79A9478FAB99D3329D39DFF215A183FCD564B2547DBBE7EBD0C6","accepted_e1_tree_sha":"b3fc7f21b6420e718eb954be0c1b5affca65d263","accepted_e2_commit_sha":"7a8b28872439dd61d40174c2500c5990790002be","accepted_e2_tree_sha":"d54ed9fab52da4929843fabdeb3c1e1920994f6a","domain_scope":"declared_finite_totalized_snapshot_only","e2_candidate_universe_manifest_sha256":"327DDC3DBD63C049A1B16B570B81F5DDECCE1B8C3C7F83734609C83B12501D9A","e2_certified_support_token_sha256":"D01170427E717D543D941740881C937EF5B535E357D67EEFDBF62773AFD6E660","e2_m0_parent_envelope_sha256":"9BA692E8A14C5C56BCDE6D565082300A9D0BB7A888DE5533F31DC1896E9B157C","e2_p1_cocycle_sha256":"6C87E7EE21B8BC0D78D024AB14C2D5F247D541531A90D6291732D284C7FFEF11","e2_p2_cocycle_sha256":"BEE7B16BC7FF8AF926CDF8F5502F21B2708A9C4C280F57AC846889B2C50A065D","e2_return_memory_bound_sha256":"95C2BEDA13B1085E46183038F857B753AE0DC531685BC3996EB1E5F5AFAD4A46","evidence_scope":"declared_synthetic","norm_id":"weighted_l1_exact_rational_v1","s0_primitive_universe_sha256":"9FA1D0431DF67EEDD0661EE70A0836A60ECF6153488EDE21699DD24867722FEC","schema_version":"odlrq.s0.hard-authority-tuple.v3"}
```

The tuple values are:

```text
accepted-E1 qualification envelope
  D959B07CEF0A79A9478FAB99D3329D39DFF215A183FCD564B2547DBBE7EBD0C6
E2 M0 pipeline parent envelope
  9BA692E8A14C5C56BCDE6D565082300A9D0BB7A888DE5533F31DC1896E9B157C
E2 candidate universe manifest
  327DDC3DBD63C049A1B16B570B81F5DDECCE1B8C3C7F83734609C83B12501D9A
E2 P1 cocycle
  6C87E7EE21B8BC0D78D024AB14C2D5F247D541531A90D6291732D284C7FFEF11
E2 P2 cocycle
  BEE7B16BC7FF8AF926CDF8F5502F21B2708A9C4C280F57AC846889B2C50A065D
E2 return-memory bound
  95C2BEDA13B1085E46183038F857B753AE0DC531685BC3996EB1E5F5AFAD4A46
E2 certified-support token
  D01170427E717D543D941740881C937EF5B535E357D67EEFDBF62773AFD6E660
S0 primitive universe
  9FA1D0431DF67EEDD0661EE70A0836A60ECF6153488EDE21699DD24867722FEC
```

`DeclaredS0HardAuthorityReference` is the serializable digest reference.
`LiveS0HardAuthorityBinding` is a nonserializable capability with no public
constructor.  `bind_s0_hard_authorities` accepts only two exact production
`FiberEnvelope` objects (the accepted-E1 qualification envelope and the E2 M0
pipeline parent envelope) plus the exact production `CertifiedSupportToken`.
It reruns strict verification, compares all three full canonical wires and
every embedded digest, and then constructs the live capability.  Subclasses, duck types, serializer
overrides, stale commits, and spliced rows fail closed.

The nominal ME0 binding is separate:

```text
accepted ME0 commit/tree
  28749bf2f0fc67bc55a24e9e07fc03ad6c66b98d
  a3b3513ca93430c9f15e5bd90888e81b0af1ff9c
selected nontrivial problem full/core SHA-256
  F055C10309DB4AFCA1A140ECFE3FAAF3AF2BF11F7B25F6366F92667446899B7B
  20A376AD298A285949284B19D8589AD190054D870B6A7341D598D59F7EBFAF8C
selected nontrivial result Windows-artifact SHA-256
  DCA363A6C8CC15ED13C4182DE7BFD2F68293E83C1766419B439C1AE8309C42E3
selected nontrivial row-table SHA-256
  75FFB3222E1CA31CF4F558F1955D18B74C62B6D622DE862820173FE329526A76
tier
  NOMINAL_MODEL_SELECTION_ONLY
```

`DeclaredME0ResultReference` is predictive provenance only.
`LiveME0ResultBinding` requires the exact nontrivial-orbit
`MaxEntProblem` and frozen-Windows `MaxEntResult`, full semantic
verification, fixed E2 support `["c0","c2"]`, the exact problem bytes, and
the runtime-qualified result bytes.  The primary fixture digests remain a
separate accepted-ME0 audit anchor and are not silently substituted.  Neither nominal type is accepted by a
positive-distance, target-residual, L-plus, hard transport, or hard pipeline
constructor.

## 3. Publication topology and authority scope

The topology is:

```text
accepted ME0 28749bf2
  +-- document-only combined S0/I0 authority sidecar
  |
  +-- S0 candidate --fast-forward--> accepted S0
                                  +-- document-only I0 activation sidecar
                                  |
                                  +-- I0 candidate --fast-forward--> accepted I0
                                                                  +-- artifact/closeout sidecar
```

### 3.1 Combined authority sidecar

```text
parent       28749bf2f0fc67bc55a24e9e07fc03ad6c66b98d
ref          codex/uprime-post-me0-s0-i0-authority
subject      docs: freeze post-ME0 S0-I0 authority
changed path docs/experiments/uprime_odlrq_post_me0_s0_i0_authority_2026-07-17.md
path mode    100644
```

The ref is created once by non-force push and never moved, deleted, rewritten,
rerun, or merged into the accepted line.  Before S0 source work, natural CI must
have exactly the sole failure
`test_u24_b0_anchor_contiguous_budget_and_terminal_topology` and:

```text
1 failed, 2618 passed, 8 skipped, 161 deselected
```

Any other failure, any S0/I0 node collection, or any different count blocks
publication until the authority-side implementation/governance defect is
repaired on a fresh authority ref.  It is not a theory failure.

After that exact CI shape is verified, S0 source and its first test mechanically
resolve and bind:

```text
S0_AUTHORITY_COMMIT_SHA
S0_AUTHORITY_PARENT_SHA
S0_AUTHORITY_DOCUMENT_PATH
S0_AUTHORITY_DOCUMENT_BLOB_SHA
S0_AUTHORITY_CI_RUN_ID
S0_AUTHORITY_CI_JOB_ID
```

The parent and path are frozen above; the commit, blob, run, and job are
necessarily filled only after the immutable authority publication.  This is
mechanical identity completion, not a semantic amendment.  Candidate preflight
fresh-fetches the authority ref and machine-compares all six values before
local qualification and before push.  Hand-copied hashes do not satisfy the
gate.

### 3.2 S0 semantic publication

The primary immutable candidate ref is `codex/uprime-s0-candidate`; fresh
replacement refs, if needed, are `-a2` then `-a3`.  Each is a direct
single-parent child of accepted ME0, never of this authority sidecar.  It
changes exactly:

```text
lean_rgc/odlrq/similarity.py
lean_rgc/odlrq/__init__.py
tests/test_odlrq_similarity.py
tests/tier_manifest.json
```

The manifest change is only the exact new row
`"test_odlrq_similarity.py":["unit"]`.  Candidate and distinct accepted CI
must each be green with exactly:

```text
2629 passed, 8 skipped, 161 deselected
```

Acceptance is a byte-identical fast-forward of `codex/uprime-odlrq-plan`.
No merge, cherry-pick, force push, rerun, authority import, or outcome-dependent
fixture change substitutes for it.

### 3.3 Mechanical I0 activation

After green accepted S0, a document-only direct child is published at:

```text
path docs/experiments/uprime_odlrq_post_s0_i0_activation_2026-07-17.md
ref  codex/uprime-post-s0-i0-activation
```

It may fill only:

- accepted S0 commit and tree;
- the four S0 path blob IDs;
- S0 candidate and accepted CI run/job IDs;
- the exact canonical S0 `SimilarityCertificate` bytes, byte count, and
  SHA-256;
- the recomputed `positive_core_sha256` and `predictive_core_sha256` values,
  with byte counts and canonical projection bytes for both projections;
- the fixed S0 runtime-manifest SHA-256 from section 4; and
- confirmation that all fixed values below matched.

It may not alter any equation, fixture, schema, node, command, cap, tier,
threshold, path, or disposition.  It is never merged into the accepted line.
Its natural CI must have only the topology failure and exactly:

```text
1 failed, 2628 passed, 8 skipped, 161 deselected
```

After that exact control shape, I0 source and tests mechanically resolve and
bind the activation's commit, parent, document path/blob, and CI run/job as
`I0_ACTIVATION_*` constants.  I0 candidate preflight fresh-fetches the
activation ref and compares them.  The activation document cannot self-name
its future commit; post-push mechanical identity completion is the only
permitted filling step.

### 3.4 I0 semantic publication and closeout

The primary immutable I0 candidate is `codex/uprime-i0-candidate`, with
`-a2/-a3` replacements.  It is a direct child of accepted S0, not the
activation sidecar, and changes exactly:

```text
lean_rgc/odlrq/certificates.py
lean_rgc/odlrq/__init__.py
lean_rgc/evals/uprime_u2_u4_development.py
tests/test_uprime_u2_u4_development.py
```

This exact four-path allowlist supersedes the broader inherited I0 list:
`tools/run_uprime_u2_u4_development_tests.ps1` and
`tests/tier_manifest.json` must not change.  Candidate and distinct accepted
CI must each be green with exactly:

```text
2638 passed, 8 skipped, 161 deselected
```

The accepted first-parent build rows are then exactly E1, E2,
E2-correction, ME0, S0, I0: six rows and one correction, meeting the existing
`MAX_BUILD_COMMITS=6` bound.  Sidecars are excluded from that ancestry.

After accepted I0, emission and closeout occur in a separate direct-child
sidecar:

```text
document docs/experiments/uprime_odlrq_post_e2_upper_stack_closeout_2026-07-17.md
ref      codex/uprime-post-e2-upper-stack-closeout
root     docs/experiments/artifacts/uprime_odlrq_post_e2_upper_stack_20260717/
```

The closeout changes only the document and the seven frozen artifacts in
section 11.  It is never merged.  Natural CI is registered to have only the
topology failure and exactly:

```text
1 failed, 2637 passed, 8 skipped, 161 deselected
```

This paragraph explicitly supersedes the single green-closeout requirement in
section 8 of authority commit `0ff63861a2957b53f4c0b5f2948d561d936337ca`.
The reason is mechanical, not scientific.  The identity core eagerly fixes
`SUCCESS_TERMINAL_PATHS`, `TRACKED_PATHS`, and `CONTROL` before the I0 extension
marker; the guard fixes the identity-core SHA and permits only zero-argument,
undecorated `test_u24_i0_*` function definitions inside that marker.  An I0
extension therefore cannot assign or mutate those eager constants, hide new
Git paths, or alter the guard/runner hashes.  Making the sidecar green would
require a fresh control authority changing the identity core together with its
guard and runner, outside the four-path I0 semantic allowlist.  This authority
instead registers the sole-red closeout shape above.  S0 and I0 semantic
candidate/accepted CI remain green; no mathematical, schema, tier, fixture, or
verification rule is weakened.

### 3.5 Unique bounded-failure closeout

If the three registered S0 or I0 candidate refs are exhausted and no rational
repair remains inside the frozen semantics, exactly one document-only failure
sidecar is licensed:

```text
document docs/experiments/uprime_odlrq_post_e2_upper_stack_failure_closeout_2026-07-17.md
ref      codex/uprime-post-e2-upper-stack-failure-closeout
```

It is a direct child of the last accepted semantic commit, contains the failed
candidate/ref/CI identities and concise remedy audit, creates no artifact, and
is never merged.  If S0 never accepts, its parent is accepted ME0 and natural
CI must have only the topology failure with exactly
`1 failed, 2618 passed, 8 skipped, 161 deselected`.  If S0 accepts but I0 never
does, its parent is accepted S0 and natural CI must have only that failure with
exactly `1 failed, 2628 passed, 8 skipped, 161 deselected`.  Any other shape is
an engineering/governance defect to record and repair, not a mathematical
result.  This sidecar is not published merely because a repair attempt fails;
the anti-fractal rule in section 12 controls exhaustion and escalation.

## 4. Execution model and resource bounds

All work is local Windows CPU plus natural repository CI.  No protected
endpoint, reserved data, GPU, SSH, LLM, native Lean oracle, external capture
wrapper, evidence ledger, custom runner, retry loop, or R13 calibration is
licensed.
Normal `git fetch`/`git ls-remote` used by the inline PowerShell parent solely
to verify immutable publication refs is control-plane traffic, not a scientific
endpoint or a license for Python-module network access.

The S0 Windows runtime manifest is exactly 443 UTF-8 bytes with SHA-256
`88FE6E69BB6B0E7BFE2C1C6EB220F420ECA0BE25826D48A90BD318641F3E89C9`:

```json
{"nominal_me0_live_verification_may_import_numpy":true,"pytest_version":"9.0.3","python_executable_sha256":"D932E5E2F324D57F392E8FD063DCF6D0185BE8A664C57C6D24E7762ED02C28CA","python_version":"3.13.7","schema_version":"uprime.s0.windows-runtime.v2","similarity_module_direct_numpy_import":false,"thread_environment":{"MKL_NUM_THREADS":"1","NUMEXPR_NUM_THREADS":"1","OMP_NUM_THREADS":"1","OPENBLAS_NUM_THREADS":"1","VECLIB_MAXIMUM_THREADS":"1"}}
```

The full integrated runtime identity remains the ME0 superset manifest
`F20A2C1A6556EAAC5371C7438A5F588A3F7E5A76282E2F500614B2E43FF6C05A`;
the S0 certificate additionally binds the direct-import/nominal-boundary stage digest above.

Thread variables are all `1`; `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`,
`PYTHONDONTWRITEBYTECODE=1`, and `PYTHONHASHSEED=0` are required.
Qualification uses an unpersisted inline `System.Diagnostics.Process` with
inherited console, hard wall, child exit-code propagation, RSS polling, and a
single kill followed by at most ten seconds cleanup.  It creates no capture,
receipt, marker, runner, or control artifact.

The inline supervisor is frozen as follows.  `ProcessStartInfo.FileName` is the
absolute Python path above; legacy Windows PowerShell 5.1 / CLR 4 uses
`ProcessStartInfo.Arguments` set by joining the applicable frozen ASCII token
array with exactly one U+0020 space (every token contains no whitespace or
quotes).  In every displayed command the absolute executable is `FileName` and
is excluded from `Arguments`: the S0 array begins with `-m`; the I0 array begins
with `-m` and expands the placeholder to the nine section-10 node IDs in their frozen order; the emission
array substitutes only the two mechanically resolved lowercase SHA-1 tokens.
`WorkingDirectory` is the clean candidate worktree,
`UseShellExecute=false`, all three standard streams are not redirected, and
`CreateNoWindow=true`.  It copies the parent OS environment, removes
`PYTEST_ADDOPTS` and `PYTHONPATH`, and overwrites exactly the eight Python/thread
variables named in this section.  A `Stopwatch` starts immediately before
`Process.Start`.  The parent polls `HasExited` and child `WorkingSet64` every
100 ms; after confirming the process has not exited, every poll calls
`Process.Refresh()` before reading `WorkingSet64`, because .NET Framework
otherwise serves a cached value.  Static capability checks forbid child subprocess creation, so the
single Python process is the RSS accounting unit.  Crossing the wall or RSS cap
calls parameterless `Kill()` exactly once, then `WaitForExit(10000)`,
and fails even if a late zero exit is observed.  Otherwise the exact child exit
code is propagated.  Failure to start, inspect, kill, or reap also fails; it
does not trigger a retry or an alternate wrapper.

S0 command:

```text
C:\Python313\python.exe -m pytest -q --tb=line --show-capture=no -p no:cacheprovider tests/test_odlrq_similarity.py
```

Before qualification, the same supervisor runs
`pytest --collect-only -q -p no:cacheprovider` on the exact ten S0 node IDs in section 10, under a
30-second/512-MiB cap, and requires those ten IDs in that order and no other
node.  Collection failure or substitution is a non-scientific repairable
preflight failure.

S0 requires exact `10 passed`, zero skip/xfail/deselection/warning
substitution, 120-second wall, and 1-GiB RSS.

I0 qualification invokes the exact nine full node IDs in section 10 with:

```text
C:\Python313\python.exe -m pytest -q --tb=line --show-capture=no -p no:cacheprovider <the nine frozen I0 node IDs in order>
```

Its preflight runs the corresponding exact-node `--collect-only -q` command
under a 60-second/512-MiB cap and requires exactly the nine IDs in order.
I0 requires exact `9 passed`, zero skip/xfail/deselection/warning
substitution, 1200-second wall, 2-GiB RSS, and no artifact left behind.
Static capability inspection rejects process, shell, network, SSH, GPU, LLM,
native Lean, protected/read-reserved, and dynamic-import escape hatches.
Because the identity extension region itself cannot contain `Import` or
`ImportFrom` statements, exactly two literal built-in imports are licensed
inside each frozen I0 test function and nowhere else:

```text
__import__("lean_rgc.odlrq", fromlist=(
  "PipelineEvidenceTier","PipelineDisposition","TypedPipelineFactor",
  "NominalPipelineAddendum","TypedPipelineBound",
  "construct_typed_pipeline_bound","verify_typed_pipeline_bound"))

__import__("lean_rgc.evals.uprime_u2_u4_development", fromlist=(
  "build_u24_i0_fixture","build_u24_artifact_wires",
  "verify_u24_artifact_wires","emit_u24_artifacts"))
```

The AST audit requires these exact module-name string literals and exact
`fromlist` tuples.  It rejects `importlib`, any other `__import__`, nonliteral
arguments, aliasing the built-in, private/underscore attribute access, and all
arbitrary dynamic import.  The four development-module names are its entire
`__all__`.  Their keyword-only signatures are exactly:

```text
build_u24_i0_fixture()
build_u24_artifact_wires(*, fixture, source_commit, source_tree)
verify_u24_artifact_wires(*, fixture, source_commit, source_tree, ordered_wires)
emit_u24_artifacts(*, fixture, source_commit, source_tree, destination_root)
```

The fixture is a sealed in-memory bundle constructed only from the frozen live
public predecessors; it is not serializable and cannot be caller-forged.
`ordered_wires` is the exact seven `(name,bytes)` tuple.  The emitter requires
an absent `Path` root and applies the same transaction to either the official
CLI root or a test-owned absent child of `TemporaryDirectory`; there is no
test-mode flag or endpoint selector.  Only the module CLI performs the parent
Git preflight and chooses the fixed official root.  Bounded error strings cap
structural output at 128 KiB.

Emission after accepted I0 uses the same inherited-console supervisor, 1200
seconds, 2 GiB, and one command:

```powershell
$sourceCommit = (& git rev-parse --verify 'HEAD^{commit}').Trim()
$sourceTree = (& git rev-parse --verify 'HEAD^{tree}').Trim()
$pythonArgumentTokens = @('-m','lean_rgc.evals.uprime_u2_u4_development','emit','--source-commit',$sourceCommit,'--source-tree',$sourceTree)
# The inline ProcessStartInfo supervisor launches Python with these joined tokens;
# direct invocation with '&' is forbidden.
```

The module constructs the official artifact root from fixed `Path` segments
so source does not contain the forbidden literal artifact-root prefix.  Tests
emit only to a fresh temporary root.  Emission is one-shot, exclusive, and
fails if the official root or any target file already exists.

Before starting the Python process, the inline PowerShell parent requires empty
`git status --porcelain=v1 --untracked-files=all`, the expected accepted branch,
and a non-detached HEAD.  It fresh-fetches `codex/uprime-odlrq-plan`, obtains
the three candidate remote values with one exact `git ls-remote --heads`, and
requires accepted HEAD to equal the accepted remote and exactly one immutable
candidate ref from `codex/uprime-i0-candidate`, `-a2`, `-a3`.  It resolves
`HEAD^{commit}` and `HEAD^{tree}` mechanically, verifies the authority and
activation refs/identities, checks the official root is absent, and only then
passes the two resolved SHA-1 values above.  A stale, dirty, detached, multiply
matching, or missing-ref state fails before Python or filesystem mutation.

The Python emitter is deliberately subprocess- and network-free.  It validates
the two CLI SHA-1 strings, requires them on every wrapper/receipt, rechecks all
embedded authority, activation, object, and runtime identities from its frozen
constants/live public constructors, and performs only build/verify/write.  The
parent's Git comparisons are the sole local-HEAD/remote-ref authority; no
Python Git library, `git` child process, or process-tree exemption is used.

All seven wires are built and verified in memory first.  The writer then
creates, with `exist_ok=false`, a same-volume sibling staging directory named
`.uprime_odlrq_post_e2_upper_stack_20260717.staging.<HEAD12>.<pid>.<32hex>`,
where the final component is one `secrets.token_hex(16)` control nonce.  The
successful exclusive directory creation makes that path invocation-owned; the
nonce has no scientific meaning and is absent from every artifact.  Files are
opened in the frozen order with `O_WRONLY|O_CREAT|O_EXCL|O_BINARY`, written once,
flushed, closed, reread, and byte- and semantically reverified.  The staging
directory must then contain exactly the seven names and no reparse point.  A
single same-volume atomic directory rename publishes it to the still-absent
official root.  On any pre-rename failure, only the invocation-owned staging
path is removed; an existing official root or foreign staging path is never
deleted or modified.  There is no retry.  Success writes exactly one compact
JSON receipt of at most 4096 UTF-8 bytes to stdout containing schema, source
commit/tree, seven ordered `(name,bytes,sha256)` rows, and disposition.  Any
aggregated diagnostic is capped at 128 KiB.

## 5. S0 public surface and strict schemas

S0 adds exactly these public types:

```text
ApproximationLevelId
PrimitiveTargetRow
CountedCoverageWitness
DeclaredS0HardAuthorityReference
LiveS0HardAuthorityBinding
DeclaredME0ResultReference
LiveME0ResultBinding
DeclaredSyntheticLPlusToken
TargetResidualBound
GlobalMeasure
PredictiveDistance
PositiveDistance
RadiusMorphism
WordDepthMorphism
GranularityMorphism
LocalTower
PredictiveTransportCertificate
PositiveTransportCertificate
FiniteRemainderCertificate
SimilarityCertificate
DeclaredSyntheticSimilarityFixture
```

and exactly these public endpoints:

```text
make_declared_s0_hard_authority_reference
bind_s0_hard_authorities
make_declared_me0_result_reference
bind_me0_result
declare_synthetic_l_plus
make_counted_coverage_witness
make_target_residual_bound
make_global_measure
compute_predictive_distance
compute_positive_distance
make_radius_morphism
make_word_depth_morphism
make_granularity_morphism
build_local_tower
verify_predictive_transport
verify_positive_transport
certify_finite_remainder
build_declared_synthetic_similarity_fixture
verify_similarity_certificate
verify_similarity_certificate_live
```

Exact schema literals and closed vocabularies:

| type | schema |
|---|---|
| `ApproximationLevelId` | `odlrq.s0.approximation-level-id.v1` |
| `PrimitiveTargetRow` | `odlrq.s0.primitive-target-row.v1` |
| primitive universe | `odlrq.s0.primitive-universe.v2` |
| `CountedCoverageWitness` | `odlrq.s0.counted-coverage-witness.v1` |
| `DeclaredS0HardAuthorityReference` | `odlrq.s0.declared-hard-authority-reference.v1` |
| `DeclaredME0ResultReference` | `odlrq.s0.declared-me0-result-reference.v1` |
| `DeclaredSyntheticLPlusToken` | `odlrq.s0.declared-synthetic-lplus-token.v1` |
| `TargetResidualBound` | `odlrq.s0.target-residual-bound.v1` |
| `GlobalMeasure` | `odlrq.s0.global-measure.v1` |
| `PredictiveDistance` | `odlrq.s0.predictive-distance.v1` |
| `PositiveDistance` | `odlrq.s0.positive-distance.v1` |
| `RadiusMorphism` | `odlrq.s0.radius-morphism.v1` |
| `WordDepthMorphism` | `odlrq.s0.word-depth-morphism.v1` |
| `GranularityMorphism` | `odlrq.s0.granularity-morphism.v1` |
| `LocalTower` | `odlrq.s0.local-tower.v1` |
| `PredictiveTransportCertificate` | `odlrq.s0.predictive-transport.v1` |
| `PositiveTransportCertificate` | `odlrq.s0.positive-transport.v1` |
| `FiniteRemainderCertificate` | `odlrq.s0.finite-remainder.v1` |
| `SimilarityCertificate` | `odlrq.s0.similarity-certificate.v1` |
| positive-core projection | `odlrq.s0.positive-core-projection.v1` |
| predictive-core projection | `odlrq.s0.predictive-core-projection.v1` |
| `DeclaredSyntheticSimilarityFixture` | `odlrq.s0.declared-similarity-fixture.v1` |
| case-result row | `odlrq.s0.similarity-case-result.v1` |

```text
normalization_mode:
  UNIT_BOTH | ZERO_BOTH
morphism axis:
  RADIUS | WORD_DEPTH | GRANULARITY
evidence tier:
  DECLARED_SYNTHETIC_HARD | PREDICTIVE_NOMINAL_ONLY
positive disposition:
  POSITIVE_SAFETY_MAJORANT_VERIFIED | ABSTAIN_INCOMPLETE_COVERAGE
target disposition:
  HARD_TARGET_RESIDUAL_VERIFIED | ABSTAIN_INCOMPLETE_COVERAGE
predictive disposition:
  PREDICTIVE_DISTANCE_VERIFIED
morphism disposition:
  FINITE_LEVEL_MORPHISM_VERIFIED
transport disposition:
  PREDICTIVE_TRANSPORT_VERIFIED | POSITIVE_TRANSPORT_VERIFIED
remainder disposition:
  FINITE_REMAINDER_VERIFIED
similarity disposition:
  CPU_SYNTHETIC_TYPED_SIMILARITY_CORE_VERIFIED
```

All public functions are keyword-only after the function name, perform exact
type checks before attribute access, and have these signatures:

```text
make_declared_s0_hard_authority_reference(*, primitive_rows)
bind_s0_hard_authorities(*,
  accepted_e1_qualification_envelope,
  e2_m0_parent_envelope,
  e2_support_token)
make_declared_me0_result_reference(*, problem_wire, result_wire)
bind_me0_result(*, problem, result)
declare_synthetic_l_plus(*, hard_reference, primitive_rows, coverage)
make_counted_coverage_witness(*, ordered_universe_ids, covered_ids)
make_target_residual_bound(*, l_plus_token, measure_id, coverage)
make_global_measure(*, measure_id, level, node_ids, edge_ids,
  node_mass, edge_mass, cross_covariance_residual, numeric_residual)
compute_predictive_distance(*, me0_reference, x, y)
compute_positive_distance(*, l_plus_token, coverage,
  x_target_residual, y_target_residual, x, y)
make_radius_morphism(*, source_level, target_level, node_matrix, coverage,
  commutator_l1, target_residual_transport, cross_covariance_budget,
  numeric_residual_budget, remainder_e)
make_word_depth_morphism(*, source_level, target_level, node_matrix, coverage,
  commutator_l1, target_residual_transport, cross_covariance_budget,
  numeric_residual_budget, remainder_e)
make_granularity_morphism(*, source_level, target_level, node_matrix, coverage,
  commutator_l1, target_residual_transport, cross_covariance_budget,
  numeric_residual_budget, remainder_e)
build_local_tower(*, ordered_levels, radius_morphism,
  word_depth_morphism, granularity_morphism)
verify_predictive_transport(*, me0_reference, morphism,
  x_fine, y_fine, x_coarse, y_coarse)
verify_positive_transport(*, l_plus_token, coverage, morphism,
  x_fine_target_residual, y_fine_target_residual,
  x_coarse_target_residual, y_coarse_target_residual,
  x_fine, y_fine, x_coarse, y_coarse)
certify_finite_remainder(*, tower,
  predictive_transport_certificates, positive_transport_certificates)
build_declared_synthetic_similarity_fixture(*, hard_reference, me0_reference)
verify_similarity_certificate(*, certificate)
verify_similarity_certificate_live(*, certificate, hard_binding, me0_binding)
```

The two envelope arguments are named and keyword-only; swapping D959 and 9BA
fails before construction.  The binder requires both exact wires to differ,
rederives the E2 token's manifest/P1/P2/return authorities, and does not assert
that the accepted-E1 qualification fixture equals E2's M0 parent fixture.

`similarity.py.__all__` and package exports equal these names plus no hidden
safety/selector endpoint.  Private helpers are not package exports.
`build_declared_synthetic_similarity_fixture` is the sole public fixture
builder used later by I0; I0 may not import test helpers.

Every serializable S0 type has a distinct `odlrq.s0.*.v1` schema.  The lists
below define the producer's readable `to_dict` order and the exact required
key set.  In-memory object-key insertion order is not semantic:
`canonical_contract_bytes` sorts object keys lexicographically, and
`from_dict` accepts that canonical parse while requiring the exact key set.
Raw canonical bytes must decode without duplicate keys and re-encode
byte-identically.  Array order, row-table order, level order, case order, and
matrix axes are semantic and must match exactly.

```text
ApproximationLevelId:
  schema_version,frame_id,domain_id,radius,word_depth,granularity

PrimitiveTargetRow:
  schema_version,primitive_id,node_load,edge_load,target_residual

CountedCoverageWitness:
  schema_version,ordered_universe_ids,covered_ids,covered_count,
  universe_count,universe_ids_sha256,covered_ids_sha256,complete

DeclaredS0HardAuthorityReference:
  schema_version,s0_authority_commit_sha,s0_authority_parent_sha,
  s0_authority_document_path,s0_authority_document_blob_sha,
  s0_authority_ci_run_id,s0_authority_ci_job_id,
  accepted_e1_commit_sha,accepted_e1_tree_sha,
  accepted_e1_qualification_envelope_sha256,accepted_e2_commit_sha,
  accepted_e2_tree_sha,e2_m0_parent_envelope_sha256,
  e2_candidate_universe_manifest_sha256,e2_p1_cocycle_sha256,
  e2_p2_cocycle_sha256,e2_return_memory_bound_sha256,
  e2_certified_support_token_sha256,s0_primitive_universe_sha256,
  norm_id,evidence_scope,domain_scope,authority_tuple_sha256

DeclaredME0ResultReference:
  schema_version,accepted_me0_commit_sha,accepted_me0_tree_sha,
  me0_problem_wire_sha256,me0_problem_core_sha256,
  me0_windows_result_wire_sha256,me0_row_table_sha256,status,
  support_candidate_ids,runtime_manifest_sha256,evidence_tier,predictive_only

DeclaredSyntheticLPlusToken:
  schema_version,hard_authority_reference,primitive_universe,node_l_plus,
  edge_l_plus,target_residual_upper_bound,coverage,norm_id,evidence_scope,
  domain_scope,disposition

TargetResidualBound:
  schema_version,primitive_universe_sha256,measure_id,value,coverage,
  evidence_scope,hard_eligible,disposition

GlobalMeasure:
  schema_version,measure_id,level,normalization_mode,node_ids,edge_ids,
  node_mass,edge_mass,rho1,rho2,cross_covariance_residual,
  numeric_residual

PredictiveDistance:
  schema_version,me0_result_reference,x_measure_sha256,y_measure_sha256,
  predictive_metric,x_cross_residual,y_cross_residual,x_numeric_residual,
  y_numeric_residual,discrepancy_upper_bound,evidence_tier,disposition

PositiveDistance:
  schema_version,x_measure_sha256,y_measure_sha256,l_plus_token_sha256,
  coverage_sha256,x_target_residual_sha256,y_target_residual_sha256,
  positive_representation_distance,safety_majorant,disposition

RadiusMorphism / WordDepthMorphism / GranularityMorphism:
  schema_version,axis,source_level,target_level,node_matrix,edge_matrix,
  edge_orientation,coverage,commutator_l1,target_residual_transport,
  cross_covariance_budget,numeric_residual_budget,remainder_e,norm_id,
  disposition

LocalTower:
  schema_version,ordered_levels,radius_morphism,word_depth_morphism,
  granularity_morphism,composition_order,disposition

PredictiveTransportCertificate:
  schema_version,channel,me0_result_reference_sha256,morphism_sha256,
  source_pair_sha256,target_pair_sha256,fine_upper,coarse_upper,
  remainder_e,inequality_holds,disposition

PositiveTransportCertificate:
  schema_version,channel,morphism_sha256,source_pair_sha256,
  target_pair_sha256,fine_upper,coarse_upper,remainder_e,
  inequality_holds,disposition

FiniteRemainderCertificate:
  schema_version,finite_level_count,ordered_level_ids,adjacent_remainders,
  suffix_majorants,composite_remainders,predictive_transport_certificates,
  positive_transport_certificates,predictive_projection_sha256,
  positive_projection_sha256,infinite_cutoff_claim,disposition

SimilarityCertificate:
  schema_version,hard_authority_reference,predictive_me0_result_reference,
  primitive_universe_sha256,l_plus_token,measures,local_tower,
  predictive_case_results,positive_case_results,
  finite_remainder_certificate,coverage,positive_core_sha256,
  predictive_core_sha256,runtime_manifest_sha256,disposition

DeclaredSyntheticSimilarityFixture:
  schema_version,hard_authority_reference,predictive_me0_result_reference,
  primitive_rows,coverage_witnesses,target_residuals,measures,local_tower,
  similarity_certificate
```

Live binding types are nonserializable and have no `to_dict`.  Unknown,
missing, duplicate raw keys, reordered arrays/rows, subclass, mutated, or
serializer-overridden objects fail closed.  Reordering object keys alone is
normalized to lexicographic canonical JSON and is not a semantic distinction.
SHA-1 commits are lowercase 40 hex; SHA-256 is uppercase 64 hex.  IDs are
nonempty ASCII of at most 128 bytes.

Predictive binary64 values are strings produced by `format(x,'.17g')` with
lowercase `e`, finite decode/re-encode identity, exact binary64 bit recovery,
and negative-zero rejection.  Raw float JSON, NaN, infinities, uppercase
exponent, locale spellings, and noncanonical alternate strings fail.
Hard/positive certificate arithmetic is reduced `ExactRational` only.

Exact scalar types are frozen as follows:

```text
node/edge masses, primitive loads, L-plus weights, target residuals:
  ExactRational
morphism node/edge matrices, commutator_l1,
target_residual_transport, remainder_e:
  ExactRational
morphism cross_covariance_budget, numeric_residual_budget:
  canonical binary64 string
PredictiveDistance metrics/residuals/upper:
  canonical binary64 string
PredictiveTransportCertificate fine_upper/coarse_upper:
  canonical binary64 string
PredictiveTransportCertificate remainder_e:
  ExactRational
PositiveDistance distance/majorant:
  ExactRational (majorant nullable only on typed abstention)
PositiveTransportCertificate fine_upper/coarse_upper/remainder_e:
  ExactRational
coverage counts:
  bounded nonnegative exact integers, never reduced rationals
```

`GlobalMeasure` is tier-neutral exact mass data and contains no ME0 object.
`compute_predictive_distance` receives the declared/live ME0 provenance
separately and records it only in `PredictiveDistance`.
`compute_positive_distance` has no ME0 parameter and rejects any attempted
nominal substitution.  The full similarity certificate carries the ME0
reference under the explicitly predictive-only field above; its positive
subcertificate is reverified solely from hard authority, L-plus, coverage, and
target residuals.

`positive_core_sha256` is SHA-256 of a strict canonical projection with exact
key set/order
`schema_version,hard_authority_reference,primitive_universe_sha256,
l_plus_token,structural_measure_sha256_rows,positive_case_results,
positive_transport_certificates,coverage,target_residuals,
positive_finite_remainder,runtime_manifest_sha256,disposition`.  It contains
no ME0 reference, predictive residual, predictive case, or predictive
transport.  Mutating ME0 while keeping the hard objects fixed must leave this
hash byte-identical.

`predictive_core_sha256` is the disjoint canonical projection with exact key
set/order
`schema_version,predictive_me0_result_reference,
structural_measure_sha256_rows,predictive_case_results,
predictive_transport_certificates,predictive_finite_remainder,
runtime_manifest_sha256,disposition`.
The full certificate verifier recomputes both projections.  I0 hard arithmetic
accepts only `positive_core_sha256`; the full certificate and predictive core
remain typed provenance/diagnostics.

Preflight occurs before copying, tuple construction, matrix materialization,
serialization, NumPy import, or quadratic work:

```text
wire depth                         16
wire nodes                      32768
wire bytes                    1048576
levels                              8
nodes                               32
edges                              128
primitive target rows               64
coverage IDs                       256
case rows                          128
global measures                     64
morphisms                            7
matrix cells / morphism          32768
matrix cells total              131072
input rational bits                 256
intermediate rational bits         4096
ID bytes                            128
```

`similarity.py` must contain no direct or top-level NumPy import.  Importing the existing `lean_rgc` package may load NumPy through immutable package initialization, and live verification of the frozen nominal ME0 result may use the existing NumPy-backed verifier.  Those two bounded facts are recorded by the v2 runtime manifest and do not permit NumPy in positive-distance, L-plus, morphism, or hard-certificate arithmetic.

## 6. Primitive universe, L-plus, coverage, and measures

The primitive universe canonical wire is exactly 2840 bytes with SHA-256
`9FA1D0431DF67EEDD0661EE70A0836A60ECF6153488EDE21699DD24867722FEC`:

```json
{"edge_ids":[["n0","n0"],["n0","n1"],["n1","n1"]],"edge_orientation":"unordered_canonical_pair_v1","node_ids":["n0","n1"],"rows":[{"edge_load":[{"denominator":"1","numerator":"1","schema_version":"lean-rgc-odlrq-exact-rational-v1"},{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"}],"node_load":[{"denominator":"1","numerator":"1","schema_version":"lean-rgc-odlrq-exact-rational-v1"},{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"}],"primitive_id":"u24_s0_t0_node0","schema_version":"odlrq.s0.primitive-target-row.v1","target_residual":{"denominator":"8","numerator":"1","schema_version":"lean-rgc-odlrq-exact-rational-v1"}},{"edge_load":[{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},{"denominator":"1","numerator":"1","schema_version":"lean-rgc-odlrq-exact-rational-v1"},{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"}],"node_load":[{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},{"denominator":"1","numerator":"2","schema_version":"lean-rgc-odlrq-exact-rational-v1"}],"primitive_id":"u24_s0_t1_node1_edge01","schema_version":"odlrq.s0.primitive-target-row.v1","target_residual":{"denominator":"8","numerator":"1","schema_version":"lean-rgc-odlrq-exact-rational-v1"}},{"edge_load":[{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},{"denominator":"1","numerator":"2","schema_version":"lean-rgc-odlrq-exact-rational-v1"}],"node_load":[{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"}],"primitive_id":"u24_s0_t2_edge11","schema_version":"odlrq.s0.primitive-target-row.v1","target_residual":{"denominator":"8","numerator":"1","schema_version":"lean-rgc-odlrq-exact-rational-v1"}},{"edge_load":[{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"}],"node_load":[{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"},{"denominator":"1","numerator":"0","schema_version":"lean-rgc-odlrq-exact-rational-v1"}],"primitive_id":"u24_s0_t3_ghost_return","schema_version":"odlrq.s0.primitive-target-row.v1","target_residual":{"denominator":"8","numerator":"1","schema_version":"lean-rgc-odlrq-exact-rational-v1"}}],"schema_version":"odlrq.s0.primitive-universe.v2"}
```

The ordered IDs are:

```text
u24_s0_t0_node0
u24_s0_t1_node1_edge01
u24_s0_t2_edge11
u24_s0_t3_ghost_return
```

Their canonical ID-array SHA-256 is
`EA763795807DA2F01FCA2B4288049D94486E4EEE2AD0135031FB05C16F1EABED`.
The first three IDs alone have SHA-256
`B232C06C00D7084691C1D7EADF3AF196655B71B41B3B8EE46139092FE85205A5`.

The independent checker enumerates all four rows and recomputes:

```text
node order         [n0,n1]
edge orientation   unordered_canonical_pair_v1
edge order         [(n0,n0),(n0,n1),(n1,n1)]
L_plus,node        [1,2]
L_plus,edge        [1,1,2]
e_target upper     1/8
```

The ghost-return row has zero direct node/edge load but remains required for
coverage and cannot be pruned as a no-op.

`CountedCoverageWitness` stores counts, not a reduced rational.  Complete
coverage is the ordered exact `4/4` set above; the `s-cover` fixture is exact
`3/4` and omits only `u24_s0_t3_ghost_return`.  Duplicate, reordered,
unknown, out-of-universe, count-mismatched, or digest-mismatched IDs fail.

`GlobalMeasure` has nonnegative exact node and edge masses.  It accepts only:

```text
UNIT_BOTH  rho1=sum node mass=1 and rho2=sum edge mass=1
ZERO_BOTH  rho1=rho2=0
```

Mixed zero/nonzero totals, arbitrary totals, implicit renormalization, and
zero/nonzero comparison fail closed.  A zero measure compares only to another
zero measure.

Predictive channel:

```text
d_pred(x,y) =
  (1/2) sum_i |m1_x(i)-m1_y(i)|
  + (1/2) sum_e |m2_x(e)-m2_y(e)|

U_pred =
  d_pred
  + r_cross,x + r_cross,y
  + r_numeric,x + r_numeric,y
```

`d_pred(x,x)=0`; `U_pred(x,x)` may be positive and is a separate field and
type.

Positive channel:

```text
d_plus =
  sum_i L_plus,node[i] |m1_x(i)-m1_y(i)|
  + sum_e L_plus,edge[e] |m2_x(e)-m2_y(e)|

SafetyMajorant =
  d_plus + e_target(x) + e_target(y)
```

The representation distance may be recomputed without complete coverage, but
`safety_majorant` is null and disposition is
`ABSTAIN_INCOMPLETE_COVERAGE` unless the exact L-plus token, complete `4/4`
coverage, and both hard target residuals are present.  Absence of sampled
violations, learned weights, a MaxEnt law, or a predictive residual can never
fill these requirements.

Fixed cases:

```text
s-id:
  x=y; node=[1,0]; edge=[1,0,0]; cross=numeric=0
  d_pred=0; U_pred=0; d_plus=0; Safety=1/4

s-node:
  x.node=[1,0]; y.node=[0,1]; both edge=[1,0,0]
  d_pred=1; d_plus=3; Safety=13/4

s-edge:
  both node=[1/2,1/2]
  x.edge=[1,0,0]; y.edge=[0,0,1]
  d_pred=1; d_plus=3; Safety=13/4

s-cross:
  masses equal s-id; x.cross=1/8; y.cross=0; numeric=0
  d_pred=0; U_pred=1/8; d_plus=0; Safety=1/4

s-cover:
  masses equal s-id; complete positive coverage replaced by exact 3/4
  d_pred=0; U_pred=0; d_plus=0; Safety=null; ABSTAIN

s-zero:
  x=y; node=edge=0; ZERO_BOTH
  d_pred=0; d_plus=0; Safety=1/4

s-zero-kill:
  x zero; y=s-id; comparison rejects

s-numeric:
  masses equal s-id; cross=0; x.numeric=1/16; y.numeric=0
  d_pred=0; U_pred=1/16; positive channel unchanged
```

Unless stated otherwise every case has complete `4/4` coverage, both hard
target residuals `1/8`, and zero cross/numeric residuals.

### 6.1 Frozen measure and case identity

Every non-compose case is located at `L3`.  The certificate's exact
`measures` array order is:

```text
u24_s0_s_id_m
u24_s0_s_node_x
u24_s0_s_node_y
u24_s0_s_edge_x
u24_s0_s_edge_y
u24_s0_s_cross_x
u24_s0_s_cross_y
u24_s0_s_cover_x
u24_s0_s_cover_y
u24_s0_s_zero_m
u24_s0_s_compose_l3_x
u24_s0_s_compose_l3_y
u24_s0_s_compose_l2_m
u24_s0_s_compose_l1_m
u24_s0_s_compose_l0_m
u24_s0_s_numeric_x
u24_s0_s_numeric_y
```

The non-compose rows have the masses/residuals displayed by their case above.
`s-id` reuses `u24_s0_s_id_m` for both sides; `s-zero` reuses
`u24_s0_s_zero_m`; `s-zero-kill` references those two existing rows rather
than creating copies.  The compose L3 rows are the displayed unequal fine
measures; each L2/L1/L0 `_m` row is the exact common image
`node=[1,0], edge=[1,0,0]` at that level and is referenced by both sides.
No two different IDs are treated as object identity merely because their
masses coincide.

The exact target-residual array follows the same 17-measure order and contains
`1/8` for every row.  Only the two `s_cover` rows use the exact `3/4`
coverage witness and set `hard_eligible=false`; both bounds are present but
cannot construct a majorant.  Every other row uses the complete `4/4`
witness and `hard_eligible=true`.  The fixture's coverage-witness array order
is `[complete_4_of_4,ghost_missing_3_of_4]`.

Predictive and positive case-result arrays both use:

```text
s-id,s-node,s-edge,s-cross,s-cover,s-zero,s-zero-kill,s-compose,s-numeric
```

Each row is strict schema `odlrq.s0.similarity-case-result.v1` with keys
`schema_version,case_id,x_measure_id,y_measure_id,coverage,
predictive_distance,positive_distance,expected_error`.  A channel not
constructed is null.  `s-cover` stores a positive ABSTAIN object with null
majorant; `s-zero-kill` stores both distances null and exact error
`ZERO_NONZERO_NORMALIZATION_MISMATCH`; all other `expected_error` values
are null.  References, result arrays, and residual arrays may not duplicate or
reorder rows.

## 7. R/N/G morphisms and finite similarity remainder

Every level fixes:

```text
frame_id  = u24.e2.declared_square.observation_frame.v1
domain_id = u24.s0.declared_finite_similarity_domain.v1
```

Only the R/N/G integers differ.  Levels are exact identifiers:

```text
L0=(R=1,N=1,G=1)
L1=(R=2,N=1,G=1)
L2=(R=2,N=2,G=1)
L3=(R=2,N=2,G=2)
```

All matrices act on column vectors, with rows indexed by coarse coordinates and
columns by fine coordinates:

```text
RadiusMorphism      L1 -> L0
WordDepthMorphism   L2 -> L1
GranularityMorphism L3 -> L2
```

Node and edge matrices are nonnegative exact rational and column-stochastic.
The fixed matrices are:

```text
P_R,node=I2   P_R,edge=I3
P_N,node=I2   P_N,edge=I3
P_G,node=[[1,1],[0,0]]
P_G,edge=[[1,1,1],[0,0,0],[0,0,0]]
```

Edge maps are never free input.  For canonical unordered source pair
`u<=v` and target pair `i<=j`, they are the symmetric-square induction:

```text
i=j:
  P_edge[(i,i),(u,v)] = P_node[i,u] P_node[i,v]

i<j:
  P_edge[(i,j),(u,v)] =
    P_node[i,u] P_node[j,v] + P_node[j,u] P_node[i,v]
```

The checker first evaluates every canonical unordered target pair.  A positive
coefficient outside the declared target edge alphabet is alphabet leakage and
rejects; declared columns must sum exactly to one.  A caller-supplied edge
matrix is rejected unless byte-equal to the rederived matrix.  This definition
makes `Sym^2(P_R P_N P_G)=Sym^2(P_R) Sym^2(P_N) Sym^2(P_G)`.

Composition is:

```text
P_(L3->L0) = P_R P_N P_G
application order = G,N,R
```

Reversed order, row/column transposition, axis substitution, missing level,
duplicate restriction, or intermediate alphabet leakage rejects.

Each adjacent morphism fixes:

```text
commutator_l1=0
target_residual_transport=0
cross_covariance_budget=0
numeric_residual_budget=0
remainder_e=1/4
coverage=4/4
norm_id=weighted_l1_exact_rational_v1
```

Predictive and positive transport certificates are distinct final types.  Each
recomputes `U_coarse(Px,Py) <= U_fine(x,y)+e`; neither can be substituted for
the other.

The `s-compose` fine level is:

```text
L3 x.node=[1,0]       y.node=[1/2,1/2]
L3 x.edge=[1,0,0]     y.edge=[1/2,1/2,0]
L3 d_pred=1
L3 d_plus=5/2
L3 SafetyMajorant=11/4
```

At L2 and below both measures are their exact displayed images and are equal;
the positive SafetyMajorant is `1/4`.  All adjacent and all composite
inequalities are enumerated.

From three exact adjacent remainders `1/4`, the finite certificate
independently derives:

```text
suffix majorants:
  B0=3/4, B1=1/2, B2=1/4, B3=0

six nonidentity composites:
  L1->L0 1/4
  L2->L1 1/4
  L3->L2 1/4
  L2->L0 1/2
  L3->L1 1/2
  L3->L0 3/4
```

For each channel, transport-certificate array order is exactly
`[L1->L0,L2->L1,L3->L2,L2->L0,L3->L1,L3->L0]`.  The predictive array is
followed by the positive array in the full finite certificate.  Identity
checks are recomputed but are not serialized as extra transport rows.

For every `i<j`,
`e_(j->i)=sum_(k=i)^(j-1)e_k=B_i-B_j` and both channel inequalities are
recomputed.  The wire must say `finite_level_count=4` and
`infinite_cutoff_claim=false`.  No infinite-cutoff, global Lean, or
horizon-uniform theorem follows.

S0 success disposition is
`CPU_SYNTHETIC_TYPED_SIMILARITY_CORE_VERIFIED`.

The granularity test also freezes a nondegenerate stochastic node map:

```text
P=[[1/2,1/3],[1/2,2/3]]
Sym2(P)=
  [[1/4,1/6,1/9],
   [1/2,1/2,4/9],
   [1/4,1/3,4/9]]
```

This detects the factor-of-two term for a diagonal source mapping to a
non-diagonal target.  Removing `(n0,n1)` from the target edge alphabet while
keeping this map must fail as alphabet leakage.  The finite-remainder test must
also reject: `coarse_upper>fine_upper+e`, any changed `1/2` or `3/4`
composite, any changed suffix majorant, and
`infinite_cutoff_claim=true`.

## 8. I0 typed hard/nominal integration

I0 adds exactly these package exports:

```text
PipelineEvidenceTier
PipelineDisposition
TypedPipelineFactor
NominalPipelineAddendum
TypedPipelineBound
construct_typed_pipeline_bound
verify_typed_pipeline_bound
```

The enums are closed and exact:

```text
PipelineEvidenceTier:
  EXACT
  EXACT_DECLARED_SYNTHETIC
  CERTIFIED_SYNTHETIC
  NOMINAL_DIAGNOSTIC_ONLY

PipelineDisposition:
  PASS
  FAIL_HARD_BOUND_EXCEEDED
  ABSTAIN_INCOMPLETE_COVERAGE
```

I0 schema literals are:

| object | schema |
|---|---|
| `TypedPipelineFactor` | `odlrq.i0.typed-pipeline-factor.v1` |
| `NominalPipelineAddendum` | `odlrq.i0.nominal-pipeline-addendum.v1` |
| pipeline coverage | `odlrq.i0.pipeline-coverage.v1` |
| propagated epsilon term | `odlrq.i0.propagated-epsilon-term.v1` |
| typed diagnostic total | `odlrq.i0.typed-diagnostic-total.v1` |
| candidate authority binding | `odlrq.i0.candidate-authority-binding.v1` |
| candidate authority manifest | `odlrq.i0.candidate-authority-manifest.v1` |
| authority sidecar identity | `odlrq.i0.authority-identity.v1` |
| pipeline verification report | `odlrq.i0.pipeline-verification-report.v1` |
| `TypedPipelineBound` | `odlrq.i0.typed-pipeline-bound.v1` |

The only public signatures are:

```text
construct_typed_pipeline_bound(*, candidate_authority_manifest,
  ordered_hard_factors, initial_residual, hard_threshold, nominal_addendum)
verify_typed_pipeline_bound(*, bound, expected_candidate_authority_manifest)
```

The constructor accepts no supplied hard, nominal, or total result.  It checks
the sealed manifest and input factors, computes every intermediate exact
rational, constructs the verification report, and returns the bound.  The
verifier independently recomputes the same data and returns the exact bound or
raises `StrictContractError`; boolean-only or digest-only verification is not a
live authority.

All public I0 classes are frozen dataclasses with strict `to_dict`/`from_dict`
round trips.  Unknown, missing, duplicate raw, or wrong-typed fields,
subclasses, booleans as integers, unreduced/nonpositive-denominator rationals,
noncanonical hashes, and serializer overrides reject before arithmetic.  All
`L`, epsilon, residual, threshold, bound, contribution, and diagnostic-total
values are production `ExactRational` wires; no binary64 value enters I0 bound
arithmetic.

The hard domains are fixed in order:

```text
u24.declared_finite_totalized_snapshot.v1
  -> u24.exact_quotient_coordinates.v1
  -> u24.positive_finite_fiber_envelope.v1
  -> u24.certified_finite_horizon_support_profile.v1
  -> u24.certified_finite_level_similarity_profile.v1
```

Every hard factor uses `weighted_l1_exact_rational_v1`.  ME0 is a nominal
sidecar from the E2 profile to
`u24.nominal_fixed_support_law.v1`; it is not a hard factor.

Pipeline coverage has exact field order
`schema_version,covered_count,universe_count,coverage_scope,complete`.
The PASS/FAIL factors and top-level bound use exact `4/4`, scope
`I0_HARD_DOMAIN_CHAIN`, and `complete=true`.  ABSTAIN changes only S0 to exact
`3/4`, scope `S0_DECLARED_SIMILARITY_DOMAIN`, and `complete=false`; the
top-level coverage is that same incomplete wire.  This private I0 wire is not
E2 candidate-universe coverage and is not artifact coverage.

The four ordered factors are exactly:

| stage | domain -> codomain | L | epsilon | factor tier | authority binding IDs |
|---|---|---:|---:|---|---|
| `E0` | totalized snapshot -> exact quotient coordinates | `1` | `0` | `EXACT` | `E0.pipeline_source_generator,E0.pipeline_target_generator` |
| `E1` | exact quotient coordinates -> positive finite-fiber envelope | `2` | `1/8` (`1/4` only in FAIL fixture) | `EXACT_DECLARED_SYNTHETIC` | `E1.accepted_qualification_envelope,E2.m0_parent_envelope` |
| `E2` | positive finite-fiber envelope -> certified finite-horizon support | `3/2` | `1/4` | `CERTIFIED_SYNTHETIC` | `E2.p1_cocycle,E2.p2_cocycle,E2.return_memory,E2.support_token` |
| `S0` | certified finite-horizon support -> certified finite-level similarity | `1` | `1/8` | `CERTIFIED_SYNTHETIC` | `S0.positive_core` |

The E0 manifest rows are declared-synthetic evidence, while the composed E0
arithmetic factor is `EXACT`; the verifier checks this one explicit mapping and
does not generally promote `EXACT_DECLARED_SYNTHETIC` to `EXACT`.

For hard stages `F_i`, I0 independently recomputes:

```text
H = (product_i L_i) e0
    + sum_i (product_(j>i) L_j) epsilon_i
```

Fixed PASS fixture:

```text
E0  L=1    epsilon=0    tier=EXACT
E1  L=2    epsilon=1/8  tier=EXACT_DECLARED_SYNTHETIC
E2  L=3/2  epsilon=1/4  tier=CERTIFIED_SYNTHETIC
S0  L=1    epsilon=1/8  tier=CERTIFIED_SYNTHETIC
e0=1/16
H=3/4
hard threshold=3/4
domain coverage=4/4
```

ME0 nominal addendum is separately `L=1, epsilon=1/10`, so
`N=1/10` and the diagnostic total is `H+N=17/20`.  It uses
`stage_id=ME0`, the exact E2-profile/nominal-law domains above,
`norm_id=weighted_l1_exact_rational_v1`, tier
`NOMINAL_DIAGNOSTIC_ONLY`, binding
`ME0.nontrivial_orbit_windows_result`, exact nominal coverage `2/3` with scope
`E2_CANDIDATE_UNIVERSE_SUPPORT`, and `hard_eligible=false`.  Its incomplete
candidate-universe coverage never controls the hard `4/4` gate.  The legacy artifact key
`total_bound` is a typed object with `tier=NOMINAL_DIAGNOSTIC_ONLY` and
`hard_eligible=false`; PASS never reads it.

FAIL changes only E1 epsilon to `1/4` and recomputes `H=15/16`, `N=1/10`,
and the diagnostic total `83/80`.
ABSTAIN changes only S0 domain coverage to counted `3/4` and emits null
hard, nominal, and total bounds.  Precedence is
`ABSTAIN > FAIL > PASS`.  PASS requires exact `4/4` coverage and
`H<=3/4`.

ME0 insertion into the hard chain, nominal `L!=1`, domain/codomain mismatch,
norm/tier/order substitution, reduced coverage fraction in place of counted
coverage, stale authority, or externally supplied arithmetic rejects.

Each candidate authority binding has exact field order:

```text
schema_version,binding_id,semantic_stage_id,producer_stage_id,binding_role,
object_schema,digest_domain,object_sha256,source_commit,source_tree,
evidence_tier,hard_eligible
```

Closed `binding_role` values are `PIPELINE_OBJECT`, `LINEAGE_ANCHOR`,
`HARD_AUTHORITY`, `NOMINAL_DIAGNOSTIC`, `HARD_CORE`, `PREDICTIVE_CORE`, and
`FULL_CONTAINER`.  Closed `digest_domain` values are
`CANONICAL_CONTRACT_BYTES_SHA256`,
`WINDOWS_RUNTIME_CANONICAL_WIRE_SHA256`, and
`CANONICAL_PROJECTION_BYTES_SHA256`.  Source SHA-1 values are lowercase; object
SHA-256 values are uppercase.  Semantic stage names what the object means;
producer stage names the accepted commit whose public constructor supplied the
bound bytes.

The ordered twelve entries are exactly:

| binding id | semantic / producer | role | object schema | digest domain | object SHA-256 | source commit / tree | tier | hard eligible |
|---|---|---|---|---|---|---|---|---|
| `E0.pipeline_source_generator` | `E0 / E2` | `PIPELINE_OBJECT` | `odlrq_exact_quotient_coordinate_generator_v1` | `CANONICAL_CONTRACT_BYTES_SHA256` | `5C920F94FA38B6F116526D0BC00340882DE5C1288A8BAE0857F54EB727A3D262` | accepted E2 / accepted E2 | `EXACT_DECLARED_SYNTHETIC` | `true` |
| `E0.pipeline_target_generator` | `E0 / E2` | `PIPELINE_OBJECT` | `odlrq_exact_quotient_coordinate_generator_v1` | `CANONICAL_CONTRACT_BYTES_SHA256` | `7281601FA840B29AC3F97AB4E2D5953163706E9C2CEEC8EE3855A8FB9807161C` | accepted E2 / accepted E2 | `EXACT_DECLARED_SYNTHETIC` | `true` |
| `E1.accepted_qualification_envelope` | `E1 / E1` | `LINEAGE_ANCHOR` | `odlrq_fiber_envelope_v1` | `CANONICAL_CONTRACT_BYTES_SHA256` | `D959B07CEF0A79A9478FAB99D3329D39DFF215A183FCD564B2547DBBE7EBD0C6` | accepted E1 / accepted E1 | `EXACT_DECLARED_SYNTHETIC` | `true` |
| `E2.m0_parent_envelope` | `E1 / E2` | `HARD_AUTHORITY` | `odlrq_fiber_envelope_v1` | `CANONICAL_CONTRACT_BYTES_SHA256` | `9BA692E8A14C5C56BCDE6D565082300A9D0BB7A888DE5533F31DC1896E9B157C` | accepted E2 / accepted E2 | `EXACT_DECLARED_SYNTHETIC` | `true` |
| `E2.p1_cocycle` | `E2 / E2` | `HARD_AUTHORITY` | `odlrq.e2.cocycle-certificate.v1` | `CANONICAL_CONTRACT_BYTES_SHA256` | `6C87E7EE21B8BC0D78D024AB14C2D5F247D541531A90D6291732D284C7FFEF11` | accepted E2 / accepted E2 | `CERTIFIED_SYNTHETIC` | `true` |
| `E2.p2_cocycle` | `E2 / E2` | `HARD_AUTHORITY` | `odlrq.e2.cocycle-certificate.v1` | `CANONICAL_CONTRACT_BYTES_SHA256` | `BEE7B16BC7FF8AF926CDF8F5502F21B2708A9C4C280F57AC846889B2C50A065D` | accepted E2 / accepted E2 | `CERTIFIED_SYNTHETIC` | `true` |
| `E2.return_memory` | `E2 / E2` | `HARD_AUTHORITY` | `odlrq.e2.finite-return-memory.v1` | `CANONICAL_CONTRACT_BYTES_SHA256` | `95C2BEDA13B1085E46183038F857B753AE0DC531685BC3996EB1E5F5AFAD4A46` | accepted E2 / accepted E2 | `CERTIFIED_SYNTHETIC` | `true` |
| `E2.support_token` | `E2 / E2` | `HARD_AUTHORITY` | `odlrq.e2.certified-support-token.v1` | `CANONICAL_CONTRACT_BYTES_SHA256` | `D01170427E717D543D941740881C937EF5B535E357D67EEFDBF62773AFD6E660` | accepted E2 / accepted E2 | `CERTIFIED_SYNTHETIC` | `true` |
| `ME0.nontrivial_orbit_windows_result` | `ME0 / ME0` | `NOMINAL_DIAGNOSTIC` | `odlrq.me0.maxent-result.v1` | `WINDOWS_RUNTIME_CANONICAL_WIRE_SHA256` | `DCA363A6C8CC15ED13C4182DE7BFD2F68293E83C1766419B439C1AE8309C42E3` | accepted ME0 / accepted ME0 | `NOMINAL_DIAGNOSTIC_ONLY` | `false` |
| `S0.positive_core` | `S0 / S0` | `HARD_CORE` | `odlrq.s0.positive-core-projection.v1` | `CANONICAL_PROJECTION_BYTES_SHA256` | activation `positive_core_sha256` | accepted S0 / accepted S0 | `CERTIFIED_SYNTHETIC` | `true` |
| `S0.predictive_core` | `S0 / S0` | `PREDICTIVE_CORE` | `odlrq.s0.predictive-core-projection.v1` | `CANONICAL_PROJECTION_BYTES_SHA256` | activation `predictive_core_sha256` | accepted S0 / accepted S0 | `NOMINAL_DIAGNOSTIC_ONLY` | `false` |
| `S0.full_similarity_certificate` | `S0 / S0` | `FULL_CONTAINER` | `odlrq.s0.similarity-certificate.v1` | `CANONICAL_CONTRACT_BYTES_SHA256` | activation full-certificate SHA-256 | accepted S0 / accepted S0 | `NOMINAL_DIAGNOSTIC_ONLY` | `false` |

Here `accepted E1` expands to commit/tree
`6fb35aa229fc60e2220cbb68c1e7fff2ce64f199 /
b3fc7f21b6420e718eb954be0c1b5affca65d263`; `accepted E2` expands to
`7a8b28872439dd61d40174c2500c5990790002be /
d54ed9fab52da4929843fabdeb3c1e1920994f6a`; and `accepted ME0` expands to
`28749bf2f0fc67bc55a24e9e07fc03ad6c66b98d /
a3b3513ca93430c9f15e5bd90888e81b0af1ff9c`.  The three S0 cells are filled
only from the byte-verified activation sidecar.

An authority identity has exact field order
`schema_version,authority_commit_sha,authority_parent_sha,
authority_document_path,authority_document_blob_sha,authority_ci_run_id,
authority_ci_job_id`.  The candidate manifest has exact field order:

```text
schema_version,ordered_bindings,full_runtime_manifest_sha256,
s0_runtime_manifest_sha256,s0_authority_identity,i0_activation_identity
```

It contains all twelve entries, the full integrated runtime digest
`F20A2C1A6556EAAC5371C7438A5F588A3F7E5A76282E2F500614B2E43FF6C05A`,
the S0 runtime digest
`88FE6E69BB6B0E7BFE2C1C6EB220F420ECA0BE25826D48A90BD318641F3E89C9`,
and all six fields for both sidecar identities.  A valid object digest with a
stale, reordered, missing, duplicated, or spliced row/sidecar rejects.

The E1 hard factor binds, in order,
`E1.accepted_qualification_envelope,E2.m0_parent_envelope`; the integrated
envelope artifact uses only `E2.m0_parent_envelope`, while the accepted-E1
object remains an immutable lineage anchor.  The E0 factor binds the two E0
generator rows; E2 binds P1, P2, return memory, and support token; S0 binds
only `S0.positive_core`.  Hard arithmetic never accepts the full or predictive
certificate hash.  E2's candidate-universe `coverage=2/3` is a different
schema/type from S0/I0 domain coverage `4/4`.

I0 reconstructs the accepted E2 public fixture once, requires exact token size
2185 and SHA
`D01170427E717D543D941740881C937EF5B535E357D67EEFDBF62773AFD6E660`,
then calls the public live binder.  It reconstructs S0 only through
`build_declared_synthetic_similarity_fixture` and requires byte equality with
the activation sidecar.  Test helper/private imports are forbidden.

I0 success disposition is
`CPU_SYNTHETIC_U2_U4_CANDIDATE_CONSTRUCTED`.

## 9. I0 strict object and artifact contracts

Serializable I0 field order is:

```text
TypedPipelineFactor:
  schema_version,stage_id,domain_id,codomain_id,norm_id,L,epsilon,
  evidence_tier,authority_bindings,coverage,hard_eligible

NominalPipelineAddendum:
  schema_version,stage_id,domain_id,codomain_id,norm_id,L,epsilon,
  evidence_tier,authority_bindings,coverage,hard_eligible

pipeline coverage:
  schema_version,covered_count,universe_count,coverage_scope,complete

propagated epsilon term:
  schema_version,stage_id,downstream_L,epsilon,contribution

typed diagnostic total:
  schema_version,value,evidence_tier,hard_eligible

candidate authority binding:
  schema_version,binding_id,semantic_stage_id,producer_stage_id,binding_role,
  object_schema,digest_domain,object_sha256,source_commit,source_tree,
  evidence_tier,hard_eligible

candidate authority manifest:
  schema_version,ordered_bindings,full_runtime_manifest_sha256,
  s0_runtime_manifest_sha256,s0_authority_identity,i0_activation_identity

authority sidecar identity:
  schema_version,authority_commit_sha,authority_parent_sha,
  authority_document_path,authority_document_blob_sha,authority_ci_run_id,
  authority_ci_job_id

pipeline verification report:
  schema_version,hard_factor_count,hard_factor_order_sha256,initial_term,
  propagated_epsilon_terms,recomputed_hard_bound,
  recomputed_nominal_addendum,recomputed_total_bound,coverage_complete,
  tier_firewall_verified,domain_chain_verified,norm_chain_verified,
  authority_manifest_verified,disposition_verified,
  verification_disposition

TypedPipelineBound:
  schema_version,candidate_authority_manifest,ordered_hard_factors,
  initial_residual,hard_bound,hard_threshold,nominal_addendum,total_bound,
  coverage,disposition,verification_report
```

Nested value types are exact and nonoverloaded:

| location | wire type |
|---|---|
| factor/addendum `L`, `epsilon` | `ExactRational` |
| factor/addendum/bound `coverage` | `odlrq.i0.pipeline-coverage.v1` |
| bound `initial_residual`, `hard_threshold` | nonnull `ExactRational` |
| bound `hard_bound` | `ExactRational` or null only on ABSTAIN |
| bound `nominal_addendum` | full `NominalPipelineAddendum` or null only on ABSTAIN |
| bound `total_bound` | full `odlrq.i0.typed-diagnostic-total.v1` or null only on ABSTAIN |
| report `initial_term` | `ExactRational`, or null on ABSTAIN |
| report `propagated_epsilon_terms` | ordered propagated-term wires, or empty on ABSTAIN |
| report `recomputed_hard_bound` | `ExactRational`, or null on ABSTAIN |
| report `recomputed_nominal_addendum` | the recomputed scalar `N` as `ExactRational`, not a duplicate addendum; null on ABSTAIN |
| report `recomputed_total_bound` | typed diagnostic-total wire, or null on ABSTAIN |
| all `*_count` values | bounded canonical nonnegative JSON integers |
| tiers/dispositions/IDs/hashes | the closed canonical strings fixed here |

`authority_bindings` is an ordered array of exact `binding_id` strings resolved
against the nested manifest; embedded replacement wires are forbidden.  PASS
and FAIL reports contain every exact intermediate.  On ABSTAIN,
`initial_term`, `propagated_epsilon_terms`, `recomputed_hard_bound`,
`recomputed_nominal_addendum`, and `recomputed_total_bound` are respectively
null, empty, null, null, and null; `coverage_complete=false` and the other five
verification booleans remain true.  PASS has hard/nominal/total
`3/4,1/10,17/20`; FAIL has `15/16,1/10,83/80`.  The typed total always has
`evidence_tier=NOMINAL_DIAGNOSTIC_ONLY` and `hard_eligible=false`.  ABSTAIN's
top-level `hard_bound`, `nominal_addendum`, and `total_bound` are all null.
Every successfully checked PASS, FAIL, or ABSTAIN report uses exact
`verification_disposition=CPU_SYNTHETIC_TYPED_PIPELINE_BOUND_VERIFIED`; that
string means the typed disposition was recomputed, not that the candidate
passed its hard threshold.

`hard_factor_order_sha256` hashes
`canonical_contract_bytes([factor.to_dict() for factor in ordered_hard_factors])`.
For PASS, `initial_term=3/16` and the E0/E1/E2/S0 propagated contributions are
`0,3/16,1/4,1/8`; for FAIL they are `0,3/8,1/4,1/8`.  Each term records the
recomputed downstream products `3,3/2,1,1` respectively.  No caller supplies
these report rows.

The fixed artifact order is:

```text
envelope_core.json
maxent_fixture.json
local_tower.json
global_measure.json
level_transport.json
similarity_certificate.json
integrated_certificate.json
```

Schemas respectively are:

```text
u24_envelope_core_v1
u24_maxent_fixture_v1
u24_local_tower_v1
u24_global_measure_v1
u24_level_transport_v1
u24_similarity_certificate_v1
u24_integrated_certificate_v1
```

All wrappers use these exact common identifiers:

```text
evidence_scope          synthetic_development
observation_frame_id    u24.e2.declared_square.observation_frame.v1
reachable_domain_id     u24.s0.declared_finite_similarity_domain.v1
response_vocabulary_id  u24.e2.declared_square.response_vocabulary.v1
transition_semantics_id u24.e2.declared_square.transition_semantics.v1
domain_scope            declared_finite_totalized_snapshot_only
```

Artifact coverage is a distinct wire with schema `u24_artifact_coverage_v1`
and exact order
`schema_version,covered_count,universe_count,coverage_scope,complete`.
It is never confused with E2 candidate acceptance or the S0
`CountedCoverageWitness`.  `censors` is the exact empty array for every row.
The closed artifact `operator_tier` vocabulary is
`EXACT_DECLARED_SYNTHETIC`, `NOMINAL_DIAGNOSTIC_ONLY`,
`CERTIFIED_SYNTHETIC`, `TYPED_MIXED_CONTAINER_NOT_HARD_ELIGIBLE`,
`TYPED_HARD_WITH_PREDICTIVE_SIDECAR`, and
`TYPED_HARD_WITH_NOMINAL_DIAGNOSTIC`.

The seven artifact semantics are frozen by this table.  `S0RT` abbreviates the
exact S0 runtime SHA `88FE6E69BB6B0E7BFE2C1C6EB220F420ECA0BE25826D48A90BD318641F3E89C9`;
`FULLRT` abbreviates the integrated runtime SHA
`F20A2C1A6556EAAC5371C7438A5F588A3F7E5A76282E2F500614B2E43FF6C05A`.

| artifact | operator tier | operator-projection schema | digest domain | runtime | coverage scope/count | disposition | wrapper hard eligible |
|---|---|---|---|---|---|---|---|
| `envelope_core.json` | `EXACT_DECLARED_SYNTHETIC` | `u24_envelope_core_operator_projection_v1` | canonical-contract bytes | `S0RT` | `E2_M0_SOURCE_BLOCKS`, `4/4`, complete | `CPU_SYNTHETIC_FIBER_ENVELOPE_CORE_VERIFIED` | yes |
| `maxent_fixture.json` | `NOMINAL_DIAGNOSTIC_ONLY` | `u24_maxent_fixture_operator_projection_v1` | frozen Windows-runtime canonical projection bytes | `FULLRT` | `E2_CANDIDATE_UNIVERSE_SUPPORT`, `2/3`, incomplete | `CPU_SYNTHETIC_MAXENT_CORE_VERIFIED` | no |
| `local_tower.json` | `CERTIFIED_SYNTHETIC` | `u24_local_tower_positive_operator_projection_v1` | canonical-contract bytes | `S0RT` | `S0_DECLARED_SIMILARITY_DOMAIN`, `4/4`, complete | `FINITE_LEVEL_MORPHISM_VERIFIED` | yes |
| `global_measure.json` | `TYPED_MIXED_CONTAINER_NOT_HARD_ELIGIBLE` | `u24_global_measure_operator_projection_v1` | canonical-contract bytes | `FULLRT` | `S0_DECLARED_SIMILARITY_DOMAIN`, `4/4`, complete | `CPU_SYNTHETIC_GLOBAL_MEASURE_CONTAINER_VERIFIED` | no |
| `level_transport.json` | `CERTIFIED_SYNTHETIC` | `u24_level_transport_positive_operator_projection_v1` | canonical-contract bytes | `S0RT` | `S0_DECLARED_SIMILARITY_DOMAIN`, `4/4`, complete | `FINITE_LEVEL_MORPHISM_VERIFIED` | yes |
| `similarity_certificate.json` | `TYPED_HARD_WITH_PREDICTIVE_SIDECAR` | `u24_similarity_certificate_operator_projection_v1` | canonical-contract bytes | `FULLRT` | `S0_DECLARED_SIMILARITY_DOMAIN`, `4/4`, complete | `CPU_SYNTHETIC_TYPED_SIMILARITY_CORE_VERIFIED` | no; only its separately bound positive core is hard eligible |
| `integrated_certificate.json` | `TYPED_HARD_WITH_NOMINAL_DIAGNOSTIC` | `u24_integrated_certificate_operator_projection_v1` | canonical-contract bytes | `FULLRT` | `I0_HARD_DOMAIN_CHAIN`, `4/4`, complete | `CPU_SYNTHETIC_U2_U4_CANDIDATE_CONSTRUCTED` | no; its hard sub-bound remains typed separately |

For each artifact, the operator projection is a new strict object whose first
key/value is the exact projection schema in the table and whose remaining keys
and values are exactly the artifact's payload keys below except
`verification_report`, in the same order.  `operator_sha256` is SHA-256 of that
projection's `canonical_contract_bytes`; for the MaxEnt projection the source
values must first match the frozen Windows result.  Thus the projection is
reconstructible from the payload but is not falsely claimed to be the complete
production object's `to_dict`.  It never contains the wrapper or its own hash.
The strict payload `verification_report` separately records and live-verifies
the complete predecessor object SHA(s), including E2 M0 `9BA...`, ME0 `DCA...`,
the S0 positive/predictive/full hashes, and the PASS `TypedPipelineBound` SHA as
applicable.  The artifact verifier chooses the projection schema/digest domain
solely from the exact artifact schema/tier row; a caller-supplied selector is
forbidden.  The level-transport projection contains only the three structural
morphisms and their composition, never the predictive half of a full
`FiniteRemainderCertificate`.

Every artifact common-field order is:

```text
schema_version,evidence_scope,source_commit,observation_frame_id,
reachable_domain_id,response_vocabulary_id,transition_semantics_id,
domain_scope,runtime_identity_sha256,operator_tier,operator_sha256,
coverage,censors,disposition,payload
```

Payload key order is:

```text
envelope_core:
  generator,source_weights,target_weights,fiber_law,transfer_layer,
  completeness_witness,inclusion_witness,envelope,verification_report

maxent_fixture:
  support_token,reference_law,orbit_law,statistics,target,kl_radius,status,
  probabilities,residuals,verification_report

local_tower:
  levels,restrictions,cauchy_majorant,verification_report

global_measure:
  measures,predictive_metric,predictive_upper_bound,
  positive_representation_distance,safety_majorant,verification_report

level_transport:
  radius_morphism,word_depth_morphism,granularity_morphism,composition,
  verification_report

similarity_certificate:
  coverage,target_residuals,l_plus_token,remainder_certificate,
  verification_report

integrated_certificate:
  candidate_manifest,stages,initial_residual,hard_bound,nominal_addendum,
  total_bound,coverage,disposition,verification_report
```

Payload values are not future free-form dictionaries.  Their exact production
mapping is:

| payload | exact value mapping |
|---|---|
| envelope `generator` | `u24_envelope_generator_pair_v1` with `schema_version,source_generator,target_generator`, using the two exact generator wires in manifest order |
| envelope weights/law/layer/completeness/envelope fields | the corresponding strict public E2 M0 fixture wires, with completeness ordered source then target; no digest-only substitute |
| envelope `inclusion_witness` | typed absence `u24_inclusion_witness_absence_v1`, ordered `schema_version,comparison_performed,reason,sole_envelope_sha256`, with exact values `false,SINGLE_ENVELOPE_NO_MONOTONE_EXTENSION_CLAIM,9BA692E8A14C5C56BCDE6D565082300A9D0BB7A888DE5533F31DC1896E9B157C`; it is not a fabricated `FiberInclusionWitness` |
| MaxEnt `support_token` | exact live-rebound E2 `CertifiedSupportToken` wire |
| MaxEnt `reference_law` | `u24_maxent_reference_law_v1` with `schema_version,support_candidate_ids,reference_mass_rows`, projected from the frozen problem |
| MaxEnt `orbit_law` | exact `MaxEntResult.orbit_reference` wire |
| MaxEnt `statistics` | `u24_maxent_statistics_v1` with `schema_version,statistic_rows`, from the frozen problem |
| MaxEnt target/radius/status/probabilities | the exact corresponding frozen problem/result fields, preserving array order and canonical float strings |
| MaxEnt `residuals` | `u24_maxent_residuals_v1` with `schema_version,simplex_residual,moment_residual_inf,dual_residual_inf,operator_span_residual,kl_divergence,kl_within_radius` |
| local `levels` | exact `LocalTower.ordered_levels` production wires |
| local `restrictions` | `u24_local_restrictions_v1` with `schema_version,radius_morphism,word_depth_morphism,granularity_morphism`; each value is the positive morphism projection defined below |
| local `cauchy_majorant` | `u24_cauchy_majorant_v1` with `schema_version,adjacent_remainders,suffix_majorants,composite_remainders,infinite_cutoff_claim`, projected from the verified finite remainder |
| global `measures` | exact ordered production `GlobalMeasure` wires |
| global predictive metric/upper | `u24_predictive_metric_projection_v1` with `schema_version,case_results,transport_certificates,finite_remainder_projection`, and `u24_predictive_upper_rows_v1` with `schema_version,rows`; rows preserve the frozen case order |
| global positive distance/majorant | `u24_positive_metric_projection_v1` with `schema_version,case_results,transport_certificates,finite_remainder_projection`, and `u24_safety_majorant_rows_v1` with `schema_version,rows`; no ME0 field is permitted |
| level radius/word-depth/granularity | the three positive morphism projections defined below, rederived from the exact production morphisms |
| level `composition` | `u24_level_composition_v1` with `schema_version,composition_order,composite_node_matrix,composite_edge_matrix,positive_composite_remainders` |
| similarity coverage/residuals/L-plus/remainder | the exact corresponding production S0 certificate wires/arrays; `remainder_certificate` is the full typed finite remainder, so this wrapper remains mixed/non-hard |
| integrated fields | the corresponding fields of the PASS `TypedPipelineBound`; `stages` is `ordered_hard_factors`, and the report below binds the complete bound including its omitted-from-legacy-payload `hard_threshold` |

Every named projection schema has exactly the displayed key order and no other
field.  Envelope completeness is specifically
`u24_completeness_witness_pair_v1` with
`schema_version,source_witness,target_witness`.  The predictive/positive finite
remainder projections are respectively
`u24_predictive_finite_remainder_projection_v1` and
`u24_positive_finite_remainder_projection_v1`, each ordered
`schema_version,adjacent_remainders,suffix_majorants,composite_remainders,
transport_certificate_sha256s,infinite_cutoff_claim`.  Predictive upper rows
use `u24_predictive_upper_row_v1` ordered
`schema_version,case_id,distance,upper_bound`; positive rows use
`u24_safety_majorant_row_v1` ordered
`schema_version,case_id,representation_distance,safety_majorant,disposition`.
Every local/level morphism value uses
`u24_positive_morphism_projection_v1` ordered
`schema_version,axis,source_level,target_level,node_matrix,edge_matrix,
edge_orientation,coverage,commutator_l1,target_residual_transport,remainder_e,
norm_id,disposition`.  It deliberately excludes `cross_covariance_budget` and
`numeric_residual_budget`; the full production morphism remains live-verified
and hash-bound in the artifact report, but those predictive fields cannot enter
a hard-eligible operator projection.
Consequently the local-tower payload and operator projection contain no full
`LocalTower` or full morphism wire: they contain exact level IDs, positive
restriction projections, and exact finite majorants only.  The full
`LocalTower` SHA in the report is provenance for live rederivation and is never
accepted as a hard arithmetic operand.
Projection `rows` retain the frozen case order.  The
artifact verifier reconstructs every mapping from the already live-verified E2,
ME0, S0, or I0 object and requires byte equality with the payload value.

Every payload `verification_report` uses its artifact schema stem plus
`_verification_report_v1` (for example
`u24_envelope_core_verification_report_v1`) and exact field order:

```text
schema_version,operator_projection_sha256,ordered_predecessor_bindings,
runtime_identity_sha256,coverage_verified,tier_firewall_verified,
live_verification_disposition
```

Each predecessor row has schema `u24_artifact_predecessor_binding_v1` and exact
order
`schema_version,binding_id,object_schema,object_sha256,digest_domain,
live_verified`.  `live_verified` must be true after strict parse, reserialize,
rehash, and public verifier execution; a digest-only row rejects.  Ordered
binding IDs are: envelope `[E2.m0_parent_envelope]`; MaxEnt
`[E2.support_token,ME0.nontrivial_orbit_windows_result]`; local tower
`[S0.local_tower,S0.full_similarity_certificate]`; global measure
`[ME0.nontrivial_orbit_windows_result,S0.positive_core,S0.predictive_core,
S0.full_similarity_certificate]`; level transport
`[S0.local_tower,S0.positive_core,S0.full_similarity_certificate]`;
similarity `[S0.positive_core,S0.predictive_core,
S0.full_similarity_certificate]`; integrated
`[I0.candidate_authority_manifest,I0.typed_pipeline_bound]`.
Artifact-local `S0.local_tower`, `I0.candidate_authority_manifest`, and
`I0.typed_pipeline_bound` rows use their exact canonical object SHA-256 values
computed before wrapper construction, with schemas/digest domains exactly:

```text
S0.local_tower                 odlrq.s0.local-tower.v1
                               CANONICAL_CONTRACT_BYTES_SHA256
I0.candidate_authority_manifest odlrq.i0.candidate-authority-manifest.v1
                               CANONICAL_CONTRACT_BYTES_SHA256
I0.typed_pipeline_bound        odlrq.i0.typed-pipeline-bound.v1
                               CANONICAL_CONTRACT_BYTES_SHA256
```

All other rows reuse the schema and digest domain of their exact section-8
manifest binding.  `live_verification_disposition` is the single exact string
`STRICT_ARTIFACT_PREDECESSORS_LIVE_VERIFIED`.  Report runtime and projection hashes
must equal their wrapper values.  `coverage_verified` and
`tier_firewall_verified` are true for every emitted artifact, including the
explicitly incomplete but nominal-only MaxEnt support.

Artifact bytes use a dedicated exact-insertion-order encoder:
UTF-8, no BOM or trailing LF, `ensure_ascii=False`, `allow_nan=False`,
separators `(',',':')`, and `sort_keys=False`.  Parsing is duplicate- and
order-aware; reordered fields reject.  Semantic object digests continue to use
sorted-key `canonical_contract_bytes`.  These two byte domains must not be
confused.

Limits:

```text
1 MiB each artifact
7 MiB aggregate
JSON depth 16
array length 256
keys/object 64
nodes 8192
string 4096 UTF-8 bytes
rational input/intermediate bits 256/4096
```

Each artifact's one-MiB cap is checked on raw bytes before UTF-8 decode or JSON
parse; the seven-MiB aggregate is checked before any filesystem write.  JSON
root depth is zero.  Descending through an object value or array element adds
one; object key names do not add depth.  Node count includes the root
object/array, every nested object/array, every object key string, and every
scalar value including null and booleans.  The 4096-byte string cap applies to
both keys and string values before semantic conversion; IDs retain the tighter
128-byte rule.  Every object is checked for the 64-key cap before dataclass or
rational construction, and duplicate/order validation uses raw pair lists.
Arrays are checked before copying.  JSON integer tokens must be canonical
signed-64 values; booleans are not integers.

For a reduced rational, input size is
`max(abs(numerator).bit_length(),denominator.bit_length())`, with zero having
bit length zero and the denominator strictly positive.  Every input is checked
against 256 bits before arithmetic.  Every multiplication, addition,
normalization result, propagated term, hard/nominal/total result, and serialized
output is checked against 4096 bits immediately after it is formed; a later
cancellation cannot rescue an over-cap intermediate.

All seven byte arrays are constructed and strictly verified in memory before
the same-volume staging transaction in section 4.  The official root must not
exist; exclusive staging/file creation, no symlink/reparse traversal, exact
seven-file set, reread verification, atomic rename, and no overwrite are
required.
`source_commit` is the already accepted I0 semantic commit, never the
artifact sidecar or a self-reference.  The closeout claim is limited to strict
local verification plus immutable Git blobs; its known-red sidecar CI is not
called artifact validation.

## 10. Frozen test nodes

S0 exact ordered nodes:

```text
tests/test_odlrq_similarity.py::test_s0_authority_references_distinguish_live_and_digest_bindings_and_firewall_me0
tests/test_odlrq_similarity.py::test_s0_global_measure_rows_recompute_normalization_and_zero_mass_rules
tests/test_odlrq_similarity.py::test_s0_predictive_distance_separates_node_edge_cross_and_numeric_terms
tests/test_odlrq_similarity.py::test_s0_declared_lplus_enumerates_complete_primitive_universe_and_builds_exact_positive_majorant
tests/test_odlrq_similarity.py::test_s0_counted_coverage_and_target_residuals_abstain_without_four_of_four
tests/test_odlrq_similarity.py::test_s0_radius_morphism_is_typed_fine_to_coarse_column_stochastic
tests/test_odlrq_similarity.py::test_s0_word_depth_morphism_is_typed_fine_to_coarse_column_stochastic
tests/test_odlrq_similarity.py::test_s0_granularity_morphism_derives_edge_map_and_composes_in_frozen_order
tests/test_odlrq_similarity.py::test_s0_finite_remainder_recomputes_all_six_composites_without_infinite_claim
tests/test_odlrq_similarity.py::test_s0_strict_wire_caps_type_substitution_and_mutation_fail_closed
```

Their UTF-8 LF-joined list without trailing newline is 1075 bytes with
SHA-256
`9B7468C31DABEFA073ACDBF723693CEE75B71230538B3EE7B2C5032340DB777F`.

I0 exact ordered extension nodes:

```text
tests/test_uprime_u2_u4_development.py::test_u24_i0_authority_bindings_and_unique_terminal_paths_are_exact
tests/test_uprime_u2_u4_development.py::test_u24_i0_typed_pipeline_pass_recomputes_hard_and_nominal_channels
tests/test_uprime_u2_u4_development.py::test_u24_i0_fail_and_abstain_precedence_are_exact
tests/test_uprime_u2_u4_development.py::test_u24_i0_nominal_maxent_cannot_enter_or_scale_the_hard_channel
tests/test_uprime_u2_u4_development.py::test_u24_i0_domains_norms_tiers_coverage_and_order_fail_closed
tests/test_uprime_u2_u4_development.py::test_u24_i0_live_e2_token_rebinds_and_candidate_manifest_rejects_splicing
tests/test_uprime_u2_u4_development.py::test_u24_i0_seven_artifact_schemas_orders_roundtrip_and_mutations_fail_closed
tests/test_uprime_u2_u4_development.py::test_u24_i0_temporary_emission_is_exclusive_capped_and_source_commit_bound
tests/test_uprime_u2_u4_development.py::test_u24_i0_public_surface_has_no_selector_protected_endpoint_or_safety_promotion
```

Their UTF-8 LF-joined list without trailing newline has SHA-256
`96B64CFFB67EDB061ED68DFCEFADDC5E84B5190CB6E488878BC7CB1E6D96973C`.
All 19 nodes are zero-argument, undecorated, contain no test imports, and may
not be replaced by skip/xfail/deselection.

## 11. Frozen closeout artifact paths

The only closeout files are:

```text
docs/experiments/uprime_odlrq_post_e2_upper_stack_closeout_2026-07-17.md
docs/experiments/artifacts/uprime_odlrq_post_e2_upper_stack_20260717/envelope_core.json
docs/experiments/artifacts/uprime_odlrq_post_e2_upper_stack_20260717/maxent_fixture.json
docs/experiments/artifacts/uprime_odlrq_post_e2_upper_stack_20260717/local_tower.json
docs/experiments/artifacts/uprime_odlrq_post_e2_upper_stack_20260717/global_measure.json
docs/experiments/artifacts/uprime_odlrq_post_e2_upper_stack_20260717/level_transport.json
docs/experiments/artifacts/uprime_odlrq_post_e2_upper_stack_20260717/similarity_certificate.json
docs/experiments/artifacts/uprime_odlrq_post_e2_upper_stack_20260717/integrated_certificate.json
```

The mutually exclusive failure closeout has only the section 3.5 document path
and no artifact path.  No absent artifact is synthesized.  If S0 or I0 cannot
publish after bounded rational repairs, that uniquely named failure sidecar
records the last accepted semantic commit and makes no success artifact.

## 12. Anti-fractal repair rule, deferred phases, and nonclaims

Deterministic engineering tests may be rerun during development.  A failed
published candidate stays immutable; a repaired direct-child replacement uses
the next registered ref.  At most three candidate refs are published per
stage.  Exhausting them triggers a concise rational-remedy review with Fable,
not automatic user escalation.  User direction is requested only if the
upper-stack program is theoretically refuted or no rational repair remains.

The following are repairable without changing the theory: code defects,
serializer bugs, wrong matrix orientation, stale hashes, CI count mistakes,
Windows process/RSS supervision, manifest wiring, sidecar topology, and
ordinary resource overruns.  Fixes remain inside the active allowlist and
frozen semantics; any endpoint/fixture/tier/cap change requires a fresh
pre-source authority.

This authority does not license the synthetic locality learner, native Lean
oracle, protected K-series, official transport, parallelization,
continuousization, gradientization, GPU, or LLM.  After successful I0 closeout
the order remains:

```text
synthetic U'1.5-L0 locality CEGAR
  -> fresh public-synthetic official transport
  -> filled Amendment A and protected work if separately authorized
  -> native Lean-oracle U'1.5-L1
  -> orbit/interface/separator parallelization
  -> finite-quotient Poisson continuousization
  -> nominal-only gradientization
  -> optional GPU learned representation
  -> optional LLM distillation last
```

The locality learner retains ghost actions, uses before-only locality and
mvar-sharing separator/cycle-rank/treewidth features, lets exact
counterexamples split only, and treats no-counterexample/merge claims as
statistical.  Its objective is conditional-covariance reduction per query
cost with frozen coverage, abstention, baseline, seed, and tie-break.  It cannot
construct an exact partition, complete fiber witness, positive envelope, or
safety token.

Untracked `llm_local.json`, `pilot_tasks.json`, and related local smoke files
remain outside this clean worktree and outside every authority/candidate byte.
They are not read or imported.  Their later quarantine is a separate
user-owned-worktree housekeeping action, not a reason to delay S0/I0.

No result here claims production Lean locality, protected solve-rate
improvement, complete all-germ enumeration, infinite-cutoff stability, MaxEnt
safety, learned hard weights, remote/GPU performance, or LLM benefit.

## 13. Pre-freeze adversarial review disposition

The 2026-07-10 47-agent theory verdict remains unchanged: theory freeze was
rejected as originally written, while the surviving core was not refuted and
the fatal defects were implementation, governance, and endpoint design.

For this implementation authority, independent read-only agents attacked:

- S0 hard/nominal authority separation and full predecessor binding;
- counted coverage, ghost retention, zero-mass and residual semantics;
- unordered-edge induction, column stochasticity, composition, and leakage;
- finite remainder versus forbidden infinite-limit promotion;
- I0 hard/nominal arithmetic and candidate-manifest splicing;
- artifact ordering, bounded emission, and source-commit identity; and
- branch topology, first-parent budget, manifest registration, and exact CI
  counts.

The authority-binding review found and repaired a draft identity ambiguity:
the accepted-E1 qualification envelope `D959B07CEF0A79A9478FAB99D3329D39DFF215A183FCD564B2547DBBE7EBD0C6` and E2's
M0 pipeline parent envelope `9BA692E8A14C5C56BCDE6D565082300A9D0BB7A888DE5533F31DC1896E9B157C` are distinct and are
now separately named and bound.  The selected ME0 result is explicitly the
nontrivial-orbit Windows artifact rather than a portable LAPACK identity.

The unordered-edge review found and repaired a second draft ambiguity: the old
product formula was insufficient for an unordered edge basis.  Section 7 now
freezes the symmetric-square formula; the proposed fixed edge matrix itself
was correct.  The topology review independently confirmed the five primary CI
shapes, the two mutually exclusive bounded-failure variants, and the exact
four-path S0/I0 semantic allowlists.  No theoretical
stop condition was found.

**Disposition: APPROVE this exact document for authority freeze; after its
registered sidecar CI shape is verified, proceed autonomously with S0.**
