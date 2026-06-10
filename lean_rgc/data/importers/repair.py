from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import sqlite3

from ...schemas import stable_hash


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


def _row_hash(*parts: Any) -> str:
    return stable_hash(parts, 40)


class RepairStore:
    def __init__(self, conn: sqlite3.Connection, run_dir: Path, run_id: str):
        self.conn = conn
        self.run_dir = run_dir
        self.run_id = run_id

    def import_supplemental_repair_artifacts(self, artifacts: list[sqlite3.Row]) -> None:
        for artifact in artifacts:
            path = Path(str(artifact["abs_path"] or artifact["rel_path"] or ""))
            if path.suffix != ".jsonl":
                continue
            rows = _read_jsonl(path)
            atype = str(artifact["artifact_type"] or "")
            if atype == "repair_faces":
                for row in rows:
                    face_id = str(row.get("face_id") or row.get("repair_face_id") or row.get("tower_face_id") or "")
                    rh = _row_hash(self.run_id, artifact["artifact_id"], "repair_face", face_id, row)
                    self.conn.execute(
                        """
                        INSERT OR IGNORE INTO repair_faces(row_hash, run_id, artifact_id, face_id, obstruction_id, parent_face_id, canonical_status, payload_json)
                        VALUES (?,?,?,?,?,?,?,?)
                        """,
                        (
                            rh,
                            self.run_id,
                            artifact["artifact_id"],
                            face_id or rh,
                            str(row.get("obstruction_id") or row.get("lambda_id") or ""),
                            str(row.get("parent_face_id") or ""),
                            str(row.get("canonical_status") or ""),
                            _json(row),
                        ),
                    )
            if atype == "hard_candidates":
                for row in rows:
                    action_id = str(row.get("action_id") or row.get("id") or "")
                    rh = _row_hash(self.run_id, artifact["artifact_id"], "hard_candidate", action_id, row)
                    meta = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
                    self.conn.execute(
                        """
                        INSERT OR IGNORE INTO hard_candidates(row_hash, run_id, artifact_id, action_id, candidate_id, hardening_id, tactic, canonical_status, payload_json)
                        VALUES (?,?,?,?,?,?,?,?,?)
                        """,
                        (
                            rh,
                            self.run_id,
                            artifact["artifact_id"],
                            action_id or rh,
                            str(row.get("candidate_id") or meta.get("candidate_id") or ""),
                            str(row.get("hardening_id") or meta.get("hardening_id") or ""),
                            str(row.get("tactic") or ""),
                            str(row.get("canonical_status") or meta.get("canonical_status") or ""),
                            _json(row),
                        ),
                    )
            if atype == "concept_decoded_repair_atoms":
                for row in rows:
                    atom_id = str(row.get("repair_atom_id") or row.get("atom_id") or "")
                    costs = row.get("cost_vector") if isinstance(row.get("cost_vector"), dict) else {}
                    rh = _row_hash(self.run_id, artifact["artifact_id"], "concept_decoded_repair_atom", atom_id, row)
                    self.conn.execute(
                        """
                        INSERT OR IGNORE INTO repair_atoms(
                            row_hash, run_dir, artifact_path, repair_atom_id, species_id, source, source_id,
                            cost, audit_risk, source_risk, ghost_risk, canonical_status, row_json
                        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                        """,
                        (
                            rh,
                            str(self.run_dir),
                            str(path),
                            atom_id or rh,
                            str(row.get("species_id") or row.get("repair_species") or "concept_latent"),
                            str(row.get("source") or "concept_search"),
                            str(row.get("source_id") or ""),
                            _float(costs.get("cost") or costs.get("cost_estimate"), 1.0),
                            _float(costs.get("audit_risk") or row.get("audit_risk"), 0.0),
                            _float(costs.get("source_risk") or row.get("source_risk"), 0.0),
                            _float(costs.get("ghost_risk") or row.get("ghost_risk"), 0.0),
                            str(row.get("canonical_status") or ""),
                            _json(row),
                        ),
                    )


def import_repair_artifacts(store: RepairStore, artifacts: list[Any]) -> None:
    store.import_supplemental_repair_artifacts(artifacts)


__all__ = ["RepairStore", "import_repair_artifacts"]
