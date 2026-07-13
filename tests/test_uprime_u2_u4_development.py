from __future__ import annotations

import copy
import inspect
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any, Mapping

import pytest

import uprime_u24_guard as u24_guard

REPO_ROOT = Path(__file__).resolve().parents[1]

ANCHOR_COMMIT = "1d448a2322b639b462d8cda8d20b4aaa55be232f"
ANCHOR_PARENT = "48c9127b0cc6122af203869c656a78b9f2160293"
ANCHOR_TREE = "4442cff7b0c84fd5d24dd4d68020f5afade9cd12"
ANCHOR_FAILURE_PATH = (
    "docs/experiments/"
    "uprime_odlrq_u2_u4_development_reconstruction_failure_closeout_2026-07-13.md"
)
ANCHOR_FAILURE_BLOB = "8c1a048249b9ac2ddb0fa1ebc74eeac03fdd0692"
ANCHOR_IDENTITY_BLOB = "b4e67b08c1d6695c90850317740b10dd9a6001b4"
ANCHOR_GUARD_BLOB = "b877884528bc917c4cbeca48bd55223fe890f9e4"
ANCHOR_RUNNER_BLOB = "61773201f5128d64dd9d17916f66c835569bf329"
ANCHOR_MANIFEST_BLOB = "47997a9bd67f7ac2cf0cd9c7f654d8f069f925d8"
ANCHOR_WORKFLOW_BLOB = "0349e9ca864b7e9e25064ab7fab5b6dc0665adee"

LEGACY_A1_COMMIT = "7377119962e07c9062ba46c2c0c2f0eb479060ef"
LEGACY_A1_DOCUMENT_PATH = (
    "docs/experiments/"
    "uprime_odlrq_u2_u4_development_reconstruction_amendment_2026-07-13.md"
)
LEGACY_A1_DOCUMENT_BLOB = "77263bc28d74c698f616717dc147c58e8995d1bd"
LEGACY_SUCCESS_CLOSEOUT_PATH = (
    "docs/experiments/"
    "uprime_odlrq_u2_u4_development_reconstruction_closeout_2026-07-13.md"
)
HISTORICAL_IDENTITY_ADDITION = "7083e766acd2ba09b45ba3f47f65dc0b34317bd3"

A2_COMMIT = "7c05c494ce79e84ffeb0d0c912ca3ba5f141f402"
A2_DOCUMENT_PATH = (
    "docs/experiments/"
    "uprime_odlrq_u2_u4_development_r2_exact_admission_integration_amendment_2026-07-13.md"
)
A2_DOCUMENT_BLOB = "a6fb65eb7a3d52bfbae985eb6bf32bf5275ac3e1"
BOOTSTRAP_DOCUMENT_PATH = (
    "docs/experiments/"
    "uprime_odlrq_u2_u4_development_r2_topology_bootstrap_amendment_2026-07-13.md"
)
BOOTSTRAP_DOCUMENT_BLOB = "c5af0cc08a1a6e148d297f9bf06300ba169987eb"

ACCEPTED_FAILURE_COMMIT = "214dec3adb7841452fea19f7ae668d8e0f7520a1"
ACCEPTED_FAILURE_PATH = (
    "docs/experiments/"
    "uprime_odlrq_u2_u4_development_failure_closeout_2026-07-13.md"
)
ACCEPTED_FAILURE_BLOB = "cc30890bca5b86512997a17d4bcffc4792197d7e"
ORIGINAL_AUTHORITY_COMMIT = "14234e209229931c00615d4b171620ec6d1bbbf5"
ORIGINAL_AUTHORITY_PARENT = "78c12549eb188610977842edbc38e2723d469ba4"
ORIGINAL_AUTHORITY_PATH = (
    "docs/experiments/"
    "uprime_odlrq_u2_u4_development_construction_bundle_amendment_2026-07-13.md"
)
ORIGINAL_AUTHORITY_BLOB = "bd3ef021dff5cb5e3a28c1d2a79b0379e5615835"
REJECTED_BUILD_COMMITS = {
    "3e6331a6b1bbcca3ca3acfea02daeb0c8de62406",
    "7ca946ef6c23cf0855cd3942eecbe20663f70e21",
}

IDENTITY_PATH = "tests/test_uprime_u2_u4_development.py"
GUARD_PATH = "tests/uprime_u24_guard.py"
RUNNER_PATH = "tools/run_uprime_u2_u4_development_tests.ps1"
MANIFEST_PATH = "tests/tier_manifest.json"
WORKFLOW_PATH = ".github/workflows/ci.yml"
SUCCESS_CLOSEOUT_PATH = (
    "docs/experiments/"
    "uprime_odlrq_u2_u4_development_r2_closeout_2026-07-13.md"
)
FAILURE_CLOSEOUT_PATH = (
    "docs/experiments/"
    "uprime_odlrq_u2_u4_development_r2_failure_closeout_2026-07-13.md"
)

FROZEN_REFS = {
    "A2": "codex/uprime-u2-u4-development-r2-a0",
    "T0": "codex/uprime-u2-u4-development-r2-topology-bootstrap",
    "build": "codex/uprime-u2-u4-development-r2-build",
    "closeout": "codex/uprime-u2-u4-development-r2-closeout",
    "failure": "codex/uprime-u2-u4-development-r2-failure-closeout",
    "accepted": "codex/uprime-odlrq-plan",
}
STAGE_ORDER = ("E0", "E1", "E2", "ME0", "S0", "I0")
MAX_BUILD_COMMITS = 7
MAX_CORRECTIONS = 1
WALL_SECONDS = {
    "B0": 60,
    "E0": 60,
    "E1": 120,
    "E2": 180,
    "ME0": 180,
    "S0": 300,
    "I0": 900,
    "EMIT": 900,
    "CLOSEOUT": 60,
}

BOOTSTRAP_CONTROL_PATHS = {
    IDENTITY_PATH,
    GUARD_PATH,
    RUNNER_PATH,
}
BOOTSTRAP_PATHS = {BOOTSTRAP_DOCUMENT_PATH, *BOOTSTRAP_CONTROL_PATHS}
BASE_BLOBS = {
    "lean_rgc/odlrq/contracts.py":
        "eca7d55bc7c2a7a08fbdc75c3b589f1972cd258f",
    "lean_rgc/odlrq/quotient_generator.py":
        "e8d95082d2e47f0829d960321cc1d62bc686d7ac",
    "lean_rgc/odlrq/__init__.py":
        "866df99205f5073335ea7304b0cc160ab657e8f5",
    "tests/test_odlrq_quotient_generator.py":
        "d014b0c9555ac5932827d86b6b92420849ed4973",
    MANIFEST_PATH: ANCHOR_MANIFEST_BLOB,
}
ANCHOR_CONTROL_BLOBS = {
    IDENTITY_PATH: ANCHOR_IDENTITY_BLOB,
    GUARD_PATH: ANCHOR_GUARD_BLOB,
    RUNNER_PATH: ANCHOR_RUNNER_BLOB,
    WORKFLOW_PATH: ANCHOR_WORKFLOW_BLOB,
}
AUTHORITY_BLOBS = {
    ORIGINAL_AUTHORITY_PATH: ORIGINAL_AUTHORITY_BLOB,
    ACCEPTED_FAILURE_PATH: ACCEPTED_FAILURE_BLOB,
    (
        "docs/experiments/"
        "uprime_odlrq_upper_stack_implementation_plan_and_u05_amendment_2026-07-11.md"
    ): "2b2355f49aef149c1a7b5493951fa10e4a254235",
    (
        "docs/experiments/"
        "uprime_odlrq_lane_isolated_recovery_closeout_2026-07-12.md"
    ): "5061650434a1fb5dde29ff1b6dd1e48fdb117182",
    (
        "docs/experiments/"
        "uprime_odlrq_kp3_d4_canonical_history_closeout_2026-07-12.md"
    ): "7205667906d2b7a7baaff8a41d68b813839cbecb",
    (
        "docs/experiments/"
        "uprime_odlrq_official_transport_v2_recovery_failure_closeout_2026-07-13.md"
    ): "d94d9890f0c0bdf90f1e47bf49f779c5fbb31928",
    LEGACY_A1_DOCUMENT_PATH: LEGACY_A1_DOCUMENT_BLOB,
    ANCHOR_FAILURE_PATH: ANCHOR_FAILURE_BLOB,
}

