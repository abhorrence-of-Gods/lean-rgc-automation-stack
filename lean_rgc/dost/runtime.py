from __future__ import annotations

from pathlib import Path
from typing import Any

from .autoplan import build_dost_auto_plan
from .dual_select import select_features_for_dual_obstructions
from .features import build_feature_closure
from .reports import build_dost_audit_reports
from .transcripts import build_bounded_transcripts, write_primitive_observables
from .common import _json_dump


def run_dost_automation_stack(
    input_path: str | Path,
    out_dir: str | Path,
    *,
    taxonomy_path: str | Path | None = None,
    tower_next_actions_path: str | Path | None = None,
    tower_summary_path: str | Path | None = None,
    max_features: int = 512,
    max_selected_per_dual: int = 8,
    kernel_state_mode: str = "features",
) -> dict[str, Any]:
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    primitive_path = out_path / "primitive_observables.jsonl"
    transcripts_path = out_path / "bounded_transcripts.jsonl"
    feature_closure_path = out_path / "feature_closure.jsonl"
    feature_values_path = out_path / "bounded_feature_transcripts.jsonl"
    selected_path = out_path / "selected_features.jsonl"
    feature_report_path = out_path / "feature_selection_report.json"
    auto_plan_path = out_path / "auto_plan.json"
    compiled_path = out_path / "compiled_experiment.sh"
    notebook_path = out_path / "compiled_notebook_cells.ipynb"

    write_primitive_observables(primitive_path)
    bounded_report = build_bounded_transcripts(
        input_path,
        transcripts_path,
        primitive_observables_out=None,
        summary_out=out_path / "bounded_transcripts_report.json",
        kernel_state_mode=kernel_state_mode,
    )
    closure_report = build_feature_closure(
        transcripts_path,
        feature_closure_path,
        values_out=feature_values_path,
        report_out=out_path / "feature_closure_report.json",
        max_features=max_features,
    )
    selection_report = select_features_for_dual_obstructions(
        feature_closure_path,
        feature_values_path,
        selected_path,
        report_out=feature_report_path,
        taxonomy_path=taxonomy_path,
        max_selected_per_dual=max_selected_per_dual,
    )
    auto_plan = build_dost_auto_plan(
        auto_plan_path,
        selected_features_path=selected_path,
        taxonomy_path=taxonomy_path,
        tower_next_actions_path=tower_next_actions_path,
        tower_summary_path=tower_summary_path,
        compiled_experiment_out=compiled_path,
        notebook_out=notebook_path,
        kernel_state_mode=kernel_state_mode,
    )
    report = {
        "schema_version": "lean-rgc-dost-automation-stack-v57.0",
        "input": str(input_path),
        "out_dir": str(out_path),
        "n_transcripts": bounded_report.get("n_transcripts"),
        "n_features": closure_report.get("n_features"),
        "n_selected_features": selection_report.get("n_selected"),
        "n_auto_plan_actions": len(auto_plan.get("selected_actions") or []),
        "artifacts": {
            "primitive_observables": str(primitive_path),
            "bounded_transcripts": str(transcripts_path),
            "feature_closure": str(feature_closure_path),
            "feature_values": str(feature_values_path),
            "selected_features": str(selected_path),
            "feature_selection_report": str(feature_report_path),
            "auto_plan": str(auto_plan_path),
            "compiled_experiment": str(compiled_path),
            "compiled_notebook_cells": str(notebook_path),
        },
        "canonical_status": "dost_automation_stack_is_finite_chart_not_canonical",
    }
    _json_dump(report, out_path / "dost_obstruction_report.json")
    audit_summary = build_dost_audit_reports(
        out_path / "audit",
        fingerprints_path=input_path,
        taxonomy_path=taxonomy_path,
        tower_next_actions_path=tower_next_actions_path,
        tower_summary_path=tower_summary_path,
        dost_report_path=out_path / "dost_obstruction_report.json",
        feature_selection_report_path=feature_report_path,
        selected_features_path=selected_path,
    )
    report["artifacts"]["audit"] = str(out_path / "audit")
    report["artifacts"]["audit_dashboard"] = audit_summary["artifacts"]["audit_dashboard"]
    report["artifacts"]["big_theorem_readiness"] = audit_summary["artifacts"]["big_theorem_readiness"]
    _json_dump(report, out_path / "dost_obstruction_report.json")
    return report


__all__ = [
    "run_dost_automation_stack",
]
