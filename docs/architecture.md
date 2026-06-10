# Architecture

Lean-RGC is now organized around a production spine rather than a single
research dispatcher. The durable runtime path is:

```text
Lean audit
  -> response completion
  -> DOST face ledger
  -> CRG problem and optimizer
  -> hardening and replay audit
  -> POMS promotion
  -> diagnosis and reports
```

## Runtime Boundaries

- `lean_rgc.core` is the metadata contract. It owns stable ids, JSONL helpers,
  and production record dataclasses.
- `lean_rgc.data` owns the SQLite run DB, artifact metadata, importers, lineage
  materialization, and invariant checks.
- `lean_rgc.cli` owns argparse wiring. Domain logic should not depend on CLI
  modules.
- `lean_rgc.dost` owns the split DOST runtime pieces that were extracted from
  the older monolithic automation module.
- `lean_rgc.lean` is the target package for Lean runtime boundaries. Some older
  Lean adapters still live at top level and remain compatibility candidates.

## Compatibility Policy

The top-level `lean_rgc.cli_*.py` files are one-line shims that re-export the
package CLI modules. They remain in place for this freeze. New code should import
from `lean_rgc.cli.*`.

The older `lean_rgc.schemas` module remains a facade for historical dataclasses
and JSONL helpers. Production metadata contract additions should go through
`lean_rgc.core`.