STAGE_ALLOWLISTS = {
    "E0": {
        "lean_rgc/odlrq/quotient_generator.py",
        "lean_rgc/odlrq/__init__.py",
        "tests/test_odlrq_quotient_generator.py",
    },
    "E1": {
        "lean_rgc/odlrq/quotient_generator.py",
        "lean_rgc/odlrq/envelope.py",
        "lean_rgc/odlrq/__init__.py",
        "tests/test_odlrq_quotient_generator.py",
        "tests/test_odlrq_envelope.py",
        MANIFEST_PATH,
    },
    "E2": {
        "lean_rgc/odlrq/envelope.py",
        "lean_rgc/odlrq/selection.py",
        "lean_rgc/odlrq/certificates.py",
        "lean_rgc/odlrq/__init__.py",
        "tests/test_odlrq_envelope.py",
        "tests/test_odlrq_selection.py",
        MANIFEST_PATH,
    },
    "ME0": {
        "lean_rgc/odlrq/maxent.py",
        "lean_rgc/odlrq/__init__.py",
        "tests/test_odlrq_maxent.py",
        MANIFEST_PATH,
    },
    "S0": {
        "lean_rgc/odlrq/similarity.py",
        "lean_rgc/odlrq/__init__.py",
        "tests/test_odlrq_similarity.py",
        MANIFEST_PATH,
    },
    "I0": {
        "lean_rgc/odlrq/certificates.py",
        "lean_rgc/odlrq/__init__.py",
        "lean_rgc/evals/uprime_u2_u4_development.py",
        IDENTITY_PATH,
        RUNNER_PATH,
        MANIFEST_PATH,
    },
}
STAGE_MARKERS = {
    "E0": {"lean_rgc/odlrq/quotient_generator.py"},
    "E1": {"lean_rgc/odlrq/envelope.py"},
    "E2": {"lean_rgc/odlrq/selection.py"},
    "ME0": {"lean_rgc/odlrq/maxent.py"},
    "S0": {"lean_rgc/odlrq/similarity.py"},
    "I0": {"lean_rgc/evals/uprime_u2_u4_development.py"},
}
STAGE_MANIFEST_NODES = {
    "E0": set(),
    "E1": {"test_odlrq_envelope.py"},
    "E2": {"test_odlrq_selection.py"},
    "ME0": {"test_odlrq_maxent.py"},
    "S0": {"test_odlrq_similarity.py"},
    "I0": set(),
}

ABSENT_AT_ANCHOR = tuple(
    sorted(
        {
            A2_DOCUMENT_PATH,
            BOOTSTRAP_DOCUMENT_PATH,
            SUCCESS_CLOSEOUT_PATH,
            FAILURE_CLOSEOUT_PATH,
            "lean_rgc/odlrq/envelope.py",
            "lean_rgc/odlrq/maxent.py",
            "lean_rgc/odlrq/similarity.py",
            "lean_rgc/odlrq/selection.py",
            "lean_rgc/odlrq/certificates.py",
            "lean_rgc/evals/uprime_u2_u4_development.py",
            "tests/test_odlrq_envelope.py",
            "tests/test_odlrq_maxent.py",
            "tests/test_odlrq_similarity.py",
            "tests/test_odlrq_selection.py",
        }
    )
)

UNION_ALLOWLIST = frozenset(u24_guard.UNION_SOURCE_PATHS)
EXPECTED_UNION_ALLOWLIST = frozenset(
    {
        "lean_rgc/odlrq/contracts.py",
        "lean_rgc/odlrq/quotient_generator.py",
        "lean_rgc/odlrq/envelope.py",
        "lean_rgc/odlrq/maxent.py",
        "lean_rgc/odlrq/similarity.py",
        "lean_rgc/odlrq/selection.py",
        "lean_rgc/odlrq/certificates.py",
        "lean_rgc/odlrq/__init__.py",
        "lean_rgc/evals/uprime_u2_u4_development.py",
        "tests/test_odlrq_quotient_generator.py",
        "tests/test_odlrq_envelope.py",
        "tests/test_odlrq_maxent.py",
        "tests/test_odlrq_similarity.py",
        "tests/test_odlrq_selection.py",
        IDENTITY_PATH,
        GUARD_PATH,
        RUNNER_PATH,
        MANIFEST_PATH,
        WORKFLOW_PATH,
    }
)

SUCCESS_ARTIFACT_PATHS = set(u24_guard.CLOSEOUT_ARTIFACTS)
SUCCESS_TERMINAL_PATHS = {SUCCESS_CLOSEOUT_PATH, *SUCCESS_ARTIFACT_PATHS}
FAILURE_TERMINAL_PATHS = {FAILURE_CLOSEOUT_PATH}

TRACKED_PATHS = tuple(
    sorted(
        {
            A2_DOCUMENT_PATH,
            BOOTSTRAP_DOCUMENT_PATH,
            LEGACY_SUCCESS_CLOSEOUT_PATH,
            *BASE_BLOBS,
            *AUTHORITY_BLOBS,
            *UNION_ALLOWLIST,
            SUCCESS_CLOSEOUT_PATH,
            FAILURE_CLOSEOUT_PATH,
            *SUCCESS_ARTIFACT_PATHS,
        }
    )
)

# This snapshot is collected before the autouse semantic guard is installed.
# The registered runner supplies the same canonical object from its outer
# read-only control plane; direct CI constructs it locally before test setup.
CONTROL = u24_guard.load_control_plane_attestation(
    REPO_ROOT,
    a0_commit=ANCHOR_COMMIT,
    identity_path=IDENTITY_PATH,
    tracked_paths=TRACKED_PATHS,
    absent_at_a0=ABSENT_AT_ANCHOR,
)


@pytest.fixture(autouse=True)
def _u24_identity_semantic_guard():
    policy = u24_guard.GuardPolicy(u24_guard.GuardMode.SEMANTIC, REPO_ROOT)
    if os.environ.get(u24_guard.PREINSTALLED_GUARD_ENV) == "1":
        u24_guard.require_active_guard(policy)
        yield
        return
    with u24_guard.install_guard(policy):
        yield


def _revision_rows(
    control: Mapping[str, Any] = CONTROL,
) -> list[dict[str, Any]]:
    rows = control["revisions"]
    assert type(rows) is list
    assert all(type(row) is dict for row in rows)
    return rows


def _revision(
    commit: str,
    control: Mapping[str, Any] = CONTROL,
) -> dict[str, Any]:
    matches = [row for row in _revision_rows(control) if row.get("commit") == commit]
    assert len(matches) == 1
    return matches[0]


def _changed(row: Mapping[str, Any]) -> set[str]:
    value = row["changed_paths"]
    assert type(value) is list and all(type(path) is str for path in value)
    return set(value)


def _blobs(row: Mapping[str, Any]) -> dict[str, str | None]:
    value = row["tree_blobs"]
    assert type(value) is dict
    assert set(value) == set(TRACKED_PATHS)
    assert all(blob is None or type(blob) is str for blob in value.values())
    return value


def _worktree_blobs(control: Mapping[str, Any]) -> dict[str, str | None]:
    value = control["worktree_blobs"]
    assert type(value) is dict and set(value) == set(TRACKED_PATHS)
    assert all(blob is None or type(blob) is str for blob in value.values())
    return value


def _governed_dirty(control: Mapping[str, Any]) -> set[str]:
    return set(
        u24_guard.governed_status_paths(
            control["status_paths"], control["ci_setup_paths"]
        )
    )


def _assert_tree_transition(
    previous: Mapping[str, Any], current: Mapping[str, Any]
) -> None:
    changed = _changed(current)
    before = _blobs(previous)
    after = _blobs(current)
    for path in TRACKED_PATHS:
        if path not in changed:
            assert after[path] == before[path]


