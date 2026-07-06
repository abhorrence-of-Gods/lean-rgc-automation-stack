"""S'1 attribution ladder, branch (b): sequential-payment fraction.

Frozen definition (docs/experiments/s_prime_1_middle_layer.md): of
stepwise-closed goals, how many have NO single action in the universe
paying their initial defect while the observed SEQUENCE pays it. If the
fraction exceeds 0.30, linear payability (the one-shot additive cone)
is the binding model error and extend-M_J is barred as a diagnosis.

Operationalization (task granularity, per the prereg's threat note):
- closed task: a success_script chain that completed all steps and whose
  final kernel state reports no remaining goals (or, when the kernel
  payload lacks a goal count, completed unbroken — counted separately).
- single-action payment: the corrected S'0 corpus contains a success
  verdict for the task whose script splits to exactly ONE step.
- sequence-only payment: closed via a >1-step chain with no single-step
  success anywhere in the corrected corpus for that task.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lean_rgc.evals.stepwise_replay import split_script

REPLAY_DIR = ROOT / "runs/s_prime_1/s1_stepwise_rerun"


def load_corrected_success_pairs() -> dict[str, list[str]]:
    verd_dir = ROOT / "runs/s0_reaudit"
    demo = {(d["task_id"], d["script"].strip())
            for d in json.loads((verd_dir / "defect6_demotions.json").read_text(encoding="utf-8"))}
    by_task: dict[str, list[str]] = {}
    for sf in sorted(verd_dir.glob("verdicts_shard*.json")):
        for v in json.loads(sf.read_text(encoding="utf-8")):
            key = (v["task_id"], v["script"].strip())
            if v["status"] == "success" and key not in demo:
                by_task.setdefault(v["task_id"], []).append(v["script"].strip())
    return by_task


def chain_closed(chain: dict, last_ks: dict | None) -> tuple[bool, str]:
    if chain.get("broken") or chain.get("completed_steps") != chain.get("n_steps"):
        return False, "incomplete"
    if last_ks is None:
        return True, "completed_no_kernel_goalcount"
    for key in ("closed", "is_closed"):
        if isinstance(last_ks.get(key), bool):
            return last_ks[key], f"kernel_{key}"
    for key in ("num_goals", "n_goals"):
        if key in last_ks:
            return float(last_ks[key]) == 0.0, f"kernel_{key}"
    goals = last_ks.get("goals")
    if isinstance(goals, list):
        return len(goals) == 0, "kernel_goals_list"
    return True, "completed_no_kernel_goalcount"


def main() -> None:
    chains = [json.loads(l) for l in open(REPLAY_DIR / "chains.jsonl", encoding="utf-8")]
    trans = [json.loads(l) for l in open(REPLAY_DIR / "stepwise_transitions.jsonl", encoding="utf-8")]
    last_ks_by_script: dict[int, dict | None] = {}
    steps_by_script: dict[int, int] = {}
    for t in trans:
        si = t["script_index"]
        if t["step_index"] >= steps_by_script.get(si, -1):
            steps_by_script[si] = t["step_index"]
            last_ks_by_script[si] = t.get("kernel_state_after")

    singles = load_corrected_success_pairs()
    single_step_tasks = {
        task for task, scripts in singles.items()
        if any(len(split_script(s)) == 1 for s in scripts)
    }

    closed, seq_only, evidence_mode = [], [], {}
    for si, ch in enumerate(chains):
        if ch.get("source") != "success_script":
            continue
        ok, mode = chain_closed(ch, last_ks_by_script.get(si))
        evidence_mode[mode] = evidence_mode.get(mode, 0) + 1
        if not ok:
            continue
        closed.append(ch)
        if ch["n_steps"] > 1 and ch["task_id"] not in single_step_tasks:
            seq_only.append(ch)

    n = len(closed)
    frac = (len(seq_only) / n) if n else float("nan")
    report = {
        "n_closed_tasks": n,
        "n_sequence_only": len(seq_only),
        "sequential_payment_fraction": round(frac, 4) if n else None,
        "threshold": 0.30,
        "verdict": ("LINEAR-PAYABILITY-BINDING" if n and frac > 0.30 else
                    "NOT-BINDING" if n else "NO-CLOSED-TASKS"),
        "small_n_caveat": n < 30,
        "closure_evidence_modes": evidence_mode,
        "sequence_only_tasks": [
            {"task_id": c["task_id"], "n_steps": c["n_steps"]} for c in seq_only
        ],
        "chains_total": len(chains),
        "transitions_total": len(trans),
        "v3_payload_transitions": sum(1 for t in trans if t.get("kernel_state_after")),
        "registered_transition_gate": 1141,
    }
    out = REPLAY_DIR / "model_error_report.json"
    out.write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
