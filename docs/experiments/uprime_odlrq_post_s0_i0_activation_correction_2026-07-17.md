# U-prime / ODLRQ post-S0 I0 activation correction

Date: 2026-07-17

Status: `MECHANICAL_CONTROL_AND_SCHEMA_CLARIFICATION_FROZEN`

This document is a narrow, document-only correction made before I0 source
work.  It is a direct child of activation commit
`2e6d0b64a88877dd1f1bd87718186c3ac040c2a4`, is published only on
`codex/uprime-post-s0-i0-activation-correction`, is never merged into the
accepted semantic line, and changes no equation, fixture value, hard/nominal
tier, threshold, operator projection, payload order, test node, resource cap,
or scientific endpoint.

## 1. Observed activation CI and its classification

The immutable activation commit is
`2e6d0b64a88877dd1f1bd87718186c3ac040c2a4`, with parent accepted S0
`2376aca8209c38a3a94dfa872334073d86dc4909`.  Its natural CI was run/job
`29561412405 / 87824486788` and ended with exactly:

```text
10 failed, 2619 passed, 8 skipped, 161 deselected
```

One failure is the already registered topology-control failure caused solely
by the document-only activation path.  The other nine failures are the nine S0
tests that reach the shared `_me0_objects()` helper.  On that Linux runner the
nominal floating-point MaxEnt re-solve produced wire SHA-256
`97B5DDA5500D4194949E9D3AE10D2EF9D4139AA809BBBF373677F6295D90D749`
instead of the frozen Windows-runtime wire SHA-256
`DCA363A6C8CC15ED13C4182DE7BFD2F68293E83C1766419B439C1AE8309C42E3`.
Every one of those nine failures has that same root assertion; no S0 positive
operator, exact rational, coverage, morphism, transport, or remainder check
failed independently.

This is a control-plane reproduction of the already declared nominal/runtime
boundary, not a new scientific S0 result.  The byte-identical S0 candidate and
accepted publications of the same commit had already passed distinct green CI runs
`29559986829 / 87820184028` and `29560359820 / 87821300305`, each with exactly
`2629 passed, 8 skipped, 161 deselected`.  The activation payload was also
independently reconstructed on the frozen Windows runtime and checked for
exact byte counts, SHA-256 values, projection separation, and canonical parse
and reserialization before publication.

Accordingly, section 3.3 of the governing authority is corrected only for this
already observed immutable activation: run/job
`29561412405 / 87824486788` and the exact ten-failure signature above satisfy
the activation control gate.  No rerun is requested or accepted.  I0 must
consume the frozen 4,177-byte Windows MaxEnt wire by strict parse,
reserialization, hash, and public verification; it must not re-solve that
nominal result and hope for cross-LAPACK byte identity.

## 2. Source commit/tree identity clarification

Section 1.3 of the governing authority preserves all seven inherited artifact
common-field orders, while section 4 accidentally said that both
`source_commit` and `source_tree` occur on every wrapper.  The exact section-9
wrapper order contains `source_commit` only.  The following sentence is the
controlling correction:

> The Python builder, verifier, and emitter validate both lowercase SHA-1
> arguments on every call.  Each serialized artifact wrapper contains
> `source_commit` only, in the unchanged exact common-field order of section 9.
> The parent preflight proves `source_tree = tree(source_commit)`, so the commit
> transitively binds the tree.  The compact emission receipt contains both
> `source_commit` and `source_tree`.  No artifact schema, common-field order,
> digest domain, or payload order changes.

## 3. Mechanical serialization clarifications

The compact emission receipt uses schema
`u24_artifact_emission_receipt_v1` and exact key order
`schema_version,source_commit,source_tree,ordered_artifacts,disposition`.
Each ordered artifact row is exactly the three-element JSON array
`[name,bytes,sha256]`.  Its disposition is
`CPU_SYNTHETIC_U2_U4_ARTIFACTS_EMITTED`.

The six mechanically resolved activation constants are exactly:

```text
I0_ACTIVATION_COMMIT_SHA
I0_ACTIVATION_PARENT_SHA
I0_ACTIVATION_DOCUMENT_PATH
I0_ACTIVATION_DOCUMENT_BLOB_SHA
I0_ACTIVATION_CI_RUN_ID
I0_ACTIVATION_CI_JOB_ID
```

The governing phrase “all public I0 classes are frozen dataclasses” means all
public I0 value-object classes other than the two closed enums
`PipelineEvidenceTier` and `PipelineDisposition`.  A materialized `dict`
cannot retain duplicate raw JSON keys: ordinary object `from_dict` methods
therefore require exact insertion-ordered keys and exact types, while raw
artifact parsing performs duplicate and order rejection on pair lists before
materialization.

## 4. Historical red-badge clarification requested for future readers

As of 2026-07-17, the earlier result commit's CI badge is red because the guard
omitted shallow-history handling; that cause has an explicit audit
classification.  Candidate CI `29166073728` was green.  The red result badge
must not be read as a scientific failure of the registered experiment.

## 5. License boundary

This correction licenses the already frozen four-path I0 semantic
implementation against the clarified contract.  It does not authorize a
protected endpoint, GPU, SSH, LLM, native-Lean execution, external capture
wrapper repair, production claim, or infinite-cutoff claim.  Any ordinary
implementation or CI defect remains repairable under the existing bounded
candidate policy; only a theoretical refutation or exhaustion of rational
repairs is an escalation condition.
