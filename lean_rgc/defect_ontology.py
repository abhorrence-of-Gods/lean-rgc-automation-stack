from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable
import json
import math
import re

import numpy as np

from .defect_registry import DefectAtom, DefectRegistry, seed_defect_registry
from .schemas import read_jsonl, write_jsonl, stable_hash

_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")


def _tokens_from_text(s: Any) -> set[str]:
    text = str(s or "").lower().replace("_", " ").replace("-", " ").replace(".", " ")
    return {t for t in _TOKEN_RE.findall(text) if t and len(t) > 1}


def _coerce_float_list(x: Any) -> list[float]:
    if not isinstance(x, list):
        return []
    out: list[float] = []
    for v in x:
        try:
            out.append(float(v))
        except Exception:
            return []
    return out


def _get_evidence(atom: dict[str, Any]) -> dict[str, Any]:
    ev = atom.get("evidence")
    return ev if isinstance(ev, dict) else {}


def _atom_id(atom: dict[str, Any]) -> str:
    return str(atom.get("atom_id") or atom.get("id") or stable_hash(atom, 12))


def _atom_source(atom: dict[str, Any]) -> str:
    ev = _get_evidence(atom)
    return str(ev.get("source") or atom.get("source") or atom.get("group") or atom.get("detector") or "unknown")


def _atom_tokens(atom: dict[str, Any]) -> set[str]:
    ev = _get_evidence(atom)
    toks: set[str] = set()
    fields: list[Any] = [
        atom.get("atom_id"), atom.get("group"), atom.get("detector"), atom.get("description"), atom.get("status"),
        ev.get("source"), ev.get("residual_key"), ev.get("coordinate_id"), ev.get("chart_status"), ev.get("canonical_status"),
    ]
    for t in atom.get("intervention_templates") or []:
        fields.append(t)
    for k in ev.get("response_keys") or []:
        fields.append(k)
    for k in ev.get("aliases") or []:
        fields.append(k)
    for tl in ev.get("top_loadings") or []:
        if isinstance(tl, dict):
            fields.append(tl.get("key"))
        else:
            fields.append(tl)
    for x in fields:
        toks |= _tokens_from_text(x)
    # qgen_residual_goal_eq should match goal.eq and eq_reflexive_goal.
    atom_id = _atom_id(atom)
    toks |= _tokens_from_text(atom_id.replace("qgen_residual_", "").replace("carrier_quotient_", "").replace("qcoord_", ""))
    return toks


def _basis_vector(atom: dict[str, Any]) -> tuple[list[str], np.ndarray]:
    ev = _get_evidence(atom)
    keys = ev.get("response_keys") or atom.get("response_keys") or []
    basis = ev.get("basis_vector") or atom.get("basis_vector") or []
    if isinstance(keys, list) and isinstance(basis, list) and len(keys) == len(basis) and keys:
        return [str(k) for k in keys], np.asarray(_coerce_float_list(basis), dtype=float)
    # Build sparse vector from top_loadings when available.
    tops = ev.get("top_loadings") or atom.get("top_loadings") or []
    kv: dict[str, float] = {}
    if isinstance(tops, list):
        for i, t in enumerate(tops):
            if isinstance(t, dict):
                k = str(t.get("key") or "")
                if not k:
                    continue
                try:
                    v = float(t.get("value", t.get("loading", t.get("weight", 1.0 / (1 + i)))))
                except Exception:
                    v = 1.0 / (1 + i)
                kv[k] = kv.get(k, 0.0) + v
    if kv:
        ks = sorted(kv)
        return ks, np.asarray([kv[k] for k in ks], dtype=float)
    return [], np.zeros(0, dtype=float)


