from __future__ import annotations

from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any
import json
import re

from .schemas import LeanTask, TacticAction, read_jsonl, write_jsonl, stable_hash, ProofState
from .goal_shape import parse_goal_shape, extract_hypotheses


def _row_text(row: dict[str, Any]) -> str:
    parts: list[str] = []
    for k in ["target", "goals_text", "stdout", "stderr"]:
        if row.get(k):
            parts.append(str(row.get(k)))
    for m in row.get("messages", []) or []:
        parts.append(str(m))
    a = row.get("action")
    if isinstance(a, dict):
        parts.append(str(a.get("tactic", "")))
        if isinstance(a.get("metadata"), dict):
            parts.append(json.dumps(a.get("metadata"), ensure_ascii=False, sort_keys=True)[:1000])
    aft = row.get("after_state")
    if isinstance(aft, dict):
        parts.extend([str(aft.get("target", "")), str(aft.get("goals_text", ""))])
        for m in aft.get("raw_messages", []) or []:
            parts.append(str(m))
    return "\n".join(p for p in parts if p)


def _status(row: dict[str, Any]) -> str:
    return str(row.get("status") or row.get("audit_status") or "unknown")


def _action_tactic(row: dict[str, Any]) -> str:
    a = row.get("action")
    if isinstance(a, dict):
        return str(a.get("tactic") or row.get("tactic") or "")
    return str(row.get("tactic") or "")


def _response_norm(row: dict[str, Any]) -> float:
    try:
        vals = row.get("response_flat")
        if isinstance(vals, list):
            return float(sum(float(x) * float(x) for x in vals) ** 0.5)
        resp = row.get("response") or {}
        if isinstance(resp, dict):
            return float(sum(float(v) * float(v) for v in resp.values()) ** 0.5)
    except Exception:
        pass
    return 0.0


def _carrier_delta_l1(row: dict[str, Any]) -> float:
    cd = row.get("carrier_delta") or {}
    if not isinstance(cd, dict):
        return 0.0
    total = 0.0
    for v in cd.values():
        try:
            total += max(0.0, float(v))
        except Exception:
            pass
    return float(total)


@dataclass
class FailureSignature:
    signature_id: str
    kind: str
    group: str
    carrier_atoms: list[str] = field(default_factory=list)
    support: int = 0
    status_counts: dict[str, int] = field(default_factory=dict)
    mean_response_norm: float = 0.0
    mean_carrier_gain: float = 0.0
    suggested_tactics: list[str] = field(default_factory=list)
    examples: list[dict[str, Any]] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FailureSignatureResult:
    signatures: list[FailureSignature]
    actions: list[dict[str, Any]]
    summary: dict[str, Any]


