from __future__ import annotations

import json
from pathlib import Path
import subprocess
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]

RECOVERY_PARENT = "92b34496d3f2455a63e05791b7a0342050c49bcd"
AMENDMENT_COMMIT = "2712060ff5b0223aa581dd611363dba517520048"
AMENDMENT_PATH = (
    "docs/experiments/"
    "uprime_odlrq_lane_isolated_recovery_amendment_2026-07-12.md"
)
IDENTITY_PATH = "tests/test_odlrq_lane_isolated_recovery_identity.py"
MANIFEST_PATH = "tests/tier_manifest.json"
CI_WORKFLOW_PATH = ".github/workflows/ci.yml"
CLOSEOUT_PATH = (
    "docs/experiments/"
    "uprime_odlrq_lane_isolated_recovery_closeout_2026-07-12.md"
)
LEGACY_IDENTITY_PATH = "tests/test_uprime_u05_identity.py"
CONTROL_REPAIR_PATH = (
    "docs/experiments/"
    "uprime_odlrq_lane_isolated_recovery_control_plane_repair_2026-07-12.md"
)
M5_CORRECTION_PATH = (
    "docs/experiments/"
    "uprime_odlrq_m5_two_sided_hankel_closure_amendment_2026-07-12.md"
)

AMENDMENT_DOCUMENT_BLOB = "955872dacb1ebfe6328a178797b68479ebc55069"
AMENDMENT_MANIFEST_BLOB = "dd52b95c998e1bf09466d62856b1e6a73256542d"
AMENDMENT_WORKFLOW_BLOB = "8fb0f09a45db657bb03cd0a6ef26c96b6beee800"
AMENDMENT_PATHS = {
    AMENDMENT_PATH,
    IDENTITY_PATH,
    MANIFEST_PATH,
    CI_WORKFLOW_PATH,
}
ORIGINAL_AMENDMENT_IDENTITY_BLOB = "b64bb52453b67118c7b7e6a89a38d8a4438ac6b8"
ORIGINAL_LEGACY_IDENTITY_BLOB = "ecb65579d800c78cbc070a101f7282db73871cd9"
CONTROL_REPAIR_DOCUMENT_BLOB = "494e424b36f20b4ad9efa6093dcebf30a78f045a"
CONTROL_REPAIR_LEGACY_IDENTITY_BLOB = "277f46ec0e4cecfe6ae3d119adb85c2b3a043182"
CONTROL_REPAIR_PATHS = {
    CONTROL_REPAIR_PATH,
    LEGACY_IDENTITY_PATH,
    IDENTITY_PATH,
}
CONTROL_REPAIR_COMMIT = "40cb97a8bac94e17538958c33c53b2f2c758b0f5"
M5_CORRECTION_PARENT = "9f67edeff33c77a756788c29023f693d1bad8ab8"
M5_CORRECTION_PARENT_IDENTITY_BLOB = "959b900902e15273fc4aa507d265300cb758dd96"
M5_CORRECTION_DOCUMENT_BLOB = "93d5417d3b313bc3559f9eebceaeab1ffcfed26d"
M5_CORRECTION_PATHS = {
    M5_CORRECTION_PATH,
    IDENTITY_PATH,
}

IMMUTABLE_PREDECESSOR_BLOBS = {
    "lean_rgc/odlrq/contracts.py":
        "eca7d55bc7c2a7a08fbdc75c3b589f1972cd258f",
    "lean_rgc/odlrq/adapters.py":
        "12b46d6418c69fd842b347a24ec783e5de052b76",
    "lean_rgc/odlrq/behavioral_partition.py":
        "0f6e961b5158b5bc684898d6ee2740427d9a689e",
    "tests/test_odlrq_behavioral_partition.py":
        "7b500bac52051744cd0032b5af8bfc1b64c30aed",
    (
        "docs/experiments/"
        "uprime_odlrq_cpu_survivor_implementation_bundle_closeout_2026-07-12.md"
    ): "c86f6d54be728d5bae429d1c7e362f580c3fe536",
    (
        "docs/experiments/artifacts/"
        "uprime_u05_20260711/u05_kill_probes.json"
    ): "33061cffae56abf4ed2a4fcdb9400eb2004e61c6",
    "docs/experiments/uprime_odlrq_u05_execution_2026-07-11.md":
        "724f8c426aa71de62c1f0837f36077133e64ca6f",
    "lean_rgc/evals/uprime_rpc_litmus.py":
        "2bbc052a2afa954b46090dcdcf2ec082d8e9a1a4",
    "tests/test_uprime_rerun_license.py":
        "9f1e20e742aa3c53cd779a1ca392e870a7e15477",
}

