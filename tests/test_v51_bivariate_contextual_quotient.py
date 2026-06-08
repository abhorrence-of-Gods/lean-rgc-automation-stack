from pathlib import Path

from lean_rgc.bivariate_contextual_quotient import (
    build_premise_use_rows,
    build_repair_face_ledger,
    generate_bivariate_contextual_candidates,
    schedule_bivariate_candidates,
    write_separator_contexts,
)
from lean_rgc.cli import main as cli_main
from lean_rgc.premise_contextual_quotient import (
    mine_premise_contextual_quotient,
    validate_premise_contextual_quotient,
)
from lean_rgc.schemas import read_jsonl, write_jsonl


def _actions(path: Path) -> Path:
    write_jsonl(
        path,
        [
            {
                "action_id": "p_add_zero",
                "tactic": "simp [Nat.add_zero]",
                "tactic_class": "simp",
                "carrier_tags": ["premise", "simp"],
                "metadata": {"premise": {"name": "Nat.add_zero"}},
            },
            {
                "action_id": "p_assoc",
                "tactic": "rw [Nat.add_assoc]",
                "tactic_class": "rw",
                "carrier_tags": ["premise", "rw"],
                "metadata": {"premise": {"name": "Nat.add_assoc"}},
            },
            {
                "action_id": "ctx_simp_all",
                "tactic": "simp_all",
                "context_kind": "simp_all",
                "position_allowed": ["post"],
                "metadata": {"role": "separator_context"},
            },
        ],
    )
    return path


def test_premise_rows_and_separator_contexts_are_separate_artifacts(tmp_path: Path):
    actions = _actions(tmp_path / "actions.jsonl")
    rows = tmp_path / "premise_use_rows.jsonl"
    report = tmp_path / "premise_use_row_report.json"
    summary = build_premise_use_rows(actions, rows, summary_out=report)

    assert summary["n_rows"] == 2
    assert summary["skipped_context_actions"] == 1
    loaded = read_jsonl(rows)
    assert {r["premise_id"] for r in loaded} == {"Nat.add_zero", "Nat.add_assoc"}
    assert all(r["canonical_status"] == "premise_use_row_chart_not_canonical" for r in loaded)

    contexts = tmp_path / "separator_contexts.jsonl"
    csum = write_separator_contexts(contexts, summary_out=tmp_path / "separator_report.json")
    assert csum["pre_contexts"] >= 2
    assert csum["post_contexts"] >= 2
    crows = read_jsonl(contexts)
    assert any(r["action_id"] == "ctx_intro" and "pre" in r["position_allowed"] for r in crows)
    assert any(r["action_id"] == "ctx_norm_num" and "post" in r["position_allowed"] for r in crows)


def test_bivariate_generation_stratifies_columns_and_schedules_baselines(tmp_path: Path):
    actions = _actions(tmp_path / "actions.jsonl")
    rows = tmp_path / "premise_use_rows.jsonl"
    contexts = tmp_path / "separator_contexts.jsonl"
    build_premise_use_rows(actions, rows)
    write_separator_contexts(contexts)

    candidates = tmp_path / "bivariate_candidates.jsonl"
    summary = generate_bivariate_contextual_candidates(
        rows,
        contexts,
        candidates,
        max_pre=4,
        max_post=8,
        summary_out=tmp_path / "candidate_report.json",
    )
    assert summary["n_premise_use_rows"] == 2
    assert summary["n_context_pairs"] >= 8
    assert "ctx_intro" in summary["pre_context_ids"]
    assert "ctx_simp_all" in summary["post_context_ids"]

    candidate_rows = read_jsonl(candidates)
    probes = [r for r in candidate_rows if not (r.get("metadata") or {}).get("is_contextual_baseline")]
    assert probes
    assert all((r.get("metadata") or {}).get("baseline_action_id") for r in probes)

    scheduled = tmp_path / "scheduled.jsonl"
    sched = schedule_bivariate_candidates(
        candidates,
        scheduled,
        budget=18,
        report_out=tmp_path / "schedule_report.json",
        require_baseline_pairs=True,
    )
    assert sched["baseline_missing"] == 0
    assert sched["n_selected_probes"] > 0
    selected = read_jsonl(scheduled)
    seen = set()
    selected_uids = set()
    for row in selected:
        meta = row.get("metadata") or {}
        if meta.get("is_contextual_baseline"):
            seen.add(row["action_id"])
        else:
            assert meta["baseline_action_id"] in seen
            selected_uids.add(meta["premise_use_id"])
    assert len(selected_uids) == 2