class FailureSignatureMiner:
    """Mine actionable failure signatures from Lean micro-audit rows.

    This is a chart-level miner.  It does not certify canonical defects; it
    groups recurring failure patterns, assigns likely carrier atoms, and emits
    tactic contexts that must be micro-audited before acceptance.
    """

    def __init__(self, *, min_support: int = 1, max_examples: int = 5):
        self.min_support = int(min_support)
        self.max_examples = int(max_examples)

    def classify_row(self, row: dict[str, Any]) -> dict[str, Any]:
        text = _row_text(row)
        low = text.lower()
        task = LeanTask(task_id=str(row.get("task_id") or "task"), statement=str(row.get("target") or row.get("statement") or ""), imports=[])
        state = ProofState(state_id=str(row.get("state_id") or "state"), task_id=task.task_id, target=task.statement, goals_text=str(row.get("goals_text") or ""), raw_messages=[str(m) for m in (row.get("messages") or [])])
        shape = parse_goal_shape(task=task, state=state, extra=text)
        tactic = _action_tactic(row).lower()
        status = _status(row)
        carrier_atoms: list[str] = []
        tactics: list[str] = []
        kind = "generic_failure"
        group = "unknown"

        if shape.has_forall or shape.has_imp or "⊢ ∀" in text or "forall" in low:
            if "rfl failed" in low or "expected the goal to be a binary relation" in low or "rfl" in tactic:
                kind = "rfl_before_intro"; group = "exposure"
            else:
                kind = "unintroduced_binder"; group = "exposure"
            carrier_atoms += ["unintroduced_forall" if shape.has_forall else "unintroduced_imp"]
            tactics += ["intros\nrfl", "intros\nsimp", "intros\nsimp_all", "intros\nomega"]
        elif shape.target_is_and:
            kind = "unsplit_and_target"; group = "exposure"
            carrier_atoms += ["unsplit_and_target", "constructor_branch_debt"]
            tactics += ["constructor <;> simp_all", "constructor <;> assumption"]
        elif shape.has_and_hyp:
            kind = "and_hyp_projection_needed"; group = "premise"
            carrier_atoms += ["missing_and_projection", "missing_premise_family"]
            tactics += ["simp_all"]
            for h in extract_hypotheses(text)[:4]:
                nm = h.get("name")
                typ = h.get("type", "")
                if nm and ("∧" in typ or "And" in typ or "/\\" in typ):
                    tactics += [f"exact {nm}.left", f"exact {nm}.right", f"have {nm}_left := {nm}.left\nhave {nm}_right := {nm}.right\nsimp_all"]
        elif "failed to synthesize" in low or "typeclass" in low:
            kind = "typeclass_synthesis_failure"; group = "typeclass"
            carrier_atoms += ["missing_typeclass_instance"]
            tactics += ["infer_instance", "exact inferInstance", "simp"]
        elif "unknown identifier" in low:
            kind = "unknown_identifier_or_missing_premise"; group = "premise"
            carrier_atoms += ["missing_premise_family"]
            tactics += ["simp_all", "assumption"]
        elif shape.has_arith or "omega" in low or "linarith" in low or "norm_num" in low:
            kind = "arith_backend_needed"; group = "arithmetic"
            carrier_atoms += ["nat_arith_goal", "missing_domain_tactic"]
            tactics += ["omega", "norm_num", "simp", "linarith"]
        elif "unsolved goals" in low or status == "partial":
            kind = "partial_progress_tail"; group = "search"
            carrier_atoms += ["constructor_branch_debt", "missing_premise_family"]
            tactics += ["simp_all", "assumption", "constructor <;> simp_all"]
        elif "timeout" in low or status == "timeout":
            kind = "timeout_or_search_tail"; group = "audit"
            carrier_atoms += ["proof_tail_branching", "audit_timeout_risk"]
            tactics += ["simp", "simp_all"]
        elif shape.target_is_eq or "rfl failed" in low:
            kind = "equality_closure_failure"; group = "equality"
            carrier_atoms += ["eq_reflexive_goal", "missing_rewrite_orientation"]
            tactics += ["rfl", "simp", "simp_all"]
        else:
            if status in {"success", "dry_run"}:
                kind = "non_failure_response"; group = "response"
            carrier_atoms += []
            tactics += ["simp", "simp_all", "assumption"]

        # Deduplicate and remove empty tactics.
        tactics = [t for i, t in enumerate(tactics) if t.strip() and t not in tactics[:i]]
        carrier_atoms = [a for i, a in enumerate(carrier_atoms) if a and a not in carrier_atoms[:i]]
        sig_id = stable_hash({"kind": kind, "atoms": carrier_atoms, "group": group}, 12)
        return {"signature_id": sig_id, "kind": kind, "group": group, "carrier_atoms": carrier_atoms, "suggested_tactics": tactics, "shape": shape.to_dict()}

    def mine(self, audit_rows: list[dict[str, Any]], response_rows: list[dict[str, Any]] | None = None) -> FailureSignatureResult:
        resp_by_key: dict[tuple[str, str], dict[str, Any]] = {}
        for r in response_rows or []:
            resp_by_key[(str(r.get("state_id")), str(r.get("action_id")))] = r
        buckets: dict[str, list[tuple[dict[str, Any], dict[str, Any], dict[str, Any] | None]]] = {}
        for row in audit_rows:
            cls = self.classify_row(row)
            rr = resp_by_key.get((str(row.get("state_id")), str(row.get("action_id"))))
            buckets.setdefault(cls["signature_id"], []).append((cls, row, rr))
        signatures: list[FailureSignature] = []
        action_rows: list[dict[str, Any]] = []
        for sig_id, triples in buckets.items():
            if len(triples) < self.min_support:
                continue
            cls0 = triples[0][0]
            statuses: dict[str, int] = {}
            resp_norms: list[float] = []
            carrier_gains: list[float] = []
            examples: list[dict[str, Any]] = []
            for cls, row, rr in triples:
                st = _status(row)
                statuses[st] = statuses.get(st, 0) + 1
                if rr is not None:
                    resp_norms.append(_response_norm(rr))
                    carrier_gains.append(_carrier_delta_l1(rr))
                if len(examples) < self.max_examples:
                    examples.append({
                        "task_id": row.get("task_id"),
                        "state_id": row.get("state_id"),
                        "action_id": row.get("action_id"),
                        "status": st,
                        "tactic": _action_tactic(row),
                        "message": (row.get("messages") or [row.get("stderr") or row.get("stdout") or ""])[0] if (row.get("messages") or row.get("stderr") or row.get("stdout")) else "",
                    })
            signatures.append(FailureSignature(
                signature_id=sig_id,
                kind=str(cls0["kind"]),
                group=str(cls0["group"]),
                carrier_atoms=list(cls0.get("carrier_atoms") or []),
                support=len(triples),
                status_counts=statuses,
                mean_response_norm=float(sum(resp_norms) / len(resp_norms)) if resp_norms else 0.0,
                mean_carrier_gain=float(sum(carrier_gains) / len(carrier_gains)) if carrier_gains else 0.0,
                suggested_tactics=list(cls0.get("suggested_tactics") or []),
                examples=examples,
                evidence={"source": "failure_signature_miner", "mined_from_rows": len(triples)},
            ))
            # Generate task-specific auditable actions from examples, not from cluster alone.
            for _, row, _ in triples:
                task_id = str(row.get("task_id") or "")
                if not task_id:
                    continue
                for tact in cls0.get("suggested_tactics") or []:
                    meta = {"generated_by": "failure_signature_miner", "signature_id": sig_id, "signature_kind": cls0["kind"], "carrier_atoms": cls0.get("carrier_atoms") or [], "source_state_id": row.get("state_id")}
                    aid = stable_hash({"task": task_id, "sig": sig_id, "tactic": tact}, 14)
                    action = TacticAction(action_id=aid, tactic=tact, tactic_class=str(cls0["group"]), carrier_tags=list(cls0.get("carrier_atoms") or []) + [str(cls0["group"])], cost_estimate=0.65, metadata=meta).to_dict()
                    action["task_id"] = task_id
                    action.setdefault("metadata", {})["task_id"] = task_id
                    action_rows.append(action)
        # Deduplicate actions by task/tactic.
        dedup: dict[tuple[str, str], dict[str, Any]] = {}
        for a in action_rows:
            dedup.setdefault((str(a.get("task_id")), str(a.get("tactic"))), a)
        action_rows = list(dedup.values())
        signatures.sort(key=lambda s: (-s.support, s.kind))
        summary = {
            "n_signatures": len(signatures),
            "n_actions": len(action_rows),
            "support_total": int(sum(s.support for s in signatures)),
            "top": [s.to_dict() for s in signatures[:10]],
        }
        return FailureSignatureResult(signatures=signatures, actions=action_rows, summary=summary)


def mine_failure_signatures(audits: str | Path, out: str | Path, *, responses: str | Path | None = None, actions_out: str | Path | None = None, summary_out: str | Path | None = None, min_support: int = 1) -> FailureSignatureResult:
    audit_rows = read_jsonl(audits)
    response_rows = read_jsonl(responses) if responses else []
    res = FailureSignatureMiner(min_support=min_support).mine(audit_rows, response_rows)
    write_jsonl(out, [s.to_dict() for s in res.signatures])
    if actions_out:
        write_jsonl(actions_out, res.actions)
    if summary_out:
        Path(summary_out).parent.mkdir(parents=True, exist_ok=True)
        Path(summary_out).write_text(json.dumps(res.summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return res


__all__ = ["FailureSignature", "FailureSignatureResult", "FailureSignatureMiner", "mine_failure_signatures"]
