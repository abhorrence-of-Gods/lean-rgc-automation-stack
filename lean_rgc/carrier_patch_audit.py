from __future__ import annotations

from pathlib import Path
from typing import Any
import json

from .schemas import read_jsonl, write_jsonl, stable_hash


def _as_action(row: dict[str, Any]) -> dict[str, Any]:
    return dict(row.get("action")) if isinstance(row.get("action"), dict) else row


def _aid(row: dict[str, Any]) -> str:
    a = _as_action(row)
    return str(a.get("action_id") or row.get("action_id") or a.get("tactic") or row.get("tactic") or "")


def _task(row: dict[str, Any]) -> str:
    a = _as_action(row)
    meta = a.get("metadata") if isinstance(a.get("metadata"), dict) else {}
    return str(row.get("task_id") or row.get("state_id") or meta.get("task_id") or meta.get("state_id") or "")


def _carrier_delta(row: dict[str, Any], atom: str) -> float | None:
    cd = row.get("carrier_delta") or {}
    if isinstance(cd, dict) and atom in cd:
        try:
            return float(cd.get(atom, 0.0))
        except Exception:
            return None
    resp = row.get("response") or {}
    key = "carrier." + atom
    if isinstance(resp, dict) and key in resp:
        try:
            return float(resp.get(key, 0.0))
        except Exception:
            return None
    return None


def _frac_for_response(row: dict[str, Any], *, salt: str = "carrier_patch_holdout") -> float:
    key = {"salt": salt, "action": _aid(row), "task": _task(row), "status": row.get("status") or row.get("audit_status")}
    h = stable_hash(key, 12)
    return int(h, 16) / float(16 ** len(h))


def _stats(vals: list[float], pred: float, *, min_count: int, min_mean_delta: float, require_sign_agreement: bool) -> dict[str, Any]:
    mean_obs = sum(vals) / max(1, len(vals)) if vals else 0.0
    sign_ok = (pred == 0.0 or mean_obs == 0.0 or (pred > 0) == (mean_obs > 0))
    ok = bool(len(vals) >= min_count and mean_obs >= min_mean_delta and (sign_ok or not require_sign_agreement))
    return {"count": len(vals), "mean_delta": mean_obs, "sign_agreement": sign_ok, "accepted": ok}