M4_ALLOWLIST = {
    "lean_rgc/odlrq/__init__.py",
    "lean_rgc/odlrq/quotient_generator.py",
    "tests/test_odlrq_quotient_generator.py",
    "tools/run_uprime_wp6_t_recovery_tests.ps1",
    MANIFEST_PATH,
}
M5_ALLOWLIST = {
    "lean_rgc/odlrq/__init__.py",
    "lean_rgc/odlrq/hankel_predictive.py",
    "tests/test_odlrq_hankel_predictive.py",
    "tools/run_uprime_wp4_h_recovery_tests.ps1",
    MANIFEST_PATH,
}
M6_ALLOWLIST = {
    "lean_rgc/odlrq/__init__.py",
    "lean_rgc/odlrq/componentwise_window.py",
    "tests/test_odlrq_componentwise_window.py",
    "tools/run_uprime_wp4_w_recovery_tests.ps1",
    MANIFEST_PATH,
}

LANES = (
    (
        "M4",
        M4_ALLOWLIST,
        M4_ALLOWLIST - {"lean_rgc/odlrq/__init__.py", MANIFEST_PATH},
        "test_odlrq_quotient_generator.py",
    ),
    (
        "M5",
        M5_ALLOWLIST,
        M5_ALLOWLIST - {"lean_rgc/odlrq/__init__.py", MANIFEST_PATH},
        "test_odlrq_hankel_predictive.py",
    ),
    (
        "M6",
        M6_ALLOWLIST,
        M6_ALLOWLIST - {"lean_rgc/odlrq/__init__.py", MANIFEST_PATH},
        "test_odlrq_componentwise_window.py",
    ),
)

MAX_COMMITS_PER_LANE = 2


