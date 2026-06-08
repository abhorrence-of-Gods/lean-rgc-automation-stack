from __future__ import annotations

from pathlib import Path
from typing import Any
import csv
import json

from .schemas import read_jsonl


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _as_action(row: dict[str, Any]) -> dict[str, Any]:
    if isinstance(row.get("action"), dict):
        return dict(row["action"])
    if isinstance(row.get("metadata"), dict) and isinstance(row["metadata"].get("action"), dict):
        return dict(row["metadata"]["action"])
    return row


def _task_id(row: dict[str, Any], action: dict[str, Any] | None = None) -> str:
    action = action if action is not None else _as_action(row)
    meta = action.get("metadata") if isinstance(action.get("metadata"), dict) else {}
    return str(row.get("task_id") or row.get("state_id") or meta.get("task_id") or meta.get("state_id") or "")


def _action_id(action: dict[str, Any]) -> str:
    return str(action.get("action_id") or action.get("id") or action.get("tactic") or action.get("full_tactic") or "")


def _tactic(action: dict[str, Any]) -> str:
    return str(action.get("tactic") or action.get("full_tactic") or "")


def _keys_for(row: dict[str, Any]) -> set[tuple[str, str]]:
    action = _as_action(row)
    aid = _action_id(action)
    tac = _tactic(action)
    task = _task_id(row, action)
    keys: set[tuple[str, str]] = set()
    if aid:
        keys.add(("id", aid))
        if task:
            keys.add(("task_id", task + "\t" + aid))
    if tac:
        keys.add(("tactic", tac))
        if task:
            keys.add(("task_tactic", task + "\t" + tac))
    return keys


def _status(row: dict[str, Any]) -> str:
    return str(row.get("audit_status") or row.get("status") or "unknown")


def _goal_response(row: dict[str, Any]) -> float:
    resp = row.get("response") or {}
    if not isinstance(resp, dict):
        return 0.0
    s = 0.0
    for k, v in resp.items():
        if str(k).startswith("goal."):
            try:
                s += float(v)
            except Exception:
                pass
    return float(s)


def _carrier_delta(row: dict[str, Any]) -> float:
    cd = row.get("carrier_delta") or {}
    if isinstance(cd, dict):
        out = 0.0
        for v in cd.values():
            try:
                out += float(v)
            except Exception:
                pass
        return float(out)
    return 0.0


def _qgen_meta(row: dict[str, Any]) -> dict[str, Any]:
    action = _as_action(row)
    meta = action.get("metadata") if isinstance(action.get("metadata"), dict) else {}
    qg = meta.get("qgen") if isinstance(meta.get("qgen"), dict) else {}
    return qg


def _source_label(path: Path) -> str:
    name = path.name
    if "registry_robust" in name:
        return "qgen_registry_robust"
    if "registry_accepted" in name:
        return "qgen_registry"
    if "robust" in name:
        return "qgen_robust"
    if "accepted" in name:
        return "qgen"
    return path.stem


def _default_accepted_files(rdir: Path) -> list[Path]:
    return [
        rdir / "qgen_robust_accepted_actions.jsonl",
        rdir / "qgen_accepted_actions.jsonl",
        rdir / "qgen_registry_robust_accepted_actions.jsonl",
        rdir / "qgen_registry_accepted_actions.jsonl",
    ]


