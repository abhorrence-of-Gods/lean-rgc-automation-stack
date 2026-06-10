from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Iterable

from .schemas import LeanTask, TacticAction, ProofState, ResponseRecord, write_records, read_jsonl
from .executor import LeanExecutor, LeanExecutorConfig
from .defects import ProofDefectExtractor


SCHEMA_AUDIT_ROW = "lean-rgc-audit-row-v1"
SCHEMA_RESPONSE_ROW = "lean-rgc-response-row-v1"
SCHEMA_DEFECT_ROW = "lean-rgc-defect-row-v1"


def _pair_key(state_id: str, action_id: str) -> tuple[str, str]:
    return (str(state_id), str(action_id))


def run_micro_audit_batch(
    tasks: list[LeanTask],
    actions_by_task: dict[str, list[TacticAction]] | list[TacticAction],
    *,
    out_dir: str | Path,
    executor_config: LeanExecutorConfig,
    max_actions: int = 64,
    jobs: int = 1,
    candidate_mode: str = "state",
    resume: bool = False,
    flush_every: int = 50,
    run_id: str | None = None,
    parent_ids: list[str] | None = None,
) -> dict:
    """Run micro-audits with optional resume and periodic flush.

    This is still a conservative file-mode batch runner, but it is now suitable
    for 1k--10k audit pilots: existing output rows can be reused and partial
    results are flushed periodically.  The LeanExecutor cache can be layered on
    top for faster reruns.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    extractor = ProofDefectExtractor()

    existing_audits: list[dict] = []
    existing_responses: list[dict] = []
    done: set[tuple[str, str]] = set()
    if resume and (out / "responses.jsonl").exists():
        existing_responses = read_jsonl(out / "responses.jsonl")
        if (out / "micro_audit.jsonl").exists():
            existing_audits = read_jsonl(out / "micro_audit.jsonl")
        for r in existing_responses:
            sid = r.get("state_id")
            aid = r.get("action_id")
            if sid is not None and aid is not None:
                done.add(_pair_key(str(sid), str(aid)))

    jobs_list: list[tuple[LeanTask, ProofState, TacticAction, object]] = []
    for task in tasks:
        state = ProofState.from_task(task)
        defect_before = extractor.extract(state)
        actions = actions_by_task[task.task_id] if isinstance(actions_by_task, dict) else actions_by_task
        for action in actions[:max_actions]:
            if _pair_key(state.state_id, action.action_id) in done:
                continue
            jobs_list.append((task, state, action, defect_before))

    def one(item):
        task, state, action, defect_before = item
        ex = LeanExecutor(executor_config)
        rec = ex.run_tactic(task, action, state)
        after_state = rec.after_state or state
        defect_after = extractor.extract(after_state, rec)
        resp, resp_flat, resp_keys = extractor.response(defect_before, defect_after)
        rec.defect_before = defect_before.to_dict()
        rec.defect_after = defect_after.to_dict()
        rec.response = resp
        rec.carrier_delta = {k: defect_before.carrier.get(k, 0.0) - defect_after.carrier.get(k, 0.0) for k in sorted(set(defect_before.carrier) | set(defect_after.carrier))}
        rr = ResponseRecord(state_id=state.state_id, action_id=action.action_id, response=resp, response_flat=resp_flat, response_keys=resp_keys, defect_before=defect_before, defect_after=defect_after, audit_status=rec.status, carrier_delta=rec.carrier_delta).to_dict()
        rr["task_id"] = task.task_id
        rr["action"] = action.to_dict()
        ad = rec.to_dict()
        ad["action"] = action.to_dict()
        ad["task_id"] = task.task_id
        ad["target"] = task.statement
        rr["target"] = task.statement
        return ad, rr

    audits = list(existing_audits)
    responses = list(existing_responses)

    def flush():
        write_records(out / "micro_audit.jsonl", audits, schema_version=SCHEMA_AUDIT_ROW, run_id=run_id, parent_ids=parent_ids)
        write_records(out / "responses.jsonl", responses, schema_version=SCHEMA_RESPONSE_ROW, run_id=run_id, parent_ids=parent_ids)
        # one defect row per state/task for carrier coker/generator convenience
        seen = set()
        defects = []
        for r in responses:
            sid = r.get("state_id")
            if sid in seen:
                continue
            seen.add(sid)
            db = r.get("defect_before", {})
            if isinstance(db, dict):
                row = dict(db)
                row["state_id"] = sid
                row["task_id"] = r.get("task_id") or db.get("task_id")
                defects.append(row)
        write_records(out / "defects.jsonl", defects, schema_version=SCHEMA_DEFECT_ROW, run_id=run_id, parent_ids=parent_ids)

    flush_every = max(1, int(flush_every or 50))
    completed_new = 0
    if jobs <= 1:
        for item in jobs_list:
            a, r = one(item)
            audits.append(a); responses.append(r); completed_new += 1
            if completed_new % flush_every == 0:
                flush()
    else:
        with ThreadPoolExecutor(max_workers=jobs) as pool:
            futs = [pool.submit(one, item) for item in jobs_list]
            for fut in as_completed(futs):
                a, r = fut.result()
                audits.append(a); responses.append(r); completed_new += 1
                if completed_new % flush_every == 0:
                    flush()
    flush()
    return {"n": len(audits), "n_new": completed_new, "n_resumed": len(existing_responses), "out": str(out)}
