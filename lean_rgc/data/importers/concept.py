from __future__ import annotations

from typing import Any


def import_concept_artifacts(store: Any, artifacts: list[Any]) -> None:
    store.import_supplemental_repair_artifacts(artifacts)


__all__ = ["import_concept_artifacts"]
