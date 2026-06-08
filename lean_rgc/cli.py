from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np

from .schemas import LeanTask, ProofState, TacticAction, DefectVector, ResponseRecord, read_jsonl, write_jsonl
from .executor import LeanExecutor, LeanExecutorConfig
from .defects import ProofDefectExtractor
from .candidates import TacticCandidateGenerator, CandidateGeneratorConfig
from .carrier_exposure import StateDependentCandidateGenerator
from .carrier import CarrierGenerator, carrier_coker_proxy
from .carrier_acceptance import accept_carrier_contexts, context_to_actions
from .carrier_promotion import write_accepted_carrier_actions
from .candidate_acceptance import accept_candidates_file, promote_registry_from_acceptance
from .quotient import ResponseQuotientDiscovery
from .response_model import ResponseModelConfig, train_response_model, predict_response_file, ResponseModel
from .trajectory import LeanTrajectoryRunner, TrajectoryRunnerConfig, write_trajectories
from .dataset import summarize_response_rows, split_jsonl, transitions_from_responses, write_run_report
from .lake_template import write_lake_template
from .batch import run_micro_audit_batch
from .gamma import GammaAuditor
from .selector import RGCTacticSelector, SelectorConfig
from .goal_shape import parse_goal_shape
from .defect_registry import seed_defect_registry
from .defect_miner import mine_defects as mine_defects_file
from .auto_defects import AutoDefectExtractor
from .proof_ir import ir_rows_from_tasks, ir_rows_from_audits, parse_audits_to_ir
from .focused_analysis import summarize_exposures
from .registry_candidates import registry_candidates_cli
from .iteration import merge_action_files, compare_pipeline_dirs
from .corebench import write_corebench
from .registry_promotion import promote_registry_file
from .registry_acceptance import run_registry_acceptance
from .robust_acceptance import run_robust_acceptance
from .premise_index import build_premise_index, PremiseIndex, premise_actions_from_hits
from .defect_ontology_lifecycle import run_defect_ontology_lifecycle
from .premise_retrieval import build_premise_index_from_tasks, premise_candidates_for_tasks
from .ir_defects import ir_defects_file
from .project_harvest import harvest_lean_project
from .sharding import shard_jsonl, merge_jsonl
from .bulk_executor import BulkAuditConfig, bulk_audit_to_files
from .ir_candidates import ir_candidates_file
from .multicarrier import build_carrier_matrix_from_responses, annotate_actions_with_carrier_matrix, multi_carrier_report, merge_carrier_incidence_patches, carrier_patch_report
from .frontier import expose_frontier_files
from .frontier import FrontierAuditor
from .exposure_frontier import write_exposure_frontiers
from .frontier import build_frontiers
from .focused import run_focused_micro_audit
from .action_analysis import write_action_group_report
from .response_eval import evaluate_response_model
from .stage_coker import run_stage_coker
from .quality import quality_gates_for_run, write_quality_report
from .failure_signatures import mine_failure_signatures
from .exposure_audit import exposure_actions_for_tasks, summarize_exposure_audit
from .iteration_report import collect_iteration_report
from .stage_report import write_stage_report, default_pipeline_stages
from .proof_replay import scripts_from_trajectories, replay_proof_scripts, export_proof_file
from .coker_synthesis import run_coker_synthesis
from .qgen import qgen_from_files
from .lineage import build_qgen_lineage, build_qgen_acceptance_lineage
from .robust_coker import run_robust_coker_acceptance
from .robust_acceptance import robust_accept_candidates_file
from .realized_response import collect_qgen_realized_calibration
from .carrier_patch_audit import audit_carrier_incidence_patches
from .poms_status import collect_poms_status
from .poms_promotion import collect_poms_promotion
from .promotion_evidence import generate_promotion_evidence
from .action_geometry import build_action_geometry_registry, score_action_geometry_registry, audit_action_cocycles, teacher_constraints_from_arithmetic_actions
from .action_geometry_loop import run_action_geometry_from_qgen
from .lean_server import LeanServerAdapter, LeanServerConfig, audit_with_lean_server, server_audit_to_files, run_server_micro_audit_to_files, adapter_from_executor_args
from .persistent_worker import PersistentLeanWorker, run_persistent_worker
from .persistent_worker import main as persistent_worker_main
from .structured_state import structured_state_extract_cli, summarize_structured_states
from .audit_db import build_audit_db, query_audit_db, write_query_outputs
from .active_audit_scheduler import active_audit_schedule_from_files, SchedulerConfig, _read_json_or_file
from .quotient_coordinates import quotient_coordinates_from_files
from .carrier_quotient import carrier_quotient_from_files, validate_carrier_quotient_coordinates
from .quotient_coordinate_loop import run_quotient_coordinate_loop, validate_quotient_coordinates
from .contextual_congruence import (
    ContextualProbeConfig,
    generate_contextual_probe_actions, generate_contextual_candidates, generate_contextual_composite_actions,
    build_contextual_response_fingerprints, mine_action_response_congruence,
    contextual_congruence_from_files, contextual_response_congruence_from_files,
    action_classes_to_registry,
)
from .response_quotient import build_response_quotient_registry, project_actions_by_response_quotient, response_quotient_from_congruence_dir
from .premise_response import build_premise_response_registry, retrieve_premise_responses, write_premise_retrieved_actions, mine_premise_quotient, _parse_json_or_file
from .premise_contextual_quotient import (
    generate_premise_contextual_candidates,
    build_premise_contextual_fingerprints,
    mine_premise_contextual_quotient,
    validate_premise_contextual_quotient,
    retrieve_premise_quotient_classes,
    premise_quotient_retrieved_actions,
)
from .bivariate_contextual_quotient import (
    build_premise_use_rows,
    write_separator_contexts,
    generate_bivariate_contextual_candidates,
    schedule_bivariate_candidates,
    build_repair_face_ledger,
)
from .source_budget_scheduler import source_budget_schedule_from_files, SourceBudgetConfig, _read_json_or_file as _read_source_budget_json_or_file
from .defect_ontology import reconcile_defect_ontology
from .arithmetic_teacher import generate_arithmetic_teacher_graph, audit_arithmetic_teacher_transitions
from .arithmetic_teacher_kernel_audit import audit_arithmetic_teacher_kernel_transitions
from .arithmetic_teacher_cocycle import arithmetic_teacher_cocycle_from_files, build_arithmetic_teacher_transition_geometry, audit_arithmetic_teacher_cocycles, write_arithmetic_teacher_gamma_constraints
from .gamma_transition_learner import learn_gamma_transition_model, merge_gamma_transition_patches_into_action_geometry
from .goal_state_dynamics import goal_state_transitions_from_audits, kernel_state_graphs_from_jsonl
from .kernel_state import KernelGoalStateServer, KernelGoalStateServerConfig, normalize_kernel_state_v1


def _load_tasks(path: str | Path) -> list[LeanTask]:
    return [LeanTask.from_dict(x) for x in read_jsonl(path)]


def _load_actions(path: str | Path | None) -> list[TacticAction]:
    if not path:
        return []
    return [TacticAction.from_dict(x) for x in read_jsonl(path)]


def _load_actions_grouped(path: str | Path | None) -> tuple[list[TacticAction], dict[str, list[TacticAction]]]:
    if not path:
        return [], {}
    global_actions: list[TacticAction] = []
    by_task: dict[str, list[TacticAction]] = {}
    for row in read_jsonl(path):
        task_id = row.get("task_id") or (row.get("metadata") or {}).get("task_id")
        action = TacticAction.from_dict(row)
        if task_id:
            by_task.setdefault(str(task_id), []).append(action)
        else:
            global_actions.append(action)
    return global_actions, by_task


def _detect_import_mode(mode: str, workdir: str | None = None, lean_cmd: str | None = None) -> str:
    mode = mode or "preserve"
    if mode != "auto":
        return mode
    if workdir:
        lake = Path(workdir) / "lakefile.lean"
        if lake.exists():
            text = lake.read_text(encoding="utf-8", errors="ignore").lower()
            return "mathlib" if "mathlib" in text else "core"
    if lean_cmd and "lake" not in lean_cmd:
        return "core"
    return "preserve"


def _normalize_tasks_imports(tasks: list[LeanTask], mode: str = "preserve", workdir: str | None = None, lean_cmd: str | None = None) -> list[LeanTask]:
    resolved = _detect_import_mode(mode, workdir, lean_cmd)
    if resolved == "preserve":
        return tasks
    out: list[LeanTask] = []
    for t in tasks:
        imports = list(t.imports)
        if resolved == "core":
            imports = [imp for imp in imports if not (imp == "Mathlib" or imp.startswith("Mathlib."))]
        elif resolved == "mathlib":
            if not any(imp == "Mathlib" or imp.startswith("Mathlib.") for imp in imports):
                imports = ["Mathlib"] + imports
        else:
            raise ValueError(f"unknown import mode: {mode}")
        out.append(replace(t, imports=imports))
    return out


def _actions_for_tasks(tasks: list[LeanTask], base_actions: list[TacticAction], task_actions: dict[str, list[TacticAction]] | None = None, *, state_candidates: bool = False, candidate_mode: str = "state", max_candidates: int = 64):
    task_actions = task_actions or {}
    if not state_candidates and base_actions and not task_actions:
        return base_actions
    gen = StateDependentCandidateGenerator(max_exposures=4) if candidate_mode == "state" else TacticCandidateGenerator(CandidateGeneratorConfig(use_carrier_exposure=False, max_candidates=max_candidates))
    by_task: dict[str, list[TacticAction]] = {}
    for task in tasks:
        state = ProofState.from_task(task)
        acts: list[TacticAction] = list(base_actions) + list(task_actions.get(task.task_id, []))
        if state_candidates or not acts:
            if isinstance(gen, StateDependentCandidateGenerator):
                acts.extend(gen.candidates(task, state, max_candidates=max_candidates))
            else:
                acts.extend(gen.candidates(task, state))
        seen: set[str] = set(); dedup: list[TacticAction] = []
        for a in acts:
            if a.tactic not in seen:
                seen.add(a.tactic); dedup.append(a)
            if len(dedup) >= max_candidates:
                break
        by_task[task.task_id] = dedup
    return by_task


def _executor_from_args(args: argparse.Namespace) -> LeanExecutor:
    return LeanExecutor(LeanExecutorConfig(lean_cmd=args.lean_cmd, timeout_s=args.timeout_s, dry_run=args.dry_run, keep_files=args.keep_files, workdir=args.workdir, cache_dir=args.cache_dir, trace_state=args.trace_state))


def _server_config_from_args(args: argparse.Namespace) -> LeanServerConfig:
    backend = getattr(args, "server_backend", None) or getattr(args, "lean_server_backend", None)
    if backend in {None, "auto"}:
        if getattr(args, "dry_run", False):
            backend = "dry_run"
        elif getattr(args, "server_cmd", None):
            backend = "jsonl"
        else:
            backend = "file_fallback"
    if backend == "dry":
        backend = "dry_run"
    if backend == "file":
        backend = "file_fallback"
    return LeanServerConfig(
        lean_cmd=getattr(args, "lean_cmd", "lake env lean"),
        workdir=getattr(args, "workdir", None),
        timeout_s=float(getattr(args, "timeout_s", 20.0)),
        dry_run=bool(getattr(args, "dry_run", False)),
        keep_files=bool(getattr(args, "keep_files", False)),
        cache_dir=getattr(args, "cache_dir", None),
        trace_state=bool(getattr(args, "trace_state", False)),
        backend=backend,
        server_cmd=getattr(args, "server_cmd", None),
        request_timeout_s=getattr(args, "request_timeout_s", None),
        fallback_to_file=not bool(getattr(args, "server_no_fallback", False)),
        native_exec_mode=getattr(args, "native_exec_mode", "source_check"),
    )


def _server_from_args(args: argparse.Namespace) -> LeanServerAdapter:
    return LeanServerAdapter(_server_config_from_args(args))

def summarize_responses(responses: list[dict[str, Any]]) -> dict[str, Any]:
    if not responses:
        return {"n": 0}
    statuses: dict[str, int] = {}
    norms: list[float] = []
    carrier_deltas: list[float] = []
    goal_responses: list[float] = []
    for r in responses:
        status = str(r.get("audit_status", r.get("status", "unknown")))
        statuses[status] = statuses.get(status, 0) + 1
        norms.append(float(np.linalg.norm(np.asarray(r.get("response_flat", []), dtype=float))))
        cd = r.get("carrier_delta", {}) or {}
        carrier_deltas.append(sum(float(v) for v in cd.values()))
        resp = r.get("response", {}) or {}
        goal_responses.append(sum(float(v) for k, v in resp.items() if str(k).startswith("goal.")))
    return {
        "n": len(responses),
        "statuses": statuses,
        "success_rate": statuses.get("success", 0) / max(1, len(responses)),
        "mean_response_norm": float(np.mean(norms)),
        "max_response_norm": float(np.max(norms)),
        "mean_goal_response": float(np.mean(goal_responses)),
        "mean_carrier_delta": float(np.mean(carrier_deltas)),
    }


def _audit_loop(tasks, actions_by_task, executor, extractor):
    audits=[]; responses=[]; defects=[]
    for task in tasks:
        state = ProofState.from_task(task)
        before = extractor.extract(state)
        defects.append({"state_id": state.state_id, "task_id": task.task_id, "target": task.statement, **before.to_dict()})
        actions = actions_by_task[task.task_id] if isinstance(actions_by_task, dict) else actions_by_task
        for action in actions:
            rec = executor.run_tactic(task, action, state)
            after = extractor.extract(rec.after_state or state, rec)
            resp, flat, keys = extractor.response(before, after)
            rec.defect_before = before.to_dict(); rec.defect_after = after.to_dict(); rec.response = resp
            rec.carrier_delta = {k: before.carrier.get(k,0.0)-after.carrier.get(k,0.0) for k in sorted(set(before.carrier)|set(after.carrier))}
            audits.append(rec.to_dict())
            rr = ResponseRecord(state_id=state.state_id, action_id=action.action_id, response=resp, response_flat=flat, response_keys=keys, defect_before=before, defect_after=after, audit_status=rec.status, carrier_delta=rec.carrier_delta).to_dict()
            rr.update({"task_id": task.task_id, "target": task.statement, "action": action.to_dict()})
            responses.append(rr)
    return audits, responses, defects


def cmd_audit(args):
    tasks = _normalize_tasks_imports(_load_tasks(args.tasks), args.import_mode, args.workdir, args.lean_cmd)
    base, by_task = _load_actions_grouped(args.actions)
    acts = _actions_for_tasks(tasks, base, by_task, state_candidates=args.state_candidates or not (base or by_task), candidate_mode=args.candidate_mode, max_candidates=args.max_actions)
    trimmed = {k: v[:args.max_actions] for k, v in acts.items()} if isinstance(acts, dict) else acts[:args.max_actions]
    if getattr(args, "lean_server", False):
        cfg = _server_config_from_args(args)
        summary = audit_with_lean_server(tasks, trimmed, out_dir=args.out, server_config=cfg, max_actions=args.max_actions, resume=args.resume, flush_every=args.flush_every)
        responses = read_jsonl(Path(args.out) / "responses.jsonl") if (Path(args.out) / "responses.jsonl").exists() else []
        summary.update(summarize_responses(responses))
        (Path(args.out) / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return 0
    audits, responses, defects = _audit_loop(tasks, trimmed, _executor_from_args(args), ProofDefectExtractor())
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    write_jsonl(out / "micro_audit.jsonl", audits); write_jsonl(out / "responses.jsonl", responses); write_jsonl(out / "defects.jsonl", defects)
    summary = summarize_responses(responses)
    (out / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def cmd_lean_server_audit(args):
    # Backward-compatible alias for v21 server-audit.
    return cmd_server_audit(args)


def cmd_persistent_worker(args):
    from .persistent_lean_worker import main as worker_main
    argv = ["--backend", args.backend, "--lean-cmd", args.lean_cmd, "--timeout-s", str(args.timeout_s)]
    if args.workdir:
        argv += ["--workdir", args.workdir]
    if args.keep_files:
        argv += ["--keep-files"]
    if args.cache_dir:
        argv += ["--cache-dir", args.cache_dir]
    if args.trace_state:
        argv += ["--trace-state"]
    if args.no_warmup:
        argv += ["--no-warmup"]
    return worker_main(argv)


def cmd_persistent_state_demo(args):
    from .persistent_lean_worker import PersistentLeanWorker, WorkerConfig
    task = LeanTask.from_dict(json.loads(Path(args.task_json).read_text(encoding="utf-8")))
    actions = [TacticAction.from_dict(r) for r in read_jsonl(args.actions)]
    worker = PersistentLeanWorker(WorkerConfig(backend="dry_run" if args.dry_run else "file", lean_cmd=args.lean_cmd, workdir=args.workdir, timeout_s=args.timeout_s, keep_files=args.keep_files, trace_state=args.trace_state))
    worker.load_project()
    base = worker.register_task(task)["state"]
    current = base["state_id"]
    rows=[]
    for action in actions[:args.max_actions]:
        rep = worker.apply_tactic(action=action, state_id=current)
        rows.append(rep)
        after = rep.get("after_state") or {}
        if rep.get("audit", {}).get("status") in {"success", "partial", "dry_run"} and after.get("state_id"):
            current = after["state_id"]
        if rep.get("audit", {}).get("status") == "success":
            break
    out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"base_state": base, "final_state_id": current, "states": worker.list_states(), "steps": rows, "status": worker.status()}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"out": str(out), "n_steps": len(rows), "n_states": len(worker.states)}, indent=2, ensure_ascii=False))
    return 0

def cmd_candidates(args):
    tasks=_normalize_tasks_imports(_load_tasks(args.tasks), args.import_mode, None, None)
    gen=StateDependentCandidateGenerator() if args.candidate_mode=="state" else TacticCandidateGenerator(CandidateGeneratorConfig(use_carrier_exposure=False, max_candidates=args.max_candidates))
    rows=[]
    for task in tasks:
        state=ProofState.from_task(task)
        cands=gen.candidates(task,state,max_candidates=args.max_candidates) if isinstance(gen,StateDependentCandidateGenerator) else gen.candidates(task,state)[:args.max_candidates]
        for a in cands:
            d=a.to_dict(); d["task_id"]=task.task_id; d.setdefault("metadata", {})["task_id"]=task.task_id; rows.append(d)
    write_jsonl(args.out, rows); print(json.dumps({"n": len(rows), "out": args.out}, indent=2, ensure_ascii=False)); return 0


def cmd_registry_candidates(args):
    registry_candidates_cli(args.tasks, args.registry, args.out, max_candidates=args.max_candidates)
    print(json.dumps({"out": args.out, "registry": args.registry}, indent=2, ensure_ascii=False)); return 0


def cmd_build_premise_index(args):
    idx = build_premise_index(tasks=args.tasks, actions=args.actions, out=args.out)
    print(json.dumps({"n_docs": len(idx.docs), "out": args.out}, indent=2, ensure_ascii=False)); return 0


def cmd_premise_retrieve(args):
    idx = PremiseIndex.load(args.index)
    queries: list[str] = []
    if args.query:
        queries.append(args.query)
    if args.tasks:
        tasks = _normalize_tasks_imports(_load_tasks(args.tasks), args.import_mode, None, None)
        for t in tasks:
            queries.append(t.statement)
    if args.states:
        for r in read_jsonl(args.states):
            queries.append("\n".join([str(r.get("target", "")), str(r.get("goals_text", "")), json.dumps(r.get("carrier", {}), ensure_ascii=False)]))
    rows=[]
    for qi, q in enumerate(queries):
        hits = idx.search(q, k=args.k, kind=args.kind)
        rows.append({"query_id": qi, "query": q[:500], "hits": [h.to_dict() for h in hits]})
    write_jsonl(args.out, rows)
    print(json.dumps({"n_queries": len(rows), "out": args.out}, indent=2, ensure_ascii=False)); return 0


def cmd_premise_actions(args):
    rows=[]
    for row in read_jsonl(args.hits):
        from .premise_index import PremiseHit
        hits=[PremiseHit(**h) for h in row.get("hits", [])]
        acts=premise_actions_from_hits(hits, prefix=f"premise:{row.get('query_id', len(rows))}")[:args.max_actions_per_query]
        for a in acts:
            d=a
            if args.task_id:
                d.setdefault("metadata", {})["task_id"] = args.task_id
                d["task_id"] = args.task_id
            rows.append(d)
    write_jsonl(args.out, rows)
    print(json.dumps({"n": len(rows), "out": args.out}, indent=2, ensure_ascii=False)); return 0


def cmd_premise_candidates(args):
    meta = premise_candidates_for_tasks(args.tasks, args.index, args.out, top_k=args.top_k, max_actions=args.max_actions)
    print(json.dumps(meta, indent=2, ensure_ascii=False)); return 0



def cmd_premise_response_registry(args):
    summary = build_premise_response_registry(
        actions_path=getattr(args, "actions", None),
        responses_path=args.responses,
        out=args.out,
        summary_out=getattr(args, "summary_out", None),
        min_count=getattr(args, "min_count", 1),
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False)); return 0


def cmd_premise_response_retrieve(args):
    rn = _parse_json_or_file(getattr(args, "response_normal", None) or getattr(args, "response_normal_json", None))
    cn = _parse_json_or_file(getattr(args, "carrier_normal", None) or getattr(args, "carrier_normal_json", None))
    summary = retrieve_premise_responses(
        registry_path=args.registry,
        out=args.out,
        summary_out=getattr(args, "summary_out", None),
        response_normal=rn,
        carrier_normal=cn,
        top_k=getattr(args, "top_k", None),
        cost_weight=getattr(args, "cost_weight", 0.05),
        uncertainty_weight=getattr(args, "uncertainty_weight", 0.10),
        audit_weight=getattr(args, "audit_weight", 0.20),
        carrier_safe=getattr(args, "carrier_safe", False),
        carrier_budget=getattr(args, "carrier_budget", 0.0),
    )
    if getattr(args, "out_actions", None):
        act_meta = write_premise_retrieved_actions(retrieved_path=args.out, out=args.out_actions)
        summary["actions"] = act_meta
        if getattr(args, "summary_out", None):
            Path(args.summary_out).write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False)); return 0


def cmd_premise_quotient_mine(args):
    summary = mine_premise_quotient(
        registry_path=args.registry,
        out_dir=args.out,
        cosine_threshold=getattr(args, "cosine_threshold", 0.95),
        distance_threshold=getattr(args, "distance_threshold", 0.25),
        include_carrier=not getattr(args, "no_carrier", False),
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False)); return 0


def cmd_premise_contextual_generate(args):
    summary = generate_premise_contextual_candidates(
        premise_actions_path=getattr(args, "premise_actions", None) or getattr(args, "actions", None),
        out=args.out,
        contexts_path=getattr(args, "contexts", None),
        max_premises=getattr(args, "max_premises", None),
        max_left=getattr(args, "max_left", 4),
        max_right=getattr(args, "max_right", 4),
        max_candidates=getattr(args, "max_candidates", None),
        include_identity=not getattr(args, "no_identity", False),
        include_baselines=not getattr(args, "no_baselines", False),
    )
    if getattr(args, "summary_out", None):
        Path(args.summary_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.summary_out).write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False)); return 0


def cmd_premise_contextual_fingerprints(args):
    summary = build_premise_contextual_fingerprints(
        responses_path=args.responses,
        actions_path=getattr(args, "actions", None),
        out=args.out,
        summary_out=getattr(args, "summary_out", None),
        min_contexts=getattr(args, "min_contexts", 1),
        include_carrier=not getattr(args, "no_carrier", False),
        include_gamma=not getattr(args, "no_gamma", False),
        include_cost=not getattr(args, "no_cost", False),
        include_audit=not getattr(args, "no_audit", False),
        baseline_required=getattr(args, "baseline_required", False),
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False)); return 0


def cmd_premise_contextual_mine(args):
    summary = mine_premise_contextual_quotient(
        fingerprints_path=args.fingerprints,
        out_dir=args.out,
        epsilon=getattr(args, "epsilon", 0.25),
        cosine_threshold=getattr(args, "cosine_threshold", 0.95),
        domain_jaccard_threshold=getattr(args, "domain_jaccard_threshold", 0.0),
        response_weight=getattr(args, "response_weight", 1.0),
        carrier_weight=getattr(args, "carrier_weight", 1.0),
        gamma_weight=getattr(args, "gamma_weight", 0.25),
        domain_weight=getattr(args, "domain_weight", 1.0),
        cost_weight=getattr(args, "cost_weight", 0.05),
        uncertainty_weight=getattr(args, "uncertainty_weight", 0.10),
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False)); return 0


def cmd_premise_contextual_validate(args):
    summary = validate_premise_contextual_quotient(
        fingerprints_path=args.fingerprints,
        classes_path=args.classes,
        out_rows=args.out_rows,
        out_report=args.out_report,
        holdout_fraction=getattr(args, "holdout_fraction", 0.35),
        epsilon_holdout=getattr(args, "epsilon_holdout", 0.35),
        separation_delta=getattr(args, "separation_delta", 0.10),
        domain_jaccard_min=getattr(args, "domain_jaccard_min", 0.0),
        carrier_mixed_threshold=getattr(args, "carrier_mixed_threshold", 0.05),
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False)); return 0


def cmd_premise_quotient_retrieve(args):
    rn = _parse_json_or_file(getattr(args, "response_normal", None) or getattr(args, "response_normal_json", None))
    cn = _parse_json_or_file(getattr(args, "carrier_normal", None) or getattr(args, "carrier_normal_json", None))
    summary = retrieve_premise_quotient_classes(
        classes_path=args.classes,
        out=args.out,
        summary_out=getattr(args, "summary_out", None),
        response_normal=rn,
        carrier_normal=cn,
        top_k=getattr(args, "top_k", None),
        gamma_weight=getattr(args, "gamma_weight", 0.10),
        cost_weight=getattr(args, "cost_weight", 0.05),
        uncertainty_weight=getattr(args, "uncertainty_weight", 0.10),
        import_cost_weight=getattr(args, "import_cost_weight", 0.05),
        require_validated=getattr(args, "require_validated", False),
    )
    if getattr(args, "out_actions", None):
        act_meta = premise_quotient_retrieved_actions(retrieved_path=args.out, out=args.out_actions)
        summary["actions"] = act_meta
        if getattr(args, "summary_out", None):
            Path(args.summary_out).write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False)); return 0


def cmd_premise_use_rows(args):
    summary = build_premise_use_rows(
        actions_path=args.actions,
        out=args.out,
        summary_out=getattr(args, "summary_out", None),
        max_rows=getattr(args, "max_rows", None),
        include_context_actions=getattr(args, "include_context_actions", False),
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False)); return 0


def cmd_separator_contexts(args):
    summary = write_separator_contexts(
        out=args.out,
        templates=getattr(args, "templates", "builtin_core"),
        summary_out=getattr(args, "summary_out", None),
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False)); return 0


def cmd_bivariate_contextual_generate(args):
    summary = generate_bivariate_contextual_candidates(
        premise_rows_path=args.premise_rows,
        contexts_path=args.contexts,
        out=args.out,
        summary_out=getattr(args, "summary_out", None),
        max_rows=getattr(args, "max_rows", None),
        max_pre=getattr(args, "max_pre", 8),
        max_post=getattr(args, "max_post", 8),
        max_candidates=getattr(args, "max_candidates", None),
        include_baselines=not getattr(args, "no_baselines", False),
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False)); return 0


def cmd_bivariate_contextual_schedule(args):
    summary = schedule_bivariate_candidates(
        candidates_path=args.candidates,
        out=args.out,
        budget=getattr(args, "budget", 512),
        report_out=getattr(args, "report_out", None),
        require_baseline_pairs=getattr(args, "require_baseline_pairs", False),
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False)); return 0


def cmd_repair_face_ledger(args):
    summary = build_repair_face_ledger(
        fingerprints_path=args.fingerprints,
        classes_path=args.classes,
        validation_rows_path=getattr(args, "validation", None),
        out=args.out,
        report_out=getattr(args, "report", None),
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False)); return 0


def cmd_carrier_actions(args):
    rows=[]
    for proposal in read_jsonl(args.proposals):
        task_id = proposal.get("task_id") or proposal.get("state_id") or ""
        contexts = proposal.get("generated_contexts")
        if contexts is None:
            contexts = [proposal]
        for ci, ctx in enumerate(contexts):
            for action in context_to_actions(ctx, prefix=f"{args.prefix}:{task_id}:{ci}")[:args.max_actions_per_context]:
                d=action.to_dict(); d["context_kind"]=ctx.get("kind"); d["source_context"]=ctx
                if task_id:
                    d["task_id"]=task_id; d.setdefault("metadata", {})["task_id"]=task_id
                d.setdefault("metadata", {}).setdefault("generated_by", "carrier_actions")
                rows.append(d)
    write_jsonl(args.out, rows); print(json.dumps({"n": len(rows), "out": args.out}, indent=2, ensure_ascii=False)); return 0


def cmd_merge_actions(args):
    seen=set(); rows=[]
    for path in args.inputs:
        for row in read_jsonl(path):
            key=(row.get("task_id") or (row.get("metadata") or {}).get("task_id") or "", row.get("tactic") or row.get("action_id") or json.dumps(row, sort_keys=True))
            if key in seen: continue
            seen.add(key); rows.append(row)
    write_jsonl(args.out, rows); print(json.dumps({"n": len(rows), "out": args.out, "inputs": args.inputs}, indent=2, ensure_ascii=False)); return 0


def cmd_expose_frontier(args):
    tasks=_normalize_tasks_imports(_load_tasks(args.tasks), args.import_mode, args.workdir, args.lean_cmd)
    norm_path = Path(args.out_tasks).parent / (Path(args.out_tasks).stem + ".input.normalized.jsonl")
    write_jsonl(norm_path, [t.to_dict() for t in tasks])
    executor = _executor_from_args(args)
    summary = write_exposure_frontiers(norm_path, args.out_tasks, args.out_report, executor, max_exposures=args.max_exposures, allow_identity=not args.no_identity)
    print(json.dumps(summary, indent=2, ensure_ascii=False)); return 0


def cmd_goal_shapes(args):
    tasks=_normalize_tasks_imports(_load_tasks(args.tasks), args.import_mode, None, None)
    rows=[]
    for t in tasks:
        st=ProofState.from_task(t); rows.append({"task_id":t.task_id,"state_id":st.state_id,"goal_shape":parse_goal_shape(t,st).to_dict()})
    write_jsonl(args.out, rows); print(json.dumps({"n": len(rows), "out": args.out}, indent=2, ensure_ascii=False)); return 0


def cmd_parse_states(args):
    rows=parse_audits_to_ir(args.audits,args.out); print(json.dumps({"n":len(rows),"out":args.out},indent=2,ensure_ascii=False)); return 0


def cmd_state_ir(args):
    if args.tasks: rows=ir_rows_from_tasks(args.tasks,args.out,import_mode=args.import_mode)
    elif args.audits: rows=ir_rows_from_audits(args.audits,args.out)
    else: raise SystemExit("provide --tasks or --audits")
    print(json.dumps({"n":len(rows),"out":args.out},indent=2,ensure_ascii=False)); return 0


def cmd_ir_defects(args):
    rows = ir_defects_file(args.ir, args.out); print(json.dumps({"n": len(rows), "out": args.out}, indent=2, ensure_ascii=False)); return 0


def cmd_exposure_report(args):
    rep=summarize_exposures(args.responses,args.out); print(json.dumps({"n_rows":rep.get("n_rows",0),"n_prefixes":len(rep.get("by_exposure_prefix",[])),"out":args.out},indent=2,ensure_ascii=False)); return 0


def cmd_exposure_candidates(args):
    meta = exposure_actions_for_tasks(args.tasks, args.out, include_identity=args.include_identity, import_mode=getattr(args, 'import_mode', 'preserve'))
    print(json.dumps(meta, indent=2, ensure_ascii=False)); return 0


def cmd_action_report(args):
    keys = args.group_keys.split(',') if args.group_keys else None
    rep = write_action_group_report(args.responses, args.out, args.csv_out, group_keys=keys)
    print(json.dumps({"n_responses": rep.get("n_responses", 0), "n_groups": len(rep.get("groups", [])), "out": args.out, "csv": args.csv_out}, indent=2, ensure_ascii=False)); return 0


def cmd_quotient(args):
    rows=read_jsonl(args.responses); by={}
    for r in rows: by.setdefault(str(r["action_id"]),[]).append(np.asarray(r.get("response_flat",[]),dtype=float))
    ids=sorted(by); mat=np.stack([np.mean(by[i],axis=0) for i in ids],axis=0) if ids else np.zeros((0,0))
    comps=ResponseQuotientDiscovery(tolerance=args.tolerance).discover(ids,mat) if ids else []
    write_jsonl(args.out,[c.__dict__ for c in comps]); print(json.dumps({"n": len(comps), "out": args.out}, indent=2, ensure_ascii=False)); return 0


def cmd_carrier_generate(args):
    rows=read_jsonl(args.defects); gen=CarrierGenerator(); out=[]
    for row in rows:
        carrier=row.get("carrier") or row.get("defect",{}).get("carrier",{})
        residual=[k for k,v in carrier.items() if float(v)>args.threshold]
        text=row.get("target","") or row.get("goals_text","") or json.dumps(row)[:512]
        out.append({"state_id":row.get("state_id"),"task_id":row.get("task_id"),"residual_atoms":residual,"generated_contexts":gen.generate(residual,text)})
    write_jsonl(args.out,out); print(json.dumps({"n": len(out), "out": args.out}, indent=2, ensure_ascii=False)); return 0


def cmd_carrier_coker(args):
    rows=read_jsonl(args.defects); actions=_load_actions(args.actions); extractor=ProofDefectExtractor(); out=[]
    for row in rows:
        if "flat" in row and "flat_keys" in row:
            defect=DefectVector.from_dict({k:row[k] for k in ["goal","type","search","carrier","audit","flat","flat_keys","quotient_meta"] if k in row})
        else:
            defect=extractor.extract(ProofState(state_id=row.get("state_id","unknown"),task_id=row.get("task_id","unknown"),target=row.get("target",""),goals_text=row.get("goals_text","")))
            if "carrier" in row: defect.carrier={k:float(v) for k,v in row["carrier"].items()}
        rep=carrier_coker_proxy(defect, actions); out.append({"state_id":row.get("state_id"),"task_id":row.get("task_id"),**rep.__dict__})
    write_jsonl(args.out,out); print(json.dumps({"n": len(out), "out": args.out}, indent=2, ensure_ascii=False)); return 0


def cmd_seed_defect_registry(args): seed_defect_registry().save(args.out); print(json.dumps({"out": args.out}, indent=2, ensure_ascii=False)); return 0


def cmd_mine_defects(args):
    score_out=args.scores_out or str(Path(args.out).with_suffix(".scores.jsonl")); reg=mine_defects_file(args.audits,args.responses,args.out,score_out,min_support=args.min_support,min_response_contrast=args.min_response_contrast,min_stability=args.min_stability,min_intervention_success=getattr(args,'min_intervention_success',0.0),min_coker_reduction=getattr(args,'min_coker_reduction',0.0)); print(json.dumps({"n_atoms":len(reg.atoms),"out":args.out,"scores":score_out},indent=2,ensure_ascii=False)); return 0


def cmd_promote_registry(args):
    audits_path = Path(args.audits)
    if audits_path.is_dir():
        audits_path = audits_path / "micro_audit.jsonl"
    responses = args.responses
    if responses is None:
        cand = audits_path.parent / "responses.jsonl"
        if cand.exists():
            responses = str(cand)
    reg, rep = promote_registry_file(
        args.registry,
        str(audits_path),
        args.out,
        responses_path=responses,
        report_out=args.report_out,
        min_support=args.min_support,
        min_intervention_success=args.min_intervention_success,
        min_coker_reduction=args.min_coker_reduction,
        min_promotion_score=args.min_promotion_score,
        drop_rejected=args.drop_rejected,
    )
    print(json.dumps({"n_atoms": len(reg.atoms), "validated": rep.n_validated, "rejected": rep.n_rejected, "out": args.out, "report": args.report_out}, indent=2, ensure_ascii=False)); return 0


def cmd_auto_defects(args):
    ext=AutoDefectExtractor(args.registry); rows=[]
    if args.tasks:
        tasks=_normalize_tasks_imports(_load_tasks(args.tasks), args.import_mode, None, None)
        for t in tasks:
            st=ProofState.from_task(t); rows.append({"task_id":t.task_id,"state_id":st.state_id,"auto_defects":ext.extract_atoms(st)})
    elif args.states:
        for r in read_jsonl(args.states):
            st=ProofState(state_id=str(r.get("state_id","state")),task_id=str(r.get("task_id","task")),target=str(r.get("target","")),goals_text=str(r.get("goals_text","")),raw_messages=[str(m) for m in r.get("messages",[]) or []]); rows.append({"task_id":st.task_id,"state_id":st.state_id,"auto_defects":ext.extract_atoms(st)})
    else: raise SystemExit("auto-defects requires --tasks or --states")
    write_jsonl(args.out,rows); print(json.dumps({"n": len(rows), "out": args.out}, indent=2, ensure_ascii=False)); return 0


def cmd_audit_defect_atoms(args):
    audits=read_jsonl(args.audits); responses=read_jsonl(args.responses) if args.responses else []; scores=AutoDefectMiner().score_atoms(audits,responses); write_jsonl(args.out,[s.to_dict() for s in scores]); print(json.dumps({"n": len(scores), "out": args.out}, indent=2, ensure_ascii=False)); return 0




def cmd_failure_signatures(args):
    responses = args.responses
    if responses is None:
        cand = Path(args.audits).parent / "responses.jsonl"
        if cand.exists():
            responses = str(cand)
    summary_out = args.summary_out or str(Path(args.out).with_suffix(".summary.json"))
    res = mine_failure_signatures(
        args.audits,
        args.out,
        responses=responses,
        actions_out=args.actions_out,
        summary_out=summary_out,
        min_support=args.min_support,
    )
    print(json.dumps({"n_signatures": len(res.signatures), "n_actions": len(res.actions), "out": args.out, "actions_out": args.actions_out, "summary_out": summary_out}, indent=2, ensure_ascii=False)); return 0

def cmd_train_response(args):
    cfg=ResponseModelConfig(lcb_kappa=args.lcb_kappa,min_count_for_action=args.min_count_for_action,shrink=args.shrink); model=train_response_model(args.responses,args.actions,args.out,config=cfg); print(json.dumps({"response_dim":len(model.response_keys),"n_actions":len(getattr(model,"by_action",{})),"n_classes":len(getattr(model,"by_class",{})),"out":str(args.out)},indent=2,ensure_ascii=False)); return 0


def cmd_predict_response(args): rows=predict_response_file(args.model,args.actions,args.out,mode=args.mode); print(json.dumps({"n": len(rows), "out": args.out}, indent=2, ensure_ascii=False)); return 0


def cmd_eval_response(args):
    rows, summary = evaluate_response_model(
        args.model,
        args.responses,
        mode=args.mode,
        out_rows=args.out_rows,
        out_summary=args.out,
        out_csv=args.csv_out,
    )
    print(json.dumps(summary.to_dict(), indent=2, ensure_ascii=False)); return 0


def cmd_select(args):
    model=ResponseModel.load(args.model); actions=_load_actions(args.actions); row=json.loads(Path(args.defect).read_text()) if str(args.defect).endswith('.json') else read_jsonl(args.defect)[0]; defect=DefectVector.from_dict(row.get('defect') or row.get('defect_before') or row); preds={a.action_id:np.asarray(model.predict(a,mode=args.response_mode).mean,dtype=float) for a in actions}; sel=RGCTacticSelector(SelectorConfig(carrier_budget=args.carrier_budget,carrier_mode=args.carrier_mode,cost_weight=args.cost_weight)).select(row.get('state_id','state'),defect,actions,preds); Path(args.out).parent.mkdir(parents=True,exist_ok=True); Path(args.out).write_text(json.dumps(sel.to_dict(),indent=2,ensure_ascii=False)); print(json.dumps(sel.to_dict(),indent=2,ensure_ascii=False)); return 0


def cmd_gamma_audit(args):
    rows=read_jsonl(args.transitions); auditor=GammaAuditor(ridge=args.ridge); residuals=[]; nexts=[]
    for row in rows:
        D=np.asarray(row['defect'],dtype=float); R=np.asarray(row['pred_response'],dtype=float); N=np.asarray(row['next_defect'],dtype=float); residuals.append(D-R); nexts.append(N)
    gamma=auditor.fit_linear_gamma(np.stack(residuals),np.stack(nexts)) if args.fit_gamma and residuals else None; reports=[]
    for row in rows:
        rep=auditor.audit(np.asarray(row['defect'],dtype=float),np.asarray(row['pred_response'],dtype=float),np.asarray(row['next_defect'],dtype=float),gamma=gamma,horizon=args.horizon); d=rep.__dict__
        if gamma is not None and args.include_gamma_matrix: d['gamma']=gamma.tolist()
        reports.append(d)
    write_jsonl(args.out,reports); print(json.dumps({"n": len(reports), "out": args.out}, indent=2, ensure_ascii=False)); return 0




def cmd_gamma_transition_learner(args):
    rep = learn_gamma_transition_model(
        args.transitions,
        args.out,
        actions_path=getattr(args, "actions", None),
        teacher_constraints_path=getattr(args, "teacher_constraints", None),
        ridge=args.ridge,
        shrink=args.shrink,
        min_count=args.min_count,
        holdout_fraction=args.holdout_fraction,
        seed=args.seed,
        teacher_weight=args.teacher_weight,
        include_matrices=args.include_matrices,
    )
    print(json.dumps(rep, indent=2, ensure_ascii=False)); return 0


def cmd_gamma_transition_patch_action_geometry(args):
    rep = merge_gamma_transition_patches_into_action_geometry(
        args.action_geometry,
        args.patches,
        args.out,
        summary_out=getattr(args, "summary_out", None),
    )
    print(json.dumps(rep, indent=2, ensure_ascii=False)); return 0


def cmd_run_search(args):
    tasks=_normalize_tasks_imports(_load_tasks(args.tasks),args.import_mode,args.workdir,args.lean_cmd); model=ResponseModel.load(args.response_model) if args.response_model else None; out=Path(args.out); out.mkdir(parents=True,exist_ok=True); executor=LeanExecutor(LeanExecutorConfig(lean_cmd=args.lean_cmd,timeout_s=args.timeout_s,dry_run=args.dry_run,keep_files=args.keep_files,workdir=args.workdir,cache_dir=args.cache_dir,trace_state=args.trace_state)); runner=LeanTrajectoryRunner(executor,response_model=model,config=TrajectoryRunnerConfig(max_steps=args.max_steps,max_candidates=args.max_candidates,carrier_budget=args.carrier_budget,carrier_mode=args.carrier_mode,response_mode=args.response_mode)); records=[runner.run_task(t) for t in tasks]; write_trajectories(out/'trajectories.jsonl',records); summary={'n':len(records),'proved':sum(1 for r in records if r.final_status=='proved'),'statuses':{},'mean_steps':float(np.mean([len(r.steps) for r in records])) if records else 0.0}
    for r in records: summary['statuses'][r.final_status]=summary['statuses'].get(r.final_status,0)+1
    (out/'trajectory_summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8'); print(json.dumps(summary,indent=2,ensure_ascii=False)); return 0





def cmd_extract_proofs(args):
    meta = scripts_from_trajectories(
        args.trajectories,
        args.tasks,
        args.out,
        proved_only=not args.include_nonproved,
        include_partial=args.include_partial,
    )
    print(json.dumps(meta, indent=2, ensure_ascii=False)); return 0


def cmd_replay_proofs(args):
    cfg = LeanExecutorConfig(
        lean_cmd=args.lean_cmd,
        timeout_s=args.timeout_s,
        dry_run=args.dry_run,
        keep_files=args.keep_files,
        workdir=args.workdir,
        cache_dir=args.cache_dir,
        trace_state=args.trace_state,
    )
    summary = replay_proof_scripts(args.scripts, args.out, cfg)
    print(json.dumps(summary, indent=2, ensure_ascii=False)); return 0


def cmd_export_proofs(args):
    meta = export_proof_file(args.scripts, args.out, theorem_prefix=args.theorem_prefix)
    print(json.dumps(meta, indent=2, ensure_ascii=False)); return 0

def cmd_focused_audit(args):
    tasks = _normalize_tasks_imports(_load_tasks(args.tasks), args.import_mode, args.workdir, args.lean_cmd)
    base, by_task = _load_actions_grouped(args.actions)
    if by_task:
        # Focused audit currently uses global core actions.  If task-specific
        # actions are supplied, flatten them conservatively.
        seen = {a.tactic for a in base}
        for xs in by_task.values():
            for a in xs:
                if a.tactic not in seen:
                    seen.add(a.tactic); base.append(a)
    cfg = LeanExecutorConfig(lean_cmd=args.lean_cmd, timeout_s=args.timeout_s, dry_run=args.dry_run, keep_files=args.keep_files, workdir=args.workdir, cache_dir=args.cache_dir, trace_state=args.trace_state)
    summary = run_focused_micro_audit(tasks, out_dir=args.out, executor_config=cfg, base_actions=base, max_exposures=args.max_exposures, max_core_actions=args.max_core_actions, audit_identity_exposure=args.audit_identity_exposure)
    print(json.dumps(summary, indent=2, ensure_ascii=False)); return 0

def cmd_make_transitions(args): rows=transitions_from_responses(args.responses,args.out); print(json.dumps({"n": len(rows), "out": args.out}, indent=2, ensure_ascii=False)); return 0


def cmd_dataset_summary(args):
    summary=summarize_response_rows(read_jsonl(args.responses)).to_dict()
    if args.out:
        Path(args.out).parent.mkdir(parents=True,exist_ok=True); Path(args.out).write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(summary,indent=2,ensure_ascii=False)); return 0


def cmd_split(args): meta=split_jsonl(args.input,args.out,train_frac=args.train_frac,seed=args.seed,key=args.group_key); print(json.dumps(meta,indent=2,ensure_ascii=False)); return 0


def cmd_carrier_accept(args):
    executor=_executor_from_args(args); tasks=_normalize_tasks_imports(_load_tasks(args.tasks),args.import_mode,args.workdir,args.lean_cmd); norm=Path(args.out).parent/'_carrier_accept_tasks.normalized.jsonl'; write_jsonl(norm,[t.to_dict() for t in tasks]); rows=accept_carrier_contexts(norm,args.proposals,args.out,executor,max_actions=args.max_actions,margin_threshold=args.margin_threshold,cost_weight=args.cost_weight); print(json.dumps({"n": len(rows), "out": args.out}, indent=2, ensure_ascii=False)); return 0


def cmd_carrier_accept_summary(args):
    rows=read_jsonl(args.accepted); n=len(rows); acc=[r for r in rows if r.get('accepted')]; by={}
    for r in rows: by[str(r.get('context_kind','unknown'))]=by.get(str(r.get('context_kind','unknown')),0)+1
    margins=[float(r.get('coker_margin_proxy',0.0)) for r in rows]
    summary={'n':n,'accepted':len(acc),'accept_rate':len(acc)/max(1,n),'mean_margin':float(np.mean(margins)) if margins else 0.0,'by_kind':by}
    Path(args.out).parent.mkdir(parents=True,exist_ok=True); Path(args.out).write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8'); print(json.dumps(summary,indent=2,ensure_ascii=False)); return 0


def cmd_accepted_carrier_actions(args):
    summary = write_accepted_carrier_actions(args.accepted, args.out, min_margin=args.min_margin, accepted_only=not args.include_rejected)
    print(json.dumps({"summary": summary, "out": args.out}, indent=2, ensure_ascii=False)); return 0



def cmd_robust_accept(args):
    rows, summary = run_robust_acceptance(
        args.base_responses,
        args.candidate_responses,
        args.out,
        summary_out=args.report_out,
        accepted_actions_out=args.accepted_actions_out,
        per_row_out=args.per_row_out,
        margin_threshold=args.margin_threshold,
        cost_weight=args.cost_weight,
        carrier_bonus=args.carrier_weight,
        goal_bonus=args.goal_weight,
        max_mass=args.max_mass,
        ridge=args.ridge,
        z_value=args.robust_z,
        min_repeats=args.robust_min_repeats,
        min_success_rate=args.robust_min_success_rate,
        max_per_task=args.max_per_task,
    )
    print(json.dumps({"n_groups": summary.get("n_groups", 0), "n_accepted": summary.get("n_accepted", 0), "out": args.out, "report": args.report_out}, indent=2, ensure_ascii=False))
    return 0

def cmd_registry_accept(args):
    rows, summary = run_registry_acceptance(
        args.base_responses,
        args.registry_responses,
        args.audit_out or args.accepted_actions_out,
        summary_out=args.report_out,
        accepted_actions_out=args.accepted_actions_out,
        margin_threshold=args.margin_threshold,
        cost_weight=args.cost_weight,
        carrier_bonus=args.carrier_weight,
        goal_bonus=args.goal_weight,
        robust_radius=getattr(args, 'robust_radius', 0.0),
        robust_relative_radius=getattr(args, 'robust_relative_radius', 0.0),
        accept_on_robust=getattr(args, 'accept_on_robust', False),
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False)); return 0



def cmd_accept_candidates(args):
    rows, summary = accept_candidates_file(
        args.base_responses,
        args.candidate_responses,
        args.out,
        summary_out=args.summary_out,
        margin_threshold=args.margin_threshold,
        cost_weight=args.cost_weight,
        carrier_weight=args.carrier_weight,
        audit_penalty=args.audit_penalty,
        require_success=args.require_success,
    )
    print(json.dumps({"n": len(rows), "accepted": summary.get("accepted", 0), "out": args.out, "summary": args.summary_out}, indent=2, ensure_ascii=False))
    return 0

def cmd_promote_from_acceptance(args):
    reg = promote_registry_from_acceptance(args.registry, args.acceptance, args.out, min_accepted=args.min_accepted, min_mean_margin=args.min_mean_margin)
    print(json.dumps({"n_atoms": len(reg.atoms), "accepted_atoms": [a.atom_id for a in reg.atoms if a.status == "accepted"], "out": args.out}, indent=2, ensure_ascii=False)); return 0



def cmd_merge_action_files(args):
    meta = merge_action_files(args.inputs, args.out, max_actions=args.max_actions)
    print(json.dumps(meta, indent=2, ensure_ascii=False)); return 0


def cmd_compare_runs(args):
    rows = compare_pipeline_dirs(args.runs, out_json=args.out_json, out_csv=args.out_csv)
    print(json.dumps({"n": len(rows), "runs": rows}, indent=2, ensure_ascii=False)); return 0


def cmd_rgc_loop(args):
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    current_actions = args.actions
    summaries = []
    for i in range(args.rounds):
        rd = out / f"round_{i:02d}"
        rd.mkdir(parents=True, exist_ok=True)
        # Pipeline args mirror cmd_pipeline.  Keep this intentionally explicit so
        # future flags do not silently change loop semantics.
        pipe_args = argparse.Namespace(
            tasks=args.tasks, actions=current_actions, out=str(rd), dry_run=args.dry_run,
            jobs=args.jobs, max_actions=args.max_actions, candidate_mode=args.candidate_mode,
            state_candidates=args.state_candidates, quotient_tolerance=args.quotient_tolerance,
            carrier_threshold=args.carrier_threshold, lean_cmd=args.lean_cmd, workdir=args.workdir,
            timeout_s=args.timeout_s, keep_files=args.keep_files, cache_dir=(str(out/'cache') if args.cache_dir is None else args.cache_dir),
            trace_state=args.trace_state, import_mode=args.import_mode, resume=args.resume,
            flush_every=args.flush_every, fit_gamma=args.fit_gamma, gamma_horizon=args.gamma_horizon,
            qgen=args.qgen, qgen_ridge=1e-4, qgen_max_mass=1.0, qgen_top_defects=args.qgen_top_defects, qgen_top_contexts=args.qgen_top_contexts, qgen_top_carriers=args.qgen_top_carriers, qgen_top_failures=args.qgen_top_failures, qgen_margin_threshold=args.qgen_margin_threshold, qgen_cost_weight=0.05, qgen_carrier_weight=0.25, qgen_audit_penalty=1.0,
            mine_defects=True, mine_min_support=args.mine_min_support,
            mine_min_response_contrast=args.mine_min_response_contrast, mine_min_stability=args.mine_min_stability,
            mine_min_intervention_success=args.mine_min_intervention_success,
            mine_min_coker_reduction=args.mine_min_coker_reduction,
            registry_candidates=True, registry_max_candidates=args.registry_max_candidates,
            audit_registry_candidates=True, registry_audit_max_actions=args.registry_audit_max_actions,
            registry_accept_coker=True, registry_accept_margin=args.registry_accept_margin,
            registry_accept_max_per_task=args.registry_accept_max_per_task,
            registry_accept_cost_weight=args.registry_accept_cost_weight,
            registry_accept_carrier_weight=args.registry_accept_carrier_weight,
            promote_registry=True, promote_min_support=args.promote_min_support,
            promote_min_intervention_success=args.promote_min_intervention_success,
            promote_min_coker_reduction=args.promote_min_coker_reduction,
            promote_min_promotion_score=args.promote_min_promotion_score,
            promote_drop_rejected=False,
            premise_index=args.premise_index, premise_top_k=args.premise_top_k,
            premise_max_actions=args.premise_max_actions, audit_premise_candidates=args.audit_premise_candidates,
            premise_audit_max_actions=args.premise_audit_max_actions,
            carrier_accept=args.carrier_accept, carrier_accept_max_actions=args.carrier_accept_max_actions,
            carrier_accept_margin=args.carrier_accept_margin, carrier_accept_cost_weight=args.carrier_accept_cost_weight,
            promote_carrier_actions=args.promote_carrier_actions, promote_carrier_min_margin=args.promote_carrier_min_margin,
        )
        cmd_pipeline(pipe_args)
        next_actions = out / f"actions_round_{i+1:02d}.jsonl"
        merge_inputs = []
        if current_actions:
            merge_inputs.append(current_actions)
        for candidate in [
            rd/'registry_accepted_actions.jsonl',
            rd/'carrier_promoted_actions.jsonl',
            rd/'qgen'/'qgen_accepted_actions.jsonl' if args.qgen_merge_actions else None,
            rd/'premise_actions.jsonl' if args.merge_premise_actions else None,
        ]:
            if candidate and Path(candidate).exists():
                merge_inputs.append(str(candidate))
        merge_meta = merge_action_files(merge_inputs, next_actions, max_actions=args.next_action_cap)
        summary = compare_pipeline_dirs([rd])[0]
        summaries.append({"round": i, "run_dir": str(rd), "actions_in": current_actions, "actions_out": str(next_actions), "merge": merge_meta, "summary": summary})
        current_actions = str(next_actions)
    (out/'rgc_loop_summary.json').write_text(json.dumps(summaries, indent=2, ensure_ascii=False), encoding='utf-8')
    compare_pipeline_dirs([x['run_dir'] for x in summaries], out_json=out/'rgc_loop_compare.json', out_csv=out/'rgc_loop_compare.csv')
    print(json.dumps({"rounds": len(summaries), "out": str(out), "summary": str(out/'rgc_loop_summary.json')}, indent=2, ensure_ascii=False)); return 0


def cmd_expose_frontier(args):
    tasks_path = args.tasks
    # Normalize imports before frontier construction so prefixes can be audited
    # under the same core/mathlib mode as the later pipeline.
    if args.import_mode != "preserve":
        tasks = _normalize_tasks_imports(_load_tasks(tasks_path), args.import_mode, args.workdir if hasattr(args, 'workdir') else None, args.lean_cmd if hasattr(args, 'lean_cmd') else None)
        tmp = Path(args.out_tasks).with_suffix(".normalized_tasks.jsonl")
        write_jsonl(tmp, [t.to_dict() for t in tasks])
        tasks_path = str(tmp)
    summary = expose_frontier_files(
        tasks_path,
        args.out_tasks,
        out_exposures=args.out_exposures,
        out_actions=args.out_actions,
        include_identity=not args.no_identity,
        max_frontiers_per_task=args.max_frontiers_per_task,
        max_core_actions=args.max_core_actions,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False)); return 0


def cmd_frontier_pipeline(args):
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    frontier_tasks = out / "frontier_tasks.jsonl"
    frontier_exposures = out / "frontier_exposures.jsonl"
    frontier_actions = out / "frontier_core_actions.jsonl"
    cmd_expose_frontier(argparse.Namespace(
        tasks=args.tasks,
        out_tasks=str(frontier_tasks),
        out_exposures=str(frontier_exposures),
        out_actions=str(frontier_actions),
        no_identity=args.no_identity,
        max_frontiers_per_task=args.max_frontiers_per_task,
        max_core_actions=args.max_core_actions,
        import_mode=args.import_mode,
        lean_cmd=args.lean_cmd,
        workdir=args.workdir,
    ))
    # Run the normal pipeline on exposed frontier states using core actions only.
    pipe_args = argparse.Namespace(
        tasks=str(frontier_tasks), actions=str(frontier_actions), out=str(out / "frontier_run"), dry_run=args.dry_run,
        jobs=args.jobs, max_actions=args.max_actions, candidate_mode="basic", state_candidates=False,
        quotient_tolerance=args.quotient_tolerance, carrier_threshold=args.carrier_threshold,
        lean_cmd=args.lean_cmd, workdir=args.workdir, timeout_s=args.timeout_s, keep_files=args.keep_files,
        cache_dir=args.cache_dir or str(out / "cache"), trace_state=args.trace_state, import_mode="preserve", resume=args.resume,
        flush_every=args.flush_every, fit_gamma=args.fit_gamma, gamma_horizon=args.gamma_horizon,
        mine_defects=args.mine_defects, mine_min_support=args.mine_min_support,
        mine_min_response_contrast=args.mine_min_response_contrast, mine_min_stability=args.mine_min_stability,
        mine_min_intervention_success=args.mine_min_intervention_success,
        mine_min_coker_reduction=args.mine_min_coker_reduction,
        registry_candidates=args.registry_candidates, registry_max_candidates=args.registry_max_candidates,
        audit_registry_candidates=args.audit_registry_candidates, registry_audit_max_actions=args.registry_audit_max_actions,
        registry_accept_coker=args.registry_accept_coker, registry_accept_margin=args.registry_accept_margin,
        registry_accept_max_per_task=args.registry_accept_max_per_task, registry_accept_cost_weight=args.registry_accept_cost_weight,
        registry_accept_carrier_weight=args.registry_accept_carrier_weight,
        promote_registry=args.promote_registry, promote_min_support=args.promote_min_support,
        promote_min_intervention_success=args.promote_min_intervention_success,
        promote_min_coker_reduction=args.promote_min_coker_reduction,
        promote_min_promotion_score=args.promote_min_promotion_score,
        promote_drop_rejected=False,
        premise_index=args.premise_index, premise_top_k=args.premise_top_k,
        premise_max_actions=args.premise_max_actions, audit_premise_candidates=args.audit_premise_candidates,
        premise_audit_max_actions=args.premise_audit_max_actions,
        carrier_accept=args.carrier_accept, carrier_accept_max_actions=args.carrier_accept_max_actions,
        carrier_accept_margin=args.carrier_accept_margin, carrier_accept_cost_weight=args.carrier_accept_cost_weight,
        promote_carrier_actions=args.promote_carrier_actions, promote_carrier_min_margin=args.promote_carrier_min_margin,
    )
    cmd_pipeline(pipe_args)
    summary = {
        "frontier_tasks": str(frontier_tasks),
        "frontier_exposures": str(frontier_exposures),
        "frontier_actions": str(frontier_actions),
        "frontier_run": str(out / "frontier_run"),
    }
    (out / "frontier_pipeline_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False)); return 0


def cmd_ir_candidates(args):
    rows = ir_candidates_file(args.ir, args.out, max_candidates=args.max_candidates)
    print(json.dumps({"n": len(rows), "out": args.out}, indent=2, ensure_ascii=False)); return 0


def cmd_carrier_matrix(args):
    cm = build_carrier_matrix_from_responses(args.responses, args.out, shrink=args.shrink, min_count=args.min_count)
    print(json.dumps({"n_atoms": len(cm.atoms), "n_actions": len(cm.action_ids), "out": args.out}, indent=2, ensure_ascii=False)); return 0


def cmd_carrier_matrix_merge_patches(args):
    cm = merge_carrier_incidence_patches(args.matrix, args.patches, args.out, patch_weight=args.patch_weight, require_safe=args.require_safe)
    rep = {"n_atoms": len(cm.atoms), "n_actions": len(cm.action_ids), "out": args.out, "patches": args.patches}
    if getattr(args, "report_out", None):
        carrier_patch_report(args.patches, args.report_out)
        rep["report_out"] = args.report_out
    print(json.dumps(rep, indent=2, ensure_ascii=False)); return 0


def cmd_carrier_safe_actions(args):
    rep = annotate_actions_with_carrier_matrix(args.actions, args.matrix, args.out, budget=args.budget, keep_unsafe=args.keep_unsafe)
    print(json.dumps(rep, indent=2, ensure_ascii=False)); return 0


def cmd_multi_carrier_report(args):
    rep = multi_carrier_report(args.matrix, defects_path=args.defects, out=args.out)
    print(json.dumps(rep, indent=2, ensure_ascii=False)); return 0


def cmd_stage_report(args):
    stages = []
    if getattr(args, "run_dir", None):
        stages.extend(default_pipeline_stages(args.run_dir))
    if getattr(args, "stage", None):
        for spec in args.stage:
            if "=" in spec:
                name, path = spec.split("=", 1)
            else:
                path = spec
                name = Path(path).stem
            stages.append((name, Path(path)))
    rep = write_stage_report(stages, args.out, args.csv_out)
    print(json.dumps({"n_stages": rep.get("n_stages", 0), "out": args.out, "csv": args.csv_out}, indent=2, ensure_ascii=False))
    return 0


def cmd_contextual_probes(args):
    cfg = ContextualProbeConfig(
        max_base_actions=args.max_base_actions,
        max_left_contexts=args.max_left_contexts,
        max_right_contexts=args.max_right_contexts,
        include_identity=not args.no_identity_context,
        include_base_identity_probe=not args.no_base_identity_probe,
        mode=args.mode,
    )
    rows, summary = generate_contextual_probe_actions(args.actions, out=args.out, contexts_path=args.contexts, config=cfg)
    summary["out"] = args.out
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def cmd_contextual_congruence(args):
    rep = contextual_congruence_from_files(
        args.responses,
        actions=args.actions,
        out_dir=args.out,
        cosine_threshold=args.cosine_threshold,
        min_observations=args.min_observations,
        min_shared_support=args.min_shared_support,
    )
    print(json.dumps(rep, indent=2, ensure_ascii=False))
    return 0

def cmd_report(args):
    summary=write_run_report(args.run_dir,args.out); print(json.dumps(summary,indent=2,ensure_ascii=False)); return 0


def cmd_pipeline(args):
    out=Path(args.out); out.mkdir(parents=True,exist_ok=True); audit_dir=out/'audit'
    def _pipeline_audit(tasks_path, actions_path, out_dir, max_actions, *, state_candidates=False, candidate_mode=None):
        scheduled_actions_path = actions_path
        if getattr(args, 'audit_scheduler', False) and actions_path:
            sched_dir = Path(out_dir) / 'audit_scheduler'
            sched_dir.mkdir(parents=True, exist_ok=True)
            scheduled_actions_path = sched_dir / 'scheduled_actions.jsonl'
            active_audit_schedule_from_files(
                candidates_path=actions_path,
                out_actions=scheduled_actions_path,
                out_rows=sched_dir / 'audit_schedule_rows.jsonl',
                out_report=sched_dir / 'audit_schedule_report.json',
                db_path=getattr(args, 'audit_scheduler_db', None),
                response_paths=[getattr(args, 'audit_scheduler_responses')] if getattr(args, 'audit_scheduler_responses', None) else None,
                response_normal=None,
                carrier_normal=None,
                config=SchedulerConfig(
                    top_k=getattr(args, 'audit_scheduler_budget', None) or max_actions,
                    per_task_cap=getattr(args, 'audit_scheduler_per_task_cap', None),
                    response_weight=getattr(args, 'audit_scheduler_coker_weight', 1.0),
                    carrier_weight=getattr(args, 'audit_scheduler_carrier_weight', 0.5),
                    uncertainty_weight=getattr(args, 'audit_scheduler_uncertainty_weight', 0.25),
                    novelty_weight=getattr(args, 'audit_scheduler_novelty_weight', 0.15),
                    success_weight=getattr(args, 'audit_scheduler_success_weight', 0.25),
                    cost_weight=getattr(args, 'audit_scheduler_cost_weight', 0.10),
                    timeout_weight=getattr(args, 'audit_scheduler_timeout_weight', 0.50),
                ),
            )
            # Legacy compatibility path used by early v36 experiments.
            legacy_sched_dir = Path(args.out) / 'audit_schedules'
            legacy_sched_dir.mkdir(parents=True, exist_ok=True)
            try:
                import shutil
                shutil.copyfile(scheduled_actions_path, legacy_sched_dir / 'audit_scheduled_actions.jsonl')
                shutil.copyfile(sched_dir / 'audit_schedule_report.json', legacy_sched_dir / 'audit_schedule_report.json')
            except Exception:
                pass
        ns = argparse.Namespace(tasks=str(tasks_path), actions=str(scheduled_actions_path) if scheduled_actions_path else None, out=str(out_dir), jobs=args.jobs, max_actions=max_actions, state_candidates=state_candidates, candidate_mode=candidate_mode or args.candidate_mode, lean_cmd=args.lean_cmd, workdir=args.workdir, timeout_s=args.timeout_s, dry_run=args.dry_run, keep_files=args.keep_files, cache_dir=args.cache_dir or str(out/'cache'), trace_state=args.trace_state, import_mode=args.import_mode, resume=args.resume, flush_every=args.flush_every, batch_size=getattr(args, 'bulk_batch_size', 64), server_cmd=getattr(args, 'server_cmd', None), server_backend=getattr(args, 'server_backend', 'auto'), server_no_fallback=getattr(args, 'server_no_fallback', False), native_exec_mode=getattr(args, 'native_exec_mode', 'source_check'))
        if getattr(args, 'audit_mode', 'batch') == 'server':
            return cmd_server_audit(ns)
        if getattr(args, 'audit_mode', 'batch') == 'bulk' and not args.dry_run:
            return cmd_bulk_audit(ns)
        return cmd_batch_audit(ns)
    frontier_tasks_path = None
    if getattr(args, 'expose_frontier', False):
        frontier_tasks_path = out / 'frontier_tasks.jsonl'
        write_jsonl(out / '_pipeline_input_tasks.jsonl', [t.to_dict() for t in _normalize_tasks_imports(_load_tasks(args.tasks), args.import_mode, args.workdir, args.lean_cmd)])
        write_exposure_frontiers(out / '_pipeline_input_tasks.jsonl', frontier_tasks_path, out / 'exposure_frontier_report.jsonl', _executor_from_args(args), max_exposures=getattr(args, 'expose_max_exposures', 8), allow_identity=not getattr(args, 'expose_no_identity', False))
        args = argparse.Namespace(**{**vars(args), 'tasks': str(frontier_tasks_path)})
    tasks_for_pipeline = args.tasks
    frontier_summary = None
    if getattr(args, 'frontier_normalize', False):
        frontier_dir = out/'frontier'
        cmd_expose_frontiers(argparse.Namespace(tasks=args.tasks,out=str(frontier_dir),max_prefixes=args.frontier_max_prefixes,include_identity=args.frontier_include_identity,accept_status=['partial','dry_run'],lean_cmd=args.lean_cmd,workdir=args.workdir,timeout_s=args.timeout_s,dry_run=args.dry_run,keep_files=args.keep_files,cache_dir=args.cache_dir or str(out/'cache'),trace_state=args.trace_state,import_mode=args.import_mode,resume=args.resume))
        ft = frontier_dir/'frontier_tasks.jsonl'
        if ft.exists() and read_jsonl(ft):
            tasks_for_pipeline = str(ft)
            frontier_summary = json.loads((frontier_dir/'frontier_summary.json').read_text(encoding='utf-8')) if (frontier_dir/'frontier_summary.json').exists() else {'frontier_tasks': str(ft)}
    _pipeline_audit(tasks_for_pipeline, args.actions, audit_dir, args.max_actions, state_candidates=args.state_candidates or args.candidate_mode=='state', candidate_mode=args.candidate_mode)
    if getattr(args, 'audit_exposures', False):
        exp_actions = out/'exposure_actions.jsonl'
        cmd_exposure_candidates(argparse.Namespace(tasks=tasks_for_pipeline, out=str(exp_actions), include_identity=False, import_mode=args.import_mode))
        exp_dir = out/'exposure_audit'
        _pipeline_audit(tasks_for_pipeline, str(exp_actions), exp_dir, args.exposure_audit_max_actions, state_candidates=False, candidate_mode='state')
        summarize_exposure_audit(exp_dir, out/'exposure_audit_report.json')
    cmd_action_report(argparse.Namespace(responses=str(audit_dir/'responses.jsonl'), out=str(out/'action_report.json'), csv_out=str(out/'action_report.csv'), group_keys=None))
    # v41: arithmetic teacher graph.  This treats arithmetic identities as
    # goal-state transformation charts g -> tau_I(g), not as data curriculum.
    arithmetic_teacher_dir = None
    arithmetic_teacher_actions_path = None
    arithmetic_teacher_audit_dir = None
    arithmetic_teacher_audit_report_path = None
    if getattr(args, 'arithmetic_teacher_graph', False):
        arithmetic_teacher_dir = out / 'arithmetic_teacher'
        arithmetic_teacher_dir.mkdir(parents=True, exist_ok=True)
        _arith_ss_arg = getattr(args, 'arithmetic_teacher_structured_states', None)
        structured_states_path = Path(_arith_ss_arg) if _arith_ss_arg else Path('__missing_arithmetic_teacher_structured_states__')
        if not structured_states_path.exists():
            # Prefer server-audit structured states if present; otherwise build a
            # stable structured-state chart from tasks and micro-audit logs.
            candidate_ss = audit_dir / 'structured_states.jsonl'
            if candidate_ss.exists():
                structured_states_path = candidate_ss
            else:
                structured_states_path = out / 'structured_states.jsonl'
                try:
                    structured_state_extract_cli(tasks=tasks_for_pipeline, audits=str(audit_dir/'micro_audit.jsonl'), out=str(structured_states_path), summary_out=str(out/'structured_state_summary.json'))
                except Exception:
                    # Last-resort tasks-only chart.
                    structured_state_extract_cli(tasks=tasks_for_pipeline, out=str(structured_states_path), summary_out=str(out/'structured_state_summary.json'))
        generate_arithmetic_teacher_graph(
            structured_states_path,
            arithmetic_teacher_dir,
            identities_path=getattr(args, 'arithmetic_teacher_identities', None),
            actions_path=args.actions,
            responses_path=audit_dir/'responses.jsonl',
            max_transforms_per_state=getattr(args, 'arithmetic_teacher_max_transforms_per_state', 32),
            emit_candidate_actions=not getattr(args, 'arithmetic_teacher_no_actions', False),
        )
        transformations = arithmetic_teacher_dir / 'arithmetic_teacher_transformations.jsonl'
        if transformations.exists():
            arithmetic_teacher_audit_report_path = arithmetic_teacher_dir / 'arithmetic_teacher_audit_report.json'
            audit_arithmetic_teacher_transitions(transformations, structured_states_path, arithmetic_teacher_dir / 'arithmetic_teacher_audit_rows.jsonl', report_out=arithmetic_teacher_audit_report_path)
            if getattr(args, 'arithmetic_teacher_kernel_audit', False):
                kernel_dir = arithmetic_teacher_dir / 'kernel_transition_audit'
                audit_arithmetic_teacher_kernel_transitions(
                    transformations,
                    tasks_for_pipeline,
                    kernel_dir,
                    identities_path=getattr(args, 'arithmetic_teacher_identities', None),
                    structured_states_path=structured_states_path,
                    server_config=_server_config_from_args(args),
                    max_transitions=getattr(args, 'arithmetic_teacher_kernel_audit_max_transitions', 32),
                )
                if getattr(args, 'arithmetic_teacher_cocycle_audit', False):
                    cocycle_dir = arithmetic_teacher_dir / 'cocycle_audit'
                    arithmetic_teacher_cocycle_from_files(
                        kernel_dir / 'arithmetic_teacher_kernel_audit_rows.jsonl',
                        cocycle_dir,
                        compositions_path=getattr(args, 'arithmetic_teacher_cocycle_compositions', None),
                        min_count=getattr(args, 'arithmetic_teacher_cocycle_min_count', 1),
                        accept_threshold=getattr(args, 'arithmetic_teacher_cocycle_accept_threshold', 1.0),
                        min_verified_rate=getattr(args, 'arithmetic_teacher_cocycle_min_verified_rate', 0.0),
                        max_tail_radius=getattr(args, 'arithmetic_teacher_cocycle_max_tail_radius', None),
                        max_auto_pairs=getattr(args, 'arithmetic_teacher_cocycle_max_auto_pairs', 0),
                    )
        arithmetic_teacher_actions_path = arithmetic_teacher_dir / 'arithmetic_teacher_actions.jsonl'
        if getattr(args, 'audit_arithmetic_teacher_candidates', False) and arithmetic_teacher_actions_path.exists():
            arithmetic_teacher_audit_dir = out / 'arithmetic_teacher_audit'
            _pipeline_audit(tasks_for_pipeline, str(arithmetic_teacher_actions_path), arithmetic_teacher_audit_dir, getattr(args, 'arithmetic_teacher_audit_max_actions', 16), state_candidates=False, candidate_mode='state')
            cmd_action_report(argparse.Namespace(responses=str(arithmetic_teacher_audit_dir/'responses.jsonl'), out=str(out/'arithmetic_teacher_action_report.json'), csv_out=str(out/'arithmetic_teacher_action_report.csv'), group_keys=None))
    # v32: finite contextual probe generation.  This creates A∘C∘B-style
    # action probes, audits them, and optionally mines contextual response
    # congruence from their responses.  These probes are charts/witnesses for
    # operation-stable congruence; they are not canonical contexts.
    contextual_probe_dir = None
    contextual_probe_candidates_path = None
    contextual_probe_audit_dir = None
    contextual_probe_accepted_actions_path = None
    contextual_probe_robust_accepted_actions_path = None
    contextual_probe_congruence_dir = None
    contextual_probe_report_path = None
    if getattr(args, 'contextual_probes', False):
        contextual_probe_dir = out / 'contextual_probes'
        contextual_probe_dir.mkdir(parents=True, exist_ok=True)
        contextual_probe_candidates_path = contextual_probe_dir / 'contextual_probe_candidates.jsonl'
        if not args.actions:
            (contextual_probe_dir / 'contextual_probe_report.json').write_text(json.dumps({
                'schema_version': 'lean-rgc-contextual-probe-loop-v32.0',
                'status': 'skipped_no_actions',
                'canonical_status': 'contextual_probe_chart_only_not_canonical',
            }, indent=2, ensure_ascii=False), encoding='utf-8')
        else:
            _, cp_summary = generate_contextual_candidates(
                args.actions,
                contextual_probe_candidates_path,
                contexts_path=getattr(args, 'contextual_probe_contexts', None),
                max_left=getattr(args, 'contextual_probe_max_left', 4),
                max_right=getattr(args, 'contextual_probe_max_right', 4),
                max_core=getattr(args, 'contextual_probe_max_core', None),
                max_candidates=getattr(args, 'contextual_probe_max_candidates', None),
                include_identity=not getattr(args, 'contextual_probe_no_identity', False),
                include_left=not getattr(args, 'contextual_probe_no_left', False),
                include_right=not getattr(args, 'contextual_probe_no_right', False),
            )
            cp_summary.update({
                'schema_version': 'lean-rgc-contextual-probe-loop-v32.0',
                'canonical_status': 'contextual_probe_action_chart_only_not_canonical',
            })
            contextual_probe_report_path = contextual_probe_dir / 'contextual_probe_report.json'
            contextual_probe_report_path.write_text(json.dumps(cp_summary, indent=2, ensure_ascii=False), encoding='utf-8')
            if getattr(args, 'audit_contextual_probe_candidates', False) and contextual_probe_candidates_path.exists():
                contextual_probe_audit_dir = out / 'contextual_probe_audit'
                _pipeline_audit(tasks_for_pipeline, str(contextual_probe_candidates_path), contextual_probe_audit_dir, getattr(args, 'contextual_probe_audit_max_actions', 24), state_candidates=False, candidate_mode='state')
                cmd_action_report(argparse.Namespace(responses=str(contextual_probe_audit_dir/'responses.jsonl'), out=str(out/'contextual_probe_action_report.json'), csv_out=str(out/'contextual_probe_action_report.csv'), group_keys=None))
                if getattr(args, 'contextual_probe_congruence', False):
                    contextual_probe_congruence_dir = contextual_probe_dir / 'contextual_probe_congruence'
                    contextual_response_congruence_from_files(
                        contextual_probe_audit_dir/'responses.jsonl',
                        contextual_probe_congruence_dir,
                        context_mode=getattr(args, 'contextual_probe_congruence_context_mode', getattr(args, 'contextual_congruence_context_mode', 'state')),
                        include_carrier=not getattr(args, 'contextual_probe_congruence_no_carrier', False),
                        min_count=getattr(args, 'contextual_probe_congruence_min_count', getattr(args, 'contextual_congruence_min_count', 1)),
                        cosine_threshold=getattr(args, 'contextual_probe_congruence_cosine_threshold', getattr(args, 'contextual_congruence_cosine_threshold', 0.95)),
                        distance_threshold=getattr(args, 'contextual_probe_congruence_distance_threshold', getattr(args, 'contextual_congruence_distance_threshold', 0.25)),
                        min_context_jaccard=getattr(args, 'contextual_probe_congruence_min_context_jaccard', getattr(args, 'contextual_congruence_min_context_jaccard', 0.0)),
                    )
                if getattr(args, 'contextual_probe_accept_coker', False):
                    if getattr(args, 'contextual_probe_robust_coker_accept', False):
                        contextual_probe_robust_accepted_actions_path = out / 'contextual_probe_robust_accepted_actions.jsonl'
                        cmd_robust_coker_accept(argparse.Namespace(
                            base_responses=str(audit_dir/'responses.jsonl'),
                            candidate_responses=str(contextual_probe_audit_dir/'responses.jsonl'),
                            out_report=str(out/'contextual_probe_robust_acceptance_report.json'),
                            out_actions=str(contextual_probe_robust_accepted_actions_path),
                            out_rows=str(out/'contextual_probe_robust_acceptance_rows.jsonl'),
                            csv_out=str(out/'contextual_probe_robust_acceptance_rows.csv'),
                            margin_threshold=getattr(args, 'contextual_probe_accept_margin', 0.0),
                            holdout_fraction=getattr(args, 'contextual_probe_robust_coker_holdout_fraction', 0.35),
                            ridge=1e-4,
                            max_mass=1.0,
                            cost_weight=getattr(args, 'contextual_probe_accept_cost_weight', 0.05),
                            carrier_gain_weight=getattr(args, 'contextual_probe_robust_coker_carrier_gain_weight', 0.25),
                            carrier_violation_weight=getattr(args, 'contextual_probe_accept_carrier_weight', 0.7),
                            audit_penalty=getattr(args, 'contextual_probe_robust_coker_audit_penalty', 1.0),
                            uncertainty_weight=getattr(args, 'contextual_probe_robust_coker_uncertainty_weight', 0.10),
                            require_success=getattr(args, 'contextual_probe_robust_coker_require_success', False),
                            max_actions=getattr(args, 'contextual_probe_accept_max_per_task', 16),
                        ))
                        contextual_probe_accepted_actions_path = out / 'contextual_probe_accepted_actions.jsonl'
                        if contextual_probe_robust_accepted_actions_path.exists():
                            contextual_probe_accepted_actions_path.write_text(contextual_probe_robust_accepted_actions_path.read_text(encoding='utf-8'), encoding='utf-8')
                    else:
                        contextual_probe_accepted_actions_path = out / 'contextual_probe_accepted_actions.jsonl'
                        cmd_registry_accept(argparse.Namespace(
                            base_responses=str(audit_dir/'responses.jsonl'),
                            registry_responses=str(contextual_probe_audit_dir/'responses.jsonl'),
                            accepted_actions_out=str(contextual_probe_accepted_actions_path),
                            report_out=str(out/'contextual_probe_acceptance_report.json'),
                            audit_out=str(out/'contextual_probe_acceptance_rows.jsonl'),
                            margin_threshold=getattr(args, 'contextual_probe_accept_margin', 0.0),
                            max_per_task=getattr(args, 'contextual_probe_accept_max_per_task', 16),
                            goal_weight=1.0, type_weight=0.6, search_weight=0.4,
                            carrier_weight=getattr(args, 'contextual_probe_accept_carrier_weight', 0.7), audit_weight=0.2,
                            success_bonus=0.25, fail_penalty=0.25, timeout_penalty=1.0,
                            cost_weight=getattr(args, 'contextual_probe_accept_cost_weight', 0.05),
                        ))
    contextual_congruence_dir = None
    contextual_congruence_report_path = None
    contextual_congruence_classes_path = None
    contextual_congruence_representatives_path = None
    if getattr(args, 'contextual_congruence', False):
        contextual_congruence_dir = out / 'contextual_congruence'
        contextual_response_congruence_from_files(
            audit_dir/'responses.jsonl',
            contextual_congruence_dir,
            context_mode=getattr(args, 'contextual_congruence_context_mode', 'state'),
            include_carrier=not getattr(args, 'contextual_congruence_no_carrier', False),
            min_count=getattr(args, 'contextual_congruence_min_count', 1),
            cosine_threshold=getattr(args, 'contextual_congruence_cosine_threshold', 0.95),
            distance_threshold=getattr(args, 'contextual_congruence_distance_threshold', 0.25),
            min_context_jaccard=getattr(args, 'contextual_congruence_min_context_jaccard', 0.0),
        )
        contextual_congruence_report_path = contextual_congruence_dir / 'contextual_response_congruence_report.json'
        contextual_congruence_classes_path = contextual_congruence_dir / 'response_congruence_classes.jsonl'
        contextual_congruence_representatives_path = contextual_congruence_dir / 'response_congruence_representatives.jsonl'
    # v33: finite response-quotient registry.  This projects contextual
    # response-congruence classes into an action->class->representative map.
    # It is still a finite chart of operation-stable congruence, not canonical.
    response_quotient_dir = None
    response_quotient_registry_path = None
    response_quotient_representatives_path = None
    response_quotient_projected_actions_path = None
    if getattr(args, 'response_quotient_registry', False):
        source_cong_dir = None
        if contextual_probe_congruence_dir and (contextual_probe_congruence_dir / 'response_congruence_classes.jsonl').exists():
            source_cong_dir = contextual_probe_congruence_dir
        elif contextual_congruence_dir and (contextual_congruence_dir / 'response_congruence_classes.jsonl').exists():
            source_cong_dir = contextual_congruence_dir
        if source_cong_dir:
            response_quotient_dir = out / 'response_quotient'
            response_quotient_registry = response_quotient_from_congruence_dir(
                source_cong_dir,
                actions_path=args.actions,
                out_dir=response_quotient_dir,
                min_members=getattr(args, 'response_quotient_min_members', 1),
                min_quality=getattr(args, 'response_quotient_min_quality', None),
            )
            response_quotient_registry_path = response_quotient_dir / 'response_quotient_registry.json'
            response_quotient_representatives_path = response_quotient_dir / 'response_quotient_representatives.jsonl'
            if getattr(args, 'response_quotient_project_actions', False) and args.actions:
                response_quotient_projected_actions_path = out / 'response_quotient_projected_actions.jsonl'
                project_actions_by_response_quotient(
                    args.actions,
                    response_quotient_registry_path,
                    response_quotient_projected_actions_path,
                    annotate_only=getattr(args, 'response_quotient_annotate_only', False),
                )
    quotient_coordinate_dir = None
    quotient_coordinate_candidates_path = None
    quotient_coordinate_registry_path = None
    quotient_coordinate_registry_candidates_path = None
    quotient_coordinate_audit_dir = None
    quotient_coordinate_accepted_actions_path = None
    quotient_coordinate_robust_accepted_actions_path = None
    quotient_coordinate_normal_path = None
    quotient_coordinate_validation_report_path = None
    quotient_coordinate_validation_report_path = None
    quotient_coordinate_response_normal_path = None
    qgen_dir = None
    qgen_context_candidates_path = None
    qgen_accepted_actions_path = None
    qgen_defect_registry_path = None
    qgen_carrier_incidence_path = None
    qgen_failure_signatures_path = None
    qgen_lineage_path = None
    qgen_registry_candidates_path = None
    qgen_registry_audit_dir = None
    qgen_registry_accepted_path = None
    if getattr(args, 'qgen', False):
        qgen_dir = out / 'qgen'
        qgen_from_files(
            audit_dir/'responses.jsonl',
            audits=audit_dir/'micro_audit.jsonl',
            out_dir=qgen_dir,
            ridge=args.qgen_ridge,
            max_mass=args.qgen_max_mass,
            top_defects=args.qgen_top_defects,
            top_contexts=args.qgen_top_contexts,
            top_carriers=args.qgen_top_carriers,
            top_failures=args.qgen_top_failures,
            margin_threshold=args.qgen_margin_threshold,
            cost_weight=args.qgen_cost_weight,
            carrier_weight=args.qgen_carrier_weight,
            audit_penalty=args.qgen_audit_penalty,
        )
        qgen_context_candidates_path = qgen_dir / 'qgen_context_candidates.jsonl'
        qgen_accepted_actions_path = qgen_dir / 'qgen_accepted_actions.jsonl'
        qgen_defect_registry_path = qgen_dir / 'qgen_defect_registry.json'
        qgen_carrier_incidence_path = qgen_dir / 'qgen_carrier_incidence.jsonl'
        qgen_failure_signatures_path = qgen_dir / 'qgen_failure_signatures.jsonl'
        qgen_lineage_path = qgen_dir / 'qgen_lineage.json'
        build_qgen_lineage(qgen_dir, out=qgen_lineage_path)
        if getattr(args, 'qgen_registry_candidates', False) and qgen_defect_registry_path.exists():
            qgen_registry_candidates_path = out / 'qgen_registry_candidates.jsonl'
            cmd_registry_candidates(argparse.Namespace(tasks=tasks_for_pipeline, registry=str(qgen_defect_registry_path), out=str(qgen_registry_candidates_path), max_candidates=args.qgen_registry_max_candidates))
    # v34: carrier-quotient mining.  This mines carrier coker residuals
    # into finite carrier-coordinate candidates q_phi^C(c)=<phi,c>.
    carrier_quotient_dir = None
    carrier_quotient_candidates_path = None
    carrier_quotient_registry_path = None
    carrier_quotient_patch_path = None
    carrier_quotient_audit_dir = None
    carrier_quotient_accepted_actions_path = None
    carrier_quotient_robust_accepted_actions_path = None
    if getattr(args, 'carrier_quotient', False):
        carrier_quotient_dir = out / 'carrier_quotient'
        carrier_quotient_from_files(
            audit_dir/'responses.jsonl',
            out_dir=carrier_quotient_dir,
            ridge=getattr(args, 'carrier_quotient_ridge', 1e-4),
            max_mass=getattr(args, 'carrier_quotient_max_mass', 1.0),
            cosine_threshold=getattr(args, 'carrier_quotient_cosine_threshold', 0.85),
            min_states=getattr(args, 'carrier_quotient_min_states', 1),
            top_action_scores=getattr(args, 'carrier_quotient_top_action_scores', 128),
            margin_threshold=getattr(args, 'carrier_quotient_margin_threshold', 0.0),
            validate=getattr(args, 'carrier_quotient_validate', False),
            infer_defect_from_violations=not getattr(args, 'carrier_quotient_no_infer_defect_from_violations', False),
        )
        carrier_quotient_candidates_path = carrier_quotient_dir / 'carrier_quotient_candidates.jsonl'
        carrier_quotient_registry_path = carrier_quotient_dir / 'carrier_quotient_defect_registry.json'
        carrier_quotient_patch_path = carrier_quotient_dir / 'carrier_quotient_incidence_patches.jsonl'
        if getattr(args, 'audit_carrier_quotient_candidates', False) and carrier_quotient_candidates_path.exists():
            carrier_quotient_audit_dir = out / 'carrier_quotient_audit'
            _pipeline_audit(tasks_for_pipeline, str(carrier_quotient_candidates_path), carrier_quotient_audit_dir, getattr(args, 'carrier_quotient_audit_max_actions', 16), state_candidates=False, candidate_mode='state')
            cmd_action_report(argparse.Namespace(responses=str(carrier_quotient_audit_dir/'responses.jsonl'), out=str(out/'carrier_quotient_action_report.json'), csv_out=str(out/'carrier_quotient_action_report.csv'), group_keys=None))
            if getattr(args, 'carrier_quotient_accept_coker', False):
                if getattr(args, 'carrier_quotient_robust_coker_accept', False):
                    carrier_quotient_robust_accepted_actions_path = out / 'carrier_quotient_robust_accepted_actions.jsonl'
                    cmd_robust_coker_accept(argparse.Namespace(
                        base_responses=str(audit_dir/'responses.jsonl'),
                        candidate_responses=str(carrier_quotient_audit_dir/'responses.jsonl'),
                        out_report=str(out/'carrier_quotient_robust_acceptance_report.json'),
                        out_actions=str(carrier_quotient_robust_accepted_actions_path),
                        out_rows=str(out/'carrier_quotient_robust_acceptance_rows.jsonl'),
                        csv_out=str(out/'carrier_quotient_robust_acceptance_rows.csv'),
                        margin_threshold=getattr(args, 'carrier_quotient_accept_margin', 0.0),
                        holdout_fraction=getattr(args, 'carrier_quotient_robust_coker_holdout_fraction', 0.35),
                        ridge=1e-4,
                        max_mass=1.0,
                        cost_weight=getattr(args, 'carrier_quotient_accept_cost_weight', 0.05),
                        carrier_gain_weight=getattr(args, 'carrier_quotient_robust_coker_carrier_gain_weight', 0.25),
                        carrier_violation_weight=getattr(args, 'carrier_quotient_accept_carrier_weight', 0.7),
                        audit_penalty=getattr(args, 'carrier_quotient_robust_coker_audit_penalty', 1.0),
                        uncertainty_weight=getattr(args, 'carrier_quotient_robust_coker_uncertainty_weight', 0.10),
                        require_success=getattr(args, 'carrier_quotient_robust_coker_require_success', False),
                        max_actions=getattr(args, 'carrier_quotient_accept_max_per_task', 16),
                    ))
                else:
                    carrier_quotient_accepted_actions_path = out / 'carrier_quotient_accepted_actions.jsonl'
                    cmd_registry_accept(argparse.Namespace(
                        base_responses=str(audit_dir/'responses.jsonl'),
                        registry_responses=str(carrier_quotient_audit_dir/'responses.jsonl'),
                        accepted_actions_out=str(carrier_quotient_accepted_actions_path),
                        report_out=str(out/'carrier_quotient_acceptance_report.json'),
                        audit_out=str(out/'carrier_quotient_acceptance_rows.jsonl'),
                        margin_threshold=getattr(args, 'carrier_quotient_accept_margin', 0.0),
                        max_per_task=getattr(args, 'carrier_quotient_accept_max_per_task', 16),
                        goal_weight=1.0, type_weight=0.6, search_weight=0.4,
                        carrier_weight=getattr(args, 'carrier_quotient_accept_carrier_weight', 0.7), audit_weight=0.2,
                        success_bonus=0.25, fail_penalty=0.25, timeout_penalty=1.0,
                        cost_weight=getattr(args, 'carrier_quotient_accept_cost_weight', 0.05),
                    ))

    # v26: quotient-coordinate generation.  This mines coker normals into
    # finite linear quotient-coordinate candidates q_phi(d)=<phi,d>.  The
    # outputs remain charts/witnesses until validated, audited and promoted.
    quotient_coordinate_dir = None
    quotient_coordinate_candidates_path = None
    quotient_coordinate_registry_path = None
    quotient_coordinate_registry_candidates_path = None
    quotient_coordinate_audit_dir = None
    quotient_coordinate_accepted_actions_path = None
    quotient_coordinate_robust_accepted_actions_path = None
    if getattr(args, 'quotient_coordinates', False):
        quotient_coordinate_dir = out / 'quotient_coordinates'
        run_quotient_coordinate_loop(
            responses=audit_dir/'responses.jsonl',
            out_dir=quotient_coordinate_dir,
            ridge=getattr(args, 'quotient_coordinate_ridge', 1e-4),
            max_mass=getattr(args, 'quotient_coordinate_max_mass', 1.0),
            cosine_threshold=getattr(args, 'quotient_coordinate_cosine_threshold', 0.85),
            min_states=getattr(args, 'quotient_coordinate_min_states', 1),
            top_action_scores=getattr(args, 'quotient_coordinate_top_action_scores', 128),
            margin_threshold=getattr(args, 'quotient_coordinate_margin_threshold', 0.0),
            validate=getattr(args, 'quotient_coordinate_validate', False),
        )
        quotient_coordinate_candidates_path = quotient_coordinate_dir / 'quotient_coordinate_selected_actions.jsonl'
        quotient_coordinate_registry_path = quotient_coordinate_dir / 'quotient_coordinate_defect_registry.json'
        quotient_coordinate_normal_path = quotient_coordinate_dir / 'quotient_coordinate_response_normal.json'
        quotient_coordinate_response_normal_path = quotient_coordinate_normal_path
        quotient_coordinate_validation_report_path = quotient_coordinate_dir / 'quotient_coordinate_validation_report.json'
        if getattr(args, 'quotient_coordinate_registry_candidates', False) and quotient_coordinate_registry_path.exists():
            quotient_coordinate_registry_candidates_path = out / 'quotient_coordinate_registry_candidates.jsonl'
            cmd_registry_candidates(argparse.Namespace(tasks=tasks_for_pipeline, registry=str(quotient_coordinate_registry_path), out=str(quotient_coordinate_registry_candidates_path), max_candidates=getattr(args, 'quotient_coordinate_registry_max_candidates', 64)))
        if getattr(args, 'audit_quotient_coordinate_candidates', False) and quotient_coordinate_candidates_path.exists():
            quotient_coordinate_audit_dir = out / 'quotient_coordinate_audit'
            _pipeline_audit(tasks_for_pipeline, str(quotient_coordinate_candidates_path), quotient_coordinate_audit_dir, getattr(args, 'quotient_coordinate_audit_max_actions', 16), state_candidates=False, candidate_mode='state')
            cmd_action_report(argparse.Namespace(responses=str(quotient_coordinate_audit_dir/'responses.jsonl'), out=str(out/'quotient_coordinate_action_report.json'), csv_out=str(out/'quotient_coordinate_action_report.csv'), group_keys=None))
            if getattr(args, 'quotient_coordinate_accept_coker', False):
                if getattr(args, 'quotient_coordinate_robust_coker_accept', False):
                    quotient_coordinate_robust_accepted_actions_path = out / 'quotient_coordinate_robust_accepted_actions.jsonl'
                    cmd_robust_coker_accept(argparse.Namespace(
                        base_responses=str(audit_dir/'responses.jsonl'),
                        candidate_responses=str(quotient_coordinate_audit_dir/'responses.jsonl'),
                        out_report=str(out/'quotient_coordinate_robust_acceptance_report.json'),
                        out_actions=str(quotient_coordinate_robust_accepted_actions_path),
                        out_rows=str(out/'quotient_coordinate_robust_acceptance_rows.jsonl'),
                        csv_out=str(out/'quotient_coordinate_robust_acceptance_rows.csv'),
                        margin_threshold=getattr(args, 'quotient_coordinate_accept_margin', 0.0),
                        holdout_fraction=getattr(args, 'quotient_coordinate_robust_coker_holdout_fraction', 0.35),
                        ridge=1e-4,
                        max_mass=1.0,
                        cost_weight=getattr(args, 'quotient_coordinate_accept_cost_weight', 0.05),
                        carrier_gain_weight=getattr(args, 'quotient_coordinate_robust_coker_carrier_gain_weight', 0.25),
                        carrier_violation_weight=getattr(args, 'quotient_coordinate_accept_carrier_weight', 0.7),
                        audit_penalty=getattr(args, 'quotient_coordinate_robust_coker_audit_penalty', 1.0),
                        uncertainty_weight=getattr(args, 'quotient_coordinate_robust_coker_uncertainty_weight', 0.10),
                        require_success=getattr(args, 'quotient_coordinate_robust_coker_require_success', False),
                        max_actions=getattr(args, 'quotient_coordinate_accept_max_per_task', 16),
                    ))
                else:
                    quotient_coordinate_accepted_actions_path = out / 'quotient_coordinate_accepted_actions.jsonl'
                    cmd_registry_accept(argparse.Namespace(
                        base_responses=str(audit_dir/'responses.jsonl'),
                        registry_responses=str(quotient_coordinate_audit_dir/'responses.jsonl'),
                        accepted_actions_out=str(quotient_coordinate_accepted_actions_path),
                        report_out=str(out/'quotient_coordinate_acceptance_report.json'),
                        audit_out=str(out/'quotient_coordinate_acceptance_rows.jsonl'),
                        margin_threshold=getattr(args, 'quotient_coordinate_accept_margin', 0.0),
                        max_per_task=getattr(args, 'quotient_coordinate_accept_max_per_task', 16),
                        goal_weight=1.0, type_weight=0.6, search_weight=0.4,
                        carrier_weight=getattr(args, 'quotient_coordinate_accept_carrier_weight', 0.7), audit_weight=0.2,
                        success_bonus=0.25, fail_penalty=0.25, timeout_penalty=1.0,
                        cost_weight=getattr(args, 'quotient_coordinate_accept_cost_weight', 0.05),
                    ))
    # v23: action-geometry retrieval loop.  This is a finite chart-level
    # action manifold search driven by qgen/coker normals; retrieved actions
    # remain witnesses until micro-audited and accepted.
    action_geometry_dir = None
    action_geometry_registry_path = None
    action_geometry_candidates_path = None
    action_geometry_audit_dir = None
    action_geometry_accepted_actions_path = None
    action_geometry_acceptance_report_path = None
    action_geometry_robust_accepted_actions_path = None
    action_geometry_robust_acceptance_report_path = None
    if getattr(args, 'action_geometry', False):
        action_geometry_dir = out / 'action_geometry'
        ag_transitions_path = out / 'transitions.jsonl'
        try:
            cmd_make_transitions(argparse.Namespace(responses=str(audit_dir/'responses.jsonl'), out=str(ag_transitions_path)))
        except Exception:
            ag_transitions_path = None
        qrep = qgen_dir / 'qgen_report.json' if qgen_dir and (qgen_dir / 'qgen_report.json').exists() else None
        if getattr(args, 'action_geometry_use_quotient_normals', False) and quotient_coordinate_normal_path and Path(quotient_coordinate_normal_path).exists():
            qrep = quotient_coordinate_normal_path
        action_geometry_gamma_transition_patches_for_retrieval = None
        if getattr(args, 'action_geometry_use_gamma_transition', False) and ag_transitions_path and Path(ag_transitions_path).exists():
            ag_gamma_dir = action_geometry_dir / 'gamma_transition_for_retrieval'
            ag_teacher_constraints = None
            if arithmetic_teacher_dir and (arithmetic_teacher_dir / 'cocycle_audit' / 'arithmetic_teacher_gamma_constraints.jsonl').exists():
                ag_teacher_constraints = arithmetic_teacher_dir / 'cocycle_audit' / 'arithmetic_teacher_gamma_constraints.jsonl'
            try:
                learn_gamma_transition_model(
                    ag_transitions_path,
                    ag_gamma_dir,
                    actions_path=args.actions,
                    teacher_constraints_path=ag_teacher_constraints,
                    ridge=getattr(args, 'gamma_transition_ridge', 1e-3),
                    shrink=getattr(args, 'gamma_transition_shrink', 4.0),
                    min_count=getattr(args, 'gamma_transition_min_count', 2),
                    holdout_fraction=getattr(args, 'gamma_transition_holdout_fraction', 0.25),
                    teacher_weight=getattr(args, 'gamma_transition_teacher_weight', 0.25),
                    include_matrices=getattr(args, 'gamma_transition_include_matrices', False),
                )
                action_geometry_gamma_transition_patches_for_retrieval = ag_gamma_dir / 'gamma_transition_action_geometry_patches.jsonl'
            except Exception:
                action_geometry_gamma_transition_patches_for_retrieval = None
        run_action_geometry_from_qgen(
            responses=audit_dir/'responses.jsonl',
            actions=args.actions,
            qgen_report=qrep if (getattr(args, 'action_geometry_use_qgen_normals', False) or getattr(args, 'action_geometry_use_quotient_normals', False)) else None,
            out_dir=action_geometry_dir,
            quotient_coordinates=(quotient_coordinate_dir / 'quotient_coordinates.jsonl') if (getattr(args, 'action_geometry_use_quotient_normals', False) and quotient_coordinate_dir and (quotient_coordinate_dir / 'quotient_coordinates.jsonl').exists()) else None,
            transitions=ag_transitions_path if ag_transitions_path and Path(ag_transitions_path).exists() else None,
            top_k=getattr(args, 'action_geometry_top_k', None),
            tail_weight=getattr(args, 'action_geometry_tail_weight', 0.25),
            cost_weight=getattr(args, 'action_geometry_cost_weight', 0.05),
            uncertainty_weight=getattr(args, 'action_geometry_uncertainty_weight', 0.10),
            audit_weight=getattr(args, 'action_geometry_audit_weight', 0.20),
            require_carrier_safe=getattr(args, 'action_geometry_require_carrier_safe', False),
            carrier_budget=getattr(args, 'action_geometry_carrier_budget', 0.0),
            min_count=getattr(args, 'action_geometry_min_count', 1),
            gamma_transition_patches=locals().get('action_geometry_gamma_transition_patches_for_retrieval'),
            gamma_aware=bool(getattr(args, 'action_geometry_use_gamma_transition', False) or str(getattr(args, 'action_geometry_gamma_value_mode', 'local')).lower() not in {'local', 'none', 'off'}),
            gamma_mode=getattr(args, 'action_geometry_gamma_value_mode', 'finite_horizon'),
            gamma_horizon=getattr(args, 'action_geometry_gamma_horizon', 4),
            gamma_discount=getattr(args, 'action_geometry_gamma_discount', 1.0),
            gamma_value_weight=getattr(args, 'action_geometry_gamma_tail_value_weight', 1.0),
            gamma_stability_delta=getattr(args, 'action_geometry_gamma_stability_margin', 0.05),
            gamma_tail_risk_mode=getattr(args, 'action_geometry_gamma_tail_risk_mode', 'spectral'),
        )
        action_geometry_registry_path = action_geometry_dir / 'action_geometry.jsonl'
        action_geometry_candidates_path = action_geometry_dir / 'action_geometry_candidates.jsonl'
        if getattr(args, 'audit_action_geometry_candidates', False) and action_geometry_candidates_path.exists():
            action_geometry_audit_dir = out / 'action_geometry_audit'
            _pipeline_audit(tasks_for_pipeline, str(action_geometry_candidates_path), action_geometry_audit_dir, getattr(args, 'action_geometry_audit_max_actions', 16), state_candidates=False, candidate_mode='state')
            cmd_action_report(argparse.Namespace(responses=str(action_geometry_audit_dir/'responses.jsonl'), out=str(out/'action_geometry_action_report.json'), csv_out=str(out/'action_geometry_action_report.csv'), group_keys=None))
            if getattr(args, 'action_geometry_accept_coker', False):
                if getattr(args, 'action_geometry_robust_coker_accept', False):
                    action_geometry_robust_accepted_actions_path = out / 'action_geometry_robust_accepted_actions.jsonl'
                    action_geometry_robust_acceptance_report_path = out / 'action_geometry_robust_acceptance_report.json'
                    cmd_robust_coker_accept(argparse.Namespace(
                        base_responses=str(audit_dir/'responses.jsonl'),
                        candidate_responses=str(action_geometry_audit_dir/'responses.jsonl'),
                        out_report=str(action_geometry_robust_acceptance_report_path),
                        out_actions=str(action_geometry_robust_accepted_actions_path),
                        out_rows=str(out/'action_geometry_robust_acceptance_rows.jsonl'),
                        csv_out=str(out/'action_geometry_robust_acceptance_rows.csv'),
                        margin_threshold=getattr(args, 'action_geometry_accept_margin', 0.0),
                        holdout_fraction=getattr(args, 'action_geometry_robust_coker_holdout_fraction', 0.35),
                        ridge=1e-4,
                        max_mass=1.0,
                        cost_weight=getattr(args, 'action_geometry_accept_cost_weight', 0.05),
                        carrier_gain_weight=getattr(args, 'action_geometry_robust_coker_carrier_gain_weight', 0.25),
                        carrier_violation_weight=getattr(args, 'action_geometry_accept_carrier_weight', 0.7),
                        audit_penalty=getattr(args, 'action_geometry_robust_coker_audit_penalty', 1.0),
                        uncertainty_weight=getattr(args, 'action_geometry_robust_coker_uncertainty_weight', 0.10),
                        require_success=getattr(args, 'action_geometry_robust_coker_require_success', False),
                        max_actions=getattr(args, 'action_geometry_accept_max_per_task', 16),
                    ))
                else:
                    action_geometry_accepted_actions_path = out / 'action_geometry_accepted_actions.jsonl'
                    action_geometry_acceptance_report_path = out / 'action_geometry_acceptance_report.json'
                    cmd_registry_accept(argparse.Namespace(
                        base_responses=str(audit_dir/'responses.jsonl'),
                        registry_responses=str(action_geometry_audit_dir/'responses.jsonl'),
                        accepted_actions_out=str(action_geometry_accepted_actions_path),
                        report_out=str(action_geometry_acceptance_report_path),
                        audit_out=str(out/'action_geometry_acceptance_rows.jsonl'),
                        margin_threshold=getattr(args, 'action_geometry_accept_margin', 0.0),
                        max_per_task=getattr(args, 'action_geometry_accept_max_per_task', 16),
                        goal_weight=1.0, type_weight=0.6, search_weight=0.4,
                        carrier_weight=getattr(args, 'action_geometry_accept_carrier_weight', 0.7), audit_weight=0.2,
                        success_bonus=0.25, fail_penalty=0.25, timeout_penalty=1.0,
                        cost_weight=getattr(args, 'action_geometry_accept_cost_weight', 0.05),
                    ))

    qgen_audit_dir = None
    qgen_audited_accepted_actions_path = None
    qgen_acceptance_report_path = None
    qgen_robust_accepted_actions_path = None
    qgen_robust_acceptance_report_path = None
    qgen_robust_acceptance_rows_path = None
    if getattr(args, 'qgen', False) and getattr(args, 'audit_qgen_candidates', False) and qgen_context_candidates_path and qgen_context_candidates_path.exists():
        qgen_audit_dir = out / 'qgen_audit'
        _pipeline_audit(tasks_for_pipeline, str(qgen_context_candidates_path), qgen_audit_dir, args.qgen_audit_max_actions, state_candidates=False, candidate_mode='state')
        cmd_action_report(argparse.Namespace(responses=str(qgen_audit_dir/'responses.jsonl'), out=str(out/'qgen_action_report.json'), csv_out=str(out/'qgen_action_report.csv'), group_keys=None))
        if getattr(args, 'qgen_accept_coker', False):
            qgen_audited_accepted_actions_path = out / 'qgen_accepted_actions.jsonl'
            qgen_acceptance_report_path = out / 'qgen_acceptance_report.json'
            if getattr(args, 'qgen_robust_coker_accept', False):
                qgen_robust_accepted_actions_path = out / 'qgen_robust_accepted_actions.jsonl'
                qgen_robust_acceptance_report_path = out / 'qgen_robust_acceptance_report.json'
                qgen_robust_acceptance_rows_path = out / 'qgen_robust_acceptance_rows.jsonl'
                cmd_robust_coker_accept(argparse.Namespace(
                    base_responses=str(audit_dir/'responses.jsonl'),
                    candidate_responses=str(qgen_audit_dir/'responses.jsonl'),
                    out_report=str(qgen_robust_acceptance_report_path),
                    out_actions=str(qgen_robust_accepted_actions_path),
                    out_rows=str(qgen_robust_acceptance_rows_path),
                    csv_out=str(out/'qgen_robust_acceptance_rows.csv'),
                    margin_threshold=args.qgen_accept_margin,
                    holdout_fraction=args.qgen_robust_coker_holdout_fraction,
                    ridge=1e-4,
                    max_mass=1.0,
                    cost_weight=args.qgen_accept_cost_weight,
                    carrier_gain_weight=args.qgen_robust_coker_carrier_gain_weight,
                    carrier_violation_weight=args.qgen_accept_carrier_weight,
                    audit_penalty=args.qgen_robust_coker_audit_penalty,
                    uncertainty_weight=args.qgen_robust_coker_uncertainty_weight,
                    require_success=args.qgen_robust_coker_require_success,
                    max_actions=args.qgen_accept_max_per_task,
                ))
                # Keep the legacy accepted-actions path populated for downstream tools while
                # preserving the robust-specific artifact name for provenance.
                if qgen_robust_accepted_actions_path.exists():
                    qgen_audited_accepted_actions_path.write_text(qgen_robust_accepted_actions_path.read_text(encoding='utf-8'), encoding='utf-8')
                if qgen_robust_acceptance_report_path.exists():
                    qgen_acceptance_report_path.write_text(qgen_robust_acceptance_report_path.read_text(encoding='utf-8'), encoding='utf-8')
            elif getattr(args, 'qgen_robust_accept', False):
                cmd_robust_accept(argparse.Namespace(
                    base_responses=str(audit_dir/'responses.jsonl'),
                    candidate_responses=str(qgen_audit_dir/'responses.jsonl'),
                    out=str(out/'qgen_robust_acceptance_rows.jsonl'),
                    report_out=str(qgen_acceptance_report_path),
                    accepted_actions_out=str(qgen_audited_accepted_actions_path),
                    per_row_out=str(out/'qgen_acceptance_rows.jsonl'),
                    margin_threshold=args.qgen_accept_margin,
                    max_per_task=args.qgen_accept_max_per_task,
                    goal_weight=1.0,
                    carrier_weight=args.qgen_accept_carrier_weight,
                    cost_weight=args.qgen_accept_cost_weight,
                    max_mass=1.0,
                    ridge=1e-4,
                    robust_z=args.qgen_robust_z,
                    robust_min_repeats=args.qgen_robust_min_repeats,
                    robust_min_success_rate=args.qgen_robust_min_success_rate,
                ))
            else:
                cmd_registry_accept(argparse.Namespace(
                    base_responses=str(audit_dir/'responses.jsonl'),
                    registry_responses=str(qgen_audit_dir/'responses.jsonl'),
                    accepted_actions_out=str(qgen_audited_accepted_actions_path),
                    report_out=str(qgen_acceptance_report_path),
                    audit_out=str(out/'qgen_acceptance_rows.jsonl'),
                    margin_threshold=args.qgen_accept_margin,
                    max_per_task=args.qgen_accept_max_per_task,
                    goal_weight=1.0, type_weight=0.6, search_weight=0.4,
                    carrier_weight=args.qgen_accept_carrier_weight, audit_weight=0.2,
                    success_bonus=0.25, fail_penalty=0.25, timeout_penalty=1.0,
                    cost_weight=args.qgen_accept_cost_weight,
                ))
    if getattr(args, 'qgen', False) and getattr(args, 'audit_qgen_registry_candidates', False) and qgen_registry_candidates_path and qgen_registry_candidates_path.exists():
        qgen_registry_audit_dir = out / 'qgen_registry_audit'
        _pipeline_audit(tasks_for_pipeline, str(qgen_registry_candidates_path), qgen_registry_audit_dir, args.qgen_registry_audit_max_actions, state_candidates=False, candidate_mode='state')
        cmd_action_report(argparse.Namespace(responses=str(qgen_registry_audit_dir/'responses.jsonl'), out=str(out/'qgen_registry_action_report.json'), csv_out=str(out/'qgen_registry_action_report.csv'), group_keys=None))
        if getattr(args, 'qgen_registry_accept_coker', False):
            qgen_registry_accepted_path = out / 'qgen_registry_accepted_actions.jsonl'
            if getattr(args, 'qgen_registry_robust_coker_accept', False):
                qgen_registry_robust_accepted_path = out / 'qgen_registry_robust_accepted_actions.jsonl'
                cmd_robust_coker_accept(argparse.Namespace(
                    base_responses=str(audit_dir/'responses.jsonl'),
                    candidate_responses=str(qgen_registry_audit_dir/'responses.jsonl'),
                    out_report=str(out/'qgen_registry_robust_acceptance_report.json'),
                    out_actions=str(qgen_registry_robust_accepted_path),
                    out_rows=str(out/'qgen_registry_robust_acceptance_rows.jsonl'),
                    csv_out=str(out/'qgen_registry_robust_acceptance_rows.csv'),
                    margin_threshold=args.qgen_registry_accept_margin,
                    holdout_fraction=args.qgen_robust_coker_holdout_fraction,
                    ridge=1e-4,
                    max_mass=1.0,
                    cost_weight=args.qgen_registry_accept_cost_weight,
                    carrier_gain_weight=args.qgen_robust_coker_carrier_gain_weight,
                    carrier_violation_weight=args.qgen_registry_accept_carrier_weight,
                    audit_penalty=args.qgen_robust_coker_audit_penalty,
                    uncertainty_weight=args.qgen_robust_coker_uncertainty_weight,
                    require_success=args.qgen_robust_coker_require_success,
                    max_actions=args.qgen_registry_accept_max_per_task,
                ))
                if qgen_registry_robust_accepted_path.exists():
                    qgen_registry_accepted_path.write_text(qgen_registry_robust_accepted_path.read_text(encoding='utf-8'), encoding='utf-8')
            elif getattr(args, 'qgen_registry_robust_accept', False):
                cmd_robust_accept(argparse.Namespace(
                    base_responses=str(audit_dir/'responses.jsonl'),
                    candidate_responses=str(qgen_registry_audit_dir/'responses.jsonl'),
                    out=str(out/'qgen_registry_robust_acceptance_rows.jsonl'),
                    report_out=str(out/'qgen_registry_acceptance_report.json'),
                    accepted_actions_out=str(qgen_registry_accepted_path),
                    per_row_out=str(out/'qgen_registry_acceptance_rows.jsonl'),
                    margin_threshold=args.qgen_registry_accept_margin,
                    max_per_task=args.qgen_registry_accept_max_per_task,
                    goal_weight=1.0,
                    carrier_weight=args.qgen_registry_accept_carrier_weight,
                    cost_weight=args.qgen_registry_accept_cost_weight,
                    max_mass=1.0,
                    ridge=1e-4,
                    robust_z=args.qgen_robust_z,
                    robust_min_repeats=args.qgen_robust_min_repeats,
                    robust_min_success_rate=args.qgen_robust_min_success_rate,
                ))
            else:
                cmd_registry_accept(argparse.Namespace(
                    base_responses=str(audit_dir/'responses.jsonl'),
                    registry_responses=str(qgen_registry_audit_dir/'responses.jsonl'),
                    accepted_actions_out=str(qgen_registry_accepted_path),
                    report_out=str(out/'qgen_registry_acceptance_report.json'),
                    audit_out=str(out/'qgen_registry_acceptance_rows.jsonl'),
                    margin_threshold=args.qgen_registry_accept_margin,
                    max_per_task=args.qgen_registry_accept_max_per_task,
                    goal_weight=1.0, type_weight=0.6, search_weight=0.4,
                    carrier_weight=args.qgen_registry_accept_carrier_weight, audit_weight=0.2,
                    success_bonus=0.25, fail_penalty=0.25, timeout_penalty=1.0,
                    cost_weight=args.qgen_registry_accept_cost_weight,
                ))
    failure_signatures_path=None; failure_signature_actions_path=None; failure_signature_audit_dir=None
    if getattr(args, 'failure_signatures', False):
        failure_signatures_path = out/'failure_signatures.jsonl'
        failure_signature_actions_path = out/'failure_signature_actions.jsonl'
        cmd_failure_signatures(argparse.Namespace(audits=str(audit_dir/'micro_audit.jsonl'), responses=str(audit_dir/'responses.jsonl'), out=str(failure_signatures_path), actions_out=str(failure_signature_actions_path), summary_out=str(out/'failure_signatures.summary.json'), min_support=args.failure_signature_min_support))
        if getattr(args, 'audit_failure_signature_candidates', False):
            failure_signature_audit_dir = out/'failure_signature_audit'
            _pipeline_audit(tasks_for_pipeline, str(failure_signature_actions_path), failure_signature_audit_dir, args.failure_signature_audit_max_actions, state_candidates=False, candidate_mode='state')
            cmd_action_report(argparse.Namespace(responses=str(failure_signature_audit_dir/'responses.jsonl'), out=str(out/'failure_signature_action_report.json'), csv_out=str(out/'failure_signature_action_report.csv'), group_keys=None))
            if getattr(args, 'failure_signature_accept_coker', False):
                cmd_registry_accept(argparse.Namespace(base_responses=str(audit_dir/'responses.jsonl'), registry_responses=str(failure_signature_audit_dir/'responses.jsonl'), accepted_actions_out=str(out/'failure_signature_accepted_actions.jsonl'), report_out=str(out/'failure_signature_acceptance_report.json'), audit_out=str(out/'failure_signature_acceptance_rows.jsonl'), margin_threshold=args.failure_signature_accept_margin, max_per_task=args.failure_signature_accept_max_per_task, goal_weight=1.0, type_weight=0.6, search_weight=0.4, carrier_weight=args.failure_signature_accept_carrier_weight, audit_weight=0.2, success_bonus=0.25, fail_penalty=0.25, timeout_penalty=1.0, cost_weight=args.failure_signature_accept_cost_weight))
    cmd_train_response(argparse.Namespace(responses=str(audit_dir/'responses.jsonl'),actions=args.actions,out=str(out/'response_model.json'),lcb_kappa=1.0,min_count_for_action=2,shrink=2.0))
    if getattr(args, 'eval_response_model', False):
        cmd_eval_response(argparse.Namespace(model=str(out/'response_model.json'), responses=str(audit_dir/'responses.jsonl'), out=str(out/'response_eval_summary.json'), out_rows=str(out/'response_eval_rows.jsonl'), csv_out=str(out/'response_eval_rows.csv'), mode=args.response_eval_mode))
    cmd_quotient(argparse.Namespace(responses=str(audit_dir/'responses.jsonl'),out=str(out/'response_components.jsonl'),tolerance=args.quotient_tolerance))
    states_ir_path=out/'states_ir.jsonl'; exposure_report_path=out/'exposure_report.json'
    cmd_parse_states(argparse.Namespace(audits=str(audit_dir/'micro_audit.jsonl'),out=str(states_ir_path)))
    cmd_ir_defects(argparse.Namespace(ir=str(states_ir_path), out=str(out/'ir_defects.jsonl')))
    cmd_exposure_report(argparse.Namespace(responses=str(audit_dir/'responses.jsonl'),out=str(exposure_report_path)))
    ir_candidates_path = None
    ir_audit_dir = None
    ir_acceptance_path = None
    if getattr(args, 'ir_candidates', False):
        ir_candidates_path = out/'ir_candidates.jsonl'
        cmd_ir_candidates(argparse.Namespace(ir=str(states_ir_path), out=str(ir_candidates_path), max_candidates=args.ir_max_candidates))
        if getattr(args, 'audit_ir_candidates', False):
            ir_audit_dir = out/'ir_audit'
            _pipeline_audit(tasks_for_pipeline, str(ir_candidates_path), ir_audit_dir, args.ir_audit_max_actions, state_candidates=False, candidate_mode='state')
            cmd_action_report(argparse.Namespace(responses=str(ir_audit_dir/'responses.jsonl'), out=str(out/'ir_action_report.json'), csv_out=str(out/'ir_action_report.csv'), group_keys=None))
            if getattr(args, 'ir_accept_coker', False):
                ir_acceptance_path = out/'ir_acceptance_rows.jsonl'
                cmd_accept_candidates(argparse.Namespace(base_responses=str(audit_dir/'responses.jsonl'), candidate_responses=str(ir_audit_dir/'responses.jsonl'), out=str(ir_acceptance_path), summary_out=str(out/'ir_acceptance_report.json'), margin_threshold=args.ir_accept_margin, cost_weight=args.ir_accept_cost_weight, carrier_weight=args.ir_accept_carrier_weight, audit_penalty=1.0, require_success=False))
        if getattr(args, 'audit_ir_candidates', False):
            ir_audit_dir = out/'ir_audit'
            _pipeline_audit(tasks_for_pipeline, str(ir_candidates_path), ir_audit_dir, args.ir_audit_max_actions, state_candidates=False, candidate_mode='state')
            cmd_action_report(argparse.Namespace(responses=str(ir_audit_dir/'responses.jsonl'), out=str(out/'ir_action_report.json'), csv_out=str(out/'ir_action_report.csv'), group_keys=None))
            if getattr(args, 'ir_accept_coker', False):
                cmd_registry_accept(argparse.Namespace(base_responses=str(audit_dir/'responses.jsonl'), registry_responses=str(ir_audit_dir/'responses.jsonl'), accepted_actions_out=str(out/'ir_accepted_actions.jsonl'), report_out=str(out/'ir_acceptance_report.json'), audit_out=str(out/'ir_acceptance_rows.jsonl'), margin_threshold=args.ir_accept_margin, max_per_task=args.ir_accept_max_per_task, goal_weight=1.0, type_weight=0.6, search_weight=0.4, carrier_weight=args.ir_accept_carrier_weight, audit_weight=0.2, success_bonus=0.25, fail_penalty=0.25, timeout_penalty=1.0, cost_weight=args.ir_accept_cost_weight))
    registry_path=None
    promoted_registry_path=None
    if args.mine_defects:
        registry_path=out/'defect_registry.json'
        cmd_mine_defects(argparse.Namespace(audits=str(audit_dir/'micro_audit.jsonl'),responses=str(audit_dir/'responses.jsonl'),out=str(registry_path),scores_out=str(out/'defect_registry.scores.jsonl'),min_support=args.mine_min_support,min_response_contrast=args.mine_min_response_contrast,min_stability=args.mine_min_stability,min_intervention_success=args.mine_min_intervention_success,min_coker_reduction=args.mine_min_coker_reduction))
        cmd_auto_defects(argparse.Namespace(registry=str(registry_path),tasks=tasks_for_pipeline,states=None,out=str(out/'auto_defects.jsonl'),import_mode=args.import_mode))
    # Carrier proposals from the base audit defects.
    cmd_carrier_generate(argparse.Namespace(defects=str(audit_dir/'defects.jsonl'),out=str(out/'carrier_generated_contexts.jsonl'),threshold=args.carrier_threshold))
    actions_for_coker=args.actions
    registry_candidates_path=None
    if registry_path is not None and args.registry_candidates:
        registry_candidates_path=out/'registry_candidates.jsonl'
        cmd_registry_candidates(argparse.Namespace(tasks=tasks_for_pipeline,registry=str(registry_path),out=str(registry_candidates_path),max_candidates=args.registry_max_candidates,registry_only=False,import_mode=args.import_mode))
        actions_for_coker=str(registry_candidates_path)
        if args.audit_registry_candidates:
            registry_audit_dir = out/'registry_audit'
            _pipeline_audit(tasks_for_pipeline, str(registry_candidates_path), registry_audit_dir, args.registry_audit_max_actions, state_candidates=False, candidate_mode='state')
            cmd_action_report(argparse.Namespace(responses=str(registry_audit_dir/'responses.jsonl'), out=str(out/'registry_action_report.json'), csv_out=str(out/'registry_action_report.csv'), group_keys=None))
            if args.registry_accept_coker:
                cmd_registry_accept(argparse.Namespace(base_responses=str(audit_dir/'responses.jsonl'), registry_responses=str(registry_audit_dir/'responses.jsonl'), accepted_actions_out=str(out/'registry_accepted_actions.jsonl'), report_out=str(out/'registry_acceptance_report.json'), audit_out=str(out/'registry_acceptance_rows.jsonl'), margin_threshold=args.registry_accept_margin, max_per_task=args.registry_accept_max_per_task, goal_weight=1.0, type_weight=0.6, search_weight=0.4, carrier_weight=args.registry_accept_carrier_weight, audit_weight=0.2, success_bonus=0.25, fail_penalty=0.25, timeout_penalty=1.0, cost_weight=args.registry_accept_cost_weight))
        if args.promote_registry:
            promoted_registry_path=out/'defect_registry.promoted.json'
            cmd_promote_registry(argparse.Namespace(registry=str(registry_path),audits=str(out/'registry_audit') if args.audit_registry_candidates else str(audit_dir/'micro_audit.jsonl'),responses=str(out/'registry_audit'/'responses.jsonl') if args.audit_registry_candidates and (out/'registry_audit'/'responses.jsonl').exists() else str(audit_dir/'responses.jsonl'),out=str(promoted_registry_path),report_out=str(out/'defect_registry.promotion_report.json'),min_support=args.promote_min_support,min_intervention_success=args.promote_min_intervention_success,min_coker_reduction=args.promote_min_coker_reduction,min_promotion_score=args.promote_min_promotion_score,drop_rejected=args.promote_drop_rejected))
    # Premise retrieval chart.
    premise_index_path=None; premise_candidates_path=None; premise_audit_dir=None
    if args.premise_index:
        premise_index_path=out/'premise_index.json'
        cmd_build_premise_index(argparse.Namespace(tasks=tasks_for_pipeline, actions=actions_for_coker, out=str(premise_index_path)))
        hits_path=out/'premise_hits.jsonl'
        cmd_premise_retrieve(argparse.Namespace(index=str(premise_index_path),out=str(hits_path),query=None,tasks=tasks_for_pipeline,states=None,k=args.premise_top_k,kind=None,import_mode=args.import_mode))
        premise_candidates_path=out/'premise_actions.jsonl'
        cmd_premise_actions(argparse.Namespace(hits=str(hits_path),out=str(premise_candidates_path),task_id=None,max_actions_per_query=args.premise_max_actions))
        if args.audit_premise_candidates:
            premise_audit_dir=out/'premise_audit'
            _pipeline_audit(tasks_for_pipeline, str(premise_candidates_path), premise_audit_dir, args.premise_audit_max_actions, state_candidates=False, candidate_mode='state')
            cmd_action_report(argparse.Namespace(responses=str(premise_audit_dir/'responses.jsonl'), out=str(out/'premise_action_report.json'), csv_out=str(out/'premise_action_report.csv'), group_keys=None))
            # v35: Premise Response Registry / Retrieval.  This treats
            # premise-use contexts as response/carrier embeddings rather than
            # theorem-name or lexical-similarity primitives.
            if getattr(args, 'premise_response_registry', False):
                premise_response_dir = out/'premise_response'
                premise_response_dir.mkdir(parents=True, exist_ok=True)
                cmd_premise_response_registry(argparse.Namespace(
                    responses=str(premise_audit_dir/'responses.jsonl'),
                    actions=str(premise_candidates_path),
                    out=str(premise_response_dir/'premise_response_registry.jsonl'),
                    summary_out=str(premise_response_dir/'premise_response_registry_summary.json'),
                    min_count=1,
                ))
                if getattr(args, 'premise_quotient_mine', False):
                    cmd_premise_quotient_mine(argparse.Namespace(
                        registry=str(premise_response_dir/'premise_response_registry.jsonl'),
                        out=str(premise_response_dir/'premise_quotient'),
                        cosine_threshold=0.95,
                        distance_threshold=0.25,
                        no_carrier=False,
                    ))
                if getattr(args, 'premise_response_retrieve', False):
                    # Prefer mined quotient-coordinate normals when available; otherwise
                    # fall back to an empty normal, yielding a conservative audit-prior sort.
                    normal_path = out/'quotient_coordinates'/'quotient_coordinate_response_normal.json'
                    rn = str(normal_path) if normal_path.exists() else None
                    retrieved_path = premise_response_dir/'premise_response_retrieved.jsonl'
                    retrieved_actions = out/'premise_response_actions.jsonl'
                    cmd_premise_response_retrieve(argparse.Namespace(
                        registry=str(premise_response_dir/'premise_response_registry.jsonl'),
                        out=str(retrieved_path),
                        summary_out=str(premise_response_dir/'premise_response_retrieval_summary.json'),
                        out_actions=str(retrieved_actions),
                        response_normal=rn, response_normal_json=None,
                        carrier_normal=None, carrier_normal_json=None,
                        top_k=getattr(args, 'premise_response_top_k', 32),
                        cost_weight=0.05, uncertainty_weight=0.10, audit_weight=0.20,
                        carrier_safe=False, carrier_budget=0.0,
                    ))
                    if getattr(args, 'audit_premise_response_candidates', False) and retrieved_actions.exists():
                        premise_resp_audit_dir = out/'premise_response_audit'
                        _pipeline_audit(tasks_for_pipeline, str(retrieved_actions), premise_resp_audit_dir, getattr(args, 'premise_response_audit_max_actions', 16), state_candidates=False, candidate_mode='state')
                        cmd_action_report(argparse.Namespace(responses=str(premise_resp_audit_dir/'responses.jsonl'), out=str(out/'premise_response_action_report.json'), csv_out=str(out/'premise_response_action_report.csv'), group_keys=None))
    # v50: premise contextual quotient.  This wraps premise-use actions in
    # finite safe pre/post contexts and fingerprints the incremental response
    # probe_response - baseline_context_response.
    premise_contextual_dir = None
    premise_contextual_candidates_path = None
    premise_contextual_audit_dir = None
    premise_contextual_fingerprints_path = None
    premise_contextual_classes_path = None
    premise_quotient_retrieved_path = None
    premise_quotient_actions_path = None
    premise_use_rows_path = None
    separator_contexts_path = None
    premise_contextual_scheduled_path = None
    repair_face_ledger_path = None
    premise_contextual_requested = any(getattr(args, k, False) for k in [
        'premise_contextual_quotient',
        'premise_contextual_generate',
        'premise_contextual_bivariate',
        'audit_premise_contextual_candidates',
        'premise_contextual_mine',
        'premise_contextual_validate',
        'premise_quotient_retrieve',
        'repair_face_ledger',
    ])
    if premise_contextual_requested:
        premise_contextual_dir = out / 'premise_contextual'
        premise_contextual_dir.mkdir(parents=True, exist_ok=True)
        source_actions = None
        for candidate_source in [
            locals().get('retrieved_actions'),
            locals().get('premise_candidates_path'),
            args.actions,
        ]:
            if candidate_source and Path(candidate_source).exists():
                source_actions = candidate_source
                break
        if not source_actions:
            (premise_contextual_dir / 'premise_contextual_report.json').write_text(json.dumps({
                'schema_version': 'lean-rgc-premise-contextual-pipeline-v50.0',
                'status': 'skipped_no_premise_actions',
                'canonical_status': 'premise_contextual_pipeline_chart_not_canonical',
            }, indent=2, ensure_ascii=False), encoding='utf-8')
        else:
            premise_contextual_candidates_path = premise_contextual_dir / 'premise_contextual_candidates.jsonl'
            if getattr(args, 'premise_contextual_bivariate', False):
                premise_use_rows_path = Path(getattr(args, 'premise_use_rows_out', None) or premise_contextual_dir / 'premise_use_rows.jsonl')
                separator_contexts_path = Path(getattr(args, 'separator_contexts_out', None) or getattr(args, 'premise_contextual_contexts', None) or premise_contextual_dir / 'separator_contexts.jsonl')
                build_premise_use_rows(
                    source_actions,
                    premise_use_rows_path,
                    summary_out=premise_contextual_dir / 'premise_use_row_report.json',
                    max_rows=getattr(args, 'premise_contextual_max_premises', None),
                )
                if not Path(separator_contexts_path).exists():
                    write_separator_contexts(
                        separator_contexts_path,
                        templates=getattr(args, 'separator_contexts_builtin', 'builtin_core'),
                        summary_out=premise_contextual_dir / 'separator_context_report.json',
                    )
                generate_bivariate_contextual_candidates(
                    premise_use_rows_path,
                    separator_contexts_path,
                    premise_contextual_candidates_path,
                    summary_out=premise_contextual_dir / 'bivariate_contextual_candidate_report.json',
                    max_rows=getattr(args, 'premise_contextual_max_premises', None),
                    max_pre=getattr(args, 'premise_contextual_max_left', 4),
                    max_post=getattr(args, 'premise_contextual_max_right', 4),
                    max_candidates=getattr(args, 'premise_contextual_max_candidates', None),
                    include_baselines=True,
                )
                premise_contextual_scheduled_path = premise_contextual_dir / 'bivariate_contextual_scheduled_actions.jsonl'
                schedule_bivariate_candidates(
                    premise_contextual_candidates_path,
                    premise_contextual_scheduled_path,
                    budget=getattr(args, 'bivariate_audit_budget', None) or getattr(args, 'premise_contextual_audit_max_actions', 32),
                    report_out=premise_contextual_dir / 'bivariate_contextual_schedule_report.json',
                    require_baseline_pairs=getattr(args, 'bivariate_require_baseline_pairs', False) or getattr(args, 'premise_contextual_baseline_required', False),
                )
            else:
                generate_premise_contextual_candidates(
                    source_actions,
                    premise_contextual_candidates_path,
                    contexts_path=getattr(args, 'premise_contextual_contexts', None),
                    max_premises=getattr(args, 'premise_contextual_max_premises', None),
                    max_left=getattr(args, 'premise_contextual_max_left', 4),
                    max_right=getattr(args, 'premise_contextual_max_right', 4),
                    max_candidates=getattr(args, 'premise_contextual_max_candidates', None),
                    include_identity=True,
                    include_baselines=True,
                )
            if getattr(args, 'audit_premise_contextual_candidates', False) or getattr(args, 'premise_contextual_quotient', False) or getattr(args, 'premise_contextual_mine', False) or getattr(args, 'premise_contextual_validate', False) or getattr(args, 'premise_quotient_retrieve', False):
                premise_contextual_audit_dir = out / 'premise_contextual_audit'
                audit_actions_path = premise_contextual_scheduled_path if premise_contextual_scheduled_path is not None else premise_contextual_candidates_path
                audit_budget = getattr(args, 'bivariate_audit_budget', None) or getattr(args, 'premise_contextual_audit_max_actions', 32)
                _pipeline_audit(tasks_for_pipeline, str(audit_actions_path), premise_contextual_audit_dir, audit_budget, state_candidates=False, candidate_mode='state')
                cmd_action_report(argparse.Namespace(responses=str(premise_contextual_audit_dir/'responses.jsonl'), out=str(out/'premise_contextual_action_report.json'), csv_out=str(out/'premise_contextual_action_report.csv'), group_keys=None))
                premise_contextual_fingerprints_path = premise_contextual_dir / 'premise_contextual_fingerprints.jsonl'
                build_premise_contextual_fingerprints(
                    responses_path=premise_contextual_audit_dir/'responses.jsonl',
                    actions_path=audit_actions_path,
                    out=premise_contextual_fingerprints_path,
                    summary_out=premise_contextual_dir/'premise_contextual_fingerprint_report.json',
                    min_contexts=1,
                    baseline_required=getattr(args, 'premise_contextual_baseline_required', False),
                )
                if getattr(args, 'premise_contextual_quotient', False) or getattr(args, 'premise_contextual_mine', False) or getattr(args, 'premise_contextual_validate', False) or getattr(args, 'premise_quotient_retrieve', False):
                    mine_premise_contextual_quotient(
                        fingerprints_path=premise_contextual_fingerprints_path,
                        out_dir=premise_contextual_dir,
                        epsilon=getattr(args, 'premise_contextual_epsilon', 0.25),
                        cosine_threshold=getattr(args, 'premise_contextual_cosine_threshold', 0.95),
                        domain_jaccard_threshold=getattr(args, 'premise_contextual_domain_jaccard_threshold', 0.0),
                    )
                    premise_contextual_classes_path = premise_contextual_dir / 'premise_quotient_classes.jsonl'
                if getattr(args, 'premise_contextual_quotient', False) or getattr(args, 'premise_contextual_validate', False):
                    if premise_contextual_classes_path and premise_contextual_classes_path.exists() and (not getattr(args, 'skip_vacuous_premise_quotient', False) or read_jsonl(premise_contextual_classes_path)):
                        validate_premise_contextual_quotient(
                            fingerprints_path=premise_contextual_fingerprints_path,
                            classes_path=premise_contextual_classes_path,
                            out_rows=premise_contextual_dir/'premise_quotient_validation_rows.jsonl',
                            out_report=premise_contextual_dir/'premise_quotient_validation_report.json',
                            epsilon_holdout=getattr(args, 'premise_contextual_epsilon_holdout', 0.35),
                            separation_delta=getattr(args, 'premise_contextual_separation_delta', 0.10),
                            domain_jaccard_min=getattr(args, 'premise_contextual_domain_jaccard_threshold', 0.0),
                        )
                if getattr(args, 'repair_face_ledger', False):
                    if premise_contextual_classes_path and premise_contextual_classes_path.exists() and read_jsonl(premise_contextual_classes_path):
                        repair_face_ledger_path = premise_contextual_dir / 'repair_faces.jsonl'
                        build_repair_face_ledger(
                            fingerprints_path=premise_contextual_fingerprints_path,
                            classes_path=premise_contextual_classes_path,
                            validation_rows_path=premise_contextual_dir/'premise_quotient_validation_rows.jsonl',
                            out=repair_face_ledger_path,
                            report_out=premise_contextual_dir/'repair_face_ledger_report.json',
                        )
                if getattr(args, 'premise_quotient_retrieve', False):
                    if premise_contextual_classes_path and premise_contextual_classes_path.exists() and (not getattr(args, 'skip_vacuous_premise_quotient', False) or read_jsonl(premise_contextual_classes_path)):
                        normal_path = out/'quotient_coordinates'/'quotient_coordinate_response_normal.json'
                        rn = str(normal_path) if normal_path.exists() else None
                        premise_quotient_retrieved_path = premise_contextual_dir / 'premise_quotient_retrieved_actions.jsonl'
                        premise_quotient_actions_path = out / 'premise_quotient_actions.jsonl'
                        retrieve_premise_quotient_classes(
                            classes_path=premise_contextual_classes_path,
                            out=premise_quotient_retrieved_path,
                            summary_out=premise_contextual_dir/'premise_quotient_retrieval_summary.json',
                            response_normal=_parse_json_or_file(rn),
                            carrier_normal={},
                            top_k=getattr(args, 'premise_quotient_top_k', 32),
                        )
                        premise_quotient_retrieved_actions(retrieved_path=premise_quotient_retrieved_path, out=premise_quotient_actions_path)
                        if getattr(args, 'audit_premise_quotient_candidates', False) and premise_quotient_actions_path.exists():
                            premise_quotient_audit_dir = out / 'premise_quotient_audit'
                            _pipeline_audit(tasks_for_pipeline, str(premise_quotient_actions_path), premise_quotient_audit_dir, getattr(args, 'premise_quotient_audit_max_actions', 16), state_candidates=False, candidate_mode='state')
                            cmd_action_report(argparse.Namespace(responses=str(premise_quotient_audit_dir/'responses.jsonl'), out=str(out/'premise_quotient_action_report.json'), csv_out=str(out/'premise_quotient_action_report.csv'), group_keys=None))
    # v37: source-budget scheduler across candidate families.  This is a
    # finite audit-budget allocation chart, not a canonical selector.
    source_budget_dir = None
    source_budget_actions_path = None
    source_budget_audit_dir = None
    source_budget_report_path = None
    if getattr(args, 'source_budget', False):
        source_budget_dir = out / 'source_budget'
        source_budget_dir.mkdir(parents=True, exist_ok=True)
        source_specs = []
        def _add_source_spec(name, path_obj):
            if path_obj and Path(path_obj).exists() and read_jsonl(path_obj):
                source_specs.append(f"{name}={Path(path_obj)}")
        _add_source_spec('qgen', locals().get('qgen_context_candidates_path'))
        _add_source_spec('qgen_registry', locals().get('qgen_registry_candidates_path'))
        _add_source_spec('action_geometry', locals().get('action_geometry_candidates_path'))
        _add_source_spec('quotient_coordinate', locals().get('quotient_coordinate_candidates_path'))
        _add_source_spec('quotient_coordinate_registry', locals().get('quotient_coordinate_registry_candidates_path'))
        _add_source_spec('carrier_quotient', locals().get('carrier_quotient_candidates_path'))
        _add_source_spec('contextual_probe', locals().get('contextual_probe_candidates_path'))
        _add_source_spec('registry', locals().get('registry_candidates_path'))
        _add_source_spec('failure_signature', locals().get('failure_signature_actions_path'))
        _add_source_spec('ir', locals().get('ir_candidates_path'))
        _add_source_spec('premise', locals().get('premise_candidates_path'))
        _add_source_spec('premise_response', locals().get('retrieved_actions'))
        _add_source_spec('premise_contextual', locals().get('premise_contextual_candidates_path'))
        _add_source_spec('premise_quotient', locals().get('premise_quotient_actions_path'))
        if source_specs:
            source_budget_actions_path = source_budget_dir / 'source_budget_actions.jsonl'
            source_budget_report_path = source_budget_dir / 'source_budget_report.json'
            source_budget_rows_path = source_budget_dir / 'source_budget_rows.jsonl'
            sb_cfg = SourceBudgetConfig(
                total_budget=getattr(args, 'source_budget_budget', None) or args.max_actions,
                min_per_source=getattr(args, 'source_budget_min_per_source', 0),
                max_per_source=getattr(args, 'source_budget_max_per_source', None),
                per_task_cap=getattr(args, 'source_budget_per_task_cap', None),
                per_action_cap=getattr(args, 'source_budget_per_action_cap', 1),
                coker_weight=getattr(args, 'source_budget_coker_weight', 1.0),
                carrier_weight=getattr(args, 'source_budget_carrier_weight', 0.5),
                uncertainty_weight=getattr(args, 'source_budget_uncertainty_weight', 0.25),
                novelty_weight=getattr(args, 'source_budget_novelty_weight', 0.15),
                success_weight=getattr(args, 'source_budget_success_weight', 0.25),
                cost_weight=getattr(args, 'source_budget_cost_weight', 0.10),
                timeout_weight=getattr(args, 'source_budget_timeout_weight', 0.50),
                gamma_aware=getattr(args, 'source_budget_gamma_aware', False),
                gamma_mode=getattr(args, 'source_budget_gamma_value_mode', 'finite_horizon'),
                gamma_horizon=getattr(args, 'source_budget_gamma_horizon', 4),
                gamma_discount=getattr(args, 'source_budget_gamma_discount', 1.0),
                gamma_value_weight=getattr(args, 'source_budget_gamma_value_weight', 0.50),
                gamma_tail_value_weight=getattr(args, 'source_budget_gamma_tail_value_weight', None),
                gamma_tail_risk_weight=getattr(args, 'source_budget_gamma_tail_risk_weight', 0.50),
                gamma_tail_radius_weight=getattr(args, 'source_budget_gamma_tail_radius_weight', 0.0),
                gamma_stability_delta=getattr(args, 'source_budget_gamma_stability_delta', 0.05),
                gamma_tail_risk_mode=getattr(args, 'source_budget_gamma_tail_risk_mode', 'spectral'),
            )
            source_budget_schedule_from_files(
                candidate_specs=source_specs,
                out_actions=source_budget_actions_path,
                out_rows=source_budget_rows_path,
                out_report=source_budget_report_path,
                db_path=getattr(args, 'audit_scheduler_db', None),
                response_paths=[str(audit_dir/'responses.jsonl')] if (audit_dir/'responses.jsonl').exists() else None,
                config=sb_cfg,
            )
            if getattr(args, 'audit_source_budget_candidates', False) and source_budget_actions_path.exists():
                source_budget_audit_dir = out / 'source_budget_audit'
                _pipeline_audit(tasks_for_pipeline, str(source_budget_actions_path), source_budget_audit_dir, getattr(args, 'source_budget_budget', None) or args.max_actions, state_candidates=False, candidate_mode='state')
                cmd_action_report(argparse.Namespace(responses=str(source_budget_audit_dir/'responses.jsonl'), out=str(out/'source_budget_action_report.json'), csv_out=str(out/'source_budget_action_report.csv'), group_keys=None))
        else:
            (source_budget_dir / 'source_budget_report.json').write_text(json.dumps({'schema_version': 'lean-rgc-source-budget-scheduler-v46.0', 'status': 'skipped_no_candidate_sources', 'canonical_status': 'source_budget_schedule_chart_not_canonical'}, indent=2, ensure_ascii=False), encoding='utf-8')

    if actions_for_coker is None:
        cand_path=out/'generated_candidates.jsonl'
        cmd_candidates(argparse.Namespace(tasks=tasks_for_pipeline,out=str(cand_path),max_candidates=args.max_actions,candidate_mode=args.candidate_mode,import_mode=args.import_mode))
        actions_for_coker=str(cand_path)
    carrier_actions_path=out/'carrier_actions.jsonl'
    cmd_carrier_actions(argparse.Namespace(proposals=str(out/'carrier_generated_contexts.jsonl'),out=str(carrier_actions_path),prefix='carrier',max_actions_per_context=8))
    cmd_carrier_coker(argparse.Namespace(defects=str(audit_dir/'defects.jsonl'),actions=actions_for_coker,out=str(out/'carrier_coker.jsonl')))
    carrier_matrix_path = None
    carrier_matrix_merged_path = None
    if getattr(args, 'carrier_matrix', False):
        carrier_matrix_path = out/'carrier_matrix.json'
        cmd_carrier_matrix(argparse.Namespace(responses=str(audit_dir/'responses.jsonl'), out=str(carrier_matrix_path), shrink=args.carrier_matrix_shrink, min_count=args.carrier_matrix_min_count))
        matrix_for_actions = carrier_matrix_path
        if getattr(args, 'carrier_matrix_merge_qgen', False) and qgen_carrier_incidence_path and qgen_carrier_incidence_path.exists():
            carrier_matrix_merged_path = out/'carrier_matrix_qgen.json'
            patch_path_for_merge = qgen_carrier_incidence_path
            if getattr(args, 'carrier_matrix_qgen_audit_patches', False):
                patch_audit_responses = None
                if qgen_audit_dir and (qgen_audit_dir/'responses.jsonl').exists():
                    patch_audit_responses = qgen_audit_dir/'responses.jsonl'
                elif qgen_registry_audit_dir and (qgen_registry_audit_dir/'responses.jsonl').exists():
                    patch_audit_responses = qgen_registry_audit_dir/'responses.jsonl'
                elif (audit_dir/'responses.jsonl').exists():
                    patch_audit_responses = audit_dir/'responses.jsonl'
                if patch_audit_responses is not None:
                    audited_patches = out/'qgen_carrier_incidence_audited.jsonl'
                    cmd_carrier_patch_audit(argparse.Namespace(
                        patches=str(qgen_carrier_incidence_path),
                        responses=str(patch_audit_responses),
                        out_report=str(out/'qgen_carrier_patch_audit_report.json'),
                        out_patches=str(audited_patches),
                        min_count=args.carrier_matrix_qgen_patch_min_count,
                        min_mean_delta=args.carrier_matrix_qgen_patch_min_mean_delta,
                        no_sign_agreement=False,
                        holdout_fraction=getattr(args, "carrier_matrix_qgen_patch_holdout_fraction", 0.0),
                        heldout_min_count=getattr(args, "carrier_matrix_qgen_patch_heldout_min_count", None),
                        heldout_min_mean_delta=getattr(args, "carrier_matrix_qgen_patch_heldout_min_mean_delta", None),
                        require_heldout=getattr(args, "carrier_matrix_qgen_patch_require_heldout", False),
                    ))
                    patch_path_for_merge = audited_patches
            cmd_carrier_matrix_merge_patches(argparse.Namespace(matrix=str(carrier_matrix_path), patches=str(patch_path_for_merge), out=str(carrier_matrix_merged_path), patch_weight=args.carrier_matrix_qgen_patch_weight, require_safe=args.carrier_matrix_qgen_require_safe, report_out=str(out/'qgen_carrier_patch_report.json')))
            matrix_for_actions = carrier_matrix_merged_path
        cmd_multi_carrier_report(argparse.Namespace(matrix=str(matrix_for_actions), defects=str(audit_dir/'defects.jsonl'), out=str(out/'multi_carrier_report.json')))
        if actions_for_coker:
            cmd_carrier_safe_actions(argparse.Namespace(actions=actions_for_coker, matrix=str(matrix_for_actions), out=str(out/'carrier_safe_actions.jsonl'), budget=args.carrier_matrix_budget, keep_unsafe=args.carrier_matrix_keep_unsafe))
    carrier_accept_path=None; carrier_accept_summary_path=None
    if args.carrier_accept:
        carrier_accept_path=out/'carrier_acceptance.jsonl'
        cmd_carrier_accept(argparse.Namespace(tasks=tasks_for_pipeline,proposals=str(out/'carrier_generated_contexts.jsonl'),out=str(carrier_accept_path),margin_threshold=args.carrier_accept_margin,cost_weight=args.carrier_accept_cost_weight,lean_cmd=args.lean_cmd,workdir=args.workdir,timeout_s=args.timeout_s,dry_run=args.dry_run,keep_files=args.keep_files,cache_dir=args.cache_dir or str(out/'cache'),trace_state=args.trace_state,import_mode=args.import_mode,max_actions=args.carrier_accept_max_actions))
        carrier_accept_summary_path=out/'carrier_acceptance_summary.json'
        cmd_carrier_accept_summary(argparse.Namespace(accepted=str(carrier_accept_path),out=str(carrier_accept_summary_path)))
        if args.promote_carrier_actions:
            cmd_accepted_carrier_actions(argparse.Namespace(accepted=str(carrier_accept_path),out=str(out/'carrier_promoted_actions.jsonl'),min_margin=args.promote_carrier_min_margin,include_rejected=False))
    qgen_acceptance_lineage_path = None
    if qgen_dir:
        accepted_paths = []
        for pth in [qgen_audited_accepted_actions_path, qgen_robust_accepted_actions_path, qgen_registry_accepted_path, locals().get('qgen_registry_robust_accepted_path')]:
            if pth and Path(pth).exists():
                accepted_paths.append(pth)
        row_paths = []
        for pth in [out/'qgen_acceptance_rows.jsonl', out/'qgen_robust_acceptance_rows.jsonl', out/'qgen_registry_acceptance_rows.jsonl', out/'qgen_registry_robust_acceptance_rows.jsonl']:
            if Path(pth).exists():
                row_paths.append(pth)
        audit_paths = []
        for pth in [qgen_audit_dir/'responses.jsonl' if qgen_audit_dir else None, qgen_registry_audit_dir/'responses.jsonl' if qgen_registry_audit_dir else None]:
            if pth and Path(pth).exists():
                audit_paths.append(pth)
        registry_paths = []
        if qgen_registry_candidates_path and Path(qgen_registry_candidates_path).exists():
            registry_paths.append(qgen_registry_candidates_path)
        qgen_acceptance_lineage_path = out/'qgen_acceptance_lineage.json'
        build_qgen_acceptance_lineage(qgen_dir, accepted_actions=accepted_paths, acceptance_rows=row_paths, audit_responses=audit_paths, registry_candidates=registry_paths, out=qgen_acceptance_lineage_path)
    transitions_path=out/'transitions.jsonl'
    cmd_make_transitions(argparse.Namespace(responses=str(audit_dir/'responses.jsonl'),out=str(transitions_path)))
    gamma_path=out/'gamma_audit.jsonl'
    cmd_gamma_audit(argparse.Namespace(transitions=str(transitions_path),out=str(gamma_path),fit_gamma=args.fit_gamma,ridge=1e-3,horizon=args.gamma_horizon,include_gamma_matrix=False))
    gamma_transition_dir = None
    gamma_transition_report_path = None
    gamma_transition_actions_path = None
    gamma_transition_patches_path = None
    gamma_transition_patched_action_geometry_path = None
    if getattr(args, 'gamma_transition_learner', False):
        gamma_transition_dir = out / 'gamma_transition'
        teacher_constraints = None
        if arithmetic_teacher_dir and (arithmetic_teacher_dir / 'cocycle_audit' / 'arithmetic_teacher_gamma_constraints.jsonl').exists():
            teacher_constraints = arithmetic_teacher_dir / 'cocycle_audit' / 'arithmetic_teacher_gamma_constraints.jsonl'
        learn_gamma_transition_model(
            transitions_path,
            gamma_transition_dir,
            actions_path=args.actions,
            teacher_constraints_path=teacher_constraints,
            ridge=getattr(args, 'gamma_transition_ridge', 1e-3),
            shrink=getattr(args, 'gamma_transition_shrink', 4.0),
            min_count=getattr(args, 'gamma_transition_min_count', 2),
            holdout_fraction=getattr(args, 'gamma_transition_holdout_fraction', 0.25),
            teacher_weight=getattr(args, 'gamma_transition_teacher_weight', 0.25),
            include_matrices=getattr(args, 'gamma_transition_include_matrices', False),
        )
        gamma_transition_report_path = gamma_transition_dir / 'gamma_transition_report.json'
        gamma_transition_actions_path = gamma_transition_dir / 'gamma_transition_actions.jsonl'
        gamma_transition_patches_path = gamma_transition_dir / 'gamma_transition_action_geometry_patches.jsonl'
        if getattr(args, 'gamma_transition_patch_action_geometry', False) and action_geometry_registry_path and Path(action_geometry_registry_path).exists() and gamma_transition_patches_path.exists():
            gamma_transition_patched_action_geometry_path = gamma_transition_dir / 'action_geometry_gamma_patched.jsonl'
            merge_gamma_transition_patches_into_action_geometry(
                action_geometry_registry_path,
                gamma_transition_patches_path,
                gamma_transition_patched_action_geometry_path,
                summary_out=gamma_transition_dir / 'action_geometry_gamma_patch_report.json',
            )
    rep=write_run_report(audit_dir,out/'pipeline_report.json')
    rep['pipeline_files']={
        'audit_dir':str(audit_dir),'frontier_summary':frontier_summary,'response_model':str(out/'response_model.json'),'response_eval_summary':str(out/'response_eval_summary.json') if getattr(args, 'eval_response_model', False) else None,'response_eval_rows':str(out/'response_eval_rows.jsonl') if getattr(args, 'eval_response_model', False) else None,'components':str(out/'response_components.jsonl'),
        'states_ir':str(states_ir_path),'ir_defects':str(out/'ir_defects.jsonl'),'exposure_report':str(exposure_report_path),'action_report':str(out/'action_report.json'),'action_report_csv':str(out/'action_report.csv'),
        'arithmetic_teacher_dir': str(arithmetic_teacher_dir) if arithmetic_teacher_dir else None,
        'arithmetic_teacher_actions': str(arithmetic_teacher_actions_path) if arithmetic_teacher_actions_path else None,
        'arithmetic_teacher_audit_dir': str(arithmetic_teacher_audit_dir) if arithmetic_teacher_audit_dir else None,
        'arithmetic_teacher_audit_report': str(arithmetic_teacher_audit_report_path) if arithmetic_teacher_audit_report_path else None,
        'arithmetic_teacher_kernel_audit_dir': str(arithmetic_teacher_dir / 'kernel_transition_audit') if arithmetic_teacher_dir and (arithmetic_teacher_dir / 'kernel_transition_audit').exists() else None,
        'arithmetic_teacher_cocycle_dir': str(arithmetic_teacher_dir / 'cocycle_audit') if arithmetic_teacher_dir and (arithmetic_teacher_dir / 'cocycle_audit').exists() else None,
        'contextual_congruence_dir': str(contextual_congruence_dir) if contextual_congruence_dir else None,
        'contextual_congruence_report': str(contextual_congruence_report_path) if contextual_congruence_report_path else None,
        'contextual_congruence_classes': str(contextual_congruence_classes_path) if contextual_congruence_classes_path else None,
        'contextual_congruence_representatives': str(contextual_congruence_representatives_path) if contextual_congruence_representatives_path else None,
        'contextual_probe_dir': str(contextual_probe_dir) if contextual_probe_dir else None,
        'contextual_probe_candidates': str(contextual_probe_candidates_path) if contextual_probe_candidates_path else None,
        'contextual_probe_audit_dir': str(contextual_probe_audit_dir) if contextual_probe_audit_dir else None,
        'contextual_probe_accepted_actions': str(contextual_probe_accepted_actions_path) if contextual_probe_accepted_actions_path else None,
        'contextual_probe_robust_accepted_actions': str(contextual_probe_robust_accepted_actions_path) if contextual_probe_robust_accepted_actions_path else None,
        'contextual_probe_congruence_dir': str(contextual_probe_congruence_dir) if contextual_probe_congruence_dir else None,
        'contextual_probe_report': str(contextual_probe_report_path) if contextual_probe_report_path else None,
        'source_budget_dir': str(source_budget_dir) if locals().get('source_budget_dir') else None,
        'source_budget_actions': str(source_budget_actions_path) if locals().get('source_budget_actions_path') else None,
        'source_budget_report': str(source_budget_report_path) if locals().get('source_budget_report_path') else None,
        'source_budget_audit_dir': str(source_budget_audit_dir) if locals().get('source_budget_audit_dir') else None,
        'source_budget_action_report': str(out/'source_budget_action_report.json') if locals().get('source_budget_audit_dir') else None,
        'response_quotient_dir': str(response_quotient_dir) if response_quotient_dir else None,
        'response_quotient_registry': str(response_quotient_registry_path) if response_quotient_registry_path else None,
        'response_quotient_representatives': str(response_quotient_representatives_path) if response_quotient_representatives_path else None,
        'response_quotient_projected_actions': str(response_quotient_projected_actions_path) if response_quotient_projected_actions_path else None,
        'carrier_quotient_dir': str(carrier_quotient_dir) if carrier_quotient_dir else None,
        'carrier_quotient_candidates': str(carrier_quotient_candidates_path) if carrier_quotient_candidates_path else None,
        'carrier_quotient_defect_registry': str(carrier_quotient_registry_path) if carrier_quotient_registry_path else None,
        'carrier_quotient_incidence_patches': str(carrier_quotient_patch_path) if carrier_quotient_patch_path else None,
        'carrier_quotient_audit_dir': str(carrier_quotient_audit_dir) if carrier_quotient_audit_dir else None,
        'carrier_quotient_accepted_actions': str(carrier_quotient_accepted_actions_path) if carrier_quotient_accepted_actions_path else None,
        'carrier_quotient_robust_accepted_actions': str(carrier_quotient_robust_accepted_actions_path) if carrier_quotient_robust_accepted_actions_path else None,
        'qgen_dir':str(qgen_dir) if qgen_dir else None,'qgen_context_candidates':str(qgen_context_candidates_path) if qgen_context_candidates_path else None,'qgen_accepted_actions':str(qgen_accepted_actions_path) if qgen_accepted_actions_path else None,'qgen_defect_registry':str(qgen_defect_registry_path) if qgen_defect_registry_path else None,'qgen_carrier_incidence':str(qgen_carrier_incidence_path) if qgen_carrier_incidence_path else None,'qgen_failure_signatures':str(qgen_failure_signatures_path) if qgen_failure_signatures_path else None,'qgen_lineage':str(qgen_lineage_path) if qgen_lineage_path else None,'qgen_registry_candidates':str(qgen_registry_candidates_path) if qgen_registry_candidates_path else None,'qgen_registry_audit_dir':str(qgen_registry_audit_dir) if qgen_registry_audit_dir else None,'qgen_registry_accepted_actions':str(qgen_registry_accepted_path) if qgen_registry_accepted_path else None,'qgen_audit_dir':str(qgen_audit_dir) if qgen_audit_dir else None,'qgen_action_report':str(out/'qgen_action_report.json') if qgen_audit_dir else None,'qgen_audited_accepted_actions':str(qgen_audited_accepted_actions_path) if qgen_audited_accepted_actions_path else None,'qgen_acceptance_report':str(qgen_acceptance_report_path) if qgen_acceptance_report_path else None,'qgen_robust_accepted_actions':str(qgen_robust_accepted_actions_path) if qgen_robust_accepted_actions_path else None,'qgen_robust_acceptance_report':str(qgen_robust_acceptance_report_path) if qgen_robust_acceptance_report_path else None,'qgen_robust_acceptance_rows':str(qgen_robust_acceptance_rows_path) if qgen_robust_acceptance_rows_path else None,'qgen_acceptance_lineage':str(qgen_acceptance_lineage_path) if qgen_acceptance_lineage_path else None,
        'quotient_coordinate_dir': str(quotient_coordinate_dir) if quotient_coordinate_dir else None,
        'quotient_coordinate_candidates': str(quotient_coordinate_candidates_path) if quotient_coordinate_candidates_path else None,
        'quotient_coordinate_defect_registry': str(quotient_coordinate_registry_path) if quotient_coordinate_registry_path else None,
        'quotient_coordinate_registry_candidates': str(quotient_coordinate_registry_candidates_path) if quotient_coordinate_registry_candidates_path else None,
        'quotient_coordinate_audit_dir': str(quotient_coordinate_audit_dir) if quotient_coordinate_audit_dir else None,
        'quotient_coordinate_accepted_actions': str(quotient_coordinate_accepted_actions_path) if quotient_coordinate_accepted_actions_path else None,
        'quotient_coordinate_robust_accepted_actions': str(quotient_coordinate_robust_accepted_actions_path) if quotient_coordinate_robust_accepted_actions_path else None,
        'action_geometry_dir': str(action_geometry_dir) if action_geometry_dir else None,
        'action_geometry_registry': str(action_geometry_registry_path) if action_geometry_registry_path else None,
        'action_geometry_candidates': str(action_geometry_candidates_path) if action_geometry_candidates_path else None,
        'action_geometry_audit_dir': str(action_geometry_audit_dir) if action_geometry_audit_dir else None,
        'action_geometry_action_report': str(out/'action_geometry_action_report.json') if action_geometry_audit_dir else None,
        'action_geometry_accepted_actions': str(action_geometry_accepted_actions_path) if action_geometry_accepted_actions_path else None,
        'action_geometry_robust_accepted_actions': str(action_geometry_robust_accepted_actions_path) if action_geometry_robust_accepted_actions_path else None,
        'action_geometry_acceptance_report': str(action_geometry_acceptance_report_path) if action_geometry_acceptance_report_path else None,
        'action_geometry_robust_acceptance_report': str(action_geometry_robust_acceptance_report_path) if action_geometry_robust_acceptance_report_path else None,
        'quotient_coordinate_dir': str(quotient_coordinate_dir) if quotient_coordinate_dir else None,
        'quotient_coordinate_candidates': str(quotient_coordinate_candidates_path) if quotient_coordinate_candidates_path else None,
        'quotient_coordinate_defect_registry': str(quotient_coordinate_registry_path) if quotient_coordinate_registry_path else None,
        'quotient_coordinate_registry_candidates': str(quotient_coordinate_registry_candidates_path) if quotient_coordinate_registry_candidates_path else None,
        'quotient_coordinate_audit_dir': str(quotient_coordinate_audit_dir) if quotient_coordinate_audit_dir else None,
        'quotient_coordinate_accepted_actions': str(quotient_coordinate_accepted_actions_path) if quotient_coordinate_accepted_actions_path else None,
        'quotient_coordinate_robust_accepted_actions': str(quotient_coordinate_robust_accepted_actions_path) if quotient_coordinate_robust_accepted_actions_path else None,
        'quotient_coordinate_validation_report': str(quotient_coordinate_validation_report_path) if quotient_coordinate_validation_report_path and Path(quotient_coordinate_validation_report_path).exists() else None,
        'quotient_coordinate_response_normal': str(quotient_coordinate_response_normal_path) if quotient_coordinate_response_normal_path else None,
        'failure_signatures':str(failure_signatures_path) if failure_signatures_path else None,'failure_signature_actions':str(failure_signature_actions_path) if failure_signature_actions_path else None,'failure_signature_audit_dir':str(failure_signature_audit_dir) if failure_signature_audit_dir else None,'failure_signature_acceptance_report':str(out/'failure_signature_acceptance_report.json') if failure_signature_audit_dir and getattr(args, 'failure_signature_accept_coker', False) else None,'exposure_audit_report':str(out/'exposure_audit_report.json') if getattr(args, 'audit_exposures', False) else None,
        'defect_registry':str(registry_path) if registry_path else None,'promoted_registry':str(promoted_registry_path) if promoted_registry_path else None,
        'auto_defects':str(out/'auto_defects.jsonl') if registry_path else None,'registry_candidates':str(registry_candidates_path) if registry_candidates_path else None,
        'registry_audit_dir':str(out/'registry_audit') if (registry_candidates_path is not None and args.audit_registry_candidates) else None,
        'registry_acceptance_report':str(out/'registry_acceptance_report.json') if (registry_candidates_path is not None and args.registry_accept_coker) else None,'registry_action_report':str(out/'registry_action_report.json') if (registry_candidates_path is not None and args.audit_registry_candidates) else None,
        'premise_index':str(premise_index_path) if premise_index_path else None,'premise_candidates':str(premise_candidates_path) if premise_candidates_path else None,'premise_audit_dir':str(premise_audit_dir) if premise_audit_dir else None,'premise_action_report':str(out/'premise_action_report.json') if premise_audit_dir else None,
        'premise_contextual_dir': str(premise_contextual_dir) if locals().get('premise_contextual_dir') else None,
        'premise_use_rows': str(premise_use_rows_path) if locals().get('premise_use_rows_path') else None,
        'separator_contexts': str(separator_contexts_path) if locals().get('separator_contexts_path') else None,
        'premise_contextual_candidates': str(premise_contextual_candidates_path) if locals().get('premise_contextual_candidates_path') else None,
        'premise_contextual_scheduled_actions': str(premise_contextual_scheduled_path) if locals().get('premise_contextual_scheduled_path') else None,
        'premise_contextual_audit_dir': str(premise_contextual_audit_dir) if locals().get('premise_contextual_audit_dir') else None,
        'premise_contextual_fingerprints': str(premise_contextual_fingerprints_path) if locals().get('premise_contextual_fingerprints_path') else None,
        'premise_contextual_classes': str(premise_contextual_classes_path) if locals().get('premise_contextual_classes_path') else None,
        'premise_contextual_validation': str(premise_contextual_dir/'premise_quotient_validation_rows.jsonl') if locals().get('premise_contextual_dir') else None,
        'premise_contextual_repair_faces': str(repair_face_ledger_path) if locals().get('repair_face_ledger_path') else None,
        'premise_quotient_retrieved': str(premise_quotient_retrieved_path) if locals().get('premise_quotient_retrieved_path') else None,
        'premise_quotient_actions': str(premise_quotient_actions_path) if locals().get('premise_quotient_actions_path') else None,
        'carrier_generated':str(out/'carrier_generated_contexts.jsonl'),'carrier_actions':str(carrier_actions_path),'carrier_coker':str(out/'carrier_coker.jsonl'),
        'carrier_acceptance':str(carrier_accept_path) if carrier_accept_path else None,'carrier_acceptance_summary':str(carrier_accept_summary_path) if carrier_accept_summary_path else None,
        'ir_candidates': str(out/'ir_candidates.jsonl') if getattr(args, 'ir_candidates', False) else None,
        'ir_audit_dir': str(out/'ir_audit') if getattr(args, 'audit_ir_candidates', False) else None,
        'ir_action_report': str(out/'ir_action_report.json') if getattr(args, 'audit_ir_candidates', False) else None,
        'ir_acceptance_report': str(out/'ir_acceptance_report.json') if getattr(args, 'ir_accept_coker', False) else None,
        'ir_audit_dir': str(out/'ir_audit') if getattr(args, 'audit_ir_candidates', False) else None,
        'ir_action_report': str(out/'ir_action_report.json') if getattr(args, 'audit_ir_candidates', False) else None,
        'ir_acceptance_report': str(out/'ir_acceptance_report.json') if getattr(args, 'ir_accept_coker', False) else None,
        'ir_accepted_actions': str(out/'ir_accepted_actions.jsonl') if getattr(args, 'ir_accept_coker', False) else None,
        'carrier_matrix': str(out/'carrier_matrix.json') if getattr(args, 'carrier_matrix', False) else None,
        'carrier_matrix_qgen': str(out/'carrier_matrix_qgen.json') if (getattr(args, 'carrier_matrix', False) and getattr(args, 'carrier_matrix_merge_qgen', False)) else None,
        'qgen_carrier_patch_report': str(out/'qgen_carrier_patch_report.json') if (getattr(args, 'carrier_matrix', False) and getattr(args, 'carrier_matrix_merge_qgen', False)) else None,
        'qgen_carrier_patch_audit_report': str(out/'qgen_carrier_patch_audit_report.json') if (getattr(args, 'carrier_matrix_qgen_audit_patches', False)) else None,
        'qgen_carrier_incidence_audited': str(out/'qgen_carrier_incidence_audited.jsonl') if (getattr(args, 'carrier_matrix_qgen_audit_patches', False)) else None,
        'multi_carrier_report': str(out/'multi_carrier_report.json') if getattr(args, 'carrier_matrix', False) else None,
        'carrier_safe_actions': str(out/'carrier_safe_actions.jsonl') if getattr(args, 'carrier_matrix', False) else None,
        'transitions':str(transitions_path),'gamma_audit':str(gamma_path),
        'gamma_transition_dir': str(gamma_transition_dir) if gamma_transition_dir else None,
        'gamma_transition_report': str(gamma_transition_report_path) if gamma_transition_report_path else None,
        'gamma_transition_actions': str(gamma_transition_actions_path) if gamma_transition_actions_path else None,
        'gamma_transition_action_geometry_patches': str(gamma_transition_patches_path) if gamma_transition_patches_path else None,
        'gamma_transition_patched_action_geometry': str(gamma_transition_patched_action_geometry_path) if gamma_transition_patched_action_geometry_path else None,
    }
    # Stage ladder summarizes whether registry/IR/premise/carrier generated charts improve over the base audit.
    try:
        stage_paths = default_pipeline_stages(out)
        if stage_paths:
            write_stage_report(stage_paths, out/'stage_report.json', out/'stage_report.csv')
            rep['pipeline_files']['stage_report'] = str(out/'stage_report.json')
            rep['pipeline_files']['stage_report_csv'] = str(out/'stage_report.csv')
            if getattr(args, 'stage_coker', False):
                stage_args = [f"{name}={path}" for name, path in stage_paths if name != 'base']
                if stage_args:
                    stage_coker_rep = run_stage_coker(
                        audit_dir/'responses.jsonl',
                        stage_args,
                        out_report=out/'stage_coker_report.json',
                        out_actions=out/'stage_coker_accepted_actions.jsonl',
                        out_rows_dir=out/'stage_coker_rows',
                        out_csv=out/'stage_coker_report.csv',
                        margin_threshold=args.stage_coker_margin,
                        cost_weight=args.stage_coker_cost_weight,
                        carrier_weight=args.stage_coker_carrier_weight,
                        max_actions=args.stage_coker_max_actions,
                    )
                    rep['pipeline_files']['stage_coker_report'] = str(out/'stage_coker_report.json')
                    rep['pipeline_files']['stage_coker_actions'] = str(out/'stage_coker_accepted_actions.jsonl')
    except Exception as e:
        rep.setdefault('warnings', []).append({'stage_report_error': str(e)})
    if getattr(args, 'audit_db', False):
        try:
            db_path = Path(args.audit_db_path) if getattr(args, 'audit_db_path', None) else (out / 'audit.db')
            db_summary = build_audit_db(out, db_path, reset=not getattr(args, 'audit_db_append', False))
            rep['pipeline_files']['audit_db'] = str(db_path)
            rep['pipeline_files']['audit_db_summary'] = str(Path(db_path).parent / 'audit_db_summary.json')
            rep['audit_db_summary'] = db_summary
        except Exception as e:
            rep.setdefault('warnings', []).append({'audit_db_error': str(e)})
    (out/'pipeline_report.json').write_text(json.dumps(rep,indent=2,ensure_ascii=False),encoding='utf-8')
    (out/'pipeline_summary.json').write_text(json.dumps(rep,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(rep,indent=2,ensure_ascii=False)); return 0








def cmd_robust_accept_candidates(args):
    rows, summary = robust_accept_candidates_file(
        args.base_responses,
        args.candidate_responses,
        args.out,
        shadow_responses=args.shadow_responses,
        accepted_actions_out=args.accepted_actions_out,
        summary_out=args.summary_out,
        margin_threshold=args.margin_threshold,
        cost_weight=args.cost_weight,
        carrier_weight=args.carrier_weight,
        audit_weight=args.audit_weight,
        disagreement_weight=args.disagreement_weight,
        require_shadow=args.require_shadow,
        require_success=args.require_success,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False)); return 0

def cmd_qgen(args):
    rep = qgen_from_files(
        args.responses,
        audits=args.audits,
        out_dir=args.out,
        ridge=args.ridge,
        max_mass=args.max_mass,
        top_defects=args.top_defects,
        top_contexts=args.top_contexts,
        top_carriers=args.top_carriers,
        top_failures=args.top_failures,
        margin_threshold=args.margin_threshold,
        cost_weight=args.cost_weight,
        carrier_weight=args.carrier_weight,
        audit_penalty=args.audit_penalty,
    )
    print(json.dumps(rep.to_dict(), indent=2, ensure_ascii=False)); return 0


def cmd_stage_coker(args):
    rep = run_stage_coker(
        args.base_responses,
        args.stage,
        out_report=args.out_report,
        out_actions=args.out_actions,
        out_rows_dir=args.out_rows_dir,
        out_csv=args.csv_out,
        margin_threshold=args.margin_threshold,
        cost_weight=args.cost_weight,
        carrier_weight=args.carrier_weight,
        audit_penalty=args.audit_penalty,
        require_success=args.require_success,
        max_actions=args.max_actions,
    )
    print(json.dumps(rep.to_dict(), indent=2, ensure_ascii=False)); return 0


def cmd_quality_gates(args):
    rep = quality_gates_for_run(
        args.run_dir,
        min_audits=args.min_audits,
        min_success_rate=args.min_success_rate,
        min_mean_goal_response=args.min_mean_goal_response,
        min_registry_accept=args.min_registry_accept,
        min_gamma_improvement=args.min_gamma_improvement,
        max_gamma_cocycle_rel=args.max_gamma_cocycle_rel,
        min_qgen_realized_match_rate=args.min_qgen_realized_match_rate,
        min_qgen_realized_success_rate=args.min_qgen_realized_success_rate,
        min_qgen_realized_goal_response=args.min_qgen_realized_goal_response,
        min_qgen_patch_audit_accept_rate=args.min_qgen_patch_audit_accept_rate,
    )
    write_quality_report(rep, args.out, args.csv_out)
    print(json.dumps(rep.to_dict(), indent=2, ensure_ascii=False)); return 0


def cmd_robust_coker_accept(args):
    rep = run_robust_coker_acceptance(
        args.base_responses,
        args.candidate_responses,
        out_report=args.out_report,
        out_actions=args.out_actions,
        out_rows=args.out_rows,
        out_csv=args.csv_out,
        margin_threshold=args.margin_threshold,
        holdout_fraction=args.holdout_fraction,
        ridge=args.ridge,
        max_mass=args.max_mass,
        cost_weight=args.cost_weight,
        carrier_gain_weight=args.carrier_gain_weight,
        carrier_violation_weight=args.carrier_violation_weight,
        audit_penalty=args.audit_penalty,
        uncertainty_weight=args.uncertainty_weight,
        require_success=args.require_success,
        max_actions=args.max_actions,
    )
    print(json.dumps(rep.to_dict(), indent=2, ensure_ascii=False)); return 0

def cmd_expose_frontiers(args):
    tasks = _normalize_tasks_imports(_load_tasks(args.tasks), args.import_mode, args.workdir, args.lean_cmd)
    cfg = LeanExecutorConfig(lean_cmd=args.lean_cmd, timeout_s=args.timeout_s, dry_run=args.dry_run, keep_files=args.keep_files, workdir=args.workdir, cache_dir=args.cache_dir, trace_state=args.trace_state)
    statuses = set(args.accept_status or ["partial", "success", "dry_run"])
    rep = build_frontiers(tasks, executor_config=cfg, out_dir=args.out, max_prefixes=args.max_prefixes, include_identity=args.include_identity, accept_statuses=statuses, resume=args.resume)
    print(json.dumps(rep, indent=2, ensure_ascii=False)); return 0

def cmd_make_corebench(args):
    imports = [] if args.import_mode == "core" else (["Mathlib"] if args.import_mode == "mathlib" else [])
    summary = write_corebench(args.out, n_nat=args.n_nat, n_prop=args.n_prop, n_bool=args.n_bool, n_eq=args.n_eq, imports=imports)
    print(json.dumps(summary, indent=2, ensure_ascii=False)); return 0


def cmd_iterate(args):
    from .iterative import run_iterative_pipeline
    rep = run_iterative_pipeline(
        tasks=args.tasks,
        actions=args.actions,
        out=args.out,
        rounds=args.rounds,
        dry_run=args.dry_run,
        jobs=args.jobs,
        max_actions=args.max_actions,
        lean_cmd=args.lean_cmd,
        workdir=args.workdir,
        timeout_s=args.timeout_s,
        import_mode=args.import_mode,
        cache_dir=args.cache_dir,
        server_cmd=args.server_cmd,
        server_backend=args.server_backend,
        server_no_fallback=args.server_no_fallback,
        native_exec_mode=getattr(args, "native_exec_mode", "source_check"),
        resume=args.resume,
        flush_every=args.flush_every,
        candidate_mode=args.candidate_mode,
        audit_mode=args.audit_mode,
        bulk_batch_size=args.bulk_batch_size,
        frontier_normalize=args.frontier_normalize,
        frontier_max_prefixes=args.frontier_max_prefixes,
        frontier_include_identity=args.frontier_include_identity,
        registry_audit_max_actions=args.registry_audit_max_actions,
        registry_accept_margin=args.registry_accept_margin,
        registry_accept_max_per_task=args.registry_accept_max_per_task,
        promote_registry=args.promote_registry,
        premise_index=args.premise_index,
        audit_premise_candidates=args.audit_premise_candidates,
        premise_audit_max_actions=args.premise_audit_max_actions,
        merge_premise_actions=args.merge_premise_actions,
        carrier_accept=args.carrier_accept,
        carrier_accept_max_actions=args.carrier_accept_max_actions,
        promote_carrier_actions=args.promote_carrier_actions,
        fit_gamma=args.fit_gamma,
        qgen=args.qgen,
        qgen_merge_actions=args.qgen_merge_actions,
        qgen_merge_policy=args.qgen_merge_policy,
        poms_promote=args.poms_promote,
        poms_generate_evidence=getattr(args, "poms_generate_evidence", False),
        poms_evidence_min_relative_residual=getattr(args, "poms_evidence_min_relative_residual", 0.05),
        poms_evidence_min_residual_norm=getattr(args, "poms_evidence_min_residual_norm", 1e-6),
        poms_evidence_min_support_count=getattr(args, "poms_evidence_min_support_count", 1),
        poms_evidence_min_margin=getattr(args, "poms_evidence_min_margin", 0.0),
        poms_evidence_min_robust_margin=getattr(args, "poms_evidence_min_robust_margin", 0.0),
        poms_evidence_least_repair_epsilon=getattr(args, "poms_evidence_least_repair_epsilon", 1e-9),
        poms_promotion_evidence=args.poms_promotion_evidence,
        poms_promote_parent_nonpaid=args.poms_promote_parent_nonpaid,
        poms_promote_dual_certificate=args.poms_promote_dual_certificate,
        poms_promote_least_repair=args.poms_promote_least_repair,
        poms_declare_canonical=args.poms_declare_canonical,
        qgen_top_defects=args.qgen_top_defects,
        qgen_top_contexts=args.qgen_top_contexts,
        qgen_top_carriers=args.qgen_top_carriers,
        qgen_top_failures=args.qgen_top_failures,
        qgen_margin_threshold=args.qgen_margin_threshold,
        qgen_cost_weight=args.qgen_cost_weight,
        qgen_carrier_weight=args.qgen_carrier_weight,
        qgen_audit_penalty=args.qgen_audit_penalty,
        audit_qgen_candidates=args.audit_qgen_candidates,
        qgen_audit_max_actions=args.qgen_audit_max_actions,
        qgen_accept_coker=args.qgen_accept_coker,
        qgen_accept_margin=args.qgen_accept_margin,
        qgen_accept_max_per_task=args.qgen_accept_max_per_task,
        qgen_accept_cost_weight=args.qgen_accept_cost_weight,
        qgen_accept_carrier_weight=args.qgen_accept_carrier_weight,
        qgen_robust_accept=args.qgen_robust_accept,
        qgen_registry_robust_accept=args.qgen_registry_robust_accept,
        qgen_robust_coker_accept=args.qgen_robust_coker_accept,
        qgen_registry_robust_coker_accept=args.qgen_registry_robust_coker_accept,
        qgen_robust_coker_holdout_fraction=args.qgen_robust_coker_holdout_fraction,
        qgen_robust_coker_uncertainty_weight=args.qgen_robust_coker_uncertainty_weight,
        qgen_robust_coker_carrier_gain_weight=args.qgen_robust_coker_carrier_gain_weight,
        qgen_robust_coker_audit_penalty=args.qgen_robust_coker_audit_penalty,
        qgen_robust_coker_require_success=args.qgen_robust_coker_require_success,
        qgen_robust_z=args.qgen_robust_z,
        qgen_robust_min_repeats=args.qgen_robust_min_repeats,
        qgen_robust_min_success_rate=args.qgen_robust_min_success_rate,
        qgen_registry_candidates=args.qgen_registry_candidates,
        qgen_registry_max_candidates=args.qgen_registry_max_candidates,
        audit_qgen_registry_candidates=args.audit_qgen_registry_candidates,
        qgen_registry_audit_max_actions=args.qgen_registry_audit_max_actions,
        qgen_registry_accept_coker=args.qgen_registry_accept_coker,
        qgen_registry_accept_margin=args.qgen_registry_accept_margin,
        qgen_registry_accept_max_per_task=args.qgen_registry_accept_max_per_task,
        qgen_registry_accept_cost_weight=args.qgen_registry_accept_cost_weight,
        qgen_registry_accept_carrier_weight=args.qgen_registry_accept_carrier_weight,
        action_geometry=args.action_geometry,
        action_geometry_retrieve=args.action_geometry_retrieve,
        action_geometry_use_qgen_normals=args.action_geometry_use_qgen_normals,
        action_geometry_top_k=args.action_geometry_top_k,
        action_geometry_min_count=args.action_geometry_min_count,
        action_geometry_tail_weight=getattr(args, "action_geometry_tail_weight", 0.25),
        action_geometry_gamma_value_mode=getattr(args, "action_geometry_gamma_value_mode", "local"),
        action_geometry_gamma_horizon=getattr(args, "action_geometry_gamma_horizon", 4),
        action_geometry_gamma_discount=getattr(args, "action_geometry_gamma_discount", 1.0),
        action_geometry_gamma_stability_margin=getattr(args, "action_geometry_gamma_stability_margin", 1.0),
        action_geometry_gamma_tail_value_weight=getattr(args, "action_geometry_gamma_tail_value_weight", 1.0),
        action_geometry_cost_weight=getattr(args, "action_geometry_cost_weight", 0.05),
        action_geometry_uncertainty_weight=getattr(args, "action_geometry_uncertainty_weight", 0.10),
        action_geometry_audit_weight=getattr(args, "action_geometry_audit_weight", 0.20),
        action_geometry_require_carrier_safe=getattr(args, "action_geometry_require_carrier_safe", False),
        action_geometry_carrier_budget=getattr(args, "action_geometry_carrier_budget", 0.0),
        audit_action_geometry_candidates=args.audit_action_geometry_candidates,
        action_geometry_audit_max_actions=args.action_geometry_audit_max_actions,
        action_geometry_accept_coker=args.action_geometry_accept_coker,
        action_geometry_accept_margin=args.action_geometry_accept_margin,
        action_geometry_accept_max_per_task=args.action_geometry_accept_max_per_task,
        action_geometry_accept_cost_weight=args.action_geometry_accept_cost_weight,
        action_geometry_accept_carrier_weight=args.action_geometry_accept_carrier_weight,
        action_geometry_robust_coker_accept=args.action_geometry_robust_coker_accept,
        action_geometry_robust_coker_holdout_fraction=args.action_geometry_robust_coker_holdout_fraction,
        action_geometry_robust_coker_uncertainty_weight=args.action_geometry_robust_coker_uncertainty_weight,
        action_geometry_robust_coker_carrier_gain_weight=args.action_geometry_robust_coker_carrier_gain_weight,
        action_geometry_robust_coker_audit_penalty=args.action_geometry_robust_coker_audit_penalty,
        action_geometry_robust_coker_require_success=args.action_geometry_robust_coker_require_success,
        quotient_coordinates=args.quotient_coordinates,
        quotient_coordinate_merge_actions=args.quotient_coordinate_merge_actions,
        quotient_coordinate_merge_policy=args.quotient_coordinate_merge_policy,
        quotient_coordinate_ridge=args.quotient_coordinate_ridge,
        quotient_coordinate_max_mass=args.quotient_coordinate_max_mass,
        quotient_coordinate_cosine_threshold=args.quotient_coordinate_cosine_threshold,
        quotient_coordinate_min_states=args.quotient_coordinate_min_states,
        quotient_coordinate_top_action_scores=args.quotient_coordinate_top_action_scores,
        quotient_coordinate_margin_threshold=args.quotient_coordinate_margin_threshold,
        quotient_coordinate_validate=args.quotient_coordinate_validate,
        quotient_coordinate_registry_candidates=args.quotient_coordinate_registry_candidates,
        quotient_coordinate_registry_max_candidates=args.quotient_coordinate_registry_max_candidates,
        audit_quotient_coordinate_candidates=args.audit_quotient_coordinate_candidates,
        quotient_coordinate_audit_max_actions=args.quotient_coordinate_audit_max_actions,
        quotient_coordinate_accept_coker=args.quotient_coordinate_accept_coker,
        quotient_coordinate_robust_coker_accept=args.quotient_coordinate_robust_coker_accept,
        quotient_coordinate_accept_margin=args.quotient_coordinate_accept_margin,
        quotient_coordinate_accept_max_per_task=args.quotient_coordinate_accept_max_per_task,
        quotient_coordinate_accept_cost_weight=args.quotient_coordinate_accept_cost_weight,
        quotient_coordinate_accept_carrier_weight=args.quotient_coordinate_accept_carrier_weight,
        quotient_coordinate_robust_coker_holdout_fraction=args.quotient_coordinate_robust_coker_holdout_fraction,
        quotient_coordinate_robust_coker_uncertainty_weight=args.quotient_coordinate_robust_coker_uncertainty_weight,
        quotient_coordinate_robust_coker_carrier_gain_weight=args.quotient_coordinate_robust_coker_carrier_gain_weight,
        quotient_coordinate_robust_coker_audit_penalty=args.quotient_coordinate_robust_coker_audit_penalty,
        quotient_coordinate_robust_coker_require_success=args.quotient_coordinate_robust_coker_require_success,
        carrier_quotient=getattr(args, "carrier_quotient", False),
        carrier_quotient_merge_actions=getattr(args, "carrier_quotient_merge_actions", False),
        carrier_quotient_merge_policy=getattr(args, "carrier_quotient_merge_policy", "robust-only"),
        carrier_quotient_ridge=getattr(args, "carrier_quotient_ridge", 1e-4),
        carrier_quotient_max_mass=getattr(args, "carrier_quotient_max_mass", 1.0),
        carrier_quotient_cosine_threshold=getattr(args, "carrier_quotient_cosine_threshold", 0.85),
        carrier_quotient_min_states=getattr(args, "carrier_quotient_min_states", 1),
        carrier_quotient_top_action_scores=getattr(args, "carrier_quotient_top_action_scores", 128),
        carrier_quotient_margin_threshold=getattr(args, "carrier_quotient_margin_threshold", 0.0),
        audit_carrier_quotient_candidates=getattr(args, "audit_carrier_quotient_candidates", False),
        carrier_quotient_audit_max_actions=getattr(args, "carrier_quotient_audit_max_actions", 16),
        carrier_quotient_accept_coker=getattr(args, "carrier_quotient_accept_coker", False),
        carrier_quotient_robust_coker_accept=getattr(args, "carrier_quotient_robust_coker_accept", False),
        carrier_quotient_accept_margin=getattr(args, "carrier_quotient_accept_margin", 0.0),
        carrier_quotient_accept_max_per_task=getattr(args, "carrier_quotient_accept_max_per_task", 16),
        carrier_quotient_accept_cost_weight=getattr(args, "carrier_quotient_accept_cost_weight", 0.05),
        carrier_quotient_accept_carrier_weight=getattr(args, "carrier_quotient_accept_carrier_weight", 0.7),
        carrier_quotient_robust_coker_holdout_fraction=getattr(args, "carrier_quotient_robust_coker_holdout_fraction", 0.35),
        carrier_quotient_robust_coker_uncertainty_weight=getattr(args, "carrier_quotient_robust_coker_uncertainty_weight", 0.10),
        carrier_quotient_robust_coker_carrier_gain_weight=getattr(args, "carrier_quotient_robust_coker_carrier_gain_weight", 0.25),
        carrier_quotient_robust_coker_audit_penalty=getattr(args, "carrier_quotient_robust_coker_audit_penalty", 1.0),
        carrier_quotient_robust_coker_require_success=getattr(args, "carrier_quotient_robust_coker_require_success", False),
        source_budget=getattr(args, "source_budget", False),
        audit_source_budget_candidates=getattr(args, "audit_source_budget_candidates", False),
        source_budget_merge_actions=getattr(args, "source_budget_merge_actions", False),
        source_budget_merge_policy=getattr(args, "source_budget_merge_policy", "scheduled-only"),
        source_budget_budget=getattr(args, "source_budget_budget", None),
        source_budget_min_per_source=getattr(args, "source_budget_min_per_source", 0),
        source_budget_max_per_source=getattr(args, "source_budget_max_per_source", None),
        source_budget_per_task_cap=getattr(args, "source_budget_per_task_cap", None),
        source_budget_per_action_cap=getattr(args, "source_budget_per_action_cap", 1),
        source_budget_allocation_mode=getattr(args, "source_budget_allocation_mode", "proportional"),
        source_budget_coker_weight=getattr(args, "source_budget_coker_weight", 1.0),
        source_budget_carrier_weight=getattr(args, "source_budget_carrier_weight", 0.5),
        source_budget_uncertainty_weight=getattr(args, "source_budget_uncertainty_weight", 0.20),
        source_budget_novelty_weight=getattr(args, "source_budget_novelty_weight", 0.25),
        source_budget_lineage_weight=getattr(args, "source_budget_lineage_weight", 0.15),
        source_budget_success_weight=getattr(args, "source_budget_success_weight", 0.25),
        source_budget_cost_weight=getattr(args, "source_budget_cost_weight", 0.10),
        source_budget_timeout_weight=getattr(args, "source_budget_timeout_weight", 0.50),
        source_budget_gamma_aware=getattr(args, "source_budget_gamma_aware", False),
        source_budget_gamma_value_mode=getattr(args, "source_budget_gamma_value_mode", "finite_horizon"),
        source_budget_gamma_horizon=getattr(args, "source_budget_gamma_horizon", 4),
        source_budget_gamma_discount=getattr(args, "source_budget_gamma_discount", 1.0),
        source_budget_gamma_value_weight=getattr(args, "source_budget_gamma_value_weight", 0.50),
        source_budget_gamma_tail_risk_weight=getattr(args, "source_budget_gamma_tail_risk_weight", 0.25),
        source_budget_gamma_stability_delta=getattr(args, "source_budget_gamma_stability_delta", 0.05),
        source_budget_gamma_tail_risk_mode=getattr(args, "source_budget_gamma_tail_risk_mode", "spectral"),
        action_geometry_use_quotient_normals=args.action_geometry_use_quotient_normals,
        contextual_congruence=getattr(args, 'contextual_congruence', False),
        contextual_congruence_context_mode=getattr(args, 'contextual_congruence_context_mode', 'state'),
        contextual_congruence_no_carrier=getattr(args, 'contextual_congruence_no_carrier', False),
        contextual_congruence_min_count=getattr(args, 'contextual_congruence_min_count', 1),
        contextual_congruence_cosine_threshold=getattr(args, 'contextual_congruence_cosine_threshold', 0.95),
        contextual_congruence_distance_threshold=getattr(args, 'contextual_congruence_distance_threshold', 0.25),
        contextual_congruence_min_context_jaccard=getattr(args, 'contextual_congruence_min_context_jaccard', 0.0),
        contextual_probes=getattr(args, 'contextual_probes', False),
        contextual_probe_contexts=getattr(args, 'contextual_probe_contexts', None),
        contextual_probe_max_left=getattr(args, 'contextual_probe_max_left', 4),
        contextual_probe_max_right=getattr(args, 'contextual_probe_max_right', 4),
        contextual_probe_max_core=getattr(args, 'contextual_probe_max_core', None),
        contextual_probe_max_candidates=getattr(args, 'contextual_probe_max_candidates', 128),
        contextual_probe_no_identity=getattr(args, 'contextual_probe_no_identity', False),
        contextual_probe_no_left=getattr(args, 'contextual_probe_no_left', False),
        contextual_probe_no_right=getattr(args, 'contextual_probe_no_right', False),
        audit_contextual_probe_candidates=getattr(args, 'audit_contextual_probe_candidates', False),
        contextual_probe_audit_max_actions=getattr(args, 'contextual_probe_audit_max_actions', 24),
        contextual_probe_congruence=getattr(args, 'contextual_probe_congruence', False),
        contextual_probe_congruence_context_mode=getattr(args, 'contextual_probe_congruence_context_mode', 'state'),
        contextual_probe_congruence_no_carrier=getattr(args, 'contextual_probe_congruence_no_carrier', False),
        contextual_probe_congruence_min_count=getattr(args, 'contextual_probe_congruence_min_count', 1),
        contextual_probe_congruence_cosine_threshold=getattr(args, 'contextual_probe_congruence_cosine_threshold', 0.95),
        contextual_probe_congruence_distance_threshold=getattr(args, 'contextual_probe_congruence_distance_threshold', 0.25),
        contextual_probe_congruence_min_context_jaccard=getattr(args, 'contextual_probe_congruence_min_context_jaccard', 0.0),
        contextual_probe_accept_coker=getattr(args, 'contextual_probe_accept_coker', False),
        contextual_probe_robust_coker_accept=getattr(args, 'contextual_probe_robust_coker_accept', False),
        contextual_probe_accept_margin=getattr(args, 'contextual_probe_accept_margin', 0.0),
        contextual_probe_accept_max_per_task=getattr(args, 'contextual_probe_accept_max_per_task', 16),
        contextual_probe_accept_cost_weight=getattr(args, 'contextual_probe_accept_cost_weight', 0.05),
        contextual_probe_accept_carrier_weight=getattr(args, 'contextual_probe_accept_carrier_weight', 0.7),
        contextual_probe_robust_coker_holdout_fraction=getattr(args, 'contextual_probe_robust_coker_holdout_fraction', 0.35),
        contextual_probe_robust_coker_uncertainty_weight=getattr(args, 'contextual_probe_robust_coker_uncertainty_weight', 0.10),
        contextual_probe_robust_coker_carrier_gain_weight=getattr(args, 'contextual_probe_robust_coker_carrier_gain_weight', 0.25),
        contextual_probe_robust_coker_audit_penalty=getattr(args, 'contextual_probe_robust_coker_audit_penalty', 1.0),
        contextual_probe_robust_coker_require_success=getattr(args, 'contextual_probe_robust_coker_require_success', False),
        contextual_probe_merge_actions=getattr(args, 'contextual_probe_merge_actions', False),
        contextual_probe_merge_policy=getattr(args, 'contextual_probe_merge_policy', 'robust-only'),
        response_quotient_registry=getattr(args, 'response_quotient_registry', False),
        response_quotient_min_members=getattr(args, 'response_quotient_min_members', 1),
        response_quotient_min_quality=getattr(args, 'response_quotient_min_quality', None),
        response_quotient_project_actions=getattr(args, 'response_quotient_project_actions', False),
        response_quotient_annotate_only=getattr(args, 'response_quotient_annotate_only', False),
        response_quotient_merge_actions=getattr(args, 'response_quotient_merge_actions', False),
        response_quotient_merge_policy=getattr(args, 'response_quotient_merge_policy', 'representatives'),
        action_geometry_merge_actions=args.action_geometry_merge_actions,
        action_geometry_merge_policy=args.action_geometry_merge_policy,
        audit_db=args.audit_db,
        audit_db_path=args.audit_db_path,
        audit_db_append=args.audit_db_append,
        audit_scheduler=getattr(args, "audit_scheduler", False),
        audit_scheduler_db=getattr(args, "audit_scheduler_db", None),
        audit_scheduler_responses=getattr(args, "audit_scheduler_responses", None),
        audit_scheduler_lineage=getattr(args, "audit_scheduler_lineage", None),
        audit_scheduler_budget=getattr(args, "audit_scheduler_budget", None),
        audit_scheduler_per_task_cap=getattr(args, "audit_scheduler_per_task_cap", None),
        audit_scheduler_per_source_cap=getattr(args, "audit_scheduler_per_source_cap", None),
        audit_scheduler_coker_weight=getattr(args, "audit_scheduler_coker_weight", 1.0),
        audit_scheduler_carrier_weight=getattr(args, "audit_scheduler_carrier_weight", 0.5),
        audit_scheduler_uncertainty_weight=getattr(args, "audit_scheduler_uncertainty_weight", 0.25),
        audit_scheduler_novelty_weight=getattr(args, "audit_scheduler_novelty_weight", 0.15),
        audit_scheduler_success_weight=getattr(args, "audit_scheduler_success_weight", 0.25),
        audit_scheduler_cost_weight=getattr(args, "audit_scheduler_cost_weight", 0.10),
        audit_scheduler_timeout_weight=getattr(args, "audit_scheduler_timeout_weight", 0.50),
        ir_candidates=args.ir_candidates,
        ir_max_candidates=args.ir_max_candidates,
        audit_ir_candidates=args.audit_ir_candidates,
        ir_audit_max_actions=args.ir_audit_max_actions,
        ir_accept_coker=args.ir_accept_coker,
        carrier_matrix=args.carrier_matrix,
        carrier_matrix_budget=args.carrier_matrix_budget,
        carrier_matrix_keep_unsafe=args.carrier_matrix_keep_unsafe,
        carrier_matrix_merge_qgen=args.carrier_matrix_merge_qgen,
        carrier_matrix_qgen_patch_weight=args.carrier_matrix_qgen_patch_weight,
        carrier_matrix_qgen_require_safe=args.carrier_matrix_qgen_require_safe,
        carrier_matrix_qgen_audit_patches=args.carrier_matrix_qgen_audit_patches,
        carrier_matrix_qgen_patch_min_count=args.carrier_matrix_qgen_patch_min_count,
        carrier_matrix_qgen_patch_min_mean_delta=args.carrier_matrix_qgen_patch_min_mean_delta,
        carrier_matrix_qgen_patch_holdout_fraction=args.carrier_matrix_qgen_patch_holdout_fraction,
        carrier_matrix_qgen_patch_require_heldout=args.carrier_matrix_qgen_patch_require_heldout,
        failure_signatures=args.failure_signatures,
        audit_failure_signature_candidates=args.audit_failure_signature_candidates,
        failure_signature_audit_max_actions=args.failure_signature_audit_max_actions,
        failure_signature_accept_coker=args.failure_signature_accept_coker,
        failure_signature_accept_margin=args.failure_signature_accept_margin,
        failure_signature_accept_max_per_task=args.failure_signature_accept_max_per_task,
        next_action_cap=args.next_action_cap,
    )
    print(json.dumps(rep, indent=2, ensure_ascii=False)); return 0

def cmd_iterate_report(args):
    rep = collect_iteration_report(args.run_dir, out_json=args.out_json, out_csv=args.out_csv)
    print(json.dumps({"run_dir": args.run_dir, "n_rounds": len(rep.get("rounds", [])), "out_json": args.out_json, "out_csv": args.out_csv, "trends": rep.get("trends", {})}, indent=2, ensure_ascii=False))
    return 0





def cmd_harvest_project(args):
    meta = harvest_lean_project(
        args.root,
        out_tasks=args.out_tasks,
        out_premises=args.out_premises,
        glob=args.glob,
        include_examples=not args.no_examples,
        include_theorems=not args.no_theorems,
        include_lemmas=not args.no_lemmas,
        max_files=args.max_files,
        max_decls=args.max_decls,
    )
    if args.out_summary:
        Path(args.out_summary).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out_summary).write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(meta, indent=2, ensure_ascii=False)); return 0


def cmd_shard_jsonl(args):
    meta = shard_jsonl(args.input, args.out_dir, shards=args.shards, key=args.key, mode=args.mode, prefix=args.prefix)
    print(json.dumps(meta, indent=2, ensure_ascii=False)); return 0


def cmd_merge_jsonl(args):
    meta = merge_jsonl(args.inputs, args.out, dedup_key=args.dedup_key)
    print(json.dumps(meta, indent=2, ensure_ascii=False)); return 0

def cmd_init_lake(args): path=write_lake_template(args.out,name=args.name,mathlib=not args.no_mathlib); print(json.dumps({'out': str(path)}, indent=2, ensure_ascii=False)); return 0



def cmd_qgen_lineage(args):
    graph = build_qgen_lineage(args.qgen_dir, out=args.out)
    print(json.dumps({"out": args.out, "summary": graph.get("summary", {})}, indent=2, ensure_ascii=False)); return 0

def cmd_qgen_acceptance_lineage(args):
    graph = build_qgen_acceptance_lineage(
        args.qgen_dir,
        accepted_actions=args.accepted_actions or None,
        acceptance_rows=args.acceptance_rows or None,
        audit_responses=args.audit_responses or None,
        registry_candidates=args.registry_candidates or None,
        out=args.out,
    )
    print(json.dumps({"out": args.out, "summary": graph.get("summary", {})}, indent=2, ensure_ascii=False)); return 0



def cmd_qgen_realized_calibration(args):
    rep = collect_qgen_realized_calibration(args.run_dir, out_json=args.out_json, out_csv=args.out_csv)
    print(json.dumps({"run_dir": args.run_dir, "summary": rep.get("summary", {}), "out_json": args.out_json, "out_csv": args.out_csv}, indent=2, ensure_ascii=False)); return 0


def cmd_carrier_patch_audit(args):
    rep = audit_carrier_incidence_patches(
        args.patches,
        args.responses,
        out_report=args.out_report,
        out_patches=args.out_patches,
        min_count=args.min_count,
        min_mean_delta=args.min_mean_delta,
        require_sign_agreement=not args.no_sign_agreement,
        holdout_fraction=getattr(args, "holdout_fraction", 0.0),
        heldout_min_count=getattr(args, "heldout_min_count", None),
        heldout_min_mean_delta=getattr(args, "heldout_min_mean_delta", None),
        require_heldout=getattr(args, "require_heldout", False),
    )
    print(json.dumps({k: v for k, v in rep.items() if k != "rows"}, indent=2, ensure_ascii=False)); return 0


def cmd_poms_status(args):
    rep = collect_poms_status(
        args.run_dir,
        out_json=args.out_json,
        out_jsonl=args.out_jsonl,
        out_csv=args.out_csv,
        min_realized_goal_response=args.min_realized_goal_response,
        require_realized_success=args.require_realized_success,
    )
    print(json.dumps({"run_dir": args.run_dir, "summary": rep.get("summary", {}), "out_json": args.out_json, "out_jsonl": args.out_jsonl, "out_csv": args.out_csv}, indent=2, ensure_ascii=False)); return 0


def cmd_poms_evidence(args):
    rep = generate_promotion_evidence(
        args.run_dir,
        out_json=args.out_json,
        out_jsonl=args.out_jsonl,
        out_poms=args.out_poms,
        out_csv=args.out_csv,
        min_relative_residual=args.min_relative_residual,
        min_residual_norm=args.min_residual_norm,
        min_support_count=args.min_support_count,
        min_margin=args.min_margin,
        min_robust_margin=args.min_robust_margin,
        least_repair_epsilon=args.least_repair_epsilon,
    )
    print(json.dumps({"run_dir": args.run_dir, "summary": rep.get("summary", {}), "out_json": args.out_json, "out_jsonl": args.out_jsonl, "out_poms": args.out_poms}, indent=2, ensure_ascii=False)); return 0


def cmd_poms_promote(args):
    rep = collect_poms_promotion(
        args.run_dir,
        poms_rows=args.poms_rows,
        evidence=args.evidence,
        out_json=args.out_json,
        out_jsonl=args.out_jsonl,
        out_csv=args.out_csv,
        out_promoted_actions=args.out_promoted_actions,
        global_parent_nonpaid=args.parent_nonpaid,
        global_dual_certificate=args.dual_certificate,
        global_least_repair=args.least_repair,
        declare_canonical=args.declare_canonical,
    )
    print(json.dumps({"run_dir": args.run_dir, "summary": rep.get("summary", {}), "out_json": args.out_json, "out_jsonl": args.out_jsonl, "out_csv": args.out_csv, "out_promoted_actions": args.out_promoted_actions}, indent=2, ensure_ascii=False)); return 0

def cmd_synthesize_from_coker(args):
    summary = run_coker_synthesis(
        args.base_responses,
        archetype_responses=args.archetype_responses or args.base_responses,
        out_actions=args.out_actions,
        out_profiles=args.out_profiles,
        out_archetypes=args.out_archetypes,
        out_atoms=args.out_atoms,
        out_summary=args.out_report,
        archetype_mode=args.archetype_mode,
        ridge=args.ridge,
        max_mass=args.max_mass,
        cost_weight=args.cost_weight,
        carrier_weight=args.carrier_weight,
        uncertainty_weight=args.uncertainty_weight,
        failure_penalty=args.failure_penalty,
        margin_threshold=args.margin_threshold,
        min_archetype_support=args.min_archetype_support,
        max_per_state=args.max_actions_per_state,
        top_k_residual=args.max_residual_keys,
    )
    print(json.dumps({"summary": summary, "out_actions": args.out_actions, "out_report": args.out_report, "out_atoms": args.out_atoms}, indent=2, ensure_ascii=False))
    return 0


def cmd_coker_synthesize(args):
    summary = run_coker_synthesis(
        args.base_responses,
        archetype_responses=args.archetype_responses,
        out_actions=args.out_actions,
        out_profiles=args.out_profiles,
        out_archetypes=args.out_archetypes,
        out_atoms=args.out_atoms,
        out_summary=args.out_summary,
        archetype_mode=args.archetype_mode,
        ridge=args.ridge,
        max_mass=args.max_mass,
        cost_weight=args.cost_weight,
        carrier_weight=args.carrier_weight,
        uncertainty_weight=args.uncertainty_weight,
        failure_penalty=args.failure_penalty,
        margin_threshold=args.margin_threshold,
        min_archetype_support=args.min_archetype_support,
        max_per_state=args.max_per_state,
        top_k_residual=args.top_k_residual,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0




def cmd_audit_db_build(args):
    summary = build_audit_db(args.run_dir, args.db, reset=not getattr(args, "append", False))
    if getattr(args, "out_json", None):
        Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out_json).write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def cmd_audit_db_query(args):
    sql = args.sql
    if getattr(args, "sql_file", None):
        sql = Path(args.sql_file).read_text(encoding="utf-8")
    rows = query_audit_db(args.db, sql, max_rows=args.max_rows)
    write_query_outputs(rows, out_json=getattr(args, "out_json", None), out_csv=getattr(args, "out_csv", None))
    print(json.dumps({"db": args.db, "n_rows": len(rows), "rows": rows[:args.print_rows]}, indent=2, ensure_ascii=False))
    return 0


def cmd_audit_schedule(args):
    # Backward-compatible alias for v36 active audit scheduler.
    response_normal = _read_json_or_file(getattr(args, "response_normal", None) or getattr(args, "response_normal_json", None))
    carrier_normal = _read_json_or_file(getattr(args, "carrier_normal", None) or getattr(args, "carrier_normal_json", None))
    cfg = SchedulerConfig(
        top_k=getattr(args, "top_k", None) or getattr(args, "budget", 32),
        per_task_cap=getattr(args, "max_per_task", None) or getattr(args, "per_task_cap", None),
        response_weight=getattr(args, "coker_weight", 1.0),
        carrier_weight=getattr(args, "carrier_weight", 0.5),
        uncertainty_weight=getattr(args, "uncertainty_weight", 0.25),
        novelty_weight=getattr(args, "novelty_weight", 0.25),
        success_weight=getattr(args, "success_weight", 0.25),
        cost_weight=getattr(args, "cost_weight", 0.10),
        timeout_weight=getattr(args, "audit_risk_weight", getattr(args, "timeout_weight", 0.5)),
        min_score=getattr(args, "min_score", None) or getattr(args, "min_priority", None),
    )
    report = active_audit_schedule_from_files(
        candidates_path=getattr(args, "candidates"),
        out_actions=getattr(args, "out", None) or getattr(args, "out_actions"),
        out_rows=getattr(args, "out_rows", None) or getattr(args, "out_schedule", None),
        out_report=getattr(args, "report_out", None) or getattr(args, "out_report", None),
        db_path=getattr(args, "db", None),
        response_paths=[getattr(args, "responses")] if getattr(args, "responses", None) else getattr(args, "history_responses", None),
        response_normal=response_normal,
        carrier_normal=carrier_normal,
        config=cfg,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0

def cmd_action_geometry_registry(args):
    summary = build_action_geometry_registry(
        args.responses,
        args.out,
        summary_out=args.summary_out,
        actions_path=args.actions,
        transitions_path=args.transitions,
        min_count=args.min_count,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def cmd_action_geometry_retrieve(args):
    response_normal = None
    carrier_normal = None
    if args.response_normal_json:
        obj = json.loads(Path(args.response_normal_json).read_text(encoding="utf-8"))
        response_normal = obj.get("response_normal", obj.get("normal", obj.get("vector", obj))) if isinstance(obj, dict) else obj
    if args.response_normal:
        response_normal = json.loads(args.response_normal)
    if args.carrier_normal_json:
        obj = json.loads(Path(args.carrier_normal_json).read_text(encoding="utf-8"))
        carrier_normal = obj.get("carrier_normal", obj.get("normal", obj.get("vector", obj))) if isinstance(obj, dict) else obj
    if args.carrier_normal:
        carrier_normal = json.loads(args.carrier_normal)
    summary = score_action_geometry_registry(
        args.registry,
        args.out,
        summary_out=args.summary_out,
        response_normal=response_normal,
        carrier_normal=carrier_normal,
        top_k=args.top_k,
        tail_weight=args.tail_weight,
        cost_weight=args.cost_weight,
        uncertainty_weight=args.uncertainty_weight,
        audit_weight=args.audit_weight,
        require_carrier_safe=args.require_carrier_safe,
        carrier_budget=args.carrier_budget,
        gamma_aware=bool(getattr(args, "gamma_aware", False) or str(getattr(args, "gamma_value_mode", "local")).lower() not in {"local", "none", "off"}),
        gamma_mode=getattr(args, "gamma_value_mode", getattr(args, "gamma_mode", "finite_horizon")),
        gamma_horizon=getattr(args, "gamma_horizon", 4),
        gamma_discount=getattr(args, "gamma_discount", 1.0),
        gamma_value_weight=getattr(args, "gamma_value_weight", getattr(args, "gamma_tail_value_weight", 0.50)),
        gamma_stability_delta=getattr(args, "gamma_stability_delta", getattr(args, "gamma_stability_margin", 0.05)),
        gamma_tail_risk_mode=getattr(args, "gamma_tail_risk_mode", "spectral"),
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def cmd_action_cocycle_audit(args):
    summary = audit_action_cocycles(
        args.registry,
        args.compositions,
        args.out,
        summary_out=args.summary_out,
        accept_threshold=args.accept_threshold,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def cmd_arithmetic_teacher_constraints(args):
    summary = teacher_constraints_from_arithmetic_actions(args.actions, args.out, summary_out=args.summary_out)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0



def cmd_goal_state_transitions(args):
    report = goal_state_transitions_from_audits(args.audits, out_path=args.out, summary_out=getattr(args, "summary_out", None))
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


def cmd_kernel_state_graphs(args):
    report = kernel_state_graphs_from_jsonl(args.kernel_jsonl, out_path=args.out, summary_out=getattr(args, "summary_out", None))
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


def cmd_kernel_state_normalize(args):
    rows = read_jsonl(args.kernel_jsonl)
    out_rows = []
    for row in rows:
        kernel = row.get("kernel_state") if isinstance(row, dict) and isinstance(row.get("kernel_state"), dict) else row
        if isinstance(kernel, dict):
            out_rows.append(normalize_kernel_state_v1(kernel))
    write_jsonl(args.out, out_rows)
    report = {
        "schema_version": "lean-rgc-kernel-state-normalize-v1",
        "n_input_rows": len(rows),
        "n_kernel_states": len(out_rows),
        "mean_expr_nodes": sum(int((r.get("expr_graph") or {}).get("n_nodes", 0) or 0) for r in out_rows) / max(1, len(out_rows)),
        "canonical_status": "kernel_state_normalize_report_not_canonical",
        "files": {"kernel_states": str(args.out)},
    }
    if getattr(args, "summary_out", None):
        Path(args.summary_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.summary_out).write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


def cmd_kernel_state_probe(args):
    task = LeanTask.from_dict(json.loads(Path(args.task_json).read_text(encoding="utf-8")))
    action = TacticAction.from_dict(json.loads(Path(args.action_json).read_text(encoding="utf-8")))
    cfg = KernelGoalStateServerConfig(
        lean_cmd=args.lean_cmd,
        workdir=args.workdir,
        timeout_s=args.timeout_s,
        backend=args.backend,
        keep_files=bool(getattr(args, "keep_files", False)),
        cache_dir=getattr(args, "cache_dir", None),
        trace_state=bool(getattr(args, "trace_state", False)),
    )
    server = KernelGoalStateServer(cfg)
    init = server.register_task(task)
    transition = server.apply_tactic(init["state"]["state_id"], action)
    out = {"status": server.status(), "initial": init, "transition": transition}
    if getattr(args, "out", None):
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(out, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0

def cmd_structured_state_extract(args):
    summary = structured_state_extract_cli(tasks=getattr(args, "tasks", None), audits=getattr(args, "audits", None), kernel_jsonl=getattr(args, "kernel_jsonl", None), out=args.out, summary_out=getattr(args, "summary_out", None))
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def cmd_frontier_audit(args):
    tasks = _normalize_tasks_imports(_load_tasks(args.tasks), args.import_mode, args.workdir, args.lean_cmd)
    executor = _executor_from_args(args)
    summary = FrontierAuditor(executor, ProofDefectExtractor()).run(
        tasks,
        out_dir=args.out,
        max_exposures=args.max_exposures,
        max_core_actions=args.max_core_actions,
        include_identity=not args.no_identity,
    )
    print(json.dumps(summary.to_dict(), indent=2, ensure_ascii=False))
    return 0





def cmd_lean_worker(args):
    # Backward-compatible alias for the v27 persistent JSONL worker.
    from .persistent_lean_worker import main as worker_main
    argv = ["--backend", "dry_run" if args.dry_run else "file", "--lean-cmd", args.lean_cmd, "--timeout-s", str(args.timeout_s)]
    if args.workdir:
        argv += ["--workdir", args.workdir]
    if args.keep_files:
        argv += ["--keep-files"]
    if args.cache_dir:
        argv += ["--cache-dir", args.cache_dir]
    if args.trace_state:
        argv += ["--trace-state"]
    return worker_main(argv)



def cmd_lean_native_worker(args):
    from .native_worker import main as native_main
    argv = ["--lean-cmd", args.lean_cmd, "--exec-mode", getattr(args, "exec_mode", "source_check")]
    if args.workdir:
        argv += ["--workdir", args.workdir]
    if getattr(args, "worker_path", None):
        argv += ["--worker-path", args.worker_path]
    # Backward-compatible aliases from the previous source-emitting shim.
    if getattr(args, "source_path", None):
        argv += ["--worker-path", args.source_path]
    if getattr(args, "emit_source", None):
        argv += ["--source-out", args.emit_source]
    if getattr(args, "source_out", None):
        argv += ["--source-out", args.source_out]
    if getattr(args, "manifest_out", None):
        argv += ["--manifest-out", args.manifest_out]
    if getattr(args, "print_source", False):
        argv += ["--print-source"]
    if getattr(args, "print_command", False):
        argv += ["--print-command"]
    if getattr(args, "keep_source", False):
        argv += ["--keep-source"]
    if getattr(args, "force", False):
        argv += ["--force"]
    return native_main(argv)

def cmd_lean_server_probe(args):
    with _server_from_args(args) as server:
        out = server.health()
    if getattr(args, "out", None):
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0

def cmd_lean_server_health(args):
    with _server_from_args(args) as server:
        out = {"health": server.health()}
    if getattr(args, "out", None):
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


def cmd_lean_server_apply(args):
    task = LeanTask.from_dict(json.loads(Path(args.task_json).read_text(encoding="utf-8")))
    action = TacticAction.from_dict(json.loads(Path(args.action_json).read_text(encoding="utf-8")))
    state = None
    if getattr(args, "state_json", None):
        state = ProofState.from_dict(json.loads(Path(args.state_json).read_text(encoding="utf-8")))
    with _server_from_args(args) as server:
        rec = server.run_tactic(task, action, state)
        structured_state = server.structured_state(task, rec.after_state or ProofState.from_task(task), rec)
        out = {"record": rec.to_dict(), "structured_state": structured_state, "health": server.info.to_dict()}
    if getattr(args, "out", None):
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


def cmd_structured_state_extract(args):
    summary = structured_state_extract_cli(tasks=getattr(args, "tasks", None), audits=getattr(args, "audits", None), kernel_jsonl=getattr(args, "kernel_jsonl", None), out=args.out, summary_out=getattr(args, "summary_out", None))
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def cmd_frontier_audit(args):
    tasks = _normalize_tasks_imports(_load_tasks(args.tasks), args.import_mode, args.workdir, args.lean_cmd)
    executor = _executor_from_args(args)
    summary = FrontierAuditor(executor, ProofDefectExtractor()).run(
        tasks,
        out_dir=args.out,
        max_exposures=args.max_exposures,
        max_core_actions=args.max_core_actions,
        include_identity=not args.no_identity,
    )
    print(json.dumps(summary.to_dict() if hasattr(summary, 'to_dict') else summary, indent=2, ensure_ascii=False))
    return 0


def cmd_batch_audit(args):
    tasks = _normalize_tasks_imports(_load_tasks(args.tasks), args.import_mode, args.workdir, args.lean_cmd)
    base, by_task = _load_actions_grouped(args.actions)
    acts = _actions_for_tasks(tasks, base, by_task, state_candidates=args.state_candidates or not (base or by_task), candidate_mode=args.candidate_mode, max_candidates=args.max_actions)
    cfg = LeanExecutorConfig(lean_cmd=args.lean_cmd, timeout_s=args.timeout_s, dry_run=args.dry_run, keep_files=args.keep_files, workdir=args.workdir, cache_dir=args.cache_dir, trace_state=args.trace_state)
    summary = run_micro_audit_batch(tasks, acts, out_dir=args.out, executor_config=cfg, max_actions=args.max_actions, jobs=getattr(args, 'jobs', 1), resume=args.resume, flush_every=args.flush_every)
    responses = read_jsonl(Path(args.out) / 'responses.jsonl') if (Path(args.out) / 'responses.jsonl').exists() else []
    summary.update(summarize_responses(responses))
    (Path(args.out) / 'summary.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def cmd_bulk_audit(args):
    tasks = _normalize_tasks_imports(_load_tasks(args.tasks), args.import_mode, args.workdir, args.lean_cmd)
    base, by_task = _load_actions_grouped(args.actions)
    acts = _actions_for_tasks(tasks, base, by_task, state_candidates=args.state_candidates or not (base or by_task), candidate_mode=args.candidate_mode, max_candidates=args.max_actions)
    trimmed = {k: v[:args.max_actions] for k, v in acts.items()}
    cfg = BulkAuditConfig(lean_cmd=args.lean_cmd, workdir=args.workdir, timeout_s=args.timeout_s, batch_size=args.batch_size, keep_files=args.keep_files, trace_state=args.trace_state)
    rep = bulk_audit_to_files(tasks, trimmed, args.out, cfg)
    print(json.dumps(rep, indent=2, ensure_ascii=False))
    return 0


def cmd_server_audit(args):
    tasks = _normalize_tasks_imports(_load_tasks(args.tasks), args.import_mode, args.workdir, args.lean_cmd)
    base, by_task = _load_actions_grouped(args.actions)
    acts = _actions_for_tasks(tasks, base, by_task, state_candidates=args.state_candidates or not (base or by_task), candidate_mode=args.candidate_mode, max_candidates=args.max_actions)
    cfg = _server_config_from_args(args)
    summary = audit_with_lean_server(tasks, acts, out_dir=args.out, server_config=cfg, max_actions=args.max_actions, resume=args.resume, flush_every=args.flush_every)
    responses = read_jsonl(Path(args.out) / 'responses.jsonl') if (Path(args.out) / 'responses.jsonl').exists() else []
    summary.update(summarize_responses(responses))
    (Path(args.out) / 'summary.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0





def cmd_contextual_compose_actions(args):
    summary = generate_contextual_composite_actions(
        args.actions,
        args.out,
        contexts_path=getattr(args, "contexts", None),
        max_core_actions=getattr(args, "max_core_actions", None),
        max_contexts=getattr(args, "max_contexts", None),
        include_identity=not getattr(args, "no_identity", False),
        separator=getattr(args, "separator", "\n"),
    )
    if getattr(args, "summary_out", None):
        Path(args.summary_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.summary_out).write_text(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def cmd_contextual_fingerprints(args):
    summary = build_contextual_response_fingerprints(
        args.responses,
        args.out,
        summary_out=getattr(args, "summary_out", None),
        min_audits=getattr(args, "min_audits", 1),
        normalize=not getattr(args, "no_normalize", False),
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def cmd_contextual_congruence(args):
    report = contextual_congruence_from_files(
        args.responses,
        args.out,
        cosine_threshold=getattr(args, "cosine_threshold", 0.95),
        distance_threshold=getattr(args, "distance_threshold", None),
        min_audits=getattr(args, "min_audits", 1),
        min_members=getattr(args, "min_members", 1),
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


def cmd_action_classes_to_registry(args):
    summary = action_classes_to_registry(args.classes, args.out, out_actions=getattr(args, "out_actions", None))
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def cmd_contextual_candidates(args):
    rows, summary = generate_contextual_candidates(
        args.actions,
        args.out,
        contexts_path=getattr(args, "contexts", None),
        max_left=getattr(args, "max_left", 8),
        max_right=getattr(args, "max_right", 8),
        max_core=getattr(args, "max_core", None),
        max_candidates=getattr(args, "max_candidates", None),
        include_identity=not getattr(args, "no_identity", False),
        include_left=not getattr(args, "no_left", False),
        include_right=not getattr(args, "no_right", False),
    )
    if getattr(args, "summary_out", None):
        Path(args.summary_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.summary_out).write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def cmd_contextual_congruence(args):
    report = contextual_congruence_from_files(
        args.responses,
        args.out,
        actions_path=getattr(args, "actions", None),
        min_contexts=getattr(args, "min_contexts", 1),
        cosine_threshold=getattr(args, "cosine_threshold", 0.95),
        l2_threshold=getattr(args, "max_distance", None),
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0





def cmd_carrier_quotient_mine(args):
    return cmd_carrier_quotient(args)

def cmd_carrier_quotient(args):
    summary = carrier_quotient_from_files(
        args.responses,
        args.out,
        ridge=getattr(args, "ridge", 1e-4),
        max_mass=getattr(args, "max_mass", 1.0),
        cosine_threshold=getattr(args, "cosine_threshold", 0.85),
        min_states=getattr(args, "min_states", 1),
        top_action_scores=getattr(args, "top_action_scores", 128),
        margin_threshold=getattr(args, "margin_threshold", 0.0),
        validate=getattr(args, "validate", False),
        registry=not getattr(args, "no_registry", False),
        incidence=not getattr(args, "no_incidence", False),
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def cmd_carrier_quotient_validate(args):
    summary = validate_carrier_quotient_coordinates(
        args.responses,
        args.coordinates,
        out_rows=args.out_rows,
        out_report=args.out_report,
        min_support_score=getattr(args, "min_support_score", 0.0),
        over_refinement_ratio=getattr(args, "over_refinement_ratio", 2.0),
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0

def cmd_quotient_coordinates(args):
    report = run_quotient_coordinate_loop(
        responses=args.responses,
        out_dir=args.out,
        ridge=args.ridge,
        max_mass=args.max_mass,
        cosine_threshold=args.cosine_threshold,
        min_states=args.min_states,
        top_action_scores=args.top_action_scores,
        margin_threshold=args.margin_threshold,
        registry=not getattr(args, "no_registry", False),
        validate=getattr(args, "validate", False),
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


def cmd_quotient_coordinate_validate(args):
    summary = validate_quotient_coordinates(
        args.responses,
        args.coordinates,
        out_report=args.out_report,
        out_rows=args.out_rows,
        holdout_fraction=getattr(args, "holdout_fraction", 0.35),
        min_support_score=getattr(args, "min_support_score", 0.0),
        over_refinement_ratio=getattr(args, "over_refinement_ratio", 2.0),
    )
    print(json.dumps({"summary": summary, "out_report": args.out_report, "out_rows": args.out_rows}, indent=2, ensure_ascii=False))
    return 0


def cmd_contextual_response_congruence(args):
    report = contextual_response_congruence_from_files(
        args.responses,
        args.out,
        context_mode=getattr(args, "context_mode", "state"),
        include_carrier=not getattr(args, "no_carrier", False),
        min_count=getattr(args, "min_count", 1),
        cosine_threshold=getattr(args, "cosine_threshold", 0.95),
        distance_threshold=getattr(args, "distance_threshold", 0.25),
        min_context_jaccard=getattr(args, "min_context_jaccard", 0.0),
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0



def cmd_carrier_quotient(args):
    summary = carrier_quotient_from_files(
        args.responses,
        args.out,
        ridge=args.ridge,
        max_mass=args.max_mass,
        cosine_threshold=args.cosine_threshold,
        min_states=args.min_states,
        top_action_scores=args.top_action_scores,
        margin_threshold=args.margin_threshold,
        validate=getattr(args, 'validate', False),
        registry=not getattr(args, 'no_registry', False),
        normal=not getattr(args, 'no_normal', False),
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def cmd_carrier_quotient_validate(args):
    summary = validate_carrier_quotient_coordinates(
        args.responses,
        args.coordinates,
        out_rows=args.out_rows,
        out_report=args.out_report,
        min_support_score=args.min_support_score,
        over_refinement_ratio=args.over_refinement_ratio,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0



# Backward-compatible alias for older v34/v33 parser hooks.
cmd_carrier_quotient_mine = cmd_carrier_quotient
cmd_carrier_quotient_mining = cmd_carrier_quotient

def cmd_response_quotient_registry(args):
    if getattr(args, "congruence_dir", None):
        report = response_quotient_from_congruence_dir(
            args.congruence_dir,
            actions_path=getattr(args, "actions", None),
            out_dir=args.out,
            min_members=getattr(args, "min_members", 1),
            min_quality=getattr(args, "min_quality", None),
        )
    else:
        report = build_response_quotient_registry(
            args.classes,
            actions_path=getattr(args, "actions", None),
            out_dir=args.out,
            min_members=getattr(args, "min_members", 1),
            min_quality=getattr(args, "min_quality", None),
        )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


def cmd_response_quotient_project_actions(args):
    report = project_actions_by_response_quotient(
        args.actions,
        args.registry,
        args.out,
        keep_unmapped=not getattr(args, "drop_unmapped", False),
        annotate_only=getattr(args, "annotate_only", False),
    )
    if getattr(args, "summary_out", None):
        Path(args.summary_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.summary_out).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0



def cmd_lean_persistent_worker(args: argparse.Namespace) -> int:
    cfg = LeanServerConfig(
        lean_cmd=getattr(args, "lean_cmd", "lake env lean"),
        workdir=getattr(args, "workdir", None),
        timeout_s=float(getattr(args, "timeout_s", 20.0)),
        dry_run=bool(getattr(args, "dry_run", False)),
        keep_files=bool(getattr(args, "keep_files", False)),
        cache_dir=getattr(args, "cache_dir", None),
        trace_state=bool(getattr(args, "trace_state", False)),
        backend="persistent",
    )
    return run_persistent_worker(cfg)


def cmd_lean_persistent_probe(args: argparse.Namespace) -> int:
    cfg = LeanServerConfig(
        lean_cmd=getattr(args, "lean_cmd", "lake env lean"),
        workdir=getattr(args, "workdir", None),
        timeout_s=float(getattr(args, "timeout_s", 20.0)),
        dry_run=bool(getattr(args, "dry_run", False)),
        keep_files=bool(getattr(args, "keep_files", False)),
        cache_dir=getattr(args, "cache_dir", None),
        trace_state=bool(getattr(args, "trace_state", False)),
    )
    worker = PersistentLeanWorker(cfg)
    status = worker.load_project()
    task = LeanTask.from_dict({"task_id":"persistent_probe", "statement":"∀ n : Nat, n = n", "imports":["Init"]})
    init = worker.init_state(task)
    intro = TacticAction(action_id="intro", tactic="intro n", tactic_class="intro")
    r1 = worker.apply_tactic(task, intro, state_id=init["state"]["state_id"])
    branch = worker.branch_state(r1.get("after_state", init["state"])["state_id"] if r1.get("after_state") else init["state"]["state_id"])
    rfl = TacticAction(action_id="rfl", tactic="rfl", tactic_class="rfl")
    r2 = worker.apply_tactic(task, rfl, state_id=branch["state"]["state_id"])
    out = {
        "status": status,
        "init_state": init["state"],
        "intro_status": (r1.get("audit") or {}).get("status"),
        "branch_state": branch.get("state"),
        "rfl_status": (r2.get("audit") or {}).get("status"),
        "n_states": len(worker.states),
        "canonical_status": "persistent_worker_probe_chart_only_not_kernel_canonical",
    }
    if getattr(args, "out", None):
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


def add_response_quotient_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument('--response-quotient-registry', action='store_true', help='Build a finite action response-quotient registry from contextual congruence classes.')
    parser.add_argument('--response-quotient-min-members', type=int, default=1)
    parser.add_argument('--response-quotient-min-quality', type=float)
    parser.add_argument('--response-quotient-project-actions', action='store_true', help='Project/deduplicate the input action file through the finite response-quotient registry.')
    parser.add_argument('--response-quotient-annotate-only', action='store_true', help='Keep all actions but annotate them with quotient class metadata instead of deduplicating.')
    parser.add_argument('--response-quotient-merge-actions', action='store_true', help='In iterate, merge response-quotient representatives/projected actions into the next action pool.')
    parser.add_argument('--response-quotient-merge-policy', choices=['representatives','projected','all'], default='representatives')


def add_contextual_probe_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument('--contextual-probes', action='store_true', help='Generate finite A∘C∘B contextual probe candidates from the current action pool.')
    parser.add_argument('--contextual-probe-contexts', help='Optional JSONL actions used as left/right contexts; defaults to --actions.')
    parser.add_argument('--contextual-probe-max-left', type=int, default=4)
    parser.add_argument('--contextual-probe-max-right', type=int, default=4)
    parser.add_argument('--contextual-probe-max-core', type=int)
    parser.add_argument('--contextual-probe-max-candidates', type=int, default=128)
    parser.add_argument('--contextual-probe-no-identity', action='store_true')
    parser.add_argument('--contextual-probe-no-left', action='store_true')
    parser.add_argument('--contextual-probe-no-right', action='store_true')
    parser.add_argument('--audit-contextual-probe-candidates', action='store_true')
    parser.add_argument('--contextual-probe-audit-max-actions', type=int, default=24)
    parser.add_argument('--contextual-probe-congruence', action='store_true')
    parser.add_argument('--contextual-probe-congruence-context-mode', choices=['state','task','global'], default='state')
    parser.add_argument('--contextual-probe-congruence-no-carrier', action='store_true')
    parser.add_argument('--contextual-probe-congruence-min-count', type=int, default=1)
    parser.add_argument('--contextual-probe-congruence-cosine-threshold', type=float, default=0.95)
    parser.add_argument('--contextual-probe-congruence-distance-threshold', type=float, default=0.25)
    parser.add_argument('--contextual-probe-congruence-min-context-jaccard', type=float, default=0.0)
    parser.add_argument('--contextual-probe-accept-coker', action='store_true')
    parser.add_argument('--contextual-probe-robust-coker-accept', action='store_true')
    parser.add_argument('--contextual-probe-accept-margin', type=float, default=0.0)
    parser.add_argument('--contextual-probe-accept-max-per-task', type=int, default=16)
    parser.add_argument('--contextual-probe-accept-cost-weight', type=float, default=0.05)
    parser.add_argument('--contextual-probe-accept-carrier-weight', type=float, default=0.7)
    parser.add_argument('--contextual-probe-robust-coker-holdout-fraction', type=float, default=0.35)
    parser.add_argument('--contextual-probe-robust-coker-uncertainty-weight', type=float, default=0.10)
    parser.add_argument('--contextual-probe-robust-coker-carrier-gain-weight', type=float, default=0.25)
    parser.add_argument('--contextual-probe-robust-coker-audit-penalty', type=float, default=1.0)
    parser.add_argument('--contextual-probe-robust-coker-require-success', action='store_true')
    parser.add_argument('--contextual-probe-merge-actions', action='store_true')
    parser.add_argument('--contextual-probe-merge-policy', choices=['all','robust-only','accepted-only'], default='robust-only')


def add_premise_contextual_pipeline_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument('--premise-contextual-quotient', action='store_true')
    parser.add_argument('--premise-contextual-generate', action='store_true')
    parser.add_argument('--premise-contextual-bivariate', action='store_true')
    parser.add_argument('--premise-contextual-contexts')
    parser.add_argument('--separator-contexts-builtin', choices=['builtin_core','core'], default='builtin_core')
    parser.add_argument('--premise-use-rows-out')
    parser.add_argument('--separator-contexts-out')
    parser.add_argument('--premise-contextual-max-premises', type=int)
    parser.add_argument('--premise-contextual-max-left', type=int, default=4)
    parser.add_argument('--premise-contextual-max-right', type=int, default=4)
    parser.add_argument('--premise-contextual-max-candidates', type=int)
    parser.add_argument('--premise-contextual-baseline-required', action='store_true')
    parser.add_argument('--audit-premise-contextual-candidates', action='store_true')
    parser.add_argument('--premise-contextual-audit-max-actions', type=int, default=32)
    parser.add_argument('--bivariate-audit-budget', type=int)
    parser.add_argument('--bivariate-require-baseline-pairs', action='store_true')
    parser.add_argument('--skip-vacuous-premise-quotient', action='store_true')
    parser.add_argument('--repair-face-ledger', action='store_true')
    parser.add_argument('--premise-contextual-mine', action='store_true')
    parser.add_argument('--premise-contextual-validate', action='store_true')
    parser.add_argument('--premise-contextual-epsilon', type=float, default=0.25)
    parser.add_argument('--premise-contextual-cosine-threshold', type=float, default=0.95)
    parser.add_argument('--premise-contextual-domain-jaccard-threshold', type=float, default=0.0)
    parser.add_argument('--premise-contextual-epsilon-holdout', type=float, default=0.35)
    parser.add_argument('--premise-contextual-separation-delta', type=float, default=0.10)
    parser.add_argument('--premise-quotient-retrieve', action='store_true')
    parser.add_argument('--premise-quotient-top-k', type=int, default=32)
    parser.add_argument('--audit-premise-quotient-candidates', action='store_true')
    parser.add_argument('--premise-quotient-audit-max-actions', type=int, default=16)



def cmd_source_budget_schedule(args):
    response_normal = _read_source_budget_json_or_file(getattr(args, "response_normal", None) or getattr(args, "response_normal_json", None))
    carrier_normal = _read_source_budget_json_or_file(getattr(args, "carrier_normal", None) or getattr(args, "carrier_normal_json", None))
    cfg = SourceBudgetConfig(
        total_budget=getattr(args, "budget", 64),
        min_per_source=getattr(args, "min_per_source", 0),
        max_per_source=getattr(args, "max_per_source", None),
        per_task_cap=getattr(args, "per_task_cap", None),
        per_action_cap=getattr(args, "per_action_cap", 1),
        source_exploration_weight=getattr(args, "source_exploration_weight", 0.25),
        source_fairness_power=getattr(args, "source_fairness_power", 0.5),
        coker_weight=getattr(args, "coker_weight", 1.0),
        carrier_weight=getattr(args, "carrier_weight", 0.5),
        uncertainty_weight=getattr(args, "uncertainty_weight", 0.25),
        novelty_weight=getattr(args, "novelty_weight", 0.15),
        success_weight=getattr(args, "success_weight", 0.25),
        cost_weight=getattr(args, "cost_weight", 0.10),
        timeout_weight=getattr(args, "timeout_weight", 0.50),
        min_score=getattr(args, "min_score", None),
        score_metric=getattr(args, "score_metric", "score_per_cost"),
        gamma_aware=getattr(args, "gamma_aware", False),
        gamma_mode=getattr(args, "gamma_value_mode", "finite_horizon"),
        gamma_horizon=getattr(args, "gamma_horizon", 4),
        gamma_discount=getattr(args, "gamma_discount", 1.0),
        gamma_value_weight=getattr(args, "gamma_value_weight", 0.50),
        gamma_tail_value_weight=getattr(args, "gamma_tail_value_weight", None),
        gamma_tail_risk_weight=getattr(args, "gamma_tail_risk_weight", 0.50),
        gamma_tail_radius_weight=getattr(args, "gamma_tail_radius_weight", 0.0),
        gamma_stability_delta=getattr(args, "gamma_stability_delta", 0.05),
        gamma_tail_risk_mode=getattr(args, "gamma_tail_risk_mode", "spectral"),
    )
    report = source_budget_schedule_from_files(
        candidate_specs=list((getattr(args, "candidates", None) or getattr(args, "source", None) or [])),
        run_dir=getattr(args, "run_dir", None),
        out_actions=getattr(args, "out_actions"),
        out_rows=getattr(args, "out_rows", None),
        out_report=getattr(args, "out_report", None),
        db_path=getattr(args, "db", None),
        response_paths=list(getattr(args, "history_responses", []) or []),
        lineage_paths=list(getattr(args, "lineage", []) or []),
        response_normal=response_normal,
        carrier_normal=carrier_normal,
        config=cfg,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0

def cmd_active_audit_schedule(args):
    response_normal = _read_json_or_file(getattr(args, "response_normal", None) or getattr(args, "response_normal_json", None))
    carrier_normal = _read_json_or_file(getattr(args, "carrier_normal", None) or getattr(args, "carrier_normal_json", None))
    candidates = list(getattr(args, "candidates", []) or [])
    if not candidates:
        raise SystemExit("--candidates is required")
    if len(candidates) > 1:
        # Merge multiple candidate files to a temporary JSONL next to the output.
        from .schemas import read_jsonl, write_jsonl
        merged = []
        for path in candidates:
            merged.extend(read_jsonl(path))
        tmp = Path(args.out_actions).parent / "active_audit_candidates_merged.jsonl"
        write_jsonl(tmp, merged)
        candidates_path = tmp
    else:
        candidates_path = candidates[0]
    cfg = SchedulerConfig(
        top_k=getattr(args, "budget", 32),
        per_task_cap=getattr(args, "per_task_cap", None),
        response_weight=getattr(args, "coker_weight", 1.0),
        carrier_weight=getattr(args, "carrier_weight", 0.5),
        uncertainty_weight=getattr(args, "uncertainty_weight", 0.25),
        novelty_weight=getattr(args, "novelty_weight", 0.25),
        success_weight=getattr(args, "success_weight", 0.25),
        cost_weight=getattr(args, "cost_weight", 1.0),
        timeout_weight=getattr(args, "timeout_weight", 0.5),
        min_score=getattr(args, "min_priority", None),
    )
    report = active_audit_schedule_from_files(
        candidates_path=candidates_path,
        out_actions=args.out_actions,
        out_rows=args.out_schedule,
        out_report=args.out_report,
        db_path=getattr(args, "db", None),
        response_paths=list(getattr(args, "history_responses", []) or []),
        response_normal=response_normal,
        carrier_normal=carrier_normal,
        config=cfg,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0



def cmd_defect_ontology_reconcile(args):
    res = reconcile_defect_ontology(
        base_registry=getattr(args, "base_registry", None),
        candidate_atom_paths=getattr(args, "candidate_atoms", []) or [],
        run_dir=getattr(args, "run_dir", None),
        out_dir=args.out,
        merge_threshold=args.merge_threshold,
        shadow_threshold=args.shadow_threshold,
        novel_threshold=args.novel_threshold,
        include_open_in_registry=args.include_open,
        include_shadow_in_registry=args.include_shadow,
    )
    print(json.dumps(res, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


def cmd_defect_ontology_lifecycle(args):
    res = run_defect_ontology_lifecycle(
        run_dir=getattr(args, "run_dir", None),
        out_dir=args.out,
        reconciliation_rows=getattr(args, "reconciliation_rows", None),
        split_suggestions=getattr(args, "split_suggestions", None),
        base_registry=getattr(args, "base_registry", None),
        reconciled_registry=getattr(args, "reconciled_registry", None),
        previous_lifecycle_rows=getattr(args, "previous_lifecycle", []) or [],
        promotion_rows=getattr(args, "promotion_rows", []) or [],
        validation_rows=getattr(args, "validation_rows", []) or [],
        min_evidence_score=args.min_evidence_score,
        min_support_count=args.min_support_count,
        include_pending_in_registry=args.include_pending,
    )
    print(json.dumps(res, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


def cmd_arithmetic_teacher_graph(args):
    rep = generate_arithmetic_teacher_graph(
        args.structured_states,
        args.out,
        identities_path=args.identities,
        actions_path=args.actions,
        responses_path=args.responses,
        max_transforms_per_state=args.max_transforms_per_state,
        emit_candidate_actions=not args.no_actions,
    )
    print(json.dumps(rep, indent=2, ensure_ascii=False))
    return 0


def cmd_arithmetic_teacher_audit(args):
    rep = audit_arithmetic_teacher_transitions(
        args.transformations,
        args.structured_states,
        args.out_rows,
        report_out=args.report_out,
    )
    print(json.dumps(rep, indent=2, ensure_ascii=False))
    return 0


def cmd_arithmetic_teacher_kernel_audit(args):
    cfg = LeanServerConfig(
        lean_cmd=args.lean_cmd,
        workdir=args.workdir,
        timeout_s=args.timeout_s,
        dry_run=args.dry_run,
        keep_files=args.keep_files,
        cache_dir=args.cache_dir,
        trace_state=args.trace_state,
        server_cmd=args.server_cmd,
        backend=args.server_backend,
        fallback_to_file=not args.server_no_fallback,
        native_exec_mode=args.native_exec_mode,
    )
    rep = audit_arithmetic_teacher_kernel_transitions(
        args.transformations,
        args.tasks,
        args.out,
        identities_path=args.identities,
        structured_states_path=args.structured_states,
        server_config=cfg,
        max_transitions=args.max_transitions,
    )
    print(json.dumps(rep, indent=2, ensure_ascii=False))
    return 0


def cmd_arithmetic_teacher_cocycle(args):
    rep = arithmetic_teacher_cocycle_from_files(
        args.kernel_audit_rows,
        args.out,
        compositions_path=args.compositions,
        min_count=args.min_count,
        accept_threshold=args.accept_threshold,
        min_verified_rate=args.min_verified_rate,
        max_tail_radius=args.max_tail_radius,
        max_auto_pairs=args.max_auto_pairs,
    )
    print(json.dumps(rep, indent=2, ensure_ascii=False))
    return 0

def cmd_arithmetic_teacher_transition_geometry(args):
    rep = build_arithmetic_teacher_transition_geometry(
        args.kernel_audit_rows,
        args.out,
        summary_out=args.summary_out,
        min_count=args.min_count,
    )
    print(json.dumps(rep, indent=2, ensure_ascii=False))
    return 0

def cmd_arithmetic_teacher_cocycle_audit(args):
    rep = audit_arithmetic_teacher_cocycles(
        args.transition_geometry,
        args.out,
        summary_out=args.summary_out,
        compositions_path=args.compositions,
        accept_threshold=args.accept_threshold,
        min_verified_rate=args.min_verified_rate,
        max_tail_radius=args.max_tail_radius,
        max_auto_pairs=args.max_auto_pairs,
    )
    if args.gamma_constraints_out:
        write_arithmetic_teacher_gamma_constraints(args.out, args.gamma_constraints_out, summary_out=args.gamma_constraints_summary_out)
    print(json.dumps(rep, indent=2, ensure_ascii=False))
    return 0

def build_parser() -> argparse.ArgumentParser:
    p=argparse.ArgumentParser(prog='lean-rgc', description='Lean-RGC automation stack')
    sub=p.add_subparsers(dest='cmd', required=True)
    def add_exec_args(a):
        a.add_argument('--lean-cmd', default='lake env lean'); a.add_argument('--workdir'); a.add_argument('--timeout-s', type=float, default=20.0); a.add_argument('--dry-run', action='store_true'); a.add_argument('--keep-files', action='store_true'); a.add_argument('--cache-dir'); a.add_argument('--trace-state', action='store_true'); a.add_argument('--import-mode', choices=['preserve','auto','core','mathlib'], default='auto'); a.add_argument('--lean-server', action='store_true'); a.add_argument('--lean-server-backend', choices=['auto','dry_run','file_fallback','file','dry','jsonl','persistent','native'], default=None); a.add_argument('--resume', action='store_true'); a.add_argument('--flush-every', type=int, default=50); a.add_argument('--max-actions', type=int, default=64); a.add_argument('--candidate-mode', choices=['basic','state'], default='state'); a.add_argument('--state-candidates', action='store_true')
    a=sub.add_parser('audit'); a.add_argument('--tasks', required=True); a.add_argument('--actions'); a.add_argument('--out', required=True); add_exec_args(a); a.set_defaults(func=cmd_audit)
    lsh=sub.add_parser('lean-server-health'); lsh.add_argument('--out'); lsh.add_argument('--lean-cmd', default='lake env lean'); lsh.add_argument('--workdir'); lsh.add_argument('--timeout-s', type=float, default=20.0); lsh.add_argument('--dry-run', action='store_true'); lsh.add_argument('--keep-files', action='store_true'); lsh.add_argument('--cache-dir'); lsh.add_argument('--trace-state', action='store_true'); lsh.add_argument('--server-cmd'); lsh.add_argument('--server-no-fallback', action='store_true'); lsh.add_argument('--lean-server-backend', choices=['file','dry','jsonl','persistent','native'], default=None); lsh.set_defaults(func=cmd_lean_server_health)
    lsa=sub.add_parser('lean-server-apply'); lsa.add_argument('--task-json', required=True); lsa.add_argument('--action-json', required=True); lsa.add_argument('--state-json'); lsa.add_argument('--out'); lsa.add_argument('--lean-cmd', default='lake env lean'); lsa.add_argument('--workdir'); lsa.add_argument('--timeout-s', type=float, default=20.0); lsa.add_argument('--dry-run', action='store_true'); lsa.add_argument('--keep-files', action='store_true'); lsa.add_argument('--cache-dir'); lsa.add_argument('--trace-state', action='store_true'); lsa.add_argument('--server-cmd'); lsa.add_argument('--server-no-fallback', action='store_true'); lsa.add_argument('--native-exec-mode', choices=['source_check','heuristic','kernel_rpc'], default='source_check'); lsa.add_argument('--request-timeout-s', type=float); lsa.add_argument('--lean-server-backend', choices=['auto','dry_run','file_fallback','file','dry','jsonl','persistent','native'], default=None); lsa.set_defaults(func=cmd_lean_server_apply)
    fa=sub.add_parser('frontier-audit'); fa.add_argument('--tasks', required=True); fa.add_argument('--out', required=True); fa.add_argument('--lean-cmd', default='lake env lean'); fa.add_argument('--workdir'); fa.add_argument('--timeout-s', type=float, default=20.0); fa.add_argument('--dry-run', action='store_true'); fa.add_argument('--keep-files', action='store_true'); fa.add_argument('--cache-dir'); fa.add_argument('--trace-state', action='store_true'); fa.add_argument('--import-mode', choices=['preserve','auto','core','mathlib'], default='auto'); fa.add_argument('--max-exposures', type=int, default=4); fa.add_argument('--max-core-actions', type=int, default=12); fa.add_argument('--no-identity', action='store_true'); fa.set_defaults(func=cmd_frontier_audit)
    ba=sub.add_parser('batch-audit'); ba.add_argument('--tasks', required=True); ba.add_argument('--actions'); ba.add_argument('--out', required=True); ba.add_argument('--jobs', type=int, default=4); add_exec_args(ba); ba.set_defaults(func=cmd_batch_audit)
    bu=sub.add_parser('bulk-audit'); bu.add_argument('--tasks', required=True); bu.add_argument('--actions'); bu.add_argument('--out', required=True); bu.add_argument('--batch-size', type=int, default=64); bu.add_argument('--lean-cmd', default='lake env lean'); bu.add_argument('--workdir'); bu.add_argument('--timeout-s', type=float, default=120.0); bu.add_argument('--keep-files', action='store_true'); bu.add_argument('--trace-state', action='store_true'); bu.add_argument('--import-mode', choices=['preserve','auto','core','mathlib'], default='auto'); bu.add_argument('--max-actions', type=int, default=64); bu.add_argument('--candidate-mode', choices=['basic','state'], default='state'); bu.add_argument('--state-candidates', action='store_true'); bu.set_defaults(func=cmd_bulk_audit)
    lw=sub.add_parser('lean-worker'); lw.add_argument('--lean-cmd', default='lake env lean'); lw.add_argument('--workdir'); lw.add_argument('--timeout-s', type=float, default=20.0); lw.add_argument('--dry-run', action='store_true'); lw.add_argument('--keep-files', action='store_true'); lw.add_argument('--cache-dir'); lw.add_argument('--trace-state', action='store_true'); lw.add_argument('--session-id'); lw.set_defaults(func=cmd_lean_worker)

    lpw=sub.add_parser('lean-persistent-worker'); lpw.add_argument('--lean-cmd', default='lake env lean'); lpw.add_argument('--workdir'); lpw.add_argument('--timeout-s', type=float, default=20.0); lpw.add_argument('--dry-run', action='store_true'); lpw.add_argument('--keep-files', action='store_true'); lpw.add_argument('--cache-dir'); lpw.add_argument('--trace-state', action='store_true'); lpw.set_defaults(func=cmd_lean_persistent_worker)
    lpp=sub.add_parser('lean-persistent-probe'); lpp.add_argument('--out'); lpp.add_argument('--lean-cmd', default='lake env lean'); lpp.add_argument('--workdir'); lpp.add_argument('--timeout-s', type=float, default=20.0); lpp.add_argument('--dry-run', action='store_true'); lpp.add_argument('--keep-files', action='store_true'); lpp.add_argument('--cache-dir'); lpp.add_argument('--trace-state', action='store_true'); lpp.set_defaults(func=cmd_lean_persistent_probe)

    lnw=sub.add_parser('lean-native-worker'); lnw.add_argument('--lean-cmd', default='lake env lean'); lnw.add_argument('--exec-mode', choices=['source_check','heuristic','kernel_rpc'], default='source_check'); lnw.add_argument('--workdir'); lnw.add_argument('--worker-path'); lnw.add_argument('--source-path'); lnw.add_argument('--emit-source'); lnw.add_argument('--source-out'); lnw.add_argument('--manifest-out'); lnw.add_argument('--print-source', action='store_true'); lnw.add_argument('--print-command', action='store_true'); lnw.add_argument('--keep-source', action='store_true'); lnw.add_argument('--force', action='store_true'); lnw.set_defaults(func=cmd_lean_native_worker)
    nlw=sub.add_parser('native-lean-worker'); nlw.add_argument('--lean-cmd', default='lake env lean'); nlw.add_argument('--exec-mode', choices=['source_check','heuristic','kernel_rpc'], default='source_check'); nlw.add_argument('--workdir'); nlw.add_argument('--worker-path'); nlw.add_argument('--source-out'); nlw.add_argument('--manifest-out'); nlw.add_argument('--print-source', action='store_true'); nlw.add_argument('--print-command', action='store_true'); nlw.add_argument('--keep-source', action='store_true'); nlw.add_argument('--force', action='store_true'); nlw.set_defaults(func=cmd_lean_native_worker)

    srvp=sub.add_parser('lean-server-probe'); srvp.add_argument('--out'); srvp.add_argument('--lean-cmd', default='lake env lean'); srvp.add_argument('--workdir'); srvp.add_argument('--timeout-s', type=float, default=20.0); srvp.add_argument('--dry-run', action='store_true'); srvp.add_argument('--keep-files', action='store_true'); srvp.add_argument('--cache-dir'); srvp.add_argument('--trace-state', action='store_true'); srvp.add_argument('--server-cmd'); srvp.add_argument('--server-backend', choices=['auto','dry_run','file','file_fallback','jsonl','persistent','native'], default='auto'); srvp.add_argument('--server-no-fallback', action='store_true'); srvp.add_argument('--native-exec-mode', choices=['source_check','heuristic','kernel_rpc'], default='source_check'); srvp.set_defaults(func=cmd_lean_server_probe)
    sa=sub.add_parser('server-audit'); sa.add_argument('--tasks', required=True); sa.add_argument('--actions'); sa.add_argument('--out', required=True); sa.add_argument('--jobs', type=int, default=1); add_exec_args(sa); sa.set_defaults(func=cmd_server_audit)
    lsa=sub.add_parser('lean-server-audit'); lsa.add_argument('--tasks', required=True); lsa.add_argument('--actions'); lsa.add_argument('--out', required=True); lsa.add_argument('--jobs', type=int, default=1, help='Reserved for future multi-worker server backend; current adapter is sequential.'); lsa.add_argument('--server-backend', choices=['auto','dry_run','file_fallback','file','dry','jsonl','persistent','native'], default=None); lsa.add_argument('--server-cmd'); lsa.add_argument('--server-no-fallback', action='store_true'); lsa.add_argument('--native-exec-mode', choices=['source_check','heuristic','kernel_rpc'], default='source_check'); lsa.add_argument('--request-timeout-s', type=float); lsa.add_argument('--no-warmup', action='store_true'); add_exec_args(lsa); lsa.set_defaults(func=cmd_lean_server_audit)
    pw=sub.add_parser('persistent-worker'); pw.add_argument('--backend', choices=['dry_run','dry','file'], default='dry_run'); pw.add_argument('--lean-cmd', default='lake env lean'); pw.add_argument('--workdir'); pw.add_argument('--timeout-s', type=float, default=20.0); pw.add_argument('--keep-files', action='store_true'); pw.add_argument('--cache-dir'); pw.add_argument('--trace-state', action='store_true'); pw.add_argument('--no-warmup', action='store_true'); pw.set_defaults(func=cmd_persistent_worker)
    psd=sub.add_parser('persistent-state-demo'); psd.add_argument('--task-json', required=True); psd.add_argument('--actions', required=True); psd.add_argument('--out', required=True); psd.add_argument('--lean-cmd', default='lake env lean'); psd.add_argument('--workdir'); psd.add_argument('--timeout-s', type=float, default=20.0); psd.add_argument('--dry-run', action='store_true'); psd.add_argument('--keep-files', action='store_true'); psd.add_argument('--trace-state', action='store_true'); psd.add_argument('--max-actions', type=int, default=8); psd.set_defaults(func=cmd_persistent_state_demo)
    cand=sub.add_parser('candidates'); cand.add_argument('--tasks', required=True); cand.add_argument('--out', required=True); cand.add_argument('--max-candidates', type=int, default=64); cand.add_argument('--candidate-mode', choices=['basic','state'], default='state'); cand.add_argument('--import-mode', choices=['preserve','auto','core','mathlib'], default='preserve'); cand.set_defaults(func=cmd_candidates)
    rc=sub.add_parser('registry-candidates'); rc.add_argument('--tasks', required=True); rc.add_argument('--registry', required=True); rc.add_argument('--out', required=True); rc.add_argument('--max-candidates', type=int, default=96); rc.add_argument('--registry-only', action='store_true'); rc.add_argument('--import-mode', choices=['preserve','auto','core','mathlib'], default='preserve'); rc.set_defaults(func=cmd_registry_candidates)
    bpi=sub.add_parser('build-premise-index'); bpi.add_argument('--tasks'); bpi.add_argument('--actions'); bpi.add_argument('--out', required=True); bpi.set_defaults(func=cmd_build_premise_index)
    pretr=sub.add_parser('premise-retrieve'); pretr.add_argument('--index', required=True); pretr.add_argument('--out', required=True); pretr.add_argument('--query'); pretr.add_argument('--tasks'); pretr.add_argument('--states'); pretr.add_argument('--k', type=int, default=10); pretr.add_argument('--kind'); pretr.add_argument('--import-mode', choices=['preserve','auto','core','mathlib'], default='preserve'); pretr.set_defaults(func=cmd_premise_retrieve)
    pact=sub.add_parser('premise-actions'); pact.add_argument('--hits', required=True); pact.add_argument('--out', required=True); pact.add_argument('--task-id'); pact.add_argument('--max-actions-per-query', type=int, default=8); pact.set_defaults(func=cmd_premise_actions)
    pc=sub.add_parser('premise-candidates'); pc.add_argument('--tasks', required=True); pc.add_argument('--index', required=True); pc.add_argument('--out', required=True); pc.add_argument('--top-k', type=int, default=8); pc.add_argument('--max-actions', type=int, default=48); pc.set_defaults(func=cmd_premise_candidates)
    prr=sub.add_parser('premise-response-registry'); prr.add_argument('--responses', required=True); prr.add_argument('--actions'); prr.add_argument('--out', required=True); prr.add_argument('--summary-out'); prr.add_argument('--min-count', type=int, default=1); prr.set_defaults(func=cmd_premise_response_registry)
    prret=sub.add_parser('premise-response-retrieve'); prret.add_argument('--registry', required=True); prret.add_argument('--out', required=True); prret.add_argument('--summary-out'); prret.add_argument('--out-actions'); prret.add_argument('--response-normal'); prret.add_argument('--response-normal-json'); prret.add_argument('--carrier-normal'); prret.add_argument('--carrier-normal-json'); prret.add_argument('--top-k', type=int); prret.add_argument('--cost-weight', type=float, default=0.05); prret.add_argument('--uncertainty-weight', type=float, default=0.10); prret.add_argument('--audit-weight', type=float, default=0.20); prret.add_argument('--carrier-safe', action='store_true'); prret.add_argument('--carrier-budget', type=float, default=0.0); prret.set_defaults(func=cmd_premise_response_retrieve)
    pqm=sub.add_parser('premise-quotient-mine'); pqm.add_argument('--registry', required=True); pqm.add_argument('--out', required=True); pqm.add_argument('--cosine-threshold', type=float, default=0.95); pqm.add_argument('--distance-threshold', type=float, default=0.25); pqm.add_argument('--no-carrier', action='store_true'); pqm.set_defaults(func=cmd_premise_quotient_mine)
    pcg=sub.add_parser('premise-contextual-generate'); pcg.add_argument('--premise-actions'); pcg.add_argument('--actions'); pcg.add_argument('--contexts'); pcg.add_argument('--out', required=True); pcg.add_argument('--summary-out'); pcg.add_argument('--max-premises', type=int); pcg.add_argument('--max-left', type=int, default=4); pcg.add_argument('--max-right', type=int, default=4); pcg.add_argument('--max-candidates', type=int); pcg.add_argument('--no-identity', action='store_true'); pcg.add_argument('--no-baselines', action='store_true'); pcg.set_defaults(func=cmd_premise_contextual_generate)
    pcf=sub.add_parser('premise-contextual-fingerprints'); pcf.add_argument('--responses', required=True); pcf.add_argument('--actions'); pcf.add_argument('--out', required=True); pcf.add_argument('--summary-out'); pcf.add_argument('--min-contexts', type=int, default=1); pcf.add_argument('--baseline-required', action='store_true'); pcf.add_argument('--no-carrier', action='store_true'); pcf.add_argument('--no-gamma', action='store_true'); pcf.add_argument('--no-cost', action='store_true'); pcf.add_argument('--no-audit', action='store_true'); pcf.set_defaults(func=cmd_premise_contextual_fingerprints)
    pcqm=sub.add_parser('premise-contextual-mine'); pcqm.add_argument('--fingerprints', required=True); pcqm.add_argument('--out', required=True); pcqm.add_argument('--epsilon', type=float, default=0.25); pcqm.add_argument('--cosine-threshold', type=float, default=0.95); pcqm.add_argument('--domain-jaccard-threshold', type=float, default=0.0); pcqm.add_argument('--response-weight', type=float, default=1.0); pcqm.add_argument('--carrier-weight', type=float, default=1.0); pcqm.add_argument('--gamma-weight', type=float, default=0.25); pcqm.add_argument('--domain-weight', type=float, default=1.0); pcqm.add_argument('--cost-weight', type=float, default=0.05); pcqm.add_argument('--uncertainty-weight', type=float, default=0.10); pcqm.set_defaults(func=cmd_premise_contextual_mine)
    pcv=sub.add_parser('premise-contextual-validate'); pcv.add_argument('--fingerprints', required=True); pcv.add_argument('--classes', required=True); pcv.add_argument('--out-rows', required=True); pcv.add_argument('--out-report', required=True); pcv.add_argument('--holdout-fraction', type=float, default=0.35); pcv.add_argument('--epsilon-holdout', type=float, default=0.35); pcv.add_argument('--separation-delta', type=float, default=0.10); pcv.add_argument('--domain-jaccard-min', type=float, default=0.0); pcv.add_argument('--carrier-mixed-threshold', type=float, default=0.05); pcv.set_defaults(func=cmd_premise_contextual_validate)
    pqr=sub.add_parser('premise-quotient-retrieve'); pqr.add_argument('--classes', required=True); pqr.add_argument('--out', required=True); pqr.add_argument('--summary-out'); pqr.add_argument('--out-actions'); pqr.add_argument('--response-normal'); pqr.add_argument('--response-normal-json'); pqr.add_argument('--carrier-normal'); pqr.add_argument('--carrier-normal-json'); pqr.add_argument('--top-k', type=int); pqr.add_argument('--gamma-weight', type=float, default=0.10); pqr.add_argument('--cost-weight', type=float, default=0.05); pqr.add_argument('--uncertainty-weight', type=float, default=0.10); pqr.add_argument('--import-cost-weight', type=float, default=0.05); pqr.add_argument('--require-validated', action='store_true'); pqr.set_defaults(func=cmd_premise_quotient_retrieve)
    pur=sub.add_parser('premise-use-rows'); pur.add_argument('--actions', required=True); pur.add_argument('--out', required=True); pur.add_argument('--summary-out'); pur.add_argument('--max-rows', type=int); pur.add_argument('--include-context-actions', action='store_true'); pur.set_defaults(func=cmd_premise_use_rows)
    sep=sub.add_parser('separator-contexts'); sep.add_argument('--templates', choices=['builtin_core','core'], default='builtin_core'); sep.add_argument('--out', required=True); sep.add_argument('--summary-out'); sep.set_defaults(func=cmd_separator_contexts)
    bcg=sub.add_parser('bivariate-contextual-generate'); bcg.add_argument('--premise-rows', required=True); bcg.add_argument('--contexts', required=True); bcg.add_argument('--out', required=True); bcg.add_argument('--summary-out'); bcg.add_argument('--max-rows', type=int); bcg.add_argument('--max-pre', type=int, default=8); bcg.add_argument('--max-post', type=int, default=8); bcg.add_argument('--max-candidates', type=int); bcg.add_argument('--no-baselines', action='store_true'); bcg.set_defaults(func=cmd_bivariate_contextual_generate)
    bcs=sub.add_parser('bivariate-contextual-schedule'); bcs.add_argument('--candidates', required=True); bcs.add_argument('--out', required=True); bcs.add_argument('--budget', type=int, default=512); bcs.add_argument('--report-out'); bcs.add_argument('--require-baseline-pairs', action='store_true'); bcs.set_defaults(func=cmd_bivariate_contextual_schedule)
    rfl=sub.add_parser('repair-face-ledger'); rfl.add_argument('--fingerprints', required=True); rfl.add_argument('--classes', required=True); rfl.add_argument('--validation'); rfl.add_argument('--out', required=True); rfl.add_argument('--report'); rfl.set_defaults(func=cmd_repair_face_ledger)
    cact=sub.add_parser('carrier-actions'); cact.add_argument('--proposals', required=True); cact.add_argument('--out', required=True); cact.add_argument('--prefix', default='carrier'); cact.add_argument('--max-actions-per-context', type=int, default=8); cact.set_defaults(func=cmd_carrier_actions)
    acact=sub.add_parser('accepted-carrier-actions'); acact.add_argument('--accepted', required=True); acact.add_argument('--out', required=True); acact.add_argument('--min-margin', type=float, default=0.0); acact.add_argument('--include-rejected', action='store_true'); acact.set_defaults(func=cmd_accepted_carrier_actions)
    ma=sub.add_parser('merge-actions'); ma.add_argument('--inputs', nargs='+', required=True); ma.add_argument('--out', required=True); ma.set_defaults(func=cmd_merge_actions)
    ef=sub.add_parser('expose-frontier'); ef.add_argument('--tasks', required=True); ef.add_argument('--out-tasks', required=True); ef.add_argument('--out-report', required=True); ef.add_argument('--out-exposures'); ef.add_argument('--out-actions'); ef.add_argument('--lean-cmd', default='lake env lean'); ef.add_argument('--workdir'); ef.add_argument('--timeout-s', type=float, default=20.0); ef.add_argument('--dry-run', action='store_true'); ef.add_argument('--keep-files', action='store_true'); ef.add_argument('--cache-dir'); ef.add_argument('--trace-state', action='store_true'); ef.add_argument('--import-mode', choices=['preserve','auto','core','mathlib'], default='auto'); ef.add_argument('--max-exposures', type=int, default=8); ef.add_argument('--max-frontiers-per-task', type=int, default=8); ef.add_argument('--max-core-actions', type=int, default=16); ef.add_argument('--no-identity', action='store_true'); ef.set_defaults(func=cmd_expose_frontier)
    gs=sub.add_parser('goal-shapes'); gs.add_argument('--tasks', required=True); gs.add_argument('--out', required=True); gs.add_argument('--import-mode', choices=['preserve','auto','core','mathlib'], default='preserve'); gs.set_defaults(func=cmd_goal_shapes)
    sir=sub.add_parser('state-ir'); sir.add_argument('--out', required=True); sir.add_argument('--tasks'); sir.add_argument('--audits'); sir.add_argument('--import-mode', choices=['preserve','auto','core','mathlib'], default='preserve'); sir.set_defaults(func=cmd_state_ir)
    ps=sub.add_parser('parse-states'); ps.add_argument('--audits', required=True); ps.add_argument('--out', required=True); ps.set_defaults(func=cmd_parse_states)
    ird=sub.add_parser('ir-defects'); ird.add_argument('--ir', required=True); ird.add_argument('--out', required=True); ird.set_defaults(func=cmd_ir_defects)
    er=sub.add_parser('exposure-report'); er.add_argument('--responses', required=True); er.add_argument('--out', required=True); er.set_defaults(func=cmd_exposure_report)
    ec=sub.add_parser('exposure-candidates'); ec.add_argument('--tasks', required=True); ec.add_argument('--out', required=True); ec.add_argument('--include-identity', action='store_true'); ec.add_argument('--import-mode', choices=['preserve','auto','core','mathlib'], default='preserve'); ec.set_defaults(func=cmd_exposure_candidates)
    ar=sub.add_parser('action-report'); ar.add_argument('--responses', required=True); ar.add_argument('--out', required=True); ar.add_argument('--csv-out'); ar.add_argument('--group-keys'); ar.set_defaults(func=cmd_action_report)
    q=sub.add_parser('quotient'); q.add_argument('--responses', required=True); q.add_argument('--out', required=True); q.add_argument('--tolerance', type=float, default=0.25); q.set_defaults(func=cmd_quotient)
    c=sub.add_parser('carrier-generate'); c.add_argument('--defects', required=True); c.add_argument('--out', required=True); c.add_argument('--threshold', type=float, default=0.1); c.set_defaults(func=cmd_carrier_generate)
    cc=sub.add_parser('carrier-coker'); cc.add_argument('--defects', required=True); cc.add_argument('--actions'); cc.add_argument('--out', required=True); cc.set_defaults(func=cmd_carrier_coker)
    fs=sub.add_parser('failure-signatures'); fs.add_argument('--audits', required=True); fs.add_argument('--responses'); fs.add_argument('--out', required=True); fs.add_argument('--actions-out'); fs.add_argument('--summary-out'); fs.add_argument('--min-support', type=int, default=1); fs.set_defaults(func=cmd_failure_signatures)
    sr=sub.add_parser('seed-defect-registry'); sr.add_argument('--out', required=True); sr.set_defaults(func=cmd_seed_defect_registry)
    md=sub.add_parser('mine-defects'); md.add_argument('--audits', required=True); md.add_argument('--responses'); md.add_argument('--out', required=True); md.add_argument('--scores-out'); md.add_argument('--min-support', type=int, default=1); md.add_argument('--min-response-contrast', type=float, default=-1e9); md.add_argument('--min-stability', type=float, default=0.0); md.add_argument('--min-intervention-success', type=float, default=0.0); md.add_argument('--min-coker-reduction', type=float, default=0.0); md.set_defaults(func=cmd_mine_defects)
    prg=sub.add_parser('promote-registry'); prg.add_argument('--registry', required=True); prg.add_argument('--audits', required=True); prg.add_argument('--responses'); prg.add_argument('--out', required=True); prg.add_argument('--report-out'); prg.add_argument('--min-support', type=int, default=1); prg.add_argument('--min-intervention-success', type=float, default=0.1); prg.add_argument('--min-coker-reduction', type=float, default=-1e9); prg.add_argument('--min-promotion-score', type=float, default=-1e9); prg.add_argument('--drop-rejected', action='store_true'); prg.set_defaults(func=cmd_promote_registry)
    ad=sub.add_parser('auto-defects'); ad.add_argument('--registry', required=True); ad.add_argument('--out', required=True); ad.add_argument('--tasks'); ad.add_argument('--states'); ad.add_argument('--import-mode', choices=['preserve','auto','core','mathlib'], default='preserve'); ad.set_defaults(func=cmd_auto_defects)
    ada=sub.add_parser('audit-defect-atoms'); ada.add_argument('--audits', required=True); ada.add_argument('--responses'); ada.add_argument('--out', required=True); ada.set_defaults(func=cmd_audit_defect_atoms)
    tr=sub.add_parser('train-response'); tr.add_argument('--responses', required=True); tr.add_argument('--actions'); tr.add_argument('--out', required=True); tr.add_argument('--lcb-kappa', type=float, default=1.0); tr.add_argument('--min-count-for-action', type=int, default=2); tr.add_argument('--shrink', type=float, default=2.0); tr.set_defaults(func=cmd_train_response)
    pr=sub.add_parser('predict-response'); pr.add_argument('--model', required=True); pr.add_argument('--actions', required=True); pr.add_argument('--out', required=True); pr.add_argument('--mode', choices=['mean','lcb'], default='mean'); pr.set_defaults(func=cmd_predict_response)
    er=sub.add_parser('eval-response'); er.add_argument('--model', required=True); er.add_argument('--responses', required=True); er.add_argument('--out', required=True); er.add_argument('--out-rows'); er.add_argument('--csv-out'); er.add_argument('--mode', choices=['mean','lcb'], default='mean'); er.set_defaults(func=cmd_eval_response)
    sel=sub.add_parser('select'); sel.add_argument('--model', required=True); sel.add_argument('--actions', required=True); sel.add_argument('--defect', required=True); sel.add_argument('--out', required=True); sel.add_argument('--response-mode', choices=['mean','lcb'], default='mean'); sel.add_argument('--carrier-budget', type=float, default=1.0); sel.add_argument('--carrier-mode', default='constraint', choices=['off','penalty','constraint']); sel.add_argument('--cost-weight', type=float, default=0.1); sel.set_defaults(func=cmd_select)
    ga=sub.add_parser('gamma-audit'); ga.add_argument('--transitions', required=True); ga.add_argument('--out', required=True); ga.add_argument('--fit-gamma', action='store_true'); ga.add_argument('--ridge', type=float, default=1e-3); ga.add_argument('--horizon', type=int, default=4); ga.add_argument('--include-gamma-matrix', action='store_true'); ga.set_defaults(func=cmd_gamma_audit)
    gtl=sub.add_parser('gamma-transition-learner'); gtl.add_argument('--transitions', required=True); gtl.add_argument('--out', required=True); gtl.add_argument('--actions'); gtl.add_argument('--teacher-constraints'); gtl.add_argument('--ridge', type=float, default=1e-3); gtl.add_argument('--shrink', type=float, default=4.0); gtl.add_argument('--min-count', type=int, default=2); gtl.add_argument('--holdout-fraction', type=float, default=0.25); gtl.add_argument('--seed', type=int, default=0); gtl.add_argument('--teacher-weight', type=float, default=0.25); gtl.add_argument('--include-matrices', action='store_true'); gtl.set_defaults(func=cmd_gamma_transition_learner)
    gtp=sub.add_parser('gamma-transition-patch-action-geometry'); gtp.add_argument('--action-geometry', required=True); gtp.add_argument('--patches', required=True); gtp.add_argument('--out', required=True); gtp.add_argument('--summary-out'); gtp.set_defaults(func=cmd_gamma_transition_patch_action_geometry)
    rs=sub.add_parser('run-search'); rs.add_argument('--tasks', required=True); rs.add_argument('--out', required=True); rs.add_argument('--response-model'); rs.add_argument('--response-mode', choices=['mean','lcb'], default='mean'); rs.add_argument('--max-steps', type=int, default=8); rs.add_argument('--max-candidates', type=int, default=32); rs.add_argument('--carrier-budget', type=float, default=1.0); rs.add_argument('--carrier-mode', choices=['off','penalty','constraint'], default='constraint'); add_exec_args(rs); rs.set_defaults(func=cmd_run_search)

    fa=sub.add_parser('focused-audit'); fa.add_argument('--tasks', required=True); fa.add_argument('--actions'); fa.add_argument('--out', required=True); fa.add_argument('--dry-run', action='store_true'); fa.add_argument('--lean-cmd', default='lake env lean'); fa.add_argument('--workdir'); fa.add_argument('--timeout-s', type=float, default=20.0); fa.add_argument('--keep-files', action='store_true'); fa.add_argument('--cache-dir'); fa.add_argument('--trace-state', action='store_true'); fa.add_argument('--import-mode', choices=['preserve','auto','core','mathlib'], default='auto'); fa.add_argument('--max-exposures', type=int, default=6); fa.add_argument('--max-core-actions', type=int, default=16); fa.add_argument('--audit-identity-exposure', action='store_true'); fa.set_defaults(func=cmd_focused_audit)
    mt=sub.add_parser('make-transitions'); mt.add_argument('--responses', required=True); mt.add_argument('--out', required=True); mt.set_defaults(func=cmd_make_transitions)
    ds=sub.add_parser('dataset-summary'); ds.add_argument('--responses', required=True); ds.add_argument('--out'); ds.set_defaults(func=cmd_dataset_summary)
    sp=sub.add_parser('split'); sp.add_argument('--input', required=True); sp.add_argument('--out', required=True); sp.add_argument('--train-frac', type=float, default=0.8); sp.add_argument('--seed', type=int, default=0); sp.add_argument('--group-key'); sp.set_defaults(func=cmd_split)
    ca=sub.add_parser('carrier-accept'); ca.add_argument('--tasks', required=True); ca.add_argument('--proposals', required=True); ca.add_argument('--out', required=True); ca.add_argument('--margin-threshold', type=float, default=0.0); ca.add_argument('--cost-weight', type=float, default=0.1); add_exec_args(ca); ca.set_defaults(func=cmd_carrier_accept)
    cas=sub.add_parser('carrier-accept-summary'); cas.add_argument('--accepted', required=True); cas.add_argument('--out', required=True); cas.set_defaults(func=cmd_carrier_accept_summary)
    rba=sub.add_parser('robust-accept'); rba.add_argument('--base-responses', required=True); rba.add_argument('--candidate-responses', required=True); rba.add_argument('--out', required=True); rba.add_argument('--report-out'); rba.add_argument('--accepted-actions-out'); rba.add_argument('--per-row-out'); rba.add_argument('--margin-threshold', type=float, default=0.0); rba.add_argument('--max-per-task', type=int, default=16); rba.add_argument('--goal-weight', type=float, default=1.0); rba.add_argument('--carrier-weight', type=float, default=0.7); rba.add_argument('--cost-weight', type=float, default=0.05); rba.add_argument('--max-mass', type=float, default=1.0); rba.add_argument('--ridge', type=float, default=1e-4); rba.add_argument('--robust-z', type=float, default=1.0); rba.add_argument('--robust-min-repeats', type=int, default=1); rba.add_argument('--robust-min-success-rate', type=float, default=1.0); rba.set_defaults(func=cmd_robust_accept)
    ra=sub.add_parser('registry-accept'); ra.add_argument('--base-responses', required=True); ra.add_argument('--registry-responses', required=True); ra.add_argument('--accepted-actions-out', required=True); ra.add_argument('--report-out', required=True); ra.add_argument('--audit-out'); ra.add_argument('--margin-threshold', type=float, default=0.0); ra.add_argument('--max-per-task', type=int, default=16); ra.add_argument('--goal-weight', type=float, default=1.0); ra.add_argument('--type-weight', type=float, default=0.6); ra.add_argument('--search-weight', type=float, default=0.4); ra.add_argument('--carrier-weight', type=float, default=0.7); ra.add_argument('--audit-weight', type=float, default=0.2); ra.add_argument('--success-bonus', type=float, default=0.25); ra.add_argument('--fail-penalty', type=float, default=0.25); ra.add_argument('--timeout-penalty', type=float, default=1.0); ra.add_argument('--cost-weight', type=float, default=0.05); ra.add_argument('--robust-radius', type=float, default=0.0); ra.add_argument('--robust-relative-radius', type=float, default=0.0); ra.add_argument('--accept-on-robust', action='store_true'); ra.set_defaults(func=cmd_registry_accept)
    ac=sub.add_parser('accept-candidates'); ac.add_argument('--base-responses', required=True); ac.add_argument('--candidate-responses', required=True); ac.add_argument('--out', required=True); ac.add_argument('--summary-out'); ac.add_argument('--margin-threshold', type=float, default=0.0); ac.add_argument('--cost-weight', type=float, default=0.05); ac.add_argument('--carrier-weight', type=float, default=0.25); ac.add_argument('--audit-penalty', type=float, default=1.0); ac.add_argument('--require-success', action='store_true'); ac.set_defaults(func=cmd_accept_candidates)
    maf=sub.add_parser('merge-action-files'); maf.add_argument('--inputs', nargs='+', required=True); maf.add_argument('--out', required=True); maf.add_argument('--max-actions', type=int); maf.set_defaults(func=cmd_merge_action_files)
    cr=sub.add_parser('compare-runs'); cr.add_argument('--runs', nargs='+', required=True); cr.add_argument('--out-json'); cr.add_argument('--out-csv'); cr.set_defaults(func=cmd_compare_runs)
    sr=sub.add_parser('stage-report'); sr.add_argument('--run-dir'); sr.add_argument('--stage', action='append', help='NAME=responses.jsonl or responses.jsonl; may be repeated'); sr.add_argument('--out', required=True); sr.add_argument('--csv-out'); sr.set_defaults(func=cmd_stage_report)
    rp=sub.add_parser('report'); rp.add_argument('--run-dir', required=True); rp.add_argument('--out'); rp.set_defaults(func=cmd_report)
    pipe=sub.add_parser('pipeline', conflict_handler='resolve'); pipe.add_argument('--tasks', required=True); pipe.add_argument('--actions'); pipe.add_argument('--out', required=True); pipe.add_argument('--expose-frontier', action='store_true'); pipe.add_argument('--expose-max-exposures', type=int, default=8); pipe.add_argument('--expose-no-identity', action='store_true'); pipe.add_argument('--dry-run', action='store_true'); pipe.add_argument('--jobs', type=int, default=1); pipe.add_argument('--audit-mode', choices=['batch','bulk','server'], default='batch'); pipe.add_argument('--bulk-batch-size', type=int, default=64); pipe.add_argument('--max-actions', type=int, default=32); pipe.add_argument('--frontier-normalize', action='store_true'); pipe.add_argument('--frontier-max-prefixes', type=int, default=8); pipe.add_argument('--frontier-include-identity', action='store_true'); pipe.add_argument('--candidate-mode', choices=['basic','state'], default='state'); pipe.add_argument('--state-candidates', action='store_true'); pipe.add_argument('--quotient-tolerance', type=float, default=0.25); pipe.add_argument('--carrier-threshold', type=float, default=0.1); pipe.add_argument('--lean-cmd', default='lake env lean'); pipe.add_argument('--workdir'); pipe.add_argument('--timeout-s', type=float, default=20.0); pipe.add_argument('--keep-files', action='store_true'); pipe.add_argument('--cache-dir'); pipe.add_argument('--trace-state', action='store_true'); pipe.add_argument('--server-cmd'); pipe.add_argument('--server-backend', choices=['auto','dry_run','file','file_fallback','jsonl','persistent','native'], default='auto'); pipe.add_argument('--server-no-fallback', action='store_true'); pipe.add_argument('--native-exec-mode', choices=['source_check','heuristic','kernel_rpc'], default='source_check'); pipe.add_argument('--audit-exposures', action='store_true'); pipe.add_argument('--exposure-audit-max-actions', type=int, default=8); pipe.add_argument('--import-mode', choices=['preserve','auto','core','mathlib'], default='auto'); pipe.add_argument('--resume', action='store_true'); pipe.add_argument('--flush-every', type=int, default=50); pipe.add_argument('--fit-gamma', action='store_true'); pipe.add_argument('--gamma-horizon', type=int, default=4); pipe.add_argument('--gamma-transition-learner', action='store_true'); pipe.add_argument('--gamma-transition-min-count', type=int, default=2); pipe.add_argument('--gamma-transition-shrink', type=float, default=4.0); pipe.add_argument('--gamma-transition-ridge', type=float, default=1e-3); pipe.add_argument('--gamma-transition-holdout-fraction', type=float, default=0.25); pipe.add_argument('--gamma-transition-teacher-weight', type=float, default=0.25); pipe.add_argument('--gamma-transition-include-matrices', action='store_true'); pipe.add_argument('--gamma-transition-patch-action-geometry', action='store_true'); pipe.add_argument('--arithmetic-teacher-graph', action='store_true'); pipe.add_argument('--arithmetic-teacher-identities'); pipe.add_argument('--arithmetic-teacher-structured-states'); pipe.add_argument('--arithmetic-teacher-max-transforms-per-state', type=int, default=32); pipe.add_argument('--arithmetic-teacher-no-actions', action='store_true'); pipe.add_argument('--audit-arithmetic-teacher-candidates', action='store_true'); pipe.add_argument('--arithmetic-teacher-audit-max-actions', type=int, default=16); pipe.add_argument('--arithmetic-teacher-kernel-audit', action='store_true'); pipe.add_argument('--arithmetic-teacher-kernel-audit-max-transitions', type=int, default=32); pipe.add_argument('--arithmetic-teacher-cocycle-audit', action='store_true'); pipe.add_argument('--arithmetic-teacher-cocycle-compositions'); pipe.add_argument('--arithmetic-teacher-cocycle-min-count', type=int, default=1); pipe.add_argument('--arithmetic-teacher-cocycle-accept-threshold', type=float, default=1.0); pipe.add_argument('--arithmetic-teacher-cocycle-min-verified-rate', type=float, default=0.0); pipe.add_argument('--arithmetic-teacher-cocycle-max-tail-radius', type=float); pipe.add_argument('--arithmetic-teacher-cocycle-max-auto-pairs', type=int, default=0); pipe.add_argument('--qgen', action='store_true'); pipe.add_argument('--qgen-ridge', type=float, default=1e-4); pipe.add_argument('--qgen-max-mass', type=float, default=1.0); pipe.add_argument('--carrier-quotient', action='store_true'); pipe.add_argument('--carrier-quotient-ridge', type=float, default=1e-4); pipe.add_argument('--carrier-quotient-max-mass', type=float, default=1.0); pipe.add_argument('--carrier-quotient-cosine-threshold', type=float, default=0.85); pipe.add_argument('--carrier-quotient-min-states', type=int, default=1); pipe.add_argument('--carrier-quotient-top-action-scores', type=int, default=128); pipe.add_argument('--carrier-quotient-margin-threshold', type=float, default=0.0); pipe.add_argument('--carrier-quotient-validate', action='store_true'); pipe.add_argument('--carrier-quotient-no-infer-defect-from-violations', action='store_true'); pipe.add_argument('--qgen-top-defects', type=int, default=16); pipe.add_argument('--qgen-top-contexts', type=int, default=32); pipe.add_argument('--qgen-top-carriers', type=int, default=64); pipe.add_argument('--qgen-top-failures', type=int, default=32); pipe.add_argument('--qgen-margin-threshold', type=float, default=0.0); pipe.add_argument('--qgen-cost-weight', type=float, default=0.05); pipe.add_argument('--qgen-carrier-weight', type=float, default=0.25); pipe.add_argument('--qgen-audit-penalty', type=float, default=1.0); pipe.add_argument('--audit-qgen-candidates', action='store_true'); pipe.add_argument('--qgen-audit-max-actions', type=int, default=24); pipe.add_argument('--qgen-accept-coker', action='store_true'); pipe.add_argument('--qgen-accept-margin', type=float, default=0.0); pipe.add_argument('--qgen-accept-max-per-task', type=int, default=16); pipe.add_argument('--qgen-accept-cost-weight', type=float, default=0.05); pipe.add_argument('--qgen-accept-carrier-weight', type=float, default=0.7); pipe.add_argument('--qgen-robust-accept', action='store_true'); pipe.add_argument('--qgen-registry-robust-accept', action='store_true'); pipe.add_argument('--qgen-robust-coker-accept', action='store_true'); pipe.add_argument('--qgen-registry-robust-coker-accept', action='store_true'); pipe.add_argument('--qgen-robust-coker-holdout-fraction', type=float, default=0.35); pipe.add_argument('--qgen-robust-coker-uncertainty-weight', type=float, default=0.10); pipe.add_argument('--qgen-robust-coker-carrier-gain-weight', type=float, default=0.25); pipe.add_argument('--qgen-robust-coker-audit-penalty', type=float, default=1.0); pipe.add_argument('--qgen-robust-coker-require-success', action='store_true'); pipe.add_argument('--qgen-robust-z', type=float, default=1.0); pipe.add_argument('--qgen-robust-min-repeats', type=int, default=1); pipe.add_argument('--qgen-robust-min-success-rate', type=float, default=1.0); pipe.add_argument('--qgen-registry-candidates', action='store_true'); pipe.add_argument('--qgen-registry-max-candidates', type=int, default=64); pipe.add_argument('--audit-qgen-registry-candidates', action='store_true'); pipe.add_argument('--qgen-registry-audit-max-actions', type=int, default=16); pipe.add_argument('--qgen-registry-accept-coker', action='store_true'); pipe.add_argument('--qgen-registry-accept-margin', type=float, default=0.0); pipe.add_argument('--qgen-registry-accept-max-per-task', type=int, default=16); pipe.add_argument('--qgen-registry-accept-cost-weight', type=float, default=0.05); pipe.add_argument('--qgen-registry-accept-carrier-weight', type=float, default=0.7); pipe.add_argument('--action-geometry', action='store_true'); pipe.add_argument('--action-geometry-retrieve', action='store_true'); pipe.add_argument('--action-geometry-use-qgen-normals', action='store_true'); pipe.add_argument('--action-geometry-top-k', type=int, default=32); pipe.add_argument('--action-geometry-min-count', type=int, default=1); pipe.add_argument('--action-geometry-tail-weight', type=float, default=0.25); pipe.add_argument('--action-geometry-cost-weight', type=float, default=0.05); pipe.add_argument('--action-geometry-uncertainty-weight', type=float, default=0.10); pipe.add_argument('--action-geometry-audit-weight', type=float, default=0.20); pipe.add_argument('--action-geometry-require-carrier-safe', action='store_true'); pipe.add_argument('--action-geometry-carrier-budget', type=float, default=0.0); pipe.add_argument('--action-geometry-use-gamma-transition', action='store_true'); pipe.add_argument('--action-geometry-gamma-aware', action='store_true'); pipe.add_argument('--action-geometry-gamma-value-mode', choices=['local','finite_horizon','stationary','resolvent','tail','tail_bonus'], default='local'); pipe.add_argument('--action-geometry-gamma-horizon', type=int, default=4); pipe.add_argument('--action-geometry-gamma-discount', type=float, default=1.0); pipe.add_argument('--action-geometry-gamma-tail-value-weight', type=float, default=1.0); pipe.add_argument('--action-geometry-gamma-stability-margin', type=float, default=0.05); pipe.add_argument('--action-geometry-gamma-tail-risk-mode', choices=['spectral','normal_amplification','none'], default='spectral'); pipe.add_argument('--audit-action-geometry-candidates', action='store_true'); pipe.add_argument('--action-geometry-audit-max-actions', type=int, default=24); pipe.add_argument('--action-geometry-accept-coker', action='store_true'); pipe.add_argument('--action-geometry-accept-margin', type=float, default=0.0); pipe.add_argument('--action-geometry-accept-max-per-task', type=int, default=16); pipe.add_argument('--action-geometry-accept-cost-weight', type=float, default=0.05); pipe.add_argument('--action-geometry-accept-carrier-weight', type=float, default=0.7); pipe.add_argument('--action-geometry-robust-coker-accept', action='store_true'); pipe.add_argument('--action-geometry-robust-coker-holdout-fraction', type=float, default=0.35); pipe.add_argument('--action-geometry-robust-coker-uncertainty-weight', type=float, default=0.10); pipe.add_argument('--action-geometry-robust-coker-carrier-gain-weight', type=float, default=0.25); pipe.add_argument('--action-geometry-robust-coker-audit-penalty', type=float, default=1.0); pipe.add_argument('--action-geometry-robust-coker-require-success', action='store_true'); pipe.add_argument('--quotient-coordinates', action='store_true'); pipe.add_argument('--quotient-coordinate-ridge', type=float, default=1e-4); pipe.add_argument('--quotient-coordinate-max-mass', type=float, default=1.0); pipe.add_argument('--quotient-coordinate-cosine-threshold', type=float, default=0.85); pipe.add_argument('--quotient-coordinate-min-states', type=int, default=1); pipe.add_argument('--quotient-coordinate-top-action-scores', type=int, default=128); pipe.add_argument('--quotient-coordinate-margin-threshold', type=float, default=0.0); pipe.add_argument('--quotient-coordinate-validate', action='store_true'); pipe.add_argument('--quotient-coordinate-registry-candidates', action='store_true'); pipe.add_argument('--quotient-coordinate-registry-max-candidates', type=int, default=64); pipe.add_argument('--audit-quotient-coordinate-candidates', action='store_true'); pipe.add_argument('--quotient-coordinate-audit-max-actions', type=int, default=16); pipe.add_argument('--quotient-coordinate-accept-coker', action='store_true'); pipe.add_argument('--quotient-coordinate-robust-coker-accept', action='store_true'); pipe.add_argument('--quotient-coordinate-accept-margin', type=float, default=0.0); pipe.add_argument('--quotient-coordinate-accept-max-per-task', type=int, default=16); pipe.add_argument('--quotient-coordinate-accept-cost-weight', type=float, default=0.05); pipe.add_argument('--quotient-coordinate-accept-carrier-weight', type=float, default=0.7); pipe.add_argument('--quotient-coordinate-robust-coker-holdout-fraction', type=float, default=0.35); pipe.add_argument('--quotient-coordinate-robust-coker-uncertainty-weight', type=float, default=0.10); pipe.add_argument('--quotient-coordinate-robust-coker-carrier-gain-weight', type=float, default=0.25); pipe.add_argument('--quotient-coordinate-robust-coker-audit-penalty', type=float, default=1.0); pipe.add_argument('--quotient-coordinate-robust-coker-require-success', action='store_true'); pipe.add_argument('--action-geometry-use-quotient-normals', action='store_true'); pipe.add_argument('--carrier-quotient', action='store_true'); pipe.add_argument('--carrier-quotient-ridge', type=float, default=1e-4); pipe.add_argument('--carrier-quotient-max-mass', type=float, default=1.0); pipe.add_argument('--carrier-quotient-cosine-threshold', type=float, default=0.85); pipe.add_argument('--carrier-quotient-min-states', type=int, default=1); pipe.add_argument('--carrier-quotient-top-action-scores', type=int, default=128); pipe.add_argument('--carrier-quotient-margin-threshold', type=float, default=0.0); pipe.add_argument('--audit-carrier-quotient-candidates', action='store_true'); pipe.add_argument('--carrier-quotient-audit-max-actions', type=int, default=16); pipe.add_argument('--carrier-quotient-accept-coker', action='store_true'); pipe.add_argument('--carrier-quotient-robust-coker-accept', action='store_true'); pipe.add_argument('--carrier-quotient-accept-margin', type=float, default=0.0); pipe.add_argument('--carrier-quotient-accept-max-per-task', type=int, default=16); pipe.add_argument('--carrier-quotient-accept-cost-weight', type=float, default=0.05); pipe.add_argument('--carrier-quotient-accept-carrier-weight', type=float, default=0.7); pipe.add_argument('--carrier-quotient-robust-coker-holdout-fraction', type=float, default=0.35); pipe.add_argument('--carrier-quotient-robust-coker-uncertainty-weight', type=float, default=0.10); pipe.add_argument('--carrier-quotient-robust-coker-carrier-gain-weight', type=float, default=0.25); pipe.add_argument('--carrier-quotient-robust-coker-audit-penalty', type=float, default=1.0); pipe.add_argument('--carrier-quotient-robust-coker-require-success', action='store_true'); pipe.add_argument('--carrier-quotient-merge-actions', action='store_true'); pipe.add_argument('--carrier-quotient-merge-policy', choices=['all','robust-only','accepted-only'], default='robust-only'); pipe.add_argument('--contextual-congruence', action='store_true'); pipe.add_argument('--contextual-congruence-context-mode', choices=['state','task','global'], default='state'); pipe.add_argument('--contextual-congruence-no-carrier', action='store_true'); pipe.add_argument('--contextual-congruence-min-count', type=int, default=1); pipe.add_argument('--contextual-congruence-cosine-threshold', type=float, default=0.95); pipe.add_argument('--contextual-congruence-distance-threshold', type=float, default=0.25); pipe.add_argument('--contextual-congruence-min-context-jaccard', type=float, default=0.0); pipe.add_argument('--audit-db', action='store_true'); pipe.add_argument('--audit-db-path'); pipe.add_argument('--audit-db-append', action='store_true'); pipe.add_argument('--audit-scheduler', action='store_true'); pipe.add_argument('--active-audit-scheduler', dest='audit_scheduler', action='store_true'); pipe.add_argument('--audit-scheduler-db'); pipe.add_argument('--audit-scheduler-responses'); pipe.add_argument('--audit-scheduler-lineage', action='append'); pipe.add_argument('--audit-scheduler-budget', type=int); pipe.add_argument('--audit-scheduler-top-k', dest='audit_scheduler_budget', type=int); pipe.add_argument('--audit-scheduler-per-task-cap', type=int); pipe.add_argument('--audit-scheduler-per-source-cap', type=int); pipe.add_argument('--audit-scheduler-coker-weight', type=float, default=1.0); pipe.add_argument('--audit-scheduler-carrier-weight', type=float, default=0.5); pipe.add_argument('--audit-scheduler-uncertainty-weight', type=float, default=0.25); pipe.add_argument('--audit-scheduler-novelty-weight', type=float, default=0.15); pipe.add_argument('--audit-scheduler-success-weight', type=float, default=0.25); pipe.add_argument('--audit-scheduler-cost-weight', type=float, default=0.10); pipe.add_argument('--audit-scheduler-timeout-weight', type=float, default=0.50); pipe.add_argument('--eval-response-model', action='store_true'); pipe.add_argument('--response-eval-mode', choices=['mean','lcb'], default='mean'); pipe.add_argument('--mine-defects', action='store_true'); pipe.add_argument('--mine-min-support', type=int, default=1); pipe.add_argument('--mine-min-response-contrast', type=float, default=-1e9); pipe.add_argument('--mine-min-stability', type=float, default=0.0); pipe.add_argument('--mine-min-intervention-success', type=float, default=0.0); pipe.add_argument('--mine-min-coker-reduction', type=float, default=0.0); pipe.add_argument('--registry-candidates', action='store_true'); pipe.add_argument('--registry-max-candidates', type=int, default=96); pipe.add_argument('--audit-registry-candidates', action='store_true'); pipe.add_argument('--registry-audit-max-actions', type=int, default=32); pipe.add_argument('--registry-accept-coker', action='store_true'); pipe.add_argument('--registry-accept-margin', type=float, default=0.0); pipe.add_argument('--registry-accept-max-per-task', type=int, default=16); pipe.add_argument('--registry-accept-cost-weight', type=float, default=0.05); pipe.add_argument('--registry-accept-carrier-weight', type=float, default=0.7); pipe.add_argument('--promote-registry', action='store_true'); pipe.add_argument('--promote-min-support', type=int, default=1); pipe.add_argument('--promote-min-intervention-success', type=float, default=0.1); pipe.add_argument('--promote-min-coker-reduction', type=float, default=-1e9); pipe.add_argument('--promote-min-promotion-score', type=float, default=-1e9); pipe.add_argument('--promote-drop-rejected', action='store_true'); pipe.add_argument('--premise-index', action='store_true'); pipe.add_argument('--premise-top-k', type=int, default=8); pipe.add_argument('--premise-max-actions', type=int, default=8); pipe.add_argument('--audit-premise-candidates', action='store_true'); pipe.add_argument('--premise-audit-max-actions', type=int, default=24); pipe.add_argument('--premise-response-registry', action='store_true'); pipe.add_argument('--premise-response-retrieve', action='store_true'); pipe.add_argument('--premise-response-top-k', type=int, default=32); pipe.add_argument('--premise-quotient-mine', action='store_true'); pipe.add_argument('--audit-premise-response-candidates', action='store_true'); pipe.add_argument('--premise-response-audit-max-actions', type=int, default=16); pipe.add_argument('--carrier-accept', action='store_true'); pipe.add_argument('--carrier-accept-max-actions', type=int, default=8); pipe.add_argument('--carrier-accept-margin', type=float, default=0.0); pipe.add_argument('--carrier-accept-cost-weight', type=float, default=0.1); pipe.add_argument('--promote-carrier-actions', action='store_true'); pipe.add_argument('--promote-carrier-min-margin', type=float, default=0.0); pipe.add_argument('--ir-candidates', action='store_true'); pipe.add_argument('--ir-max-candidates', type=int, default=64); pipe.add_argument('--audit-ir-candidates', action='store_true'); pipe.add_argument('--ir-audit-max-actions', type=int, default=24); pipe.add_argument('--ir-accept-coker', action='store_true'); pipe.add_argument('--ir-accept-margin', type=float, default=0.0); pipe.add_argument('--ir-accept-max-per-task', type=int, default=16); pipe.add_argument('--ir-accept-cost-weight', type=float, default=0.05); pipe.add_argument('--ir-accept-carrier-weight', type=float, default=0.7); pipe.add_argument('--carrier-matrix', action='store_true'); pipe.add_argument('--carrier-matrix-shrink', type=float, default=2.0); pipe.add_argument('--carrier-matrix-min-count', type=int, default=1); pipe.add_argument('--carrier-matrix-budget', type=float, default=0.0); pipe.add_argument('--carrier-matrix-keep-unsafe', action='store_true'); pipe.add_argument('--carrier-matrix-merge-qgen', action='store_true'); pipe.add_argument('--carrier-matrix-qgen-patch-weight', type=float, default=1.0); pipe.add_argument('--carrier-matrix-qgen-require-safe', action='store_true'); pipe.add_argument('--carrier-matrix-qgen-audit-patches', action='store_true'); pipe.add_argument('--carrier-matrix-qgen-patch-min-count', type=int, default=1); pipe.add_argument('--carrier-matrix-qgen-patch-min-mean-delta', type=float, default=0.0); pipe.add_argument('--carrier-matrix-qgen-patch-holdout-fraction', type=float, default=0.0); pipe.add_argument('--carrier-matrix-qgen-patch-require-heldout', action='store_true'); pipe.add_argument('--failure-signatures', action='store_true'); pipe.add_argument('--failure-signature-min-support', type=int, default=1); pipe.add_argument('--audit-failure-signature-candidates', action='store_true'); pipe.add_argument('--failure-signature-audit-max-actions', type=int, default=16); pipe.add_argument('--failure-signature-accept-coker', action='store_true'); pipe.add_argument('--failure-signature-accept-margin', type=float, default=0.0); pipe.add_argument('--failure-signature-accept-max-per-task', type=int, default=16); pipe.add_argument('--failure-signature-accept-cost-weight', type=float, default=0.05); pipe.add_argument('--failure-signature-accept-carrier-weight', type=float, default=0.7); pipe.add_argument('--stage-coker', action='store_true'); pipe.add_argument('--stage-coker-margin', type=float, default=0.0); pipe.add_argument('--stage-coker-cost-weight', type=float, default=0.05); pipe.add_argument('--stage-coker-carrier-weight', type=float, default=0.25); pipe.add_argument('--stage-coker-max-actions', type=int); add_contextual_probe_args(pipe); add_response_quotient_args(pipe); add_premise_contextual_pipeline_args(pipe);
    # v37 source-budget scheduler: allocate audit budget across candidate sources.
    for _parser in (pipe,):
        _parser.add_argument('--source-budget', action='store_true')
        _parser.add_argument('--audit-source-budget-candidates', action='store_true')
        _parser.add_argument('--source-budget-budget', type=int)
        _parser.add_argument('--source-budget-min-per-source', type=int, default=0)
        _parser.add_argument('--source-budget-max-per-source', type=int)
        _parser.add_argument('--source-budget-per-task-cap', type=int)
        _parser.add_argument('--source-budget-per-action-cap', type=int, default=1)
        _parser.add_argument('--source-budget-allocation-mode', choices=['proportional','score','round_robin'], default='proportional')
        _parser.add_argument('--source-budget-coker-weight', type=float, default=1.0)
        _parser.add_argument('--source-budget-carrier-weight', type=float, default=0.5)
        _parser.add_argument('--source-budget-uncertainty-weight', type=float, default=0.20)
        _parser.add_argument('--source-budget-novelty-weight', type=float, default=0.25)
        _parser.add_argument('--source-budget-lineage-weight', type=float, default=0.15)
        _parser.add_argument('--source-budget-success-weight', type=float, default=0.25)
        _parser.add_argument('--source-budget-cost-weight', type=float, default=0.10)
        _parser.add_argument('--source-budget-timeout-weight', type=float, default=0.50); _parser.add_argument('--source-budget-gamma-aware', action='store_true'); _parser.add_argument('--source-budget-gamma-value-mode', choices=['local','finite_horizon','stationary','resolvent','tail','tail_bonus'], default='finite_horizon'); _parser.add_argument('--source-budget-gamma-horizon', type=int, default=4); _parser.add_argument('--source-budget-gamma-discount', type=float, default=1.0); _parser.add_argument('--source-budget-gamma-value-weight', type=float, default=0.50); _parser.add_argument('--source-budget-gamma-tail-value-weight', type=float); _parser.add_argument('--source-budget-gamma-tail-risk-weight', type=float, default=0.50); _parser.add_argument('--source-budget-gamma-stability-delta', type=float, default=0.05); _parser.add_argument('--source-budget-gamma-tail-risk-mode', choices=['spectral','normal_amplification','none'], default='spectral'); _parser.add_argument('--source-budget-gamma-tail-radius-weight', type=float, default=0.0)
    pipe.set_defaults(func=cmd_pipeline)
    ef=sub.add_parser('expose-frontiers'); ef.add_argument('--tasks', required=True); ef.add_argument('--out', required=True); ef.add_argument('--max-prefixes', type=int, default=8); ef.add_argument('--include-identity', action='store_true'); ef.add_argument('--accept-status', nargs='*', default=['partial','success','dry_run']); add_exec_args(ef); ef.set_defaults(func=cmd_expose_frontiers)
    mb=sub.add_parser('make-corebench'); mb.add_argument('--out', required=True); mb.add_argument('--n-nat', type=int, default=20); mb.add_argument('--n-prop', type=int, default=20); mb.add_argument('--n-bool', type=int, default=10); mb.add_argument('--n-eq', type=int, default=10); mb.add_argument('--import-mode', choices=['core','mathlib'], default='core'); mb.set_defaults(func=cmd_make_corebench)
    it=sub.add_parser('iterate', conflict_handler='resolve'); it.add_argument('--tasks', required=True); it.add_argument('--actions'); it.add_argument('--out', required=True); it.add_argument('--rounds', type=int, default=2); it.add_argument('--dry-run', action='store_true'); it.add_argument('--jobs', type=int, default=1); it.add_argument('--audit-mode', choices=['batch','bulk','server'], default='batch'); it.add_argument('--bulk-batch-size', type=int, default=64); it.add_argument('--max-actions', type=int, default=32); it.add_argument('--candidate-mode', choices=['basic','state'], default='state'); it.add_argument('--frontier-normalize', action='store_true'); it.add_argument('--frontier-max-prefixes', type=int, default=8); it.add_argument('--frontier-include-identity', action='store_true'); it.add_argument('--lean-cmd', default='lake env lean'); it.add_argument('--workdir'); it.add_argument('--timeout-s', type=float, default=20.0); it.add_argument('--cache-dir'); it.add_argument('--server-cmd'); it.add_argument('--server-backend', choices=['auto','dry_run','file','file_fallback','jsonl','persistent','native'], default='auto'); it.add_argument('--server-no-fallback', action='store_true'); it.add_argument('--import-mode', choices=['preserve','auto','core','mathlib'], default='auto'); it.add_argument('--resume', action='store_true'); it.add_argument('--flush-every', type=int, default=50); it.add_argument('--registry-audit-max-actions', type=int, default=16); it.add_argument('--registry-accept-margin', type=float, default=0.0); it.add_argument('--registry-accept-max-per-task', type=int, default=16); it.add_argument('--promote-registry', action='store_true'); it.add_argument('--premise-index', action='store_true'); it.add_argument('--audit-premise-candidates', action='store_true'); it.add_argument('--premise-audit-max-actions', type=int, default=16); it.add_argument('--premise-response-registry', action='store_true'); it.add_argument('--premise-response-retrieve', action='store_true'); it.add_argument('--premise-response-top-k', type=int, default=32); it.add_argument('--premise-quotient-mine', action='store_true'); it.add_argument('--audit-premise-response-candidates', action='store_true'); it.add_argument('--premise-response-audit-max-actions', type=int, default=16); it.add_argument('--merge-premise-response-actions', action='store_true'); it.add_argument('--merge-premise-actions', action='store_true'); it.add_argument('--carrier-accept', action='store_true'); it.add_argument('--carrier-accept-max-actions', type=int, default=8); it.add_argument('--promote-carrier-actions', action='store_true'); it.add_argument('--carrier-matrix', action='store_true'); it.add_argument('--carrier-matrix-budget', type=float, default=0.0); it.add_argument('--carrier-matrix-keep-unsafe', action='store_true'); it.add_argument('--carrier-matrix-merge-qgen', action='store_true'); it.add_argument('--carrier-matrix-qgen-patch-weight', type=float, default=1.0); it.add_argument('--carrier-matrix-qgen-require-safe', action='store_true'); it.add_argument('--carrier-matrix-qgen-audit-patches', action='store_true'); it.add_argument('--carrier-matrix-qgen-patch-min-count', type=int, default=1); it.add_argument('--carrier-matrix-qgen-patch-min-mean-delta', type=float, default=0.0); it.add_argument('--carrier-matrix-qgen-patch-holdout-fraction', type=float, default=0.0); it.add_argument('--carrier-matrix-qgen-patch-require-heldout', action='store_true'); it.add_argument('--ir-candidates', action='store_true'); it.add_argument('--ir-max-candidates', type=int, default=64); it.add_argument('--audit-ir-candidates', action='store_true'); it.add_argument('--ir-audit-max-actions', type=int, default=24); it.add_argument('--ir-accept-coker', action='store_true'); it.add_argument('--next-action-cap', type=int); it.add_argument('--failure-signatures', action='store_true'); it.add_argument('--audit-failure-signature-candidates', action='store_true'); it.add_argument('--failure-signature-audit-max-actions', type=int, default=16); it.add_argument('--failure-signature-accept-coker', action='store_true'); it.add_argument('--failure-signature-accept-margin', type=float, default=0.0); it.add_argument('--failure-signature-accept-max-per-task', type=int, default=16); it.add_argument('--fit-gamma', action='store_true'); it.add_argument('--action-geometry', action='store_true'); it.add_argument('--action-geometry-retrieve', action='store_true'); it.add_argument('--action-geometry-use-qgen-normals', action='store_true'); it.add_argument('--action-geometry-merge-actions', action='store_true'); it.add_argument('--action-geometry-merge-policy', choices=['all','robust-only','accepted-only'], default='robust-only'); it.add_argument('--audit-db', action='store_true'); it.add_argument('--audit-db-path'); it.add_argument('--audit-db-append', action='store_true'); it.add_argument('--audit-scheduler', action='store_true'); it.add_argument('--audit-scheduler-db'); it.add_argument('--audit-scheduler-responses'); it.add_argument('--audit-scheduler-lineage', action='append'); it.add_argument('--audit-scheduler-budget', type=int); it.add_argument('--audit-scheduler-per-task-cap', type=int); it.add_argument('--audit-scheduler-per-source-cap', type=int); it.add_argument('--audit-scheduler-coker-weight', type=float, default=1.0); it.add_argument('--audit-scheduler-carrier-weight', type=float, default=0.5); it.add_argument('--audit-scheduler-uncertainty-weight', type=float, default=0.25); it.add_argument('--audit-scheduler-novelty-weight', type=float, default=0.15); it.add_argument('--audit-scheduler-success-weight', type=float, default=0.25); it.add_argument('--audit-scheduler-cost-weight', type=float, default=0.10); it.add_argument('--audit-scheduler-timeout-weight', type=float, default=0.50); it.add_argument('--action-geometry-top-k', type=int, default=32); it.add_argument('--action-geometry-min-count', type=int, default=1); it.add_argument('--action-geometry-tail-weight', type=float, default=0.25); it.add_argument('--action-geometry-cost-weight', type=float, default=0.05); it.add_argument('--action-geometry-uncertainty-weight', type=float, default=0.10); it.add_argument('--action-geometry-audit-weight', type=float, default=0.20); it.add_argument('--action-geometry-require-carrier-safe', action='store_true'); it.add_argument('--action-geometry-carrier-budget', type=float, default=0.0); it.add_argument('--action-geometry-use-gamma-transition', action='store_true'); it.add_argument('--action-geometry-gamma-aware', action='store_true'); it.add_argument('--action-geometry-gamma-value-mode', choices=['local','finite_horizon','stationary','resolvent','tail','tail_bonus'], default='local'); it.add_argument('--action-geometry-gamma-horizon', type=int, default=4); it.add_argument('--action-geometry-gamma-discount', type=float, default=1.0); it.add_argument('--action-geometry-gamma-tail-value-weight', type=float, default=1.0); it.add_argument('--action-geometry-gamma-stability-margin', type=float, default=0.05); it.add_argument('--action-geometry-gamma-tail-risk-mode', choices=['spectral','normal_amplification','none'], default='spectral'); it.add_argument('--audit-action-geometry-candidates', action='store_true'); it.add_argument('--action-geometry-audit-max-actions', type=int, default=24); it.add_argument('--action-geometry-accept-coker', action='store_true'); it.add_argument('--action-geometry-accept-margin', type=float, default=0.0); it.add_argument('--action-geometry-accept-max-per-task', type=int, default=16); it.add_argument('--action-geometry-accept-cost-weight', type=float, default=0.05); it.add_argument('--action-geometry-accept-carrier-weight', type=float, default=0.7); it.add_argument('--action-geometry-robust-coker-accept', action='store_true'); it.add_argument('--action-geometry-robust-coker-holdout-fraction', type=float, default=0.35); it.add_argument('--action-geometry-robust-coker-uncertainty-weight', type=float, default=0.10); it.add_argument('--action-geometry-robust-coker-carrier-gain-weight', type=float, default=0.25); it.add_argument('--action-geometry-robust-coker-audit-penalty', type=float, default=1.0); it.add_argument('--action-geometry-robust-coker-require-success', action='store_true'); it.add_argument('--quotient-coordinates', action='store_true'); it.add_argument('--quotient-coordinate-ridge', type=float, default=1e-4); it.add_argument('--quotient-coordinate-max-mass', type=float, default=1.0); it.add_argument('--quotient-coordinate-cosine-threshold', type=float, default=0.85); it.add_argument('--quotient-coordinate-min-states', type=int, default=1); it.add_argument('--quotient-coordinate-top-action-scores', type=int, default=128); it.add_argument('--quotient-coordinate-margin-threshold', type=float, default=0.0); it.add_argument('--quotient-coordinate-validate', action='store_true'); it.add_argument('--quotient-coordinate-registry-candidates', action='store_true'); it.add_argument('--quotient-coordinate-registry-max-candidates', type=int, default=64); it.add_argument('--audit-quotient-coordinate-candidates', action='store_true'); it.add_argument('--quotient-coordinate-audit-max-actions', type=int, default=16); it.add_argument('--quotient-coordinate-accept-coker', action='store_true'); it.add_argument('--quotient-coordinate-robust-coker-accept', action='store_true'); it.add_argument('--quotient-coordinate-accept-margin', type=float, default=0.0); it.add_argument('--quotient-coordinate-accept-max-per-task', type=int, default=16); it.add_argument('--quotient-coordinate-accept-cost-weight', type=float, default=0.05); it.add_argument('--quotient-coordinate-accept-carrier-weight', type=float, default=0.7); it.add_argument('--quotient-coordinate-robust-coker-holdout-fraction', type=float, default=0.35); it.add_argument('--quotient-coordinate-robust-coker-uncertainty-weight', type=float, default=0.10); it.add_argument('--quotient-coordinate-robust-coker-carrier-gain-weight', type=float, default=0.25); it.add_argument('--quotient-coordinate-robust-coker-audit-penalty', type=float, default=1.0); it.add_argument('--quotient-coordinate-robust-coker-require-success', action='store_true'); it.add_argument('--action-geometry-use-quotient-normals', action='store_true'); it.add_argument('--contextual-congruence', action='store_true'); it.add_argument('--contextual-congruence-context-mode', choices=['state','task','global'], default='state'); it.add_argument('--contextual-congruence-no-carrier', action='store_true'); it.add_argument('--contextual-congruence-min-count', type=int, default=1); it.add_argument('--contextual-congruence-cosine-threshold', type=float, default=0.95); it.add_argument('--contextual-congruence-distance-threshold', type=float, default=0.25); it.add_argument('--contextual-congruence-min-context-jaccard', type=float, default=0.0); it.add_argument('--quotient-coordinate-merge-actions', action='store_true'); it.add_argument('--quotient-coordinate-merge-policy', choices=['all','robust-only','accepted-only'], default='robust-only'); it.add_argument('--qgen', action='store_true'); it.add_argument('--qgen-merge-actions', action='store_true'); it.add_argument('--qgen-merge-policy', choices=['all','robust-only','accepted-only'], default='all'); it.add_argument('--poms-promote', action='store_true'); it.add_argument('--poms-generate-evidence', action='store_true'); it.add_argument('--poms-evidence-min-relative-residual', type=float, default=0.05); it.add_argument('--poms-evidence-min-residual-norm', type=float, default=1e-6); it.add_argument('--poms-evidence-min-support-count', type=int, default=1); it.add_argument('--poms-evidence-min-margin', type=float, default=0.0); it.add_argument('--poms-evidence-min-robust-margin', type=float, default=0.0); it.add_argument('--poms-evidence-least-repair-epsilon', type=float, default=1e-9); it.add_argument('--poms-promotion-evidence', action='append'); it.add_argument('--poms-promote-parent-nonpaid', action='store_true'); it.add_argument('--poms-promote-dual-certificate', action='store_true'); it.add_argument('--poms-promote-least-repair', action='store_true'); it.add_argument('--poms-declare-canonical', action='store_true'); it.add_argument('--qgen-top-defects', type=int, default=16); it.add_argument('--qgen-top-contexts', type=int, default=32); it.add_argument('--qgen-top-carriers', type=int, default=64); it.add_argument('--qgen-top-failures', type=int, default=32); it.add_argument('--qgen-margin-threshold', type=float, default=0.0); it.add_argument('--qgen-cost-weight', type=float, default=0.05); it.add_argument('--qgen-carrier-weight', type=float, default=0.25); it.add_argument('--qgen-audit-penalty', type=float, default=1.0); it.add_argument('--audit-qgen-candidates', action='store_true'); it.add_argument('--qgen-audit-max-actions', type=int, default=24); it.add_argument('--qgen-accept-coker', action='store_true'); it.add_argument('--qgen-accept-margin', type=float, default=0.0); it.add_argument('--qgen-accept-max-per-task', type=int, default=16); it.add_argument('--qgen-accept-cost-weight', type=float, default=0.05); it.add_argument('--qgen-accept-carrier-weight', type=float, default=0.7); it.add_argument('--qgen-robust-accept', action='store_true'); it.add_argument('--qgen-registry-robust-accept', action='store_true'); it.add_argument('--qgen-robust-coker-accept', action='store_true'); it.add_argument('--qgen-registry-robust-coker-accept', action='store_true'); it.add_argument('--qgen-robust-coker-holdout-fraction', type=float, default=0.35); it.add_argument('--qgen-robust-coker-uncertainty-weight', type=float, default=0.10); it.add_argument('--qgen-robust-coker-carrier-gain-weight', type=float, default=0.25); it.add_argument('--qgen-robust-coker-audit-penalty', type=float, default=1.0); it.add_argument('--qgen-robust-coker-require-success', action='store_true'); it.add_argument('--qgen-robust-z', type=float, default=1.0); it.add_argument('--qgen-robust-min-repeats', type=int, default=1); it.add_argument('--qgen-robust-min-success-rate', type=float, default=1.0); it.add_argument('--qgen-registry-candidates', action='store_true'); it.add_argument('--qgen-registry-max-candidates', type=int, default=64); it.add_argument('--audit-qgen-registry-candidates', action='store_true'); it.add_argument('--qgen-registry-audit-max-actions', type=int, default=16); it.add_argument('--qgen-registry-accept-coker', action='store_true'); it.add_argument('--qgen-registry-accept-margin', type=float, default=0.0); it.add_argument('--qgen-registry-accept-max-per-task', type=int, default=16); it.add_argument('--qgen-registry-accept-cost-weight', type=float, default=0.05); it.add_argument('--qgen-registry-accept-carrier-weight', type=float, default=0.7); 
    # v34 carrier quotient mining / action loop flags.
    it.add_argument('--carrier-quotient', action='store_true')
    it.add_argument('--carrier-quotient-ridge', type=float, default=1e-4)
    it.add_argument('--carrier-quotient-max-mass', type=float, default=1.0)
    it.add_argument('--carrier-quotient-cosine-threshold', type=float, default=0.85)
    it.add_argument('--carrier-quotient-min-states', type=int, default=1)
    it.add_argument('--carrier-quotient-top-action-scores', type=int, default=128)
    it.add_argument('--carrier-quotient-margin-threshold', type=float, default=0.0)
    it.add_argument('--carrier-quotient-no-infer-defect-from-violations', action='store_true')
    it.add_argument('--carrier-quotient-validate', action='store_true')
    it.add_argument('--audit-carrier-quotient-candidates', action='store_true')
    it.add_argument('--carrier-quotient-audit-max-actions', type=int, default=16)
    it.add_argument('--carrier-quotient-accept-coker', action='store_true')
    it.add_argument('--carrier-quotient-robust-coker-accept', action='store_true')
    it.add_argument('--carrier-quotient-accept-margin', type=float, default=0.0)
    it.add_argument('--carrier-quotient-accept-max-per-task', type=int, default=16)
    it.add_argument('--carrier-quotient-accept-cost-weight', type=float, default=0.05)
    it.add_argument('--carrier-quotient-accept-carrier-weight', type=float, default=0.7)
    it.add_argument('--carrier-quotient-robust-coker-holdout-fraction', type=float, default=0.35)
    it.add_argument('--carrier-quotient-robust-coker-uncertainty-weight', type=float, default=0.10)
    it.add_argument('--carrier-quotient-robust-coker-carrier-gain-weight', type=float, default=0.25)
    it.add_argument('--carrier-quotient-robust-coker-audit-penalty', type=float, default=1.0)
    it.add_argument('--carrier-quotient-robust-coker-require-success', action='store_true')
    it.add_argument('--carrier-quotient-merge-actions', action='store_true')
    it.add_argument('--carrier-quotient-merge-policy', choices=['all','robust-only','accepted-only'], default='robust-only')
    add_contextual_probe_args(it); add_response_quotient_args(it);
    # v37 source-budget scheduler for iterate.
    for _parser in (it,):
        _parser.add_argument('--source-budget', action='store_true')
        _parser.add_argument('--audit-source-budget-candidates', action='store_true')
        _parser.add_argument('--source-budget-merge-actions', action='store_true')
        _parser.add_argument('--source-budget-merge-policy', choices=['all','scheduled-only'], default='scheduled-only')
        _parser.add_argument('--source-budget-budget', type=int)
        _parser.add_argument('--source-budget-min-per-source', type=int, default=0)
        _parser.add_argument('--source-budget-max-per-source', type=int)
        _parser.add_argument('--source-budget-per-task-cap', type=int)
        _parser.add_argument('--source-budget-per-action-cap', type=int, default=1)
        _parser.add_argument('--source-budget-allocation-mode', choices=['proportional','score','round_robin'], default='proportional')
        _parser.add_argument('--source-budget-coker-weight', type=float, default=1.0)
        _parser.add_argument('--source-budget-carrier-weight', type=float, default=0.5)
        _parser.add_argument('--source-budget-uncertainty-weight', type=float, default=0.20)
        _parser.add_argument('--source-budget-novelty-weight', type=float, default=0.25)
        _parser.add_argument('--source-budget-lineage-weight', type=float, default=0.15)
        _parser.add_argument('--source-budget-success-weight', type=float, default=0.25)
        _parser.add_argument('--source-budget-cost-weight', type=float, default=0.10)
        _parser.add_argument('--source-budget-timeout-weight', type=float, default=0.50); _parser.add_argument('--source-budget-gamma-aware', action='store_true'); _parser.add_argument('--source-budget-gamma-value-mode', choices=['local','finite_horizon','stationary','resolvent','tail','tail_bonus'], default='finite_horizon'); _parser.add_argument('--source-budget-gamma-horizon', type=int, default=4); _parser.add_argument('--source-budget-gamma-discount', type=float, default=1.0); _parser.add_argument('--source-budget-gamma-value-weight', type=float, default=0.50); _parser.add_argument('--source-budget-gamma-tail-value-weight', type=float); _parser.add_argument('--source-budget-gamma-tail-risk-weight', type=float, default=0.50); _parser.add_argument('--source-budget-gamma-stability-delta', type=float, default=0.05); _parser.add_argument('--source-budget-gamma-tail-risk-mode', choices=['spectral','normal_amplification','none'], default='spectral'); _parser.add_argument('--source-budget-gamma-tail-radius-weight', type=float, default=0.0)
    it.set_defaults(func=cmd_iterate)
    irp=sub.add_parser('iterate-report'); irp.add_argument('--run-dir', required=True); irp.add_argument('--out-json'); irp.add_argument('--out-csv'); irp.set_defaults(func=cmd_iterate_report)
    loop=sub.add_parser('rgc-loop', conflict_handler='resolve'); loop.add_argument('--tasks', required=True); loop.add_argument('--actions'); loop.add_argument('--out', required=True); loop.add_argument('--rounds', type=int, default=2); loop.add_argument('--dry-run', action='store_true'); loop.add_argument('--jobs', type=int, default=1); loop.add_argument('--max-actions', type=int, default=24); loop.add_argument('--candidate-mode', choices=['basic','state'], default='state'); loop.add_argument('--state-candidates', action='store_true'); loop.add_argument('--quotient-tolerance', type=float, default=0.25); loop.add_argument('--carrier-threshold', type=float, default=0.1); loop.add_argument('--lean-cmd', default='lake env lean'); loop.add_argument('--workdir'); loop.add_argument('--timeout-s', type=float, default=20.0); loop.add_argument('--keep-files', action='store_true'); loop.add_argument('--cache-dir'); loop.add_argument('--trace-state', action='store_true'); loop.add_argument('--import-mode', choices=['preserve','auto','core','mathlib'], default='auto'); loop.add_argument('--resume', action='store_true'); loop.add_argument('--flush-every', type=int, default=50); loop.add_argument('--fit-gamma', action='store_true'); loop.add_argument('--gamma-horizon', type=int, default=4); loop.add_argument('--qgen', action='store_true'); loop.add_argument('--qgen-merge-actions', action='store_true'); loop.add_argument('--qgen-top-defects', type=int, default=16); loop.add_argument('--qgen-top-contexts', type=int, default=32); loop.add_argument('--qgen-top-carriers', type=int, default=64); loop.add_argument('--qgen-top-failures', type=int, default=32); loop.add_argument('--qgen-margin-threshold', type=float, default=0.0); loop.add_argument('--mine-min-support', type=int, default=1); loop.add_argument('--mine-min-response-contrast', type=float, default=-1e9); loop.add_argument('--mine-min-stability', type=float, default=0.0); loop.add_argument('--mine-min-intervention-success', type=float, default=0.0); loop.add_argument('--mine-min-coker-reduction', type=float, default=0.0); loop.add_argument('--registry-max-candidates', type=int, default=96); loop.add_argument('--registry-audit-max-actions', type=int, default=24); loop.add_argument('--registry-accept-margin', type=float, default=0.0); loop.add_argument('--registry-accept-max-per-task', type=int, default=16); loop.add_argument('--registry-accept-cost-weight', type=float, default=0.05); loop.add_argument('--registry-accept-carrier-weight', type=float, default=0.7); loop.add_argument('--promote-min-support', type=int, default=1); loop.add_argument('--promote-min-intervention-success', type=float, default=0.1); loop.add_argument('--promote-min-coker-reduction', type=float, default=-1e9); loop.add_argument('--promote-min-promotion-score', type=float, default=-1e9); loop.add_argument('--premise-index', action='store_true'); loop.add_argument('--premise-top-k', type=int, default=8); loop.add_argument('--premise-max-actions', type=int, default=8); loop.add_argument('--audit-premise-candidates', action='store_true'); loop.add_argument('--premise-audit-max-actions', type=int, default=16); loop.add_argument('--merge-premise-actions', action='store_true'); loop.add_argument('--carrier-accept', action='store_true'); loop.add_argument('--carrier-accept-max-actions', type=int, default=8); loop.add_argument('--carrier-accept-margin', type=float, default=0.0); loop.add_argument('--carrier-accept-cost-weight', type=float, default=0.1); loop.add_argument('--promote-carrier-actions', action='store_true'); loop.add_argument('--promote-carrier-min-margin', type=float, default=0.0); loop.add_argument('--next-action-cap', type=int); loop.set_defaults(func=cmd_rgc_loop)

    ep=sub.add_parser('extract-proofs'); ep.add_argument('--trajectories', required=True); ep.add_argument('--tasks', required=True); ep.add_argument('--out', required=True); ep.add_argument('--include-nonproved', action='store_true'); ep.add_argument('--include-partial', action='store_true'); ep.set_defaults(func=cmd_extract_proofs)
    rp=sub.add_parser('replay-proofs'); rp.add_argument('--scripts', required=True); rp.add_argument('--out', required=True); rp.add_argument('--lean-cmd', default='lake env lean'); rp.add_argument('--workdir'); rp.add_argument('--timeout-s', type=float, default=60.0); rp.add_argument('--dry-run', action='store_true'); rp.add_argument('--keep-files', action='store_true'); rp.add_argument('--cache-dir'); rp.add_argument('--trace-state', action='store_true'); rp.set_defaults(func=cmd_replay_proofs)
    xp=sub.add_parser('export-proofs'); xp.add_argument('--scripts', required=True); xp.add_argument('--out', required=True); xp.add_argument('--theorem-prefix', default='rgc_replay'); xp.set_defaults(func=cmd_export_proofs)
    hp=sub.add_parser('harvest-project'); hp.add_argument('--root', required=True); hp.add_argument('--out-tasks'); hp.add_argument('--out-premises'); hp.add_argument('--out-summary'); hp.add_argument('--glob', default='**/*.lean'); hp.add_argument('--no-examples', action='store_true'); hp.add_argument('--no-theorems', action='store_true'); hp.add_argument('--no-lemmas', action='store_true'); hp.add_argument('--max-files', type=int); hp.add_argument('--max-decls', type=int); hp.set_defaults(func=cmd_harvest_project)
    sh=sub.add_parser('shard-jsonl'); sh.add_argument('--input', required=True); sh.add_argument('--out-dir', required=True); sh.add_argument('--shards', type=int, required=True); sh.add_argument('--key', default='task_id'); sh.add_argument('--mode', choices=['hash','round_robin'], default='hash'); sh.add_argument('--prefix', default='shard'); sh.set_defaults(func=cmd_shard_jsonl)
    mj=sub.add_parser('merge-jsonl'); mj.add_argument('--inputs', nargs='+', required=True); mj.add_argument('--out', required=True); mj.add_argument('--dedup-key'); mj.set_defaults(func=cmd_merge_jsonl)
    ic=sub.add_parser('ir-candidates'); ic.add_argument('--ir', required=True); ic.add_argument('--out', required=True); ic.add_argument('--max-candidates', type=int, default=64); ic.set_defaults(func=cmd_ir_candidates)
    cmx=sub.add_parser('carrier-matrix'); cmx.add_argument('--responses', required=True); cmx.add_argument('--out', required=True); cmx.add_argument('--shrink', type=float, default=2.0); cmx.add_argument('--min-count', type=int, default=1); cmx.set_defaults(func=cmd_carrier_matrix)
    cmp=sub.add_parser('carrier-matrix-merge-patches'); cmp.add_argument('--matrix', required=True); cmp.add_argument('--patches', required=True); cmp.add_argument('--out', required=True); cmp.add_argument('--patch-weight', type=float, default=1.0); cmp.add_argument('--require-safe', action='store_true'); cmp.add_argument('--report-out'); cmp.set_defaults(func=cmd_carrier_matrix_merge_patches)
    csa=sub.add_parser('carrier-safe-actions'); csa.add_argument('--actions', required=True); csa.add_argument('--matrix', required=True); csa.add_argument('--out', required=True); csa.add_argument('--budget', type=float, default=0.0); csa.add_argument('--keep-unsafe', action='store_true'); csa.set_defaults(func=cmd_carrier_safe_actions)
    mcr=sub.add_parser('multi-carrier-report'); mcr.add_argument('--matrix', required=True); mcr.add_argument('--defects'); mcr.add_argument('--out'); mcr.set_defaults(func=cmd_multi_carrier_report)
    qg2=sub.add_parser('qgen'); qg2.add_argument('--responses', required=True); qg2.add_argument('--audits'); qg2.add_argument('--out', required=True); qg2.add_argument('--ridge', type=float, default=1e-4); qg2.add_argument('--max-mass', type=float, default=1.0); qg2.add_argument('--top-defects', type=int, default=16); qg2.add_argument('--top-contexts', type=int, default=32); qg2.add_argument('--top-carriers', type=int, default=64); qg2.add_argument('--top-failures', type=int, default=32); qg2.add_argument('--margin-threshold', type=float, default=0.0); qg2.add_argument('--cost-weight', type=float, default=0.05); qg2.add_argument('--carrier-weight', type=float, default=0.25); qg2.add_argument('--audit-penalty', type=float, default=1.0); qg2.set_defaults(func=cmd_qgen)
    qgl=sub.add_parser('qgen-lineage'); qgl.add_argument('--qgen-dir', required=True); qgl.add_argument('--out', required=True); qgl.set_defaults(func=cmd_qgen_lineage); qgal=sub.add_parser('qgen-acceptance-lineage'); qgal.add_argument('--qgen-dir', required=True); qgal.add_argument('--out', required=True); qgal.add_argument('--accepted-actions', action='append'); qgal.add_argument('--acceptance-rows', action='append'); qgal.add_argument('--audit-responses', action='append'); qgal.add_argument('--registry-candidates', action='append'); qgal.set_defaults(func=cmd_qgen_acceptance_lineage)
    qreal=sub.add_parser('qgen-realized-calibration'); qreal.add_argument('--run-dir', required=True); qreal.add_argument('--out-json'); qreal.add_argument('--out-csv'); qreal.set_defaults(func=cmd_qgen_realized_calibration)
    cpa=sub.add_parser('carrier-patch-audit'); cpa.add_argument('--patches', required=True); cpa.add_argument('--responses', required=True); cpa.add_argument('--out-report'); cpa.add_argument('--out-patches'); cpa.add_argument('--min-count', type=int, default=1); cpa.add_argument('--min-mean-delta', type=float, default=0.0); cpa.add_argument('--no-sign-agreement', action='store_true'); cpa.add_argument('--holdout-fraction', type=float, default=0.0); cpa.add_argument('--heldout-min-count', type=int); cpa.add_argument('--heldout-min-mean-delta', type=float); cpa.add_argument('--require-heldout', action='store_true'); cpa.set_defaults(func=cmd_carrier_patch_audit)
    poms=sub.add_parser('poms-status'); poms.add_argument('--run-dir', required=True); poms.add_argument('--out-json'); poms.add_argument('--out-jsonl'); poms.add_argument('--out-csv'); poms.add_argument('--min-realized-goal-response', type=float, default=0.0); poms.add_argument('--require-realized-success', action='store_true'); poms.set_defaults(func=cmd_poms_status)

    pe=sub.add_parser('poms-evidence'); pe.add_argument('--run-dir', required=True); pe.add_argument('--out-json'); pe.add_argument('--out-jsonl'); pe.add_argument('--out-poms'); pe.add_argument('--out-csv'); pe.add_argument('--min-relative-residual', type=float, default=0.05); pe.add_argument('--min-residual-norm', type=float, default=1e-6); pe.add_argument('--min-support-count', type=int, default=1); pe.add_argument('--min-margin', type=float, default=0.0); pe.add_argument('--min-robust-margin', type=float, default=0.0); pe.add_argument('--least-repair-epsilon', type=float, default=1e-9); pe.set_defaults(func=cmd_poms_evidence)
    dor=sub.add_parser('defect-ontology-reconcile'); dor.add_argument('--run-dir'); dor.add_argument('--base-registry'); dor.add_argument('--candidate-atoms', action='append', default=[]); dor.add_argument('--out', required=True); dor.add_argument('--merge-threshold', type=float, default=0.72); dor.add_argument('--shadow-threshold', type=float, default=0.35); dor.add_argument('--novel-threshold', type=float, default=0.18); dor.add_argument('--include-open', action='store_true'); dor.add_argument('--include-shadow', action='store_true'); dor.set_defaults(func=cmd_defect_ontology_reconcile)
    dol=sub.add_parser('defect-ontology-lifecycle'); dol.add_argument('--run-dir'); dol.add_argument('--reconciliation-rows'); dol.add_argument('--split-suggestions'); dol.add_argument('--base-registry'); dol.add_argument('--reconciled-registry'); dol.add_argument('--previous-lifecycle', action='append', default=[]); dol.add_argument('--promotion-rows', action='append', default=[]); dol.add_argument('--validation-rows', action='append', default=[]); dol.add_argument('--out', required=True); dol.add_argument('--min-evidence-score', type=float, default=2.0); dol.add_argument('--min-support-count', type=int, default=1); dol.add_argument('--include-pending', action='store_true'); dol.set_defaults(func=cmd_defect_ontology_lifecycle)
    pp=sub.add_parser('poms-promote'); pp.add_argument('--run-dir', required=True); pp.add_argument('--poms-rows'); pp.add_argument('--evidence', action='append'); pp.add_argument('--out-json'); pp.add_argument('--out-jsonl'); pp.add_argument('--out-csv'); pp.add_argument('--out-promoted-actions'); pp.add_argument('--parent-nonpaid', action='store_true'); pp.add_argument('--dual-certificate', action='store_true'); pp.add_argument('--least-repair', action='store_true'); pp.add_argument('--declare-canonical', action='store_true'); pp.set_defaults(func=cmd_poms_promote)


    rac=sub.add_parser('robust-accept-candidates'); rac.add_argument('--base-responses', required=True); rac.add_argument('--candidate-responses', required=True); rac.add_argument('--shadow-responses'); rac.add_argument('--out', required=True); rac.add_argument('--accepted-actions-out'); rac.add_argument('--summary-out'); rac.add_argument('--margin-threshold', type=float, default=0.0); rac.add_argument('--cost-weight', type=float, default=0.05); rac.add_argument('--carrier-weight', type=float, default=0.7); rac.add_argument('--audit-weight', type=float, default=0.2); rac.add_argument('--disagreement-weight', type=float, default=0.5); rac.add_argument('--require-shadow', action='store_true'); rac.add_argument('--require-success', action='store_true'); rac.set_defaults(func=cmd_robust_accept_candidates)

    rca=sub.add_parser('robust-coker-accept'); rca.add_argument('--base-responses', required=True); rca.add_argument('--candidate-responses', required=True); rca.add_argument('--out-report', required=True); rca.add_argument('--out-actions'); rca.add_argument('--out-rows'); rca.add_argument('--csv-out'); rca.add_argument('--margin-threshold', type=float, default=0.0); rca.add_argument('--holdout-fraction', type=float, default=0.35); rca.add_argument('--ridge', type=float, default=1e-4); rca.add_argument('--max-mass', type=float, default=1.0); rca.add_argument('--cost-weight', type=float, default=0.05); rca.add_argument('--carrier-gain-weight', type=float, default=0.25); rca.add_argument('--carrier-violation-weight', type=float, default=0.7); rca.add_argument('--audit-penalty', type=float, default=1.0); rca.add_argument('--uncertainty-weight', type=float, default=0.10); rca.add_argument('--require-success', action='store_true'); rca.add_argument('--max-actions', type=int); rca.set_defaults(func=cmd_robust_coker_accept)
    sc=sub.add_parser('stage-coker'); sc.add_argument('--base-responses', required=True); sc.add_argument('--stage', action='append', required=True, help='Stage response file, either name=path or path. Repeatable.'); sc.add_argument('--out-report', required=True); sc.add_argument('--out-actions'); sc.add_argument('--out-rows-dir'); sc.add_argument('--csv-out'); sc.add_argument('--margin-threshold', type=float, default=0.0); sc.add_argument('--cost-weight', type=float, default=0.05); sc.add_argument('--carrier-weight', type=float, default=0.25); sc.add_argument('--audit-penalty', type=float, default=1.0); sc.add_argument('--require-success', action='store_true'); sc.add_argument('--max-actions', type=int); sc.set_defaults(func=cmd_stage_coker)
    cs=sub.add_parser('coker-synthesize'); cs.add_argument('--base-responses', required=True); cs.add_argument('--archetype-responses'); cs.add_argument('--out-actions', required=True); cs.add_argument('--out-profiles'); cs.add_argument('--out-archetypes'); cs.add_argument('--out-atoms'); cs.add_argument('--out-summary'); cs.add_argument('--archetype-mode', choices=['tactic','class','class+tactic_head'], default='tactic'); cs.add_argument('--ridge', type=float, default=1e-4); cs.add_argument('--max-mass', type=float, default=1.0); cs.add_argument('--cost-weight', type=float, default=0.05); cs.add_argument('--carrier-weight', type=float, default=0.25); cs.add_argument('--uncertainty-weight', type=float, default=0.10); cs.add_argument('--failure-penalty', type=float, default=0.25); cs.add_argument('--margin-threshold', type=float, default=0.0); cs.add_argument('--min-archetype-support', type=int, default=1); cs.add_argument('--max-per-state', type=int, default=16); cs.add_argument('--top-k-residual', type=int, default=8); cs.set_defaults(func=cmd_coker_synthesize)
    qg=sub.add_parser('quality-gates'); qg.add_argument('--run-dir', required=True); qg.add_argument('--out'); qg.add_argument('--csv-out'); qg.add_argument('--min-audits', type=int, default=50); qg.add_argument('--min-success-rate', type=float, default=0.05); qg.add_argument('--min-mean-goal-response', type=float, default=0.0); qg.add_argument('--min-registry-accept', type=int, default=1); qg.add_argument('--min-gamma-improvement', type=float); qg.add_argument('--max-gamma-cocycle-rel', type=float); qg.add_argument('--min-qgen-realized-match-rate', type=float); qg.add_argument('--min-qgen-realized-success-rate', type=float); qg.add_argument('--min-qgen-realized-goal-response', type=float); qg.add_argument('--min-qgen-patch-audit-accept-rate', type=float); qg.set_defaults(func=cmd_quality_gates)
    syn=sub.add_parser('synthesize-from-coker'); syn.add_argument('--base-responses', required=True); syn.add_argument('--out-actions', required=True); syn.add_argument('--out-report'); syn.add_argument('--out-profiles'); syn.add_argument('--out-archetypes'); syn.add_argument('--out-atoms'); syn.add_argument('--archetype-responses'); syn.add_argument('--archetype-mode', choices=['tactic','class','class+tactic_head'], default='tactic'); syn.add_argument('--ridge', type=float, default=1e-4); syn.add_argument('--max-mass', type=float, default=1.0); syn.add_argument('--margin-threshold', type=float, default=0.0); syn.add_argument('--cost-weight', type=float, default=0.05); syn.add_argument('--carrier-weight', type=float, default=0.25); syn.add_argument('--uncertainty-weight', type=float, default=0.10); syn.add_argument('--failure-penalty', type=float, default=0.25); syn.add_argument('--min-archetype-support', type=int, default=1); syn.add_argument('--max-residual-keys', type=int, default=8); syn.add_argument('--max-actions-per-state', type=int, default=16); syn.set_defaults(func=cmd_synthesize_from_coker)
    il=sub.add_parser('init-lake'); il.add_argument('--out', required=True); il.add_argument('--name', default='LeanRGCPlayground'); il.add_argument('--no-mathlib', action='store_true'); il.set_defaults(func=cmd_init_lake)
    ag=sub.add_parser('action-geometry-registry'); ag.add_argument('--responses', required=True); ag.add_argument('--out', required=True); ag.add_argument('--summary-out'); ag.add_argument('--actions'); ag.add_argument('--transitions'); ag.add_argument('--min-count', type=int, default=1); ag.set_defaults(func=cmd_action_geometry_registry)
    agr=sub.add_parser('action-geometry-retrieve'); agr.add_argument('--registry', required=True); agr.add_argument('--out', required=True); agr.add_argument('--summary-out'); agr.add_argument('--response-normal-json'); agr.add_argument('--response-normal'); agr.add_argument('--carrier-normal-json'); agr.add_argument('--carrier-normal'); agr.add_argument('--top-k', type=int); agr.add_argument('--tail-weight', type=float, default=0.25); agr.add_argument('--cost-weight', type=float, default=0.05); agr.add_argument('--uncertainty-weight', type=float, default=0.10); agr.add_argument('--audit-weight', type=float, default=0.20); agr.add_argument('--require-carrier-safe', action='store_true'); agr.add_argument('--carrier-budget', type=float, default=0.0); agr.add_argument('--gamma-aware', action='store_true'); agr.add_argument('--gamma-value-mode', choices=['local','finite_horizon','finite-horizon','stationary','resolvent','tail','tail_bonus'], default='local'); agr.add_argument('--gamma-horizon', type=int, default=4); agr.add_argument('--gamma-discount', type=float, default=1.0); agr.add_argument('--gamma-value-weight', type=float, default=0.50); agr.add_argument('--gamma-stability-delta', type=float, default=0.05); agr.add_argument('--gamma-stability-margin', type=float, default=0.05); agr.add_argument('--gamma-tail-risk-mode', choices=['spectral','normal','normal_amplification','coker','coker_normal','none','off'], default='spectral'); agr.set_defaults(func=cmd_action_geometry_retrieve)
    aca=sub.add_parser('action-cocycle-audit'); aca.add_argument('--registry', required=True); aca.add_argument('--compositions', required=True); aca.add_argument('--out', required=True); aca.add_argument('--summary-out'); aca.add_argument('--accept-threshold', type=float, default=1.0); aca.set_defaults(func=cmd_action_cocycle_audit)
    atc=sub.add_parser('arithmetic-teacher-constraints'); atc.add_argument('--actions', required=True); atc.add_argument('--out', required=True); atc.add_argument('--summary-out'); atc.set_defaults(func=cmd_arithmetic_teacher_constraints)
    atg=sub.add_parser('arithmetic-teacher-graph'); atg.add_argument('--structured-states', required=True); atg.add_argument('--out', required=True); atg.add_argument('--identities'); atg.add_argument('--actions'); atg.add_argument('--responses'); atg.add_argument('--max-transforms-per-state', type=int, default=32); atg.add_argument('--no-actions', action='store_true'); atg.set_defaults(func=cmd_arithmetic_teacher_graph)
    ata=sub.add_parser('arithmetic-teacher-audit'); ata.add_argument('--transformations', required=True); ata.add_argument('--structured-states', required=True); ata.add_argument('--out-rows', required=True); ata.add_argument('--report-out'); ata.set_defaults(func=cmd_arithmetic_teacher_audit)
    atk=sub.add_parser('arithmetic-teacher-kernel-audit'); atk.add_argument('--transformations', required=True); atk.add_argument('--tasks', required=True); atk.add_argument('--out', required=True); atk.add_argument('--identities'); atk.add_argument('--structured-states'); atk.add_argument('--max-transitions', type=int); atk.add_argument('--lean-cmd', default='lake env lean'); atk.add_argument('--workdir'); atk.add_argument('--timeout-s', type=float, default=20.0); atk.add_argument('--dry-run', action='store_true'); atk.add_argument('--keep-files', action='store_true'); atk.add_argument('--cache-dir'); atk.add_argument('--trace-state', action='store_true'); atk.add_argument('--server-cmd'); atk.add_argument('--server-backend', choices=['auto','dry_run','file','file_fallback','jsonl','persistent','native'], default='auto'); atk.add_argument('--server-no-fallback', action='store_true'); atk.add_argument('--native-exec-mode', choices=['source_check','heuristic','kernel_rpc'], default='source_check'); atk.set_defaults(func=cmd_arithmetic_teacher_kernel_audit)
    atgeom=sub.add_parser('arithmetic-teacher-transition-geometry'); atgeom.add_argument('--kernel-audit-rows', required=True); atgeom.add_argument('--out', required=True); atgeom.add_argument('--summary-out'); atgeom.add_argument('--min-count', type=int, default=1); atgeom.set_defaults(func=cmd_arithmetic_teacher_transition_geometry)
    atcyc=sub.add_parser('arithmetic-teacher-cocycle-audit'); atcyc.add_argument('--transition-geometry', required=True); atcyc.add_argument('--out', required=True); atcyc.add_argument('--summary-out'); atcyc.add_argument('--compositions'); atcyc.add_argument('--accept-threshold', type=float, default=1.0); atcyc.add_argument('--min-verified-rate', type=float, default=0.0); atcyc.add_argument('--max-tail-radius', type=float); atcyc.add_argument('--max-auto-pairs', type=int, default=0); atcyc.add_argument('--gamma-constraints-out'); atcyc.add_argument('--gamma-constraints-summary-out'); atcyc.set_defaults(func=cmd_arithmetic_teacher_cocycle_audit)
    atloop=sub.add_parser('arithmetic-teacher-cocycle'); atloop.add_argument('--kernel-audit-rows', required=True); atloop.add_argument('--out', required=True); atloop.add_argument('--compositions'); atloop.add_argument('--min-count', type=int, default=1); atloop.add_argument('--accept-threshold', type=float, default=1.0); atloop.add_argument('--min-verified-rate', type=float, default=0.0); atloop.add_argument('--max-tail-radius', type=float); atloop.add_argument('--max-auto-pairs', type=int, default=0); atloop.set_defaults(func=cmd_arithmetic_teacher_cocycle)

    sse=sub.add_parser('structured-state-extract'); sse.add_argument('--tasks'); sse.add_argument('--audits'); sse.add_argument('--kernel-jsonl'); sse.add_argument('--out', required=True); sse.add_argument('--summary-out'); sse.set_defaults(func=cmd_structured_state_extract)
    adb=sub.add_parser('audit-db-build'); adb.add_argument('--run-dir', required=True); adb.add_argument('--db'); adb.add_argument('--append', action='store_true'); adb.add_argument('--out-json'); adb.set_defaults(func=cmd_audit_db_build)
    adq=sub.add_parser('audit-db-query'); adq.add_argument('--db', required=True); adq.add_argument('--sql'); adq.add_argument('--sql-file'); adq.add_argument('--max-rows', type=int, default=1000); adq.add_argument('--print-rows', type=int, default=20); adq.add_argument('--out-json'); adq.add_argument('--out-csv'); adq.set_defaults(func=cmd_audit_db_query)

    sch=sub.add_parser('audit-schedule'); sch.add_argument('--db'); sch.add_argument('--candidates', required=True); sch.add_argument('--out', dest='out', required=False); sch.add_argument('--out-actions', dest='out_actions'); sch.add_argument('--out-rows'); sch.add_argument('--report-out'); sch.add_argument('--top-k', type=int, default=32); sch.add_argument('--max-per-task', type=int); sch.add_argument('--min-score', type=float); sch.add_argument('--coker-weight', type=float, default=1.0); sch.add_argument('--carrier-weight', type=float, default=0.5); sch.add_argument('--novelty-weight', type=float, default=0.25); sch.add_argument('--uncertainty-weight', type=float, default=0.25); sch.add_argument('--success-weight', type=float, default=0.25); sch.add_argument('--cost-weight', type=float, default=0.10); sch.add_argument('--carrier-violation-weight', type=float, default=0.75); sch.add_argument('--prior-weight', type=float, default=1.0); sch.add_argument('--response-normal'); sch.add_argument('--carrier-normal'); sch.set_defaults(func=cmd_audit_schedule)
    sbs=sub.add_parser('source-budget-schedule')
    sbs.add_argument('--candidates', action='append', help='Candidate action JSONL. May be passed multiple times. Accepts PATH or SOURCE=PATH.')
    sbs.add_argument('--source', action='append', help='Backward-compatible alias for --candidates; accepts SOURCE=PATH.')
    sbs.add_argument('--run-dir', help='Discover known candidate-source files under a run directory.')
    sbs.add_argument('--out-actions', required=True)
    sbs.add_argument('--out-rows')
    sbs.add_argument('--out-report')
    sbs.add_argument('--db')
    sbs.add_argument('--history-responses', action='append')
    sbs.add_argument('--lineage', action='append')
    sbs.add_argument('--response-normal')
    sbs.add_argument('--response-normal-json')
    sbs.add_argument('--carrier-normal')
    sbs.add_argument('--carrier-normal-json')
    sbs.add_argument('--budget', type=int, default=64)
    sbs.add_argument('--min-per-source', type=int, default=0)
    sbs.add_argument('--max-per-source', type=int)
    sbs.add_argument('--per-task-cap', type=int)
    sbs.add_argument('--per-action-cap', type=int, default=1)
    sbs.add_argument('--source-exploration-weight', type=float, default=0.25)
    sbs.add_argument('--source-fairness-power', type=float, default=0.5)
    sbs.add_argument('--score-metric', choices=['score_per_cost','score','response'], default='score_per_cost')
    sbs.add_argument('--min-score', type=float)
    sbs.add_argument('--coker-weight', type=float, default=1.0)
    sbs.add_argument('--carrier-weight', type=float, default=0.5)
    sbs.add_argument('--uncertainty-weight', type=float, default=0.25)
    sbs.add_argument('--novelty-weight', type=float, default=0.15)
    sbs.add_argument('--success-weight', type=float, default=0.25)
    sbs.add_argument('--cost-weight', type=float, default=0.10)
    sbs.add_argument('--timeout-weight', type=float, default=0.50); sbs.add_argument('--gamma-aware', action='store_true'); sbs.add_argument('--gamma-value-mode', choices=['local','finite_horizon','stationary','resolvent','tail','tail_bonus'], default='finite_horizon'); sbs.add_argument('--gamma-horizon', type=int, default=4); sbs.add_argument('--gamma-discount', type=float, default=1.0); sbs.add_argument('--gamma-value-weight', type=float, default=0.50); sbs.add_argument('--gamma-tail-value-weight', type=float); sbs.add_argument('--gamma-tail-risk-weight', type=float, default=0.50); sbs.add_argument('--gamma-stability-delta', type=float, default=0.05); sbs.add_argument('--gamma-tail-risk-mode', choices=['spectral','normal_amplification','none'], default='spectral'); sbs.add_argument('--gamma-tail-radius-weight', type=float, default=0.0)
    sbs.set_defaults(func=cmd_source_budget_schedule)


    ccand=sub.add_parser('contextual-candidates'); ccand.add_argument('--actions', required=True); ccand.add_argument('--out', required=True); ccand.add_argument('--contexts'); ccand.add_argument('--summary-out'); ccand.add_argument('--max-left', type=int, default=8); ccand.add_argument('--max-right', type=int, default=8); ccand.add_argument('--max-core', type=int); ccand.add_argument('--max-candidates', type=int); ccand.add_argument('--no-identity', action='store_true'); ccand.add_argument('--no-left', action='store_true'); ccand.add_argument('--no-right', action='store_true'); ccand.set_defaults(func=cmd_contextual_candidates)
    ccong=sub.add_parser('contextual-congruence'); ccong.add_argument('--responses', required=True); ccong.add_argument('--out', required=True); ccong.add_argument('--actions'); ccong.add_argument('--min-contexts', type=int, default=1); ccong.add_argument('--cosine-threshold', type=float, default=0.95); ccong.add_argument('--max-distance', type=float); ccong.set_defaults(func=cmd_contextual_congruence)
    rq=sub.add_parser('response-quotient-registry'); rq.add_argument('--classes'); rq.add_argument('--congruence-dir'); rq.add_argument('--actions'); rq.add_argument('--out', required=True); rq.add_argument('--min-members', type=int, default=1); rq.add_argument('--min-quality', type=float); rq.set_defaults(func=cmd_response_quotient_registry)
    rqp=sub.add_parser('response-quotient-project-actions'); rqp.add_argument('--actions', required=True); rqp.add_argument('--registry', required=True); rqp.add_argument('--out', required=True); rqp.add_argument('--summary-out'); rqp.add_argument('--drop-unmapped', action='store_true'); rqp.add_argument('--annotate-only', action='store_true'); rqp.set_defaults(func=cmd_response_quotient_project_actions)
    cqm=sub.add_parser('carrier-quotient-mine'); cqm.add_argument('--responses', required=True); cqm.add_argument('--out', required=True); cqm.add_argument('--ridge', type=float, default=1e-4); cqm.add_argument('--max-mass', type=float, default=1.0); cqm.add_argument('--cosine-threshold', type=float, default=0.85); cqm.add_argument('--min-states', type=int, default=1); cqm.add_argument('--top-action-scores', type=int, default=128); cqm.add_argument('--margin-threshold', type=float, default=0.0); cqm.add_argument('--no-registry', action='store_true'); cqm.set_defaults(func=cmd_carrier_quotient_mine)
    qc=sub.add_parser('quotient-coordinates'); qc.add_argument('--responses', required=True); qc.add_argument('--out', required=True); qc.add_argument('--ridge', type=float, default=1e-4); qc.add_argument('--max-mass', type=float, default=1.0); qc.add_argument('--cosine-threshold', type=float, default=0.85); qc.add_argument('--min-states', type=int, default=1); qc.add_argument('--top-action-scores', type=int, default=128); qc.add_argument('--margin-threshold', type=float, default=0.0); qc.add_argument('--no-registry', action='store_true'); qc.add_argument('--no-normal', action='store_true'); qc.add_argument('--validate', action='store_true'); qc.set_defaults(func=cmd_quotient_coordinates)
    cq=sub.add_parser('carrier-quotient'); cq.add_argument('--responses', required=True); cq.add_argument('--out', required=True); cq.add_argument('--ridge', type=float, default=1e-4); cq.add_argument('--max-mass', type=float, default=1.0); cq.add_argument('--cosine-threshold', type=float, default=0.85); cq.add_argument('--min-states', type=int, default=1); cq.add_argument('--top-action-scores', type=int, default=128); cq.add_argument('--margin-threshold', type=float, default=0.0); cq.add_argument('--no-registry', action='store_true'); cq.add_argument('--no-incidence', action='store_true'); cq.add_argument('--validate', action='store_true'); cq.set_defaults(func=cmd_carrier_quotient)
    cqv=sub.add_parser('carrier-quotient-validate'); cqv.add_argument('--coordinates', required=True); cqv.add_argument('--responses', required=True); cqv.add_argument('--out-report', required=True); cqv.add_argument('--out-rows', required=True); cqv.add_argument('--min-support-score', type=float, default=0.0); cqv.add_argument('--over-refinement-ratio', type=float, default=2.0); cqv.set_defaults(func=cmd_carrier_quotient_validate)
    qcv=sub.add_parser('quotient-coordinate-validate'); qcv.add_argument('--coordinates', required=True); qcv.add_argument('--responses', required=True); qcv.add_argument('--out-report', required=True); qcv.add_argument('--out-rows', required=True); qcv.add_argument('--holdout-fraction', type=float, default=0.35); qcv.add_argument('--min-support-score', type=float, default=0.0); qcv.add_argument('--over-refinement-ratio', type=float, default=2.0); qcv.set_defaults(func=cmd_quotient_coordinate_validate)
    crc=sub.add_parser('contextual-response-congruence'); crc.add_argument('--responses', required=True); crc.add_argument('--out', required=True); crc.add_argument('--context-mode', choices=['state','task','global'], default='state'); crc.add_argument('--no-carrier', action='store_true'); crc.add_argument('--min-count', type=int, default=1); crc.add_argument('--cosine-threshold', type=float, default=0.95); crc.add_argument('--distance-threshold', type=float, default=0.25); crc.add_argument('--min-context-jaccard', type=float, default=0.0); crc.set_defaults(func=cmd_contextual_response_congruence)

    gst=sub.add_parser('goal-state-transitions'); gst.add_argument('--audits', required=True); gst.add_argument('--out', required=True); gst.add_argument('--summary-out'); gst.set_defaults(func=cmd_goal_state_transitions)
    ksg=sub.add_parser('kernel-state-graphs'); ksg.add_argument('--kernel-jsonl', required=True); ksg.add_argument('--out', required=True); ksg.add_argument('--summary-out'); ksg.set_defaults(func=cmd_kernel_state_graphs)
    ksn=sub.add_parser('kernel-state-normalize'); ksn.add_argument('--kernel-jsonl', required=True); ksn.add_argument('--out', required=True); ksn.add_argument('--summary-out'); ksn.set_defaults(func=cmd_kernel_state_normalize)
    ksp=sub.add_parser('kernel-state-probe'); ksp.add_argument('--task-json', required=True); ksp.add_argument('--action-json', required=True); ksp.add_argument('--out'); ksp.add_argument('--backend', choices=['dry_run','file'], default='dry_run'); ksp.add_argument('--lean-cmd', default='lake env lean'); ksp.add_argument('--workdir'); ksp.add_argument('--timeout-s', type=float, default=20.0); ksp.add_argument('--keep-files', action='store_true'); ksp.add_argument('--cache-dir'); ksp.add_argument('--trace-state', action='store_true'); ksp.set_defaults(func=cmd_kernel_state_probe)

    aas=sub.add_parser('active-audit-schedule')
    aas.add_argument('--candidates', action='append', required=True, help='Candidate action JSONL. May be passed multiple times.')
    aas.add_argument('--db', help='Optional audit.db for historical response/cost stats.')
    aas.add_argument('--history-responses', action='append', help='Optional historical responses.jsonl, may repeat.')
    aas.add_argument('--lineage', action='append', help='Optional lineage JSON/JSONL for novelty features, may repeat.')
    aas.add_argument('--response-normal')
    aas.add_argument('--response-normal-json')
    aas.add_argument('--carrier-normal')
    aas.add_argument('--carrier-normal-json')
    aas.add_argument('--budget', type=int, default=32)
    aas.add_argument('--per-source-cap', type=int)
    aas.add_argument('--per-action-cap', type=int, default=1)
    aas.add_argument('--min-priority', type=float)
    aas.add_argument('--coker-weight', type=float, default=1.0)
    aas.add_argument('--carrier-weight', type=float, default=0.5)
    aas.add_argument('--uncertainty-weight', type=float, default=0.25)
    aas.add_argument('--novelty-weight', type=float, default=0.25)
    aas.add_argument('--success-weight', type=float, default=0.25)
    aas.add_argument('--cost-weight', type=float, default=1.0)
    aas.add_argument('--audit-risk-weight', type=float, default=0.25)
    aas.add_argument('--out-actions', required=True)
    aas.add_argument('--out-schedule', required=True)
    aas.add_argument('--out-report', required=True)
    aas.set_defaults(func=cmd_active_audit_schedule)
    return p


def main(argv: list[str] | None = None) -> int:
    parser=build_parser()
    args=parser.parse_args(argv)
    return int(args.func(args))


if __name__ == '__main__':
    raise SystemExit(main())