def _classify_build_rows(
    rows: list[dict[str, Any]], *, correction_used: int = 0
) -> tuple[list[str], dict[str, int], int]:
    completed: list[str] = []
    counts = {name: 0 for name in STAGE_ORDER}
    next_stage_index = 0
    last_stage: str | None = None
    corrections = correction_used

    for row in rows:
        changed = _changed(row)
        assert changed
        candidate = (
            STAGE_ORDER[next_stage_index]
            if next_stage_index < len(STAGE_ORDER)
            else None
        )
        if (
            candidate is not None
            and changed <= STAGE_ALLOWLISTS[candidate]
            and bool(changed & STAGE_MARKERS[candidate])
        ):
            completed.append(candidate)
            counts[candidate] = 1
            next_stage_index += 1
            last_stage = candidate
            continue

        assert last_stage is not None
        assert changed <= STAGE_ALLOWLISTS[last_stage]
        assert counts[last_stage] == 1
        counts[last_stage] = 2
        corrections += 1
        assert corrections <= MAX_CORRECTIONS

    return completed, counts, corrections


def _validate_epoch_topology(control: Mapping[str, Any]) -> dict[str, Any]:
    assert set(control) == {
        "schema_version",
        "head",
        "is_shallow",
        "status_paths",
        "ci_setup_paths",
        "identity_additions",
        "first_parent_after_a0",
        "revisions",
        "worktree_blobs",
        "absent_at_a0",
        "a0_manifest",
    }
    assert control["schema_version"] == u24_guard.CONTROL_ATTESTATION_SCHEMA
    assert control["is_shallow"] is False
    assert control["identity_additions"] == [HISTORICAL_IDENTITY_ADDITION]
    assert control["absent_at_a0"] == {
        path: True for path in ABSENT_AT_ANCHOR
    }
    assert type(control["a0_manifest"]) is dict
    assert control["ci_setup_paths"] in ([], list(u24_guard.CI_SETUP_PATHS))
    assert set(control["ci_setup_paths"]) <= set(control["status_paths"])

    interval = control["first_parent_after_a0"]
    assert type(interval) is list and all(type(item) is str for item in interval)
    assert len(interval) == len(set(interval))
    revisions = _revision_rows(control)
    commits = [row.get("commit") for row in revisions]
    assert commits == [ANCHOR_COMMIT, *interval]
    assert len(commits) == len(set(commits))
    assert control["head"] == (interval[-1] if interval else ANCHOR_COMMIT)
    assert interval and interval[0] == A2_COMMIT

    anchor = revisions[0]
    assert anchor["parents"] == [ANCHOR_PARENT]
    assert _changed(anchor) == {ANCHOR_FAILURE_PATH}
    anchor_blobs = _blobs(anchor)
    assert anchor_blobs[ANCHOR_FAILURE_PATH] == ANCHOR_FAILURE_BLOB
    for path, expected in {
        **BASE_BLOBS,
        **ANCHOR_CONTROL_BLOBS,
        **AUTHORITY_BLOBS,
    }.items():
        assert anchor_blobs[path] == expected

    a2 = revisions[1]
    assert a2["commit"] == A2_COMMIT
    assert a2["parents"] == [ANCHOR_COMMIT]
    assert _changed(a2) == {A2_DOCUMENT_PATH}
    _assert_tree_transition(anchor, a2)
    a2_blobs = _blobs(a2)
    assert a2_blobs[A2_DOCUMENT_PATH] == A2_DOCUMENT_BLOB
    assert a2_blobs[BOOTSTRAP_DOCUMENT_PATH] is None
    for path, expected in {
        **BASE_BLOBS,
        **ANCHOR_CONTROL_BLOBS,
        **AUTHORITY_BLOBS,
    }.items():
        assert a2_blobs[path] == expected

    for previous, current in zip(revisions, revisions[1:]):
        assert current["parents"] == [previous["commit"]]
        _assert_tree_transition(previous, current)

    worktree = _worktree_blobs(control)
    dirty = _governed_dirty(control)
    head_blobs = _blobs(revisions[-1])
    for path in TRACKED_PATHS:
        if path not in dirty:
            assert worktree[path] == head_blobs[path]

    if len(interval) == 1:
        assert control["head"] == A2_COMMIT
        assert dirty == BOOTSTRAP_PATHS
        assert worktree[BOOTSTRAP_DOCUMENT_PATH] == BOOTSTRAP_DOCUMENT_BLOB
        assert all(worktree[path] is not None for path in BOOTSTRAP_PATHS)
        return {
            "completed": [],
            "counts": {name: 0 for name in STAGE_ORDER},
            "corrections": 0,
            "pending": "T0",
            "terminal": None,
        }

    t0 = revisions[2]
    assert t0["parents"] == [A2_COMMIT]
    assert _changed(t0) == BOOTSTRAP_PATHS
    t0_blobs = _blobs(t0)
    assert t0_blobs[BOOTSTRAP_DOCUMENT_PATH] == BOOTSTRAP_DOCUMENT_BLOB
    for path in BOOTSTRAP_CONTROL_PATHS:
        assert t0_blobs[path] is not None
        assert t0_blobs[path] != ANCHOR_CONTROL_BLOBS[path]
    for path, expected in {**BASE_BLOBS, **AUTHORITY_BLOBS}.items():
        assert t0_blobs[path] == expected
    assert t0_blobs[WORKFLOW_PATH] == ANCHOR_WORKFLOW_BLOB

    remaining = revisions[3:]
    corrections = 0
    frozen_control_row = t0
    if remaining and _changed(remaining[0]) <= BOOTSTRAP_CONTROL_PATHS:
        assert _changed(remaining[0])
        frozen_control_row = remaining.pop(0)
        corrections = 1

    terminal = None
    if remaining and _changed(remaining[-1]) in (
        SUCCESS_TERMINAL_PATHS,
        FAILURE_TERMINAL_PATHS,
    ):
        terminal = remaining.pop()
    assert all(
        _changed(row) not in (SUCCESS_TERMINAL_PATHS, FAILURE_TERMINAL_PATHS)
        for row in remaining
    )
    assert len(remaining) <= len(STAGE_ORDER) + MAX_CORRECTIONS - corrections
    assert len(remaining) <= MAX_BUILD_COMMITS
    completed, counts, corrections = _classify_build_rows(
        remaining, correction_used=corrections
    )
    assert corrections <= MAX_CORRECTIONS

    frozen_blobs = _blobs(frozen_control_row)
    for row in [*remaining, *((terminal,) if terminal is not None else ())]:
        blobs = _blobs(row)
        for path in (GUARD_PATH, RUNNER_PATH, WORKFLOW_PATH):
            assert blobs[path] == frozen_blobs[path]
        assert blobs[A2_DOCUMENT_PATH] == A2_DOCUMENT_BLOB
        assert blobs[BOOTSTRAP_DOCUMENT_PATH] == BOOTSTRAP_DOCUMENT_BLOB
        for path, expected in AUTHORITY_BLOBS.items():
            assert blobs[path] == expected

    pending: str | None = None
    if terminal is not None:
        assert not dirty
        if _changed(terminal) == SUCCESS_TERMINAL_PATHS:
            assert completed == list(STAGE_ORDER)
    elif dirty:
        if (
            corrections == 0
            and not remaining
            and dirty <= BOOTSTRAP_CONTROL_PATHS
            and bool(dirty)
        ):
            pending = "T0-correction"
        else:
            assert not dirty & {GUARD_PATH, RUNNER_PATH, WORKFLOW_PATH}
            next_stage = (
                STAGE_ORDER[len(completed)]
                if len(completed) < len(STAGE_ORDER)
                else None
            )
            if (
                next_stage is not None
                and dirty <= STAGE_ALLOWLISTS[next_stage]
                and bool(dirty & STAGE_MARKERS[next_stage])
            ):
                pending = next_stage
            else:
                assert corrections == 0 and completed
                assert dirty <= STAGE_ALLOWLISTS[completed[-1]]
                assert bool(dirty)
                pending = completed[-1] + "-correction"

    return {
        "completed": completed,
        "counts": counts,
        "corrections": corrections,
        "pending": pending,
        "terminal": terminal,
    }


def _worktree_manifest() -> dict[str, list[str]]:
    value = json.loads((REPO_ROOT / MANIFEST_PATH).read_text(encoding="utf-8"))
    assert type(value) is dict
    return value


