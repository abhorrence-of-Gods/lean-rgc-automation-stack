from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]

PARENT_COMMIT = "5bb86a43fbd05731dd7e5db25394995139854805"
AMENDMENT_PATH = (
    "docs/experiments/"
    "uprime_odlrq_kp3_d4_canonical_history_amendment_2026-07-12.md"
)
TASK_INPUT_PATH = (
    "docs/experiments/inputs/uprime_kp3_d4_fresh_tasks.json"
)
ACTION_INPUT_PATH = (
    "docs/experiments/inputs/uprime_kp3_d4_actions.json"
)
IDENTITY_PATH = "tests/test_odlrq_kp3_d4_identity.py"
MANIFEST_PATH = "tests/tier_manifest.json"
RESULT_PATH = (
    "docs/experiments/artifacts/"
    "uprime_kp3_d4_20260712/fresh_family_d4.json"
)
CLOSEOUT_PATH = (
    "docs/experiments/"
    "uprime_odlrq_kp3_d4_canonical_history_closeout_2026-07-12.md"
)

AMENDMENT_PATHS = {
    AMENDMENT_PATH,
    TASK_INPUT_PATH,
    ACTION_INPUT_PATH,
    IDENTITY_PATH,
    MANIFEST_PATH,
}

AMENDMENT_DOCUMENT_SHA256 = (
    "280E250E14F41D705A0C5BD2EBB0168C1B5907007285084CF8E2EA80DA02EF3E"
)
AMENDMENT_DOCUMENT_BLOB = "3a8ab712f0b32e85586d2e8608376cc3db3669b5"
TASK_INPUT_SHA256 = (
    "C0B5428DCB7174CB96F469E38E229043AF47B9E9ECF684797FF45EE8AE4163A0"
)
TASK_INPUT_CANONICAL_SHA256 = (
    "814BFBC235B6E464013637210E1C5382B0CED5AEB0C8D50C9C282E3236202D62"
)
TASK_PAYLOAD_CANONICAL_SHA256 = (
    "402410B252C71EFFF250437D9715ECA7A39F433BE056DF5D1997D9EB2FDECB95"
)
TASK_INPUT_BLOB = "9b5c999ebab9e039040498f972a4730f86e798e5"
ACTION_INPUT_SHA256 = (
    "FC9FB44E8E5D6929712CE15DC2D6F93FCCA74B81EE99C9EAF55D13B76A0CCF51"
)
ACTION_INPUT_CANONICAL_SHA256 = (
    "BE4AC0348631D0D7E3ABCA3DD22A05240E1D86B494B21FDBB47EF7FADA99FB1A"
)
ACTION_PAYLOAD_CANONICAL_SHA256 = (
    "8A203CD2C993ABECECEE860A071C75E4C81A5E9E1D87CA37F8E7CC5AEEC879DE"
)
ACTION_INPUT_BLOB = "b3a7cf0570b2aa322506649cd9df5985d4a4028d"

PARENT_MANIFEST_BLOB = "292cc7de29ea4891b1b5c1c0fdbc1346727fb9a8"
IMMUTABLE_PARENT_BLOBS = {
    (
        "docs/experiments/"
        "uprime_odlrq_lane_isolated_recovery_closeout_2026-07-12.md"
    ): "5061650434a1fb5dde29ff1b6dd1e48fdb117182",
    "tests/test_odlrq_lane_isolated_recovery_identity.py": (
        "27f103c258b004a3e45bc33b5234303c675b64c7"
    ),
    "tests/test_uprime_u05_identity.py": (
        "277f46ec0e4cecfe6ae3d119adb85c2b3a043182"
    ),
    "lean_rgc/odlrq/contracts.py": (
        "eca7d55bc7c2a7a08fbdc75c3b589f1972cd258f"
    ),
    "lean_rgc/odlrq/rule_algebra.py": (
        "1deff84c42168c65c5fa1ef953cd51f5b772502e"
    ),
    "lean_rgc/odlrq/reachable_chart.py": (
        "67204f31f03d228362132e5892ecb7c2832434f1"
    ),
    "lean_rgc/odlrq/hankel.py": (
        "c724d1a31257ba7f63f55a2af6ae8c4acbbda387"
    ),
    "lean_rgc/lean/kernel_state_identity.py": (
        "f9924024609d1ffd2ad60fe296b8bb9173dcd40d"
    ),
    "lean_rgc/lean/kernel_rpc_client.py": (
        "ef5d81bff4c6ab4d8110fe6671f5e5b5f8bc263a"
    ),
    "lean_rgc/native_lean/RGCKernelRPC.lean": (
        "305509d9b89081a3d002734e09724b98e244a24c"
    ),
    (
        "docs/experiments/artifacts/"
        "uprime_u05_20260711/u05_kill_probes.json"
    ): "33061cffae56abf4ed2a4fcdb9400eb2004e61c6",
    "lean_rgc/evals/uprime_u05_kill_probes.py": (
        "d47f99f90ff4cfb1332fde3de90c734fd8e876ed"
    ),
}