def test_vacuous_premise_quotient_and_singleton_validation_are_marked(tmp_path: Path):
    fingerprints = tmp_path / "fingerprints.jsonl"
    write_jsonl(
        fingerprints,
        [
            {
                "premise_use_id": "u1",
                "premise_id": "Nat.add_zero",
                "use_mode": "simp",
                "fingerprint": {"ctx:s|pre:__id__|post:__id__::resp::goal.eq": 1.0},
                "domain_support": ["ctx:s|pre:__id__|post:__id__"],
                "response_summary": {"goal.eq": 1.0},
                "carrier_summary": {},
                "gamma_summary": {},
                "cost_summary": {},
                "audit_summary": {},
            }
        ],
    )
    qdir = tmp_path / "q"
    summary = mine_premise_contextual_quotient(fingerprints_path=fingerprints, out_dir=qdir)
    assert summary["quotient_status"] == "skipped_or_vacuous_row_universe"
    assert read_jsonl(qdir / "premise_quotient_classes.jsonl") == []

    write_jsonl(
        qdir / "premise_quotient_classes.jsonl",
        [
            {
                "premise_class_id": "qprem_single",
                "representative_premise_use_id": "u1",
                "member_premise_use_ids": ["u1"],
                "premise_ids": ["Nat.add_zero"],
                "fingerprint_centroid": {"ctx:s|pre:__id__|post:__id__::resp::goal.eq": 1.0},
                "domain_support": ["ctx:s|pre:__id__|post:__id__"],
            }
        ],
    )
    rows_out = qdir / "validation_rows.jsonl"
    validate_premise_contextual_quotient(
        fingerprints_path=fingerprints,
        classes_path=qdir / "premise_quotient_classes.jsonl",
        out_rows=rows_out,
        out_report=qdir / "validation_report.json",
    )
    assert read_jsonl(rows_out)[0]["validation_status"] == "singleton_vacuously_stable_not_informative"


def test_repair_face_ledger_and_cli_subcommands(tmp_path: Path):
    actions = _actions(tmp_path / "actions.jsonl")
    rows = tmp_path / "rows.jsonl"
    contexts = tmp_path / "contexts.jsonl"
    candidates = tmp_path / "candidates.jsonl"

    assert cli_main(["premise-use-rows", "--actions", str(actions), "--out", str(rows)]) == 0
    assert cli_main(["separator-contexts", "--out", str(contexts)]) == 0
    assert (
        cli_main(
            [
                "bivariate-contextual-generate",
                "--premise-rows",
                str(rows),
                "--contexts",
                str(contexts),
                "--out",
                str(candidates),
                "--max-pre",
                "3",
                "--max-post",
                "3",
            ]
        )
        == 0
    )
    scheduled = tmp_path / "scheduled.jsonl"
    assert (
        cli_main(
            [
                "bivariate-contextual-schedule",
                "--candidates",
                str(candidates),
                "--out",
                str(scheduled),
                "--budget",
                "12",
                "--require-baseline-pairs",
            ]
        )
        == 0
    )
    assert read_jsonl(scheduled)

    fingerprints = tmp_path / "fingerprints.jsonl"
    classes = tmp_path / "classes.jsonl"
    validation = tmp_path / "validation.jsonl"
    write_jsonl(fingerprints, [{"premise_use_id": "u1"}])
    write_jsonl(
        classes,
        [
            {
                "premise_class_id": "qprem1",
                "member_premise_use_ids": ["u1"],
                "response_summary": {"goal.eq": 1.0},
            }
        ],
    )
    write_jsonl(validation, [{"premise_class_id": "qprem1", "validation_status": "heldout_validated_premise_class"}])
    faces = tmp_path / "faces.jsonl"
    summary = build_repair_face_ledger(
        fingerprints_path=fingerprints,
        classes_path=classes,
        validation_rows_path=validation,
        out=faces,
    )
    assert summary["n_faces"] == 1
    assert read_jsonl(faces)[0]["canonical_status"] == "finite_repair_face_chart_not_canonical"
