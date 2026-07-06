"""Defect #6 regression: sorry warnings must never classify as success.

`sorry` elaborates at exit code 0 with only the warning
"declaration uses 'sorry'", so both lanes' success paths certified proof
holes as successes (caught 2026-07-06 by the S'0 golden-sample manual
inspection: 6/35 surviving "successes" were bare `sorry`, including 3 of
G1re3's 5 "verified" RFT traces).
"""
from lean_rgc.lean.bulk_executor import _classify_block_failure, _errors_by_line
from lean_rgc.lean.executor import LeanExecutor

SORRY_WARNING = "/tmp/f.lean:10:8: warning: declaration uses 'sorry'"


def test_single_lane_success_classifier_demotes_sorry():
    assert LeanExecutor._classify_success(SORRY_WARNING) == "unsafe"


def test_single_lane_clean_output_stays_success():
    assert LeanExecutor._classify_success("") == "success"
    assert LeanExecutor._classify_success("compilation ok") == "success"


def test_bulk_lane_collects_sorry_warning_and_classifies_unsafe():
    out = _errors_by_line(SORRY_WARNING)
    assert 10 in out
    assert _classify_block_failure("\n".join(out[10])) == "unsafe"


def test_bulk_lane_still_drops_unrelated_warnings():
    out = _errors_by_line("/tmp/f.lean:3:0: warning: unused variable `h`")
    assert out == {}
