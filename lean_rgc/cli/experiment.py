from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np

from ..schemas import LeanTask, ProofState, TacticAction, DefectVector, ResponseRecord, read_jsonl, stable_hash, write_jsonl, write_records
from ..defects import ProofDefectExtractor
from ..candidates import TacticCandidateGenerator, CandidateGeneratorConfig
from ..carrier_exposure import StateDependentCandidateGenerator
from ..carrier import CarrierGenerator, carrier_coker_proxy
from ..carrier_acceptance import accept_carrier_contexts, context_to_actions
from ..carrier_promotion import write_accepted_carrier_actions
from ..candidate_acceptance import accept_candidates_file, promote_registry_from_acceptance
from ..quotient import ResponseQuotientDiscovery
from ..response_model import ResponseModelConfig, train_response_model, predict_response_file, ResponseModel
from ..trajectory import LeanTrajectoryRunner, TrajectoryRunnerConfig, write_trajectories
from ..dataset import summarize_response_rows, split_jsonl, transitions_from_responses, write_run_report
from ..lake_template import write_lake_template
from ..batch import SCHEMA_AUDIT_ROW, SCHEMA_DEFECT_ROW, SCHEMA_RESPONSE_ROW, run_micro_audit_batch
from ..gamma import GammaAuditor
from ..selector import RGCTacticSelector, SelectorConfig
from ..goal_shape import parse_goal_shape
from ..defect_registry import seed_defect_registry
from ..defect_miner import mine_defects as mine_defects_file
from ..auto_defects import AutoDefectExtractor
from ..proof_ir import ir_rows_from_tasks, ir_rows_from_audits, parse_audits_to_ir
from ..focused_analysis import summarize_exposures
from ..registry_candidates import registry_candidates_cli
from ..iteration import merge_action_files, compare_pipeline_dirs
from ..corebench import write_corebench
from ..registry_promotion import promote_registry_file
from ..registry_acceptance import run_registry_acceptance
from ..robust_acceptance import run_robust_acceptance
from ..premise_index import build_premise_index, PremiseIndex, premise_actions_from_hits
from ..defect_ontology_lifecycle import run_defect_ontology_lifecycle
from ..premise_retrieval import build_premise_index_from_tasks, premise_candidates_for_tasks
from ..ir_defects import ir_defects_file
from ..project_harvest import harvest_lean_project
from ..sharding import shard_jsonl, merge_jsonl
from ..audit_env_profile import profile_audit_environment
from ..ir_candidates import ir_candidates_file
from ..multicarrier import build_carrier_matrix_from_responses, annotate_actions_with_carrier_matrix, multi_carrier_report, merge_carrier_incidence_patches, carrier_patch_report
from ..exposure_frontier import write_exposure_frontiers
from ..focused import run_focused_micro_audit
from ..action_analysis import write_action_group_report
from ..response_eval import evaluate_response_model
from ..stage_coker import run_stage_coker
from ..quality import quality_gates_for_run, write_quality_report
from ..failure_signatures import mine_failure_signatures
from ..exposure_audit import exposure_actions_for_tasks, summarize_exposure_audit
from ..iteration_report import collect_iteration_report
from ..stage_report import write_stage_report, default_pipeline_stages
from ..proof_replay import scripts_from_trajectories, replay_proof_scripts, export_proof_file
from ..coker_synthesis import run_coker_synthesis
from ..qgen import qgen_from_files
from ..lineage import build_qgen_lineage, build_qgen_acceptance_lineage
from ..robust_coker import run_robust_coker_acceptance
from ..robust_acceptance import robust_accept_candidates_file
from ..realized_response import collect_qgen_realized_calibration
from ..carrier_patch_audit import audit_carrier_incidence_patches
from ..poms_status import collect_poms_status
from ..poms_promotion import collect_poms_promotion
from ..promotion_evidence import generate_promotion_evidence
from ..action_geometry import build_action_geometry_registry, score_action_geometry_registry, audit_action_cocycles, teacher_constraints_from_arithmetic_actions
from ..action_geometry_loop import run_action_geometry_from_qgen
from ..audit_db import build_audit_db
from ..audit_job_queue import audit_queue_status, enqueue_audit_jobs, init_audit_queue_db, project_fingerprint
from ..audit_pruning import prune_actions_file
from ..data.store import build_run_db
from ..lean.bulk_executor import BulkAuditConfig, bulk_audit_to_files
from ..lean.executor import LeanExecutor, LeanExecutorConfig
from ..lean.frontier import build_frontiers, expose_frontier_files
from ..lean.server import LeanServerConfig
from ..lean.worker_supervisor import enqueue_and_run_supervised_audit, run_bulk_audit_queue, run_supervised_audit_queue
from .common import (
    _actions_for_tasks,
    _executor_from_args,
    _load_actions,
    _load_actions_grouped,
    _load_tasks,
    _normalize_tasks_imports,
    add_exec_args,
)
from ..timeout_ledger import timeout_ledger_report
from ..action_quarantine import action_quarantine_report, export_quarantined_actions
from ..repair_db import failure_attribution_report
from ..poms_promotion_service import poms_promotion_decisions, run_poms_promotion_service
from ..active_audit_scheduler import active_audit_schedule_from_files, SchedulerConfig, _read_json_or_file
from ..quotient_coordinates import quotient_coordinates_from_files
from ..carrier_quotient import carrier_quotient_from_files, validate_carrier_quotient_coordinates
from ..quotient_coordinate_loop import run_quotient_coordinate_loop, validate_quotient_coordinates
from ..contextual_congruence import (
    ContextualProbeConfig,
    generate_contextual_probe_actions, generate_contextual_candidates, generate_contextual_composite_actions,
    build_contextual_response_fingerprints, mine_action_response_congruence,
    contextual_congruence_from_files, contextual_response_congruence_from_files,
    action_classes_to_registry,
)
from ..premise_response import build_premise_response_registry, retrieve_premise_responses, write_premise_retrieved_actions, mine_premise_quotient, _parse_json_or_file
from ..relaxed_species import write_relaxed_species_registry
from ..crg_registry import SCHEMA_REPAIR_SPECIES_REGISTRY, build_repair_species_registry
from ..crg_problem import build_crg_problems
from ..nonlinear_generator import generate_nonlinear_repair_candidates
from ..crg_hardening import harden_crg_candidates
from ..crg_audit import audit_crg_candidates
from ..hardening_gap_report import build_hardening_gap_report
from ..repair_gradient_flow import repair_gradient_flow_steps
from ..concept_geometry import build_concept_geometry
from ..concept_search import search_concepts
from ..concept_hardening import decode_concepts_to_repair_atoms
from ..source_budget_scheduler import source_budget_schedule_from_files, SourceBudgetConfig, _read_json_or_file as _read_source_budget_json_or_file
from ..defect_ontology import reconcile_defect_ontology
from ..arithmetic_teacher import generate_arithmetic_teacher_graph, audit_arithmetic_teacher_transitions
from ..arithmetic_teacher_kernel_audit import audit_arithmetic_teacher_kernel_transitions
from ..arithmetic_teacher_cocycle import arithmetic_teacher_cocycle_from_files, build_arithmetic_teacher_transition_geometry, audit_arithmetic_teacher_cocycles, write_arithmetic_teacher_gamma_constraints
from ..gamma_transition_learner import learn_gamma_transition_model, merge_gamma_transition_patches_into_action_geometry
from ..kernel_context_cache import audit_contextual_candidates_with_kernel_cache
from ..minif2f_adapter import DEFAULT_MINIF2F_LEAN4_URL, build_minif2f_tasks, fetch_minif2f