def audit_carrier_incidence_patches(
    patches_path: str | Path,
    responses_path: str | Path,
    *,
    out_report: str | Path | None = None,
    out_patches: str | Path | None = None,
    min_count: int = 1,
    min_mean_delta: float = 0.0,
    require_sign_agreement: bool = True,
    holdout_fraction: float = 0.0,
    heldout_min_count: int | None = None,
    heldout_min_mean_delta: float | None = None,
    require_heldout: bool = False,
    holdout_salt: str = "carrier_patch_holdout",
) -> dict[str, Any]:
    """Audit qgen carrier-incidence patches against measured carrier deltas.

    By default this preserves the v17 behavior: all available audit rows for an action are
    pooled and a patch is accepted if the observed carrier delta has sufficient count,
    sufficient mean, and sign agreement.

    If ``holdout_fraction > 0`` or ``require_heldout`` is set, the audit rows are split by
    a stable hash into train and holdout charts.  A patch is accepted only if the pooled
    audit passes and the train split passes; if ``require_heldout`` is true, the holdout
    split must also pass.  This is still a finite audit chart, not canonical promotion.
    """
    patches = read_jsonl(patches_path) if Path(patches_path).exists() else []
    responses = read_jsonl(responses_path) if Path(responses_path).exists() else []
    holdout_fraction = max(0.0, min(0.95, float(holdout_fraction or 0.0)))
    heldout_min_count = min_count if heldout_min_count is None else int(heldout_min_count)
    heldout_min_mean_delta = min_mean_delta if heldout_min_mean_delta is None else float(heldout_min_mean_delta)

    by_action: dict[str, list[dict[str, Any]]] = {}
    for r in responses:
        aid = _aid(r)
        if aid:
            by_action.setdefault(aid, []).append(r)

    rows: list[dict[str, Any]] = []
    accepted: list[dict[str, Any]] = []
    for p in patches:
        aid = str(p.get("action_id") or p.get("action") or "")
        atom = str(p.get("carrier_atom") or p.get("atom") or "")
        pred = float(p.get("mean_delta", p.get("delta", 0.0)) or 0.0)
        vals_all: list[float] = []
        vals_train: list[float] = []
        vals_hold: list[float] = []
        for r in by_action.get(aid, []):
            v = _carrier_delta(r, atom)
            if v is None:
                continue
            fv = float(v)
            vals_all.append(fv)
            if holdout_fraction > 0.0 and _frac_for_response(r, salt=holdout_salt) < holdout_fraction:
                vals_hold.append(fv)
            else:
                vals_train.append(fv)
        # With no holdout split, train is the same as all for backward compatibility.
        if holdout_fraction <= 0.0 and not require_heldout:
            vals_train = list(vals_all)
        all_stats = _stats(vals_all, pred, min_count=min_count, min_mean_delta=min_mean_delta, require_sign_agreement=require_sign_agreement)
        train_stats = _stats(vals_train, pred, min_count=min_count, min_mean_delta=min_mean_delta, require_sign_agreement=require_sign_agreement)
        hold_stats = _stats(vals_hold, pred, min_count=heldout_min_count, min_mean_delta=heldout_min_mean_delta, require_sign_agreement=require_sign_agreement)
        accepted_flag = bool(all_stats["accepted"] and train_stats["accepted"] and (hold_stats["accepted"] if require_heldout else True))
        row = dict(p)
        # Preserve v17 flat fields.
        row["audit_count"] = int(all_stats["count"])
        row["observed_mean_delta"] = float(all_stats["mean_delta"])
        row["sign_agreement"] = bool(all_stats["sign_agreement"])
        row["accepted_by_patch_audit"] = accepted_flag
        # Add v18 robust fields.
        row["train_audit_count"] = int(train_stats["count"])
        row["train_observed_mean_delta"] = float(train_stats["mean_delta"])
        row["train_sign_agreement"] = bool(train_stats["sign_agreement"])
        row["train_patch_audit_pass"] = bool(train_stats["accepted"])
        row["holdout_audit_count"] = int(hold_stats["count"])
        row["holdout_observed_mean_delta"] = float(hold_stats["mean_delta"])
        row["holdout_sign_agreement"] = bool(hold_stats["sign_agreement"])
        row["holdout_patch_audit_pass"] = bool(hold_stats["accepted"])
        row["accepted_by_heldout_patch_audit"] = bool(accepted_flag and require_heldout)
        row.setdefault("evidence", {})
        if isinstance(row["evidence"], dict):
            row["evidence"].update({
                "carrier_patch_audit": {
                    "responses": str(responses_path),
                    "min_count": min_count,
                    "min_mean_delta": min_mean_delta,
                    "require_sign_agreement": require_sign_agreement,
                    "holdout_fraction": holdout_fraction,
                    "heldout_min_count": heldout_min_count,
                    "heldout_min_mean_delta": heldout_min_mean_delta,
                    "require_heldout": require_heldout,
                    "canonical_status": "carrier_patch_audit_chart_only_not_canonical",
                }
            })
        rows.append(row)
        if accepted_flag:
            accepted.append(row)

    by_atom: dict[str, dict[str, Any]] = {}
    for r in rows:
        atom = str(r.get("carrier_atom") or r.get("atom") or "")
        d = by_atom.setdefault(atom, {"n": 0, "accepted": 0, "mean_observed_delta": 0.0, "holdout_n": 0, "holdout_accepted": 0, "mean_holdout_delta": 0.0})
        d["n"] += 1
        d["accepted"] += int(bool(r.get("accepted_by_patch_audit")))
        d["mean_observed_delta"] += float(r.get("observed_mean_delta", 0.0))
        d["holdout_n"] += int(bool(r.get("holdout_audit_count", 0)))
        d["holdout_accepted"] += int(bool(r.get("holdout_patch_audit_pass")))
        d["mean_holdout_delta"] += float(r.get("holdout_observed_mean_delta", 0.0))
    for d in by_atom.values():
        n = max(1, int(d["n"]))
        hn = max(1, int(d["holdout_n"]))
        d["mean_observed_delta"] /= n
        d["accept_rate"] = d["accepted"] / n
        d["mean_holdout_delta"] /= hn
        d["holdout_accept_rate"] = d["holdout_accepted"] / hn if d["holdout_n"] else None
    rep = {
        "patches": str(patches_path),
        "responses": str(responses_path),
        "canonical_status": "carrier_patch_audit_chart_only_not_canonical",
        "n_patches": len(patches),
        "n_audited": sum(1 for r in rows if int(r.get("audit_count", 0)) > 0),
        "n_train_audited": sum(1 for r in rows if int(r.get("train_audit_count", 0)) > 0),
        "n_holdout_audited": sum(1 for r in rows if int(r.get("holdout_audit_count", 0)) > 0),
        "n_accepted": len(accepted),
        "accept_rate": len(accepted) / max(1, len(patches)) if patches else None,
        "settings": {
            "min_count": min_count,
            "min_mean_delta": min_mean_delta,
            "require_sign_agreement": require_sign_agreement,
            "holdout_fraction": holdout_fraction,
            "heldout_min_count": heldout_min_count,
            "heldout_min_mean_delta": heldout_min_mean_delta,
            "require_heldout": require_heldout,
        },
        "by_atom": by_atom,
    }
    if out_report:
        p = Path(out_report); p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({**rep, "rows": rows}, indent=2, ensure_ascii=False), encoding="utf-8")
    if out_patches:
        write_jsonl(out_patches, accepted)
    return {**rep, "rows": rows}


__all__ = ["audit_carrier_incidence_patches"]
