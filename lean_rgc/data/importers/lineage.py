from __future__ import annotations

from typing import Any
import json
import sqlite3

from ...schemas import stable_hash


def _json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, default=str)


def _loads(text: str | None) -> Any:
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        return None


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    return conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


class LineageStore:
    def __init__(self, conn: sqlite3.Connection, run_id: str):
        self.conn = conn
        self.run_id = run_id
        self._edge_index = 10_000_000

    def add_edge(
        self,
        *,
        src_type: str,
        src_id: str,
        dst_type: str,
        dst_id: str,
        edge_type: str,
        artifact_id: int | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        if not src_id or not dst_id:
            return
        payload = payload or {}
        edge_id = "edge_" + stable_hash(
            {
                "run_id": self.run_id,
                "src_type": src_type,
                "src_id": src_id,
                "dst_type": dst_type,
                "dst_id": dst_id,
                "edge_type": edge_type,
                "payload": payload,
            },
            32,
        )
        self._edge_index += 1
        aid = int(artifact_id or 0)
        self.conn.execute(
            """
            INSERT OR REPLACE INTO lineage_edges(
                artifact_id, edge_index, src, dst, edge_type, raw_json,
                edge_id, run_id, src_type, src_id, dst_type, dst_id, payload_json
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                aid,
                self._edge_index,
                f"{src_type}:{src_id}",
                f"{dst_type}:{dst_id}",
                edge_type,
                _json(payload),
                edge_id,
                self.run_id,
                src_type,
                src_id,
                dst_type,
                dst_id,
                _json(payload),
            ),
        )

    def materialize_from_tables(self) -> None:
        if _table_exists(self.conn, "audit_rows"):
            for r in self.conn.execute("SELECT artifact_id, row_index, task_id, state_id, action_id FROM audit_rows").fetchall():
                audit_id = f"audit:{r['artifact_id']}:{r['row_index']}"
                self.add_edge(src_type="task", src_id=str(r["task_id"] or r["state_id"] or ""), dst_type="action", dst_id=str(r["action_id"] or ""), edge_type="task_audited_by_action", artifact_id=r["artifact_id"])
                self.add_edge(src_type="action", src_id=str(r["action_id"] or ""), dst_type="audit_response", dst_id=audit_id, edge_type="audit_yields_response", artifact_id=r["artifact_id"])
        if _table_exists(self.conn, "response_rows"):
            for r in self.conn.execute("SELECT artifact_id, row_index, state_id, action_id FROM response_rows").fetchall():
                response_id = f"response:{r['artifact_id']}:{r['row_index']}"
                self.add_edge(src_type="audit_response", src_id=f"audit:{r['artifact_id']}:{r['row_index']}", dst_type="response", dst_id=response_id, edge_type="audit_yields_response", artifact_id=r["artifact_id"])
                self.add_edge(src_type="response", src_id=response_id, dst_type="defect", dst_id=f"defect:{r['state_id']}", edge_type="response_yields_defect", artifact_id=r["artifact_id"])
        if _table_exists(self.conn, "repair_faces") and _table_exists(self.conn, "crg_problems"):
            for r in self.conn.execute("SELECT row_hash, face_id, obstruction_id FROM repair_faces").fetchall():
                self.add_edge(src_type="obstruction", src_id=str(r["obstruction_id"] or ""), dst_type="repair_face", dst_id=str(r["face_id"] or r["row_hash"]), edge_type="obstruction_yields_repair_face")
            for r in self.conn.execute("SELECT problem_id, parent_face_id FROM crg_problems").fetchall():
                self.add_edge(src_type="repair_face", src_id=str(r["parent_face_id"] or ""), dst_type="crg_problem", dst_id=str(r["problem_id"] or ""), edge_type="repair_face_yields_crg_problem")
        if _table_exists(self.conn, "relaxed_candidates"):
            for r in self.conn.execute("SELECT candidate_id, problem_id FROM relaxed_candidates").fetchall():
                self.add_edge(src_type="crg_problem", src_id=str(r["problem_id"] or ""), dst_type="relaxed_candidate", dst_id=str(r["candidate_id"] or ""), edge_type="crg_problem_yields_relaxed_candidate")
        if _table_exists(self.conn, "hardening_attempts"):
            for r in self.conn.execute("SELECT hardening_id, candidate_id FROM hardening_attempts").fetchall():
                self.add_edge(src_type="relaxed_candidate", src_id=str(r["candidate_id"] or ""), dst_type="hardening_attempt", dst_id=str(r["hardening_id"] or ""), edge_type="relaxed_candidate_yields_hardening_attempt")
        if _table_exists(self.conn, "hard_candidates"):
            for r in self.conn.execute("SELECT action_id, candidate_id, hardening_id FROM hard_candidates").fetchall():
                self.add_edge(src_type="hardening_attempt", src_id=str(r["hardening_id"] or r["candidate_id"] or ""), dst_type="hard_candidate", dst_id=str(r["action_id"] or ""), edge_type="hardening_attempt_yields_hard_candidate")
        if _table_exists(self.conn, "crg_audit_rows"):
            for r in self.conn.execute("SELECT candidate_id FROM crg_audit_rows").fetchall():
                self.add_edge(src_type="hard_candidate", src_id=str(r["candidate_id"] or ""), dst_type="audit_response", dst_id=f"crg_audit:{r['candidate_id']}", edge_type="hard_candidate_yields_audit")
        if _table_exists(self.conn, "poms_evidence"):
            for r in self.conn.execute("SELECT evidence_id, action_id FROM poms_evidence").fetchall():
                self.add_edge(src_type="audit_response", src_id=str(r["action_id"] or ""), dst_type="poms_evidence", dst_id=str(r["evidence_id"] or ""), edge_type="audit_yields_poms_evidence")
        if _table_exists(self.conn, "poms_promotion_decisions"):
            for r in self.conn.execute("SELECT decision_id, action_id FROM poms_promotion_decisions").fetchall():
                self.add_edge(src_type="poms_evidence", src_id=str(r["action_id"] or ""), dst_type="poms_promotion_decision", dst_id=str(r["decision_id"] or ""), edge_type="poms_evidence_yields_promotion_decision")
        if _table_exists(self.conn, "concept_search_rows"):
            for r in self.conn.execute("SELECT row_hash, concept_id, row_json FROM concept_search_rows").fetchall():
                payload = _loads(r["row_json"]) if "row_json" in r.keys() else None
                if not isinstance(payload, dict):
                    payload = {}
                search_id = str(payload.get("search_row_id") or r["row_hash"] or "")
                concept_id = str(r["concept_id"] or payload.get("concept_id") or "")
                self.add_edge(
                    src_type="concept_point",
                    src_id=concept_id,
                    dst_type="concept_search_row",
                    dst_id=search_id,
                    edge_type="concept_point_yields_search_witness",
                    payload={"row_hash": r["row_hash"]},
                )
        if _table_exists(self.conn, "repair_atoms"):
            for r in self.conn.execute("SELECT repair_atom_id, species_id, source, source_id, row_json FROM repair_atoms").fetchall():
                if str(r["species_id"] or "") != "concept_latent":
                    continue
                payload = _loads(r["row_json"]) if "row_json" in r.keys() else None
                if not isinstance(payload, dict):
                    payload = {}
                source_row = payload.get("provenance", {}).get("source_row") if isinstance(payload.get("provenance"), dict) else {}
                meta = source_row.get("metadata") if isinstance(source_row, dict) and isinstance(source_row.get("metadata"), dict) else {}
                search_id = str(meta.get("concept_search_row_id") or "")
                concept_id = str(meta.get("concept_id") or r["source_id"] or "")
                if search_id:
                    self.add_edge(
                        src_type="concept_search_row",
                        src_id=search_id,
                        dst_type="repair_atom",
                        dst_id=str(r["repair_atom_id"] or ""),
                        edge_type="concept_search_yields_repair_atom",
                    )
                elif concept_id:
                    self.add_edge(
                        src_type="concept_point",
                        src_id=concept_id,
                        dst_type="repair_atom",
                        dst_id=str(r["repair_atom_id"] or ""),
                        edge_type="concept_decode_yields_repair_atom",
                    )


def materialize_lineage(store: LineageStore) -> None:
    store.materialize_from_tables()


__all__ = ["LineageStore", "materialize_lineage"]
