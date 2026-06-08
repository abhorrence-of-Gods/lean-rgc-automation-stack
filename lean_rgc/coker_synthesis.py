from __future__ import annotations

"""Coker-driven context synthesis for Lean-RGC.

This module implements the first system-side step from a hand-written chart
universe toward a response-mined quotient universe:

    audited responses -> per-state coker residuals -> coker-normal scoring of
    audited action archetypes -> new auditable proof-context candidates.

The output is deliberately a *candidate chart*, not a canonical object.  Every
synthesized action must still be micro-audited and pass POMS/coker acceptance.
"""

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable
import json
import re

import numpy as np

from .coker import project_onto_response_cone
from .defect_registry import DefectAtom, DefectRegistry
from .schemas import TacticAction, read_jsonl, stable_hash, write_jsonl


_KEY_RE = re.compile(r"[^A-Za-z0-9_]+")


def _sanitize_key(k: str) -> str:
    s = _KEY_RE.sub("_", str(k)).strip("_").lower()
    return s or "coord"


def _action_dict(row: dict[str, Any]) -> dict[str, Any]:
    a = row.get("action")
    return a if isinstance(a, dict) else {}


def _status(row: dict[str, Any]) -> str:
    return str(row.get("audit_status") or row.get("status") or "unknown")


def _carrier_delta(row: dict[str, Any]) -> dict[str, float]:
    cd = row.get("carrier_delta") or {}
    if not isinstance(cd, dict):
        return {}
    out: dict[str, float] = {}
    for k, v in cd.items():
        try:
            out[str(k)] = float(v)
        except Exception:
            pass
    return out


def _flat_from_dict_blocks(d: dict[str, Any], keys: list[str]) -> np.ndarray:
    vals: list[float] = []
    for key in keys:
        if "." in key:
            block, atom = key.split(".", 1)
            bd = d.get(block)
            if isinstance(bd, dict):
                try:
                    vals.append(float(bd.get(atom, 0.0)))
                    continue
                except Exception:
                    pass
        try:
            vals.append(float(d.get(key, 0.0)))
        except Exception:
            vals.append(0.0)
    return np.asarray(vals, dtype=float)


def _align_vector(row: dict[str, Any], *, field: str, keys: list[str] | None = None) -> tuple[np.ndarray, list[str]]:
    """Return a vector aligned to keys from a response/defect field.

    field may be "response" or "defect_before"/"defect"/"defect_after".
    """
    if field == "response":
        if keys is None and isinstance(row.get("response_keys"), list) and isinstance(row.get("response_flat"), list):
            return np.asarray(row.get("response_flat") or [], dtype=float), list(map(str, row.get("response_keys") or []))
        if keys is not None:
            if isinstance(row.get("response_keys"), list) and isinstance(row.get("response_flat"), list):
                m = {str(k): float(v) for k, v in zip(row.get("response_keys") or [], row.get("response_flat") or [])}
                return np.asarray([m.get(k, 0.0) for k in keys], dtype=float), keys
            if isinstance(row.get("response"), dict):
                resp = row.get("response") or {}
                return np.asarray([float(resp.get(k, 0.0) or 0.0) for k in keys], dtype=float), keys
        return np.zeros(0, dtype=float), keys or []

    obj = row.get(field) or row.get("defect_before") or row.get("defect") or {}
    if not isinstance(obj, dict):
        return np.zeros(0, dtype=float), keys or []
    if keys is None and isinstance(obj.get("flat_keys"), list) and isinstance(obj.get("flat"), list):
        return np.asarray(obj.get("flat") or [], dtype=float), list(map(str, obj.get("flat_keys") or []))
    if keys is not None:
        if isinstance(obj.get("flat_keys"), list) and isinstance(obj.get("flat"), list):
            m = {str(k): float(v) for k, v in zip(obj.get("flat_keys") or [], obj.get("flat") or [])}
            return np.asarray([m.get(k, 0.0) for k in keys], dtype=float), keys
        return _flat_from_dict_blocks(obj, keys), keys
    # Last-resort stable flattening.
    flat_keys: list[str] = []
    flat_vals: list[float] = []
    for block in ("goal", "type", "search", "carrier", "audit"):
        bd = obj.get(block)
        if isinstance(bd, dict):
            for k in sorted(bd):
                flat_keys.append(f"{block}.{k}")
                try:
                    flat_vals.append(float(bd[k]))
                except Exception:
                    flat_vals.append(0.0)
    return np.asarray(flat_vals, dtype=float), flat_keys