def test_u24_a0_anchor_authorities_and_nonexistence_are_frozen() -> None:
    assert set(CONTROL) == {
        "schema_version",
        "head",
        "is_shallow",
        "status_paths",
        "ci_setup_paths",
        "identity_additions",
        "first_parent_after_a0",
        "revisions",
        "worktree_blobs",
        "absent_at_a0",
        "a0_manifest",
    }
    assert CONTROL["schema_version"] == u24_guard.CONTROL_ATTESTATION_SCHEMA
    assert u24_guard.CONTROL_ATTESTATION_SCHEMA == "u24-control-plane-attestation-v2"
    assert u24_guard.CI_SETUP_ROOT == u24_guard.DENYLIST_ROWS[-1]
    setup_names = (
        "PKG-INFO",
        "SOURCES.txt",
        "dependency_links.txt",
        "entry_points.txt",
        "requires.txt",
        "top_level.txt",
    )
    assert u24_guard.CI_SETUP_PATHS == tuple(
        u24_guard.CI_SETUP_ROOT + name for name in setup_names
    )
    exact_setup = list(u24_guard.CI_SETUP_PATHS)
    legal_t0_status = sorted([*exact_setup, *BOOTSTRAP_PATHS])
    assert u24_guard.governed_status_paths([], []) == []
    assert u24_guard.governed_status_paths([WORKFLOW_PATH], []) == [WORKFLOW_PATH]
    assert u24_guard.governed_status_paths(exact_setup, exact_setup) == []
    assert u24_guard.governed_status_paths(legal_t0_status, exact_setup) == sorted(
        BOOTSTRAP_PATHS
    )
    outside_status = sorted([*exact_setup, "unregistered-u24-dirt.txt"])
    governed_outside = u24_guard.governed_status_paths(outside_status, exact_setup)
    assert governed_outside == ["unregistered-u24-dirt.txt"]
    assert not set(governed_outside) <= BOOTSTRAP_PATHS
    invalid_setup_rows: tuple[list[Any], ...] = (
        exact_setup[:-1],
        sorted([*exact_setup, u24_guard.CI_SETUP_ROOT + "seventh.txt"]),
        [*exact_setup, u24_guard.CI_SETUP_ROOT + "nested/entry.txt"],
        [u24_guard.CI_SETUP_ROOT.rstrip("/")],
        [path.swapcase() for path in exact_setup],
        [*exact_setup, exact_setup[-1]],
        list(reversed(exact_setup)),
        [*exact_setup[:-1], 1],
    )
    for invalid_setup in invalid_setup_rows:
        with pytest.raises((TypeError, ValueError)):
            u24_guard.governed_status_paths(
                sorted({path for path in invalid_setup if type(path) is str}),
                invalid_setup,
            )
    with pytest.raises((TypeError, ValueError)):
        u24_guard.governed_status_paths([WORKFLOW_PATH, WORKFLOW_PATH], [])
    with pytest.raises((TypeError, ValueError)):
        u24_guard.governed_status_paths([WORKFLOW_PATH, ".github/actions.txt"], [])

    def raw_status(rows: list[tuple[str, str]]) -> bytes:
        return b"".join(
            xy.encode("ascii") + b" " + path.encode("utf-8") + b"\x00"
            for xy, path in rows
        )

    exact_rows = [("??", path) for path in exact_setup]
    with tempfile.TemporaryDirectory(prefix="u24-b0r-status-") as temporary:
        temporary_root = Path(temporary).resolve()
        residue_root = temporary_root / u24_guard.CI_SETUP_ROOT.rstrip("/")
        residue_root.mkdir()
        for path in exact_setup:
            (temporary_root / path).write_bytes(b"untrusted setup residue\n")

        observed, admitted = u24_guard._validate_status_payload(  # type: ignore[attr-defined]
            raw_status(exact_rows), temporary_root
        )
        assert observed == exact_setup and admitted == exact_setup

        for xy in ("A ", " M", "R "):
            forged_rows = [(xy, exact_setup[0]), *exact_rows[1:]]
            with pytest.raises(ValueError):
                u24_guard._validate_status_payload(  # type: ignore[attr-defined]
                    raw_status(forged_rows), temporary_root
                )
        for forged_rows in (
            exact_rows[:-1],
            [*exact_rows, ("??", u24_guard.CI_SETUP_ROOT + "seventh.txt")],
            [
                ("??", exact_setup[0].swapcase()),
                *exact_rows[1:],
            ],
        ):
            with pytest.raises(ValueError):
                u24_guard._validate_status_payload(  # type: ignore[attr-defined]
                    raw_status(forged_rows), temporary_root
                )

        victim = temporary_root / exact_setup[0]
        victim.unlink()
        victim.mkdir()
        with pytest.raises(ValueError):
            u24_guard._validate_status_payload(  # type: ignore[attr-defined]
                raw_status(exact_rows), temporary_root
            )
        victim.rmdir()
        victim.write_bytes(b"restored setup residue\n")

        root_stat = u24_guard.os.lstat(residue_root)

        class FakeRootStat:
            def __init__(self, mode: int, attributes: int, tag: int) -> None:
                self.st_mode = mode
                self.st_file_attributes = attributes
                self.st_reparse_tag = tag

        fake_root_stats = (
            FakeRootStat(u24_guard.stat.S_IFLNK | 0o777, 0, 0),
            FakeRootStat(root_stat.st_mode, 0x400, 1),
        )
        for fake_root_stat in fake_root_stats:
            monkeypatch = pytest.MonkeyPatch()
            monkeypatch.setattr(
                u24_guard.os,
                "lstat",
                lambda _path, result=fake_root_stat: result,
            )
            try:
                with pytest.raises(ValueError):
                    u24_guard._validate_setup_filesystem(  # type: ignore[attr-defined]
                        temporary_root
                    )
            finally:
                monkeypatch.undo()
        residue_root.rename(temporary_root / "setup-residue-cleanup")
    assert CONTROL["is_shallow"] is False
    assert REJECTED_BUILD_COMMITS.isdisjoint(
        {row["commit"] for row in _revision_rows()}
    )
    anchor = _revision(ANCHOR_COMMIT)
    assert anchor["parents"] == [ANCHOR_PARENT]
    assert _changed(anchor) == {ANCHOR_FAILURE_PATH}
    blobs = _blobs(anchor)
    assert blobs[ANCHOR_FAILURE_PATH] == ANCHOR_FAILURE_BLOB
    for path, expected in BASE_BLOBS.items():
        assert blobs[path] == expected
    for path, expected in ANCHOR_CONTROL_BLOBS.items():
        assert blobs[path] == expected
    for path, expected in AUTHORITY_BLOBS.items():
        assert blobs[path] == expected
    a2 = _revision(A2_COMMIT)
    assert a2["parents"] == [ANCHOR_COMMIT]
    assert _changed(a2) == {A2_DOCUMENT_PATH}
    assert _blobs(a2)[A2_DOCUMENT_PATH] == A2_DOCUMENT_BLOB
    assert ANCHOR_TREE == "4442cff7b0c84fd5d24dd4d68020f5afade9cd12"
    assert ORIGINAL_AUTHORITY_COMMIT == "14234e209229931c00615d4b171620ec6d1bbbf5"
    assert ORIGINAL_AUTHORITY_PARENT == "78c12549eb188610977842edbc38e2723d469ba4"
    assert blobs[ACCEPTED_FAILURE_PATH] == ACCEPTED_FAILURE_BLOB
    assert blobs[ORIGINAL_AUTHORITY_PATH] == ORIGINAL_AUTHORITY_BLOB
    assert CONTROL["absent_at_a0"] == {
        path: True for path in ABSENT_AT_ANCHOR
    }
    assert UNION_ALLOWLIST == EXPECTED_UNION_ALLOWLIST
    assert FROZEN_REFS == {
        "A2": "codex/uprime-u2-u4-development-r2-a0",
        "T0": "codex/uprime-u2-u4-development-r2-topology-bootstrap",
        "build": "codex/uprime-u2-u4-development-r2-build",
        "closeout": "codex/uprime-u2-u4-development-r2-closeout",
        "failure": "codex/uprime-u2-u4-development-r2-failure-closeout",
        "accepted": "codex/uprime-odlrq-plan",
    }
    assert STAGE_ORDER == ("E0", "E1", "E2", "ME0", "S0", "I0")
    assert MAX_BUILD_COMMITS == 7 and MAX_CORRECTIONS == 1
    assert WALL_SECONDS == {
        "B0": 60,
        "E0": 60,
        "E1": 120,
        "E2": 180,
        "ME0": 180,
        "S0": 300,
        "I0": 900,
        "EMIT": 900,
        "CLOSEOUT": 60,
    }


