from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import json

from .schemas import TacticAction, read_jsonl, write_jsonl, stable_hash


def _class_and_tags(tactic: str, context_kind: str = "") -> tuple[str, list[str]]:
    low = (tactic or "").lower()
    kind = (context_kind or "generated").lower()
    tags = ["carrier_promoted"]
    if kind:
        tags.append(kind)
    cls = "generated"
    if "simp" in low:
        cls = "simp"; tags.append("simp")
    if "intro" in low:
        cls = "intro"; tags.extend(["intro", "exposure"])
    if "constructor" in low:
        cls = "constructor"; tags.append("constructor")
    if "rw" in low:
        cls = "rewrite"; tags.append("rewrite")
    if "apply" in low:
        cls = "apply"; tags.append("premise")
    if "exact" in low or "assumption" in low:
        cls = "exact"; tags.append("premise")
    if any(k in low for k in ["omega", "linarith", "norm_num", "ring_nf"]):
        cls = "arithmetic"; tags.extend(["arithmetic", "nat"])
    if "induction" in low:
        cls = "induction"; tags.append("induction")
    # Carry context kind atoms into tags for carrier coker coverage.
    aliases = {
        "carrier_exposure": ["unintroduced_forall", "unintroduced_imp", "exposure"],
        "constructor_exposure": ["unsplit_and_target", "constructor"],
        "premise_projection": ["missing_and_projection", "premise"],
        "equality_closure": ["eq_reflexive_goal", "rfl"],
        "arithmetic_context": ["nat_arith_goal", "arithmetic"],
        "list_simp_context": ["list_simp_goal", "simp"],
        "branch_closure": ["constructor_branch_debt", "constructor"],
        "induction_scheme": ["missing_induction_scheme", "induction"],
        "simp_set_extension": ["missing_simp_lemma", "simp"],
        "rewrite_orientation_search": ["missing_rewrite_orientation", "rewrite"],
        "premise_retrieval": ["missing_premise_family", "premise"],
        "typeclass_context": ["missing_typeclass_instance", "typeclass"],
        "domain_tactic": ["missing_domain_tactic", "arithmetic"],
    }
    tags.extend(aliases.get(kind, []))
    # Deduplicate preserving order.
    out: list[str] = []
    for t in tags:
        if t and t not in out:
            out.append(t)
    return cls, out


@dataclass
class CarrierPromotionSummary:
    n_rows: int
    n_accepted_rows: int
    n_actions: int
    min_margin: float
    by_kind: dict[str, dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def accepted_carrier_actions(
    accepted_path: str | Path,
    *,
    min_margin: float = 0.0,
    accepted_only: bool = True,
) -> tuple[list[dict[str, Any]], CarrierPromotionSummary]:
    """Convert accepted carrier-audit rows to reusable tactic action rows.

    The result is a finite carrier-generator chart.  It should be re-audited in
    new states before being treated as a response certificate.
    """
    rows = read_jsonl(accepted_path)
    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    by_kind: dict[str, dict[str, Any]] = {}
    n_acc = 0
    for r in rows:
        margin = float(r.get("coker_margin_proxy", 0.0))
        is_acc = bool(r.get("accepted"))
        if accepted_only and not is_acc:
            continue
        if margin < min_margin:
            continue
        n_acc += 1
        task_id = str(r.get("task_id") or "")
        tactic = str(r.get("tactic") or "").strip()
        if not tactic:
            continue
        kind = str(r.get("context_kind") or "carrier_generated")
        cls, tags = _class_and_tags(tactic, kind)
        residual_atoms = list(map(str, r.get("residual_atoms") or []))
        for atom in residual_atoms:
            if atom and atom not in tags:
                tags.append(atom)
        aid = stable_hash({"carrier_promoted": True, "task_id": task_id, "tactic": tactic, "kind": kind, "atoms": residual_atoms}, 14)
        meta = {
            "generated_by": "carrier_acceptance_promotion",
            "carrier_context_kind": kind,
            "carrier_acceptance_margin": margin,
            "carrier_delta_l1": float(r.get("carrier_delta_l1", 0.0)),
            "carrier_residual_l1_before": float(r.get("carrier_residual_l1_before", 0.0)),
            "carrier_residual_l1_after": float(r.get("carrier_residual_l1_after", 0.0)),
            "residual_atoms": residual_atoms,
            "source_action_id": str(r.get("action_id") or ""),
            "source_status": str(r.get("status") or ""),
            "task_id": task_id,
        }
        cost = max(0.05, float(r.get("cost", 1.0)) * 0.9)
        row = TacticAction(action_id=aid, tactic=tactic, tactic_class=cls, carrier_tags=tags, cost_estimate=cost, metadata=meta).to_dict()
        row["task_id"] = task_id
        # Keep best margin for duplicate (task,tactic).
        key = (task_id, tactic)
        old = by_key.get(key)
        if old is None or margin > float((old.get("metadata") or {}).get("carrier_acceptance_margin", -1e9)):
            by_key[key] = row
        d = by_kind.setdefault(kind, {"rows": 0, "accepted_rows": 0, "actions": 0, "mean_margin": 0.0})
        d["rows"] += 1
        d["accepted_rows"] += int(is_acc)
        d["mean_margin"] += margin
    actions = list(by_key.values())
    # Stable ordering: task-specific first, then margin desc, cost asc.
    actions.sort(key=lambda x: (str(x.get("task_id") or ""), -float((x.get("metadata") or {}).get("carrier_acceptance_margin", 0.0)), float(x.get("cost_estimate", 1.0)), str(x.get("tactic", ""))))
    for d in by_kind.values():
        d["actions"] = 0
        if d["rows"]:
            d["mean_margin"] /= d["rows"]
    for a in actions:
        k = str((a.get("metadata") or {}).get("carrier_context_kind", "unknown"))
        by_kind.setdefault(k, {"rows": 0, "accepted_rows": 0, "actions": 0, "mean_margin": 0.0})["actions"] += 1
    return actions, CarrierPromotionSummary(n_rows=len(rows), n_accepted_rows=n_acc, n_actions=len(actions), min_margin=float(min_margin), by_kind=by_kind)


def write_accepted_carrier_actions(
    accepted_path: str | Path,
    out: str | Path,
    *,
    report_out: str | Path | None = None,
    min_margin: float = 0.0,
    accepted_only: bool = True,
) -> dict[str, Any]:
    actions, summary = accepted_carrier_actions(accepted_path, min_margin=min_margin, accepted_only=accepted_only)
    write_jsonl(out, actions)
    rep = summary.to_dict()
    if report_out:
        Path(report_out).parent.mkdir(parents=True, exist_ok=True)
        Path(report_out).write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")
    return rep