def _mean(vs: list[np.ndarray], dim: int) -> np.ndarray:
    if not vs:
        return np.zeros(dim, dtype=float)
    return np.mean(np.stack(vs), axis=0)


def _std(vs: list[np.ndarray], dim: int) -> np.ndarray:
    if len(vs) < 2:
        return np.zeros(dim, dtype=float)
    return np.std(np.stack(vs), axis=0)


@dataclass
class CokerProfile:
    state_id: str
    task_id: str
    response_keys: list[str]
    defect: list[float]
    projection: list[float]
    residual: list[float]
    normal: list[float]
    defect_norm: float
    projection_norm: float
    residual_norm: float
    relative_residual: float
    support_value: float
    active_count: int
    top_residual: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ActionArchetype:
    archetype_id: str
    tactic: str
    tactic_class: str
    carrier_tags: list[str]
    response_keys: list[str]
    mean_response: list[float]
    std_response: list[float]
    mean_carrier_delta: dict[str, float]
    success_rate: float
    support: int
    mean_cost: float
    source_action_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SynthesizedContext:
    task_id: str
    state_id: str
    action: dict[str, Any]
    archetype_id: str
    score: float
    raw_surplus: float
    support_value: float
    coker_dot: float
    carrier_gain: float
    uncertainty_penalty: float
    success_rate: float
    top_residual: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        out = dict(d["action"])
        out["task_id"] = self.task_id
        meta = dict(out.get("metadata") or {})
        meta.update({
            "generated_by": "coker_driven_synthesis",
            "source_archetype_id": self.archetype_id,
            "source_state_id": self.state_id,
            "coker_score": self.score,
            "coker_raw_surplus": self.raw_surplus,
            "coker_dot": self.coker_dot,
            "coker_support_value": self.support_value,
            "coker_carrier_gain": self.carrier_gain,
            "coker_uncertainty_penalty": self.uncertainty_penalty,
            "coker_success_rate": self.success_rate,
            "top_residual": self.top_residual,
        })
        out["metadata"] = meta
        return out


