# U'1 RPC diagnostic artifacts (2026-07-10)

This directory contains publication-safe derivatives of the anchored Windows
CPU native-RPC diagnostics. The investigator-local raw artifacts and durable
reservation sidecars remain under the gitignored `runs/uprime_u1_rpc_20260710/`
directory. Each `PUBLICATION_MANIFEST*.json` binds the SHA-256 values for its
named execution.

The `eb38b4b9c0cb` artifact is intentionally retained as `HARNESS_ERROR`; it is
not a substrate verdict and must never be replaced by a repaired rerun.

The amended `fc6b69ea14fb` run completed all 23 registered responses but is
also retained as `HARNESS_ERROR`: the worker acknowledged shutdown, then did
not finish process teardown inside the original ten-second grace period.