C1_ALLOWLIST = {
    "lean_rgc/odlrq/__init__.py",
    "lean_rgc/odlrq/history_normal_form.py",
    "lean_rgc/odlrq/hankel_depth4.py",
    "tests/test_odlrq_history_normal_form.py",
    "tests/test_odlrq_hankel_depth4.py",
    "tools/run_uprime_kp3_d4_history_tests.ps1",
    MANIFEST_PATH,
}
C2_ALLOWLIST = {
    "lean_rgc/evals/uprime_kp3_d4_canonical_history.py",
    "tests/test_uprime_kp3_d4_canonical_history.py",
    "tools/run_uprime_kp3_d4_native_tests.ps1",
    "tools/run_uprime_kp3_d4_fresh_execution.ps1",
    MANIFEST_PATH,
}
C1_MANIFEST_ROWS = {
    "test_odlrq_history_normal_form.py": ["unit"],
    "test_odlrq_hankel_depth4.py": ["unit"],
}
C2_MANIFEST_ROWS = {
    "test_uprime_kp3_d4_canonical_history.py": ["unit"],
}
MAX_COMMITS_PER_WORK_PACKAGE = 2

OLD_TASK_IDS = {
    "u05_identity",
    "u05_pair",
    "u05_split",
    "u05_nested_split",
    "u05_nat_zero",
}


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


def _worktree_blob(path: str) -> str:
    return _git("hash-object", "--", path).stdout.decode("ascii").strip()


def _index_blob(path: str) -> str:
    rows = (
        _git("ls-files", "--stage", "--", path)
        .stdout.decode("utf-8")
        .splitlines()
    )
    assert len(rows) == 1
    return rows[0].split(maxsplit=3)[1]


def _assert_manifest_append(
    before: dict[str, Any],
    after: dict[str, Any],
    expected: dict[str, list[str]],
) -> None:
    assert set(after) - set(before) == set(expected)
    assert set(before) <= set(after)
    for name, tiers in before.items():
        assert after[name] == tiers
    for name, tiers in expected.items():
        assert after[name] == tiers


def _assert_parent_blobs(revision: str) -> None:
    for path, expected in IMMUTABLE_PARENT_BLOBS.items():
        assert _tree_blob(revision, path) == expected


def _assert_a0_base(revision: str, *, identity_blob: str) -> None:
    _assert_parent_blobs(revision)
    assert _tree_blob(revision, AMENDMENT_PATH) == AMENDMENT_DOCUMENT_BLOB
    assert _tree_blob(revision, TASK_INPUT_PATH) == TASK_INPUT_BLOB
    assert _tree_blob(revision, ACTION_INPUT_PATH) == ACTION_INPUT_BLOB
    assert _tree_blob(revision, IDENTITY_PATH) == identity_blob


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