def _vector_cosine(a: dict[str, Any], b: dict[str, Any]) -> float | None:
    ka, va = _basis_vector(a)
    kb, vb = _basis_vector(b)
    if not ka or not kb:
        return None
    keys = sorted(set(ka) | set(kb))
    ia = {k: i for i, k in enumerate(ka)}
    ib = {k: i for i, k in enumerate(kb)}
    xa = np.asarray([va[ia[k]] if k in ia else 0.0 for k in keys], dtype=float)
    xb = np.asarray([vb[ib[k]] if k in ib else 0.0 for k in keys], dtype=float)
    na = float(np.linalg.norm(xa)); nb = float(np.linalg.norm(xb))
    if na <= 1e-12 or nb <= 1e-12:
        return None
    return float(np.dot(xa, xb) / (na * nb))


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / max(1, len(a | b))


def atom_similarity(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    ta = _atom_tokens(a); tb = _atom_tokens(b)
    shared = ta & tb
    token_sim = _jaccard(ta, tb)
    vec_sim = _vector_cosine(a, b)
    # Defect atoms often have terse IDs but informative groups/residual keys.  Add a
    # small alias boost when the mined coordinate and seed atom share group-level
    # semantics such as goal/eq/arith/carrier.  This is still a chart heuristic.
    boost = 0.0
    ga = str(a.get("group") or _get_evidence(a).get("residual_key") or "").lower()
    gb = str(b.get("group") or _get_evidence(b).get("residual_key") or "").lower()
    if ga and gb and (ga == gb or ga.split(".")[0] == gb.split(".")[0]) and shared:
        boost += 0.12
    if {"eq", "arith", "forall", "simp", "typeclass", "constructor"} & shared:
        boost += 0.08
    if vec_sim is None:
        sim = token_sim + boost
        mode = "token_jaccard_with_alias_boost" if boost else "token_jaccard"
    else:
        # Vector agreement is stronger when present, but token similarity keeps aliases useful.
        sim = 0.70 * max(0.0, vec_sim) + 0.30 * token_sim + boost
        mode = "vector_cosine_plus_token" + ("_alias_boost" if boost else "")
    sim = min(1.0, max(0.0, sim))
    return {
        "similarity": float(sim),
        "token_similarity": float(token_sim),
        "vector_similarity": None if vec_sim is None else float(vec_sim),
        "alias_boost": float(boost),
        "mode": mode,
        "shared_tokens": sorted(shared)[:32],
    }


@dataclass
class DefectOntologyRecord:
    candidate_atom_id: str
    candidate_source: str
    nearest_atom_id: str | None
    relation: str
    recommendation: str
    similarity: float
    token_similarity: float
    vector_similarity: float | None
    chart_status: str
    poms_status: str
    evidence: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DefectOntologyReport:
    n_existing_atoms: int
    n_candidate_atoms: int
    n_records: int
    n_merge: int
    n_shadow: int
    n_over_refinement: int
    n_novel: int
    n_open: int
    n_split_suggestions: int
    merge_threshold: float
    shadow_threshold: float
    novel_threshold: float
    canonical_status: str
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _load_registry(path: str | Path | None) -> DefectRegistry:
    if path and Path(path).exists():
        return DefectRegistry.load(path)
    return seed_defect_registry()


def _atoms_from_registry_file(path: Path) -> list[dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if isinstance(data, dict) and isinstance(data.get("atoms"), list):
        return [a for a in data["atoms"] if isinstance(a, dict)]
    if isinstance(data, dict) and isinstance(data.get("defect_atoms"), list):
        return [a for a in data["defect_atoms"] if isinstance(a, dict)]
    return []


def load_candidate_atoms(paths: Iterable[str | Path]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for p0 in paths:
        p = Path(p0)
        if not p.exists():
            continue
        rows: list[dict[str, Any]] = []
        if p.suffix == ".jsonl":
            rows = [r for r in read_jsonl(p) if isinstance(r, dict)]
        elif p.suffix == ".json":
            rows = _atoms_from_registry_file(p)
        for r in rows:
            aid = _atom_id(r)
            key = aid + "::" + stable_hash(r, 10)
            if key in seen:
                continue
            seen.add(key)
            rr = dict(r)
            rr.setdefault("atom_id", aid)
            out.append(rr)
    return out


def discover_candidate_atom_paths(run_dir: str | Path) -> list[Path]:
    r = Path(run_dir)
    names = [
        "qgen/qgen_defect_atoms.jsonl",
        "qgen/qgen_defect_registry.json",
        "quotient_coordinates/quotient_coordinate_defect_atoms.jsonl",
        "quotient_coordinates/quotient_coordinate_defect_registry.json",
        "carrier_quotient/carrier_quotient_defect_atoms.jsonl",
        "carrier_quotient/carrier_quotient_defect_registry.json",
        "promotion_evidence_rows.jsonl",
    ]
    paths: list[Path] = []
    for name in names:
        paths.extend(sorted(r.glob(f"**/{name}")))
    # Also accept common root-level outputs.
    for glob in ["**/*defect_atoms.jsonl", "**/*defect_registry.json"]:
        for p in sorted(r.glob(glob)):
            if p not in paths:
                paths.append(p)
    return paths


def _as_atom_dict(atom: DefectAtom | dict[str, Any]) -> dict[str, Any]:
    return atom.to_dict() if isinstance(atom, DefectAtom) else dict(atom)


def _classify_candidate(
    cand: dict[str, Any],
    existing: list[dict[str, Any]],
    *,
    merge_threshold: float,
    shadow_threshold: float,
    novel_threshold: float,
) -> DefectOntologyRecord:
    cid = _atom_id(cand)
    source = _atom_source(cand)
    exact = [a for a in existing if _atom_id(a) == cid]
    if exact:
        siminfo = atom_similarity(cand, exact[0])
        relation = "existing_update"
        rec = "update_existing_evidence"
        chart = "same_atom_id_existing_coordinate"
        nearest = cid
    else:
        best: tuple[float, dict[str, Any], dict[str, Any]] | None = None
        for ex in existing:
            info = atom_similarity(cand, ex)
            sim = float(info["similarity"])
            if best is None or sim > best[0]:
                best = (sim, ex, info)
        if best is None:
            info = {"similarity": 0.0, "token_similarity": 0.0, "vector_similarity": None, "shared_tokens": [], "mode": "none"}
            nearest = None; relation = "novel"; rec = "add_as_candidate_atom"; chart = "novel_candidate_chart"
        else:
            sim, ex, info = best
            nearest = _atom_id(ex)
            if sim >= merge_threshold:
                relation = "merge"
                rec = "merge_into_existing_atom"
                chart = "likely_over_refinement_of_existing_atom"
            elif sim >= shadow_threshold:
                relation = "shadow"
                rec = "keep_as_shadow_readout_pending_contextual_validation"
                chart = "quotient_shadow_candidate"
            elif sim <= novel_threshold:
                relation = "novel"
                rec = "add_as_candidate_atom"
                chart = "novel_candidate_chart"
            else:
                relation = "open"
                rec = "hold_open_for_more_audit"
                chart = "ambiguous_chart_candidate"
    poms = str(_get_evidence(cand).get("canonical_status") or cand.get("canonical_status") or "witness_candidate_not_canonical")
    return DefectOntologyRecord(
        candidate_atom_id=cid,
        candidate_source=source,
        nearest_atom_id=nearest,
        relation=relation,
        recommendation=rec,
        similarity=float(info.get("similarity", 0.0)),
        token_similarity=float(info.get("token_similarity", 0.0)),
        vector_similarity=info.get("vector_similarity"),
        chart_status=chart,
        poms_status=poms,
        evidence={
            "candidate": cand,
            "similarity_info": info,
            "canonical_status": "defect_ontology_reconciliation_chart_not_canonical",
        },
    )


def _candidate_mutual_similarity(a: dict[str, Any], b: dict[str, Any]) -> float:
    return float(atom_similarity(a, b).get("similarity", 0.0))


def _split_suggestions(records: list[DefectOntologyRecord], candidates: dict[str, dict[str, Any]], *, split_similarity_threshold: float = 0.35) -> list[dict[str, Any]]:
    by_near: dict[str, list[DefectOntologyRecord]] = {}
    for r in records:
        if r.nearest_atom_id and r.relation in {"shadow", "open", "novel"}:
            by_near.setdefault(r.nearest_atom_id, []).append(r)
    out: list[dict[str, Any]] = []
    for atom_id, recs in by_near.items():
        if len(recs) < 2:
            continue
        low_pairs = []
        for i in range(len(recs)):
            for j in range(i + 1, len(recs)):
                a = candidates.get(recs[i].candidate_atom_id)
                b = candidates.get(recs[j].candidate_atom_id)
                if not a or not b:
                    continue
                sim = _candidate_mutual_similarity(a, b)
                if sim <= split_similarity_threshold:
                    low_pairs.append({"a": recs[i].candidate_atom_id, "b": recs[j].candidate_atom_id, "similarity": sim})
        if low_pairs:
            out.append({
                "existing_atom_id": atom_id,
                "suggestion": "split_existing_atom_or_create_subatlas",
                "n_candidate_children": len(recs),
                "low_similarity_pairs": low_pairs[:20],
                "candidate_atom_ids": [r.candidate_atom_id for r in recs],
                "canonical_status": "split_suggestion_chart_not_canonical_parent_nonpaid_least_repair_required",
            })
    return out


def reconcile_defect_ontology(
    *,
    base_registry: str | Path | None = None,
    candidate_atom_paths: Iterable[str | Path] = (),
    run_dir: str | Path | None = None,
    out_dir: str | Path,
    merge_threshold: float = 0.72,
    shadow_threshold: float = 0.35,
    novel_threshold: float = 0.18,
    include_open_in_registry: bool = False,
    include_shadow_in_registry: bool = False,
) -> dict[str, Any]:
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    reg = _load_registry(base_registry)
    existing = [_as_atom_dict(a) for a in reg.atoms]
    paths = list(Path(p) for p in candidate_atom_paths)
    if run_dir:
        for p in discover_candidate_atom_paths(run_dir):
            if p not in paths:
                paths.append(p)
    candidates = load_candidate_atoms(paths)
    cand_by_id: dict[str, dict[str, Any]] = {}
    # De-duplicate by atom id, keeping highest information evidence length.
    for c in candidates:
        aid = _atom_id(c)
        old = cand_by_id.get(aid)
        if old is None or len(json.dumps(c, default=str)) > len(json.dumps(old, default=str)):
            cand_by_id[aid] = c
    candidates = list(cand_by_id.values())
    records = [_classify_candidate(c, existing, merge_threshold=merge_threshold, shadow_threshold=shadow_threshold, novel_threshold=novel_threshold) for c in candidates]
    splits = _split_suggestions(records, cand_by_id)

    # Build reconciled registry: preserve existing, attach merge/shadow evidence, add novel/open candidates by policy.
    atom_by_id = {_atom_id(a): dict(a) for a in existing}
    merge_map: list[dict[str, Any]] = []
    for rec in records:
        cand = cand_by_id.get(rec.candidate_atom_id, {})
        if rec.relation in {"merge", "existing_update"} and rec.nearest_atom_id:
            base = atom_by_id.get(rec.nearest_atom_id)
            if base is not None:
                ev = dict(base.get("evidence") or {})
                ev.setdefault("ontology_reconciliation", []).append({
                    "candidate_atom_id": rec.candidate_atom_id,
                    "relation": rec.relation,
                    "similarity": rec.similarity,
                    "source": rec.candidate_source,
                    "recommendation": rec.recommendation,
                })
                base["evidence"] = ev
                atom_by_id[rec.nearest_atom_id] = base
            merge_map.append({
                "candidate_atom_id": rec.candidate_atom_id,
                "existing_atom_id": rec.nearest_atom_id,
                "relation": rec.relation,
                "similarity": rec.similarity,
                "recommendation": rec.recommendation,
            })
        elif rec.relation == "novel" or (rec.relation == "open" and include_open_in_registry) or (rec.relation == "shadow" and include_shadow_in_registry):
            d = dict(cand)
            aid = _atom_id(d)
            d.setdefault("group", d.get("group") or rec.candidate_source or "mined")
            d.setdefault("detector", d.get("detector") or "defect_ontology_reconcile")
            d.setdefault("intervention_templates", d.get("intervention_templates") or [])
            d["status"] = "candidate" if rec.relation == "novel" else rec.relation
            ev = dict(d.get("evidence") or {})
            ev["ontology_reconciliation"] = {
                "relation": rec.relation,
                "nearest_atom_id": rec.nearest_atom_id,
                "similarity": rec.similarity,
                "recommendation": rec.recommendation,
                "canonical_status": "reconciled_defect_atom_chart_not_canonical",
            }
            d["evidence"] = ev
            d.setdefault("description", f"Defect atom {aid} added by ontology reconciliation as {rec.relation} candidate.")
            atom_by_id[aid] = d

    reconciled_atoms: list[DefectAtom] = []
    for d in atom_by_id.values():
        # DefectAtom is strict; normalize to fields.
        nd = {
            "atom_id": _atom_id(d),
            "group": str(d.get("group") or "unknown"),
            "detector": str(d.get("detector") or "unknown"),
            "intervention_templates": list(d.get("intervention_templates") or []),
            "status": str(d.get("status") or "active"),
            "evidence": dict(d.get("evidence") or {}),
            "description": str(d.get("description") or ""),
        }
        reconciled_atoms.append(DefectAtom(**nd))
    reconciled = DefectRegistry(atoms=sorted(reconciled_atoms, key=lambda a: a.atom_id), version="lean-rgc-defect-registry-v39-ontology", metadata={
        "source": "defect_ontology_reconcile",
        "base_registry": str(base_registry) if base_registry else "seed_defect_registry",
        "candidate_atom_paths": [str(p) for p in paths],
        "canonical_status": "defect_ontology_registry_chart_not_canonical",
    })
    report = DefectOntologyReport(
        n_existing_atoms=len(existing),
        n_candidate_atoms=len(candidates),
        n_records=len(records),
        n_merge=sum(1 for r in records if r.relation in {"merge", "existing_update"}),
        n_shadow=sum(1 for r in records if r.relation == "shadow"),
        n_over_refinement=sum(1 for r in records if "over_refinement" in r.chart_status),
        n_novel=sum(1 for r in records if r.relation == "novel"),
        n_open=sum(1 for r in records if r.relation == "open"),
        n_split_suggestions=len(splits),
        merge_threshold=merge_threshold,
        shadow_threshold=shadow_threshold,
        novel_threshold=novel_threshold,
        canonical_status="defect_ontology_reconciliation_chart_not_canonical_parent_nonpaid_least_repair_required",
        notes=[
            "Classifications are finite chart heuristics, not canonical ontology decisions.",
            "Use held-out audit/POMS evidence before promoting merged or novel atoms.",
        ],
    )

    write_jsonl(out / "defect_ontology_rows.jsonl", [r.to_dict() for r in records])
    write_jsonl(out / "defect_ontology_merge_map.jsonl", merge_map)
    write_jsonl(out / "defect_ontology_split_suggestions.jsonl", splits)
    reconciled.save(out / "defect_registry_reconciled.json")
    (out / "defect_ontology_report.json").write_text(json.dumps(report.to_dict(), indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return {
        "out_dir": str(out),
        "report": report.to_dict(),
        "paths": {
            "rows": str(out / "defect_ontology_rows.jsonl"),
            "merge_map": str(out / "defect_ontology_merge_map.jsonl"),
            "split_suggestions": str(out / "defect_ontology_split_suggestions.jsonl"),
            "reconciled_registry": str(out / "defect_registry_reconciled.json"),
            "report": str(out / "defect_ontology_report.json"),
        },
    }


__all__ = [
    "reconcile_defect_ontology",
    "discover_candidate_atom_paths",
    "load_candidate_atoms",
    "atom_similarity",
    "DefectOntologyRecord",
    "DefectOntologyReport",
]
