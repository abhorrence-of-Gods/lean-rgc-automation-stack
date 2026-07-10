# U'1 evidence milestone 2b phase 2b1 Windows stat-binding correction

Date: 2026-07-11

Status: PREREGISTERED PORTABILITY CORRECTION; READ-ONLY SYNTHETIC SCOPE ONLY;
NO CLAIM, WRITE, REMOTE, RUN, NETWORK, LEAN, LATER-STAGE, OR GPU AUTHORITY.

## 1. Trigger and disposition

The committed Phase-2b1 amendment required the no-follow path snapshot `S0`
and descriptor snapshots `F0/F1/F2` to compare through a binding that dropped
only the path-only reparse bit. The first uncommitted Windows implementation
probe showed that this equality is not satisfiable on the registered local
platform: `os.stat(path, follow_symlinks=False).st_ctime_ns` and
`os.fstat(fd).st_ctime_ns` differ for the same open file while device, inode,
mode, size, and modification time agree.

The implementation must not silently weaken a preregistered identity check.
This correction freezes the cross-family comparison before a Phase-2b1 source
or result commit. It changes no event, receipt, path, grammar, authority, or
network rule.

## 2. Reproduced local observation

On Windows 11 build 26200 and CPython 3.13.7, a read-only probe of the tracked
file `lean_rgc/evals/uprime_rpc_bundle_reservation.py` produced:

```text
path stat: dev=12826398884339490889
           ino=22517998136885155
           mode=33206
           ctime_ns=1783713675782670800
           size=22710
           mtime_ns=1783714100185198300

fd stat:   dev=12826398884339490889
           ino=22517998136885155
           mode=33206
           ctime_ns=1783714100185198300
           size=22710
           mtime_ns=1783714100185198300
```

The mismatch is not evidence of replacement: both observations bind the same
Windows file identity and content extent. The already-green Phase-2a verifier
also uses `(dev, ino, size, mtime_ns)` for its post-open path binding rather
than equating cross-family ctime.

## 3. Exact superseding metadata relations

This section supersedes only the Phase-2b1 amendment Section-8 phrase
`bind(S0)=bind(F0)=bind(F1)=bind(F2)` and its statement that `bind` drops only
the reparse bit.

The complete path snapshot remains:

```text
S = (st_dev, st_ino, st_mode, reparse_bit,
     st_ctime_ns, st_size, st_mtime_ns)
```

The complete descriptor snapshot remains:

```text
F = (st_dev, st_ino, st_mode, st_ctime_ns, st_size, st_mtime_ns)
```

The exact rules are now:

1. first-scan and post-close path observations require exact `S0 == S1`;
2. descriptor observations require exact `F0 == F1 == F2`;
3. both path observations must independently be regular and non-reparse;
4. all descriptor observations must independently satisfy `stat.S_ISREG`;
5. the only cross-family projection is
   `B(X)=(st_dev, st_ino, st_size, st_mtime_ns)`; and
6. require `B(S0) == B(F0)` before retaining bytes and, redundantly,
   `B(S1) == B(F2)` after the two passes and post-close path stat.

`st_mode`, `st_ctime_ns`, and the path-only reparse bit are not compared across
the path/descriptor API boundary. They remain fully compared within their own
families, so a path metadata change or descriptor metadata change still
rejects. Device/inode bind object identity; size and modification time bind the
observed extent. Equal cross-family bindings do not authenticate origin and do
not claim immunity to an adversary able to preserve all four values and both
pass digests.

Directory `D0/D1`, two directory scans, exact `S0/S1`, two descriptor passes,
event hashes, and the final observation point are unchanged.

## 4. Two small private-surface closures

The preregistered private helper has the exact return:

```python
_classify_chain_suffix(
    event_index: int, terminal_event: bool
) -> tuple[str, int | None]
```

It returns `("valid_terminal", None)` for a terminal event,
`("valid_nonterminal_index_exhausted", None)` for nonterminal index 9999, and
otherwise `("valid_nonterminal", event_index + 1)`.

The exact `__all__` name sequence from the parent amendment is represented as
a Python list, matching the existing evaluation modules. This container choice
has no authority consequence.

## 5. Corrected acceptance cases

Before a Phase-2b1 result commit, the support matrix additionally proves:

1. a real Windows file with unequal cross-family ctime but equal `B` passes;
2. changing each of `dev`, `ino`, `size`, or `mtime_ns` in either side of `B`
   rejects before parsing;
3. changing path ctime/mode between `S0` and `S1` rejects;
4. changing descriptor ctime/mode between any `F0/F1/F2` rejects;
5. a nonregular descriptor or path, or a path reparse bit, rejects;
6. the exact three `_classify_chain_suffix` outputs above; and
7. `__all__` is the exact ordered list of ten registered names.

The frozen Windows/four-file/full-suite and Ubuntu CI gates remain unchanged.
Test-only fixture corrections may align a failure code with its independently
computed golden digest and mutate an existing frozen dataclass field rather
than relying on CPython's behavior for assignment to a nonexistent slotted
field; neither changes the registered protocol.

## 6. Stop rule

Commit and push of this correction license only conformance edits to the
uncommitted Phase-2b1 read-only source and support matrix. It grants no writer,
claim, remote, CAS, recovery oracle, artifact observation, inventory coverage,
execution, rerun, network, Lean, publication, Phase-2b2 implementation, or GPU
authority. The rerun registry and exposure state remain byte-identical.
