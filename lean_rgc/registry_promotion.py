from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import json

from .schemas import read_jsonl, write_jsonl
from .defect_registry import DefectRegistry, DefectAtom
from .defect_miner import AutoDefectMiner, CandidateAtomScore


@dataclass
class RegistryPromotionRecord:
    atom_id: str
    old_status: str
    new_status: str
    support: int
    response_contrast: float
    intervention_success: float
    coker_reduction_proxy: float
    addressed_rate: float
    bootstrap_stability: float
    promotion_score: float
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RegistryPromotionReport:
    n_atoms_in: int
    n_validated: int
    n_rejected: int
    min_support: int
    min_intervention_success: float
    min_coker_reduction: float
    min_promotion_score: float
    records: list[RegistryPromotionRecord]

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["records"] = [r.to_dict() for r in self.records]
        return d


def _score_map(scores: list[CandidateAtomScore]) -> dict[str, CandidateAtomScore]:
    # Keep the best score per atom by promotion_score.
    out: dict[str, CandidateAtomScore] = {}
    for s in scores:
        old = out.get(s.atom_id)
        if old is None or s.promotion_score > old.promotion_score:
            out[s.atom_id] = s
    return out


def promote_registry_from_audits(
    registry: DefectRegistry,
    audit_rows: list[dict[str, Any]],
    response_rows: list[dict[str, Any]] | None = None,
    *,
    min_support: int = 1,
    min_intervention_success: float = 0.1,
    min_coker_reduction: float = -1e-9,
    min_promotion_score: float = -1e9,
    drop_rejected: bool = False,
) -> tuple[DefectRegistry, RegistryPromotionReport]:
    """Validate mined defect atoms using micro-audited generated candidates.

    This is still a finite chart of the coker-margin criterion.  An atom is
    promoted to ``validated`` if actions that address the atom empirically reduce
    its carrier residual / response proxy.  Rejected atoms can be retained as
    open witnesses or dropped from the active registry.
    """
    miner = AutoDefectMiner(seed=registry)
    scores = miner.score_atoms(audit_rows or [], response_rows or [])
    smap = _score_map(scores)
    new_atoms: list[DefectAtom] = []
    records: list[RegistryPromotionRecord] = []
    validated = 0
    rejected = 0
    for atom in registry.atoms:
        old_status = atom.status or "active"
        s = smap.get(atom.atom_id)
        if s is None:
            reason = "no_audit_evidence"
            ok = False
            vals = dict(support=0, response_contrast=0.0, intervention_success=0.0, coker_reduction_proxy=0.0, addressed_rate=0.0, bootstrap_stability=0.0, promotion_score=0.0)
        else:
            vals = dict(
                support=s.support,
                response_contrast=s.response_contrast,
                intervention_success=s.intervention_success,
                coker_reduction_proxy=s.coker_reduction_proxy,
                addressed_rate=s.addressed_rate,
                bootstrap_stability=s.bootstrap_stability,
                promotion_score=s.promotion_score,
            )
            ok = (
                s.support >= min_support
                and s.intervention_success >= min_intervention_success
                and s.coker_reduction_proxy >= min_coker_reduction
                and s.promotion_score >= min_promotion_score
            )
            if ok:
                reason = "validated_by_registry_candidate_audit"
            else:
                reason = "failed_thresholds"
        if ok:
            validated += 1
            new_status = "validated"
            d = atom.to_dict()
            ev = dict(d.get("evidence") or {})
            ev["registry_promotion"] = {**vals, "reason": reason}
            d["evidence"] = ev
            d["status"] = new_status
            new_atoms.append(DefectAtom(**d))
        else:
            rejected += 1
            new_status = "open" if not drop_rejected else "dropped"
            if not drop_rejected:
                d = atom.to_dict()
                ev = dict(d.get("evidence") or {})
                ev["registry_promotion"] = {**vals, "reason": reason}
                d["evidence"] = ev
                d["status"] = "open"
                new_atoms.append(DefectAtom(**d))
        records.append(RegistryPromotionRecord(
            atom_id=atom.atom_id,
            old_status=old_status,
            new_status=new_status,
            reason=reason,
            **vals,
        ))
    new_reg = DefectRegistry(atoms=new_atoms, version="lean-rgc-defect-registry-v0.7", metadata={
        **(registry.metadata or {}),
        "promotion": {
            "source": "registry_candidate_audit",
            "n_audit_rows": len(audit_rows or []),
            "n_response_rows": len(response_rows or []),
            "drop_rejected": drop_rejected,
        },
    })
    report = RegistryPromotionReport(
        n_atoms_in=len(registry.atoms),
        n_validated=validated,
        n_rejected=rejected,
        min_support=min_support,
        min_intervention_success=min_intervention_success,
        min_coker_reduction=min_coker_reduction,
        min_promotion_score=min_promotion_score,
        records=records,
    )
    return new_reg, report


def promote_registry_file(
    registry_path: str | Path,
    audits_path: str | Path,
    out_registry: str | Path,
    *,
    responses_path: str | Path | None = None,
    report_out: str | Path | None = None,
    min_support: int = 1,
    min_intervention_success: float = 0.1,
    min_coker_reduction: float = -1e-9,
    min_promotion_score: float = -1e9,
    drop_rejected: bool = False,
) -> tuple[DefectRegistry, RegistryPromotionReport]:
    reg = DefectRegistry.load(registry_path)
    audits = read_jsonl(audits_path)
    responses = read_jsonl(responses_path) if responses_path else []
    new_reg, report = promote_registry_from_audits(
        reg,
        audits,
        responses,
        min_support=min_support,
        min_intervention_success=min_intervention_success,
        min_coker_reduction=min_coker_reduction,
        min_promotion_score=min_promotion_score,
        drop_rejected=drop_rejected,
    )
    new_reg.save(out_registry)
    if report_out:
        Path(report_out).parent.mkdir(parents=True, exist_ok=True)
        Path(report_out).write_text(json.dumps(report.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    return new_reg, report
