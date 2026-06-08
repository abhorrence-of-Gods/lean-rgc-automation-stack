from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable
import csv
import json

from .defect_registry import DefectAtom, DefectRegistry, seed_defect_registry
from .defect_ontology import reconcile_defect_ontology
from .schemas import read_jsonl, write_jsonl, stable_hash


CANONICAL_NOTE = "defect_ontology_lifecycle_chart_not_canonical_parent_nonpaid_least_repair_required"


def _read_json(path: str | Path | None) -> Any:
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


def _atom_id(x: dict[str, Any]) -> str:
    return str(x.get("candidate_atom_id") or x.get("atom_id") or x.get("id") or stable_hash(x, 12))


def _as_list(x: Any) -> list[Any]:
    return x if isinstance(x, list) else []


def _discover_first(run_dir: str | Path | None, patterns: Iterable[str]) -> Path | None:
    if not run_dir:
        return None
    root = Path(run_dir)
    for pat in patterns:
        hits = sorted(root.glob(pat))
        if hits:
            return hits[0]
    return None


def _discover_many(run_dir: str | Path | None, patterns: Iterable[str]) -> list[Path]:
    if not run_dir:
        return []
    root = Path(run_dir)
    out: list[Path] = []
    for pat in patterns:
        for p in sorted(root.glob(pat)):
            if p not in out:
                out.append(p)
    return out


def _load_registry(path: str | Path | None) -> DefectRegistry:
    if path and Path(path).exists():
        try:
            return DefectRegistry.load(path)
        except Exception:
            pass
    return seed_defect_registry()


def _normalize_atom_dict(d: dict[str, Any], *, status: str | None = None, evidence_extra: dict[str, Any] | None = None) -> DefectAtom:
    ev = dict(d.get("evidence") or {})
    if evidence_extra:
        ev.setdefault("ontology_lifecycle", {}).update(evidence_extra)
    return DefectAtom(
        atom_id=str(d.get("atom_id") or d.get("candidate_atom_id") or d.get("id") or stable_hash(d, 12)),
        group=str(d.get("group") or d.get("candidate_source") or d.get("source") or "lifecycle"),
        detector=str(d.get("detector") or "defect_ontology_lifecycle"),
        intervention_templates=list(d.get("intervention_templates") or []),
        status=str(status or d.get("status") or "candidate"),
        evidence=ev,
        description=str(d.get("description") or f"Defect atom mined by lifecycle manager: {d.get('atom_id') or d.get('candidate_atom_id') or ''}"),
    )


@dataclass
class LifecycleDecision:
    atom_id: str
    source: str
    previous_relation: str
    lifecycle_status: str
    lifecycle_recommendation: str
    nearest_atom_id: str | None = None
    similarity: float = 0.0
    evidence_score: float = 0.0
    support_count: int = 0
    heldout_verified: bool = False
    parent_nonpaid: bool = False
    dual_certificate: bool = False
    least_repair: bool = False
    poms_promoted_status: str | None = None
    canonical_status: str = CANONICAL_NOTE
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LifecycleReport:
    schema_version: str
    n_records: int
    by_lifecycle_status: dict[str, int]
    n_validated: int
    n_pending: int
    n_deprecated: int
    n_merge_validated: int
    n_split_suggestions: int
    out_dir: str
    canonical_status: str
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _index_promotion_rows(paths: Iterable[str | Path]) -> dict[str, dict[str, Any]]:
    idx: dict[str, dict[str, Any]] = {}
    for p0 in paths:
        p = Path(p0)
        if not p.exists():
            continue
        for r in read_jsonl(p):
            if not isinstance(r, dict):
                continue
            keys = set()
            for k in ["action_id", "atom_id", "candidate_atom_id", "carrier_atom", "residual_key", "coordinate_id"]:
                if r.get(k):
                    keys.add(str(r[k]))
            for k in _as_list(r.get("parent_residual_keys")):
                keys.add(str(k))
            status = str(r.get("promoted_status") or r.get("status") or r.get("poms_status") or "")
            score = 0.0
            score += 1.0 if r.get("parent_nonpaid") else 0.0
            score += 1.0 if r.get("dual_certificate") else 0.0
            score += 1.0 if r.get("least_repair") else 0.0
            if status in {"paid_witness", "forced_candidate", "canonical_candidate", "canonical_observable"}:
                score += 1.0
            for key in keys:
                old = idx.get(key)
                if old is None or score > _safe_float(old.get("_score")):
                    rr = dict(r)
                    rr["_score"] = score
                    idx[key] = rr
    return idx