def test_u24_b0_anchor_contiguous_budget_and_terminal_topology() -> None:
    state = _validate_epoch_topology(CONTROL)
    actual_interval = CONTROL["first_parent_after_a0"]
    actual_rows = _revision_rows(CONTROL)
    actual_dirty = _governed_dirty(CONTROL)
    if len(actual_interval) == 1:
        assert actual_dirty == BOOTSTRAP_PATHS
        assert state["pending"] == "T0"
        assert state["completed"] == []
        assert state["corrections"] == 0
        assert state["terminal"] is None
    else:
        post_t0_rows = actual_rows[3:]
        committed_t0_correction = bool(
            post_t0_rows
            and _changed(post_t0_rows[0]) <= BOOTSTRAP_CONTROL_PATHS
        )
        if committed_t0_correction:
            assert _changed(post_t0_rows[0]) == {IDENTITY_PATH, GUARD_PATH}
        if not post_t0_rows:
            if actual_dirty:
                assert actual_dirty == {IDENTITY_PATH, GUARD_PATH}
                assert state == {
                    "completed": [],
                    "counts": {name: 0 for name in STAGE_ORDER},
                    "corrections": 0,
                    "pending": "T0-correction",
                    "terminal": None,
                }
            else:
                assert state == {
                    "completed": [],
                    "counts": {name: 0 for name in STAGE_ORDER},
                    "corrections": 0,
                    "pending": None,
                    "terminal": None,
                }
        elif committed_t0_correction and len(post_t0_rows) == 1:
            if actual_dirty:
                assert actual_dirty <= STAGE_ALLOWLISTS["E0"]
                assert bool(actual_dirty & STAGE_MARKERS["E0"])
                expected_pending = "E0"
            else:
                expected_pending = None
            assert state == {
                "completed": [],
                "counts": {name: 0 for name in STAGE_ORDER},
                "corrections": 1,
                "pending": expected_pending,
                "terminal": None,
            }
        elif committed_t0_correction and len(post_t0_rows) == 2:
            assert _changed(post_t0_rows[1]) <= STAGE_ALLOWLISTS["E0"]
            assert bool(_changed(post_t0_rows[1]) & STAGE_MARKERS["E0"])
            if actual_dirty:
                assert actual_dirty <= STAGE_ALLOWLISTS["E1"]
                assert bool(actual_dirty & STAGE_MARKERS["E1"])
                expected_pending = "E1"
            else:
                expected_pending = None
            assert state == {
                "completed": ["E0"],
                "counts": {
                    name: (1 if name == "E0" else 0)
                    for name in STAGE_ORDER
                },
                "corrections": 1,
                "pending": expected_pending,
                "terminal": None,
            }
        else:
            assert not committed_t0_correction or state["corrections"] == 1
            assert state["completed"] == list(
                STAGE_ORDER[: len(state["completed"])]
            )

    def append_row(
        source: Mapping[str, Any],
        commit: str,
        changed: set[str],
        overrides: Mapping[str, str | None] | None = None,
    ) -> dict[str, Any]:
        result = copy.deepcopy(source)
        previous = result["revisions"][-1]
        tree = copy.deepcopy(previous["tree_blobs"])
        replacements = {} if overrides is None else dict(overrides)
        for path in changed:
            if path in tree:
                tree[path] = replacements.get(path, commit[:40])
        row = {
            "commit": commit,
            "parents": [previous["commit"]],
            "changed_paths": sorted(changed),
            "tree_blobs": tree,
        }
        result["first_parent_after_a0"].append(commit)
        result["revisions"].append(row)
        result["head"] = commit
        result["status_paths"] = []
        result["ci_setup_paths"] = []
        result["worktree_blobs"] = copy.deepcopy(tree)
        return result

    pending_t0 = copy.deepcopy(CONTROL)
    pending_t0["head"] = A2_COMMIT
    pending_t0["first_parent_after_a0"] = [A2_COMMIT]
    pending_t0["revisions"] = pending_t0["revisions"][:2]
    pending_t0["status_paths"] = sorted(BOOTSTRAP_PATHS)
    pending_t0["ci_setup_paths"] = []
    pending_t0["worktree_blobs"] = copy.deepcopy(
        pending_t0["revisions"][1]["tree_blobs"]
    )
    bootstrap_source = (
        _blobs(_revision_rows(CONTROL)[2])
        if len(actual_interval) >= 2
        else _worktree_blobs(CONTROL)
    )
    for path in BOOTSTRAP_PATHS:
        pending_t0["worktree_blobs"][path] = bootstrap_source[path]
    pending_bootstrap = _validate_epoch_topology(pending_t0)
    assert pending_bootstrap["pending"] == "T0"
    assert pending_bootstrap["completed"] == []

    t0_commit = "10" * 20
    t0 = append_row(
        pending_t0,
        t0_commit,
        BOOTSTRAP_PATHS,
        {
            path: _worktree_blobs(pending_t0)[path]
            for path in BOOTSTRAP_PATHS
        },
    )
    committed = _validate_epoch_topology(t0)
    assert committed["completed"] == []
    assert committed["pending"] is None

    pending_e0 = copy.deepcopy(t0)
    pending_e0["status_paths"] = ["lean_rgc/odlrq/quotient_generator.py"]
    pending_e0["worktree_blobs"][
        "lean_rgc/odlrq/quotient_generator.py"
    ] = "19" * 20
    e0_pending_state = _validate_epoch_topology(pending_e0)
    assert e0_pending_state["completed"] == []
    assert e0_pending_state["pending"] == "E0"

    e0_commit = "20" * 20
    e0 = append_row(
        t0,
        e0_commit,
        {"lean_rgc/odlrq/quotient_generator.py"},
    )
    after_e0 = _validate_epoch_topology(e0)
    assert after_e0["completed"] == ["E0"]
    assert after_e0["counts"]["E0"] == 1

    def rejected(candidate: Mapping[str, Any]) -> None:
        with pytest.raises((AssertionError, KeyError, TypeError, ValueError)):
            _validate_epoch_topology(candidate)

    attacks: list[dict[str, Any]] = []

    missing_a2 = copy.deepcopy(pending_t0)
    missing_a2["head"] = ANCHOR_COMMIT
    missing_a2["first_parent_after_a0"] = []
    missing_a2["revisions"] = missing_a2["revisions"][:1]
    missing_a2["worktree_blobs"] = copy.deepcopy(
        missing_a2["revisions"][0]["tree_blobs"]
    )
    attacks.append(missing_a2)

    wrong_a2_parent = copy.deepcopy(pending_t0)
    wrong_a2_parent["revisions"][1]["parents"] = [ANCHOR_PARENT]
    attacks.append(wrong_a2_parent)
    changed_a2_document = copy.deepcopy(pending_t0)
    changed_a2_document["revisions"][1]["tree_blobs"][A2_DOCUMENT_PATH] = (
        "00" * 20
    )
    attacks.append(changed_a2_document)
    merge_a2 = copy.deepcopy(pending_t0)
    merge_a2["revisions"][1]["parents"].append("ff" * 20)
    attacks.append(merge_a2)

    wrong_t0_parent = copy.deepcopy(t0)
    wrong_t0_parent["revisions"][2]["parents"] = [ANCHOR_COMMIT]
    attacks.append(wrong_t0_parent)
    merge_t0 = copy.deepcopy(t0)
    merge_t0["revisions"][2]["parents"].append("ee" * 20)
    attacks.append(merge_t0)

    reordered = copy.deepcopy(t0)
    reordered["first_parent_after_a0"] = [t0_commit, A2_COMMIT]
    reordered["revisions"] = [
        reordered["revisions"][0],
        reordered["revisions"][2],
        reordered["revisions"][1],
    ]
    reordered["head"] = A2_COMMIT
    attacks.append(reordered)
    duplicate = copy.deepcopy(pending_t0)
    duplicate["revisions"].append(copy.deepcopy(duplicate["revisions"][1]))
    attacks.append(duplicate)

    inserted = copy.deepcopy(t0)
    inserted_row = copy.deepcopy(inserted["revisions"][1])
    inserted_row["commit"] = "11" * 20
    inserted_row["parents"] = [A2_COMMIT]
    inserted_row["changed_paths"] = ["lean_rgc/odlrq/quotient_generator.py"]
    inserted["revisions"][2]["parents"] = [inserted_row["commit"]]
    inserted["revisions"].insert(2, inserted_row)
    inserted["first_parent_after_a0"].insert(1, inserted_row["commit"])
    attacks.append(inserted)

    extra_t0_path = copy.deepcopy(t0)
    extra_t0_path["revisions"][2]["changed_paths"].append(MANIFEST_PATH)
    attacks.append(extra_t0_path)
    changed_t0_document = copy.deepcopy(t0)
    changed_t0_document["revisions"][2]["tree_blobs"][
        BOOTSTRAP_DOCUMENT_PATH
    ] = "00" * 20
    changed_t0_document["worktree_blobs"][BOOTSTRAP_DOCUMENT_PATH] = "00" * 20
    attacks.append(changed_t0_document)
    changed_e0_base = copy.deepcopy(e0)
    changed_e0_base["revisions"][-1]["tree_blobs"][
        "lean_rgc/odlrq/contracts.py"
    ] = "00" * 20
    changed_e0_base["worktree_blobs"]["lean_rgc/odlrq/contracts.py"] = "00" * 20
    attacks.append(changed_e0_base)

    success_reopen = append_row(
        pending_t0, "31" * 20, SUCCESS_TERMINAL_PATHS
    )
    attacks.append(success_reopen)
    other_failure = append_row(
        pending_t0, "32" * 20, {FAILURE_CLOSEOUT_PATH}
    )
    attacks.append(other_failure)
    second_bootstrap = append_row(t0, "33" * 20, BOOTSTRAP_PATHS)
    attacks.append(second_bootstrap)

    failure_terminal = append_row(
        e0, "34" * 20, FAILURE_TERMINAL_PATHS
    )
    post_terminal = append_row(
        failure_terminal,
        "35" * 20,
        {"lean_rgc/odlrq/envelope.py"},
    )
    attacks.append(post_terminal)

    skipped_e0 = append_row(
        t0, "41" * 20, {"lean_rgc/odlrq/envelope.py"}
    )
    attacks.append(skipped_e0)
    cross_stage_correction = append_row(
        e0, "42" * 20, {"lean_rgc/odlrq/selection.py"}
    )
    attacks.append(cross_stage_correction)
    correction_one = append_row(
        e0, "43" * 20, {"lean_rgc/odlrq/quotient_generator.py"}
    )
    correction_two = append_row(
        correction_one,
        "44" * 20,
        {"lean_rgc/odlrq/quotient_generator.py"},
    )
    attacks.append(correction_two)
    t0_correction = append_row(
        t0, "45" * 20, {IDENTITY_PATH, GUARD_PATH}
    )
    clean_t0_correction = _validate_epoch_topology(t0_correction)
    assert clean_t0_correction == {
        "completed": [],
        "counts": {name: 0 for name in STAGE_ORDER},
        "corrections": 1,
        "pending": None,
        "terminal": None,
    }
    dirty_e0_after_correction = copy.deepcopy(t0_correction)
    dirty_e0_after_correction["status_paths"] = [
        "lean_rgc/odlrq/quotient_generator.py"
    ]
    dirty_e0_after_correction["worktree_blobs"][
        "lean_rgc/odlrq/quotient_generator.py"
    ] = "48" * 20
    pending_e0_after_correction = _validate_epoch_topology(
        dirty_e0_after_correction
    )
    assert pending_e0_after_correction == {
        "completed": [],
        "counts": {name: 0 for name in STAGE_ORDER},
        "corrections": 1,
        "pending": "E0",
        "terminal": None,
    }
    t0_correction_e0 = append_row(
        t0_correction,
        "46" * 20,
        {"lean_rgc/odlrq/quotient_generator.py"},
    )
    committed_e0_after_correction = _validate_epoch_topology(t0_correction_e0)
    assert committed_e0_after_correction == {
        "completed": ["E0"],
        "counts": {
            name: (1 if name == "E0" else 0) for name in STAGE_ORDER
        },
        "corrections": 1,
        "pending": None,
        "terminal": None,
    }
    shared_quota_reuse = append_row(
        t0_correction_e0,
        "47" * 20,
        {"lean_rgc/odlrq/quotient_generator.py"},
    )
    attacks.append(shared_quota_reuse)

    wrong_correction_parent = copy.deepcopy(t0_correction)
    wrong_correction_parent["revisions"][3]["parents"] = [A2_COMMIT]
    attacks.append(wrong_correction_parent)
    merge_correction = copy.deepcopy(t0_correction)
    merge_correction["revisions"][3]["parents"].append("dd" * 20)
    attacks.append(merge_correction)
    non_immediate_correction = append_row(e0, "49" * 20, {GUARD_PATH})
    attacks.append(non_immediate_correction)
    for extra_path in (
        BOOTSTRAP_DOCUMENT_PATH,
        A2_DOCUMENT_PATH,
        WORKFLOW_PATH,
        MANIFEST_PATH,
        "lean_rgc/odlrq/quotient_generator.py",
        SUCCESS_CLOSEOUT_PATH,
    ):
        mixed_correction = append_row(
            t0,
            ("7" + str(len(attacks) % 10)) * 20,
            {IDENTITY_PATH, GUARD_PATH, extra_path},
        )
        attacks.append(mixed_correction)

    through_s0 = t0
    for index, stage in enumerate(STAGE_ORDER[:-1], start=50):
        through_s0 = append_row(
            through_s0,
            f"{index:02d}" * 20,
            STAGE_MARKERS[stage],
        )
    dirty_pending_i0_runner = copy.deepcopy(through_s0)
    pending_i0_paths = {RUNNER_PATH, *STAGE_MARKERS["I0"]}
    dirty_pending_i0_runner["status_paths"] = sorted(pending_i0_paths)
    for path in pending_i0_paths:
        dirty_pending_i0_runner["worktree_blobs"][path] = "aa" * 20
    attacks.append(dirty_pending_i0_runner)

    through_i0 = append_row(
        through_s0,
        "60" * 20,
        STAGE_MARKERS["I0"],
    )
    dirty_after_i0_runner = copy.deepcopy(through_i0)
    dirty_after_i0_runner["status_paths"] = [RUNNER_PATH]
    dirty_after_i0_runner["worktree_blobs"][RUNNER_PATH] = "bb" * 20
    attacks.append(dirty_after_i0_runner)

    for additions in ([], ["00" * 20], [HISTORICAL_IDENTITY_ADDITION] * 2):
        forged = copy.deepcopy(CONTROL)
        forged["identity_additions"] = additions
        attacks.append(forged)
    shallow = copy.deepcopy(CONTROL)
    shallow["is_shallow"] = True
    attacks.append(shallow)
    wrong_head = copy.deepcopy(CONTROL)
    wrong_head["head"] = ANCHOR_COMMIT
    attacks.append(wrong_head)
    omitted_interval = copy.deepcopy(t0)
    omitted_interval["first_parent_after_a0"] = [A2_COMMIT]
    attacks.append(omitted_interval)
    malformed = copy.deepcopy(CONTROL)
    malformed["unexpected"] = True
    attacks.append(malformed)

    for attack in attacks:
        rejected(attack)

    baseline = CONTROL["a0_manifest"]
    assert type(baseline) is dict
    manifest = _worktree_manifest()
    for name, tiers in baseline.items():
        assert manifest[name] == tiers
    manifest_stages = [*state["completed"]]
    if state["pending"] in STAGE_ORDER:
        manifest_stages.append(state["pending"])
    expected_new = set().union(*(STAGE_MANIFEST_NODES[name] for name in manifest_stages))
    assert set(manifest) - set(baseline) == expected_new
    for name in expected_new:
        assert manifest[name] == ["unit"]


