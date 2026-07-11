from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import re
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
        litmus.EVIDENCE_MILESTONE_2B_PHASE2B2F_EXECUTION_PATH,
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
        litmus.INTEGRATED_SYNTHETIC_MANIFEST_SOURCE_PATH,
        litmus.INTEGRATED_SYNTHETIC_MANIFEST_TEST_SUPPORT_PATH,
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


def test_phase2b2f_result_matches_green_implementation_gate():
    prereg_parent = "d838d8c4873e04bc649b8551f0545af5d9944c4c"
    prereg_commit = "8f1c0ba42b9c8568e802b79ee8bfc55ac3459a75"
    implementation_commit = "0a6eb4a92edc1061773c175975f986f0c5ea5a3c"
    result_commit_expected = "df38daea2139b67d9935408c82bfb3297efd9536"
    implementation_blobs = {
        "docs/experiments/uprime_odlrq_u1_evidence_milestone_2b_phase2b2f_"
        "integrated_synthetic_manifest_recovery_audit_amendment_2026-07-11.md":
            "c72d18a17411071f1d1511581978d1b6792761e6",
        "lean_rgc/evals/uprime_rpc_integrated_synthetic_manifest.py":
            "82039799ad79165b4d39bffb38e8fee58bdf3bdc",
        "tests/uprime_rpc_integrated_synthetic_manifest_cases.py":
            "5b84bd782713efd6815995c09ee2d8a54e9bd594",
        "tests/test_uprime_rpc_ledger.py":
            "69694b9d9e3f2f92c4cd19c17534b2e24f7731cc",
        "lean_rgc/evals/uprime_rpc_litmus.py":
            "445e5d032cfbf178aeda74b9e4f9f2886e9bd78e",
        "tests/test_uprime_rerun_license.py":
            "d53fea74951bad131e2c2d9ef1754e278907ed05",
    }
    source_sha256 = "0ECFB8597F86546171613F7DA3A63531D86D7E7787F916C99C85A638DE10E812"
    support_sha256 = "6BB63EDA1D32BADAD04342E26C398CC3BF95FAF98D7D65A1FDB2444BF08EBCBF"
    result_blob = "2013c1fec71dd51bfabcb369a2f1844966786d88"
    result_litmus_blob = "58ea51e44acca2cf2ec86a640e218db5c7c6e095"
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
    litmus_path = Path("lean_rgc/evals/uprime_rpc_litmus.py")
    rerun_test_path = Path("tests/test_uprime_rerun_license.py")
    result_path = Path(
        "docs/experiments/uprime_odlrq_u1_evidence_milestone_2b_phase2b2f_"
        "execution_2026-07-11.md"
    )
    assert litmus.EVIDENCE_MILESTONE_2B_PHASE2B2F_AMENDMENT_PATH == amendment_path
    assert litmus.INTEGRATED_SYNTHETIC_MANIFEST_SOURCE_PATH == source_path
    assert litmus.INTEGRATED_SYNTHETIC_MANIFEST_TEST_SUPPORT_PATH == support_path
    assert litmus.EVIDENCE_MILESTONE_2B_PHASE2B2F_EXECUTION_PATH == result_path

    assert litmus.ANCHOR_PATHS.count(amendment_path) == 1
    assert source_path.exists() and source_path.is_file() and not source_path.is_symlink()
    assert support_path.exists() and support_path.is_file() and not support_path.is_symlink()
    assert result_path.exists() and result_path.is_file() and not result_path.is_symlink()
    assert amendment_path.is_file() and not amendment_path.is_symlink()
    assert litmus_path.is_file() and not litmus_path.is_symlink()
    assert rerun_test_path.is_file() and not rerun_test_path.is_symlink()
    assert litmus.ANCHOR_PATHS.count(source_path) == 1
    assert litmus.ANCHOR_PATHS.count(support_path) == 1
    assert litmus.ANCHOR_PATHS.count(result_path) == 1

    collector_path = Path("tests/test_uprime_rpc_ledger.py")
    collector = collector_path.read_text(encoding="utf-8")
    import_line = (
        "from uprime_rpc_integrated_synthetic_manifest_cases import *  # noqa: F403"
    )
    assert collector.splitlines().count(import_line) == 1
    assert collector.count("uprime_rpc_integrated_synthetic_manifest_cases") == 1

    def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            ["git", "--no-replace-objects", *args],
            check=check,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def raw_parents(commit: str) -> list[str]:
        raw = git("cat-file", "-p", commit).stdout.decode("utf-8")
        headers = raw.split("\n\n", 1)[0].splitlines()
        return [line.removeprefix("parent ") for line in headers if line.startswith("parent ")]

    for path in (amendment_path, source_path, support_path, collector_path):
        expected_blob = implementation_blobs[path.as_posix()]
        assert git("hash-object", str(path)).stdout.decode("ascii").strip() == (
            expected_blob
        )
    assert git("hash-object", str(result_path)).stdout.decode("ascii").strip() == (
        result_blob
    )
    assert hashlib.sha256(source_path.read_bytes()).hexdigest().upper() == source_sha256
    assert hashlib.sha256(support_path.read_bytes()).hexdigest().upper() == support_sha256

    result_text = result_path.read_text(encoding="utf-8")
    assert implementation_commit in result_text
    assert "29153784500" in result_text and "86547466250" in result_text
    assert "three U'0.5 kill probes" in result_text

    head = git("rev-parse", "HEAD").stdout.decode("ascii").strip()
    history_complete = (
        git("cat-file", "-e", f"{prereg_commit}^{{commit}}", check=False).returncode
        == 0
        and git(
            "cat-file", "-e", f"{implementation_commit}^{{commit}}", check=False
        ).returncode == 0
    )
    implementation_paths = tuple(
        sorted((
            "lean_rgc/evals/uprime_rpc_integrated_synthetic_manifest.py",
            "tests/uprime_rpc_integrated_synthetic_manifest_cases.py",
            "tests/test_uprime_rpc_ledger.py",
            "lean_rgc/evals/uprime_rpc_litmus.py",
            "tests/test_uprime_rerun_license.py",
        ))
    )
    result_paths = tuple(sorted((
        result_path.as_posix(),
        "lean_rgc/evals/uprime_rpc_litmus.py",
        "tests/test_uprime_rerun_license.py",
    )))
    if history_complete:
        prereg_ancestry = git(
            "rev-list", "--parents", "-n", "1", prereg_commit
        ).stdout.decode("ascii").split()
        assert prereg_ancestry == [prereg_commit, prereg_parent]
        assert raw_parents(prereg_commit) == [prereg_parent]
        for path in (source_path, support_path, result_path):
            probe = git(
                "cat-file", "-e", f"{prereg_commit}:{path.as_posix()}",
                check=False,
            )
            assert probe.returncode != 0
        assert git(
            "rev-parse", f"{prereg_commit}:{amendment_path.as_posix()}"
        ).stdout.decode("ascii").strip() == implementation_blobs[
            amendment_path.as_posix()
        ]

        implementation_ancestry = git(
            "rev-list", "--parents", "-n", "1", implementation_commit
        ).stdout.decode("ascii").split()
        assert implementation_ancestry == [implementation_commit, prereg_commit]
        assert raw_parents(implementation_commit) == [prereg_commit]
        implementation_changed = tuple(sorted(
            git(
                "diff-tree", "--no-commit-id", "--name-only", "--no-renames",
                "-r", implementation_commit
            ).stdout.decode("utf-8").splitlines()
        ))
        assert implementation_changed == implementation_paths
        for relative, expected_blob in implementation_blobs.items():
            actual_blob = git(
                "rev-parse", f"{implementation_commit}:{relative}"
            ).stdout.decode("ascii").strip()
            assert actual_blob == expected_blob
            tree_row = git(
                "ls-tree", implementation_commit, "--", relative
            ).stdout.decode("utf-8").split()
            assert len(tree_row) == 4
            assert tree_row[:3] == ["100644", "blob", expected_blob]
            assert tree_row[3] == relative
        assert git(
            "cat-file", "-e", f"{implementation_commit}:{result_path.as_posix()}",
            check=False,
        ).returncode != 0

        result_commits = git(
            "log", "--diff-filter=A", "--format=%H", "--", result_path.as_posix()
        ).stdout.decode("ascii").splitlines()
        if result_commits:
            result_commit = result_commits[0]
            assert result_commit == result_commit_expected
            result_ancestry = git(
                "rev-list", "--parents", "-n", "1", result_commit
            ).stdout.decode("ascii").split()
            assert result_ancestry == [result_commit, implementation_commit]
            assert raw_parents(result_commit) == [implementation_commit]
            result_changed = tuple(sorted(
                git(
                    "diff-tree", "--no-commit-id", "--name-only", "--no-renames",
                    "-r", result_commit
                ).stdout.decode("utf-8").splitlines()
            ))
            assert result_changed == result_paths
            result_tree = git(
                "ls-tree", result_commit, "--", result_path.as_posix()
            ).stdout.decode("utf-8").split()
            assert len(result_tree) == 4
            assert result_tree[:2] == ["100644", "blob"]
            assert result_tree[2] == result_blob
            assert result_tree[3] == result_path.as_posix()
            for relative in result_paths:
                result_row = git(
                    "ls-tree", result_commit, "--", relative
                ).stdout.decode("utf-8").split()
                assert len(result_row) == 4
                assert result_row[:2] == ["100644", "blob"]
                if relative == result_path.as_posix():
                    assert result_row[2] == result_blob
                if relative == litmus_path.as_posix():
                    assert result_row[2] == result_litmus_blob
                assert result_row[3] == relative
        else:
            assert head == implementation_commit
    else:
        assert git("rev-parse", "--is-shallow-repository").stdout.decode(
            "ascii"
        ).strip() == "true"
        hidden_ancestry = git(
            "rev-list", "--parents", "-n", "1", "HEAD"
        ).stdout.decode("ascii").split()
        assert hidden_ancestry == [head]
        parents = raw_parents(head)
        if parents == [implementation_commit]:
            assert head == result_commit_expected
        elif parents == [result_commit_expected]:
            assert litmus.UPPER_STACK_IMPLEMENTATION_PLAN_AND_U05_AMENDMENT_PATH.is_file()
        else:
            assert len(parents) == 1
            assert litmus.UPPER_STACK_IMPLEMENTATION_PLAN_AND_U05_AMENDMENT_PATH.is_file()

    for path in (amendment_path, source_path, support_path, collector_path):
        tree_row = git("ls-tree", "HEAD", "--", path.as_posix()).stdout.decode(
            "utf-8"
        ).split()
        assert len(tree_row) == 4
        assert tree_row[:2] == ["100644", "blob"]
        assert tree_row[2] == implementation_blobs[path.as_posix()]
        assert tree_row[3] == path.as_posix()
    if head != implementation_commit or not history_complete:
        result_tree = git(
            "ls-tree", "HEAD", "--", result_path.as_posix()
        ).stdout.decode("utf-8").split()
        assert len(result_tree) == 4
        assert result_tree[:2] == ["100644", "blob"]
        assert result_tree[2] == result_blob
        assert result_tree[3] == result_path.as_posix()
        if head == result_commit_expected:
            litmus_tree = git(
                "ls-tree", "HEAD", "--", litmus_path.as_posix()
            ).stdout.decode("utf-8").split()
            assert len(litmus_tree) == 4
            assert litmus_tree[:3] == ["100644", "blob", result_litmus_blob]
            assert litmus_tree[3] == litmus_path.as_posix()
        rerun_tree = git(
            "ls-tree", "HEAD", "--", rerun_test_path.as_posix()
        ).stdout.decode("utf-8").split()
        assert len(rerun_tree) == 4
        assert rerun_tree[:2] == ["100644", "blob"]
        assert rerun_tree[3] == rerun_test_path.as_posix()

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