@dataclass
class CokerSynthesisSummary:
    n_response_rows: int
    n_profiles: int
    n_archetypes: int
    n_synthesized: int
    n_atoms: int
    mean_relative_residual: float
    max_relative_residual: float
    top_residual_keys: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class CokerDrivenSynthesizer:
    """Generate proof-context candidates from coker residual normals.

    This is the first implementation of the theoretical transition

        human-designed chart universe -> response-mined quotient universe ->
        coker-driven context synthesis.

    It is intentionally conservative: it retrieves and re-tags audited action
    archetypes rather than inventing arbitrary Lean syntax.
    """

    def __init__(
        self,
        *,
        ridge: float = 1e-4,
        max_mass: float = 1.0,
        cost_weight: float = 0.05,
        carrier_weight: float = 0.25,
        uncertainty_weight: float = 0.10,
        failure_penalty: float = 0.25,
        margin_threshold: float = 0.0,
        min_archetype_support: int = 1,
        max_per_state: int = 16,
        top_k_residual: int = 8,
    ):
        self.ridge = float(ridge)
        self.max_mass = float(max_mass)
        self.cost_weight = float(cost_weight)
        self.carrier_weight = float(carrier_weight)
        self.uncertainty_weight = float(uncertainty_weight)
        self.failure_penalty = float(failure_penalty)
        self.margin_threshold = float(margin_threshold)
        self.min_archetype_support = int(min_archetype_support)
        self.max_per_state = int(max_per_state)
        self.top_k_residual = int(top_k_residual)

    @staticmethod
    def _archetype_key(row: dict[str, Any], mode: str = "tactic") -> str:
        a = _action_dict(row)
        tactic = str(a.get("tactic") or row.get("tactic") or "")
        cls = str(a.get("tactic_class") or a.get("class") or row.get("tactic_class") or "unknown")
        tags = sorted(map(str, a.get("carrier_tags") or []))
        if mode == "class":
            return stable_hash({"class": cls, "tags": tags}, 12)
        if mode == "class+tactic_head":
            head = tactic.strip().split()[0] if tactic.strip() else ""
            return stable_hash({"class": cls, "head": head, "tags": tags}, 12)
        return stable_hash({"tactic": tactic, "class": cls, "tags": tags}, 14)

    def compute_profiles(self, response_rows: list[dict[str, Any]]) -> list[CokerProfile]:
        by_state: dict[str, list[dict[str, Any]]] = {}
        for row in response_rows:
            sid = str(row.get("state_id") or "")
            if sid:
                by_state.setdefault(sid, []).append(row)
        profiles: list[CokerProfile] = []
        for sid, rows in by_state.items():
            # Pick a stable key set.  Response keys usually equal defect flat keys.
            _, keys = _align_vector(rows[0], field="response", keys=None)
            if not keys:
                _, keys = _align_vector(rows[0], field="defect_before", keys=None)
            if not keys:
                continue
            defect, _ = _align_vector(rows[0], field="defect_before", keys=keys)
            R: list[np.ndarray] = []
            for r in rows:
                rv, _ = _align_vector(r, field="response", keys=keys)
                if rv.size == defect.size:
                    R.append(rv)
            if not R:
                continue
            rep = project_onto_response_cone(defect, np.stack(R), ridge=self.ridge, max_mass=self.max_mass)
            residual = np.asarray(rep.residual, dtype=float)
            top_idx = np.argsort(-np.maximum(residual, 0.0))[: self.top_k_residual]
            top: list[dict[str, Any]] = []
            for i in top_idx:
                if i < len(keys) and residual[i] > 1e-9:
                    top.append({"key": keys[i], "value": float(residual[i])})
            profiles.append(CokerProfile(
                state_id=sid,
                task_id=str(rows[0].get("task_id") or ""),
                response_keys=keys,
                defect=defect.tolist(),
                projection=list(rep.projection),
                residual=list(rep.residual),
                normal=list(rep.normal),
                defect_norm=float(rep.defect_norm),
                projection_norm=float(rep.projection_norm),
                residual_norm=float(rep.residual_norm),
                relative_residual=float(rep.relative_residual),
                support_value=float(rep.support_value),
                active_count=int(rep.active_count),
                top_residual=top,
            ))
        return profiles

    def mine_archetypes(self, response_rows: list[dict[str, Any]], *, mode: str = "tactic") -> list[ActionArchetype]:
        # Use union of response keys for cross-state archetypes.
        key_set: list[str] = []
        seen_keys: set[str] = set()
        for row in response_rows:
            _, ks = _align_vector(row, field="response", keys=None)
            for k in ks:
                if k not in seen_keys:
                    seen_keys.add(k); key_set.append(k)
        if not key_set:
            return []
        buckets: dict[str, list[dict[str, Any]]] = {}
        for row in response_rows:
            key = self._archetype_key(row, mode)
            buckets.setdefault(key, []).append(row)
        out: list[ActionArchetype] = []
        for key, rows in buckets.items():
            if len(rows) < self.min_archetype_support:
                continue
            vecs: list[np.ndarray] = []
            carrier: dict[str, list[float]] = {}
            statuses: list[str] = []
            costs: list[float] = []
            action_ids: list[str] = []
            for r in rows:
                rv, _ = _align_vector(r, field="response", keys=key_set)
                vecs.append(rv)
                statuses.append(_status(r))
                a = _action_dict(r)
                action_ids.append(str(r.get("action_id") or a.get("action_id") or ""))
                try:
                    costs.append(float(a.get("cost_estimate", 1.0) or 1.0))
                except Exception:
                    costs.append(1.0)
                for ck, cv in _carrier_delta(r).items():
                    carrier.setdefault(ck, []).append(cv)
            a0 = _action_dict(rows[0])
            mean_car = {k: float(np.mean(vs)) for k, vs in carrier.items()}
            success_rate = float(sum(1 for s in statuses if s in {"success", "partial", "dry_run"}) / max(1, len(statuses)))
            out.append(ActionArchetype(
                archetype_id=key,
                tactic=str(a0.get("tactic") or rows[0].get("tactic") or ""),
                tactic_class=str(a0.get("tactic_class") or a0.get("class") or "unknown"),
                carrier_tags=list(map(str, a0.get("carrier_tags") or [])),
                response_keys=key_set,
                mean_response=_mean(vecs, len(key_set)).tolist(),
                std_response=_std(vecs, len(key_set)).tolist(),
                mean_carrier_delta=mean_car,
                success_rate=success_rate,
                support=len(rows),
                mean_cost=float(np.mean(costs)) if costs else 1.0,
                source_action_ids=[x for x in action_ids if x],
                metadata={"source": "response_mined_archetype", "mode": mode},
            ))
        return out

    def _archetype_vector_for_profile(self, arch: ActionArchetype, profile: CokerProfile) -> tuple[np.ndarray, np.ndarray]:
        m = {k: float(v) for k, v in zip(arch.response_keys, arch.mean_response)}
        s = {k: float(v) for k, v in zip(arch.response_keys, arch.std_response)}
        rv = np.asarray([m.get(k, 0.0) for k in profile.response_keys], dtype=float)
        uv = np.asarray([s.get(k, 0.0) for k in profile.response_keys], dtype=float)
        return rv, uv

    def synthesize(self, profiles: list[CokerProfile], archetypes: list[ActionArchetype]) -> list[SynthesizedContext]:
        out: list[SynthesizedContext] = []
        for prof in profiles:
            normal = np.asarray(prof.normal, dtype=float)
            candidates: list[SynthesizedContext] = []
            residual_keys = {str(x.get("key")) for x in prof.top_residual}
            for arch in archetypes:
                rv, uv = self._archetype_vector_for_profile(arch, prof)
                if rv.size != normal.size or rv.size == 0:
                    continue
                coker_dot = float(np.dot(normal, rv))
                raw_surplus = float(coker_dot - prof.support_value)
                # Carrier gain is only counted on residual carrier atoms, or all
                # positive carrier gains if no residual carrier key is known.
                carrier_gain = 0.0
                for k, v in arch.mean_carrier_delta.items():
                    kk = f"carrier.{k}" if not str(k).startswith("carrier.") else str(k)
                    if not residual_keys or kk in residual_keys or str(k) in residual_keys:
                        carrier_gain += max(0.0, float(v))
                uncertainty = float(np.linalg.norm(uv))
                fail_pen = self.failure_penalty * max(0.0, 1.0 - float(arch.success_rate))
                score = raw_surplus + self.carrier_weight * carrier_gain - self.cost_weight * float(arch.mean_cost) - self.uncertainty_weight * uncertainty - fail_pen
                if score <= self.margin_threshold:
                    continue
                aid = stable_hash({"src": arch.archetype_id, "state": prof.state_id, "score": round(score, 6)}, 14)
                meta = dict(arch.metadata or {})
                meta.update({
                    "task_id": prof.task_id,
                    "source_response_archetype": arch.to_dict(),
                })
                action = TacticAction(
                    action_id=f"coker:{aid}",
                    tactic=arch.tactic,
                    tactic_class=f"coker:{arch.tactic_class}",
                    carrier_tags=list(dict.fromkeys(list(arch.carrier_tags) + ["coker_synthesized"])),
                    cost_estimate=float(arch.mean_cost),
                    metadata=meta,
                ).to_dict()
                candidates.append(SynthesizedContext(
                    task_id=prof.task_id,
                    state_id=prof.state_id,
                    action=action,
                    archetype_id=arch.archetype_id,
                    score=float(score),
                    raw_surplus=float(raw_surplus),
                    support_value=float(prof.support_value),
                    coker_dot=float(coker_dot),
                    carrier_gain=float(carrier_gain),
                    uncertainty_penalty=float(self.uncertainty_weight * uncertainty),
                    success_rate=float(arch.success_rate),
                    top_residual=prof.top_residual,
                ))
            candidates.sort(key=lambda x: (-x.score, x.action.get("tactic", "")))
            out.extend(candidates[: self.max_per_state])
        # Deduplicate by task/tactic, keep highest score.
        dedup: dict[tuple[str, str], SynthesizedContext] = {}
        for c in out:
            k = (c.task_id, str(c.action.get("tactic") or ""))
            old = dedup.get(k)
            if old is None or c.score > old.score:
                dedup[k] = c
        return sorted(dedup.values(), key=lambda x: (-x.score, x.task_id, x.action.get("tactic", "")))

    def mine_residual_atoms(self, profiles: list[CokerProfile], *, min_total: float = 1e-6, max_atoms: int = 64) -> DefectRegistry:
        totals: dict[str, float] = {}
        supports: dict[str, int] = {}
        examples: dict[str, list[dict[str, Any]]] = {}
        for prof in profiles:
            for item in prof.top_residual:
                key = str(item.get("key"))
                val = float(item.get("value", 0.0) or 0.0)
                if val <= 0:
                    continue
                totals[key] = totals.get(key, 0.0) + val
                supports[key] = supports.get(key, 0) + 1
                examples.setdefault(key, []).append({"state_id": prof.state_id, "task_id": prof.task_id, "value": val})
        ordered = sorted(totals.items(), key=lambda kv: -kv[1])[:max_atoms]
        atoms: list[DefectAtom] = []
        for key, total in ordered:
            if total < min_total:
                continue
            group = key.split(".", 1)[0] if "." in key else "coker"
            atom_id = "coker_residual_" + _sanitize_key(key)
            atoms.append(DefectAtom(
                atom_id=atom_id,
                group=f"coker:{group}",
                detector=f"positive_coker_residual:{key}",
                intervention_templates=[],
                status="open",
                evidence={
                    "source": "coker_driven_synthesis",
                    "residual_key": key,
                    "total_positive_residual": float(total),
                    "support": int(supports.get(key, 0)),
                    "examples": examples.get(key, [])[:8],
                    "status_note": "chart-level residual atom; not canonical until parent non-paid + least repair",
                },
                description=f"Response-mined positive coker residual coordinate for {key}.",
            ))
        return DefectRegistry(atoms=atoms, version="lean-rgc-coker-mined-defects-v0.1", metadata={"source": "coker_driven_synthesis"})

    def run(
        self,
        base_responses: str | Path,
        *,
        archetype_responses: str | Path | None = None,
        out_actions: str | Path | None = None,
        out_profiles: str | Path | None = None,
        out_archetypes: str | Path | None = None,
        out_atoms: str | Path | None = None,
        out_summary: str | Path | None = None,
        archetype_mode: str = "tactic",
    ) -> dict[str, Any]:
        base_rows = read_jsonl(base_responses)
        arch_rows = read_jsonl(archetype_responses) if archetype_responses else base_rows
        profiles = self.compute_profiles(base_rows)
        archetypes = self.mine_archetypes(arch_rows, mode=archetype_mode)
        synth = self.synthesize(profiles, archetypes)
        atoms = self.mine_residual_atoms(profiles)
        rels = [p.relative_residual for p in profiles]
        key_totals: dict[str, float] = {}
        for p in profiles:
            for x in p.top_residual:
                key_totals[str(x.get("key"))] = key_totals.get(str(x.get("key")), 0.0) + float(x.get("value", 0.0) or 0.0)
        top_keys = [{"key": k, "total": float(v)} for k, v in sorted(key_totals.items(), key=lambda kv: -kv[1])[:16]]
        summary = CokerSynthesisSummary(
            n_response_rows=len(base_rows),
            n_profiles=len(profiles),
            n_archetypes=len(archetypes),
            n_synthesized=len(synth),
            n_atoms=len(atoms.atoms),
            mean_relative_residual=float(np.mean(rels)) if rels else 0.0,
            max_relative_residual=float(np.max(rels)) if rels else 0.0,
            top_residual_keys=top_keys,
        ).to_dict()
        if out_actions:
            write_jsonl(out_actions, [s.to_dict() for s in synth])
        if out_profiles:
            write_jsonl(out_profiles, [p.to_dict() for p in profiles])
        if out_archetypes:
            write_jsonl(out_archetypes, [a.to_dict() for a in archetypes])
        if out_atoms:
            atoms.save(out_atoms)
        if out_summary:
            Path(out_summary).parent.mkdir(parents=True, exist_ok=True)
            Path(out_summary).write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        return summary


