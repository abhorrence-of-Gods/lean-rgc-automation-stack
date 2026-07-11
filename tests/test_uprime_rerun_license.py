from __future__ import annotations

import json
import os
from pathlib import Path
import runpy
import subprocess

import pytest

from lean_rgc.evals import uprime_rpc_litmus as litmus
from lean_rgc.evals.uprime_rerun_license import (
    RERUN_REGISTRY_PATH,
    SCHEMA_UPRIME_RERUN_REGISTRY,
    UPrimeRerunLicenseError,
    canonical_registry_bytes,
    load_rerun_registry,
    reject_canonical_rerun_bootstrap,
)


def _empty_registry():
    return {
        "default_allow": False,
        "licenses": {},
        "schema_version": SCHEMA_UPRIME_RERUN_REGISTRY,
    }


def _write_empty_registry(root: Path) -> Path:
    target = root / RERUN_REGISTRY_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(canonical_registry_bytes(_empty_registry()))
    return target


def test_repository_rerun_registry_is_canonical_and_default_deny():
    value = load_rerun_registry(RERUN_REGISTRY_PATH)
    assert value == _empty_registry()
    with pytest.raises(UPrimeRerunLicenseError, match="not licensed"):
        reject_canonical_rerun_bootstrap(".", "0" * 40)


@pytest.mark.parametrize(
    "raw",
    [
        b'{"default_allow":false,"licenses":{},"licenses":{},"schema_version":"lean-rgc-uprime-u1-rerun-registry-v1.0"}\n',
        b'{"default_allow":true,"licenses":{},"schema_version":"lean-rgc-uprime-u1-rerun-registry-v1.0"}\n',
        b'{"default_allow":false,"extra":0,"licenses":{},"schema_version":"lean-rgc-uprime-u1-rerun-registry-v1.0"}\n',
        b'{"default_allow":false,"licenses":{},"schema_version":"wrong"}\n',
        b'{"default_allow":false,"licenses":[],"schema_version":"lean-rgc-uprime-u1-rerun-registry-v1.0"}\n',
        b'{"schema_version":"lean-rgc-uprime-u1-rerun-registry-v1.0", "licenses":{},"default_allow":false}\n',
    ],
)
def test_rerun_registry_rejects_noncanonical_or_unsafe_forms(tmp_path, raw):
    path = tmp_path / "registry.json"
    path.write_bytes(raw)
    with pytest.raises(UPrimeRerunLicenseError):
        load_rerun_registry(path)


def test_nonempty_registry_still_cannot_activate_before_verifier_exists(tmp_path):
    value = _empty_registry()
    value["licenses"] = {"a" * 40: {"allow_once": True}}
    path = tmp_path / "registry.json"
    path.write_bytes(canonical_registry_bytes(value))
    assert load_rerun_registry(path)["licenses"]

    repo = tmp_path / "repo"
    target = repo / RERUN_REGISTRY_PATH
    target.parent.mkdir(parents=True)
    target.write_bytes(canonical_registry_bytes(value))
    with pytest.raises(UPrimeRerunLicenseError, match="not implemented"):
        reject_canonical_rerun_bootstrap(repo, "b" * 40)


def test_registry_canonical_serializer_rejects_nan():
    value = _empty_registry()
    value["licenses"] = {"x": {"bad": float("nan")}}
    with pytest.raises(ValueError):
        canonical_registry_bytes(value)


@pytest.mark.parametrize(
    "raw",
    [
        b'{"default_allow":false,"licenses":{"x":NaN},"schema_version":"lean-rgc-uprime-u1-rerun-registry-v1.0"}\n',
        b'{"default_allow":false,"licenses":{"x":Infinity},"schema_version":"lean-rgc-uprime-u1-rerun-registry-v1.0"}\n',
        b'{"default_allow":false,"licenses":{"x":"\\ud800"},"schema_version":"lean-rgc-uprime-u1-rerun-registry-v1.0"}\n',
    ],
)
def test_registry_nonfinite_and_unencodable_values_fail_with_license_error(
    tmp_path, raw
):
    path = tmp_path / "registry.json"
    path.write_bytes(raw)
    with pytest.raises(UPrimeRerunLicenseError, match="noncanonical value"):
        load_rerun_registry(path)


