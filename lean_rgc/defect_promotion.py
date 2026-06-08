from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
import json
import numpy as np

from .schemas import read_jsonl, write_jsonl
from .defect_registry import DefectRegistry, DefectAtom


@dataclass
class DefectPromotionRecord:
    atom_id: str
    group: str
    status_before: str
    status_after: str
    support: int = 0
    response_contrast: float = 0.0
    intervention_success: float = 0.0
    coker_reduction_proxy: float = 0.0
    registry_audit_margin: float = 0.0
    registry_audit_success_rate: float = 0.0
    promotion_score: float = 0.0
    promoted: bool = False
    reason: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _load_scores(path: str | Path | None) -> dict[str, dict[str, Any]]:
    if not path or not Path(path).exists():
        return {}
    rows = read_jsonl(path)
    out: dict[str, dict[str, Any]] = {}
    for r in rows:
        aid = str(r.get("atom_id", ""))
        if aid:
            out[aid] = r
    return out


def _registry_audit_by_atom(path: str | Path | None) -> dict[str, dict[str, float]]:
    if not path or not Path(path).exists():
        return {}
    rows = read_jsonl(path)
    by: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        act = r.get("action") if isinstance(r.get("action"), dict) else {}
        meta = act.get("metadata", {}) if isinstance(act.get("metadata"), dict) else {}
        atom_ids: list[str] = []
        # Direct registry candidates store atom metadata in several possible places.
        for key in ["atom_id", "carrier_atom"]:
            if meta.get(key):
                atom_ids.append(str(meta.get(key)))
        exp = meta.get("exposure") if isinstance(meta.get("exposure"), dict) else {}
        ecd = exp.get("expected_carrier_delta") if isinstance(exp.get("expected_carrier_delta"), dict) else {}
        atom_ids.extend(str(k) for k, v in ecd.items() if float(v) < 0)
        # Carrier tags include many atom ids in generated candidates.
        for tag in act.get("carrier_tags", []) or []:
            if isinstance(tag, str) and ("_" in tag or tag.startswith("missing") or tag.startswith("unintroduced")):
                atom_ids.append(tag)
        if not atom_ids:
            continue
        for atom in set(atom_ids):
            by.setdefault(atom, []).append(r)
    out: dict[str, dict[str, float]] = {}
    for atom, rs in by.items():
        margins = []
        successes = 0
        carrier_gains = []
        response_norms = []
        for r in rs:
            status = str(r.get("audit_status") or r.get("status") or "")
            successes += int(status == "success")
            cd = r.get("carrier_delta") or {}
            carrier_gain = 0.0
            if isinstance(cd, dict):
                carrier_gain = float(max(0.0, cd.get(atom, 0.0)))
            carrier_gains.append(carrier_gain)
            rf = r.get("response_flat") or []
            try:
                response_norms.append(float(np.linalg.norm(np.asarray(rf, dtype=float))))
            except Exception:
                response_norms.append(0.0)
            cost = 0.0
            act = r.get("action") if isinstance(r.get("action"), dict) else {}
            try:
                cost = float(act.get("cost_estimate", 0.0))
            except Exception:
                cost = 0.0
            margins.append(carrier_gain + 0.1 * response_norms[-1] - 0.05 * cost)
        out[atom] = {
            "n": float(len(rs)),
            "registry_audit_margin": float(np.mean(margins)) if margins else 0.0,
            "registry_audit_success_rate": float(successes / max(1, len(rs))),
            "mean_carrier_gain": float(np.mean(carrier_gains)) if carrier_gains else 0.0,
            "mean_response_norm": float(np.mean(response_norms)) if response_norms else 0.0,
        }
    return out


def promote_defects(registry_path: str | Path, *, scores_path: str | Path | None = None, registry_audit_responses: str | Path | None = None, out_registry: str | Path | None = None, out_report: str | Path | None = None, min_support: int = 1, min_response_contrast: float = -1e9, min_intervention_success: float = 0.0, min_coker_reduction: float = -1e9, min_registry_margin: float = -1e9, min_registry_success: float = 0.0, min_promotion_score: float = -1e9) -> tuple[DefectRegistry, list[DefectPromotionRecord]]:
    reg = DefectRegistry.load(registry_path)
    scores = _load_scores(scores_path)
    audits = _registry_audit_by_atom(registry_audit_responses)
    new_atoms: list[DefectAtom] = []
    records: list[DefectPromotionRecord] = []
    for atom in reg.atoms:
        sc = scores.get(atom.atom_id, {})
        au = audits.get(atom.atom_id, {})
        support = int(sc.get("support", atom.evidence.get("support", 0) if isinstance(atom.evidence, dict) else 0) or 0)
        response_contrast = float(sc.get("response_contrast", atom.evidence.get("response_contrast", 0.0) if isinstance(atom.evidence, dict) else 0.0) or 0.0)
        intervention_success = float(sc.get("intervention_success", atom.evidence.get("intervention_success", 0.0) if isinstance(atom.evidence, dict) else 0.0) or 0.0)
        coker_red = float(sc.get("coker_reduction_proxy", atom.evidence.get("coker_reduction_proxy", 0.0) if isinstance(atom.evidence, dict) else 0.0) or 0.0)
        reg_margin = float(au.get("registry_audit_margin", 0.0))
        reg_success = float(au.get("registry_audit_success_rate", 0.0))
        promotion_score = float(sc.get("promotion_score", 0.0) or 0.0) + max(0.0, reg_margin) + 0.5 * reg_success
        ok = (
            support >= min_support
            and response_contrast >= min_response_contrast
            and intervention_success >= min_intervention_success
            and coker_red >= min_coker_reduction
            and reg_margin >= min_registry_margin
            and reg_success >= min_registry_success
            and promotion_score >= min_promotion_score
        )
        status_after = "active" if ok else ("open" if atom.status == "active" else atom.status)
        ev = dict(atom.evidence or {})
        ev.update({"support": support, "response_contrast": response_contrast, "intervention_success": intervention_success, "coker_reduction_proxy": coker_red, "registry_audit": au, "promotion_score": promotion_score})
        new_atom = DefectAtom(atom_id=atom.atom_id, group=atom.group, detector=atom.detector, intervention_templates=list(atom.intervention_templates), status=status_after, evidence=ev)
        new_atoms.append(new_atom)
        records.append(DefectPromotionRecord(atom_id=atom.atom_id, group=atom.group, status_before=atom.status, status_after=status_after, support=support, response_contrast=response_contrast, intervention_success=intervention_success, coker_reduction_proxy=coker_red, registry_audit_margin=reg_margin, registry_audit_success_rate=reg_success, promotion_score=promotion_score, promoted=ok, reason="passes promotion thresholds" if ok else "below threshold", evidence=ev))
    new_reg = DefectRegistry(new_atoms)
    if out_registry:
        new_reg.save(out_registry)
    if out_report:
        write_jsonl(out_report, [r.to_dict() for r in records])
    return new_reg, records


__all__ = ["DefectPromotionRecord", "promote_defects"]
