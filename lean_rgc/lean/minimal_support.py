"""M2: proof-term minimal support accessors.

After a kernel_rpc tactic application assigns a goal mvar, the v3 worker
payload (`lean-rgc-kernel-state-v3`) carries `minimal_support`: per closed
goal, `used_hypotheses` — the local-context fvars occurring in the
instantiated proof term, expanded to their dependency closure in the local
context — and `used_constants` — the bounded list of constants the proof
references.  This is the exact rung of the M1 reuse ladder (the honest
version of K3's textual dependency-closure proxy) and the anti-overfit
canonicalization input for the S6 lemma foundry.

Accessors are shape-permissive: they accept a raw v3 kernel payload, a
structured-state row (``StructuredProofState.to_dict()``), an ``apply_tactic``
reply (``state_delta`` / ``kernel_state_after``), or an audit row whose
``audit_flags`` embed those objects.
"""

from __future__ import annotations

from typing import Any, Iterator

from ..schemas import stable_hash

SCHEMA_MINIMAL_SUPPORT = "lean-rgc-minimal-support-v1"


def _support_obj(d: dict[str, Any]) -> dict[str, Any] | None:
    ms = d.get("minimal_support")
    if isinstance(ms, dict) and isinstance(ms.get("goals"), list):
        return ms
    if isinstance(ms, list):
        return {"schema_version": SCHEMA_MINIMAL_SUPPORT, "goals": ms}
    return None


def _candidate_dicts(payload: dict[str, Any]) -> Iterator[dict[str, Any]]:
    yield payload
    for key in ("state_delta", "kernel_state_after", "kernel_state", "delta"):
        v = payload.get(key)
        if isinstance(v, dict):
            yield v
    audit = payload.get("audit") if isinstance(payload.get("audit"), dict) else {}
    flags = payload.get("audit_flags") or audit.get("audit_flags") or {}
    if isinstance(flags, dict):
        for key in ("state_delta", "kernel_state_after"):
            v = flags.get(key)
            if isinstance(v, dict):
                yield v


def minimal_support_goals(payload: Any) -> list[dict[str, Any]]:
    """Per-closed-goal minimal-support entries carried by ``payload``.

    Empty list when the payload predates v3 or no goal was closed.  Note the
    face-taxonomy ``minimal_support`` (keyed by ``rows``/``contexts``) is a
    different object and is deliberately not matched here.
    """
    if not isinstance(payload, dict):
        return []
    for d in _candidate_dicts(payload):
        ms = _support_obj(d)
        if ms is not None:
            return [dict(g) for g in ms["goals"] if isinstance(g, dict)]
    return []


def support_by_mvar(payload: Any) -> dict[str, dict[str, Any]]:
    return {str(g["mvar_id"]): g for g in minimal_support_goals(payload) if g.get("mvar_id")}


def used_hypothesis_names(goal_entry: dict[str, Any]) -> list[str]:
    """User names of the hypotheses in a goal's minimal support (lctx order)."""
    names = goal_entry.get("used_hypothesis_names")
    if isinstance(names, list) and names:
        return [str(n) for n in names if str(n)]
    out: list[str] = []
    for h in goal_entry.get("used_hypotheses") or []:
        if isinstance(h, dict):
            name = str(h.get("user_name") or h.get("fvar_id") or "")
        else:
            name = str(h)
        if name:
            out.append(name)
    return out


def used_constants(goal_entry: dict[str, Any]) -> list[str]:
    return [str(c) for c in goal_entry.get("used_constants") or []]


def support_signature(goal_entry: dict[str, Any], *, target_text: str = "") -> dict[str, Any]:
    """Order-insensitive canonical signature of one goal's minimal support.

    Hypotheses enter by their (sorted) type texts, not their names, so the
    signature is alpha-invariant at the hypothesis-name level — the M2 rung of
    the M1 key ladder.  ``target_text`` is the caller-supplied goal target
    (the support entry itself does not repeat it).
    """
    hyp_types = sorted(
        str(h.get("type_text") or "")
        for h in goal_entry.get("used_hypotheses") or []
        if isinstance(h, dict) and not h.get("is_implementation_detail")
    )
    return {
        "schema_version": SCHEMA_MINIMAL_SUPPORT,
        "target_text": str(target_text or ""),
        "hypothesis_types": hyp_types,
        "constants": sorted(used_constants(goal_entry)),
        "fully_closed": bool(goal_entry.get("fully_closed", not goal_entry.get("residual_mvars"))),
    }


def support_key(goal_entry: dict[str, Any], *, target_text: str = "", n: int = 24) -> str:
    return stable_hash(support_signature(goal_entry, target_text=target_text), n=n)


__all__ = [
    "SCHEMA_MINIMAL_SUPPORT",
    "minimal_support_goals",
    "support_by_mvar",
    "support_key",
    "support_signature",
    "used_constants",
    "used_hypothesis_names",
]