def test_registry_size_is_bounded_before_json_decode(tmp_path):
    path = tmp_path / "registry.json"
    path.write_bytes(b" " * (1024 * 1024 + 1))
    with pytest.raises(UPrimeRerunLicenseError, match="too large"):
        load_rerun_registry(path)


def test_license_requires_full_commit_before_reading_registry(tmp_path):
    with pytest.raises(UPrimeRerunLicenseError, match="full 40-character"):
        reject_canonical_rerun_bootstrap(tmp_path, "a" * 12)


def test_harness_checks_license_before_reserving_canonical_output():
    source = (
        Path(__file__).resolve().parents[1]
        / "lean_rgc"
        / "evals"
        / "uprime_rpc_litmus.py"
    ).read_text(encoding="utf-8")
    main_source = source[source.index("def main(") :]
    assert main_source.index("reject_canonical_rerun_bootstrap") < main_source.index(
        "_reserve_output"
    )


def _mock_git_preflight(monkeypatch, commit: str) -> None:
    monkeypatch.setattr(litmus, "_assert_git_top_level", lambda _root: None)
    monkeypatch.setattr(litmus, "_git_commit", lambda _root: commit)
    monkeypatch.setattr(litmus, "_assert_anchor_inputs_clean", lambda _root: None)
    monkeypatch.setattr(
        litmus,
        "_assert_anchor_pushed",
        lambda _root, _commit: "origin/codex/uprime-odlrq-plan",
    )


def test_cli_denial_is_behavioral_and_precedes_reservation_or_worker(
    tmp_path, monkeypatch
):
    commit = "a" * 40
    anchor = commit[:12]
    _write_empty_registry(tmp_path)
    _mock_git_preflight(monkeypatch, commit)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("reservation or worker boundary was reached")

    monkeypatch.setattr(litmus, "_reserve_output", forbidden)
    monkeypatch.setattr(litmus, "_RpcProcess", forbidden)
    out = tmp_path / litmus.REGISTERED_RUN_DIR / f"rpc_diagnostic_{anchor}.json"
    with pytest.raises(UPrimeRerunLicenseError, match="not licensed"):
        litmus.main(
            [
                "--repo-root",
                str(tmp_path),
                "--anchor",
                anchor,
                "--out",
                str(out),
            ]
        )
    assert not out.exists()
    assert not litmus._reservation_file(out).exists()


def test_direct_runner_denial_precedes_reservation_verification_or_worker(
    tmp_path, monkeypatch
):
    commit = "b" * 40
    anchor = commit[:12]
    _write_empty_registry(tmp_path)
    _mock_git_preflight(monkeypatch, commit)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("reservation verification or worker boundary was reached")

    monkeypatch.setattr(litmus, "_verify_reservation", forbidden)
    monkeypatch.setattr(litmus, "_RpcProcess", forbidden)
    out = tmp_path / litmus.REGISTERED_RUN_DIR / f"rpc_diagnostic_{anchor}.json"
    with pytest.raises(UPrimeRerunLicenseError, match="not licensed"):
        litmus.run_diagnostic(
            tmp_path,
            anchor=anchor,
            reservation_path=out,
            reservation_token="unused",
        )
    assert not out.exists()


def test_reservation_and_publication_helpers_are_independently_default_deny(
    tmp_path, monkeypatch
):
    commit = "c" * 40
    anchor = commit[:12]
    _write_empty_registry(tmp_path)
    out = tmp_path / litmus.REGISTERED_RUN_DIR / f"rpc_diagnostic_{anchor}.json"

    with pytest.raises(UPrimeRerunLicenseError, match="not licensed"):
        litmus._reserve_output(
            out,
            repo_root=tmp_path,
            anchor=anchor,
            commit=commit,
        )
    assert not out.parent.exists()

    def forbidden(*_args, **_kwargs):
        raise AssertionError("reservation verification was reached")

    monkeypatch.setattr(litmus, "_verify_reservation", forbidden)
    with pytest.raises(UPrimeRerunLicenseError, match="not licensed"):
        litmus._publish_reserved_json(
            out,
            {"verdict": "fabricated"},
            repo_root=tmp_path,
            token="unused",
            anchor=anchor,
            commit=commit,
        )
    assert not out.exists()