def test_u24_denylist_static_scan_and_exact_runner_copy() -> None:
    assert u24_guard.canonical_denylist_bytes() == u24_guard.DENYLIST_CANONICAL_BYTES
    assert len(u24_guard.DENYLIST_ROWS) == 17
    assert len(set(u24_guard.DENYLIST_ROWS)) == 17
    assert u24_guard.CI_SETUP_ROOT in u24_guard.DENYLIST_ROWS
    assert u24_guard.DENYLIST_SHA256 == __import__("hashlib").sha256(
        u24_guard.DENYLIST_CANONICAL_BYTES
    ).hexdigest().upper()
    u24_guard.static_scan_union_sources(REPO_ROOT)
    workflow_bytes = (REPO_ROOT / WORKFLOW_PATH).read_bytes()
    assert __import__("hashlib").sha256(workflow_bytes).hexdigest().upper() == (
        "7879CC590945366A356DDEAE2B38480E5434048BFBCEC7E37848D443EA528D3B"
    )
    workflow = workflow_bytes.decode("utf-8")
    test_step = (
        "      - name: Test\n"
        "        env:\n"
        "          PYTEST_DISABLE_PLUGIN_AUTOLOAD: \"1\"\n"
        "        run: python -m pytest -q\n"
    )
    assert workflow.count(test_step) == 1
    assert workflow.count("PYTEST_DISABLE_PLUGIN_AUTOLOAD") == 1
    runner = (REPO_ROOT / RUNNER_PATH).read_text(encoding="utf-8")
    for literal in (
        '$MemoryLimitBytes = [uint64]2 * 1024 * 1024 * 1024',
        '$OutputLimitBytes = [int64]64 * 1024 * 1024',
        'B0 = 60; E0 = 60; E1 = 120; E2 = 180; ME0 = 180',
        'S0 = 300; I0 = 900; EMIT = 900; CLOSEOUT = 60',
        'LimitFlags=0x8u|0x100u|0x200u|0x2000u',
        'ActiveProcessLimit=1',
        'guard.install_guard(policy)',
        'PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"',
        'OMP_NUM_THREADS = "1"',
        'OPENBLAS_NUM_THREADS = "1"',
        'MKL_NUM_THREADS = "1"',
        'NUMEXPR_NUM_THREADS = "1"',
        'D6E6DEBCE5C150AE31BA0D04EAF6E59FD2D79FDC4C0D5272264574665C0242F4',
        'requested lane has not reached its frozen source marker',
    ):
        assert runner.count(literal) >= 1
    manifest_match = __import__("re").search(
        r"\$RuntimeManifestCanonical = @'\n(.*?)\n'@", runner, __import__("re").S
    )
    assert manifest_match is not None
    assert __import__("hashlib").sha256(
        manifest_match.group(1).encode("utf-8")
    ).hexdigest().upper() == "D6E6DEBCE5C150AE31BA0D04EAF6E59FD2D79FDC4C0D5272264574665C0242F4"
    bootstrap = runner.split("$bootstrap = @'", 1)[1].split("'@", 1)[0]
    control = runner.split("$control = @'", 1)[1].split("'@", 1)[0]
    assert bootstrap.index("import numpy as np") < bootstrap.index("guard.install_guard(policy)")
    assert bootstrap.index("guard.install_guard(policy)") < bootstrap.index("import pytest")
    assert 'test_uprime_u2_u4_development.py")' not in control
    assert '-X "pycache_prefix=$controlPycachePrefix" $controlPath' in runner
    assert '@("-I", "-S", "-X", "pycache_prefix=$childPycachePrefix", $bootstrapPath)' in runner
    assert runner.count('pycache prefix is not empty') == 2
    assert "PYTHONPYCACHEPREFIX" not in runner

    def replace_exact(
        value: str, old: str, new: str, expected_count: int
    ) -> str:
        assert value.count(old) == expected_count
        return value.replace(old, new)

    def git_blob_sha1(raw: bytes) -> str:
        digest = __import__("hashlib").sha1()
        digest.update(f"blob {len(raw)}\0".encode("ascii"))
        digest.update(raw)
        return digest.hexdigest()

    guard_raw = (REPO_ROOT / GUARD_PATH).read_bytes().replace(b"\r\n", b"\n")
    assert b"\r" not in guard_raw
    guard_source = guard_raw.decode("utf-8")
    anchor_identity_core_sha256 = (
        "E18B8844D8E3274BA338621113FF405BE9805F73088B76920DDCBA219EBF9354"
    )
    anchor_runner_sha256 = (
        "38A3C357413FC3444034556AA675D9723D2B22E0E2B5A519ABDE935E4BD60DD1"
    )
    assert u24_guard.FROZEN_IDENTITY_CORE_SHA256 != anchor_identity_core_sha256
    assert u24_guard.FROZEN_RUNNER_SHA256 != anchor_runner_sha256
    reconstructed_guard = replace_exact(
        guard_source,
        f'FROZEN_IDENTITY_CORE_SHA256 = "{u24_guard.FROZEN_IDENTITY_CORE_SHA256}"',
        f'FROZEN_IDENTITY_CORE_SHA256 = "{anchor_identity_core_sha256}"',
        1,
    )
    reconstructed_guard = replace_exact(
        reconstructed_guard,
        f'FROZEN_RUNNER_SHA256 = "{u24_guard.FROZEN_RUNNER_SHA256}"',
        f'FROZEN_RUNNER_SHA256 = "{anchor_runner_sha256}"',
        1,
    )
    reconstructed_guard = replace_exact(
        reconstructed_guard,
        "MAX_BUILD_COMMITS = 7",
        "MAX_BUILD_COMMITS = 8",
        1,
    )
    reconstructed_guard_bytes = reconstructed_guard.encode("utf-8")
    assert __import__("hashlib").sha256(
        reconstructed_guard_bytes
    ).hexdigest().upper() == (
        "34880CA312F411FB526843A16A4722D5A19EADEE04C25402977A962DA3F5717C"
    )
    assert git_blob_sha1(reconstructed_guard_bytes) == ANCHOR_GUARD_BLOB

    runner_raw = (REPO_ROOT / RUNNER_PATH).read_bytes().replace(b"\r\n", b"\n")
    assert b"\r" not in runner_raw
    reconstructed_runner = runner_raw.decode("utf-8")
    r2_documents = (
        SUCCESS_CLOSEOUT_PATH,
        A2_DOCUMENT_PATH,
        FAILURE_CLOSEOUT_PATH,
        BOOTSTRAP_DOCUMENT_PATH,
    )
    added_document_block = "".join(
        f"    '{path}',\n" for path in r2_documents
    )
    reconstructed_runner = replace_exact(
        reconstructed_runner, added_document_block, "", 2
    )
    current_absent_tail = (
        "    'tests/test_odlrq_selection.py', 'tests/test_odlrq_similarity.py',\n"
        ")"
    )
    anchor_absent_tail = (
        "    'tests/test_odlrq_selection.py', 'tests/test_odlrq_similarity.py',\n"
        "    'tests/test_uprime_u2_u4_development.py', 'tests/uprime_u24_guard.py',\n"
        "    'tools/run_uprime_u2_u4_development_tests.ps1',\n"
        ")"
    )
    reconstructed_runner = replace_exact(
        reconstructed_runner, current_absent_tail, anchor_absent_tail, 1
    )
    t0_dirty_exception = (
        'if lane == "B0":\n'
        "    allowed_dirty.add(\n"
        f"        '{BOOTSTRAP_DOCUMENT_PATH}'\n"
        "    )\n"
    )
    reconstructed_runner = replace_exact(
        reconstructed_runner, t0_dirty_exception, "", 1
    )
    reconstructed_runner = replace_exact(
        reconstructed_runner, ANCHOR_COMMIT, LEGACY_A1_COMMIT, 3
    )
    reconstructed_runner_bytes = reconstructed_runner.encode("utf-8")
    assert __import__("hashlib").sha256(
        reconstructed_runner_bytes
    ).hexdigest().upper() == anchor_runner_sha256
    assert git_blob_sha1(reconstructed_runner_bytes) == ANCHOR_RUNNER_BLOB

    identity_tree = __import__("ast").parse(
        (REPO_ROOT / IDENTITY_PATH).read_text(encoding="utf-8")
    )
    identity_tests = [
        node.name
        for node in identity_tree.body
        if isinstance(node, __import__("ast").FunctionDef)
        and node.name.startswith("test_u24_")
        and not node.name.startswith("test_u24_i0_")
    ]
    assert identity_tests == [
        "test_u24_a0_anchor_authorities_and_nonexistence_are_frozen",
        "test_u24_b0_anchor_contiguous_budget_and_terminal_topology",
        "test_u24_denylist_static_scan_and_exact_runner_copy",
        "test_u24_autouse_guard_blocks_paths_process_network_and_dynamic_import",
        "test_u24_four_tier_public_wires_do_not_trust_tier_booleans",
    ]

    encoded = u24_guard.encode_control_plane_attestation(CONTROL)
    assert encoded.startswith("z1:") and len(encoded) < 24000
    os.environ[u24_guard.CONTROL_ATTESTATION_ENV] = encoded
    assert u24_guard.load_control_plane_attestation(
        REPO_ROOT,
        a0_commit=ANCHOR_COMMIT,
        identity_path=IDENTITY_PATH,
        tracked_paths=TRACKED_PATHS,
        absent_at_a0=ABSENT_AT_ANCHOR,
    ) == CONTROL
    for invalid_setup in (
        list(u24_guard.CI_SETUP_PATHS[:-1]),
        [*u24_guard.CI_SETUP_PATHS, u24_guard.CI_SETUP_ROOT + "seventh.txt"],
        list(reversed(u24_guard.CI_SETUP_PATHS)),
    ):
        forged_control = copy.deepcopy(CONTROL)
        forged_control["ci_setup_paths"] = invalid_setup
        with pytest.raises(ValueError):
            u24_guard.encode_control_plane_attestation(forged_control)
    forged_extra = copy.deepcopy(CONTROL)
    forged_extra["ci_setup_digest"] = "00" * 32
    with pytest.raises(ValueError):
        u24_guard.encode_control_plane_attestation(forged_extra)