def _index_validation_rows(paths: Iterable[str | Path]) -> dict[str, dict[str, Any]]:
    idx: dict[str, dict[str, Any]] = {}
    for p0 in paths:
        p = Path(p0)
        if not p.exists():
            continue
        rows = read_jsonl(p) if p.suffix == ".jsonl" else []
        for r in rows:
            if not isinstance(r, dict):
                continue
            keys = []
            for k in ["atom_id", "candidate_atom_id", "coordinate_id", "carrier_coordinate_id", "coordinate", "defect_atom_id"]:
                if r.get(k):
                    keys.append(str(r[k]))
            score = 0.0
            for k in ["holdout_support_score", "validation_score", "mean_margin", "robust_margin", "support_score", "score"]:
                score = max(score, _safe_float(r.get(k), 0.0))
            passed = bool(r.get("accepted") or r.get("validated") or r.get("holdout_verified") or r.get("validation_pass"))
            if passed:
                score += 1.0
            for key in keys:
                old = idx.get(key)
                if old is None or score > _safe_float(old.get("_score")):
                    rr = dict(r)
                    rr["_score"] = score
                    rr["_passed"] = passed
                    idx[key] = rr
    return idx


def _load_reconciliation_rows(path: str | Path | None, *, run_dir: str | Path | None = None, reconcile_kwargs: dict[str, Any] | None = None) -> tuple[list[dict[str, Any]], dict[str, Any] | None, Path | None]:
    if path and Path(path).exists():
        p = Path(path)
        return [r for r in read_jsonl(p) if isinstance(r, dict)], _read_json(p.with_name("defect_ontology_report.json")), p
    found = _discover_first(run_dir, ["**/defect_ontology_rows.jsonl"])
    if found:
        return [r for r in read_jsonl(found) if isinstance(r, dict)], _read_json(found.with_name("defect_ontology_report.json")), found
    # Run reconciliation lazily if no rows exist and run_dir/out_dir info was supplied.
    if run_dir and reconcile_kwargs:
        tmp_out = Path(reconcile_kwargs.get("out_dir") or Path(run_dir) / "defect_ontology")
        res = reconcile_defect_ontology(run_dir=run_dir, out_dir=tmp_out, base_registry=reconcile_kwargs.get("base_registry"), candidate_atom_paths=reconcile_kwargs.get("candidate_atom_paths", []))
        p = tmp_out / "defect_ontology_rows.jsonl"
        if p.exists():
            return [r for r in read_jsonl(p) if isinstance(r, dict)], res.get("report"), p
    return [], None, None