def test_rerun_gate_and_executed_package_initializers_are_anchored():
    required = {
        litmus.EVIDENCE_MILESTONE_2A_PATH,
        litmus.EVIDENCE_MILESTONE_2B_PREREG_PATH,
        litmus.EVIDENCE_MILESTONE_2B_PHASE1A_EXECUTION_PATH,
        litmus.EVIDENCE_MILESTONE_2B_PHASE1B1_EXECUTION_PATH,
        litmus.EVIDENCE_MILESTONE_2B_PHASE1B2_AMENDMENT_PATH,
        litmus.EVIDENCE_MILESTONE_2B_PHASE1B2_EXECUTION_PATH,
        litmus.EVIDENCE_MILESTONE_2B_PHASE2A_AMENDMENT_PATH,
        litmus.EVIDENCE_MILESTONE_2B_PHASE2A_EXECUTION_PATH,
        litmus.EVIDENCE_MILESTONE_2B_PHASE2B1_AMENDMENT_PATH,
        litmus.EVIDENCE_MILESTONE_2B_PHASE2B1_WINDOWS_BINDING_CORRECTION_PATH,
        litmus.EVIDENCE_MILESTONE_2B_PHASE2B1_EXECUTION_PATH,
        litmus.EVIDENCE_MILESTONE_2B_PHASE2B2A_AMENDMENT_PATH,
        litmus.EVIDENCE_MILESTONE_2B_PHASE2B2A_EXECUTION_PATH,
        litmus.EVIDENCE_MILESTONE_2B_PHASE2B2B_AMENDMENT_PATH,
        litmus.EVIDENCE_MILESTONE_2B_PHASE2B2B_EXECUTION_PATH,
        litmus.EVIDENCE_MILESTONE_2B_PHASE2B2C_AMENDMENT_PATH,
        litmus.EVIDENCE_MILESTONE_2B_PHASE2B2C_EXECUTION_PATH,
        litmus.EVIDENCE_MILESTONE_2B_PHASE2B2D_AMENDMENT_PATH,
        litmus.EVIDENCE_MILESTONE_2B_PHASE2B2D_EXECUTION_PATH,
        litmus.EVIDENCE_MILESTONE_2B_PHASE2B2E_AMENDMENT_PATH,
        litmus.EVIDENCE_MILESTONE_2B_PHASE2B2E_EXECUTION_PATH,
        litmus.EVIDENCE_MILESTONE_2B_PHASE2B2F_AMENDMENT_PATH,
        RERUN_REGISTRY_PATH,
        litmus.RERUN_LICENSE_SOURCE_PATH,
        litmus.RERUN_LICENSE_TEST_PATH,
        litmus.LEDGER_SOURCE_PATH,
        litmus.LEDGER_TEST_PATH,
        litmus.LEDGER_SEMANTICS_SOURCE_PATH,
        litmus.LEDGER_SEMANTICS_TEST_SUPPORT_PATH,
        litmus.CONTRACT_ORACLE_SOURCE_PATH,
        litmus.CONTRACT_ORACLE_TEST_SUPPORT_PATH,
        litmus.BUNDLE_RESERVATION_SOURCE_PATH,
        litmus.BUNDLE_RESERVATION_TEST_SUPPORT_PATH,
        litmus.ATTEMPT_MANIFEST_SOURCE_PATH,
        litmus.ATTEMPT_MANIFEST_TEST_SUPPORT_PATH,
        litmus.SEED_INVENTORY_SOURCE_PATH,
        litmus.SEED_INVENTORY_TEST_SUPPORT_PATH,
        litmus.LOCAL_ARTIFACT_OBSERVER_SOURCE_PATH,
        litmus.LOCAL_ARTIFACT_OBSERVER_TEST_SUPPORT_PATH,
        litmus.FAKE_CAS_KERNEL_SOURCE_PATH,
        litmus.FAKE_CAS_KERNEL_TEST_SUPPORT_PATH,
        litmus.LOCAL_STAGING_FAKE_PUBLISHER_SOURCE_PATH,
        litmus.LOCAL_STAGING_FAKE_PUBLISHER_TEST_SUPPORT_PATH,
        litmus.SYNTHETIC_RECOVERY_COORDINATOR_SOURCE_PATH,
        litmus.SYNTHETIC_RECOVERY_COORDINATOR_TEST_SUPPORT_PATH,
        litmus.PACKAGE_INIT_PATH,
        litmus.EVALS_PACKAGE_INIT_PATH,
        litmus.TEST_PATH,
        litmus.TIER_PATH,
    }
    assert required <= set(litmus.ANCHOR_PATHS)


