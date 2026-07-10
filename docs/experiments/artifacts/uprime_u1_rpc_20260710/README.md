# U'1 RPC diagnostic artifacts (2026-07-10)

This directory contains publication-safe derivatives of the anchored Windows
CPU native-RPC diagnostics. The investigator-local raw artifacts and durable
reservation sidecars remain under the gitignored `runs/uprime_u1_rpc_20260710/`
directory. `PUBLICATION_MANIFEST.json` binds their SHA-256 values.

The `eb38b4b9c0cb` artifact is intentionally retained as `HARNESS_ERROR`; it is
not a substrate verdict and must never be replaced by a repaired rerun.