def test_u24_autouse_guard_blocks_paths_process_network_and_dynamic_import() -> None:
    policy = u24_guard.GuardPolicy(u24_guard.GuardMode.SEMANTIC, REPO_ROOT)
    u24_guard.require_active_guard(policy)
    blocked_path = REPO_ROOT / u24_guard.DENYLIST_ROWS[0] / "never-read.json"
    with pytest.raises(u24_guard.U24ResourceOrScopeBlocked, match=u24_guard.DENIAL_DISPOSITION):
        open(blocked_path, "rb")
    with pytest.raises(u24_guard.U24ResourceOrScopeBlocked, match=u24_guard.DENIAL_DISPOSITION):
        os.open(blocked_path, os.O_RDONLY)
    with pytest.raises(u24_guard.U24ResourceOrScopeBlocked, match=u24_guard.DENIAL_DISPOSITION):
        blocked_path.read_bytes()
    with pytest.raises(u24_guard.U24ResourceOrScopeBlocked, match=u24_guard.DENIAL_DISPOSITION):
        os.listdir(blocked_path.parent)
    setup_root = REPO_ROOT / u24_guard.CI_SETUP_ROOT
    setup_entry_points = setup_root / "entry_points.txt"
    with pytest.raises(u24_guard.U24ResourceOrScopeBlocked, match=u24_guard.DENIAL_DISPOSITION):
        open(setup_entry_points, "rb")
    with pytest.raises(u24_guard.U24ResourceOrScopeBlocked, match=u24_guard.DENIAL_DISPOSITION):
        setup_entry_points.read_bytes()
    with pytest.raises(u24_guard.U24ResourceOrScopeBlocked, match=u24_guard.DENIAL_DISPOSITION):
        setup_entry_points.stat()
    with pytest.raises(u24_guard.U24ResourceOrScopeBlocked, match=u24_guard.DENIAL_DISPOSITION):
        os.listdir(setup_root)
    with pytest.raises(u24_guard.U24ResourceOrScopeBlocked, match=u24_guard.DENIAL_DISPOSITION):
        os.scandir(setup_root)
    with pytest.raises(u24_guard.U24ResourceOrScopeBlocked, match=u24_guard.DENIAL_DISPOSITION):
        list(setup_root.glob("*"))
    with pytest.raises(u24_guard.U24ResourceOrScopeBlocked, match=u24_guard.DENIAL_DISPOSITION):
        sys.modules["subprocess"].run(["git", "status"])
    with pytest.raises(u24_guard.U24ResourceOrScopeBlocked, match=u24_guard.DENIAL_DISPOSITION):
        sys.modules["socket"].socket()
    with pytest.raises(u24_guard.U24ResourceOrScopeBlocked, match=u24_guard.DENIAL_DISPOSITION):
        u24_guard.importlib.import_module("torch")
    with pytest.raises(u24_guard.U24ResourceOrScopeBlocked, match=u24_guard.DENIAL_DISPOSITION):
        u24_guard.importlib.import_module("ctypes")
    allowed_fd = os.open(REPO_ROOT / "pyproject.toml", os.O_RDONLY)
    os.close(allowed_fd)
    with pytest.raises(u24_guard.U24ResourceOrScopeBlocked, match=u24_guard.DENIAL_DISPOSITION):
        os.chdir(REPO_ROOT.parent)
    if "nt" in sys.modules:
        with pytest.raises(u24_guard.U24ResourceOrScopeBlocked, match=u24_guard.DENIAL_DISPOSITION):
            sys.modules["nt"].system("exit 0")
        with pytest.raises(u24_guard.U24ResourceOrScopeBlocked, match=u24_guard.DENIAL_DISPOSITION):
            sys.modules["nt"].open(blocked_path, os.O_RDONLY)

    emit = u24_guard.GuardPolicy(u24_guard.GuardMode.EMIT, REPO_ROOT)
    u24_guard._check_path(  # type: ignore[attr-defined]
        emit, REPO_ROOT / u24_guard.EMIT_ROOT, write=True
    )
    u24_guard._check_path(  # type: ignore[attr-defined]
        emit, REPO_ROOT / u24_guard.CLOSEOUT_ARTIFACTS[0], write=True
    )
    with pytest.raises(u24_guard.U24ResourceOrScopeBlocked, match=u24_guard.DENIAL_DISPOSITION):
        u24_guard._check_path(  # type: ignore[attr-defined]
            emit, REPO_ROOT / u24_guard.EMIT_ROOT / "extra.json", write=True
        )


