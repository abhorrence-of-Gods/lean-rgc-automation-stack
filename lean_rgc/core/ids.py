from __future__ import annotations

from typing import Any
import hashlib
import json


def stable_hash(obj: Any, n: int = 16) -> str:
    data = json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
    return hashlib.sha256(data).hexdigest()[:n]


def stable_entity_id(prefix: str, payload: Any, n: int = 24) -> str:
    return f"{prefix}_{stable_hash(payload, n)}"


__all__ = ["stable_entity_id", "stable_hash"]
