from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import json

import numpy as np

from .schemas import read_jsonl, write_jsonl, TacticAction


@dataclass
class CarrierMatrix:
    atoms: list[str]
    action_ids: list[str]
    matrix: list[list[float]]  # shape atoms x actions; positive = carrier defect reduced
    counts: dict[str, int]
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "CarrierMatrix":
        return cls(atoms=list(d.get("atoms", [])), action_ids=list(d.get("action_ids", [])), matrix=d.get("matrix", []), counts=dict(d.get("counts", {})), metadata=dict(d.get("metadata", {})))

    def save(self, path: str | Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "CarrierMatrix":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def as_array(self) -> np.ndarray:
        return np.asarray(self.matrix, dtype=float)


def _carrier_delta(row: dict[str, Any]) -> dict[str, float]:
    cd = row.get("carrier_delta") or {}
    if not cd and isinstance(row.get("response"), dict):
        # Some rows store carrier deltas as carrier.* response coordinates.
        cd = {str(k).split(".", 1)[1]: float(v) for k, v in row["response"].items() if str(k).startswith("carrier.")}
    return {str(k): float(v) for k, v in cd.items()}


def build_carrier_matrix_from_responses(responses_path: str | Path, out: str | Path | None = None, *, shrink: float = 2.0, min_count: int = 1) -> CarrierMatrix:
    rows = read_jsonl(responses_path)
    atom_set: set[str] = set()
    by_action: dict[str, list[dict[str, float]]] = {}
    for r in rows:
        aid = str(r.get("action_id") or (r.get("action") or {}).get("action_id") or "")
        if not aid:
            continue
        cd = _carrier_delta(r)
        if not cd:
            continue
        atom_set.update(cd)
        by_action.setdefault(aid, []).append(cd)
    atoms = sorted(atom_set)
    action_ids = sorted(by_action)
    # global mean for shrinkage
    global_vals = {a: [] for a in atoms}
    for ds in by_action.values():
        for d in ds:
            for a in atoms:
                global_vals[a].append(float(d.get(a, 0.0)))
    gmean = {a: float(np.mean(v)) if v else 0.0 for a, v in global_vals.items()}
    mat = np.zeros((len(atoms), len(action_ids)), dtype=float)
    counts: dict[str, int] = {}
    for j, aid in enumerate(action_ids):
        ds = by_action[aid]
        counts[aid] = len(ds)
        n = len(ds)
        for i, atom in enumerate(atoms):
            vals = [float(d.get(atom, 0.0)) for d in ds]
            mean = float(np.mean(vals)) if vals else 0.0
            # empirical Bayes shrink toward global mean; keeps low-count actions conservative
            mat[i, j] = (n * mean + shrink * gmean[atom]) / (n + shrink)
    # Optionally zero out unsupported low-count action columns.
    for j, aid in enumerate(action_ids):
        if counts[aid] < min_count:
            mat[:, j] = np.minimum(mat[:, j], 0.0)
    cm = CarrierMatrix(atoms=atoms, action_ids=action_ids, matrix=mat.tolist(), counts=counts, metadata={"source": str(responses_path), "shrink": shrink, "min_count": min_count, "meaning": "positive entries reduce carrier defects; negative entries increase them"})
    if out:
        cm.save(out)
    return cm


def carrier_defect_mean(defects_path: str | Path) -> dict[str, float]:
    vals: dict[str, list[float]] = {}
    for r in read_jsonl(defects_path):
        carrier = r.get("carrier") or (r.get("defect") or {}).get("carrier") or {}
        for k, v in carrier.items():
            vals.setdefault(str(k), []).append(float(v))
    return {k: float(np.mean(v)) for k, v in vals.items() if v}


def carrier_safe_action_ids(cm: CarrierMatrix, *, budget: float = 0.0, per_atom_budget: dict[str, float] | None = None) -> set[str]:
    arr = cm.as_array()
    safe: set[str] = set()
    per_atom_budget = per_atom_budget or {}
    for j, aid in enumerate(cm.action_ids):
        ok = True
        for i, atom in enumerate(cm.atoms):
            b = float(per_atom_budget.get(atom, budget))
            # Negative value is violation. Allow down to -budget.
            if arr[i, j] < -b:
                ok = False; break
        if ok:
            safe.add(aid)
    return safe


def annotate_actions_with_carrier_matrix(actions_path: str | Path, matrix_path: str | Path, out: str | Path, *, budget: float = 0.0, keep_unsafe: bool = False) -> dict[str, Any]:
    cm = CarrierMatrix.load(matrix_path)
    safe = carrier_safe_action_ids(cm, budget=budget)
    arr = cm.as_array()
    idx = {aid: j for j, aid in enumerate(cm.action_ids)}
    rows: list[dict[str, Any]] = []
    for row in read_jsonl(actions_path):
        action = TacticAction.from_dict(row).to_dict()
        aid = action.get("action_id")
        j = idx.get(str(aid))
        if j is not None:
            deltas = {atom: float(arr[i, j]) for i, atom in enumerate(cm.atoms)}
            violation = {k: max(0.0, -v - budget) for k, v in deltas.items()}
            risk = float(sum(violation.values()))
            is_safe = str(aid) in safe
        else:
            deltas = {}; risk = 0.0; is_safe = True
        action.setdefault("metadata", {})["carrier_matrix"] = {"safe": is_safe, "risk": risk, "deltas": deltas, "budget": budget}
        action.setdefault("carrier_tags", action.get("carrier_tags") or [])
        if keep_unsafe or is_safe:
            rows.append(action)
    write_jsonl(out, rows)
    return {"out": str(out), "n_in": len(read_jsonl(actions_path)), "n_out": len(rows), "n_safe_ids": len(safe), "budget": budget, "matrix": str(matrix_path)}


def multi_carrier_report(matrix_path: str | Path, defects_path: str | Path | None = None, out: str | Path | None = None) -> dict[str, Any]:
    cm = CarrierMatrix.load(matrix_path)
    arr = cm.as_array()
    atom_stats = []
    for i, atom in enumerate(cm.atoms):
        col = arr[i, :] if arr.size else np.zeros(0)
        atom_stats.append({
            "atom": atom,
            "mean_delta": float(np.mean(col)) if col.size else 0.0,
            "min_delta": float(np.min(col)) if col.size else 0.0,
            "max_delta": float(np.max(col)) if col.size else 0.0,
            "unsafe_fraction_0": float(np.mean(col < 0)) if col.size else 0.0,
            "covered_fraction_pos": float(np.mean(col > 0)) if col.size else 0.0,
        })
    rep: dict[str, Any] = {"n_atoms": len(cm.atoms), "n_actions": len(cm.action_ids), "atoms": atom_stats}
    if defects_path:
        d = carrier_defect_mean(defects_path)
        residual = {a: float(d.get(a, 0.0)) for a in cm.atoms if d.get(a, 0.0) > 0 and (arr[cm.atoms.index(a), :].max() if arr.size else 0.0) <= 0}
        rep["mean_carrier_defect"] = d
        rep["uncovered_positive_atoms"] = residual
        rep["uncovered_l1"] = float(sum(residual.values()))
    if out:
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")
    return rep



def merge_carrier_incidence_patches(
    matrix_path: str | Path,
    patches_path: str | Path,
    out: str | Path | None = None,
    *,
    patch_weight: float = 1.0,
    require_safe: bool = False,
) -> CarrierMatrix:
    """Merge qgen/carrier-incidence patch rows into a CarrierMatrix.

    Patch rows are candidate chart updates, not canonical carrier facts.  Each row
    is expected to contain at least ``action_id``, ``carrier_atom``, ``mean_delta``
    and ``count``.  Positive deltas mean the action reduces the carrier defect;
    negative deltas mean carrier violation.  The merge is conservative and stores
    provenance in metadata.
    """
    cm = CarrierMatrix.load(matrix_path)
    patches = read_jsonl(patches_path)
    atoms = list(cm.atoms)
    action_ids = list(cm.action_ids)
    arr = cm.as_array()
    if arr.size == 0:
        arr = np.zeros((len(atoms), len(action_ids)), dtype=float)
    if arr.shape != (len(atoms), len(action_ids)):
        arr = np.asarray(cm.matrix, dtype=float).reshape((len(atoms), len(action_ids))) if atoms and action_ids else np.zeros((len(atoms), len(action_ids)), dtype=float)
    counts = dict(cm.counts)
    patch_records: list[dict[str, Any]] = []

    def ensure_atom(atom: str) -> int:
        nonlocal arr
        if atom in atoms:
            return atoms.index(atom)
        atoms.append(atom)
        arr = np.vstack([arr, np.zeros((1, arr.shape[1]), dtype=float)]) if arr.size else np.zeros((len(atoms), len(action_ids)), dtype=float)
        return len(atoms) - 1

    def ensure_action(aid: str) -> int:
        nonlocal arr
        if aid in action_ids:
            return action_ids.index(aid)
        action_ids.append(aid)
        arr = np.hstack([arr, np.zeros((arr.shape[0], 1), dtype=float)]) if arr.size else np.zeros((len(atoms), len(action_ids)), dtype=float)
        counts.setdefault(aid, 0)
        return len(action_ids) - 1

    for row in patches:
        aid = str(row.get("action_id") or row.get("action") or "")
        atom = str(row.get("carrier_atom") or row.get("atom") or "")
        if not aid or not atom:
            continue
        mean = float(row.get("mean_delta", row.get("delta", 0.0)) or 0.0)
        safe_dir = bool(row.get("safe_direction", mean >= 0.0))
        if require_safe and not safe_dir:
            continue
        cnt = max(1, int(row.get("count", 1) or 1))
        eff_count = float(cnt) * float(patch_weight)
        i = ensure_atom(atom)
        j = ensure_action(aid)
        old_count = float(counts.get(aid, 0))
        old = float(arr[i, j])
        arr[i, j] = (old_count * old + eff_count * mean) / (old_count + eff_count) if (old_count + eff_count) > 0 else mean
        counts[aid] = int(old_count + cnt)
        patch_records.append({"action_id": aid, "carrier_atom": atom, "mean_delta": mean, "count": cnt, "safe_direction": safe_dir})

    meta = dict(cm.metadata or {})
    meta.setdefault("patches", []).append({
        "source": str(patches_path),
        "n_input": len(patches),
        "n_merged": len(patch_records),
        "patch_weight": patch_weight,
        "require_safe": require_safe,
        "canonical_status": "carrier_incidence_patch_chart_not_canonical",
    })
    merged = CarrierMatrix(atoms=atoms, action_ids=action_ids, matrix=arr.tolist(), counts=counts, metadata=meta)
    if out:
        merged.save(out)
    return merged


def carrier_patch_report(patches_path: str | Path, out: str | Path | None = None) -> dict[str, Any]:
    rows = read_jsonl(patches_path)
    by_atom: dict[str, list[float]] = {}
    by_action: dict[str, int] = {}
    for r in rows:
        atom = str(r.get("carrier_atom") or r.get("atom") or "")
        aid = str(r.get("action_id") or "")
        if atom:
            by_atom.setdefault(atom, []).append(float(r.get("mean_delta", 0.0) or 0.0))
        if aid:
            by_action[aid] = by_action.get(aid, 0) + 1
    rep = {
        "source": str(patches_path),
        "n_patches": len(rows),
        "n_atoms": len(by_atom),
        "n_actions": len(by_action),
        "atoms": [{"atom": k, "mean_delta": float(np.mean(v)) if v else 0.0, "n": len(v)} for k, v in sorted(by_atom.items())],
        "canonical_status": "patch_report_only",
    }
    if out:
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")
    return rep


__all__ = ["CarrierMatrix", "build_carrier_matrix_from_responses", "annotate_actions_with_carrier_matrix", "carrier_safe_action_ids", "multi_carrier_report", "carrier_defect_mean", "merge_carrier_incidence_patches", "carrier_patch_report"]
