import os
import subprocess

import pytest

from lean_rgc.evals.uprime_t0 import (
    PROBE_BUILDERS,
    run_t0,
)


pytestmark = pytest.mark.skipif(
    os.environ.get("UPRIME_T0_ANCHORED_EXECUTION") != "1",
    reason="canonical anchored T0 CLI must run before the post-anchor pytest replay",
)


def test_each_t0_probe_exposes_legacy_and_handles_amended_contract():
    for builder in PROBE_BUILDERS:
        report = builder()
        assert report["legacy_counterexample_detected"] is True, report["probe_id"]
        assert report["amended_negative_handled"] is True, report["probe_id"]
        assert report["amended_positive_fixture_passed"] is True, report["probe_id"]


def test_anchored_t0_report_passes_only_theory_gate():
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    report = run_t0(".", anchor=commit[:12])
    assert report["verdict"] == "T0_PASS"
    assert report["failures"] == []
    assert report["licenses_next_repair_stage"] is True
    assert report["licenses_later_stage"] is False
