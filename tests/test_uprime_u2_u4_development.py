from __future__ import annotations

import copy
import inspect
import json
import os
from pathlib import Path
import sys
from typing import Any, Mapping

import pytest

import uprime_u24_guard as u24_guard

REPO_ROOT = Path(__file__).resolve().parents[1]

A0_COMMIT = "14234e209229931c00615d4b171620ec6d1bbbf5"
A0_PARENT = "78c12549eb188610977842edbc38e2723d469ba4"
A0_DOCUMENT_PATH = (
    "docs/experiments/"
    "uprime_odlrq_u2_u4_development_construction_bundle_amendment_2026-07-13.md"
)
A0_DOCUMENT_BLOB = "bd3ef021dff5cb5e3a28c1d2a79b0379e5615835"
A0_MANIFEST_BLOB = "88eb765c7c0eb484825e39b956860621db71bc84"

IDENTITY_PATH = "tests/test_uprime_u2_u4_development.py"
GUARD_PATH = "tests/uprime_u24_guard.py"
RUNNER_PATH = "tools/run_uprime_u2_u4_development_tests.ps1"
MANIFEST_PATH = "tests/tier_manifest.json"
SUCCESS_CLOSEOUT_PATH = (
    "docs/experiments/"
    "uprime_odlrq_u2_u4_development_construction_closeout_2026-07-13.md"
)
FAILURE_CLOSEOUT_PATH = (
    "docs/experiments/"
    "uprime_odlrq_u2_u4_development_failure_closeout_2026-07-13.md"
)

FROZEN_REFS = {
    "A0": "codex/uprime-u2-u4-development-a0",
    "build": "codex/uprime-u2-u4-development-build",
    "closeout": "codex/uprime-u2-u4-development-closeout",
    "failure": "codex/uprime-u2-u4-development-failure-closeout",
    "accepted": "codex/uprime-odlrq-plan",
}
STAGE_ORDER = ("B0", "E0", "E1", "E2", "ME0", "S0", "I0")
MAX_BUILD_COMMITS = 8
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

B0_PATHS = {
    IDENTITY_PATH,
    GUARD_PATH,
    RUNNER_PATH,
    MANIFEST_PATH,
}
BASE_BLOBS = {
    "lean_rgc/odlrq/contracts.py":
        "eca7d55bc7c2a7a08fbdc75c3b589f1972cd258f",
    "lean_rgc/odlrq/quotient_generator.py":
        "e8d95082d2e47f0829d960321cc1d62bc686d7ac",
    "lean_rgc/odlrq/__init__.py":
        "866df99205f5073335ea7304b0cc160ab657e8f5",
    "tests/test_odlrq_quotient_generator.py":
        "d014b0c9555ac5932827d86b6b92420849ed4973",
    MANIFEST_PATH: A0_MANIFEST_BLOB,
}
AUTHORITY_BLOBS = {
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
}

STAGE_ALLOWLISTS = {
    "B0": B0_PATHS,
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
    "B0": {IDENTITY_PATH.rsplit("/", 1)[1]},
    "E0": set(),
    "E1": {"test_odlrq_envelope.py"},
    "E2": {"test_odlrq_selection.py"},
    "ME0": {"test_odlrq_maxent.py"},
    "S0": {"test_odlrq_similarity.py"},
    "I0": set(),
}