def test_upper_stack_plan_and_u05_amendment_seals_phase2b2f_result():
    result_commit = "df38daea2139b67d9935408c82bfb3297efd9536"
    result_parent = "0a6eb4a92edc1061773c175975f986f0c5ea5a3c"
    result_blobs = {
        "docs/experiments/uprime_odlrq_u1_evidence_milestone_2b_"
        "phase2b2f_execution_2026-07-11.md":
            "2013c1fec71dd51bfabcb369a2f1844966786d88",
        "lean_rgc/evals/uprime_rpc_litmus.py":
            "58ea51e44acca2cf2ec86a640e218db5c7c6e095",
        "tests/test_uprime_rerun_license.py":
            "8966af27c07f97b0fff85fb2229f577142e9db7f",
    }
    result_paths = tuple(sorted(result_blobs))
    plan_path = Path(
        "docs/experiments/"
        "uprime_odlrq_upper_stack_implementation_plan_and_u05_amendment_2026-07-11.md"
    )
    litmus_path = Path("lean_rgc/evals/uprime_rpc_litmus.py")
    test_path = Path("tests/test_uprime_rerun_license.py")
    plan_paths = tuple(sorted((
        plan_path.as_posix(),
        litmus_path.as_posix(),
        test_path.as_posix(),
    )))
    future_apparatus = (
        "lean_rgc/lean/kernel_state_identity.py",
        "lean_rgc/lean/kernel_rpc_client.py",
        "lean_rgc/odlrq/contracts.py",
        "lean_rgc/evals/uprime_u05_kill_probes.py",
        "tests/test_uprime_u05_identity.py",
        "tests/test_uprime_u05_kill_probes.py",
    )

    assert litmus.UPPER_STACK_IMPLEMENTATION_PLAN_AND_U05_AMENDMENT_PATH == plan_path
    assert litmus.ANCHOR_PATHS.count(plan_path) == 1
    assert plan_path.is_file() and not plan_path.is_symlink()
    assert litmus_path.is_file() and not litmus_path.is_symlink()
    assert test_path.is_file() and not test_path.is_symlink()

    plan_text = plan_path.read_text(encoding="utf-8")
    for literal in (
        result_commit,
        result_parent,
        *result_blobs.values(),
        "29154121499",
        "86548332796",
        "13ffca6de484effc66f0e628d2e46823277271c6",
        "C86569C9C5A793C842BD3F4D7E5795A16C5B6C0B8F6E806F3D30D6A8B571E0E3",
        "6EA21704F48153362504D4AC7F753C30B8EF6FBDFB0FD98B15A37E56120D393D",
        "upper_stack_substrate_rpc",
        "upper_stack_substrate_models",
        "upper_stack_governance_map",
        "Final disposition: APPROVE",
    ):
        assert literal in plan_text
    assert "ssh -p" not in plan_text.lower()
    assert re.search(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", plan_text) is None

    json_blocks = re.findall(r"```json\n(\[.*?\])\n```", plan_text, re.DOTALL)
    assert len(json_blocks) >= 2
    task_matrix = json.loads(json_blocks[0])
    assert [row["task_id"] for row in task_matrix] == [
        "u05_identity",
        "u05_pair",
        "u05_split",
        "u05_nested_split",
        "u05_nat_zero",
    ]
    task_bytes = json.dumps(
        task_matrix,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    assert hashlib.sha256(task_bytes).hexdigest().upper() == (
        "C86569C9C5A793C842BD3F4D7E5795A16C5B6C0B8F6E806F3D30D6A8B571E0E3"
    )

    action_matrix = json.loads(json_blocks[1])
    assert len(action_matrix) == 12
    assert [row["action_id"] for row in action_matrix] == sorted(
        row["action_id"] for row in action_matrix
    )
    assert {row["target_selector"] for row in action_matrix} == {"first", "last"}
    assert all(row["max_heartbeats"] == 20_000 for row in action_matrix)
    assert all("premise_slot_rule_id" in row for row in action_matrix)
    action_bytes = json.dumps(
        action_matrix,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    assert hashlib.sha256(action_bytes).hexdigest().upper() == (
        "6EA21704F48153362504D4AC7F753C30B8EF6FBDFB0FD98B15A37E56120D393D"
    )

    registry = load_rerun_registry(Path(RERUN_REGISTRY_PATH))
    assert registry == _empty_registry()

    def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            ["git", "--no-replace-objects", *args],
            check=check,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def raw_parents(commit: str) -> list[str]:
        raw = git("cat-file", "-p", commit).stdout.decode("utf-8")
        headers = raw.split("\n\n", 1)[0].splitlines()
        return [line.removeprefix("parent ") for line in headers if line.startswith("parent ")]

    head = git("rev-parse", "HEAD").stdout.decode("ascii").strip()
    result_available = (
        git("cat-file", "-e", f"{result_commit}^{{commit}}", check=False).returncode
        == 0
    )
    if result_available:
        assert raw_parents(result_commit) == [result_parent]
        changed = tuple(sorted(
            git(
                "diff-tree", "--no-commit-id", "--name-only", "--no-renames",
                "-r", result_commit,
            ).stdout.decode("utf-8").splitlines()
        ))
        assert changed == result_paths
        for relative, expected_blob in result_blobs.items():
            row = git("ls-tree", result_commit, "--", relative).stdout.decode(
                "utf-8"
            ).split()
            assert row == ["100644", "blob", expected_blob, relative]

        additions = git(
            "log", "--diff-filter=A", "--format=%H", "--", plan_path.as_posix()
        ).stdout.decode("ascii").splitlines()
        if additions:
            plan_commit = additions[0]
            assert raw_parents(plan_commit) == [result_commit]
            plan_changed = tuple(sorted(
                git(
                    "diff-tree", "--no-commit-id", "--name-only", "--no-renames",
                    "-r", plan_commit,
                ).stdout.decode("utf-8").splitlines()
            ))
            assert plan_changed == plan_paths
            for relative in plan_paths:
                row = git("ls-tree", plan_commit, "--", relative).stdout.decode(
                    "utf-8"
                ).split()
                assert len(row) == 4 and row[:2] == ["100644", "blob"]
                assert row[3] == relative
            for relative in future_apparatus:
                assert git(
                    "cat-file", "-e", f"{plan_commit}:{relative}", check=False
                ).returncode != 0
        else:
            # Pre-commit local validation is allowed only on the sealed result
            # head. Hosted CI and every descendant take the strict branch above.
            assert head == result_commit
            status = git("status", "--porcelain=v1", "--", plan_path.as_posix())
            assert status.stdout.decode("utf-8").startswith("?? ")
            for relative in future_apparatus:
                assert not Path(relative).exists()
    else:
        assert git("rev-parse", "--is-shallow-repository").stdout.decode(
            "ascii"
        ).strip() == "true"
        parents = raw_parents(head)
        assert len(parents) == 1
        if parents == [result_commit]:
            # Exact depth-one plan-commit CI: parent/diff contents are sealed by
            # raw parent plus the three current regular paths and literals above.
            for relative in plan_paths:
                row = git("ls-tree", "HEAD", "--", relative).stdout.decode(
                    "utf-8"
                ).split()
                assert len(row) == 4 and row[:2] == ["100644", "blob"]
                assert row[3] == relative
            for relative in future_apparatus:
                assert not Path(relative).exists()


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


def test_u05_one_look_result_is_canonical_anchored_and_default_deny():
    candidate = "3bb3408afc50a08307cff2c9b1906a299739dfb5"
    artifact_sha256 = (
        "75BD0F4A742FD7F5DA221FD629DA58F080FD17CB0ACE9BFC8150153D8FDB55F8"
    )
    artifact_blob = "33061cffae56abf4ed2a4fcdb9400eb2004e61c6"
    raw_sha256 = "704E05D66AB57633F015486C4C9E4718493A8A3529F3877693DD56B7CB79E6E9"
    expected_paths = tuple(
        sorted(
            (
                "docs/experiments/uprime_odlrq_u05_execution_2026-07-11.md",
                "docs/experiments/artifacts/uprime_u05_20260711/u05_kill_probes.json",
                "lean_rgc/evals/uprime_rpc_litmus.py",
                "tests/test_uprime_rerun_license.py",
            )
        )
    )
    result_path = Path(expected_paths[1])
    artifact_path = Path(expected_paths[0])
    # The sorted order places the artifact before the execution document.
    assert artifact_path == litmus.UPRIME_U05_EXECUTION_ARTIFACT_PATH
    assert result_path == litmus.UPRIME_U05_EXECUTION_RESULT_PATH
    assert litmus.ANCHOR_PATHS.count(artifact_path) == 1
    assert litmus.ANCHOR_PATHS.count(result_path) == 1
    assert artifact_path.is_file() and not artifact_path.is_symlink()
    assert result_path.is_file() and not result_path.is_symlink()

    def reject_duplicates(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError(f"duplicate JSON key: {key}")
            value[key] = item
        return value

    def reject_constant(value):
        raise ValueError(f"nonfinite JSON constant: {value}")

    artifact_bytes = artifact_path.read_bytes()
    assert len(artifact_bytes) == 160_974
    assert hashlib.sha256(artifact_bytes).hexdigest().upper() == artifact_sha256
    assert (
        subprocess.run(
            ["git", "hash-object", "--stdin"],
            input=artifact_bytes,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        .stdout.decode("ascii")
        .strip()
        == artifact_blob
    )
    envelope = json.loads(
        artifact_bytes.decode("utf-8", errors="strict"),
        object_pairs_hook=reject_duplicates,
        parse_constant=reject_constant,
    )
    assert artifact_bytes == (
        json.dumps(
            envelope,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
    )
    assert envelope["schema"] == "lean-rgc-uprime-u05-attempt-envelope-v1.0"
    assert envelope["candidate"] == candidate
    assert envelope["envelope_kind"] == "runner_complete"
    assert envelope["look_consumed"] is True
    assert envelope["matrix_open_marker_valid"] is True
    assert envelope["raw_child_schema_valid"] is True
    assert envelope["raw_child_status"] == "U05_COMPLETE"
    assert envelope["process"]["exit_code"] == 0
    assert envelope["process"]["exception_class"] is None
    assert envelope["process"]["stdout"]["byte_length"] == 0
    assert envelope["process"]["stderr"]["byte_length"] == 0

    raw_bytes = base64.b64decode(
        envelope["raw_child_output"]["bytes_base64"], validate=True
    )
    assert len(raw_bytes) == envelope["raw_child_output"]["byte_length"] == 9_208
    assert hashlib.sha256(raw_bytes).hexdigest().upper() == raw_sha256
    assert envelope["raw_child_output"]["sha256"] == raw_sha256
    raw = json.loads(
        raw_bytes.decode("utf-8", errors="strict"),
        object_pairs_hook=reject_duplicates,
        parse_constant=reject_constant,
    )
    assert raw_bytes == (
        json.dumps(
            raw,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
    )
    assert raw["status"] == "U05_COMPLETE"
    assert raw["candidate"] == candidate
    assert raw["probe_report"]["kp1"]["disposition"] == "U05_KP1_SCALE_READY"
    assert raw["probe_report"]["kp2"]["disposition"] == "U05_KP2_EVENTUAL_WINDOW"
    assert raw["probe_report"]["kp3"]["disposition"] == "U05_KP3_PLATEAU_AT_D3"
    expected_licenses = {
        "licenses_k1_k4",
        "licenses_u2_u5_claims",
        "licenses_wp4_wp12_implementation",
        "licenses_gpu",
        "licenses_canonical_rpc_rerun",
        "licenses_reserved_data_read",
    }
    assert {key for key in raw if key.startswith("licenses_")} == expected_licenses
    assert {
        key for key in raw["probe_report"] if key.startswith("licenses_")
    } == expected_licenses
    assert all(raw[key] is False for key in expected_licenses)
    assert all(raw["probe_report"][key] is False for key in expected_licenses)
    capabilities = raw["probe_report"]["capability_matrix"]
    assert capabilities["candidate_exact_partition"] == {
        "candidate": True,
        "may_draft": True,
        "scale_ready": True,
    }
    assert capabilities["candidate_hankel_predictive_model"] == {
        "candidate": True,
        "may_draft": True,
    }
    assert capabilities["candidate_componentwise_window"] == {
        "candidate": True,
        "may_draft": True,
    }
    assert all(
        capabilities[name]["candidate"] is False
        and capabilities[name]["may_draft"] is False
        for name in (
            "candidate_finite_horizon_envelope",
            "candidate_maxent_nominal",
            "candidate_predictive_similarity",
            "candidate_positive_similarity",
        )
    )

    receipt_bytes = base64.b64decode(envelope["receipt"]["bytes_base64"], validate=True)
    assert hashlib.sha256(receipt_bytes).hexdigest().upper() == (
        "E3225BE4AB7E3BE5E482B119352DD0A8F08891E6D7E9336859FB35FF2DF9D0BB"
    )
    receipt = json.loads(
        receipt_bytes.decode("utf-8", errors="strict"),
        object_pairs_hook=reject_duplicates,
        parse_constant=reject_constant,
    )
    assert receipt["candidate"] == candidate
    assert receipt["ci_control_plane"]["run_id"] == 29166073728
    assert receipt["ci_control_plane"]["job_id"] == 86579287017
    assert receipt["ci_control_plane"]["conclusion"] == "success"
    assert receipt["rerun_registry"]["default_allow"] is False
    assert receipt["rerun_registry"]["license_count"] == 0
    assert load_rerun_registry(Path(RERUN_REGISTRY_PATH)) == _empty_registry()

    result_text = result_path.read_text(encoding="utf-8")
    for literal in (
        candidate,
        artifact_sha256,
        artifact_blob,
        raw_sha256,
        "U05_KP1_SCALE_READY",
        "U05_KP2_EVENTUAL_WINDOW",
        "U05_KP3_PLATEAU_AT_D3",
        "licenses_gpu                      false",
    ):
        assert literal in result_text
    assert "ssh -p" not in result_text.lower()
    assert re.search(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", result_text) is None

    def git(*args, check=True):
        return subprocess.run(
            ["git", "--no-replace-objects", *args],
            check=check,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def raw_parents(commit):
        payload = git("cat-file", "-p", commit).stdout.decode("utf-8")
        return [
            row.removeprefix("parent ")
            for row in payload.split("\n\n", 1)[0].splitlines()
            if row.startswith("parent ")
        ]

    head = git("rev-parse", "HEAD").stdout.decode("ascii").strip()
    if head == candidate:
        # Pre-commit local verification: the candidate is immutable and only
        # the four frozen result paths may be dirty/untracked.
        status = git("status", "--porcelain=v1", "--untracked-files=all").stdout.decode(
            "utf-8"
        )
        changed = tuple(sorted(row[3:] for row in status.splitlines() if row))
        assert changed == expected_paths
        return

    result_commit = None
    if raw_parents(head) == [candidate]:
        result_commit = head
    elif git("cat-file", "-e", f"{candidate}^{{commit}}", check=False).returncode == 0:
        additions = git(
            "log",
            "--diff-filter=A",
            "--format=%H",
            "--",
            result_path.as_posix(),
        ).stdout.decode("ascii").splitlines()
        if additions:
            result_commit = additions[0]
    if result_commit is not None:
        assert raw_parents(result_commit) == [candidate]
        if git("cat-file", "-e", f"{candidate}^{{commit}}", check=False).returncode == 0:
            changed = tuple(
                sorted(
                    git(
                        "diff-tree",
                        "--no-commit-id",
                        "--name-only",
                        "--no-renames",
                        "-r",
                        result_commit,
                    ).stdout.decode("utf-8").splitlines()
                )
            )
            assert changed == expected_paths
        else:
            assert git("rev-parse", "--is-shallow-repository").stdout.decode(
                "ascii"
            ).strip() == "true"
        for relative in expected_paths:
            row = git("ls-tree", result_commit, "--", relative).stdout.decode(
                "utf-8"
            ).split()
            assert len(row) == 4 and row[:2] == ["100644", "blob"]
            assert row[3] == relative
