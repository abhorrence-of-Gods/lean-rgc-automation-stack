# U'1 evidence milestone 2a: default-deny canonical rerun gate

Status at this bootstrap revision: FORWARD-ONLY; NO CANONICAL RERUN IS
LICENSED.

## Purpose

The third canonical diagnostic was result-aware, and repair milestone 1 now
changes the worker and cache behavior. A new commit would otherwise obtain a
fresh canonical filename merely by changing the anchor. Local reservation
prevents overwrite at one anchor but does not prevent premature repeated runs
across anchors.

This milestone makes every current repository-owned artifact boundary deny by
default:

- the formal U'1 CLI rejects before reservation creation;
- the programmatic diagnostic runner rejects before it verifies or uses a
  caller-supplied reservation and before it starts Lean;
- the reservation helper rejects before creating its parent directory or
  reservation file; and
- the hard-link publication helper rejects before reservation verification or
  artifact creation.

The tracked registry is strict canonical JSON with `default_allow=false` and
an empty license map. A nonempty map also remains rejected because the
activation verifier is deliberately absent. These repeated assertions are
side-effect-free defense in depth for the bootstrap. They MUST NOT later be
changed into repeated remote claims.

## Frozen forward activation topology

Activation must preserve this commit topology:

```text
G(default-deny bootstrap) -> ... -> C(clear candidate) -> L(license-only commit)
```

`L` has candidate `C` as its single direct parent. The `C..L` diff changes only
the registry and adds exactly one map key without changing or deleting any
prior key. That key is the lowercase full 40-character `C` commit. It binds
the candidate tree and input manifest, the fixed fixture profile, candidate
CI evidence, and the activation fields below.

There is exactly one global attempt identifier for a candidate:

```text
license_id = lowercase_hex_sha256(
  utf8("lean-rgc-uprime-u1-attempt-v1") || NUL || ascii(lowercase(C))
)
```

It is not configurable by CLI, environment, registry author, or sibling
license commit. The authenticated remote is fixed to the repository
`https://github.com/abhorrence-of-Gods/lean-rgc-automation-stack.git`, remote
name `origin`, branch `refs/heads/codex/uprime-odlrq-plan`, and claim namespace
`refs/tags/uprime-u1-attempts/<license_id>`. Any sibling `L` for the same `C`
therefore contends for the same remote ref.

## Claim-once receipt protocol

The activation implementation replaces the bootstrap's repeated assertions
with distinct phases:

1. `claim_once` verifies the exact `C -> L` topology, registry entry, candidate
   tree/input manifest, remote branch head, and frozen CI/fixture evidence.
2. Before any local reservation, it performs a non-force, server-side
   create-if-absent push of the one deterministic remote claim ref to `L`.
   Any pre-existing ref is consumed and causes rejection even if it already
   points to `L`.
3. A successful claim returns one opaque receipt binding `C`, `L`, the license
   id/ref, registry blob, candidate manifest, and observed remote object id.
4. The same receipt is verified, without another remote mutation, by
   reservation, live runner, ledger closure, report construction, and
   hard-link publication. Its public canonical digest is recorded in all
   those artifacts.

Thus a crash or `HARNESS_ERROR` consumes the one attempt across machines. A
post-`L` result commit is not licensed because it is neither `L` nor the
registered direct-child topology. Receipt verification must be strict and
must never fall back to path existence or a self-asserted JSON field.

## Activation MUST-CLOSE checks

No positive path may be merged until all of the following are implemented and
adversarially reviewed:

- the claim-once receipt API and receipt binding at every artifact boundary;
- exact `HEAD:<registry>` blob/OID loading, eliminating the clean-check/read
  race;
- a disposable clean worktree, isolated interpreter invocation, and runtime
  module-path/digest provenance for the executed package and transitive
  imports;
- authenticated remote URL and remote branch-head verification rather than a
  possibly stale local tracking ref;
- create-if-absent remote-claim integration tests, including concurrent
  claimers, crash consumption, sibling `L` commits, fake remotes, and tag
  reuse/deletion cases;
- the exact required workflow `.github/workflows/ci.yml`, job `pytest`, event
  `push`, immutable workflow digest, action commit SHAs, runner-image
  provenance, and frozen retry policy: candidate evidence has `head_sha=C` and
  license evidence has `head_sha=L`, both on the fixed branch;
- a dedicated hard-coded fixture profile at `C` and `L` with zero failures,
  errors, skips, or xfails, plus successful candidate and license-commit CI;
- strict reservation/ledger/report schemas whose independent verifier rejects
  missing, forged, stale, or mismatched receipts;
- positive and negative temporary-Git tests for the complete topology; and
- an evidenced ruleset for the fixed branch and claim-tag namespace, including
  its policy identity and explicit treatment of owner/admin bypass, recorded
  in the receipt and checked by the verifier.

Until those checks are committed and reviewed, every canonical run remains
denied.

## Scope and limitations

This is repository governance, not a hostile-local-process security boundary.
It does not stop an owner from modifying Python in memory, calling operating
system primitives directly, checking out pre-bootstrap history, substituting
a malicious interpreter, force-pushing, or deleting a remote tag. The future
independent artifact verifier and protected external repository policy are
therefore part of the trust boundary; a canonical-looking path alone confers
no authority.

At this revision the two executed package initializer files are included in
the anchor set, but that is not a substitute for the clean-worktree and full
runtime-provenance requirement above.

No scientific contract, repair fixture, full-frame ledger, GPU task, or prior
artifact is changed or licensed here.
