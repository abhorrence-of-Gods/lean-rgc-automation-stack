# U'1 live RPC diagnostic amendment 1

Status: FROZEN BEFORE SECOND LIVE EXECUTION.

This amendment repairs only the side-effect fixture target selector in
`uprime_odlrq_u1_rpc_diagnostic_preregistration.md`. The first anchored run at
`eb38b4b9c0cb2711c88bb9bea8f2e5646d851925` remains permanently recorded as
`HARNESS_ERROR`; its raw/public hashes and reservation are not changed.

## Triggering evidence

Frame 14 (`side_init`) of the first artifact successfully returned exactly two
open metavariable IDs after prefix `refine ⟨?_, ?_⟩`. The harness then required
exactly one serialized goal row to carry `relation == "="`. That presentation
marker did not yield a singleton, so the harness raised before applying `rfl`.

The failure concerns target identification only. It does not amend any budget,
action, task, replay, delta, verdict, timeout, artifact-governance, or gate rule.

## Frozen selector repair

Lean's constructor/refine order for the registered existential term is the
tuple order:

1. witness goal for `n : Nat`;
2. proof goal for `n = 0`.

The repaired harness must:

- require the raw serialized `goals` array to contain exactly two distinct rows,
  each with a nonempty string `mvar_id`;
- select `goals[1].mvar_id` (zero-based index 1) as the equality target;
- record selector source `refine_tuple_position_1` and the selected ID;
- make no decision from the optional `relation` presentation marker.

Any cardinality other than two remains `HARNESS_ERROR`. All downstream D0/D1/D2
checks still decide whether the selected target and side-effect sweep behave as
registered; positional selection itself cannot make those contracts pass.

## Temporal rule

This amendment, its pure regression, and the harness change must be committed
and pushed together. CI must pass before the second canonical Windows CPU run.
The second run uses its new 12-character anchor in the already frozen canonical
path template and may not overwrite or reuse the first run or reservation.
