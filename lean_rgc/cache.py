from __future__ import annotations

from pathlib import Path
from typing import Any
import json

from .schemas import AuditRecord, LeanTask, ProofState, TacticAction, stable_hash


def audit_record_from_dict(d: dict[str, Any]) -> AuditRecord:
    after = d.get("after_state")
    if isinstance(after, dict):
        d = dict(d)
        d["after_state"] = ProofState.from_dict(after)
    return AuditRecord(**d)


class AuditCache:
    """Content-addressed cache for Lean micro-audit results.

    Key includes task/action/env-affecting fields, not measured runtime. Cache is
    intentionally file based so it works in Colab and distributed workers.
    """

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def key(self, task: LeanTask, action: TacticAction, state: ProofState | None = None, lean_cmd: str = "", workdir_hash: str = "", version: str = "v1") -> str:
        return stable_hash(
            {
                "version": version,
                "task": task.to_dict(),
                "state": state.to_dict() if state is not None else None,
                "action": action.to_dict(),
                "lean_cmd": lean_cmd,
                "workdir_hash": workdir_hash,
            },
            n=32,
        )

    def path_for_key(self, key: str) -> Path:
        return self.root / key[:2] / f"{key}.json"

    def get(self, key: str) -> AuditRecord | None:
        p = self.path_for_key(key)
        if not p.exists():
            return None
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            rec = audit_record_from_dict(data)
            rec.audit_flags["cached"] = True
            return rec
        except Exception:
            return None

    def put(self, key: str, rec: AuditRecord) -> None:
        p = self.path_for_key(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(rec.to_dict(), ensure_ascii=False, sort_keys=True), encoding="utf-8")

    def set(self, key: str, rec: AuditRecord) -> None:
        self.put(key, rec)
