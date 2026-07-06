"""S1: stepwise replay corpus (roadmap rung S1).

Replays verified scripts (and D3-verified failed-script prefixes)
STEP BY STEP through the stateful kernel_rpc lane, recording one
(S, A, E, S') transition per tactic boundary with the full v3 payload
(mvar graphs, state hashes, minimal support). Deterministic — no LLM.

Two halves:
- build_script_inventory(): local, gathers deduped (task_id, script)
  pairs from success rows plus D3 nonzero frozen prefixes.
- replay_scripts(): pod-side, drives LeanServerAdapter sequentially
  (register_task -> apply_tactic_to_state_id(create_state=True) chain),
  with fallback DISABLED (fallback backends fabricate payloads).
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from ..schemas import LeanTask, TacticAction, read_jsonl, write_jsonl
from .prefix_salvage import tactic_boundaries

SCHEMA_STEPWISE = "lean-rgc-stepwise-replay-v99.0"


def split_script(script: str) -> list[str]:
    """Split a verified script at top-level tactic boundaries into
    executable steps (separator-stripped, empties dropped).

    A newline cut is only a step boundary when the next line starts a
    NEW top-level tactic: indented lines and calc/anonymous-constructor
    continuations (_ · | .) belong to the previous step."""
    flat = "\n".join(script.splitlines() or [""])
    cuts = []
    for c in tactic_boundaries(flat):
        if 0 < c < len(flat) and flat[c - 1] == "\n" and flat[c] in " \t_·|.":
            continue
        cuts.append(c)
    cuts = sorted(set(cuts + [len(flat)]))
    steps: list[str] = []
    for a, b in zip(cuts, cuts[1:]):
        seg = flat[a:b].strip().strip(";").strip()
        if seg and seg != ",":
            steps.append(seg)
    return steps


def build_script_inventory(
    waves_roots: list[str | Path],
    *,
    include_d3_prefixes: bool = True,
    d3_waves_roots: list[str | Path] | None = None,
) -> list[dict[str, Any]]:
    """Deduped (task_id, script, source) inventory from success rows in
    pilot-layout or bare-run-layout wave dirs, plus D3 frozen prefixes."""
    from ..grad.twist import load_rows_multi

    seen: set[tuple[str, str]] = set()
    out: list[dict[str, Any]] = []

    def add(task_id: str, script: str, source: str) -> None:
        script = script.strip()
        key = (task_id, script)
        if not task_id or not script or key in seen:
            return
        seen.add(key)
        out.append({"task_id": task_id, "script": script, "source": source, "n_steps": len(split_script(script))})

    for r in load_rows_multi(waves_roots):
        if r.get("status") == "success":
            add(r["task_id"], r["tactic"], "success_script")
    if include_d3_prefixes:
        from .prefix_salvage import estimate_candidates

        for root in (d3_waves_roots or [waves_roots[0]]):
            try:
                records, _diag = estimate_candidates(root)
            except Exception:
                continue
            for rec in records:
                if 0 < rec["f"] < 1 and rec.get("prefix"):
                    add(rec["task_id"], rec["prefix"], "d3_verified_prefix")
    return out


def _kernel_state_of(rec: Any) -> dict[str, Any] | None:
    flags = getattr(rec, "audit_flags", None) or {}
    ks = flags.get("kernel_state")
    return ks if isinstance(ks, dict) else None


def replay_scripts(
    scripts: list[dict[str, Any]],
    task_defs: dict[str, dict[str, Any]],
    *,
    out_dir: str | Path,
    lean_cmd: str = "lake env lean",
    workdir: str | None = None,
    timeout_s: float = 60.0,
    flush_every: int = 50,
    max_scripts: int | None = None,
    recycle_every: int = 40,
) -> dict[str, Any]:
    from ..lean.server import LeanServerAdapter, LeanServerConfig

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    cfg = LeanServerConfig(
        lean_cmd=lean_cmd,
        workdir=workdir,
        timeout_s=timeout_s,
        backend="native",
        native_exec_mode="kernel_rpc",
        fallback_to_file=False,  # fabricating fallbacks poison the corpus
    )
    transitions: list[dict[str, Any]] = []
    chains: list[dict[str, Any]] = []
    counts = {"scripts": 0, "no_taskdef": 0, "register_failed": 0, "transitions": 0, "broken_chains": 0, "worker_recycles": 0}

    def flush() -> None:
        write_jsonl(out / "stepwise_transitions.jsonl", transitions)
        write_jsonl(out / "chains.jsonl", chains)

    t0 = time.time()
    items = list(enumerate(scripts if max_scripts is None else scripts[:max_scripts]))
    # The kernel_rpc worker retains every KState (each pinning a full
    # Environment) with no eviction op in the protocol, so a whole-corpus
    # run OOMs. Chains never span scripts, so recycling the worker at
    # script boundaries is behavior-preserving (S'1 rider, 2026-07-06).
    for chunk_start in range(0, len(items), max(1, recycle_every)):
        chunk = items[chunk_start:chunk_start + max(1, recycle_every)]
        if chunk_start:
            counts["worker_recycles"] += 1
        try:
            server_cm = LeanServerAdapter(cfg)
            server_cm.__enter__()
        except Exception as e:
            # Startup failure at a chunk boundary must not lose completed
            # work: persist, record, and stop honestly.
            counts["startup_failed_chunk"] = chunk_start // max(1, recycle_every)
            counts["startup_error"] = str(e)[:200]
            flush()
            break
        try:
            server = server_cm
            server.load_project()
            for si, item in chunk:
                td = task_defs.get(str(item["task_id"]))
                if td is None:
                    counts["no_taskdef"] += 1
                    continue
                counts["scripts"] += 1
                task = LeanTask.from_dict(td)
                steps = split_script(item["script"])
                if any("sorry" in s or "admit" in s for s in steps):
                    # Defect #6: sorryAx closes goals, so the kernel lane
                    # would report success on a hole. Never execute these.
                    counts["skipped_unsafe"] = counts.get("skipped_unsafe", 0) + 1
                    chains.append({
                        "schema_version": SCHEMA_STEPWISE,
                        "task_id": task.task_id,
                        "source": item.get("source"),
                        "script_index": si,
                        "n_steps": len(steps),
                        "completed_steps": 0,
                        "broken": True,
                        "error": "skipped_unsafe: sorry/admit step",
                    })
                    continue
                chain: dict[str, Any] = {
                    "schema_version": SCHEMA_STEPWISE,
                    "task_id": task.task_id,
                    "source": item.get("source"),
                    "script_index": si,
                    "n_steps": len(steps),
                    "completed_steps": 0,
                    "broken": False,
                }
                try:
                    init = server.register_task(task)
                    state = init.get("state") if isinstance(init, dict) else None
                    sid = str((state or {}).get("state_id") or "")
                    if not sid:
                        raise RuntimeError(f"register_task returned no state_id: {init}")
                except Exception as e:
                    counts["register_failed"] += 1
                    chain["broken"] = True
                    chain["error"] = f"register: {e}"
                    chains.append(chain)
                    continue
                for k, step in enumerate(steps):
                    action = TacticAction(action_id=f"replay_s{k}", tactic=step)
                    try:
                        rec = server.apply_tactic_to_state_id(task, action, sid, create_state=True)
                    except Exception as e:
                        chain["broken"] = True
                        chain["error"] = f"step {k}: {e}"
                        counts["broken_chains"] += 1
                        break
                    ks = _kernel_state_of(rec)
                    after_sid = str((ks or {}).get("state_id") or (rec.after_state.state_id if rec.after_state else ""))
                    transitions.append({
                        "schema_version": SCHEMA_STEPWISE,
                        "task_id": task.task_id,
                        "source": item.get("source"),
                        "script_index": si,
                        "step_index": k,
                        "tactic": step,
                        "status": rec.status,
                        "before_state_id": sid,
                        "after_state_id": after_sid,
                        "elapsed_ms": rec.elapsed_ms,
                        "messages": (rec.messages or [])[:10],
                        "kernel_state_after": ks,
                        "audit_flags": {
                            kk: vv for kk, vv in (rec.audit_flags or {}).items()
                            if kk in ("kernel_state_hash", "structured_state_backend", "server_backend")
                        },
                    })
                    counts["transitions"] += 1
                    if rec.status in ("success", "partial") and isinstance(ks, dict) and str(ks.get("schema_version", "")).endswith("v3"):
                        # Strict gate currency (S'1 amendment b): failure
                        # payloads clone the before-state and must not count.
                        counts["v3_success_transitions"] = counts.get("v3_success_transitions", 0) + 1
                    if rec.status in ("fail", "elab_error", "timeout", "unsafe") or not after_sid:
                        # Verified scripts should not break; record honestly.
                        chain["broken"] = True
                        chain["error"] = f"step {k}: status={rec.status}"
                        counts["broken_chains"] += 1
                        break
                    chain["completed_steps"] = k + 1
                    sid = after_sid
                chains.append(chain)
                if counts["scripts"] % flush_every == 0:
                    flush()
        finally:
            server_cm.__exit__(None, None, None)
            flush()  # chunk-boundary durability: no chunk's work is ever lost
    flush()
    summary = {
        "schema_version": SCHEMA_STEPWISE,
        "counts": counts,
        "elapsed_s": time.time() - t0,
        "out": str(out),
        "canonical_status": "stepwise_replay_corpus_witness_not_canonical",
    }
    (out / "replay_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    inv = sub.add_parser("inventory")
    inv.add_argument("--waves-roots", nargs="+", required=True)
    inv.add_argument("--d3-waves-roots", nargs="+")
    inv.add_argument("--no-d3-prefixes", action="store_true")
    inv.add_argument("--out", required=True)
    rep = sub.add_parser("replay")
    rep.add_argument("--scripts", required=True)
    rep.add_argument("--tasks", required=True)
    rep.add_argument("--out-dir", required=True)
    rep.add_argument("--lean-cmd", default="lake env lean")
    rep.add_argument("--workdir")
    rep.add_argument("--timeout-s", type=float, default=60.0)
    rep.add_argument("--max-scripts", type=int)
    rep.add_argument("--recycle-every", type=int, default=40)
    args = ap.parse_args(argv)
    if args.cmd == "inventory":
        items = build_script_inventory(
            args.waves_roots,
            include_d3_prefixes=not args.no_d3_prefixes,
            d3_waves_roots=args.d3_waves_roots,
        )
        write_jsonl(args.out, items)
        n_steps = sum(i["n_steps"] for i in items)
        print(json.dumps({"n_scripts": len(items), "n_expected_transitions": n_steps,
                          "by_source": {s: sum(1 for i in items if i["source"] == s) for s in {i["source"] for i in items}}}, indent=2))
        return 0
    task_defs = {str(t["task_id"]): t for t in read_jsonl(args.tasks) if isinstance(t, dict)}
    scripts = [s for s in read_jsonl(args.scripts) if isinstance(s, dict)]
    summary = replay_scripts(
        scripts, task_defs, out_dir=args.out_dir, lean_cmd=args.lean_cmd,
        workdir=args.workdir, timeout_s=args.timeout_s, max_scripts=args.max_scripts,
        recycle_every=args.recycle_every,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


__all__ = ["SCHEMA_STEPWISE", "build_script_inventory", "replay_scripts", "split_script"]

if __name__ == "__main__":
    raise SystemExit(main())