def test_seed_inventory_support_is_collected_exactly_once():
    collector = Path("tests/test_uprime_rpc_ledger.py").read_text(encoding="utf-8")
    import_line = "from uprime_rpc_seed_inventory_cases import *  # noqa: F403"
    assert collector.splitlines().count(import_line) == 1
    assert collector.count("uprime_rpc_seed_inventory_cases") == 1


def test_local_artifact_observer_support_is_collected_exactly_once():
    collector = Path("tests/test_uprime_rpc_ledger.py").read_text(encoding="utf-8")
    import_line = (
        "from uprime_rpc_local_artifact_observer_cases import *  # noqa: F403"
    )
    assert collector.splitlines().count(import_line) == 1
    assert collector.count("uprime_rpc_local_artifact_observer_cases") == 1


def test_fake_cas_kernel_support_is_collected_exactly_once():
    collector = Path("tests/test_uprime_rpc_ledger.py").read_text(encoding="utf-8")
    import_line = "from uprime_rpc_fake_cas_kernel_cases import *  # noqa: F403"
    assert collector.splitlines().count(import_line) == 1
    assert collector.count("uprime_rpc_fake_cas_kernel_cases") == 1


def test_local_staging_fake_publisher_support_is_collected_exactly_once():
    collector = Path("tests/test_uprime_rpc_ledger.py").read_text(encoding="utf-8")
    import_line = (
        "from uprime_rpc_local_staging_fake_publisher_cases import *  # noqa: F403"
    )
    assert collector.splitlines().count(import_line) == 1
    assert collector.count("uprime_rpc_local_staging_fake_publisher_cases") == 1


def test_synthetic_recovery_coordinator_support_is_collected_exactly_once():
    collector = Path("tests/test_uprime_rpc_ledger.py").read_text(encoding="utf-8")
    import_line = (
        "from uprime_rpc_synthetic_recovery_coordinator_cases import *  # noqa: F403"
    )
    assert collector.splitlines().count(import_line) == 1
    assert collector.count("uprime_rpc_synthetic_recovery_coordinator_cases") == 1


