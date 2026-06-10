# Testing Tiers

The default test target is the production CI contract:

```bash
python -m pytest -q
```

Test tiers are assigned in `tests/tier_manifest.json` and applied during pytest
collection by `tests/conftest.py`. Every `tests/test_*.py` file must be listed
in the manifest.

Useful targets:

```bash
python -m pytest -m "unit or integration or golden" -q
python -m pytest -m e2e -q
python -m pytest -m "legacy or slow" -q
```

Tier meanings:

- `unit`: fast pure-function or small-fixture checks.
- `integration`: CLI, DB, pipeline, or multi-module behavior.
- `golden`: artifact shape, schema, and report contracts.
- `e2e`: Lean worker, subprocess, native worker, or kernel-state paths.
- `legacy`: historical version tests kept out of default CI.
- `slow`: expensive checks reserved for nightly or manual runs.