def _decision_from_record(
    rec: dict[str, Any],
    *,
    promotion_index: dict[str, dict[str, Any]],
    validation_index: dict[str, dict[str, Any]],
    min_evidence_score: float,
    min_support_count: int,
) -> LifecycleDecision:
    atom_id = str(rec.get("candidate_atom_id") or rec.get("atom_id") or stable_hash(rec, 12))
    relation = str(rec.get("relation") or "open")
    nearest = rec.get("nearest_atom_id")
    source = str(rec.get("candidate_source") or "unknown")
    sim = _safe_float(rec.get("similarity"), 0.0)
    ev = rec.get("evidence") if isinstance(rec.get("evidence"), dict) else {}
    candidate = ev.get("candidate") if isinstance(ev.get("candidate"), dict) else {}
    keys = {atom_id}
    for k in [nearest, candidate.get("atom_id"), candidate.get("candidate_atom_id")]:
        if k:
            keys.add(str(k))
    cev = candidate.get("evidence") if isinstance(candidate.get("evidence"), dict) else {}
    for k in [cev.get("residual_key"), cev.get("coordinate_id"), cev.get("carrier_coordinate_id")]:
        if k:
            keys.add(str(k))
    for tl in _as_list(cev.get("top_loadings")):
        if isinstance(tl, dict) and tl.get("key"):
            keys.add(str(tl.get("key")))

    promo: dict[str, Any] = {}
    val: dict[str, Any] = {}
    for key in keys:
        if key in promotion_index and _safe_float(promotion_index[key].get("_score")) > _safe_float(promo.get("_score")):
            promo = promotion_index[key]
        if key in validation_index and _safe_float(validation_index[key].get("_score")) > _safe_float(val.get("_score")):
            val = validation_index[key]

    parent_nonpaid = bool(promo.get("parent_nonpaid"))
    dual_certificate = bool(promo.get("dual_certificate"))
    least_repair = bool(promo.get("least_repair"))
    pstatus = str(promo.get("promoted_status") or promo.get("status") or "") or None
    heldout = bool(val.get("_passed") or val.get("holdout_verified"))
    support_count = int(_safe_float(candidate.get("support_count") or cev.get("support_count") or rec.get("support_count"), 0.0))
    evidence_score = 0.0
    evidence_score += 1.0 if parent_nonpaid else 0.0
    evidence_score += 1.0 if dual_certificate else 0.0
    evidence_score += 1.0 if least_repair else 0.0
    evidence_score += 1.0 if heldout else 0.0
    evidence_score += min(1.0, support_count / max(1, min_support_count))
    evidence_score += max(0.0, min(1.0, sim)) * 0.25

    if relation in {"merge", "existing_update"}:
        if heldout or dual_certificate or evidence_score >= min_evidence_score:
            status = "merge_validated"
            recommendation = "merge_candidate_into_existing_atom_and_deprecate_candidate_alias"
        else:
            status = "merge_pending"
            recommendation = "keep_candidate_as_merge_pending_until_heldout_verified"
    elif relation == "novel":
        if parent_nonpaid and dual_certificate and least_repair and (heldout or evidence_score >= min_evidence_score):
            status = "validated_novel_atom"
            recommendation = "add_to_defect_ontology_as_validated_candidate"
        elif heldout or evidence_score >= min_evidence_score:
            status = "novel_pending_poms"
            recommendation = "add_as_candidate_but_do_not_promote_without_poms_evidence"
        else:
            status = "novel_pending_verification"
            recommendation = "hold_pending_heldout_validation"
    elif relation == "shadow":
        if heldout and dual_certificate:
            status = "shadow_validated"
            recommendation = "record_as_shadow_readout_of_existing_atom"
        else:
            status = "shadow_pending"
            recommendation = "keep_as_shadow_candidate_pending_contextual_validation"
    elif relation == "open":
        if heldout and evidence_score >= min_evidence_score:
            status = "open_verified_needs_classification"
            recommendation = "request_additional_merge_split_audit"
        else:
            status = "open_pending"
            recommendation = "hold_open_for_more_audit"
    else:
        status = "pending"
        recommendation = "hold_pending"

    if status.startswith("merge"):
        deprecated = True
    else:
        deprecated = False
    return LifecycleDecision(
        atom_id=atom_id,
        source=source,
        previous_relation=relation,
        lifecycle_status=status,
        lifecycle_recommendation=recommendation,
        nearest_atom_id=str(nearest) if nearest else None,
        similarity=sim,
        evidence_score=float(evidence_score),
        support_count=support_count,
        heldout_verified=heldout,
        parent_nonpaid=parent_nonpaid,
        dual_certificate=dual_certificate,
        least_repair=least_repair,
        poms_promoted_status=pstatus,
        evidence={
            "reconciliation_record": rec,
            "promotion_evidence": promo,
            "validation_evidence": val,
            "deprecated_candidate_alias": deprecated,
        },
    )


def _load_split_suggestions(path: str | Path | None, run_dir: str | Path | None) -> list[dict[str, Any]]:
    p = Path(path) if path else _discover_first(run_dir, ["**/defect_ontology_split_suggestions.jsonl"])
    if p and p.exists():
        return [r for r in read_jsonl(p) if isinstance(r, dict)]
    return []