def run_coker_synthesis(
    base_responses: str | Path,
    *,
    archetype_responses: str | Path | None = None,
    out_actions: str | Path | None = None,
    out_profiles: str | Path | None = None,
    out_archetypes: str | Path | None = None,
    out_atoms: str | Path | None = None,
    out_summary: str | Path | None = None,
    archetype_mode: str = "tactic",
    **kwargs: Any,
) -> dict[str, Any]:
    return CokerDrivenSynthesizer(**kwargs).run(
        base_responses,
        archetype_responses=archetype_responses,
        out_actions=out_actions,
        out_profiles=out_profiles,
        out_archetypes=out_archetypes,
        out_atoms=out_atoms,
        out_summary=out_summary,
        archetype_mode=archetype_mode,
    )


@dataclass
class SynthesisRunReport:
    n_responses: int
    n_audits: int
    n_seed_actions: int
    n_profiles: int
    n_archetypes: int
    n_actions_out: int
    n_defect_atoms_out: int
    n_carrier_patches: int
    out_dir: str
    summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _carrier_incidence_patches_from_rows(rows: list[dict[str, Any]], *, min_count: int = 1) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, str], list[float]] = {}
    for r in rows:
        a = _action_dict(r)
        aid = str(r.get("action_id") or a.get("action_id") or "")
        if not aid:
            continue
        for atom, delta in _carrier_delta(r).items():
            buckets.setdefault((aid, atom), []).append(float(delta))
    out: list[dict[str, Any]] = []
    for (aid, atom), vals in sorted(buckets.items()):
        if len(vals) < min_count:
            continue
        mean = float(np.mean(vals)) if vals else 0.0
        out.append({
            "action_id": aid,
            "carrier_atom": atom,
            "mean_delta": mean,
            "count": len(vals),
            "safe_direction": mean >= 0.0,
            "status": "candidate_incidence_patch",
            "evidence": {"source": "micro_audit_carrier_delta", "meaning": "positive delta reduces carrier defect; negative delta is violation"},
        })
    out.sort(key=lambda r: (abs(float(r.get("mean_delta", 0.0))), int(r.get("count", 0))), reverse=True)
    return out


