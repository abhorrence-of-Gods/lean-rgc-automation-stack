from __future__ import annotations

import json

from ..concept_geometry import build_concept_geometry
from ..concept_hardening import decode_concepts_to_repair_atoms
from ..concept_search import search_concepts
from ..crg_audit import audit_crg_candidates
from ..crg_hardening import harden_crg_candidates
from ..crg_problem import build_crg_problems
from ..crg_registry import build_repair_species_registry
from ..hardening_gap_report import build_hardening_gap_report
from ..nonlinear_generator import generate_nonlinear_repair_candidates
from ..relaxed_species import write_relaxed_species_registry
from ..repair_gradient_flow import repair_gradient_flow_steps


def cmd_relaxed_species_registry(args):
    summary = write_relaxed_species_registry(
        out=args.out,
        summary_out=getattr(args, "summary_out", None),
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def cmd_repair_species_registry(args):
    summary = build_repair_species_registry(
        out=args.out,
        summary_out=getattr(args, "summary_out", None),
        actions_path=getattr(args, "actions", None),
        action_geometry_path=getattr(args, "action_geometry", None),
        premise_registry_path=getattr(args, "premise_registry", None),
        quotient_coordinates_path=getattr(args, "quotient_coordinates", None),
        carrier_quotient_path=getattr(args, "carrier_quotient", None),
        tower_retrieval_path=getattr(args, "tower_retrieval", None),
        repair_faces_path=getattr(args, "repair_faces", None),
        include_species_rows=not getattr(args, "atoms_only", False),
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def cmd_crg_build_problems(args):
    budget = {}
    for key in ["cost_max", "audit_risk_max", "source_risk_max", "ghost_risk_max", "hardening_cost_max"]:
        value = getattr(args, key, None)
        if value is not None:
            budget[key] = value
    summary = build_crg_problems(
        out=args.out,
        repair_faces_path=getattr(args, "repair_faces", None),
        tower_dual_components_path=getattr(args, "tower_dual_components", None),
        response_completion_path=getattr(args, "response_completion", None),
        summary_out=getattr(args, "summary_out", None),
        budget=budget or None,
        repair_space_scope=getattr(args, "repair_space_scope", "relaxed"),
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def cmd_crg_optimize(args):
    summary = generate_nonlinear_repair_candidates(
        problems_path=args.problems,
        registry_path=args.registry,
        response_completion_path=getattr(args, "response_completion", None),
        out=args.out,
        summary_out=getattr(args, "summary_out", None),
        optimizer=getattr(args, "optimizer", "convex_mixture"),
        temperature=getattr(args, "temperature", 1.0),
        top_k=getattr(args, "top_k", 16),
        cost_weight=getattr(args, "cost_weight", 0.0),
        audit_weight=getattr(args, "audit_weight", 0.0),
        source_weight=getattr(args, "source_weight", 0.0),
        ghost_weight=getattr(args, "ghost_weight", 0.0),
        hardening_weight=getattr(args, "hardening_weight", 0.0),
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def cmd_crg_harden(args):
    summary = harden_crg_candidates(
        candidates_path=args.candidates,
        out_attempts=args.out_attempts,
        out_actions=getattr(args, "out_actions", None),
        summary_out=getattr(args, "summary_out", None),
        method=getattr(args, "method", "mixture_to_beam"),
        top_k=getattr(args, "top_k", 3),
        include_sequence=not getattr(args, "no_sequence", False),
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def cmd_crg_audit(args):
    summary = audit_crg_candidates(
        candidates_path=args.candidates,
        hardening_attempts_path=args.hardening_attempts,
        audited_responses_path=getattr(args, "audited_responses", None),
        out_rows=args.out,
        poms_out=getattr(args, "poms_out", None),
        summary_out=getattr(args, "summary_out", None),
        max_hardening_gap=getattr(args, "max_hardening_gap", 0.25),
        max_ghost_risk=getattr(args, "max_ghost_risk", 0.25),
    )
    if getattr(args, "gap_report_out", None):
        build_hardening_gap_report(crg_audit_rows_path=args.out, out=args.gap_report_out)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def cmd_repair_gradient_flow(args):
    summary = repair_gradient_flow_steps(
        problems_path=args.problems,
        registry_path=args.registry,
        response_completion_path=getattr(args, "response_completion", None),
        previous_candidates_path=getattr(args, "previous_candidates", None),
        out=args.out,
        summary_out=getattr(args, "summary_out", None),
        tau=getattr(args, "tau", 1.0),
        steps=getattr(args, "steps", 1),
        top_k=getattr(args, "top_k", 16),
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def cmd_concept_geometry(args):
    summary = build_concept_geometry(
        out_dir=args.out,
        taxonomy_path=getattr(args, "taxonomy", None),
        selected_features_path=getattr(args, "selected_features", None),
        summary_out=getattr(args, "summary_out", None),
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def cmd_concept_search(args):
    summary = search_concepts(
        concept_points_path=args.concept_points,
        concept_edges_path=getattr(args, "concept_edges", None),
        out=args.out,
        summary_out=getattr(args, "summary_out", None),
        response_normal=getattr(args, "response_normal", None),
        problems_path=getattr(args, "problems", None),
        top_k=getattr(args, "top_k", 32),
        mode=getattr(args, "mode", "response-nearest-neighbor"),
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def cmd_concept_decode(args):
    summary = decode_concepts_to_repair_atoms(
        concept_search_path=args.concept_search,
        concept_points_path=args.concept_points,
        out=args.out,
        summary_out=getattr(args, "summary_out", None),
        top_k=getattr(args, "top_k", None),
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def register_crg_commands(sub) -> None:
    rsp = sub.add_parser("relaxed-species-registry")
    rsp.add_argument("--out", required=True)
    rsp.add_argument("--summary-out")
    rsp.set_defaults(func=cmd_relaxed_species_registry)

    rsr = sub.add_parser("repair-species-registry")
    rsr.add_argument("--out", required=True)
    rsr.add_argument("--summary-out")
    rsr.add_argument("--actions")
    rsr.add_argument("--action-geometry")
    rsr.add_argument("--premise-registry")
    rsr.add_argument("--quotient-coordinates")
    rsr.add_argument("--carrier-quotient")
    rsr.add_argument("--tower-retrieval")
    rsr.add_argument("--repair-faces")
    rsr.add_argument("--atoms-only", action="store_true")
    rsr.set_defaults(func=cmd_repair_species_registry)

    cbp = sub.add_parser("crg-build-problems")
    cbp.add_argument("--out", required=True)
    cbp.add_argument("--repair-faces")
    cbp.add_argument("--tower-dual-components")
    cbp.add_argument("--response-completion")
    cbp.add_argument("--summary-out")
    cbp.add_argument("--repair-space-scope", choices=["active", "known", "relaxed", "concept"], default="relaxed")
    cbp.add_argument("--cost-max", type=float)
    cbp.add_argument("--audit-risk-max", type=float)
    cbp.add_argument("--source-risk-max", type=float)
    cbp.add_argument("--ghost-risk-max", type=float)
    cbp.add_argument("--hardening-cost-max", type=float)
    cbp.set_defaults(func=cmd_crg_build_problems)

    copt = sub.add_parser("crg-optimize")
    copt.add_argument("--problems", required=True)
    copt.add_argument("--registry", required=True)
    copt.add_argument("--out", required=True)
    copt.add_argument("--response-completion")
    copt.add_argument("--summary-out")
    copt.add_argument(
        "--optimizer",
        choices=["linear", "linear_support", "convex", "convex_mixture", "LinearSupportOptimizer", "ConvexMixtureOptimizer"],
        default="convex_mixture",
    )
    copt.add_argument("--temperature", type=float, default=1.0)
    copt.add_argument("--top-k", type=int, default=16)
    copt.add_argument("--cost-weight", type=float, default=0.0)
    copt.add_argument("--audit-weight", type=float, default=0.0)
    copt.add_argument("--source-weight", type=float, default=0.0)
    copt.add_argument("--ghost-weight", type=float, default=0.0)
    copt.add_argument("--hardening-weight", type=float, default=0.0)
    copt.set_defaults(func=cmd_crg_optimize)

    ch = sub.add_parser("crg-harden")
    ch.add_argument("--candidates", required=True)
    ch.add_argument("--out-attempts", required=True)
    ch.add_argument("--out-actions")
    ch.add_argument("--summary-out")
    ch.add_argument("--method", choices=["mixture_to_beam", "mixture_to_sequence"], default="mixture_to_beam")
    ch.add_argument("--top-k", type=int, default=3)
    ch.add_argument("--no-sequence", action="store_true")
    ch.set_defaults(func=cmd_crg_harden)

    caud = sub.add_parser("crg-audit")
    caud.add_argument("--candidates", required=True)
    caud.add_argument("--hardening-attempts", required=True)
    caud.add_argument("--audited-responses")
    caud.add_argument("--out", required=True)
    caud.add_argument("--poms-out")
    caud.add_argument("--summary-out")
    caud.add_argument("--gap-report-out")
    caud.add_argument("--max-hardening-gap", type=float, default=0.25)
    caud.add_argument("--max-ghost-risk", type=float, default=0.25)
    caud.set_defaults(func=cmd_crg_audit)

    rgf = sub.add_parser("repair-gradient-flow")
    rgf.add_argument("--problems", required=True)
    rgf.add_argument("--registry", required=True)
    rgf.add_argument("--out", required=True)
    rgf.add_argument("--response-completion")
    rgf.add_argument("--previous-candidates")
    rgf.add_argument("--summary-out")
    rgf.add_argument("--tau", type=float, default=1.0)
    rgf.add_argument("--steps", type=int, default=1)
    rgf.add_argument("--top-k", type=int, default=16)
    rgf.set_defaults(func=cmd_repair_gradient_flow)

    cgeo = sub.add_parser("concept-geometry")
    cgeo.add_argument("--out", required=True)
    cgeo.add_argument("--taxonomy")
    cgeo.add_argument("--selected-features")
    cgeo.add_argument("--summary-out")
    cgeo.set_defaults(func=cmd_concept_geometry)

    csrch = sub.add_parser("concept-search")
    csrch.add_argument("--concept-points", required=True)
    csrch.add_argument("--concept-edges")
    csrch.add_argument("--out", required=True)
    csrch.add_argument("--summary-out")
    csrch.add_argument("--response-normal")
    csrch.add_argument("--problems")
    csrch.add_argument("--top-k", type=int, default=32)
    csrch.add_argument(
        "--mode",
        choices=["response-nearest-neighbor", "operation-graph", "operation-graph expansion", "operation_graph", "all"],
        default="response-nearest-neighbor",
    )
    csrch.set_defaults(func=cmd_concept_search)

    cdec = sub.add_parser("concept-decode")
    cdec.add_argument("--concept-search", required=True)
    cdec.add_argument("--concept-points", required=True)
    cdec.add_argument("--out", required=True)
    cdec.add_argument("--summary-out")
    cdec.add_argument("--top-k", type=int)
    cdec.set_defaults(func=cmd_concept_decode)


__all__ = [
    "cmd_concept_decode",
    "cmd_concept_geometry",
    "cmd_concept_search",
    "cmd_crg_audit",
    "cmd_crg_build_problems",
    "cmd_crg_harden",
    "cmd_crg_optimize",
    "cmd_relaxed_species_registry",
    "cmd_repair_gradient_flow",
    "cmd_repair_species_registry",
    "register_crg_commands",
]