def _action_task_id(row: dict[str, Any]) -> str | None:
    meta = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
    task_id = row.get("task_id") or meta.get("task_id")
    return str(task_id) if task_id else None


def _is_contextual_baseline_row(row: dict[str, Any]) -> bool:
    meta = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
    return bool(meta.get("is_contextual_baseline")) or str(meta.get("source") or "").startswith("premise_contextual_baseline")


def _clone_action_for_task(row: dict[str, Any], task_id: str, *, role: str = "task_budget") -> dict[str, Any]:
    out = dict(row)
    meta = dict(out.get("metadata") if isinstance(out.get("metadata"), dict) else {})
    source_action_id = str(out.get("action_id") or stable_hash(out, 12))
    task_suffix = stable_hash({"action_id": source_action_id, "task_id": task_id, "role": role}, 10)
    out["action_id"] = f"{source_action_id}__task_{task_suffix}"
    out["task_id"] = task_id
    out["metadata"] = {
        **meta,
        "task_id": task_id,
        "source_action_id": source_action_id,
        "task_budget_materialized": True,
        "task_budget_role": role,
    }
    return out


def _materialize_total_budget_task_actions(
    actions_path: str | Path,
    tasks: list[LeanTask],
    out_path: str | Path,
    *,
    budget: int | None,
    require_baseline_pairs: bool = False,
) -> dict[str, Any]:
    """Convert a global scheduled action budget into a total audit-job budget.

    `_pipeline_audit` treats global actions as a per-task pool.  For scheduled
    contextual candidates, users usually mean "audit at most N total probes",
    not "audit N probes on every task".  This helper assigns global rows to
    concrete tasks, preserving baseline/probe context pairs on the same task.
    """
    rows = [r for r in read_jsonl(actions_path) if isinstance(r, dict)]
    task_ids = [t.task_id for t in tasks]
    cap = max(0, int(budget or len(rows)))
    if not rows or not task_ids or cap <= 0:
        write_jsonl(out_path, [])
        summary = {
            "schema_version": "lean-rgc-task-budget-materialized-actions-v64.1",
            "source": str(actions_path),
            "out": str(out_path),
            "budget": cap,
            "n_source_actions": len(rows),
            "n_tasks": len(task_ids),
            "n_actions": 0,
            "n_baselines": 0,
            "n_probes": 0,
            "canonical_status": "task_budget_materialization_chart_not_canonical",
        }
        return summary

    baselines_by_id = {str(r.get("action_id")): r for r in rows if _is_contextual_baseline_row(r)}
    probes = [r for r in rows if not _is_contextual_baseline_row(r)]
    emitted: list[dict[str, Any]] = []
    emitted_baseline_for_task: dict[tuple[str, str], str] = {}
    task_index = 0

    def choose_task(row: dict[str, Any]) -> str:
        nonlocal task_index
        explicit = _action_task_id(row)
        if explicit:
            return explicit
        task_id = task_ids[task_index % len(task_ids)]
        task_index += 1
        return task_id

    for probe in probes:
        if len(emitted) >= cap:
            break
        meta = probe.get("metadata") if isinstance(probe.get("metadata"), dict) else {}
        task_id = choose_task(probe)
        baseline_id = str(meta.get("baseline_action_id") or "")
        cloned_baseline_id = ""
        if baseline_id and baseline_id in baselines_by_id:
            key = (task_id, baseline_id)
            if key not in emitted_baseline_for_task:
                if len(emitted) + (2 if require_baseline_pairs else 1) > cap:
                    break
                base = _clone_action_for_task(baselines_by_id[baseline_id], task_id, role="baseline")
                emitted_baseline_for_task[key] = str(base.get("action_id"))
                emitted.append(base)
            cloned_baseline_id = emitted_baseline_for_task[key]
        elif require_baseline_pairs:
            continue
        if len(emitted) >= cap:
            break
        cloned_probe = _clone_action_for_task(probe, task_id, role="probe")
        cloned_meta = dict(cloned_probe.get("metadata") if isinstance(cloned_probe.get("metadata"), dict) else {})
        if cloned_baseline_id:
            cloned_meta["baseline_action_id"] = cloned_baseline_id
        cloned_probe["metadata"] = cloned_meta
        emitted.append(cloned_probe)

    if not probes:
        for i, row in enumerate(rows[:cap]):
            emitted.append(_clone_action_for_task(row, task_ids[i % len(task_ids)], role="scheduled"))

    write_jsonl(out_path, emitted)
    n_baselines = sum(1 for r in emitted if _is_contextual_baseline_row(r))
    summary = {
        "schema_version": "lean-rgc-task-budget-materialized-actions-v64.1",
        "source": str(actions_path),
        "out": str(out_path),
        "budget": cap,
        "n_source_actions": len(rows),
        "n_tasks": len(task_ids),
        "n_actions": len(emitted),
        "n_baselines": n_baselines,
        "n_probes": len(emitted) - n_baselines,
        "n_distinct_task_ids": len({str(r.get("task_id")) for r in emitted if r.get("task_id")}),
        "require_baseline_pairs": bool(require_baseline_pairs),
        "canonical_status": "task_budget_materialization_chart_not_canonical",
    }
    return summary

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
        from ..premise_index import PremiseHit
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




























