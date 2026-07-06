"""S'1 registered gate: does phi_true predict future unpaid defect fractions?

Implements docs/experiments/s_prime_1_middle_layer.md (FROZEN 2026-07-06):
- FIT side: pilot-src pairs from the S'0 isolated re-audit (corrected labels),
  failure-side after-states re-parsed from stored messages (correction (g));
  synthetic after-states never enter any chart.
- SCORE side: G1-era wave rows (g1_prod_train + g1re3_train) restricted to
  train tasks with zero pilot rows.
- Primary: Spearman rho(u_hat, u) vs the ||D|| baseline; PASS requires
  rho_phi - rho_baseline >= 0.10 with bootstrap 95% CI excluding zero.
- Scale-ablation: primary uses 1/std scaling (z-score centering would break
  the cone's zero-defect semantics — disclosed); re-run under raw units and
  log-only; verdict must be invariant or UNSTABLE-UNITS.
"""
from __future__ import annotations

import json
import sys
import tarfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lean_rgc.coker import project_onto_response_cone
from lean_rgc.defects import ProofDefectExtractor
from lean_rgc.lean.state_parser import LeanMessageParser
from lean_rgc.schemas import LeanTask, ProofState, stable_hash

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "runs/s_prime_1"
EXTRACTOR = ProofDefectExtractor()
PARSER = LeanMessageParser()


def load_taskdefs() -> dict[str, LeanTask]:
    out = {}
    for line in open(OUT / "minif2f_test_tasks.jsonl", encoding="utf-8"):
        d = json.loads(line)
        out[d["task_id"]] = LeanTask.from_dict(d)
    return out


def load_corrected_verdicts() -> dict[tuple[str, str], str]:
    verd = {}
    for sf in sorted((ROOT / "runs/s0_reaudit").glob("verdicts_shard*.json")):
        for v in json.loads(sf.read_text(encoding="utf-8")):
            verd[(v["task_id"], v["script"].strip())] = v["status"]
    for d in json.loads((ROOT / "runs/s0_reaudit/defect6_demotions.json").read_text(encoding="utf-8")):
        verd[(d["task_id"], d["script"].strip())] = "unsafe"
    return verd


def parsed_after_state(task_id: str, messages: list[str]) -> ProofState | None:
    """Genuine residual-goal state from stored messages, or None.

    raw_messages stays EMPTY: re-attaching error text would re-inject the
    message-counting artifacts that correction (g) exists to remove.
    """
    text = "\n".join(str(m) for m in (messages or []))
    if "unsolved goal" not in text.lower():
        return None
    goals = PARSER.extract_goals(text)
    if not goals:
        return None
    goals_text = "\n\n".join(g.raw for g in goals)
    return ProofState(
        state_id=stable_hash({"task_id": task_id, "parsed_goals": goals_text[:4000]}),
        task_id=task_id,
        goals_text=goals_text,
        target=goals[0].target or "",
        raw_messages=[],
    )


def defect_vec(state: ProofState) -> tuple[np.ndarray, list[str]]:
    d = EXTRACTOR.extract(state)
    return np.asarray(d.flat, dtype=float), list(d.flat_keys)


def root_state(task: LeanTask) -> ProofState:
    return ProofState.from_task(task)


def iter_shard_rows():
    """Yield (pair, corrected_status, messages) for every S'0 re-audit row."""
    manifests = {
        "s0": [json.loads(l) for l in open(ROOT / "runs/s0_reaudit_input_pairs.jsonl", encoding="utf-8")],
        "topup": [json.loads(l) for l in open(ROOT / "runs/s0_reaudit/topup_pairs.jsonl", encoding="utf-8")],
    }
    by_shard = {
        tag: {k: [x for i, x in enumerate(items) if i % 4 == k] for k in range(4)}
        for tag, items in manifests.items()
    }
    paths = {"s0": ROOT / "runs/s0_reaudit", "topup": ROOT / "runs/s0_reaudit/topup"}
    for tag in ["s0", "topup"]:
        for sh in range(4):
            p = paths[tag] / f"shard_{sh}/micro_audit.jsonl"
            for line in open(p, encoding="utf-8"):
                r = json.loads(line)
                tid = r["task_id"]  # s0_{sh}_{i} / topup_{sh}_{i}
                idx = int(tid.rsplit("_", 1)[1])
                pair = by_shard[tag][sh][idx]
                yield pair, r.get("messages") or []


def build_fit_matrix(verd, taskdefs, weights_mode: str):
    """Fit-side (pilot-src) response rows; returns (R, w, root_cache, log)."""
    root_cache: dict[str, np.ndarray] = {}
    keys_ref: list[str] | None = None

    def root_vec(task_id):
        nonlocal keys_ref
        if task_id not in root_cache:
            v, keys = defect_vec(root_state(taskdefs[task_id]))
            keys_ref = keys_ref or keys
            root_cache[task_id] = v
        return root_cache[task_id]

    rows, log = [], {"success": 0, "partial_parsed": 0, "partial_unrecoverable": 0, "other_skipped": 0}
    pilot_tasks = set()
    for pair, messages in iter_shard_rows():
        if pair["src"] not in ("pilot", "pilot_topup"):
            continue
        task_id = pair["task_id"]
        pilot_tasks.add(task_id)
        status = verd[(task_id, pair["script"].strip())]
        d_before = root_vec(task_id)
        if status == "success":
            rows.append(d_before.copy())
            log["success"] += 1
        elif status == "partial":
            st = parsed_after_state(task_id, messages)
            if st is None:
                log["partial_unrecoverable"] += 1
                continue
            d_after, _ = defect_vec(st)
            rows.append(d_before - d_after)
            log["partial_parsed"] += 1
        else:
            log["other_skipped"] += 1
    R = np.vstack(rows)
    D_fit = np.vstack([root_cache[t] for t in sorted(root_cache)])
    if weights_mode == "std":
        std = D_fit.std(axis=0)
        w = np.where(std > 1e-6, 1.0 / np.maximum(std, 1e-6), 0.0)
    elif weights_mode == "raw":
        w = np.ones(D_fit.shape[1])
    elif weights_mode == "log":
        w = None  # log transform applied per-vector instead
    else:
        raise ValueError(weights_mode)
    return R, w, root_vec, pilot_tasks, log, keys_ref


