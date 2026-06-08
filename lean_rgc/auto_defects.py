from __future__ import annotations

from pathlib import Path
from typing import Any

from .defect_registry import DefectRegistry
from .defect_miner import AutoDefectMiner
from .schemas import ProofState


class AutoDefectExtractor:
    def __init__(self, registry: DefectRegistry | str | Path | dict[str, Any]):
        if isinstance(registry, DefectRegistry):
            self.registry = registry
        elif isinstance(registry, dict):
            self.registry = DefectRegistry.from_dict(registry)
        else:
            self.registry = DefectRegistry.load(registry)
        self.miner = AutoDefectMiner(self.registry)

    def extract_atoms(self, state: ProofState, *, extra: str = "") -> dict[str, float]:
        row = {"state_id": state.state_id, "task_id": state.task_id, "target": state.target, "goals_text": state.goals_text, "messages": state.raw_messages}
        if extra:
            row["stderr"] = extra
        sig = self.miner.signals_for_row(row)
        active = {a.atom_id for a in self.registry.atoms if a.status == "active"}
        return {k: float(v) for k, v in sig.items() if k in active}

    def extract_text(self, text: str, target: str = "") -> dict[str, float]:
        row = {"state_id": "text", "task_id": "text", "target": target or text, "goals_text": text, "messages": []}
        sig = self.miner.signals_for_row(row)
        active = {a.atom_id for a in self.registry.atoms if a.status == "active"}
        return {k: float(v) for k, v in sig.items() if k in active}
