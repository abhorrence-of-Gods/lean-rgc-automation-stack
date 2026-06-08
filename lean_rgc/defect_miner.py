from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import json

import numpy as np

from .defect_registry import DefectAtom, DefectRegistry, seed_defect_registry
from .goal_shape import parse_goal_shape
from .schemas import ProofState, read_jsonl, write_jsonl


@dataclass
class CandidateAtomScore:
    atom_id: str
    group: str
    support: int
    response_contrast: float
    intervention_success: float
    bootstrap_stability: float
    paid_null_violation: float
    coker_reduction_proxy: float = 0.0
    addressed_rate: float = 0.0
    promotion_score: float = 0.0
    evidence: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if d.get("evidence") is None:
            d["evidence"] = {}
        return d


class AutoDefectMiner:
    """Mine defect atoms from micro-audit/response rows.

    v0.6 adds a quotient-style validation layer: an atom is scored not only by
    correlation with response norm, but also by whether actions that claim to
    address the atom produce carrier/defect decrease on states where the atom is
    present.  This remains a finite chart, not a canonical proof of defecthood.
    """

    def __init__(self, seed: DefectRegistry | None = None, min_support: int = 1, response_threshold: float = -1e9, stability_threshold: float = 0.0, min_intervention_success: float = 0.0, min_coker_reduction: float = -1e9):
        self.seed = seed or seed_defect_registry()
        self.min_support = min_support
        self.response_threshold = response_threshold
        self.stability_threshold = stability_threshold
        self.min_intervention_success = min_intervention_success
        self.min_coker_reduction = min_coker_reduction

    def signals_for_row(self, row: dict[str, Any]) -> dict[str, float]:
        text = "\n".join([
            str(row.get("target", "")),
            str(row.get("goals_text", "")),
            str(row.get("stdout", "")),
            str(row.get("stderr", "")),
            "\n".join(map(str, row.get("messages", []) or [])),
        ])
        if "action" in row and isinstance(row.get("action"), dict):
            text += "\n" + str(row["action"].get("tactic", ""))
            text += "\n" + jsonish(row["action"].get("metadata", {}))
        if "audit_record" in row and isinstance(row["audit_record"], dict):
            text += "\n" + jsonish(row["audit_record"])
        shape = parse_goal_shape(None, ProofState(state_id=str(row.get("state_id", "s")), task_id=str(row.get("task_id", "t")), target=str(row.get("target", "")), goals_text=str(row.get("goals_text", "")), raw_messages=list(map(str, row.get("messages", []) or []))), extra=text)
        low = text.lower()
        sig = {
            "unintroduced_forall": float(shape.has_forall or "⊢ ∀" in text or "forall" in low),
            "unintroduced_imp": float(shape.has_imp),
            "unsplit_and_target": float(shape.target_is_and),
            "missing_and_projection": float(shape.has_and_hyp),
            "eq_reflexive_goal": float(shape.target_is_eq or "rfl failed" in low),
            "nat_arith_goal": float(shape.has_arith),
            "list_simp_goal": float(shape.has_list),
            "missing_rewrite_orientation": float("rewrite" in low or "rw" in low or (shape.target_is_eq and "rfl failed" not in low)),
            "missing_typeclass_instance": float(shape.has_typeclass_error or "failed to synthesize" in low),
            "constructor_branch_debt": float("constructor" in low and ("unsolved goal" in low or shape.target_is_and)),
            "metavar_exposure_debt": float(shape.has_metavar),
        }
        return sig

    @staticmethod
    def _response_norm(row: dict[str, Any]) -> float:
        if row.get("response_flat"):
            try:
                return float(np.linalg.norm(np.asarray(row.get("response_flat", []), dtype=float)))
            except Exception:
                return 0.0
        if isinstance(row.get("response"), dict):
            try:
                return float(np.linalg.norm(np.asarray(list(row["response"].values()), dtype=float)))
            except Exception:
                return 0.0
        return 0.0

    @staticmethod
    def _status(row: dict[str, Any]) -> str:
        return str(row.get("status") or row.get("audit_status") or row.get("audit", {}).get("status") or "")

    @staticmethod
    def _action_dict(row: dict[str, Any]) -> dict[str, Any]:
        a = row.get("action")
        return a if isinstance(a, dict) else {}

    @staticmethod
    def _addresses_atom(row: dict[str, Any], atom_id: str, atom: DefectAtom | None = None) -> bool:
        a = AutoDefectMiner._action_dict(row)
        tactic = str(a.get("tactic", row.get("tactic", ""))).lower()
        tags = set(map(str, a.get("carrier_tags", []) or []))
        meta = a.get("metadata", {}) if isinstance(a.get("metadata"), dict) else {}
        expected = {}
        exp = meta.get("exposure") if isinstance(meta.get("exposure"), dict) else {}
        if isinstance(exp.get("expected_carrier_delta"), dict):
            expected.update(exp.get("expected_carrier_delta"))
        if isinstance(meta.get("expected_carrier_delta"), dict):
            expected.update(meta.get("expected_carrier_delta"))
        if atom_id in expected and float(expected.get(atom_id, 0.0)) < 0:
            return True
        # Template hints from registry.
        templates = atom.intervention_templates if atom else []
        for templ in templates:
            if not templ or "?" in templ:
                continue
            key = templ.split()[0].lower()
            if key and key in tactic:
                return True
        # Semantic fallbacks.
        if atom_id in {"unintroduced_forall", "unintroduced_imp"} and ("intro" in tactic or "intros" in tactic):
            return True
        if atom_id == "unsplit_and_target" and "constructor" in tactic:
            return True
        if atom_id == "missing_and_projection" and any(k in tactic for k in ["simp_all", ".left", ".right", "assumption"]):
            return True
        if atom_id == "eq_reflexive_goal" and any(k in tactic for k in ["rfl", "simp"]):
            return True
        if atom_id == "nat_arith_goal" and any(k in tactic for k in ["omega", "norm_num", "linarith", "ring_nf", "simp"]):
            return True
        if atom_id == "list_simp_goal" and "simp" in tactic:
            return True
        if atom_id == "missing_typeclass_instance" and any(k in tactic for k in ["infer_instance", "simp"]):
            return True
        if atom_id == "constructor_branch_debt" and "constructor" in tactic:
            return True
        return False

    @staticmethod
    def _carrier_delta_for(row: dict[str, Any], atom_id: str) -> float:
        cd = row.get("carrier_delta") or {}
        if isinstance(cd, dict):
            return float(cd.get(atom_id, 0.0))
        return 0.0

    def score_atoms(self, audit_rows: list[dict[str, Any]], response_rows: list[dict[str, Any]] | None = None) -> list[CandidateAtomScore]:
        merged = merge_rows_for_mining(audit_rows, response_rows or [])
        all_sigs = [self.signals_for_row(r) for r in merged]
        scores: list[CandidateAtomScore] = []
        by_id = {a.atom_id: a for a in self.seed.atoms}
        for atom in self.seed.atoms:
            vals: list[float] = []
            resp_present: list[float] = []
            resp_absent: list[float] = []
            n_present = 0
            n_addr = 0
            addr_success = 0
            addr_carrier_gain: list[float] = []
            nonaddr_carrier_gain: list[float] = []
            status_success = 0
            for row, sig in zip(merged, all_sigs):
                z = float(sig.get(atom.atom_id, 0.0) > 0)
                vals.append(z)
                norm = self._response_norm(row)
                addressed = self._addresses_atom(row, atom.atom_id, atom)
                carrier_delta = self._carrier_delta_for(row, atom.atom_id)
                if z:
                    n_present += 1
                    status_success += int(self._status(row) == "success")
                    resp_present.append(norm)
                    if addressed:
                        n_addr += 1
                        addr_success += int(self._status(row) == "success" or carrier_delta > 0)
                        addr_carrier_gain.append(max(0.0, carrier_delta))
                    else:
                        nonaddr_carrier_gain.append(max(0.0, carrier_delta))
                else:
                    resp_absent.append(norm)
            support = int(sum(vals))
            if support == 0:
                continue
            mean_present = float(np.mean(resp_present)) if resp_present else 0.0
            mean_absent = float(np.mean(resp_absent)) if resp_absent else 0.0
            response_contrast = mean_present - mean_absent
            fallback_success = float(status_success / max(1, n_present))
            intervention_success = float(addr_success / max(1, n_addr)) if n_addr else fallback_success
            addressed_rate = float(n_addr / max(1, n_present))
            mean_addr_gain = float(np.mean(addr_carrier_gain)) if addr_carrier_gain else 0.0
            mean_nonaddr_gain = float(np.mean(nonaddr_carrier_gain)) if nonaddr_carrier_gain else 0.0
            coker_reduction_proxy = mean_addr_gain - mean_nonaddr_gain
            p = support / max(1, len(vals))
            bootstrap_stability = float(max(0.0, 1.0 - abs(p - 0.5) * 1.2)) if len(vals) >= 4 else float(min(1.0, support / 3.0))
            paid_null_violation = 0.0
            promotion_score = float(response_contrast + 0.5 * intervention_success + 0.5 * max(0.0, coker_reduction_proxy) + 0.25 * addressed_rate - paid_null_violation)
            scores.append(CandidateAtomScore(
                atom_id=atom.atom_id,
                group=atom.group,
                support=support,
                response_contrast=float(response_contrast),
                intervention_success=float(intervention_success),
                bootstrap_stability=float(bootstrap_stability),
                paid_null_violation=float(paid_null_violation),
                coker_reduction_proxy=float(coker_reduction_proxy),
                addressed_rate=float(addressed_rate),
                promotion_score=promotion_score,
                evidence={
                    "mean_response_present": mean_present,
                    "mean_response_absent": mean_absent,
                    "support_fraction": p,
                    "addressed_present_count": n_addr,
                    "addressed_success_count": addr_success,
                    "mean_addressed_carrier_gain": mean_addr_gain,
                    "mean_nonaddressed_carrier_gain": mean_nonaddr_gain,
                    "fallback_success_rate": fallback_success,
                },
            ))
        return scores

    def score(self, audit_rows: list[dict[str, Any]], response_rows: list[dict[str, Any]] | None = None):
        return self.score_and_promote(audit_rows, response_rows)

    def score_and_promote(self, audit_rows: list[dict[str, Any]], response_rows: list[dict[str, Any]] | None = None):
        scores = self.score_atoms(audit_rows, response_rows)
        reg = self.promote(scores, min_support=self.min_support, min_response_contrast=self.response_threshold, min_stability=self.stability_threshold, min_intervention_success=self.min_intervention_success, min_coker_reduction=self.min_coker_reduction)
        return reg, scores

    def promote(self, scores: list[CandidateAtomScore] | tuple[Any, list[CandidateAtomScore]], *, min_support: int = 1, min_response_contrast: float = -1e9, min_stability: float = 0.0, min_intervention_success: float = 0.0, min_coker_reduction: float = -1e9) -> DefectRegistry:
        if isinstance(scores, tuple) and len(scores) == 2:
            scores = scores[1]
        atoms: list[DefectAtom] = []
        by_id = {a.atom_id: a for a in self.seed.atoms}
        for s in scores:
            if s.support < min_support or s.response_contrast < min_response_contrast or s.bootstrap_stability < min_stability or s.intervention_success < min_intervention_success or s.coker_reduction_proxy < min_coker_reduction:
                continue
            base = by_id.get(s.atom_id)
            if not base:
                continue
            d = base.to_dict()
            d["evidence"] = s.to_dict()
            d["status"] = "active"
            atoms.append(DefectAtom(**d))
        return DefectRegistry(atoms=atoms, version="lean-rgc-defect-registry-v0.6", metadata={"source": "auto_mined", "n_scores": len(scores)})