def synthesize(
    *,
    responses_path: str | Path,
    audits_path: str | Path | None = None,
    actions_path: str | Path | None = None,
    out_dir: str | Path,
    failure_min_support: int = 1,
    ridge: float = 1e-4,
    max_mass: float = 1.0,
    margin_threshold: float = 0.0,
    cost_weight: float = 0.05,
    carrier_weight: float = 0.25,
    uncertainty_weight: float = 0.10,
    failure_penalty: float = 0.25,
    max_per_state: int = 16,
    min_archetype_support: int = 1,
) -> SynthesisRunReport:
    """High-level coker-driven synthesis entry point.

    This wrapper writes the artifact names used by the v12 tests and notebooks:
    synthesized_actions.jsonl, synthesized_defect_atoms.jsonl,
    carrier_incidence_patches.jsonl, and synthesis_report.json.

    All outputs are candidate charts.  They still need Lean micro-audit and POMS
    promotion before they can be treated as paid/canonical.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    responses = read_jsonl(responses_path)
    audits = read_jsonl(audits_path) if audits_path else []
    seed_actions = read_jsonl(actions_path) if actions_path else []

    synth = CokerDrivenSynthesizer(
        ridge=ridge,
        max_mass=max_mass,
        margin_threshold=margin_threshold,
        cost_weight=cost_weight,
        carrier_weight=carrier_weight,
        uncertainty_weight=uncertainty_weight,
        failure_penalty=failure_penalty,
        max_per_state=max_per_state,
        min_archetype_support=min_archetype_support,
    )
    profiles = synth.compute_profiles(responses)
    archetypes = synth.mine_archetypes(responses, mode="tactic")
    contexts = synth.synthesize(profiles, archetypes)
    registry = synth.mine_residual_atoms(profiles)
    carrier_patches = _carrier_incidence_patches_from_rows(responses)

    # Add failure-signature-generated fallback actions as candidate contexts.
    failure_actions: list[dict[str, Any]] = []
    if audits:
        try:
            fs = FailureSignatureMiner(min_support=failure_min_support).mine(audits, responses)
            failure_actions.extend(fs.actions)
            write_jsonl(out / "failure_signature_candidates.jsonl", fs.actions)
            write_jsonl(out / "failure_signatures.jsonl", [s.to_dict() for s in fs.signatures])
        except Exception as e:
            (out / "failure_signature_error.txt").write_text(str(e), encoding="utf-8")

    action_rows = [c.to_dict() for c in contexts]
    # If no coker context was positive, still seed from failure signatures so the
    # next audit can test newly exposed chart hypotheses.
    if failure_actions:
        action_rows.extend(failure_actions)
    # Preserve explicit seed actions in a separate artifact for lineage but do not
    # re-label them as generated actions unless they scored through coker/failure.
    if seed_actions:
        write_jsonl(out / "seed_actions.jsonl", seed_actions)

    write_jsonl(out / "synthesized_actions.jsonl", action_rows)
    write_jsonl(out / "synthesized_defect_atoms.jsonl", [a.to_dict() for a in registry.atoms])
    registry.save(out / "synthesized_defect_registry.json")
    write_jsonl(out / "carrier_incidence_patches.jsonl", carrier_patches)
    write_jsonl(out / "coker_profiles.jsonl", [p.to_dict() for p in profiles])
    write_jsonl(out / "response_archetypes.jsonl", [a.to_dict() for a in archetypes])

    rels = [p.relative_residual for p in profiles]
    summary = {
        "n_response_rows": len(responses),
        "n_profiles": len(profiles),
        "n_archetypes": len(archetypes),
        "n_synthesized_contexts": len(contexts),
        "n_failure_actions": len(failure_actions),
        "n_actions_out": len(action_rows),
        "n_defect_atoms_out": len(registry.atoms),
        "n_carrier_patches": len(carrier_patches),
        "mean_relative_residual": float(np.mean(rels)) if rels else 0.0,
        "max_relative_residual": float(np.max(rels)) if rels else 0.0,
        "canonical_status": "candidate_charts_only_micro_audit_required",
    }
    rep = SynthesisRunReport(
        n_responses=len(responses),
        n_audits=len(audits),
        n_seed_actions=len(seed_actions),
        n_profiles=len(profiles),
        n_archetypes=len(archetypes),
        n_actions_out=len(action_rows),
        n_defect_atoms_out=len(registry.atoms),
        n_carrier_patches=len(carrier_patches),
        out_dir=str(out),
        summary=summary,
    )
    (out / "synthesis_report.json").write_text(json.dumps(rep.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    return rep


def synthesize_from_coker_files(
    base_responses: str | Path,
    out_actions: str | Path,
    *,
    out_report: str | Path | None = None,
    actions: str | Path | None = None,
    audits: str | Path | None = None,
    ridge: float = 1e-4,
    max_mass: float | None = 1.0,
    residual_threshold: float = 1e-6,
    max_residual_keys: int = 12,
    max_actions_per_state: int = 32,
    include_failure_signatures: bool = True,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Compatibility wrapper for the CLI added in v12 notes."""
    out_dir = Path(out_report).parent if out_report else Path(out_actions).parent
    rep = synthesize(
        responses_path=base_responses,
        audits_path=audits if include_failure_signatures else None,
        actions_path=actions,
        out_dir=out_dir,
        ridge=ridge,
        max_mass=1.0 if max_mass is None else float(max_mass),
        margin_threshold=residual_threshold * 0.0,
        max_per_state=max_actions_per_state,
    )
    generated = read_jsonl(out_dir / "synthesized_actions.jsonl")
    write_jsonl(out_actions, generated)
    report = rep.to_dict()
    report["n_states"] = rep.n_profiles
    report["n_unknown_defect_atoms"] = rep.n_defect_atoms_out
    if out_report:
        Path(out_report).parent.mkdir(parents=True, exist_ok=True)
        Path(out_report).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return generated, report


__all__ = [
    "CokerProfile",
    "ActionArchetype",
    "SynthesizedContext",
    "CokerDrivenSynthesizer",
    "run_coker_synthesis",
    "synthesize",
    "synthesize_from_coker_files",
]
