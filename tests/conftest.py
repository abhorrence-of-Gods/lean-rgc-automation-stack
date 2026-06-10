import json
import sys
from functools import lru_cache
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = Path(__file__).resolve().parent
MANIFEST_PATH = TESTS_DIR / "tier_manifest.json"
VALID_TIERS = {"unit", "integration", "golden", "e2e", "legacy", "slow"}

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@lru_cache(maxsize=1)
def load_tier_manifest() -> dict[str, list[str]]:
    raw = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return {str(name): list(tiers) for name, tiers in raw.items()}


def tiers_for_test_file(path: Path) -> list[str]:
    try:
        rel = path.resolve().relative_to(TESTS_DIR).as_posix()
    except ValueError:
        return []
    return load_tier_manifest().get(rel, [])


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config, items):
    for item in items:
        item_path = Path(str(item.fspath))
        for tier in tiers_for_test_file(item_path):
            item.add_marker(getattr(pytest.mark, tier))