def _read_actions_by_round(rdir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for p in _default_accepted_files(rdir):
        if not p.exists():
            continue
        for row in read_jsonl(p):
            row = dict(row)
            row.setdefault("_accepted_source", _source_label(p))
            rows.append(row)
    return rows


def _index_responses(rows: list[dict[str, Any]]) -> dict[tuple[str, str], list[dict[str, Any]]]:
    idx: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        for k in _keys_for(row):
            idx.setdefault(k, []).append(row)
    return idx


def _best_matches(action_row: dict[str, Any], index: dict[tuple[str, str], list[dict[str, Any]]]) -> list[dict[str, Any]]:
    keys = list(_keys_for(action_row))
    # Prefer exact task+tactic/id keys over global tactic keys.
    priority = {"task_id": 0, "task_tactic": 1, "id": 2, "tactic": 3}
    keys.sort(key=lambda x: priority.get(x[0], 10))
    seen: set[int] = set()
    out: list[dict[str, Any]] = []
    for k in keys:
        vals = index.get(k, [])
        if vals:
            for v in vals:
                ident = id(v)
                if ident not in seen:
                    seen.add(ident); out.append(v)
            # Stop at first successful key kind; otherwise global tactic can overmatch.
            return out
    return out


def collect_qgen_realized_calibration(run_dir: str | Path, *, out_json: str | Path | None = None, out_csv: str | Path | None = None) -> dict[str, Any]:
    """Compare qgen accepted actions in round r against next-round base audit responses.

    This is a finite chart diagnostic, not a canonical promotion rule.  It asks whether
    accepted qgen witnesses are re-audited in the next round and still show positive
    realized goal/carrier response.
    """
    root = Path(run_dir)
    round_dirs = sorted([p for p in root.glob("round_*") if p.is_dir()])
    rows_out: list[dict[str, Any]] = []
    round_summaries: list[dict[str, Any]] = []
    for i, rdir in enumerate(round_dirs[:-1]):
        next_dir = round_dirs[i + 1]
        accepted = _read_actions_by_round(rdir)
        next_responses_path = next_dir / "audit" / "responses.jsonl"
        next_rows = read_jsonl(next_responses_path) if next_responses_path.exists() else []
        idx = _index_responses(next_rows)
        matched = 0
        goals: list[float] = []
        carriers: list[float] = []
        succ = 0
        by_src: dict[str, dict[str, Any]] = {}
        for a in accepted:
            matches = _best_matches(a, idx)
            src = str(a.get("_accepted_source") or "qgen")
            bd = by_src.setdefault(src, {"n_accepted": 0, "n_reaudited": 0, "success": 0, "mean_goal_response": 0.0, "mean_carrier_delta": 0.0})
            bd["n_accepted"] += 1
            if not matches:
                rows_out.append({
                    "round": i,
                    "next_round": i + 1,
                    "accepted_source": src,
                    "action": _as_action(a),
                    "matched": False,
                    "canonical_status": "realized_response_chart_only_not_canonical",
                })
                continue
            matched += 1
            # Aggregate all matched rows for this action key.
            gr = sum(_goal_response(m) for m in matches) / max(1, len(matches))
            cd = sum(_carrier_delta(m) for m in matches) / max(1, len(matches))
            ok = any(_status(m) in {"success", "partial", "dry_run"} for m in matches)
            goals.append(gr); carriers.append(cd); succ += int(ok)
            bd["n_reaudited"] += 1
            bd["success"] += int(ok)
            bd["mean_goal_response"] += gr
            bd["mean_carrier_delta"] += cd
            qg = _qgen_meta(a)
            rows_out.append({
                "round": i,
                "next_round": i + 1,
                "accepted_source": src,
                "matched": True,
                "n_matches": len(matches),
                "goal_response_next": gr,
                "carrier_delta_next": cd,
                "success_next": ok,
                "action": _as_action(a),
                "qgen_lineage_id": qg.get("lineage_id"),
                "parent_residual_keys": qg.get("parent_residual_keys", []),
                "canonical_status": "realized_response_chart_only_not_canonical",
            })
        for d in by_src.values():
            n = max(1, int(d["n_reaudited"]))
            d["success_rate"] = d["success"] / n if d["n_reaudited"] else None
            if d["n_reaudited"]:
                d["mean_goal_response"] /= n
                d["mean_carrier_delta"] /= n
            else:
                d["mean_goal_response"] = None
                d["mean_carrier_delta"] = None
        round_summaries.append({
            "round": i,
            "next_round": i + 1,
            "round_dir": str(rdir),
            "next_round_dir": str(next_dir),
            "n_accepted": len(accepted),
            "n_reaudited_next": matched,
            "match_rate": matched / max(1, len(accepted)) if accepted else None,
            "success_rate_next": succ / max(1, matched) if matched else None,
            "mean_goal_response_next": sum(goals) / max(1, len(goals)) if goals else None,
            "mean_carrier_delta_next": sum(carriers) / max(1, len(carriers)) if carriers else None,
            "by_source": by_src,
        })
    all_matched = sum(int(r.get("matched", False)) for r in rows_out)
    all_rows = len(rows_out)
    matched_rows = [r for r in rows_out if r.get("matched")]
    summary = {
        "run_dir": str(root),
        "canonical_status": "realized_response_chart_only_not_canonical",
        "n_round_pairs": max(0, len(round_dirs) - 1),
        "n_accepted_records": all_rows,
        "n_reaudited_records": all_matched,
        "match_rate": all_matched / max(1, all_rows) if all_rows else None,
        "success_rate_next": sum(1 for r in matched_rows if r.get("success_next")) / max(1, len(matched_rows)) if matched_rows else None,
        "mean_goal_response_next": sum(float(r.get("goal_response_next", 0.0)) for r in matched_rows) / max(1, len(matched_rows)) if matched_rows else None,
        "mean_carrier_delta_next": sum(float(r.get("carrier_delta_next", 0.0)) for r in matched_rows) / max(1, len(matched_rows)) if matched_rows else None,
    }
    rep = {"summary": summary, "rounds": round_summaries, "rows": rows_out}
    if out_json:
        p = Path(out_json); p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")
    if out_csv:
        p = Path(out_csv); p.parent.mkdir(parents=True, exist_ok=True)
        keys: list[str] = []
        flat_rows = []
        for r in rows_out:
            fr = dict(r)
            fr["action"] = json.dumps(fr.get("action", {}), ensure_ascii=False)
            fr["parent_residual_keys"] = json.dumps(fr.get("parent_residual_keys", []), ensure_ascii=False)
            flat_rows.append(fr)
            for k in fr:
                if k not in keys:
                    keys.append(k)
        with p.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=keys)
            w.writeheader()
            for r in flat_rows:
                w.writerow(r)
    return rep


__all__ = ["collect_qgen_realized_calibration"]