def transform(v: np.ndarray, w, mode: str) -> np.ndarray:
    if mode == "log":
        return np.sign(v) * np.log1p(np.abs(v))
    return v * w


def score_side_tasks(pilot_tasks: set[str]) -> dict[str, list[dict]]:
    """G1-era wave rows grouped by task, restricted to pilot-unseen tasks."""
    stores = [
        ROOT / "runs/g1_prod_train/extracted/wave_rows.jsonl",
        ROOT / "runs/g1re3_train/wave_rows_archive.tar.gz",
    ]
    rows_by_task: dict[str, list[dict]] = {}
    for p in stores:
        if p.suffix == ".jsonl":
            it = (json.loads(l) for l in open(p, encoding="utf-8"))
            for r in it:
                rows_by_task.setdefault(r["task_id"], []).append(r)
        else:
            with tarfile.open(p) as t:
                for m in t.getmembers():
                    if m.isfile() and m.name.endswith("wave_rows.jsonl"):
                        for line in t.extractfile(m):
                            r = json.loads(line)
                            rows_by_task.setdefault(r["task_id"], []).append(r)
    return {t: rs for t, rs in rows_by_task.items() if t not in pilot_tasks}


def realized_unpaid(task_id, rows, verd, root_vec, w, mode) -> float:
    d0 = transform(root_vec(task_id), w, mode)
    n0 = float(np.linalg.norm(d0))
    if n0 <= 0:
        return 1.0
    best = 1.0
    for r in rows:
        tac = ((r.get("action") or {}).get("tactic") or "").strip()
        status = verd.get((task_id, tac), r.get("status"))
        if status == "success" and ("sorry" in tac or "admit" in tac):
            status = "unsafe"  # defect #6 screen for un-re-audited rows
        if status == "success":
            return 0.0
        if status == "partial":
            st = parsed_after_state(task_id, r.get("messages") or [])
            if st is None:
                continue
            d_after, _ = defect_vec(st)
            best = min(best, float(np.linalg.norm(transform(d_after, w, mode))) / n0)
    return best


def spearman(a, b):
    from scipy.stats import spearmanr
    return float(spearmanr(a, b).statistic)


def gate(mode: str) -> dict:
    taskdefs = load_taskdefs()
    verd = load_corrected_verdicts()
    R_raw, w, root_vec, pilot_tasks, fit_log, keys = build_fit_matrix(verd, taskdefs, "std" if mode == "std" else mode)
    if mode == "log":
        w = None
    Rw = np.vstack([transform(r, w, mode) for r in R_raw])
    score = score_side_tasks(pilot_tasks)
    score = {t: rs for t, rs in score.items() if t in taskdefs}
    u_hat, u_real, d_norm, tasks = [], [], [], []
    for t, rs in sorted(score.items()):
        d0 = transform(root_vec(t), w, mode)
        n0 = float(np.linalg.norm(d0))
        if n0 <= 0:
            continue
        rep = project_onto_response_cone(d0, Rw, max_mass=None)
        u_hat.append(float(np.linalg.norm(np.asarray(rep.residual))) / n0)
        u_real.append(realized_unpaid(t, rs, verd, root_vec, w, mode))
        d_norm.append(n0)
        tasks.append(t)
    u_hat, u_real, d_norm = map(np.asarray, (u_hat, u_real, d_norm))
    rho_phi = spearman(u_hat, u_real)
    rho_base = spearman(d_norm, u_real)
    rng = np.random.default_rng(20260706)
    diffs = []
    n = len(tasks)
    for _ in range(4000):
        idx = rng.integers(0, n, n)
        if len(set(u_real[idx])) < 2:
            continue
        diffs.append(spearman(u_hat[idx], u_real[idx]) - spearman(d_norm[idx], u_real[idx]))
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    verdict = "PASS" if (rho_phi - rho_base >= 0.10 and lo > 0) else "FAIL"
    return {
        "mode": mode, "n_tasks": n, "fit_log": fit_log, "n_fit_rows": int(Rw.shape[0]),
        "rho_phi": round(rho_phi, 4), "rho_baseline": round(rho_base, 4),
        "diff": round(rho_phi - rho_base, 4), "diff_ci95": [round(float(lo), 4), round(float(hi), 4)],
        "verdict": verdict,
        "per_task": [
            {"task_id": t, "u_hat": round(float(a), 4), "u_real": round(float(b), 4), "d_norm": round(float(c), 3)}
            for t, a, b, c in zip(tasks, u_hat, u_real, d_norm)
        ],
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    report = {}
    for mode in ["std", "raw", "log"]:
        r = gate(mode)
        report[mode] = r
        print(f"[{mode}] n={r['n_tasks']} fit_rows={r['n_fit_rows']} rho_phi={r['rho_phi']} "
              f"rho_base={r['rho_baseline']} diff={r['diff']} CI={r['diff_ci95']} -> {r['verdict']}")
    verdicts = {report[m]["verdict"] for m in report}
    report["registered_verdict"] = report["std"]["verdict"] if len(verdicts) == 1 else "UNSTABLE-UNITS"
    print("REGISTERED VERDICT:", report["registered_verdict"])
    (OUT / "gate_report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
