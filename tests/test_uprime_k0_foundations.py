from lean_rgc.evals.uprime_k0 import (
    covariance_probe,
    environment_fingerprint_probe,
    projection_probe,
    run_foundation_probe,
    weighted_lifting_probe,
)


def test_weighted_lifting_probe_exposes_legacy_mismatch_and_repaired_coordinates():
    report = weighted_lifting_probe()
    assert report["legacy_counterexample_detected"] is True
    assert report["legacy_claim_holds"] is False
    assert report["corrected_claim_holds"] is True


def test_projection_probe_exposes_both_unconditional_identities():
    report = projection_probe()
    assert report["legacy_counterexample_detected"] is True
    assert report["adjacent_product_identity_holds"] is False
    assert report["contextual_commutativity_holds"] is False


def test_covariance_probe_exposes_missing_cross_term():
    report = covariance_probe()
    assert report["legacy_counterexample_detected"] is True
    assert report["diagonal_covariance_claim_holds"] is False
    assert report["missing_cross_covariance"]["float"] == 2.0


def test_environment_probe_reports_current_content_sensitivity_without_masking_it():
    report = environment_fingerprint_probe()
    assert isinstance(report["content_sensitive"], bool)
    assert report["gate_F0a_cache_content_pass"] is report["content_sensitive"]
    assert "not full U'0/F0" in report["scope"]


def test_integrated_foundation_probe_reaches_a_registered_verdict():
    report = run_foundation_probe(".")
    assert report["legacy_math_counterexamples_detected"] is True
    assert report["verdict"] == "BLOCKED_AS_WRITTEN"
    assert any(blocker.startswith("T0_") for blocker in report["current_blockers"])
    assert report["licenses_later_stage"] is False
