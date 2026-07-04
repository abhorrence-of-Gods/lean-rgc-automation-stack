"""Toy 0: exactly solvable phase-selected stochastic closed loop.

Tokens are meaningless labels (a random permutation is applied); the only
object of study is how a prefix-selected phase changes the future token law
and the closed-loop kernel. Every quantity of the phase-split / certified
freezing theory is computable exactly here, so the split rule and freeze
rule are validated against ground truth before they are trusted on the
LLM/Lean loop.

System layout (per leaf phase):
  hidden state h in {0..n_hidden-1} with transition T_phi(h'|h)
  memory bit  m in {0,1}: 1 = last verifier event was a failure
  emission    E_phi(y|h,m): mass p_correct(m) on the token pair of h,
              split (w, 1-w) inside the pair; failure memory adds a repair
              boost to p_correct (this is the closed-loop feedback)
  verifier    R(y,h) = 1 iff y belongs to the token pair of h (labels are
              permuted by a system-wide sigma, so token identity is
              meaningless; only the paired-group structure carries reward)
Closed-loop finite state x = (h, m); everything below is exact linear
algebra on that state space.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import json

import numpy as np


SCHEMA_TOY0_REPORT = "lean-rgc-toy0-phase-report-v95.0"

GAMMA = 0.9
REPAIR_BOOST = 0.15


@dataclass
class PhaseSpec:
    name: str
    p_correct: float
    within_pair_pref: float  # w: mass share of the pair's first element
    family: str  # "A" (lazy walk) or "B" (cyclic walk)


@dataclass
class PhaseSystem:
    scenario: str
    n_tokens: int
    n_hidden: int
    sigma: np.ndarray  # token label permutation (meaning eraser)
    specs: dict[str, PhaseSpec]
    tree: dict[str, list[str]] = field(default_factory=dict)

    @property
    def leaves(self) -> list[str]:
        return [n for n in self.specs]

    def members(self, cell: str) -> list[str]:
        if cell in self.specs:
            return [cell]
        out: list[str] = []
        for child in self.tree.get(cell, []):
            out.extend(self.members(child))
        return out


def make_phase_system(scenario: str, *, n_tokens: int = 8, n_hidden: int = 4, seed: int = 0) -> PhaseSystem:
    """Scenarios:

    S1: A1/A2 differ only in which token of the correct pair they prefer —
        future token law differs, reward and loop kernel are identical.
    S2: A1/A2 differ in p_correct — reward and loop kernel differ.
        B1/B2 differ only in pair preference (loop-identical), so the
        reward-relevant ground-truth partition is {A1},{A2},{B1,B2}.
    """

    rng = np.random.default_rng(seed)
    sigma = rng.permutation(n_tokens)
    if scenario == "S1":
        specs = {
            "A1": PhaseSpec("A1", 0.70, 0.9, "A"),
            "A2": PhaseSpec("A2", 0.70, 0.1, "A"),
            "B1": PhaseSpec("B1", 0.55, 0.5, "B"),
            "B2": PhaseSpec("B2", 0.55, 0.5, "B"),
        }
    elif scenario == "S2":
        specs = {
            "A1": PhaseSpec("A1", 0.70, 0.9, "A"),
            "A2": PhaseSpec("A2", 0.35, 0.9, "A"),
            "B1": PhaseSpec("B1", 0.55, 0.5, "B"),
            "B2": PhaseSpec("B2", 0.55, 0.3, "B"),
        }
    elif scenario == "S2h":
        # Hard variant for the recovery experiment: the A1/A2 gap sits near
        # the detection threshold, so the multiple-comparison penalty of the
        # flat procedure actually bites.
        specs = {
            "A1": PhaseSpec("A1", 0.70, 0.9, "A"),
            "A2": PhaseSpec("A2", 0.58, 0.9, "A"),
            "B1": PhaseSpec("B1", 0.55, 0.5, "B"),
            "B2": PhaseSpec("B2", 0.55, 0.3, "B"),
        }
    else:
        raise ValueError(f"unknown scenario: {scenario}")
    tree = {"root": ["A", "B"], "A": ["A1", "A2"], "B": ["B1", "B2"]}
    return PhaseSystem(scenario, n_tokens, n_hidden, sigma, specs, tree)


def _transition(system: PhaseSystem, family: str) -> np.ndarray:
    n = system.n_hidden
    uniform = np.full((n, n), 1.0 / n)
    if family == "A":
        return 0.6 * np.eye(n) + 0.4 * uniform
    shift = np.zeros((n, n))
    for h in range(n):
        shift[h, (h + 1) % n] = 1.0
    return 0.7 * shift + 0.3 * uniform


def _emission(system: PhaseSystem, spec: PhaseSpec) -> np.ndarray:
    """E[m, h, y] over permuted token labels."""

    V, nH = system.n_tokens, system.n_hidden
    E = np.zeros((2, nH, V))
    for m in range(2):
        p_c = min(spec.p_correct + (REPAIR_BOOST if m == 1 else 0.0), 0.95)
        for h in range(nH):
            base = np.full(V, (1.0 - p_c) / (V - 2))
            base[2 * h] = p_c * spec.within_pair_pref
            base[2 * h + 1] = p_c * (1.0 - spec.within_pair_pref)
            E[m, h, system.sigma] = base  # permute labels: meaning eraser
    return E


def _reward_table(system: PhaseSystem) -> np.ndarray:
    """R[h, y] = 1 iff permuted token y belongs to the pair of h."""

    V, nH = system.n_tokens, system.n_hidden
    R = np.zeros((nH, V))
    for h in range(nH):
        R[h, system.sigma[2 * h]] = 1.0
        R[h, system.sigma[2 * h + 1]] = 1.0
    return R


def build_loop_kernel(system: PhaseSystem, phase: str, *, closed: bool = True) -> tuple[np.ndarray, np.ndarray]:
    """Exact closed-loop kernel P[(h,m) -> (h',m')] and reward vector r[(h,m)].

    Order per step: emit y from E(.|h,m); verifier event e = R(y,h);
    memory m' = 1 - e (closed loop) or frozen (open loop); hidden h' ~ T.
    """

    spec = system.specs[phase]
    T = _transition(system, spec.family)
    E = _emission(system, spec)
    R = _reward_table(system)
    nH = system.n_hidden
    nX = nH * 2
    P = np.zeros((nX, nX))
    r = np.zeros(nX)
    for h in range(nH):
        for m in range(2):
            x = h * 2 + m
            p_success = float(E[m, h] @ R[h])
            r[x] = p_success
            for h2 in range(nH):
                if closed:
                    P[x, h2 * 2 + 0] += T[h, h2] * p_success
                    P[x, h2 * 2 + 1] += T[h, h2] * (1.0 - p_success)
                else:
                    P[x, h2 * 2 + m] += T[h, h2]
    return P, r


def value(P: np.ndarray, r: np.ndarray, gamma: float = GAMMA) -> np.ndarray:
    return np.linalg.solve(np.eye(len(r)) - gamma * P, r)


def phase_value(system: PhaseSystem, phase: str, *, closed: bool = True, gamma: float = GAMMA) -> float:
    """Normalized discounted value from the uniform initial state, in [0,1]."""

    P, r = build_loop_kernel(system, phase, closed=closed)
    V = value(P, r, gamma)
    init = np.zeros(len(r))
    init[0::2] = 1.0 / system.n_hidden  # uniform over h, memory starts at 0
    return float(init @ V) * (1.0 - gamma)


def cell_value(system: PhaseSystem, cell: str, **kw) -> float:
    members = system.members(cell)
    return float(np.mean([phase_value(system, p, **kw) for p in members]))


def cell_kernel(system: PhaseSystem, cell: str) -> np.ndarray:
    members = system.members(cell)
    return np.mean([build_loop_kernel(system, p)[0] for p in members], axis=0)


def future_marginals(system: PhaseSystem, cell: str, horizon: int) -> np.ndarray:
    """Exact per-step token marginals q[t, y] under the closed loop (cell mixture)."""

    out = np.zeros((horizon, system.n_tokens))
    members = system.members(cell)
    for phase in members:
        spec = system.specs[phase]
        E = _emission(system, spec)
        P, _ = build_loop_kernel(system, phase)
        rho = np.zeros(system.n_hidden * 2)
        rho[0::2] = 1.0 / system.n_hidden
        for t in range(horizon):
            q = np.zeros(system.n_tokens)
            for h in range(system.n_hidden):
                for m in range(2):
                    q += rho[h * 2 + m] * E[m, h]
            out[t] += q / len(members)
            rho = rho @ P
    return out


def _tv(p: np.ndarray, q: np.ndarray) -> float:
    return 0.5 * float(np.abs(p - q).sum())


def future_distance(system: PhaseSystem, cell_a: str, cell_b: str, *, horizon: int = 6) -> float:
    qa = future_marginals(system, cell_a, horizon)
    qb = future_marginals(system, cell_b, horizon)
    return float(np.mean([_tv(qa[t], qb[t]) for t in range(horizon)]))


def _kernel_distance(P1: np.ndarray, P2: np.ndarray) -> float:
    return float(np.mean([_tv(P1[x], P2[x]) for x in range(P1.shape[0])]))


def split_gains(system: PhaseSystem, cell: str, *, horizon: int = 6) -> dict[str, float]:
    """Exact split gains for cell -> its children (uniform child weights)."""

    children = system.tree.get(cell)
    if not children:
        raise ValueError(f"cell {cell} has no children")
    w = 1.0 / len(children)
    parent_kernel = cell_kernel(system, cell)
    parent_value = cell_value(system, cell)
    parent_future = future_marginals(system, cell, horizon)
    g_loop = g_target = g_future = 0.0
    for child in children:
        g_loop += w * _kernel_distance(cell_kernel(system, child), parent_kernel)
        g_target += w * abs(cell_value(system, child) - parent_value)
        child_future = future_marginals(system, child, horizon)
        g_future += w * float(np.mean([_tv(child_future[t], parent_future[t]) for t in range(horizon)]))
    return {"g_loop": g_loop, "g_target": g_target, "g_future": g_future}


def decide_split(
    gains: dict[str, float],
    *,
    alpha: float = 1.0,
    beta: float = 0.1,
    split_cost: float = 0.05,
    uncertainty: float = 0.0,
    tail: float = 0.0,
) -> dict[str, Any]:
    total = gains["g_loop"] + alpha * gains["g_target"] + beta * gains["g_future"]
    threshold = split_cost + uncertainty + tail
    return {**gains, "total_gain": total, "threshold": threshold, "split": bool(total > threshold)}


def simulate_episode(system: PhaseSystem, phase: str, *, steps: int, rng: np.random.Generator) -> float:
    """One closed-loop episode; returns mean verifier reward over `steps`."""

    spec = system.specs[phase]
    T = _transition(system, spec.family)
    E = _emission(system, spec)
    R = _reward_table(system)
    h = int(rng.integers(system.n_hidden))
    m = 0
    total = 0.0
    for _ in range(steps):
        y = int(rng.choice(system.n_tokens, p=E[m, h]))
        e = float(R[h, y])
        total += e
        m = 0 if e > 0.5 else 1
        h = int(rng.choice(system.n_hidden, p=T[h]))
    return total / steps


def estimate_value(system: PhaseSystem, phase: str, *, n_episodes: int, steps: int, rng: np.random.Generator) -> tuple[float, float]:
    ys = np.array([simulate_episode(system, phase, steps=steps, rng=rng) for _ in range(n_episodes)])
    se = float(ys.std(ddof=1) / np.sqrt(n_episodes)) if n_episodes > 1 else float("inf")
    return float(ys.mean()), se


def freeze_decision(
    estimates: dict[str, tuple[float, float]],
    *,
    tail: float = 0.02,
    freeze_cost: float = 0.01,
) -> dict[str, Any]:
    """Certified freezing: freeze iff margin > 2*SE_combined + tail + cost."""

    ranked = sorted(estimates.items(), key=lambda kv: -kv[1][0])
    (best, (jb, sb)), (runner, (jr, sr)) = ranked[0], ranked[1]
    margin = jb - jr
    eps = float(np.sqrt(sb**2 + sr**2))
    threshold = 2.0 * eps + tail + freeze_cost
    return {
        "chosen": best,
        "runner_up": runner,
        "margin": margin,
        "uncertainty": eps,
        "threshold": threshold,
        "frozen": bool(margin > threshold),
    }


def loop_effect(system: PhaseSystem, phase: str) -> float:
    return phase_value(system, phase, closed=True) - phase_value(system, phase, closed=False)


def selection_defect(system: PhaseSystem, cell: str) -> float:
    members = system.members(cell)
    worst = 0.0
    for i, a in enumerate(members):
        for b in members[i + 1 :]:
            worst = max(worst, _kernel_distance(build_loop_kernel(system, a)[0], build_loop_kernel(system, b)[0]))
    return worst


def dual_error(system: PhaseSystem, *, target_phase: str, posterior: float, atlas_cell: str) -> float:
    """|J_init(u) - J_phase([u])| for a selector with mass `posterior` on target."""

    others = [p for p in system.leaves if p != target_phase]
    j_init = posterior * phase_value(system, target_phase) + (1.0 - posterior) * float(
        np.mean([phase_value(system, p) for p in others])
    )
    j_phase = cell_value(system, atlas_cell)
    return abs(j_init - j_phase)


def hierarchical_vs_flat_recovery(
    system: PhaseSystem,
    *,
    budget_episodes: int,
    steps: int = 20,
    n_trials: int = 40,
    z: float = 2.0,
    seed: int = 0,
) -> dict[str, float]:
    """Recover the reward-relevant partition ({A1},{A2},{B1,B2}) from samples.

    Both procedures get the SAME per-leaf sample budget; the hierarchical
    advantage under test is purely the look structure. The tree restricts
    testing to the 2 within-family comparisons at the nominal z, while the
    flat procedure must run all 6 pairwise tests and pay the Bonferroni
    correction on z to hold the same family-wise error. Recovery = A1/A2
    separated AND B1/B2 not separated.
    """

    rng = np.random.default_rng(seed)
    z_bonf = 2.64  # per-look alpha scaled 2 -> 6 looks at equal family-wise error

    def sep(ja, sa, jb, sb, zz) -> bool:
        return abs(ja - jb) > zz * float(np.sqrt(sa**2 + sb**2))

    hier_ok = flat_ok = 0
    n_leaf = max(2, budget_episodes // 4)
    for _ in range(n_trials):
        est = {p: estimate_value(system, p, n_episodes=n_leaf, steps=steps, rng=rng) for p in system.leaves}
        if sep(*est["A1"], *est["A2"], z) and not sep(*est["B1"], *est["B2"], z):
            hier_ok += 1
        if sep(*est["A1"], *est["A2"], z_bonf) and not sep(*est["B1"], *est["B2"], z_bonf):
            flat_ok += 1
    return {"hierarchical": hier_ok / n_trials, "flat": flat_ok / n_trials}


def run_toy0_report(out: str | Path | None = None, *, seed: int = 0) -> dict[str, Any]:
    """Run the full Toy 0 validation and grade hypotheses H1-H4."""

    s1 = make_phase_system("S1", seed=seed)
    s2 = make_phase_system("S2", seed=seed)
    rng = np.random.default_rng(seed)

    root_s2 = decide_split(split_gains(s2, "root"))
    a_s1 = decide_split(split_gains(s1, "A"))
    a_s2 = decide_split(split_gains(s2, "A"))
    b_s2 = decide_split(split_gains(s2, "B"))

    small = {p: estimate_value(s2, p, n_episodes=2, steps=5, rng=rng) for p in ("A1", "A2")}
    large = {p: estimate_value(s2, p, n_episodes=200, steps=20, rng=rng) for p in ("A1", "A2")}
    freeze_small = freeze_decision(small)
    freeze_large = freeze_decision(large)

    s2h = make_phase_system("S2h", seed=seed)
    recovery = hierarchical_vs_flat_recovery(s2h, budget_episodes=32, seed=seed)

    report = {
        "schema_version": SCHEMA_TOY0_REPORT,
        "splits": {"root_S2": root_s2, "A_S1": a_s1, "A_S2": a_s2, "B_S2": b_s2},
        "freeze": {"small_n": freeze_small, "large_n": freeze_large},
        "loop_effect_A1_S2": loop_effect(s2, "A1"),
        "selection_defect": {"A_S1": selection_defect(s1, "A"), "A_S2": selection_defect(s2, "A")},
        "dual_error": {
            "coarse_atlas": dual_error(s2, target_phase="A1", posterior=0.95, atlas_cell="A"),
            "fine_atlas": dual_error(s2, target_phase="A1", posterior=0.95, atlas_cell="A1"),
        },
        "recovery": recovery,
        "hypotheses": {},
        "canonical_status": "toy0_report_is_theory_validation_not_canonical",
    }
    report["hypotheses"] = {
        "H1_phase_from_future_law": bool(a_s1["g_future"] > 0.02),
        "H2_split_driven_by_loop_not_future": bool(
            a_s2["split"] and not a_s1["split"] and a_s1["g_future"] > a_s1["g_loop"]
        ),
        "H3_hierarchical_sample_efficient": bool(recovery["hierarchical"] >= recovery["flat"]),
        "H4_freeze_needs_margin_rule": bool(freeze_large["frozen"] and not freeze_small["frozen"]),
    }
    if out:
        p = Path(out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True, default=float), encoding="utf-8")
    return report


__all__ = [
    "GAMMA",
    "SCHEMA_TOY0_REPORT",
    "PhaseSpec",
    "PhaseSystem",
    "build_loop_kernel",
    "cell_kernel",
    "cell_value",
    "decide_split",
    "dual_error",
    "estimate_value",
    "freeze_decision",
    "future_distance",
    "future_marginals",
    "hierarchical_vs_flat_recovery",
    "loop_effect",
    "make_phase_system",
    "phase_value",
    "run_toy0_report",
    "selection_defect",
    "simulate_episode",
    "split_gains",
    "value",
]
