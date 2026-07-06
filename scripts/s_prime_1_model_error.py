"""S'1 attribution ladder, branch (b) — Amendment b instruments.

BINDING instrument (additivity test): realized chain payment
P = defect(root) - defect(S_last) is exactly the telescoped sum of
per-step responses; the cone's structural assumption replaces each
step response by the tactic's state-marginalized global mean Rbar.
Linear payability is BINDING if the median relative error
||P - sum_k Rbar(tactic_k)|| / max(||P||, 1e-6) over covered chains
exceeds 0.50 (tactics with < 3 occurrences excluded; chains with
< 80% step coverage skipped, coverage reported).

DESCRIPTIVE (original rung-(b) fraction, ceiling 3/28 disclosed):
closed success-script chains whose task has no 1-step success in the
corrected corpus.

Defect granularity: kernel-provided goal target_texts only (no message
text); a closed kernel state (no goals) is the zero defect vector.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lean_rgc.defects import ProofDefectExtractor
from lean_rgc.evals.stepwise_replay import split_script
from lean_rgc.schemas import LeanTask, ProofState, stable_hash

REPLAY_DIR = ROOT / "runs/s_prime_1/s1_stepwise_rerun2"
EXTRACTOR = ProofDefectExtractor()


def kernel_goal_texts(ks: dict | None) -> list[str] | None:
    if not isinstance(ks, dict):
        return None
    goals = ks.get("goals")
    if not isinstance(goals, list):
        return None
    texts = []
    for g in goals:
        if isinstance(g, dict):
            texts.append(str(g.get("target_text") or g.get("pp") or g.get("raw") or ""))
    return texts


def defect_of_goals(task_id: str, texts: list[str]) -> np.ndarray:
    if not texts or all(not t.strip() for t in texts):
        return np.zeros(DIM)
    goals_text = "\n\n".join(f"⊢ {t}" for t in texts)
    st = ProofState(
        state_id=stable_hash({"task_id": task_id, "kernel_goals": goals_text[:4000]}),
        task_id=task_id, goals_text=goals_text, target=texts[0], raw_messages=[],
    )
    return np.asarray(EXTRACTOR.extract(st).flat, dtype=float)


def main() -> None:
    global DIM
    taskdefs = {}
    for line in open(ROOT / "runs/s_prime_1/minif2f_test_tasks.jsonl", encoding="utf-8"):
        d = json.loads(line)
        taskdefs[d["task_id"]] = LeanTask.from_dict(d)
    probe = EXTRACTOR.extract(ProofState.from_task(next(iter(taskdefs.values()))))
    DIM = len(probe.flat)

    chains = [json.loads(l) for l in open(REPLAY_DIR / "chains.jsonl", encoding="utf-8")]
    trans = [json.loads(l) for l in open(REPLAY_DIR / "stepwise_transitions.jsonl", encoding="utf-8")]
    by_script: dict[int, list[dict]] = defaultdict(list)
    for t in trans:
        by_script[t["script_index"]].append(t)
    for v in by_script.values():
        v.sort(key=lambda t: t["step_index"])

    root_cache: dict[str, np.ndarray] = {}

    def root_vec(task_id: str) -> np.ndarray:
        if task_id not in root_cache:
            root_cache[task_id] = np.asarray(
                EXTRACTOR.extract(ProofState.from_task(taskdefs[task_id])).flat, dtype=float)
        return root_cache[task_id]

    # ---- per-step responses at kernel granularity --------------------------
    step_resp: list[tuple[str, int, str, np.ndarray]] = []  # (tactic, si, task, response)
    chain_steps: dict[int, list[tuple[str, np.ndarray]]] = defaultdict(list)
    for si, steps in by_script.items():
        task_id = steps[0]["task_id"]
        prev = root_vec(task_id)
        for t in steps:
            if t["status"] not in ("success", "partial"):
                break
            texts = kernel_goal_texts(t.get("kernel_state_after"))
            if texts is None:
                break
            cur = defect_of_goals(task_id, texts)
            resp = prev - cur
            tac = t["tactic"].strip()
            step_resp.append((tac, si, task_id, resp))
            chain_steps[si].append((tac, resp))
            prev = cur

    by_tactic: dict[str, list[np.ndarray]] = defaultdict(list)
    for tac, _, _, resp in step_resp:
        by_tactic[tac].append(resp)
    rbar = {tac: np.mean(v, axis=0) for tac, v in by_tactic.items() if len(v) >= 3}

    rel_errors, skipped_cov, covered = [], 0, 0
    for si, steps in chain_steps.items():
        if not steps:
            continue
        have = [tac in rbar for tac, _ in steps]
        if sum(have) / len(steps) < 0.8:
            skipped_cov += 1
            continue
        P = np.sum([r for _, r in steps], axis=0)
        P_hat = np.sum([rbar[tac] for tac, _ in steps if tac in rbar], axis=0)
        rel_errors.append(float(np.linalg.norm(P - P_hat) / max(np.linalg.norm(P), 1e-6)))
        covered += 1
    median_err = float(np.median(rel_errors)) if rel_errors else None
    (REPLAY_DIR / "rel_errors.json").write_text(json.dumps(rel_errors), encoding="utf-8")

    # secondary: per-tactic dispersion (1 - R^2 vs global mean), >=5 occurrences
    dispersion = {}
    for tac, v in by_tactic.items():
        if len(v) < 5:
            continue
        M = np.vstack(v)
        ss_tot = float(np.sum((M - M.mean(axis=0)) ** 2)) + float(np.sum(M.mean(axis=0) ** 2)) * len(v)
        ss_res = float(np.sum((M - M.mean(axis=0)) ** 2))
        dispersion[tac] = round(ss_res / max(ss_tot, 1e-9), 4)

    # ---- descriptive: original sequential fraction -------------------------
    demo = {(d["task_id"], d["script"].strip())
            for d in json.loads((ROOT / "runs/s0_reaudit/defect6_demotions.json").read_text(encoding="utf-8"))}
    singles_by_task: dict[str, bool] = defaultdict(bool)
    for sf in sorted((ROOT / "runs/s0_reaudit").glob("verdicts_shard*.json")):
        for v in json.loads(sf.read_text(encoding="utf-8")):
            key = (v["task_id"], v["script"].strip())
            if v["status"] == "success" and key not in demo and len(split_script(v["script"])) == 1:
                singles_by_task[v["task_id"]] = True
    closed, seq_only, closure_modes = 0, 0, defaultdict(int)
    for ch in chains:
        if ch.get("source") != "success_script" or ch.get("broken") or ch["completed_steps"] != ch["n_steps"]:
            continue
        steps = by_script.get(ch.get("script_index"), [])
        texts = kernel_goal_texts(steps[-1].get("kernel_state_after")) if steps else None
        if texts is None:
            closure_modes["no_kernel_payload_NOT_closed"] += 1
            continue
        if len([t for t in texts if t.strip()]) > 0:
            closure_modes["kernel_goals_remain"] += 1
            continue
        closure_modes["kernel_closed"] += 1
        closed += 1
        if ch["n_steps"] > 1 and not singles_by_task[ch["task_id"]]:
            seq_only += 1

    # ---- gate accounting ----------------------------------------------------
    summary = json.loads((REPLAY_DIR / "replay_summary.json").read_text(encoding="utf-8"))
    strict = summary["counts"].get("v3_success_transitions", 0)
    shortfall = []
    for ch in chains:
        miss = ch["n_steps"] - ch["completed_steps"]
        if miss > 0:
            shortfall.append({"task_id": ch["task_id"], "source": ch.get("source"),
                              "missing_steps": miss, "error": (ch.get("error") or "")[:80]})
    shortfall.sort(key=lambda x: -x["missing_steps"])

    report = {
        "gate": {"strict_v3_transitions": strict, "registered_gate": 1139,
                 "gate_met": strict >= 1139,
                 "shortfall_total_steps": sum(s["missing_steps"] for s in shortfall),
                 "top_broken": shortfall[:8]},
        "additivity_test": {
            "n_chains_covered": covered, "n_skipped_low_coverage": skipped_cov,
            "n_tactics_with_rbar": len(rbar),
            "median_relative_error": round(median_err, 4) if median_err is not None else None,
            "threshold": 0.50,
            "verdict": ("LINEAR-PAYABILITY-BINDING" if median_err is not None and median_err > 0.50
                        else "NOT-BINDING" if median_err is not None else "NO-DATA"),
            "rel_error_quartiles": [round(float(q), 4) for q in np.percentile(rel_errors, [25, 50, 75])] if rel_errors else None,
        },
        "per_tactic_dispersion_1minusR2": dict(sorted(dispersion.items(), key=lambda kv: -kv[1])[:15]),
        "descriptive_sequential_fraction": {
            "n_closed": closed, "n_sequence_only": seq_only,
            "fraction": round(seq_only / closed, 4) if closed else None,
            "ceiling_disclosed": "3/28; descriptive only per Amendment b",
            "closure_evidence": dict(closure_modes),
        },
    }
    out = REPLAY_DIR / "model_error_report.json"
    out.write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