def _git(*args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", "--no-replace-objects", *args],
        cwd=REPO_ROOT,
        check=check,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _head() -> str:
    return _git("rev-parse", "HEAD").stdout.decode("ascii").strip()


def _raw_parents(commit: str) -> list[str]:
    # Read the commit payload itself.  Unlike rev-list, this retains the raw
    # parent header even when a parent object is absent in a shallow checkout.
    payload = _git("cat-file", "-p", commit).stdout.decode("utf-8")
    return [row[7:] for row in payload.splitlines() if row.startswith("parent ")]


def _tree_blob(revision: str, path: str) -> str:
    return (
        _git("rev-parse", f"{revision}:{path}")
        .stdout.decode("ascii")
        .strip()
    )


def _changed_paths(commit: str) -> set[str]:
    return set(
        _git(
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "--no-renames",
            "-r",
            commit,
        )
        .stdout.decode("utf-8")
        .splitlines()
    )


def _manifest(revision: str) -> dict[str, Any]:
    value = json.loads(_git("show", f"{revision}:{MANIFEST_PATH}").stdout)
    assert type(value) is dict
    return value


def _worktree_manifest() -> dict[str, Any]:
    value = json.loads((REPO_ROOT / MANIFEST_PATH).read_text(encoding="utf-8"))
    assert type(value) is dict
    return value


def _assert_one_manifest_append(
    before: dict[str, Any], after: dict[str, Any], expected_name: str
) -> None:
    assert set(after) - set(before) == {expected_name}
    assert set(before) <= set(after)
    for name, tiers in before.items():
        assert after[name] == tiers
    assert after[expected_name] == ["unit"]


def _assert_predecessor_blobs(revision: str) -> None:
    for path, expected_blob in IMMUTABLE_PREDECESSOR_BLOBS.items():
        assert _tree_blob(revision, path) == expected_blob


def _assert_recovery_base(
    revision: str, *, recovery_identity_blob: str
) -> None:
    _assert_predecessor_blobs(revision)
    assert _tree_blob(revision, AMENDMENT_PATH) == AMENDMENT_DOCUMENT_BLOB
    assert _tree_blob(revision, CI_WORKFLOW_PATH) == AMENDMENT_WORKFLOW_BLOB
    assert _tree_blob(revision, CONTROL_REPAIR_PATH) == CONTROL_REPAIR_DOCUMENT_BLOB
    assert (
        _tree_blob(revision, LEGACY_IDENTITY_PATH)
        == CONTROL_REPAIR_LEGACY_IDENTITY_BLOB
    )
    assert _tree_blob(revision, IDENTITY_PATH) == recovery_identity_blob


def _assert_m5_correction_base(
    revision: str, *, correction_identity_blob: str
) -> None:
    _assert_recovery_base(
        revision, recovery_identity_blob=correction_identity_blob
    )
    assert (
        _tree_blob(revision, M5_CORRECTION_PATH)
        == M5_CORRECTION_DOCUMENT_BLOB
    )


def test_lane_isolated_recovery_anchor_and_topology_are_immutable() -> None:
    head = _head()

    if head == M5_CORRECTION_PARENT:
        # One-time, pre-commit validation for the M5 mathematical-direction
        # correction.  The identity file cannot pin its own future Git blob;
        # pin the exact parent, document blob, and scoped two-path dirt now.
        status = (
            _git(
                "status",
                "--porcelain=v1",
                "--untracked-files=all",
                "--",
                *sorted(M5_CORRECTION_PATHS),
            )
            .stdout.decode("utf-8")
            .splitlines()
        )
        dirty_paths = {row[3:] for row in status if len(row) >= 4}
        assert dirty_paths == M5_CORRECTION_PATHS
        assert (
            _git("hash-object", M5_CORRECTION_PATH)
            .stdout.decode("ascii")
            .strip()
            == M5_CORRECTION_DOCUMENT_BLOB
        )
        assert _raw_parents("HEAD") == [CONTROL_REPAIR_COMMIT]
        assert _changed_paths("HEAD") == M4_ALLOWLIST
        assert (
            _tree_blob("HEAD", IDENTITY_PATH)
            == M5_CORRECTION_PARENT_IDENTITY_BLOB
        )
        _assert_recovery_base(
            "HEAD",
            recovery_identity_blob=M5_CORRECTION_PARENT_IDENTITY_BLOB,
        )
        _assert_one_manifest_append(
            _manifest(CONTROL_REPAIR_COMMIT),
            _manifest("HEAD"),
            "test_odlrq_quotient_generator.py",
        )
        return

    if head == AMENDMENT_COMMIT:
        # Pre-commit validation for the one control-plane successor.  The
        # recovery identity file cannot contain its own future Git blob, so the
        # other two blobs and the exact scoped three-path dirt are frozen here.
        status = (
            _git(
                "status",
                "--porcelain=v1",
                "--untracked-files=all",
                "--",
                *sorted(CONTROL_REPAIR_PATHS),
            )
            .stdout.decode("utf-8")
            .splitlines()
        )
        dirty_paths = {row[3:] for row in status if len(row) >= 4}
        assert dirty_paths == CONTROL_REPAIR_PATHS
        assert (
            _git("hash-object", CONTROL_REPAIR_PATH)
            .stdout.decode("ascii")
            .strip()
            == CONTROL_REPAIR_DOCUMENT_BLOB
        )
        assert (
            _git("hash-object", LEGACY_IDENTITY_PATH)
            .stdout.decode("ascii")
            .strip()
            == CONTROL_REPAIR_LEGACY_IDENTITY_BLOB
        )
        assert _tree_blob("HEAD", AMENDMENT_PATH) == AMENDMENT_DOCUMENT_BLOB
        assert _tree_blob("HEAD", MANIFEST_PATH) == AMENDMENT_MANIFEST_BLOB
        assert _tree_blob("HEAD", CI_WORKFLOW_PATH) == AMENDMENT_WORKFLOW_BLOB
        assert (
            _tree_blob("HEAD", IDENTITY_PATH)
            == ORIGINAL_AMENDMENT_IDENTITY_BLOB
        )
        assert (
            _tree_blob("HEAD", LEGACY_IDENTITY_PATH)
            == ORIGINAL_LEGACY_IDENTITY_BLOB
        )
        _assert_predecessor_blobs("HEAD")
        return

    if head == RECOVERY_PARENT:
        # Pre-commit validation is scoped to the amendment paths, so unrelated
        # user-owned dirt in the shared worktree remains untouched and ignored.
        status = (
            _git(
                "status",
                "--porcelain=v1",
                "--untracked-files=all",
                "--",
                *sorted(AMENDMENT_PATHS),
            )
            .stdout.decode("utf-8")
            .splitlines()
        )
        dirty_paths = {row[3:] for row in status if len(row) >= 4}
        assert dirty_paths == AMENDMENT_PATHS
        assert (
            _git("hash-object", AMENDMENT_PATH).stdout.decode("ascii").strip()
            == AMENDMENT_DOCUMENT_BLOB
        )
        assert (
            _git("hash-object", CI_WORKFLOW_PATH).stdout.decode("ascii").strip()
            == AMENDMENT_WORKFLOW_BLOB
        )
        assert (
            _git("hash-object", MANIFEST_PATH).stdout.decode("ascii").strip()
            == AMENDMENT_MANIFEST_BLOB
        )
        _assert_one_manifest_append(
            _manifest("HEAD"),
            _worktree_manifest(),
            Path(IDENTITY_PATH).name,
        )
        _assert_predecessor_blobs("HEAD")
        return

    assert (
        _git("rev-parse", "--is-shallow-repository")
        .stdout.decode("ascii")
        .strip()
        == "false"
    ), "lane-isolated recovery identity requires full Git history"

    additions = (
        _git(
            "log",
            "--diff-filter=A",
            "--format=%H",
            "--",
            AMENDMENT_PATH,
        )
        .stdout.decode("ascii")
        .splitlines()
    )
    assert len(additions) == 1
    amendment_commit = additions[0]
    assert amendment_commit == AMENDMENT_COMMIT
    assert _raw_parents(amendment_commit) == [RECOVERY_PARENT]
    assert _changed_paths(amendment_commit) == AMENDMENT_PATHS
    assert _tree_blob(amendment_commit, AMENDMENT_PATH) == AMENDMENT_DOCUMENT_BLOB
    assert _tree_blob(amendment_commit, MANIFEST_PATH) == AMENDMENT_MANIFEST_BLOB
    assert _tree_blob(amendment_commit, CI_WORKFLOW_PATH) == AMENDMENT_WORKFLOW_BLOB
    _assert_one_manifest_append(
        _manifest(RECOVERY_PARENT),
        _manifest(amendment_commit),
        Path(IDENTITY_PATH).name,
    )
    _assert_predecessor_blobs(amendment_commit)
    assert (
        _tree_blob(amendment_commit, IDENTITY_PATH)
        == ORIGINAL_AMENDMENT_IDENTITY_BLOB
    )
    assert (
        _tree_blob(amendment_commit, LEGACY_IDENTITY_PATH)
        == ORIGINAL_LEGACY_IDENTITY_BLOB
    )

    repair_additions = (
        _git(
            "log",
            "--diff-filter=A",
            "--format=%H",
            "--",
            CONTROL_REPAIR_PATH,
        )
        .stdout.decode("ascii")
        .splitlines()
    )
    assert len(repair_additions) == 1
    phase_anchor = repair_additions[0]
    assert phase_anchor == CONTROL_REPAIR_COMMIT
    assert _raw_parents(phase_anchor) == [amendment_commit]
    assert _changed_paths(phase_anchor) == CONTROL_REPAIR_PATHS
    assert (
        _tree_blob(phase_anchor, CONTROL_REPAIR_PATH)
        == CONTROL_REPAIR_DOCUMENT_BLOB
    )
    assert (
        _tree_blob(phase_anchor, LEGACY_IDENTITY_PATH)
        == CONTROL_REPAIR_LEGACY_IDENTITY_BLOB
    )
    assert _manifest(phase_anchor) == _manifest(amendment_commit)
    recovery_identity_blob = _tree_blob(phase_anchor, IDENTITY_PATH)
    assert recovery_identity_blob == M5_CORRECTION_PARENT_IDENTITY_BLOB
    _assert_recovery_base(
        phase_anchor, recovery_identity_blob=recovery_identity_blob
    )

    # M4 is a completed, immutable predecessor of the one-time mathematical
    # correction.  The correction does not reopen M4 or consume a lane commit.
    assert _raw_parents(M5_CORRECTION_PARENT) == [phase_anchor]
    assert _changed_paths(M5_CORRECTION_PARENT) == M4_ALLOWLIST
    _assert_recovery_base(
        M5_CORRECTION_PARENT,
        recovery_identity_blob=M5_CORRECTION_PARENT_IDENTITY_BLOB,
    )
    _assert_one_manifest_append(
        _manifest(phase_anchor),
        _manifest(M5_CORRECTION_PARENT),
        "test_odlrq_quotient_generator.py",
    )
    assert (
        _git(
            "merge-base",
            "--is-ancestor",
            M5_CORRECTION_PARENT,
            head,
            check=False,
        ).returncode
        == 0
    )

    correction_additions = (
        _git(
            "log",
            "--diff-filter=A",
            "--format=%H",
            f"{M5_CORRECTION_PARENT}..{head}",
            "--",
            M5_CORRECTION_PATH,
        )
        .stdout.decode("ascii")
        .splitlines()
    )
    assert len(correction_additions) == 1
    correction_commit = correction_additions[0]
    assert _raw_parents(correction_commit) == [M5_CORRECTION_PARENT]
    assert _changed_paths(correction_commit) == M5_CORRECTION_PATHS
    assert (
        _tree_blob(correction_commit, M5_CORRECTION_PATH)
        == M5_CORRECTION_DOCUMENT_BLOB
    )
    correction_identity_blob = _tree_blob(correction_commit, IDENTITY_PATH)
    assert correction_identity_blob != M5_CORRECTION_PARENT_IDENTITY_BLOB
    _assert_m5_correction_base(
        correction_commit,
        correction_identity_blob=correction_identity_blob,
    )
    assert _manifest(correction_commit) == _manifest(M5_CORRECTION_PARENT)
    assert (
        _git(
            "merge-base",
            "--is-ancestor",
            correction_commit,
            head,
            check=False,
        ).returncode
        == 0
    )

    closeout_additions = (
        _git(
            "log",
            "--diff-filter=A",
            "--format=%H",
            f"{correction_commit}..{head}",
            "--",
            CLOSEOUT_PATH,
        )
        .stdout.decode("ascii")
        .splitlines()
    )
    assert len(closeout_additions) <= 1
    if closeout_additions:
        phase_head = closeout_additions[0]
        assert (
            _git(
                "merge-base",
                "--is-ancestor",
                phase_head,
                head,
                check=False,
            ).returncode
            == 0
        )
        closeout_blob = _tree_blob(phase_head, CLOSEOUT_PATH)
        assert _tree_blob(head, CLOSEOUT_PATH) == closeout_blob
    else:
        phase_head = head

    interval = (
        _git(
            "rev-list",
            "--first-parent",
            "--reverse",
            f"{correction_commit}..{phase_head}",
        )
        .stdout.decode("ascii")
        .splitlines()
    )
    lane_counts = [1, 0, 0]
    previous_lane = 0
    previous_commit = correction_commit
    closeout_seen = False

    for index, commit in enumerate(interval):
        assert _raw_parents(commit) == [previous_commit]
        _assert_m5_correction_base(
            commit, correction_identity_blob=correction_identity_blob
        )
        changed = _changed_paths(commit)
        assert changed

        if CLOSEOUT_PATH in changed:
            assert not closeout_seen
            assert changed == {CLOSEOUT_PATH}
            assert index == len(interval) - 1
            assert _manifest(commit) == _manifest(previous_commit)
            closeout_seen = True
            previous_commit = commit
            continue

        assert not closeout_seen
        matching_lanes = [
            lane_index
            for lane_index, (_name, _allowlist, markers, _test_name) in enumerate(LANES)
            if changed & markers
        ]
        assert len(matching_lanes) == 1
        lane_index = matching_lanes[0]
        assert lane_index in {1, 2}, "M4 is complete at the correction parent"
        _lane_name, allowlist, _markers, expected_test = LANES[lane_index]
        assert changed <= allowlist
        assert lane_index >= previous_lane
        lane_counts[lane_index] += 1
        assert lane_counts[lane_index] <= MAX_COMMITS_PER_LANE

        before_manifest = _manifest(previous_commit)
        after_manifest = _manifest(commit)
        if MANIFEST_PATH in changed:
            _assert_one_manifest_append(
                before_manifest, after_manifest, expected_test
            )
        else:
            assert after_manifest == before_manifest
        assert after_manifest.get(expected_test) == ["unit"]

        previous_lane = lane_index
        previous_commit = commit

    assert sum(lane_counts) <= len(LANES) * MAX_COMMITS_PER_LANE

    assert len(closeout_additions) == (1 if closeout_seen else 0)