def test_phase2b2f_implementation_matches_green_preregistration_gate():
    prereg_commit = "8f1c0ba42b9c8568e802b79ee8bfc55ac3459a75"
    amendment_blob = "c72d18a17411071f1d1511581978d1b6792761e6"
    amendment_path = Path(
        "docs/experiments/uprime_odlrq_u1_evidence_milestone_2b_phase2b2f_"
        "integrated_synthetic_manifest_recovery_audit_amendment_2026-07-11.md"
    )
    source_path = Path(
        "lean_rgc/evals/uprime_rpc_integrated_synthetic_manifest.py"
    )
    support_path = Path(
        "tests/uprime_rpc_integrated_synthetic_manifest_cases.py"
    )
    result_path = Path(
        "docs/experiments/uprime_odlrq_u1_evidence_milestone_2b_phase2b2f_"
        "execution_2026-07-11.md"
    )
    assert litmus.EVIDENCE_MILESTONE_2B_PHASE2B2F_AMENDMENT_PATH == amendment_path
    assert litmus.INTEGRATED_SYNTHETIC_MANIFEST_SOURCE_PATH == source_path
    assert litmus.INTEGRATED_SYNTHETIC_MANIFEST_TEST_SUPPORT_PATH == support_path
    assert litmus.EVIDENCE_MILESTONE_2B_PHASE2B2F_EXECUTION_PATH == result_path

    assert litmus.ANCHOR_PATHS.count(
        amendment_path
    ) == 1
    assert source_path.exists() and source_path.is_file() and not source_path.is_symlink()
    assert support_path.exists() and support_path.is_file() and not support_path.is_symlink()
    assert litmus.ANCHOR_PATHS.count(source_path) == 1
    assert litmus.ANCHOR_PATHS.count(support_path) == 1
    assert not os.path.lexists(str(result_path))
    assert result_path not in litmus.ANCHOR_PATHS

    collector = Path("tests/test_uprime_rpc_ledger.py").read_text(encoding="utf-8")
    import_line = (
        "from uprime_rpc_integrated_synthetic_manifest_cases import *  # noqa: F403"
    )
    assert collector.splitlines().count(import_line) == 1
    assert collector.count("uprime_rpc_integrated_synthetic_manifest_cases") == 1

    def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            ["git", *args],
            check=check,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    assert git("hash-object", str(amendment_path)).stdout.decode("ascii").strip() == (
        amendment_blob
    )

    head = git("rev-parse", "HEAD").stdout.decode("ascii").strip()
    prereg_available = (
        git("cat-file", "-e", f"{prereg_commit}^{{commit}}", check=False).returncode
        == 0
    )
    allowed_paths = tuple(
        sorted((
            "lean_rgc/evals/uprime_rpc_integrated_synthetic_manifest.py",
            "tests/uprime_rpc_integrated_synthetic_manifest_cases.py",
            "tests/test_uprime_rpc_ledger.py",
            "lean_rgc/evals/uprime_rpc_litmus.py",
            "tests/test_uprime_rerun_license.py",
        ))
    )
    if prereg_available:
        for path in (source_path, support_path, result_path):
            probe = git(
                "cat-file", "-e", f"{prereg_commit}:{path.as_posix()}",
                check=False,
            )
            assert probe.returncode != 0
        actual_amendment_blob = git(
            "rev-parse", f"{prereg_commit}:{amendment_path.as_posix()}"
        ).stdout.decode("ascii").strip()
        assert actual_amendment_blob == amendment_blob
        if head != prereg_commit:
            ancestry = git(
                "rev-list", "--parents", "-n", "1", "HEAD"
            ).stdout.decode("ascii").split()
            assert ancestry == [head, prereg_commit]
        if head != prereg_commit:
            changed = tuple(
                sorted(
                    git(
                        "diff-tree", "--no-commit-id", "--name-only",
                        "--no-renames", "-r", "HEAD"
                    )
                    .stdout.decode("utf-8")
                    .splitlines()
                )
            )
            assert changed == allowed_paths
    else:
        assert git("rev-parse", "--is-shallow-repository").stdout.decode(
            "ascii"
        ).strip() == "true"
        hidden_ancestry = git(
            "rev-list", "--parents", "-n", "1", "HEAD"
        ).stdout.decode("ascii").split()
        assert hidden_ancestry == [head]

    if head != prereg_commit:
        for path in (source_path, support_path):
            tree_row = git("ls-tree", "HEAD", "--", path.as_posix()).stdout.decode(
                "utf-8"
            ).split()
            assert len(tree_row) == 4
            assert tree_row[:2] == ["100644", "blob"]
            assert tree_row[3] == path.as_posix()

    lines = amendment_path.read_text(encoding="utf-8").splitlines()
    header = (
        "case_id|obligation|killed_mutant|expected_outcome|"
        "expected_side_effects"
    )
    start = lines.index(header) + 1
    expected_matrix = []
    for line in lines[start:]:
        if line == "```":
            break
        cells = tuple(line.split("|"))
        assert len(cells) == 5 and all(cells)
        expected_matrix.append(cells)
    assert len(expected_matrix) == 64

    support = runpy.run_path(str(support_path))
    expected_matrix_tuple = tuple(expected_matrix)
    expected_ids = tuple(row[0] for row in expected_matrix_tuple)
    expected_tests = tuple(f"test_phase2b2f_{case_id}" for case_id in expected_ids)
    assert support["PHASE2B2F_CASE_IDS"] == expected_ids
    assert support["CASE_MATRIX"] == expected_matrix_tuple
    actual_tests = tuple(
        name
        for name, value in support.items()
        if name.startswith("test_phase2b2f_") and callable(value)
    )
    assert actual_tests == expected_tests
    assert tuple(support["__all__"]) == expected_tests


def test_anchor_preflight_compares_head_blob_despite_assume_unchanged(
    tmp_path, monkeypatch
):
    def git(*args: str) -> None:
        subprocess.run(
            ["git", *args],
            cwd=tmp_path,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    git("init")
    git("config", "user.email", "uprime-test@example.invalid")
    git("config", "user.name", "UPrime Test")
    guarded = tmp_path / "guarded.txt"
    guarded.write_text("committed\n", encoding="utf-8", newline="\n")
    git("add", "guarded.txt")
    git("commit", "-m", "guard")
    git("update-index", "--assume-unchanged", "guarded.txt")
    guarded.write_text("silently changed\n", encoding="utf-8", newline="\n")
    monkeypatch.setattr(litmus, "ANCHOR_PATHS", (Path("guarded.txt"),))

    with pytest.raises(RuntimeError, match="anchored input differs from HEAD blob"):
        litmus._assert_anchor_inputs_clean(tmp_path)