def cmd_minif2f_fetch(args):
    summary = fetch_minif2f(
        args.out,
        url=getattr(args, "url", DEFAULT_MINIF2F_LEAN4_URL),
        ref=getattr(args, "ref", None),
        depth=getattr(args, "depth", 1),
        force=getattr(args, "force", False),
        summary_out=getattr(args, "summary_out", None),
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False)); return 0


def cmd_minif2f_tasks(args):
    imports = getattr(args, "import_name", None)
    summary = build_minif2f_tasks(
        args.repo,
        args.out,
        split=getattr(args, "split", "valid"),
        limit=getattr(args, "limit", None),
        offset=getattr(args, "offset", 0),
        imports=imports,
        max_heartbeats=getattr(args, "max_heartbeats", 400000),
        summary_out=getattr(args, "summary_out", None),
        name_regex=getattr(args, "name_regex", None),
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

def cmd_make_transitions(args): rows=transitions_from_responses(args.responses,args.out,response_model=getattr(args,'response_model',None),response_mode=getattr(args,'response_mode','mean')); n_model=sum(1 for r in rows if r.get('pred_response_source')=='response_model'); print(json.dumps({"n": len(rows), "n_model_pred": n_model, "out": args.out}, indent=2, ensure_ascii=False)); return 0


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



def cmd_report(args):
    summary=write_run_report(args.run_dir,args.out); print(json.dumps(summary,indent=2,ensure_ascii=False)); return 0










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




def cmd_action_classes_to_registry(args):
    summary = action_classes_to_registry(args.classes, args.out, out_actions=getattr(args, "out_actions", None))
    print(json.dumps(summary, indent=2, ensure_ascii=False))
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
        from ..schemas import read_jsonl, write_jsonl
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


def register_experiment_commands(sub: argparse._SubParsersAction) -> None:
    cand=sub.add_parser('candidates'); cand.add_argument('--tasks', required=True); cand.add_argument('--out', required=True); cand.add_argument('--max-candidates', type=int, default=64); cand.add_argument('--candidate-mode', choices=['basic','state'], default='state'); cand.add_argument('--import-mode', choices=['preserve','auto','core','mathlib'], default='preserve'); cand.set_defaults(func=cmd_candidates)
    rc=sub.add_parser('registry-candidates'); rc.add_argument('--tasks', required=True); rc.add_argument('--registry', required=True); rc.add_argument('--out', required=True); rc.add_argument('--max-candidates', type=int, default=96); rc.add_argument('--registry-only', action='store_true'); rc.add_argument('--import-mode', choices=['preserve','auto','core','mathlib'], default='preserve'); rc.set_defaults(func=cmd_registry_candidates)
    bpi=sub.add_parser('build-premise-index'); bpi.add_argument('--tasks'); bpi.add_argument('--actions'); bpi.add_argument('--out', required=True); bpi.set_defaults(func=cmd_build_premise_index)
    mf=sub.add_parser('minif2f-fetch'); mf.add_argument('--out', required=True); mf.add_argument('--url', default=DEFAULT_MINIF2F_LEAN4_URL); mf.add_argument('--ref'); mf.add_argument('--depth', type=int, default=1); mf.add_argument('--force', action='store_true'); mf.add_argument('--summary-out'); mf.set_defaults(func=cmd_minif2f_fetch)
    mt=sub.add_parser('minif2f-tasks'); mt.add_argument('--repo', required=True); mt.add_argument('--out', required=True); mt.add_argument('--split', choices=['valid','test','all'], default='valid'); mt.add_argument('--limit', type=int); mt.add_argument('--offset', type=int, default=0); mt.add_argument('--import-name', action='append'); mt.add_argument('--max-heartbeats', type=int, default=400000); mt.add_argument('--summary-out'); mt.add_argument('--name-regex'); mt.set_defaults(func=cmd_minif2f_tasks)
    pretr=sub.add_parser('premise-retrieve'); pretr.add_argument('--index', required=True); pretr.add_argument('--out', required=True); pretr.add_argument('--query'); pretr.add_argument('--tasks'); pretr.add_argument('--states'); pretr.add_argument('--k', type=int, default=10); pretr.add_argument('--kind'); pretr.add_argument('--import-mode', choices=['preserve','auto','core','mathlib'], default='preserve'); pretr.set_defaults(func=cmd_premise_retrieve)
    pact=sub.add_parser('premise-actions'); pact.add_argument('--hits', required=True); pact.add_argument('--out', required=True); pact.add_argument('--task-id'); pact.add_argument('--max-actions-per-query', type=int, default=8); pact.set_defaults(func=cmd_premise_actions)
    pc=sub.add_parser('premise-candidates'); pc.add_argument('--tasks', required=True); pc.add_argument('--index', required=True); pc.add_argument('--out', required=True); pc.add_argument('--top-k', type=int, default=8); pc.add_argument('--max-actions', type=int, default=48); pc.set_defaults(func=cmd_premise_candidates)
    prr=sub.add_parser('premise-response-registry'); prr.add_argument('--responses', required=True); prr.add_argument('--actions'); prr.add_argument('--out', required=True); prr.add_argument('--summary-out'); prr.add_argument('--min-count', type=int, default=1); prr.set_defaults(func=cmd_premise_response_registry)
    prret=sub.add_parser('premise-response-retrieve'); prret.add_argument('--registry', required=True); prret.add_argument('--out', required=True); prret.add_argument('--summary-out'); prret.add_argument('--out-actions'); prret.add_argument('--response-normal'); prret.add_argument('--response-normal-json'); prret.add_argument('--carrier-normal'); prret.add_argument('--carrier-normal-json'); prret.add_argument('--top-k', type=int); prret.add_argument('--cost-weight', type=float, default=0.05); prret.add_argument('--uncertainty-weight', type=float, default=0.10); prret.add_argument('--audit-weight', type=float, default=0.20); prret.add_argument('--carrier-safe', action='store_true'); prret.add_argument('--carrier-budget', type=float, default=0.0); prret.set_defaults(func=cmd_premise_response_retrieve)
    pqm=sub.add_parser('premise-quotient-mine'); pqm.add_argument('--registry', required=True); pqm.add_argument('--out', required=True); pqm.add_argument('--cosine-threshold', type=float, default=0.95); pqm.add_argument('--distance-threshold', type=float, default=0.25); pqm.add_argument('--no-carrier', action='store_true'); pqm.set_defaults(func=cmd_premise_quotient_mine)
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
    mt=sub.add_parser('make-transitions'); mt.add_argument('--responses', required=True); mt.add_argument('--out', required=True); mt.add_argument('--response-model'); mt.add_argument('--response-mode', default='mean'); mt.set_defaults(func=cmd_make_transitions)
    ds=sub.add_parser('dataset-summary'); ds.add_argument('--responses', required=True); ds.add_argument('--out'); ds.set_defaults(func=cmd_dataset_summary)
    sp=sub.add_parser('split'); sp.add_argument('--input', required=True); sp.add_argument('--out', required=True); sp.add_argument('--train-frac', type=float, default=0.8); sp.add_argument('--seed', type=int, default=0); sp.add_argument('--group-key'); sp.set_defaults(func=cmd_split)
    ca=sub.add_parser('carrier-accept'); ca.add_argument('--tasks', required=True); ca.add_argument('--proposals', required=True); ca.add_argument('--out', required=True); ca.add_argument('--margin-threshold', type=float, default=0.0); ca.add_argument('--cost-weight', type=float, default=0.1); add_exec_args(ca); ca.set_defaults(func=cmd_carrier_accept)
    cas=sub.add_parser('carrier-accept-summary'); cas.add_argument('--accepted', required=True); cas.add_argument('--out', required=True); cas.set_defaults(func=cmd_carrier_accept_summary)
    rba=sub.add_parser('robust-accept'); rba.add_argument('--base-responses', required=True); rba.add_argument('--candidate-responses', required=True); rba.add_argument('--out', required=True); rba.add_argument('--report-out'); rba.add_argument('--accepted-actions-out'); rba.add_argument('--per-row-out'); rba.add_argument('--margin-threshold', type=float, default=0.0); rba.add_argument('--max-per-task', type=int, default=16); rba.add_argument('--goal-weight', type=float, default=1.0); rba.add_argument('--carrier-weight', type=float, default=0.7); rba.add_argument('--cost-weight', type=float, default=0.05); rba.add_argument('--max-mass', type=float, default=1.0); rba.add_argument('--ridge', type=float, default=1e-4); rba.add_argument('--robust-z', type=float, default=1.0); rba.add_argument('--robust-min-repeats', type=int, default=1); rba.add_argument('--robust-min-success-rate', type=float, default=1.0); rba.set_defaults(func=cmd_robust_accept)
    ra=sub.add_parser('registry-accept'); ra.add_argument('--base-responses', required=True); ra.add_argument('--registry-responses', required=True); ra.add_argument('--accepted-actions-out', required=True); ra.add_argument('--report-out', required=True); ra.add_argument('--audit-out'); ra.add_argument('--margin-threshold', type=float, default=0.0); ra.add_argument('--max-per-task', type=int, default=16); ra.add_argument('--goal-weight', type=float, default=1.0); ra.add_argument('--type-weight', type=float, default=0.6); ra.add_argument('--search-weight', type=float, default=0.4); ra.add_argument('--carrier-weight', type=float, default=0.7); ra.add_argument('--audit-weight', type=float, default=0.2); ra.add_argument('--success-bonus', type=float, default=0.25); ra.add_argument('--fail-penalty', type=float, default=0.25); ra.add_argument('--timeout-penalty', type=float, default=1.0); ra.add_argument('--cost-weight', type=float, default=0.05); ra.add_argument('--robust-radius', type=float, default=0.0); ra.add_argument('--robust-relative-radius', type=float, default=0.0); ra.add_argument('--accept-on-robust', action='store_true'); ra.set_defaults(func=cmd_registry_accept)
    ac=sub.add_parser('accept-candidates'); ac.add_argument('--base-responses', required=True); ac.add_argument('--candidate-responses', required=True); ac.add_argument('--out', required=True); ac.add_argument('--summary-out'); ac.add_argument('--margin-threshold', type=float, default=0.0); ac.add_argument('--cost-weight', type=float, default=0.05); ac.add_argument('--carrier-weight', type=float, default=0.25); ac.add_argument('--audit-penalty', type=float, default=1.0); ac.add_argument('--require-success', action='store_true'); ac.set_defaults(func=cmd_accept_candidates)
    maf=sub.add_parser('merge-action-files'); maf.add_argument('--inputs', nargs='+', required=True); maf.add_argument('--out', required=True); maf.add_argument('--max-actions', type=int); maf.set_defaults(func=cmd_merge_action_files)
    rp=sub.add_parser('report'); rp.add_argument('--run-dir', required=True); rp.add_argument('--out'); rp.set_defaults(func=cmd_report)
    ef=sub.add_parser('expose-frontiers'); ef.add_argument('--tasks', required=True); ef.add_argument('--out', required=True); ef.add_argument('--max-prefixes', type=int, default=8); ef.add_argument('--include-identity', action='store_true'); ef.add_argument('--accept-status', nargs='*', default=['partial','success','dry_run']); add_exec_args(ef); ef.set_defaults(func=cmd_expose_frontiers)
    mb=sub.add_parser('make-corebench'); mb.add_argument('--out', required=True); mb.add_argument('--n-nat', type=int, default=20); mb.add_argument('--n-prop', type=int, default=20); mb.add_argument('--n-bool', type=int, default=10); mb.add_argument('--n-eq', type=int, default=10); mb.add_argument('--import-mode', choices=['core','mathlib'], default='core'); mb.set_defaults(func=cmd_make_corebench)

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

    dor=sub.add_parser('defect-ontology-reconcile'); dor.add_argument('--run-dir'); dor.add_argument('--base-registry'); dor.add_argument('--candidate-atoms', action='append', default=[]); dor.add_argument('--out', required=True); dor.add_argument('--merge-threshold', type=float, default=0.72); dor.add_argument('--shadow-threshold', type=float, default=0.35); dor.add_argument('--novel-threshold', type=float, default=0.18); dor.add_argument('--include-open', action='store_true'); dor.add_argument('--include-shadow', action='store_true'); dor.set_defaults(func=cmd_defect_ontology_reconcile)
    dol=sub.add_parser('defect-ontology-lifecycle'); dol.add_argument('--run-dir'); dol.add_argument('--reconciliation-rows'); dol.add_argument('--split-suggestions'); dol.add_argument('--base-registry'); dol.add_argument('--reconciled-registry'); dol.add_argument('--previous-lifecycle', action='append', default=[]); dol.add_argument('--promotion-rows', action='append', default=[]); dol.add_argument('--validation-rows', action='append', default=[]); dol.add_argument('--out', required=True); dol.add_argument('--min-evidence-score', type=float, default=2.0); dol.add_argument('--min-support-count', type=int, default=1); dol.add_argument('--include-pending', action='store_true'); dol.set_defaults(func=cmd_defect_ontology_lifecycle)


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


    cqm=sub.add_parser('carrier-quotient-mine'); cqm.add_argument('--responses', required=True); cqm.add_argument('--out', required=True); cqm.add_argument('--ridge', type=float, default=1e-4); cqm.add_argument('--max-mass', type=float, default=1.0); cqm.add_argument('--cosine-threshold', type=float, default=0.85); cqm.add_argument('--min-states', type=int, default=1); cqm.add_argument('--top-action-scores', type=int, default=128); cqm.add_argument('--margin-threshold', type=float, default=0.0); cqm.add_argument('--no-registry', action='store_true'); cqm.set_defaults(func=cmd_carrier_quotient_mine)
    qc=sub.add_parser('quotient-coordinates'); qc.add_argument('--responses', required=True); qc.add_argument('--out', required=True); qc.add_argument('--ridge', type=float, default=1e-4); qc.add_argument('--max-mass', type=float, default=1.0); qc.add_argument('--cosine-threshold', type=float, default=0.85); qc.add_argument('--min-states', type=int, default=1); qc.add_argument('--top-action-scores', type=int, default=128); qc.add_argument('--margin-threshold', type=float, default=0.0); qc.add_argument('--no-registry', action='store_true'); qc.add_argument('--no-normal', action='store_true'); qc.add_argument('--validate', action='store_true'); qc.set_defaults(func=cmd_quotient_coordinates)
    cq=sub.add_parser('carrier-quotient'); cq.add_argument('--responses', required=True); cq.add_argument('--out', required=True); cq.add_argument('--ridge', type=float, default=1e-4); cq.add_argument('--max-mass', type=float, default=1.0); cq.add_argument('--cosine-threshold', type=float, default=0.85); cq.add_argument('--min-states', type=int, default=1); cq.add_argument('--top-action-scores', type=int, default=128); cq.add_argument('--margin-threshold', type=float, default=0.0); cq.add_argument('--no-registry', action='store_true'); cq.add_argument('--no-incidence', action='store_true'); cq.add_argument('--validate', action='store_true'); cq.set_defaults(func=cmd_carrier_quotient)
    cqv=sub.add_parser('carrier-quotient-validate'); cqv.add_argument('--coordinates', required=True); cqv.add_argument('--responses', required=True); cqv.add_argument('--out-report', required=True); cqv.add_argument('--out-rows', required=True); cqv.add_argument('--min-support-score', type=float, default=0.0); cqv.add_argument('--over-refinement-ratio', type=float, default=2.0); cqv.set_defaults(func=cmd_carrier_quotient_validate)
    qcv=sub.add_parser('quotient-coordinate-validate'); qcv.add_argument('--coordinates', required=True); qcv.add_argument('--responses', required=True); qcv.add_argument('--out-report', required=True); qcv.add_argument('--out-rows', required=True); qcv.add_argument('--holdout-fraction', type=float, default=0.35); qcv.add_argument('--min-support-score', type=float, default=0.0); qcv.add_argument('--over-refinement-ratio', type=float, default=2.0); qcv.set_defaults(func=cmd_quotient_coordinate_validate)

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


__all__ = ["register_experiment_commands"]