def _strict_json(raw: bytes) -> Any:
    def reject_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def reject_constant(value: str) -> Any:
        raise ValueError(f"non-finite JSON constant: {value}")

    return json.loads(
        raw.decode("utf-8", errors="strict"),
        object_pairs_hook=reject_pairs,
        parse_constant=reject_constant,
    )


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def test_kp3_d4_registered_inputs_and_plan_bytes_are_frozen() -> None:
    document = (REPO_ROOT / AMENDMENT_PATH).read_bytes()
    assert _sha256(document) == AMENDMENT_DOCUMENT_SHA256
    text = document.decode("utf-8", errors="strict")
    for literal in (
        "CONDITIONAL_KSTATE_MARKOV",
        "RUN_OPENED",
        "862,715",
        "same-family RPC rerun",
        "NOT_ATTEMPTED_IN_THIS_PHASE",
        TASK_INPUT_SHA256,
        ACTION_INPUT_SHA256,
    ):
        assert literal in text

    task_raw = (REPO_ROOT / TASK_INPUT_PATH).read_bytes()
    action_raw = (REPO_ROOT / ACTION_INPUT_PATH).read_bytes()
    assert _sha256(task_raw) == TASK_INPUT_SHA256
    assert _sha256(action_raw) == ACTION_INPUT_SHA256
    tasks_wrapper = _strict_json(task_raw)
    actions_wrapper = _strict_json(action_raw)
    assert type(tasks_wrapper) is dict and set(tasks_wrapper) == {"schema", "tasks"}
    assert type(actions_wrapper) is dict and set(actions_wrapper) == {
        "schema",
        "actions",
    }
    assert _sha256(_canonical_bytes(tasks_wrapper)) == TASK_INPUT_CANONICAL_SHA256
    assert _sha256(_canonical_bytes(actions_wrapper)) == ACTION_INPUT_CANONICAL_SHA256
    assert _sha256(_canonical_bytes(tasks_wrapper["tasks"])) == (
        TASK_PAYLOAD_CANONICAL_SHA256
    )
    assert _sha256(_canonical_bytes(actions_wrapper["actions"])) == (
        ACTION_PAYLOAD_CANONICAL_SHA256
    )
    tasks = tasks_wrapper["tasks"]
    actions = actions_wrapper["actions"]
    assert type(tasks) is list and len(tasks) == 5
    assert type(actions) is list and len(actions) == 12
    task_ids = [row["task_id"] for row in tasks]
    action_ids = [row["action_id"] for row in actions]
    assert len(task_ids) == len(set(task_ids))
    assert len(action_ids) == len(set(action_ids))
    assert not OLD_TASK_IDS.intersection(task_ids)
    assert action_ids == sorted(action_ids)
    assert 5 * sum(12**depth for depth in range(4)) == 9_425
    assert 5 * sum(12**depth for depth in range(5)) == 113_105
    assert (5 * (1 + 12 + 12**2)) * (7 * (1 + 12 + 12**2)) == 862_715


