"""S'1c instruments 1-3 on the real corpus (litmus-certified stack).

Produces runs/s_prime_1c/leakage_spectrum.json and the Schur-selection
verdict that decides whether instrument 5 (the single-shot gate) may
fire. Gate frame is untouched here (Amendment d): this is estimation.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from s_prime_1c_estimators import (FiberRidge, SweepModel, dedup_indices,
                                   fiber_of, leakage_gram, schur_reduction)
from lean_rgc.defects import ProofDefectExtractor
from lean_rgc.schemas import LeanTask, ProofState, stable_hash

REPLAY = ROOT / "runs/s_prime_1/s1_stepwise_rerun2"
OUT = ROOT / "runs/s_prime_1c"
EXTRACTOR = ProofDefectExtractor()
F_MIN = 20
R_ADD = 16

HEAD_RELS = [("↔", "Iff"), ("∧", "And"), ("∨", "Or"), ("∃", "Exists"),
             ("≤", "le"), ("<", "lt"), ("∣", "dvd"), ("∈", "mem"), ("=", "Eq")]


def kernel_goal_texts(ks):
    if not isinstance(ks, dict):
        return None
    goals = ks.get("goals")
    if not isinstance(goals, list):
        return None
    return [str(g.get("target_text") or g.get("pp") or g.get("raw") or "")
            for g in goals if isinstance(g, dict)]


def head_symbol(text: str) -> str:
    """Frozen unwrapping rule: strip leading universal binders and
    negations, classify by the top-level relation, else first ident."""
    t = (text or "").strip()
    for _ in range(8):
        m = re.match(r"^∀[^,]*,\s*", t)
        if m:
            t = t[m.end():]
            continue
        if t.startswith("¬"):
            t = t[1:].lstrip()
            continue
        break
    depth = 0
    for i, ch in enumerate(t):
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif depth == 0:
            for sym, name in HEAD_RELS:
                if t.startswith(sym, i):
                    return name
    m = re.match(r"[A-Za-z_][A-Za-z0-9_.]*", t)
    return m.group(0).split(".")[0] if m else "opaque"


QUAL_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z0-9_']+)+")


def build_corpus():
    taskdefs = {}
    for line in open(ROOT / "runs/s_prime_1/minif2f_test_tasks.jsonl", encoding="utf-8"):
        d = json.loads(line)
        taskdefs[d["task_id"]] = LeanTask.from_dict(d)
    probe = EXTRACTOR.extract(ProofState.from_task(next(iter(taskdefs.values()))))
    keys = list(probe.flat_keys)

    def defect_of(texts, task_id):
        if not texts or all(not t.strip() for t in texts):
            return np.zeros(len(keys))
        gt = "\n\n".join(f"⊢ {t}" for t in texts)
        st = ProofState(state_id=stable_hash({"t": task_id, "g": gt[:4000]}),
                        task_id=task_id, goals_text=gt, target=texts[0], raw_messages=[])
        return np.asarray(EXTRACTOR.extract(st).flat, dtype=float)

    root_cache = {}

    def root_vec(tid):
        if tid not in root_cache:
            root_cache[tid] = np.asarray(
                EXTRACTOR.extract(ProofState.from_task(taskdefs[tid])).flat, dtype=float)
        return root_cache[tid]

    trans = [json.loads(l) for l in open(REPLAY / "stepwise_transitions.jsonl", encoding="utf-8")]
    by_script = defaultdict(list)
    for t in trans:
        by_script[t["script_index"]].append(t)
    rows = []
    for si, steps in by_script.items():
        steps.sort(key=lambda t: t["step_index"])
        tid = steps[0]["task_id"]
        prev_vec, prev_text = root_vec(tid), taskdefs[tid].statement
        for t in steps:
            if t["status"] not in ("success", "partial"):
                break
            texts = kernel_goal_texts(t.get("kernel_state_after"))
            if texts is None:
                break
            cur = defect_of(texts, tid)
            rows.append({"task_id": tid, "chain": si, "fiber": fiber_of(t["tactic"]),
                         "z": prev_vec, "resp": prev_vec - cur, "before_text": prev_text})
            prev_vec = cur
            prev_text = "\n".join(texts)
    # whitening (Amendment-a convention): std over pilot-population roots
    pilot_tasks = {json.loads(l)["task_id"] for l in
                   open(ROOT / "runs/s0_reaudit_input_pairs.jsonl", encoding="utf-8")
                   if json.loads(l)["src"] == "pilot"}
    D_fit = np.vstack([root_vec(t) for t in sorted(pilot_tasks & set(taskdefs))])
    std = D_fit.std(axis=0)
    w = np.where(std > 1e-6, 1.0 / np.maximum(std, 1e-6), 0.0)
    return rows, keys, w


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows, keys, w = build_corpus()
    keep = dedup_indices(keys)
    keys_d = [keys[i] for i in keep]
    Z = np.vstack([r["z"] for r in rows])[:, keep] * w[keep]
    R = np.vstack([r["resp"] for r in rows])[:, keep] * w[keep]
    fibers = [r["fiber"] for r in rows]
    chains = [r["chain"] for r in rows]
    d_norm = np.linalg.norm(Z, axis=1)
    print(f"corpus rows: {len(rows)} | dims: {len(keep)} | fibers: {len(set(fibers))}")

    # instrument 1: sweeping (estimation frame)
    sw = SweepModel().fit(d_norm, R, fibers)
    R_cm = sw.residual(d_norm, R, fibers)

    # instrument 2: leakage Gram on co-moving residuals
    fr = FiberRidge()
    resid, mask = fr.heldout_residuals(Z, R_cm, fibers, chains)
    gate_dims = [i for i, k in enumerate(keys_d) if not k.startswith("carrier.")]
    g_all = leakage_gram(resid, mask, fr.folds)
    g_gate = leakage_gram(resid[:, gate_dims], mask, fr.folds)
    intro_mask = mask & np.isin(fibers, ["intro", "intros"])
    g_intro = leakage_gram(resid[:, gate_dims], intro_mask)
    g_nonintro = leakage_gram(resid[:, gate_dims], mask & ~np.isin(fibers, ["intro", "intros"]))

    def eig_summary(g, names, k=5):
        out = []
        for j in range(min(k, g["evecs"].shape[1])):
            v = g["evecs"][:, j]
            top = np.argsort(-np.abs(v))[:4]
            out.append({"eigenvalue": round(float(g["evals"][j]), 4),
                        "share": round(float(g["evals"][j] / max(g["evals"].sum(), 1e-12)), 4),
                        "top_loadings": {names[i]: round(float(v[i]), 3) for i in top}})
        return out

    # instrument 3: candidate features from before-state text
    heads = [head_symbol((r["before_text"] or "").split("\n")[0]) for r in rows]
    head_counts = Counter(heads)
    vocab = Counter()
    for r in rows:
        vocab.update(set(QUAL_RE.findall(r["before_text"] or "")))
    cand = []
    for h, c in head_counts.items():
        if c >= F_MIN:
            cand.append((f"head:{h}", np.array([1.0 if x == h else 0.0 for x in heads])))
    for tok, c in vocab.items():
        if c >= F_MIN and len(tok) > 3:
            col = np.array([1.0 if tok in (r["before_text"] or "") else 0.0 for r in rows])
            cand.append((f"const:{tok}", col))
    print(f"candidate features: {len(cand)} (heads {sum(1 for n,_ in cand if n.startswith('head'))}, consts {sum(1 for n,_ in cand if n.startswith('const'))})")

    selected, cur_Z = [], Z
    best_report = None
    for _ in range(R_ADD):
        best = None
        for name, col in cand:
            if name in [s[0] for s in selected]:
                continue
            Ze = np.hstack([cur_Z, col[:, None]])
            sr = schur_reduction(Z, Ze, R_cm, fibers, chains, gate_dims)
            if best is None or sr["reduction"] > best[2]["reduction"]:
                best = (name, col, sr)
        if best is None or (best_report and best[2]["reduction"] <= best_report["reduction"] + 0.005):
            break
        selected.append((best[0], best[1]))
        cur_Z = np.hstack([cur_Z, best[1][:, None]])
        best_report = best[2]
        print(f"  + {best[0]}: cumulative Schur reduction {best[2]['reduction']:.4f}")

    verdict = "NOT-MET"
    if best_report and best_report["reduction"] >= 0.30 and \
       best_report["n_directions_hit"] >= 3 and best_report["max_direction_share"] <= 0.50:
        verdict = "MET"
    report = {
        "corpus": {"rows": len(rows), "dims": len(keep),
                   "fiber_sizes": dict(Counter(fibers).most_common()),
                   "accepted_fibers": fr.accepted_fibers,
                   "excluded_row_share": round(fr.excluded_row_share, 4)},
        "sweep": {"beta_global": round(sw.beta_global, 4),
                  "s_dir_top": {keys_d[i]: round(float(sw.s_dir[i]), 3)
                                 for i in np.argsort(-np.abs(sw.s_dir))[:5]}},
        "leakage": {"trace_all_dims": round(g_all["trace"], 4),
                     "trace_gate_dims": round(g_gate["trace"], 4),
                     "fold_max_principal_angle_deg": g_gate.get("fold_max_principal_angle_deg"),
                     "top5": eig_summary(g_gate, [keys_d[i] for i in gate_dims]),
                     "intro_stratum_trace": round(g_intro["trace"], 4),
                     "nonintro_stratum_trace": round(g_nonintro["trace"], 4)},
        "schur_selection": {"selected": [s[0] for s in selected],
                             "final": best_report, "criterion": "reduction >= 0.30, >= 3 directions, max share <= 0.50",
                             "verdict": verdict},
    }
    (OUT / "leakage_spectrum.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "corpus"}, indent=1, ensure_ascii=False)[:3000])
    print("SCHUR CRITERION:", verdict)


if __name__ == "__main__":
    main()
