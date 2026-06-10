from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import sqlite3
import time

from ...schemas import stable_hash


def _now() -> float:
    return float(time.time())


def _json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, default=str)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                obj = {"_parse_error": True, "raw_line": line}
            rows.append(obj if isinstance(obj, dict) else {"value": obj})
    return rows


def _float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _int_bool(value: Any) -> int:
    return 1 if bool(value) else 0


def _row_hash(*parts: Any) -> str:
    return stable_hash(parts, 40)


def import_poms_artifacts(conn: sqlite3.Connection, run_dir: Path, run_id: str, artifacts: list[sqlite3.Row]) -> None:
    for artifact in artifacts:
        path = Path(str(artifact["abs_path"] or artifact["rel_path"] or ""))
        if path.suffix != ".jsonl":
            continue
        rows = _read_jsonl(path)
        atype = str(artifact["artifact_type"] or "")
        for row in rows:
            if atype == "poms_evidence" or any(k in row for k in ("parent_nonpaid", "dual_certificate", "least_repair")):
                evidence_id = str(row.get("evidence_id") or row.get("id") or stable_hash(row, 16))
                rh = _row_hash(run_id, artifact["artifact_id"], "poms_evidence", evidence_id, row)
                conn.execute(
                    """
                    INSERT OR IGNORE INTO poms_evidence(
                        row_hash, run_id, artifact_id, evidence_id, candidate_id, action_id,
                        parent_nonpaid, dual_certificate, least_repair, payload_json
                    ) VALUES (?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        rh,
                        run_id,
                        artifact["artifact_id"],
                        evidence_id,
                        str(row.get("candidate_id") or ""),
                        str(row.get("action_id") or ""),
                        _int_bool(row.get("parent_nonpaid")),
                        _int_bool(row.get("dual_certificate")),
                        _int_bool(row.get("least_repair")),
                        _json(row),
                    ),
                )
            if atype == "poms_promotion_decisions" or "promotion_status" in row:
                decision_id = str(row.get("decision_id") or row.get("id") or "poms_decision_" + stable_hash(row, 16))
                conn.execute(
                    """
                    INSERT OR REPLACE INTO poms_promotion_decisions(
                        decision_id, ts, run_id, candidate_id, action_id, parent_nonpaid,
                        dual_certificate, least_repair, promotion_status, canonical_status, reason, row_json
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        decision_id,
                        _float(row.get("ts"), _now()),
                        run_id,
                        str(row.get("candidate_id") or ""),
                        str(row.get("action_id") or ""),
                        _int_bool(row.get("parent_nonpaid")),
                        _int_bool(row.get("dual_certificate")),
                        _int_bool(row.get("least_repair")),
                        str(row.get("promotion_status") or row.get("status") or ""),
                        str(row.get("canonical_status") or ""),
                        str(row.get("reason") or ""),
                        _json(row),
                    ),
                )


__all__ = ["import_poms_artifacts"]