def test_u24_four_tier_public_wires_do_not_trust_tier_booleans() -> None:
    import lean_rgc.odlrq.quotient_generator as qg
    import test_odlrq_quotient_generator as base_qg

    exact_parameters = tuple(inspect.signature(qg.ExactFiniteOperator.from_dict).parameters)
    certified_parameters = tuple(
        inspect.signature(qg.CertifiedIntervalOperator.from_dict).parameters
    )
    assert exact_parameters == ("value", "source")
    assert certified_parameters == ("value", "exact", "candidate", "witness")

    _, exact, candidate, _evidence, witness, certified = base_qg._bundle()
    assert qg.ExactFiniteOperator.from_dict(exact.to_dict(), exact._verified_source) == exact
    assert qg.CertifiedIntervalOperator.from_dict(
        certified.to_dict(), exact, candidate, witness
    ) == certified
    forged_exact = copy.deepcopy(exact.to_dict())
    forged_exact["operator_sha256"] = "00" * 32
    with pytest.raises(qg.StrictContractError):
        qg.ExactFiniteOperator.from_dict(forged_exact, exact._verified_source)
    forged_certified = copy.deepcopy(certified.to_dict())
    forged_certified["operator_tier"] = qg.NOMINAL_OPERATOR_TIER
    with pytest.raises(qg.StrictContractError):
        qg.CertifiedIntervalOperator.from_dict(
            forged_certified, exact, candidate, witness
        )

    row = qg.IntervalTargetRow(0, "u24_b0_action", (0,))
    observed = qg.ObservedIntervalOperator("u24_b0_observation", (row,))
    nominal = qg.NominalOperator("u24_b0_model", (row,))
    assert qg.ObservedIntervalOperator.from_dict(observed.to_dict()) == observed
    assert qg.NominalOperator.from_dict(nominal.to_dict()) == nominal

    observed_wire = copy.deepcopy(observed.to_dict())
    observed_wire["operator_tier"] = qg.EXACT_OPERATOR_TIER
    with pytest.raises(qg.StrictContractError):
        qg.ObservedIntervalOperator.from_dict(observed_wire)
    nominal_wire = copy.deepcopy(nominal.to_dict())
    nominal_wire["evidence_scope"] = qg.OBSERVED_OPERATOR_TIER
    with pytest.raises(qg.StrictContractError):
        qg.NominalOperator.from_dict(nominal_wire)

    forbidden_promotions = {
        "promote_observed",
        "promote_nominal",
        "exact_to_observed",
        "certified_to_nominal",
    }
    assert forbidden_promotions.isdisjoint(qg.__all__)


# U24_I0_TEST_EXTENSION_BEGIN
# I0 may add only undecorated ``test_u24_i0_*`` function definitions here.
# U24_I0_TEST_EXTENSION_END