def run_defect_ontology_lifecycle(
    *,
    run_dir: str | Path | None = None,
    out_dir: str | Path,
    reconciliation_rows: str | Path | None = None,
    split_suggestions: str | Path | None = None,
    base_registry: str | Path | None = None,
    reconciled_registry: str | Path | None = None,
    previous_lifecycle_rows: Iterable[str | Path] = (),
    promotion_rows: Iterable[str | Path] = (),
    validation_rows: Iterable[str | Path] = (),
    min_evidence_score: float = 2.0,
    min_support_count: int = 1,
    include_pending_in_registry: bool = False,
) -> dict[str, Any]:
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    if not promotion_rows:
        promotion_rows = _discover_many(run_dir, ["**/poms_promotion_rows.jsonl", "**/promotion_evidence_for_poms.jsonl", "**/promotion_evidence_rows.jsonl"])
    if not validation_rows:
        validation_rows = _discover_many(run_dir, ["**/*validation_rows.jsonl", "**/*robust_acceptance_rows.jsonl", "**/*acceptance_rows.jsonl"])
    recs, rec_report, rec_path = _load_reconciliation_rows(
        reconciliation_rows,
        run_dir=run_dir,
        reconcile_kwargs={"out_dir": Path(run_dir) / "defect_ontology" if run_dir else out / "defect_ontology", "base_registry": base_registry} if run_dir else None,
    )
    promo_idx = _index_promotion_rows(promotion_rows)
    val_idx = _index_validation_rows(validation_rows)
    decisions = [_decision_from_record(r, promotion_index=promo_idx, validation_index=val_idx, min_evidence_score=min_evidence_score, min_support_count=min_support_count) for r in recs]

    # Include previous lifecycle rows as historical records.  They do not override current evidence, but they preserve state continuity.
    historical: list[dict[str, Any]] = []
    for p0 in previous_lifecycle_rows or []:
        p = Path(p0)
        if p.exists():
            historical.extend([r for r in read_jsonl(p) if isinstance(r, dict)])
    current_ids = {d.atom_id for d in decisions}
    for h in historical:
        aid = str(h.get("atom_id") or "")
        if aid and aid not in current_ids:
            hh = dict(h)
            hh["lifecycle_status"] = str(hh.get("lifecycle_status") or "historical")
            hh["lifecycle_recommendation"] = "carry_forward_historical_lifecycle_state_pending_new_evidence"
            hh.setdefault("canonical_status", CANONICAL_NOTE)
            decisions.append(LifecycleDecision(**{k: hh.get(k) for k in LifecycleDecision.__dataclass_fields__.keys() if k in hh}))

    splits_in = _load_split_suggestions(split_suggestions, run_dir)
    split_rows: list[dict[str, Any]] = []
    for s in splits_in:
        row = dict(s)
        support = int(_safe_float(row.get("n_candidate_children") or len(_as_list(row.get("candidate_atom_ids"))), 0.0))
        row["lifecycle_status"] = "split_validated" if support >= max(2, min_support_count) else "split_proposed"
        row["canonical_status"] = CANONICAL_NOTE
        split_rows.append(row)

    rows = [d.to_dict() for d in decisions]
    by: dict[str, int] = {}
    for r in rows:
        by[str(r.get("lifecycle_status"))] = by.get(str(r.get("lifecycle_status")), 0) + 1

    validated_statuses = {"validated_novel_atom", "merge_validated", "shadow_validated", "split_validated", "novel_pending_poms"}
    pending_statuses = {"merge_pending", "novel_pending_verification", "shadow_pending", "open_pending", "pending", "open_verified_needs_classification"}
    deprecated = [r for r in rows if r.get("evidence", {}).get("deprecated_candidate_alias")]
    merge_decisions = [r for r in rows if str(r.get("lifecycle_status", "")).startswith("merge")]
    validated = [r for r in rows if r.get("lifecycle_status") in validated_statuses]

    write_jsonl(out / "defect_ontology_lifecycle_rows.jsonl", rows)
    write_jsonl(out / "defect_ontology_deprecations.jsonl", deprecated)
    write_jsonl(out / "defect_ontology_merge_decisions.jsonl", merge_decisions)
    write_jsonl(out / "defect_ontology_split_decisions.jsonl", split_rows)
    write_jsonl(out / "defect_ontology_validated_atoms.jsonl", validated)
    if rows:
        with (out / "defect_ontology_lifecycle_rows.csv").open("w", encoding="utf-8", newline="") as f:
            cols = ["atom_id", "source", "previous_relation", "lifecycle_status", "lifecycle_recommendation", "nearest_atom_id", "similarity", "evidence_score", "heldout_verified", "parent_nonpaid", "dual_certificate", "least_repair", "poms_promoted_status"]
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            for r in rows:
                w.writerow({c: r.get(c) for c in cols})

    # Registry lifecycle output.
    reg_path = reconciled_registry or _discover_first(run_dir, ["**/defect_registry_reconciled.json"]) or base_registry
    reg = _load_registry(reg_path)
    atom_by_id = {a.atom_id: a for a in reg.atoms}
    # Update existing atoms with lifecycle evidence.
    for d in decisions:
        if d.nearest_atom_id and d.nearest_atom_id in atom_by_id:
            a = atom_by_id[d.nearest_atom_id]
            ev = dict(a.evidence or {})
            ev.setdefault("ontology_lifecycle", []).append({
                "candidate_atom_id": d.atom_id,
                "lifecycle_status": d.lifecycle_status,
                "recommendation": d.lifecycle_recommendation,
                "evidence_score": d.evidence_score,
                "canonical_status": CANONICAL_NOTE,
            })
            atom_by_id[d.nearest_atom_id] = DefectAtom(atom_id=a.atom_id, group=a.group, detector=a.detector, intervention_templates=a.intervention_templates, status=a.status, evidence=ev, description=a.description)
    # Add validated novel / optionally pending candidates.
    for r in rows:
        st = str(r.get("lifecycle_status"))
        cand = (((r.get("evidence") or {}).get("reconciliation_record") or {}).get("evidence") or {}).get("candidate") or {}
        if not isinstance(cand, dict) or not cand:
            cand = {"atom_id": r.get("atom_id"), "group": r.get("source"), "description": r.get("lifecycle_recommendation")}
        add = st in {"validated_novel_atom", "novel_pending_poms"} or (include_pending_in_registry and st in pending_statuses)
        if add:
            atom = _normalize_atom_dict(cand, status="validated_candidate" if st == "validated_novel_atom" else "candidate", evidence_extra={
                "lifecycle_status": st,
                "lifecycle_recommendation": r.get("lifecycle_recommendation"),
                "canonical_status": CANONICAL_NOTE,
            })
            atom_by_id[atom.atom_id] = atom
    lifecycle_registry = DefectRegistry(atoms=sorted(atom_by_id.values(), key=lambda a: a.atom_id), version="lean-rgc-defect-registry-v40-lifecycle", metadata={
        "source": "defect_ontology_lifecycle",
        "run_dir": str(run_dir) if run_dir else None,
        "reconciliation_rows": str(rec_path) if rec_path else None,
        "canonical_status": CANONICAL_NOTE,
    })
    lifecycle_registry.save(out / "defect_registry_lifecycle.json")

    report = LifecycleReport(
        schema_version="lean-rgc-defect-ontology-lifecycle-v40.0",
        n_records=len(rows),
        by_lifecycle_status=by,
        n_validated=len(validated),
        n_pending=sum(by.get(s, 0) for s in pending_statuses),
        n_deprecated=len(deprecated),
        n_merge_validated=by.get("merge_validated", 0),
        n_split_suggestions=len(split_rows),
        out_dir=str(out),
        canonical_status=CANONICAL_NOTE,
        notes=[
            "Lifecycle statuses are finite audit/provenance witnesses, not canonical ontology decisions.",
            "Validated candidates still require POMS parent-nonpaid / dual / least-repair evidence for canonical promotion.",
        ],
    )
    (out / "defect_ontology_lifecycle_report.json").write_text(json.dumps(report.to_dict(), indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return {"report": report.to_dict(), "out_dir": str(out), "files": {
        "rows": str(out / "defect_ontology_lifecycle_rows.jsonl"),
        "csv": str(out / "defect_ontology_lifecycle_rows.csv"),
        "validated_atoms": str(out / "defect_ontology_validated_atoms.jsonl"),
        "deprecations": str(out / "defect_ontology_deprecations.jsonl"),
        "merge_decisions": str(out / "defect_ontology_merge_decisions.jsonl"),
        "split_decisions": str(out / "defect_ontology_split_decisions.jsonl"),
        "registry": str(out / "defect_registry_lifecycle.json"),
        "report": str(out / "defect_ontology_lifecycle_report.json"),
    }}
