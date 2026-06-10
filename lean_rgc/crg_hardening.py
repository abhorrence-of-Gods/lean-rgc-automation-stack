from __future__ import annotations

from pathlib import Path
from typing import Any
import json

from .schemas import read_jsonl, stable_hash, write_records


SCHEMA_CRG_HARDENING = "lean-rgc-hardening-attempt-v59.0"


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


def _support(candidate: dict[str, Any]) -> list[dict[str, Any]]:
    relaxed = candidate.get("relaxed_object") if isinstance(candidate.get("relaxed_object"), dict) else {}
    rows = [r for r in (relaxed.get("support") or []) if isinstance(r, dict)]
    return sorted(rows, key=lambda r: (float(r.get("weight") or 0.0), float(r.get("predicted_score") or 0.0)), reverse=True)


def _action_from_support(candidate: dict[str, Any], supp: dict[str, Any], *, suffix: str, tactic: str | None = None) -> dict[str, Any]:
    tactic = str(tactic if tactic is not None else (supp.get("tactic") or "skip"))
    hid = "crg_hardened_" + stable_hash({"candidate": candidate.get("candidate_id"), "suffix": suffix, "tactic": tactic}, 14)
    return {
        "action_id": hid,
        "tactic": tactic,
        "tactic_class": "crg_hardened",
        "carrier_tags": ["crg", str(supp.get("species_id") or "mixed")],
        "cost_estimate": float((supp.get("cost_vector") or {}).get("cost") or 1.0),
        "metadata": {
            "source": "crg_hardening",
            "candidate_id": candidate.get("candidate_id"),
            "problem_id": candidate.get("problem_id"),
            "support_repair_atom_id": supp.get("repair_atom_id"),
            "support_weight": supp.get("weight"),
            "hardening_method": "mixture_to_beam" if suffix.startswith("beam") else "mixture_to_sequence",
            "canonical_status": "hard_candidate_witness_not_canonical",
        },
    }


def harden_crg_candidates(
    *,
    candidates_path: str | Path,
    out_attempts: str | Path,
    out_actions: str | Path | None = None,
    summary_out: str | Path | None = None,
    method: str = "mixture_to_beam",
    top_k: int = 3,
    include_sequence: bool = True,
    run_id: str | None = None,
    parent_ids: list[str] | None = None,
) -> dict[str, Any]:
    candidates = _read_rows(candidates_path)
    attempts: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    seen_actions: set[str] = set()
    for cand in candidates:
        support = [s for s in _support(cand) if str(s.get("tactic") or "").strip()]
        hard: list[dict[str, Any]] = []
        for i, supp in enumerate(support[: max(0, int(top_k))]):
            action = _action_from_support(cand, supp, suffix=f"beam_{i}")
            hard.append(
                {
                    "action_id": action["action_id"],
                    "tactic": action["tactic"],
                    "cost_estimate": action["cost_estimate"],
                    "source_support": supp,
                }
            )
            if action["action_id"] not in seen_actions:
                actions.append(action)
                seen_actions.add(action["action_id"])
        if include_sequence and len(support) >= 2:
            seq_tactics = []
            for supp in support[: max(2, min(int(top_k), 4))]:
                tactic = str(supp.get("tactic") or "").strip()
                if tactic and tactic not in seq_tactics:
                    seq_tactics.append(tactic)
            if seq_tactics:
                seq = "; ".join(seq_tactics)
                action = _action_from_support(cand, support[0], suffix="sequence", tactic=seq)
                hard.append(
                    {
                        "action_id": action["action_id"],
                        "tactic": action["tactic"],
                        "cost_estimate": action["cost_estimate"],
                        "source_support": support[: len(seq_tactics)],
                    }
                )
                if action["action_id"] not in seen_actions:
                    actions.append(action)
                    seen_actions.add(action["action_id"])
        relaxed_score = float(((cand.get("scores") or {}).get("lambda_response") or 0.0))
        best_support = max([float(s.get("predicted_score") or 0.0) for s in support], default=0.0)
        gap = max(0.0, relaxed_score - best_support)
        attempts.append(
            {
                "schema_version": SCHEMA_CRG_HARDENING,
                "hardening_id": "hard_" + stable_hash({"candidate": cand.get("candidate_id"), "hard": hard}, 16),
                "candidate_id": cand.get("candidate_id"),
                "problem_id": cand.get("problem_id"),
                "relaxed_object_id": cand.get("candidate_id"),
                "hardening_method": method,
                "hard_candidates": hard,
                "hardening_status": "decoded" if hard else "failed",
                "hardening_gap": float(gap),
                "canonical_status": "hardening_witness_not_canonical",
            }
        )
    write_records(out_attempts, attempts, schema_version=SCHEMA_CRG_HARDENING, run_id=run_id, parent_ids=parent_ids)
    if out_actions:
        write_records(out_actions, actions, schema_version=SCHEMA_CRG_HARDENING, run_id=run_id, parent_ids=parent_ids)
    summary = {
        "schema_version": SCHEMA_CRG_HARDENING,
        "candidates": str(candidates_path),
        "out_attempts": str(out_attempts),
        "out_actions": str(out_actions) if out_actions else None,
        "n_candidates": len(candidates),
        "n_attempts": len(attempts),
        "n_hard_actions": len(actions),
        "method": method,
        "canonical_status": "hardening_outputs_are_witnesses_not_canonical",
    }
    if summary_out:
        _json_dump(summary, summary_out)
    return summary


__all__ = ["SCHEMA_CRG_HARDENING", "harden_crg_candidates"]