def test_kp3_d4_anchor_topology_and_phase_files_are_immutable() -> None:
    assert (
        _git("rev-parse", "--is-shallow-repository")
        .stdout.decode("ascii")
        .strip()
        == "false"
    ), "KP3 D4 governance requires complete Git history"
    head = _head()

    if head == PARENT_COMMIT:
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

        staged_paths = set(
            _git(
                "diff",
                "--cached",
                "--name-only",
                "--no-renames",
                "--",
                *sorted(AMENDMENT_PATHS),
            )
            .stdout.decode("utf-8")
            .splitlines()
        )
        if staged_paths:
            # A pre-commit test must inspect the bytes that will actually be
            # committed.  Reject a partial index and an index/worktree split;
            # both would let green worktree tests bless different A0 bytes.
            assert staged_paths == AMENDMENT_PATHS
            for path in AMENDMENT_PATHS:
                assert _index_blob(path) == _worktree_blob(path)
        assert (
            _git("hash-object", AMENDMENT_PATH).stdout.decode("ascii").strip()
            == AMENDMENT_DOCUMENT_BLOB
        )
        assert (
            _git("hash-object", TASK_INPUT_PATH).stdout.decode("ascii").strip()
            == TASK_INPUT_BLOB
        )
        assert (
            _git("hash-object", ACTION_INPUT_PATH).stdout.decode("ascii").strip()
            == ACTION_INPUT_BLOB
        )
        _assert_parent_blobs("HEAD")
        assert _tree_blob("HEAD", MANIFEST_PATH) == PARENT_MANIFEST_BLOB
        _assert_manifest_append(
            _manifest("HEAD"),
            _worktree_manifest(),
            {"test_odlrq_kp3_d4_identity.py": ["unit"]},
        )
        return

    amendment_additions = (
        _git(
            "log",
            "--diff-filter=A",
            "--format=%H",
            f"{PARENT_COMMIT}..{head}",
            "--",
            AMENDMENT_PATH,
        )
        .stdout.decode("ascii")
        .splitlines()
    )
    assert len(amendment_additions) == 1
    amendment_commit = amendment_additions[0]
    assert _raw_parents(amendment_commit) == [PARENT_COMMIT]
    assert _changed_paths(amendment_commit) == AMENDMENT_PATHS
    amendment_identity_blob = _tree_blob(amendment_commit, IDENTITY_PATH)
    _assert_a0_base(amendment_commit, identity_blob=amendment_identity_blob)
    assert _tree_blob(PARENT_COMMIT, MANIFEST_PATH) == PARENT_MANIFEST_BLOB
    _assert_manifest_append(
        _manifest(PARENT_COMMIT),
        _manifest(amendment_commit),
        {"test_odlrq_kp3_d4_identity.py": ["unit"]},
    )
    assert (
        _git(
            "merge-base",
            "--is-ancestor",
            amendment_commit,
            head,
            check=False,
        ).returncode
        == 0
    )
    # Preserve the A0 guard, inputs, plan, and inherited substrate even after
    # the phase closeout permits later amendments to add unrelated paths.
    _assert_a0_base(head, identity_blob=amendment_identity_blob)

    closeout_additions = (
        _git(
            "log",
            "--diff-filter=A",
            "--format=%H",
            f"{amendment_commit}..{head}",
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
    else:
        phase_head = head

    interval = (
        _git(
            "rev-list",
            "--first-parent",
            "--reverse",
            f"{amendment_commit}..{phase_head}",
        )
        .stdout.decode("ascii")
        .splitlines()
    )
    counts = [0, 0]
    previous_commit = amendment_commit
    previous_lane = 0
    result_seen = False
    closeout_seen = False
    result_commit: str | None = None

    for index, commit in enumerate(interval):
        assert _raw_parents(commit) == [previous_commit]
        _assert_a0_base(commit, identity_blob=amendment_identity_blob)
        changed = _changed_paths(commit)
        assert changed

        if changed == {RESULT_PATH}:
            assert counts[0] >= 1 and counts[1] >= 1
            assert not result_seen and not closeout_seen
            assert _manifest(commit) == _manifest(previous_commit)
            result_seen = True
            result_commit = commit
            previous_commit = commit
            continue

        if CLOSEOUT_PATH in changed:
            assert changed == {CLOSEOUT_PATH}
            assert counts[0] >= 1 and counts[1] >= 1
            assert not closeout_seen
            assert index == len(interval) - 1
            assert _manifest(commit) == _manifest(previous_commit)
            closeout_seen = True
            previous_commit = commit
            continue

        assert not result_seen and not closeout_seen
        lane_matches = []
        for lane_index, allowlist in enumerate((C1_ALLOWLIST, C2_ALLOWLIST)):
            if changed & (allowlist - {MANIFEST_PATH}):
                lane_matches.append(lane_index)
        assert len(lane_matches) == 1
        lane_index = lane_matches[0]
        assert lane_index >= previous_lane
        if lane_index == 1:
            assert counts[0] >= 1, "C2 cannot begin before an accepted C1 commit"
        allowlist = (C1_ALLOWLIST, C2_ALLOWLIST)[lane_index]
        expected_rows = (C1_MANIFEST_ROWS, C2_MANIFEST_ROWS)[lane_index]
        assert changed <= allowlist

        if counts[lane_index] == 0:
            assert changed == allowlist
            _assert_manifest_append(
                _manifest(previous_commit),
                _manifest(commit),
                expected_rows,
            )
        else:
            assert MANIFEST_PATH not in changed
            assert _manifest(commit) == _manifest(previous_commit)
        counts[lane_index] += 1
        assert counts[lane_index] <= MAX_COMMITS_PER_WORK_PACKAGE
        previous_lane = lane_index
        previous_commit = commit

    assert len(closeout_additions) == (1 if closeout_seen else 0)
    if closeout_seen:
        closeout_blob = _tree_blob(phase_head, CLOSEOUT_PATH)
        assert _tree_blob(head, CLOSEOUT_PATH) == closeout_blob
    if result_seen:
        assert result_commit is not None
        result_blob = _tree_blob(result_commit, RESULT_PATH)
        assert _tree_blob(head, RESULT_PATH) == result_blob
    elif closeout_seen:
        result_probe = _git("cat-file", "-e", f"{head}:{RESULT_PATH}", check=False)
        assert result_probe.returncode != 0