ABSENT_AT_A0 = tuple(
    sorted(
        {
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
            IDENTITY_PATH,
            GUARD_PATH,
            RUNNER_PATH,
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
    }
)

SUCCESS_ARTIFACT_PATHS = set(u24_guard.CLOSEOUT_ARTIFACTS)
SUCCESS_TERMINAL_PATHS = {SUCCESS_CLOSEOUT_PATH, *SUCCESS_ARTIFACT_PATHS}
FAILURE_TERMINAL_PATHS = {FAILURE_CLOSEOUT_PATH}

TRACKED_PATHS = tuple(
    sorted(
        {
            A0_DOCUMENT_PATH,
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
    a0_commit=A0_COMMIT,
    identity_path=IDENTITY_PATH,
    tracked_paths=TRACKED_PATHS,
    absent_at_a0=ABSENT_AT_A0,
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


def _revision_rows() -> list[dict[str, Any]]:
    rows = CONTROL["revisions"]
    assert type(rows) is list
    assert all(type(row) is dict for row in rows)
    return rows


def _revision(commit: str) -> dict[str, Any]:
    matches = [row for row in _revision_rows() if row.get("commit") == commit]
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


def _semantic_rows() -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    interval = CONTROL["first_parent_after_a0"]
    assert type(interval) is list and all(type(item) is str for item in interval)
    rows = [_revision(commit) for commit in interval]
    terminal = None
    if rows and _changed(rows[-1]) in (SUCCESS_TERMINAL_PATHS, FAILURE_TERMINAL_PATHS):
        terminal = rows.pop()
    assert all(
        _changed(row) not in (SUCCESS_TERMINAL_PATHS, FAILURE_TERMINAL_PATHS)
        for row in rows
    )
    return rows, terminal


def _classify_build_rows(
    rows: list[dict[str, Any]],
) -> tuple[list[str], dict[str, int]]:
    assert rows
    assert _changed(rows[0]) == B0_PATHS
    completed: list[str] = ["B0"]
    counts = {name: 0 for name in STAGE_ORDER}
    counts["B0"] = 1
    next_stage_index = 1
    last_stage = "B0"
    corrections = 0

    for row in rows[1:]:
        changed = _changed(row)
        assert changed
        if next_stage_index < len(STAGE_ORDER):
            candidate = STAGE_ORDER[next_stage_index]
        else:
            candidate = None
        if (
            candidate is not None
            and changed <= STAGE_ALLOWLISTS[candidate]
            and bool(changed & STAGE_MARKERS[candidate])
        ):
            stage = candidate
            completed.append(stage)
            counts[stage] = 1
            next_stage_index += 1
            last_stage = stage
            continue

        assert changed <= STAGE_ALLOWLISTS[last_stage]
        assert counts[last_stage] == 1
        counts[last_stage] = 2
        corrections += 1
        assert corrections <= MAX_CORRECTIONS

    return completed, counts


def _worktree_manifest() -> dict[str, list[str]]:
    value = json.loads((REPO_ROOT / MANIFEST_PATH).read_text(encoding="utf-8"))
    assert type(value) is dict
    return value


def test_u24_a0_anchor_authorities_and_nonexistence_are_frozen() -> None:
    assert CONTROL["schema_version"] == u24_guard.CONTROL_ATTESTATION_SCHEMA
    assert CONTROL["is_shallow"] is False
    a0 = _revision(A0_COMMIT)
    assert a0["parents"] == [A0_PARENT]
    assert _changed(a0) == {A0_DOCUMENT_PATH}
    blobs = _blobs(a0)
    assert blobs[A0_DOCUMENT_PATH] == A0_DOCUMENT_BLOB
    for path, expected in BASE_BLOBS.items():
        assert blobs[path] == expected
    for path, expected in AUTHORITY_BLOBS.items():
        assert blobs[path] == expected
    assert CONTROL["absent_at_a0"] == {path: True for path in ABSENT_AT_A0}
    assert UNION_ALLOWLIST == EXPECTED_UNION_ALLOWLIST
    assert FROZEN_REFS == {
        "A0": "codex/uprime-u2-u4-development-a0",
        "build": "codex/uprime-u2-u4-development-build",
        "closeout": "codex/uprime-u2-u4-development-closeout",
        "failure": "codex/uprime-u2-u4-development-failure-closeout",
        "accepted": "codex/uprime-odlrq-plan",
    }
    assert STAGE_ORDER == ("B0", "E0", "E1", "E2", "ME0", "S0", "I0")
    assert MAX_BUILD_COMMITS == 8 and MAX_CORRECTIONS == 1
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
    head = CONTROL["head"]
    additions = CONTROL["identity_additions"]
    assert type(additions) is list and all(type(item) is str for item in additions)
    rows, terminal = _semantic_rows()
    previous = A0_COMMIT
    for row in rows:
        assert row["parents"] == [previous]
        previous = row["commit"]
    if terminal is not None:
        assert terminal["parents"] == [previous]

    if head == A0_COMMIT:
        assert additions == []
        assert rows == [] and terminal is None
        assert set(CONTROL["status_paths"]) == B0_PATHS
        assert all(CONTROL["worktree_blobs"][path] is not None for path in B0_PATHS)
        completed = ["B0"]
        pending = None
    else:
        assert len(additions) == 1
        b0_commit = additions[0]
        assert rows and rows[0]["commit"] == b0_commit
        assert rows[0]["parents"] == [A0_COMMIT]
        assert _changed(rows[0]) == B0_PATHS
        assert len(rows) <= MAX_BUILD_COMMITS
        completed, counts = _classify_build_rows(rows)
        assert sum(counts.values()) == len(rows)
        assert sum(max(0, amount - 1) for amount in counts.values()) <= MAX_CORRECTIONS
        b0_rows = []
        for row in rows:
            if _changed(row) <= B0_PATHS:
                b0_rows.append(row)
                continue
            break
        b0_guard_blob = _blobs(b0_rows[-1])[GUARD_PATH]
        assert type(b0_guard_blob) is str
        for row in rows[len(b0_rows):]:
            assert _blobs(row)[GUARD_PATH] == b0_guard_blob
        for row in rows:
            blobs = _blobs(row)
            assert blobs[A0_DOCUMENT_PATH] == A0_DOCUMENT_BLOB
            for path, expected in AUTHORITY_BLOBS.items():
                assert blobs[path] == expected
        dirty = set(CONTROL["status_paths"])
        pending = None
        if dirty:
            assert len(completed) < len(STAGE_ORDER)
            pending = STAGE_ORDER[len(completed)]
            assert dirty <= STAGE_ALLOWLISTS[pending]
            assert bool(dirty & STAGE_MARKERS[pending])

    if terminal is not None:
        changed = _changed(terminal)
        assert changed in (SUCCESS_TERMINAL_PATHS, FAILURE_TERMINAL_PATHS)
        if changed == SUCCESS_TERMINAL_PATHS:
            assert completed == list(STAGE_ORDER)

    baseline = CONTROL["a0_manifest"]
    assert type(baseline) is dict
    manifest = _worktree_manifest()
    for name, tiers in baseline.items():
        assert manifest[name] == tiers
    manifest_stages = [*completed, *((pending,) if pending is not None else ())]
    expected_new = set().union(*(STAGE_MANIFEST_NODES[name] for name in manifest_stages))
    assert set(manifest) - set(baseline) == expected_new
    for name in expected_new:
        assert manifest[name] == ["unit"]


def test_u24_denylist_static_scan_and_exact_runner_copy() -> None:
    assert u24_guard.canonical_denylist_bytes() == u24_guard.DENYLIST_CANONICAL_BYTES
    assert len(u24_guard.DENYLIST_ROWS) == 16
    assert len(set(u24_guard.DENYLIST_ROWS)) == 16
    assert u24_guard.DENYLIST_SHA256 == __import__("hashlib").sha256(
        u24_guard.DENYLIST_CANONICAL_BYTES
    ).hexdigest().upper()
    u24_guard.static_scan_union_sources(REPO_ROOT)
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
    assert bootstrap.index("import numpy as np") < bootstrap.index("guard.install_guard(policy)")
    assert bootstrap.index("guard.install_guard(policy)") < bootstrap.index("import pytest")
    assert 'test_uprime_u2_u4_development.py")' not in runner.split("$control = @'", 1)[1].split("'@", 1)[0]
    encoded = u24_guard.encode_control_plane_attestation(CONTROL)
    assert encoded.startswith("z1:") and len(encoded) < 24000
    os.environ[u24_guard.CONTROL_ATTESTATION_ENV] = encoded
    assert u24_guard.load_control_plane_attestation(
        REPO_ROOT,
        a0_commit=A0_COMMIT,
        identity_path=IDENTITY_PATH,
        tracked_paths=TRACKED_PATHS,
        absent_at_a0=ABSENT_AT_A0,
    ) == CONTROL


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
