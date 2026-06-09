from __future__ import annotations

from pathlib import Path
from typing import Any
import json

from .repair_space import make_repair_atom
from .schemas import read_jsonl, write_jsonl


SCHEMA_CONCEPT_DECODE = "lean-rgc-concept-decode-v62.0"


def _json_dump(obj: dict[str, Any], path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def _read_rows(path: str | Path | None) -> list[dict[str, Any]]:
    if not path:
        return []
    p = Path(path)
    if not p.exists():
        return []
    return [r for r in read_jsonl(p) if isinstance(r, dict)]


def _point_embedding(point: dict[str, Any]) -> dict[str, float]:
    if isinstance(point.get("response_embedding_map"), dict):
        return {str(k): float(v) for k, v in point["response_embedding_map"].items()}
    emb = point.get("response_embedding") if isinstance(point.get("response_embedding"), dict) else {}
    keys = [str(k) for k in emb.get("keys") or []]
    vals = emb.get("values") or []
    out: dict[str, float] = {}
    for i, key in enumerate(keys):
        try:
            out[key] = float(vals[i])
        except Exception:
            out[key] = 0.0
    return out


def decode_concepts_to_repair_atoms(
    *,
    concept_search_path: str | Path,
    concept_points_path: str | Path,
    out: str | Path,
    summary_out: str | Path | None = None,
    top_k: int | None = None,
) -> dict[str, Any]:
    search_rows = _read_rows(concept_search_path)
    points = {str(row.get("concept_id")): row for row in _read_rows(concept_points_path)}
    if top_k is not None and int(top_k) > 0:
        search_rows = search_rows[: int(top_k)]
    atoms: list[dict[str, Any]] = []
    for row in search_rows:
        point = points.get(str(row.get("concept_id")))
        if not point:
            continue
        source_row = {
            "concept_id": point.get("concept_id"),
            "source_id": point.get("source_id"),
            "response_embedding": _point_embedding(point),
            "cost": {
                "cost_estimate": (point.get("cost_embedding") or {}).get("description_cost", 1.0),
            },
            "audit_risk": (point.get("cost_embedding") or {}).get("audit_risk", 0.1),
            "hardening_cost": (point.get("cost_embedding") or {}).get("hardening_risk", 0.3),
            "metadata": {
                "source": "concept_decode",
                "concept_id": point.get("concept_id"),
                "concept_search_row_id": row.get("search_row_id"),
                "canonical_status": "concept_decode_witness_not_canonical",
            },
        }
        atom = make_repair_atom(
            species_id="concept_latent",
            source="concept_search",
            source_row=source_row,
            response_embedding=_point_embedding(point),
            candidate_action=None,
            atom_hint=str(point.get("concept_id")),
        )
        atom["concept_search_score"] = row.get("repair_score")
        atom["row_kind"] = "repair_atom"
        atom["canonical_status"] = "repair_witness_not_canonical"
        atoms.append(atom)
    write_jsonl(out, atoms)
    summary = {
        "schema_version": SCHEMA_CONCEPT_DECODE,
        "concept_search": str(concept_search_path),
        "concept_points": str(concept_points_path),
        "out": str(out),
        "n_atoms": len(atoms),
        "canonical_status": "concept_decode_outputs_repair_witnesses_not_canonical",
    }
    if summary_out:
        _json_dump(summary, summary_out)
    return summary


__all__ = ["SCHEMA_CONCEPT_DECODE", "decode_concepts_to_repair_atoms"]
