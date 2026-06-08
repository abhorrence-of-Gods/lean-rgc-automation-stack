from pathlib import Path
import json

from lean_rgc.cli import main
from lean_rgc.schemas import read_jsonl


def test_pipeline_contextual_probe_loop(tmp_path: Path):
    out = tmp_path / "pipe"
    rc = main([
        "pipeline",
        "--tasks", "examples/minimal_theorems.jsonl",
        "--actions", "examples/core_tactics.jsonl",
        "--out", str(out),
        "--dry-run",
        "--max-actions", "3",
        "--contextual-probes",
        "--contextual-probe-max-left", "1",
        "--contextual-probe-max-right", "1",
        "--contextual-probe-max-candidates", "6",
        "--audit-contextual-probe-candidates",
        "--contextual-probe-audit-max-actions", "4",
        "--contextual-probe-congruence",
        "--contextual-probe-accept-coker",
        "--contextual-probe-robust-coker-accept",
    ])
    assert rc == 0
    cand = out / "contextual_probes" / "contextual_probe_candidates.jsonl"
    audit = out / "contextual_probe_audit" / "responses.jsonl"
    cong = out / "contextual_probes" / "contextual_probe_congruence" / "response_congruence_classes.jsonl"
    robust = out / "contextual_probe_robust_acceptance_report.json"
    assert cand.exists() and len(read_jsonl(cand)) > 0
    assert audit.exists() and len(read_jsonl(audit)) > 0
    assert cong.exists()
    assert robust.exists()
    summary = json.loads((out / "pipeline_summary.json").read_text())
    files = summary.get("pipeline_files", {}) or summary.get("summary", {}).get("pipeline_files", {})
    assert files.get("contextual_probe_candidates")


def test_iterate_contextual_probe_merge(tmp_path: Path):
    out = tmp_path / "iter"
    rc = main([
        "iterate",
        "--tasks", "examples/minimal_theorems.jsonl",
        "--actions", "examples/core_tactics.jsonl",
        "--out", str(out),
        "--dry-run",
        "--rounds", "1",
        "--max-actions", "3",
        "--contextual-probes",
        "--contextual-probe-max-left", "1",
        "--contextual-probe-max-right", "1",
        "--contextual-probe-max-candidates", "6",
        "--audit-contextual-probe-candidates",
        "--contextual-probe-audit-max-actions", "4",
        "--contextual-probe-congruence",
        "--contextual-probe-accept-coker",
        "--contextual-probe-robust-coker-accept",
        "--contextual-probe-merge-actions",
    ])
    assert rc == 0
    assert (out / "round_00" / "contextual_probes" / "contextual_probe_candidates.jsonl").exists()
    assert (out / "round_00" / "contextual_probe_audit" / "responses.jsonl").exists()
    rep = json.loads((out / "iterate_summary.json").read_text())
    assert rep["rounds"][0]["contextual_probe_candidates"] == 6
    assert (out / "round_00_actions_next.jsonl").exists()
