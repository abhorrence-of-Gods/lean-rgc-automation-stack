from __future__ import annotations

from pathlib import Path
from typing import Any
import json

from .relaxed_species import default_relaxed_species_rows
from .repair_space import make_repair_atom, normalize_response_embedding, read_rows, safe_float
from .schemas import stable_hash, write_jsonl


SCHEMA_REPAIR_SPECIES_REGISTRY = "lean-rgc-repair-species-registry-v58.0"


def _json_dump(obj: dict[str, Any], path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def _from_action_geometry(path: str | Path | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in read_rows(path):
        rows.append(make_repair_atom(species_id="action_distribution", source="action_geometry", source_row=row))
    return rows


def _from_actions(path: str | Path | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in read_rows(path):
        if not (row.get("tactic") or row.get("action_id")):
            continue
        rows.append(make_repair_atom(species_id="action_distribution", source="actions", source_row=row))
    return rows


def _from_premise_registry(path: str | Path | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in read_rows(path):
        rows.append(make_repair_atom(species_id="premise_distribution", source="premise_response", source_row=row))
    return rows


def _coordinate_embedding(row: dict[str, Any], *, key_field: str) -> dict[str, float]:
    out: dict[str, float] = {}
    keys = [str(k) for k in (row.get(key_field) or [])]
    basis = row.get("basis_vector") or []
    if isinstance(basis, list):
        prefix = "carrier." if key_field == "carrier_keys" else ""
        for key, value in zip(keys, basis):
            out[prefix + str(key)] = safe_float(value)
    for loading in row.get("top_loadings") or []:
        if isinstance(loading, dict):
            key = str(loading.get("key") or "")
            if key:
                prefix = "carrier." if key_field == "carrier_keys" and not key.startswith("carrier.") else ""
                out.setdefault(prefix + key, safe_float(loading.get("loading")))
    return out


def _from_quotient_coordinates(path: str | Path | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in read_rows(path):
        emb = _coordinate_embedding(row, key_field="response_keys")
        rows.append(
            make_repair_atom(
                species_id="quotient_coordinate_cone",
                source="quotient_coordinates",
                source_row=row,
                response_embedding=emb,
            )
        )
    return rows


def _from_carrier_quotients(path: str | Path | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in read_rows(path):
        emb = _coordinate_embedding(row, key_field="carrier_keys")
        rows.append(
            make_repair_atom(
                species_id="carrier_patch_measure",
                source="carrier_quotient",
                source_row=row,
                response_embedding=emb,
            )
        )
    return rows


def _from_tower_retrieval(path: str | Path | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in read_rows(path):
        emb = normalize_response_embedding(row)
        if not emb:
            score = row.get("score_proxy") if isinstance(row.get("score_proxy"), dict) else {}
            emb = {
                "tower.support": safe_float(score.get("support"), 0.0),
                "tower.carrier_safe": 1.0 if score.get("carrier_safe") else 0.0,
                "tower.retrieval_allowed": 1.0 if score.get("retrieval_allowed") else 0.0,
            }
        rows.append(
            make_repair_atom(
                species_id="context_portfolio",
                source="tower_retrieval",
                source_row=row,
                response_embedding=emb,
            )
        )
    return rows


def _from_repair_faces(path: str | Path | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in read_rows(path):
        emb = normalize_response_embedding(row)
        rows.append(make_repair_atom(species_id="context_portfolio", source="repair_face", source_row=row, response_embedding=emb))
    return rows


def _dedup_atoms(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for row in rows:
        rid = str(row.get("repair_atom_id") or stable_hash(row, 16))
        if rid in seen:
            continue
        seen.add(rid)
        out.append(row)
    return out


def build_repair_species_registry(
    *,
    out: str | Path,
    summary_out: str | Path | None = None,
    actions_path: str | Path | None = None,
    action_geometry_path: str | Path | None = None,
    premise_registry_path: str | Path | None = None,
    quotient_coordinates_path: str | Path | None = None,
    carrier_quotient_path: str | Path | None = None,
    tower_retrieval_path: str | Path | None = None,
    repair_faces_path: str | Path | None = None,
    include_species_rows: bool = True,
) -> dict[str, Any]:
    atoms: list[dict[str, Any]] = []
    atoms.extend(_from_actions(actions_path))
    atoms.extend(_from_action_geometry(action_geometry_path))
    atoms.extend(_from_premise_registry(premise_registry_path))
    atoms.extend(_from_quotient_coordinates(quotient_coordinates_path))
    atoms.extend(_from_carrier_quotients(carrier_quotient_path))
    atoms.extend(_from_tower_retrieval(tower_retrieval_path))
    atoms.extend(_from_repair_faces(repair_faces_path))
    atoms = _dedup_atoms(atoms)

    rows: list[dict[str, Any]] = []
    if include_species_rows:
        for species in default_relaxed_species_rows():
            rows.append({**species, "row_kind": "species"})
    for atom in atoms:
        rows.append({**atom, "row_kind": "repair_atom"})
    write_jsonl(out, rows)
    species_counts: dict[str, int] = {}
    for atom in atoms:
        sid = str(atom.get("species_id") or "unknown")
        species_counts[sid] = species_counts.get(sid, 0) + 1
    summary = {
        "schema_version": SCHEMA_REPAIR_SPECIES_REGISTRY,
        "out": str(out),
        "n_rows": len(rows),
        "n_species": len(default_relaxed_species_rows()) if include_species_rows else 0,
        "n_repair_atoms": len(atoms),
        "species_counts": dict(sorted(species_counts.items())),
        "inputs": {
            "actions": str(actions_path) if actions_path else None,
            "action_geometry": str(action_geometry_path) if action_geometry_path else None,
            "premise_registry": str(premise_registry_path) if premise_registry_path else None,
            "quotient_coordinates": str(quotient_coordinates_path) if quotient_coordinates_path else None,
            "carrier_quotient": str(carrier_quotient_path) if carrier_quotient_path else None,
            "tower_retrieval": str(tower_retrieval_path) if tower_retrieval_path else None,
            "repair_faces": str(repair_faces_path) if repair_faces_path else None,
        },
        "canonical_status": "repair_species_registry_chart_not_canonical",
    }
    if summary_out:
        _json_dump(summary, summary_out)
    return summary


def load_repair_atoms(path: str | Path | None) -> list[dict[str, Any]]:
    return [row for row in read_rows(path) if row.get("row_kind") == "repair_atom" or row.get("repair_atom_id")]


__all__ = [
    "SCHEMA_REPAIR_SPECIES_REGISTRY",
    "build_repair_species_registry",
    "load_repair_atoms",
]