def jsonish(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, sort_keys=True)
    except Exception:
        return str(obj)


def merge_rows_for_mining(audit_rows: list[dict[str, Any]], response_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key = {(str(r.get("state_id")), str(r.get("action_id"))): dict(r) for r in audit_rows or []}
    if response_rows:
        out = []
        for r in response_rows:
            key = (str(r.get("state_id")), str(r.get("action_id")))
            merged = {**by_key.get(key, {}), **r}
            out.append(merged)
        return out
    return audit_rows or []


def mine_defects(audits_path: str, responses_path: str | None, out_registry: str, out_scores: str | None = None, *, min_support: int = 1, min_response_contrast: float = -1e9, min_stability: float = 0.0, min_intervention_success: float = 0.0, min_coker_reduction: float = -1e9) -> DefectRegistry:
    audits = read_jsonl(audits_path) if audits_path else []
    responses = read_jsonl(responses_path) if responses_path else []
    miner = AutoDefectMiner(min_support=min_support, response_threshold=min_response_contrast, stability_threshold=min_stability, min_intervention_success=min_intervention_success, min_coker_reduction=min_coker_reduction)
    scores = miner.score_atoms(audits, responses)
    reg = miner.promote(scores, min_support=min_support, min_response_contrast=min_response_contrast, min_stability=min_stability, min_intervention_success=min_intervention_success, min_coker_reduction=min_coker_reduction)
    reg.save(out_registry)
    if out_scores:
        write_jsonl(out_scores, [s.to_dict() for s in scores])
    return reg


def load_rows_for_mining(audits: str | None = None, responses: str | None = None) -> list[dict[str, Any]]:
    audit_rows = read_jsonl(audits) if audits else []
    resp_rows = read_jsonl(responses) if responses else []
    return merge_rows_for_mining(audit_rows, resp_rows)


SEED_ATOMS = seed_defect_registry().atoms


def mine_defect_registry(audit_rows: list[dict[str, Any]], response_rows: list[dict[str, Any]] | None = None, *, min_support: int = 2, contrast_threshold: float = 0.05) -> dict[str, Any]:
    miner = AutoDefectMiner()
    scores = miner.score_atoms(audit_rows or [], response_rows or [])
    reg = miner.promote(scores, min_support=min_support, min_response_contrast=contrast_threshold, min_stability=0.0)
    return {
        "registry_version": "lean-rgc-autodefect-v0.6",
        "n_rows": len(audit_rows or []),
        "active_atoms": [a.to_dict() for a in reg.atoms],
        "all_scores": [s.to_dict() for s in scores],
        "seed_atoms": [a.to_dict() for a in seed_defect_registry().atoms],
    }


def save_registry(registry: dict[str, Any], out: str | Path) -> None:
    p = Path(out); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(registry, indent=2, ensure_ascii=False), encoding="utf-8")


def load_registry(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def apply_registry_to_rows(registry: dict[str, Any], rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    miner = AutoDefectMiner()
    active = {a.get("atom_id") for a in registry.get("active_atoms", [])}
    out = []
    for r in rows:
        sig = miner.signals_for_row(r)
        vals = {k: float(v) for k, v in sig.items() if k in active}
        rr = dict(r); rr["auto_defects"] = vals
        out.append(rr)
    return out
