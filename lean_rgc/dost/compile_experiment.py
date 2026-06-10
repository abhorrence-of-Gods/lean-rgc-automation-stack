from __future__ import annotations

from pathlib import Path
from typing import Any

import json

from .common import (
    SCHEMA_PRIMITIVE_OBSERVABLE,
    SCHEMA_BOUNDED_TRANSCRIPT,
    SCHEMA_FEATURE_CLOSURE,
    SCHEMA_FEATURE_VALUE,
    SCHEMA_FEATURE_SELECTION,
    SCHEMA_AUTO_PLAN,
    SCHEMA_DOST_AUDIT,
    DEFAULT_PRIMITIVE_OBSERVABLES,
    _json_dump,
    _json_load,
    _read_rows,
    _safe_float,
    _as_list,
    _path_if_exists,
    _first_existing,
    _ratio,
    _score_avg,
    _json_bytes,
    _row_identity,
    _status_counter,
    _class_member_count,
    _row_tactic_text,
    _is_macro_policy_row,
    _is_structural_row,
    _nf_status,
    _is_typed_nf_status,
    _matrix_metrics,
)



def compile_experiment_from_auto_plan(
    auto_plan_path: str | Path,
    out: str | Path,
    *,
    notebook_out: str | Path | None = None,
    base_command: str = "lean-rgc pipeline",
) -> dict[str, Any]:
    plan = json.loads(Path(auto_plan_path).read_text(encoding="utf-8"))
    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "",
        "# Generated from a finite DOST auto-plan chart.",
    ]
    cells: list[dict[str, Any]] = []

    def add_cmd(cmd: str) -> None:
        lines.append(cmd)
        cells.append({"cell_type": "code", "metadata": {}, "source": [cmd + "\n"], "outputs": [], "execution_count": None})

    for action in plan.get("selected_actions") or []:
        kind = str(action.get("action_kind") or "")
        if kind == "set_observation_policy":
            mode = str(action.get("kernel_state_mode") or "features")
            add_cmd(f"{base_command} --kernel-state-mode {mode} --dost-automation")
        elif kind == "generate_features":
            add_cmd("lean-rgc dost-feature-closure --transcripts bounded_transcripts.jsonl --out feature_closure.jsonl --values-out bounded_feature_transcripts.jsonl")
        elif kind == "generate_separator_contexts":
            add_cmd("lean-rgc separator-contexts --out separator_contexts.jsonl")
        elif kind == "generate_tower_object":
            add_cmd("lean-rgc obstruction-tower --out obstruction_tower --taxonomy-dir face_taxonomy --fingerprints bounded_feature_transcripts.jsonl")
        elif kind == "hard_split_carrier":
            face = action.get("target_face_id") or "unknown_face"
            add_cmd(f"# hard_split_carrier target_face_id={face}")
        elif kind == "block_retrieval":
            face = action.get("target_face_id") or "unknown_face"
            add_cmd(f"# block_retrieval target_face_id={face}")
        elif kind == "allow_retrieval":
            face = action.get("target_face_id") or "unknown_face"
            add_cmd(f"# allow face-mediated retrieval target_face_id={face}")
        elif kind == "run_ablation":
            face = action.get("target_face_id") or "unknown_face"
            add_cmd(f"# run_ablation target_face_id={face}")
        else:
            add_cmd(f"# inspect action_kind={kind}")

    p = Path(out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if notebook_out:
        nb = {
            "cells": cells,
            "metadata": {
                "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                "language_info": {"name": "python"},
            },
            "nbformat": 4,
            "nbformat_minor": 5,
        }
        Path(notebook_out).parent.mkdir(parents=True, exist_ok=True)
        Path(notebook_out).write_text(json.dumps(nb, indent=2, ensure_ascii=False), encoding="utf-8")
    return {
        "schema_version": SCHEMA_AUTO_PLAN,
        "auto_plan": str(auto_plan_path),
        "out": str(out),
        "notebook_out": str(notebook_out) if notebook_out else None,
        "n_commands": len(cells),
        "canonical_status": "compiled_experiment_is_plan_chart_not_canonical",
    }


__all__ = [
    "compile_experiment_from_auto_plan",
]
