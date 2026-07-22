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

ANCHOR_COMMIT = "b57ac55e823bc90a7d86f8b593249b70feeadaf1"
ANCHOR_PARENT = "fbc1259dc276265a8949aad86d9e15b87e4a6dff"
ANCHOR_TREE = "3fbb08d6e3d496460e97ca60b83c7667ec518480"
ANCHOR_FAILURE_PATH = (
    "docs/experiments/"
    "uprime_odlrq_u2_u4_development_r4_failure_closeout_2026-07-14.md"
)
ANCHOR_FAILURE_BLOB = "fc1f409d2150fcfd199383d6d881549ee81984e7"
ANCHOR_IDENTITY_BLOB = "1e5b5607d9c66443e49206cf3d2c27fbf2b06178"
ANCHOR_GUARD_BLOB = "39ab9f378da06d54580c99d73da726d78b543123"
ANCHOR_RUNNER_BLOB = "7ab0d04eb2efd21be0bdcf54fcac9fcf21b11b96"
ANCHOR_MANIFEST_BLOB = "47997a9bd67f7ac2cf0cd9c7f654d8f069f925d8"
ANCHOR_WORKFLOW_BLOB = "0349e9ca864b7e9e25064ab7fab5b6dc0665adee"

ACCEPTED_BASE_COMMIT = ANCHOR_PARENT
ACCEPTED_BASE_PARENT = "773a4bae0ed6c88fe855d92a69a211f8834c688c"
ACCEPTED_BASE_TREE = "e17b8dd85e6ee4bf299c6dcfc491deb7119253c5"

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
R1_FAILURE_PATH = (
    "docs/experiments/"
    "uprime_odlrq_u2_u4_development_reconstruction_failure_closeout_2026-07-13.md"
)
R1_FAILURE_BLOB = "8c1a048249b9ac2ddb0fa1ebc74eeac03fdd0692"
HISTORICAL_IDENTITY_ADDITION = "7083e766acd2ba09b45ba3f47f65dc0b34317bd3"

R2_A2_COMMIT = "7c05c494ce79e84ffeb0d0c912ca3ba5f141f402"
R2_A2_DOCUMENT_PATH = (
    "docs/experiments/"
    "uprime_odlrq_u2_u4_development_r2_exact_admission_integration_amendment_2026-07-13.md"
)
R2_A2_DOCUMENT_BLOB = "a6fb65eb7a3d52bfbae985eb6bf32bf5275ac3e1"
R2_BOOTSTRAP_COMMIT = "3970b4f505b842a76573329aaa526a1af08da7c4"
R2_BOOTSTRAP_DOCUMENT_PATH = (
    "docs/experiments/"
    "uprime_odlrq_u2_u4_development_r2_topology_bootstrap_amendment_2026-07-13.md"
)
R2_BOOTSTRAP_DOCUMENT_BLOB = "c5af0cc08a1a6e148d297f9bf06300ba169987eb"
R3_BOOTSTRAP_COMMIT = "4b0fa1ff2f701b1814a835d3b43f1251a92a3296"

R3_BOOTSTRAP_DOCUMENT_PATH = (
    "docs/experiments/"
    "uprime_odlrq_u2_u4_development_r3_stage_local_reentry_amendment_2026-07-13.md"
)
R3_BOOTSTRAP_DOCUMENT_BLOB = "39d0b739954f7170ac4de8e5bda254df22328ae8"
R3_SUCCESS_CLOSEOUT_PATH = (
    "docs/experiments/"
    "uprime_odlrq_u2_u4_development_r3_closeout_2026-07-13.md"
)
R3_FAILURE_CLOSEOUT_PATH = (
    "docs/experiments/"
    "uprime_odlrq_u2_u4_development_r3_failure_closeout_2026-07-13.md"
)
R3_FAILURE_CLOSEOUT_BLOB = "95ec66bb4cddbf7471d017430e5f375e0dd3efe5"

R4_BOOTSTRAP_COMMIT = ANCHOR_PARENT
R4_BOOTSTRAP_DOCUMENT_PATH = (
    "docs/experiments/"
    "uprime_odlrq_u2_u4_development_r4_guard_canonicalization_reentry_amendment_2026-07-14.md"
)
R4_BOOTSTRAP_DOCUMENT_BLOB = "384c203ebec46ec044b010bbd42e7543b6b163ac"
R4_SUCCESS_CLOSEOUT_PATH = (
    "docs/experiments/"
    "uprime_odlrq_u2_u4_development_r4_closeout_2026-07-14.md"
)

R5_AMENDMENT_PATH = (
    "docs/experiments/"
    "uprime_odlrq_u2_u4_development_r5_powershell51_decode_reentry_amendment_2026-07-14.md"
)
R5_AMENDMENT_BLOB = "a15d3e339d634f7dfe36e5c8b7a7595d39a2dbde"
R5_FAILURE_CLOSEOUT_PATH = (
    "docs/experiments/"
    "uprime_odlrq_u2_u4_development_r5_failure_closeout_2026-07-14.md"
)
R5_FAILURE_CLOSEOUT_BLOB = "fca1d61127ded045275d1c40fe4a55815d389304"
R5_SUCCESS_CLOSEOUT_PATH = (
    "docs/experiments/"
    "uprime_odlrq_u2_u4_development_r5_closeout_2026-07-14.md"
)

BOOTSTRAP_DOCUMENT_PATH = (
    "docs/experiments/"
    "uprime_odlrq_u2_u4_development_r6_static_scope_reentry_amendment_2026-07-14.md"
)
BOOTSTRAP_DOCUMENT_BLOB = "bde7e3456dcac6e699e983b84947d838bcee4d5d"
BOOTSTRAP_EVIDENCE_BLOBS = {
    R5_AMENDMENT_PATH: R5_AMENDMENT_BLOB,
    R5_FAILURE_CLOSEOUT_PATH: R5_FAILURE_CLOSEOUT_BLOB,
    BOOTSTRAP_DOCUMENT_PATH: BOOTSTRAP_DOCUMENT_BLOB,
}
BOOTSTRAP_EVIDENCE_BYTES = {
    R5_AMENDMENT_PATH: 18061,
    R5_FAILURE_CLOSEOUT_PATH: 7778,
    BOOTSTRAP_DOCUMENT_PATH: 18638,
}
assert set(BOOTSTRAP_EVIDENCE_BYTES) == set(BOOTSTRAP_EVIDENCE_BLOBS)
assert len(BOOTSTRAP_EVIDENCE_BLOBS) == 3

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
    "uprime_odlrq_u2_u4_development_r6_closeout_2026-07-14.md"
)
FAILURE_CLOSEOUT_PATH = (
    "docs/experiments/"
    "uprime_odlrq_u2_u4_development_r6_failure_closeout_2026-07-14.md"
)

FROZEN_REFS = {
    "bootstrap": "codex/uprime-u2-u4-development-r6-static-scope-bootstrap",
    "build": "codex/uprime-u2-u4-development-r6-build",
    "closeout": "codex/uprime-u2-u4-development-r6-closeout",
    "failure": "codex/uprime-u2-u4-development-r6-failure-closeout",
    "accepted": "codex/uprime-odlrq-plan",
}
STAGE_ORDER = ("E1", "E2", "ME0", "S0", "I0")
MAX_BUILD_COMMITS = 6
MAX_CORRECTIONS = 1

# The historical U24 construction epoch is immutable after accepted I0.  The
# portability phase is a separately governed descendant and must neither spend
# the old repair budget nor be reinterpreted as another old-epoch stage.
OLD_U24_ENDPOINT_COMMIT = "f1df8dd5d92706d907091e6add463fb6c9ca7130"
OLD_U24_ENDPOINT_TREE = "c15e50c683263b50c8ddf371938785d03353b1fc"
OLD_U24_ENDPOINT_PARENT = "2376aca8209c38a3a94dfa872334073d86dc4909"
OLD_U24_ENDPOINT_BLOBS = {
    "lean_rgc/evals/uprime_u2_u4_development.py":
        "32f68a477bbb2432a91cd463d49db658ff012258",
    "lean_rgc/odlrq/__init__.py":
        "7e08787436b385e50f071a44b9e26f31dea0c597",
    "lean_rgc/odlrq/certificates.py":
        "99e88abadaffc8c108953bcac663ffb135143317",
    IDENTITY_PATH: "ef4a56778c9734952257e56f91a0b93003bc577a",
    MANIFEST_PATH: "1663889c4732481eb6e2176df7c48ee396868216",
}
OLD_U24_CONTROL_BLOBS = {
    GUARD_PATH: "cd0a4fe0def1c5523e0c0b9fe023dde8fc0b09e7",
    RUNNER_PATH: "b79f1fa354cdddde2b2ae7b6efce8d9ac005be8b",
}
DELEGATED_PORTABILITY_MANIFEST_NODES = frozenset(
    u24_guard.PORTABILITY_DELEGATED_MANIFEST_NODES
)
WALL_SECONDS = {
    "B0": 60,
    "E0": 90,
    "E1": 120,
    "E2": 180,
    "ME0": 180,
    "S0": 300,
    "I0": 900,
    "EMIT": 900,
    "CLOSEOUT": 60,
}
IDENTITY_TEST_NAMES = (
    "test_u24_a0_anchor_authorities_and_nonexistence_are_frozen",
    "test_u24_b0_anchor_contiguous_budget_and_terminal_topology",
    "test_u24_denylist_static_scan_and_exact_runner_copy",
    "test_u24_autouse_guard_blocks_paths_process_network_and_dynamic_import",
    "test_u24_four_tier_public_wires_do_not_trust_tier_booleans",
)
E0_DIRECT_TEST_NAMES = (
    "test_e0_exact_coordinate_generator_matches_frozen_independent_oracle",
    "test_e0_roundtrip_permutation_cancellation_and_terminal_rows",
    "test_e0_wire_and_source_attacks_fail_closed",
    "test_e0_capability_types_and_later_tiers_are_rejected",
    "test_e0_public_surface_has_no_later_tier_tokens",
    "test_read_only_bundle_cache_is_quarantined_from_mutation_tests",
    "test_e0_scope_fields_fail_closed_at_every_wire_layer",
    "test_e0_signed64_preflight_rejects_before_authority",
    "test_e0_source_type_is_checked_before_attribute_access",
)

BOOTSTRAP_CONTROL_PATHS = {
    IDENTITY_PATH,
    GUARD_PATH,
    RUNNER_PATH,
}
BOOTSTRAP_PATHS = {*BOOTSTRAP_EVIDENCE_BLOBS, *BOOTSTRAP_CONTROL_PATHS}
BOOTSTRAP_CORRECTION_PATH_SETS = (
    frozenset({GUARD_PATH}),
    frozenset({IDENTITY_PATH, GUARD_PATH}),
    frozenset({RUNNER_PATH, GUARD_PATH}),
    frozenset({IDENTITY_PATH, GUARD_PATH, RUNNER_PATH}),
)
BASE_BLOBS = {
    "lean_rgc/odlrq/contracts.py":
        "eca7d55bc7c2a7a08fbdc75c3b589f1972cd258f",
    "lean_rgc/odlrq/quotient_generator.py":
        "6f2af348cfafe667955c08aa273c807b010a2698",
    "lean_rgc/odlrq/__init__.py":
        "6cb6e7904ad76cbf590df4e523d18e6fd24dcd04",
    "tests/test_odlrq_quotient_generator.py":
        "66da007454348ed62d7b346b719e2744ccb65fc5",
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
    R1_FAILURE_PATH: R1_FAILURE_BLOB,
    R2_A2_DOCUMENT_PATH: R2_A2_DOCUMENT_BLOB,
    R2_BOOTSTRAP_DOCUMENT_PATH: R2_BOOTSTRAP_DOCUMENT_BLOB,
    R3_BOOTSTRAP_DOCUMENT_PATH: R3_BOOTSTRAP_DOCUMENT_BLOB,
    R3_FAILURE_CLOSEOUT_PATH: R3_FAILURE_CLOSEOUT_BLOB,
    R4_BOOTSTRAP_DOCUMENT_PATH: R4_BOOTSTRAP_DOCUMENT_BLOB,
    ANCHOR_FAILURE_PATH: ANCHOR_FAILURE_BLOB,
}

STAGE_ALLOWLISTS = {
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
        MANIFEST_PATH,
    },
}
STAGE_MARKERS = {
    "E1": {"lean_rgc/odlrq/envelope.py"},
    "E2": {"lean_rgc/odlrq/selection.py"},
    "ME0": {"lean_rgc/odlrq/maxent.py"},
    "S0": {"lean_rgc/odlrq/similarity.py"},
    "I0": {"lean_rgc/evals/uprime_u2_u4_development.py"},
}
STAGE_MANIFEST_NODES = {
    "E1": {"test_odlrq_envelope.py"},
    "E2": {"test_odlrq_selection.py"},
    "ME0": {"test_odlrq_maxent.py"},
    "S0": {"test_odlrq_similarity.py"},
    "I0": set(),
}
E1_FROZEN_BYTES = {
    "lean_rgc/odlrq/quotient_generator.py": 153187,
    "lean_rgc/odlrq/envelope.py": 87121,
    "lean_rgc/odlrq/__init__.py": 13341,
    "tests/test_odlrq_quotient_generator.py": 59547,
    "tests/test_odlrq_envelope.py": 32675,
    MANIFEST_PATH: 8827,
}
E1_FROZEN_SHA256 = {
    "lean_rgc/odlrq/quotient_generator.py":
        "21030E4DD3C392D5EA2A9DEA1D5A8354F57AFE1301A59CFA6B0A2CDEE199EF16",
    "lean_rgc/odlrq/envelope.py":
        "13C4F4D97AFFB363A1EC484BDDD870AF9FB88B0C0796D6728AC774DE941D5496",
    "lean_rgc/odlrq/__init__.py":
        "F968B3BC4EB945811E88553F118856658CE45D476B94860B56D7F39DBE90D752",
    "tests/test_odlrq_quotient_generator.py":
        "4D1FAF8C725BB2EA9FAD01E83A330C578B1ABE01840EAD263E98D174A84CA7C0",
    "tests/test_odlrq_envelope.py":
        "90580302C24F99B8CAF1500EF013296E214D2206F6C936D781BAA8E8A64832D5",
    MANIFEST_PATH:
        "D955F797DFA2F4C0943F5F385F9301CED0A9D592BE19D459BF5EB2BEEB657854",
}
E1_FROZEN_BLOBS = {
    "lean_rgc/odlrq/quotient_generator.py":
        "1e1576ad1f51ebf667bc55d159048c0ae6587524",
    "lean_rgc/odlrq/envelope.py":
        "0618f603b86eba3c61c9fb2e15c4edaacce44a14",
    "lean_rgc/odlrq/__init__.py":
        "f97272d5de222fb555a78639d66eb89e77e63d86",
    "tests/test_odlrq_quotient_generator.py":
        "400f630e10ddbd98657fd1b142c6b202a8656c7d",
    "tests/test_odlrq_envelope.py":
        "66f9be1a3c5455b822b229fc2024b9c58b768fff",
    MANIFEST_PATH:
        "8bb7810cc49b56aff3d7b18020dab475644911a2",
}
assert set(E1_FROZEN_BYTES) == set(E1_FROZEN_SHA256) == set(E1_FROZEN_BLOBS)
assert set(E1_FROZEN_BLOBS) == STAGE_ALLOWLISTS["E1"]

ABSENT_AT_ANCHOR = tuple(
    sorted(
        {
            *BOOTSTRAP_EVIDENCE_BLOBS,
            R3_SUCCESS_CLOSEOUT_PATH,
            R4_SUCCESS_CLOSEOUT_PATH,
            R5_SUCCESS_CLOSEOUT_PATH,
            SUCCESS_CLOSEOUT_PATH,
            FAILURE_CLOSEOUT_PATH,
            "lean_rgc/odlrq/envelope.py",
            "lean_rgc/odlrq/maxent.py",
            "lean_rgc/odlrq/similarity.py",
            "lean_rgc/odlrq/selection.py",
            "lean_rgc/odlrq/certificates.py",
            "lean_rgc/odlrq/finite_e2.py",
            "lean_rgc/odlrq/finite_maxent.py",
            "lean_rgc/odlrq/finite_similarity.py",
            "lean_rgc/odlrq/finite_upper_stack.py",
            "lean_rgc/evals/uprime_u2_u4_development.py",
            "lean_rgc/evals/uprime_u24_upper_stack_portability.py",
            "tests/test_odlrq_envelope.py",
            "tests/test_odlrq_maxent.py",
            "tests/test_odlrq_similarity.py",
            "tests/test_odlrq_selection.py",
            "tests/test_uprime_u24_upper_stack_portability_identity.py",
            "tests/test_odlrq_finite_e2.py",
            "tests/test_odlrq_finite_maxent.py",
            "tests/test_odlrq_finite_similarity.py",
            "tests/test_odlrq_finite_upper_stack.py",
            "tests/test_uprime_u24_upper_stack_portability.py",
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
        "lean_rgc/odlrq/finite_e2.py",
        "lean_rgc/odlrq/finite_maxent.py",
        "lean_rgc/odlrq/finite_similarity.py",
        "lean_rgc/odlrq/finite_upper_stack.py",
        "lean_rgc/evals/uprime_u2_u4_development.py",
        "lean_rgc/evals/uprime_u24_upper_stack_portability.py",
        "tests/test_odlrq_quotient_generator.py",
        "tests/test_odlrq_envelope.py",
        "tests/test_odlrq_maxent.py",
        "tests/test_odlrq_similarity.py",
        "tests/test_odlrq_selection.py",
        "tests/test_uprime_u24_upper_stack_portability_identity.py",
        "tests/test_odlrq_finite_e2.py",
        "tests/test_odlrq_finite_maxent.py",
        "tests/test_odlrq_finite_similarity.py",
        "tests/test_odlrq_finite_upper_stack.py",
        "tests/test_uprime_u24_upper_stack_portability.py",
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
            *BOOTSTRAP_EVIDENCE_BLOBS,
            R3_SUCCESS_CLOSEOUT_PATH,
            R4_SUCCESS_CLOSEOUT_PATH,
            R5_SUCCESS_CLOSEOUT_PATH,
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


def _project_old_u24_epoch(control: Mapping[str, Any]) -> dict[str, Any]:
    """Return the exact historical attestation prefix ending at accepted I0."""

    projected = copy.deepcopy(dict(control))
    assert projected["is_shallow"] is False
    revisions = projected["revisions"]
    interval = projected["first_parent_after_a0"]
    assert type(revisions) is list and type(interval) is list
    endpoint_indices = [
        index
        for index, row in enumerate(revisions)
        if type(row) is dict and row.get("commit") == OLD_U24_ENDPOINT_COMMIT
    ]
    assert len(endpoint_indices) == 1
    endpoint_index = endpoint_indices[0]
    assert endpoint_index > 0
    assert interval[endpoint_index - 1] == OLD_U24_ENDPOINT_COMMIT
    endpoint = revisions[endpoint_index]
    assert endpoint["parents"] == [OLD_U24_ENDPOINT_PARENT]
    endpoint_blobs = endpoint["tree_blobs"]
    assert type(endpoint_blobs) is dict
    for path, expected in {
        **OLD_U24_ENDPOINT_BLOBS,
        **OLD_U24_CONTROL_BLOBS,
    }.items():
        assert endpoint_blobs[path] == expected

    projected["head"] = OLD_U24_ENDPOINT_COMMIT
    projected["first_parent_after_a0"] = interval[:endpoint_index]
    projected["revisions"] = revisions[: endpoint_index + 1]
    projected["status_paths"] = []
    projected["ci_setup_paths"] = []
    projected["worktree_blobs"] = copy.deepcopy(endpoint_blobs)
    return projected


# This snapshot is collected before the autouse semantic guard is installed.
# The registered runner supplies the same canonical object from its outer
# read-only control plane; direct CI constructs it locally before test setup.
RAW_CONTROL = u24_guard.load_control_plane_attestation(
    REPO_ROOT,
    a0_commit=ANCHOR_COMMIT,
    identity_path=IDENTITY_PATH,
    tracked_paths=TRACKED_PATHS,
    absent_at_a0=ABSENT_AT_ANCHOR,
)
CONTROL = _project_old_u24_epoch(RAW_CONTROL)


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
    assert value and len(value) == len(set(value))
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
            if candidate == "E1":
                assert changed == STAGE_ALLOWLISTS["E1"]
                blobs = _blobs(row)
                assert all(
                    blobs[path] == expected
                    for path, expected in E1_FROZEN_BLOBS.items()
                )
            completed.append(candidate)
            counts[candidate] = 1
            next_stage_index += 1
            last_stage = candidate
            continue

        assert last_stage is not None and last_stage != "E1"
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
    assert not interval or interval[0] != ANCHOR_COMMIT

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

    for previous, current in zip(revisions, revisions[1:]):
        assert current["parents"] == [previous["commit"]]
        _assert_tree_transition(previous, current)

    worktree = _worktree_blobs(control)
    dirty = _governed_dirty(control)
    head_blobs = _blobs(revisions[-1])
    for path in TRACKED_PATHS:
        if path not in dirty:
            assert worktree[path] == head_blobs[path]

    if not interval:
        assert control["head"] == ANCHOR_COMMIT
        assert dirty == BOOTSTRAP_PATHS
        for path, expected in BOOTSTRAP_EVIDENCE_BLOBS.items():
            assert worktree[path] == expected
        assert all(worktree[path] is not None for path in BOOTSTRAP_PATHS)
        assert all(
            worktree[path] != anchor_blobs[path]
            for path in BOOTSTRAP_CONTROL_PATHS
        )
        for path in TRACKED_PATHS:
            if path not in BOOTSTRAP_PATHS:
                assert worktree[path] == anchor_blobs[path]
        return {
            "completed": [],
            "counts": {name: 0 for name in STAGE_ORDER},
            "corrections": 0,
            "pending": "R6-bootstrap",
            "terminal": None,
        }

    bootstrap = revisions[1]
    assert bootstrap["parents"] == [ANCHOR_COMMIT]
    assert _changed(bootstrap) == BOOTSTRAP_PATHS
    bootstrap_blobs = _blobs(bootstrap)
    for path, expected in BOOTSTRAP_EVIDENCE_BLOBS.items():
        assert bootstrap_blobs[path] == expected
    for path in BOOTSTRAP_CONTROL_PATHS:
        assert bootstrap_blobs[path] is not None
        assert bootstrap_blobs[path] != ANCHOR_CONTROL_BLOBS[path]
    for path, expected in {**BASE_BLOBS, **AUTHORITY_BLOBS}.items():
        assert bootstrap_blobs[path] == expected
    assert bootstrap_blobs[WORKFLOW_PATH] == ANCHOR_WORKFLOW_BLOB

    remaining = revisions[2:]
    corrections = 0
    frozen_control_row = bootstrap
    if remaining and frozenset(_changed(remaining[0])) in BOOTSTRAP_CORRECTION_PATH_SETS:
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
        for path, expected in BOOTSTRAP_EVIDENCE_BLOBS.items():
            assert blobs[path] == expected
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
            and frozenset(dirty) in BOOTSTRAP_CORRECTION_PATH_SETS
        ):
            pending = "R6-bootstrap-correction"
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
                if next_stage == "E1":
                    assert dirty == STAGE_ALLOWLISTS["E1"]
                    assert all(
                        worktree[path] == expected
                        for path, expected in E1_FROZEN_BLOBS.items()
                    )
                pending = next_stage
            else:
                assert corrections == 0 and completed
                assert completed[-1] != "E1"
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
    for delegated in DELEGATED_PORTABILITY_MANIFEST_NODES:
        value.pop(delegated, None)
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
    assert u24_guard.PORTABILITY_AUTHORITY_PARENT == OLD_U24_ENDPOINT_COMMIT
    raw_authority_rows = [
        row
        for row in _revision_rows(RAW_CONTROL)
        if row.get("commit") == u24_guard.PORTABILITY_AUTHORITY_COMMIT
    ]
    assert len(raw_authority_rows) == 1
    assert raw_authority_rows[0]["parents"] == [OLD_U24_ENDPOINT_COMMIT]
    assert set(raw_authority_rows[0]["changed_paths"]) == {
        u24_guard.PORTABILITY_AUTHORITY_DOCUMENT_PATH,
        u24_guard.PORTABILITY_MATRIX_PATH,
    }
    portability_matrix = u24_guard._portability_matrix(  # type: ignore[attr-defined]
        REPO_ROOT
    )
    historical_noninputs = portability_matrix["historical_noninputs"]
    assert {
        name: historical_noninputs[name]
        for name, _value in u24_guard.PORTABILITY_HISTORICAL_NONINPUT_COMMITS
    } == dict(u24_guard.PORTABILITY_HISTORICAL_NONINPUT_COMMITS)
    assert historical_noninputs["forbidden_scientific_inputs"] == list(
        u24_guard.PORTABILITY_FORBIDDEN_SCIENTIFIC_INPUT_PATHS
    )
    active_table = u24_guard._ACTIVE_CANONICAL_DENYLIST  # type: ignore[attr-defined]
    table_type = u24_guard._CanonicalDenylistTable  # type: ignore[attr-defined]
    assert type(active_table) is table_type
    assert table_type.__dataclass_params__.frozen is True
    assert u24_guard._ACTIVE_POLICY_FINGERPRINT == (  # type: ignore[attr-defined]
        u24_guard.GuardMode.SEMANTIC,
        REPO_ROOT,
    )
    assert u24_guard._ACTIVE_CANONICAL_DENYLIST_CONTENT == (  # type: ignore[attr-defined]
        active_table.repo_root_key,
        active_table.canonical_repo_root,
        active_table.denylist_sha256,
        active_table.rows,
        active_table.emit_root,
        active_table.closeout_artifacts,
        active_table.portability_matrix,
        active_table.portability_matrix_sha256,
        active_table.scope_sha256,
    )
    assert active_table.repo_root_key == REPO_ROOT
    assert active_table.canonical_repo_root == u24_guard._canonical_path(  # type: ignore[attr-defined]
        REPO_ROOT, REPO_ROOT
    )
    assert active_table.denylist_sha256 == u24_guard.DENYLIST_SHA256
    assert type(active_table.rows) is tuple
    assert len(active_table.rows) == len(u24_guard.DENYLIST_ROWS)
    assert all(type(row) is tuple and len(row) == 2 for row in active_table.rows)
    assert type(active_table.closeout_artifacts) is tuple
    assert len(active_table.closeout_artifacts) == len(
        u24_guard.CLOSEOUT_ARTIFACTS
    )
    equivalent_table = u24_guard._build_canonical_denylist_table(  # type: ignore[attr-defined]
        REPO_ROOT
    )
    assert equivalent_table == active_table
    assert equivalent_table is not active_table
    windows_absolute = __import__("re").compile(r"^[A-Za-z]:[/\\]")

    def independently_canonicalize_constant(value: str) -> tuple[str, bool]:
        prefix = value.endswith("/")
        raw = value.rstrip("/")
        candidate = (
            raw
            if windows_absolute.match(raw.replace("\\", "/"))
            else str(REPO_ROOT / raw)
        )
        canonical = u24_guard._canonical_path(candidate, REPO_ROOT)  # type: ignore[attr-defined]
        assert canonical is not None
        return canonical, prefix

    assert active_table.rows == tuple(
        independently_canonicalize_constant(row)
        for row in u24_guard.DENYLIST_ROWS
    )
    assert active_table.emit_root == independently_canonicalize_constant(
        u24_guard.EMIT_ROOT
    )[0]
    assert active_table.closeout_artifacts == tuple(
        independently_canonicalize_constant(path)[0]
        for path in u24_guard.CLOSEOUT_ARTIFACTS
    )
    assert active_table.portability_matrix == independently_canonicalize_constant(
        u24_guard.PORTABILITY_MATRIX_PATH
    )[0]
    assert active_table.portability_matrix_sha256 == (
        u24_guard.PORTABILITY_MATRIX_RAW_SHA256
    )

    valid_table_fields = {
        "repo_root_key": active_table.repo_root_key,
        "canonical_repo_root": active_table.canonical_repo_root,
        "denylist_sha256": active_table.denylist_sha256,
        "rows": active_table.rows,
        "emit_root": active_table.emit_root,
        "closeout_artifacts": active_table.closeout_artifacts,
        "portability_matrix": active_table.portability_matrix,
        "portability_matrix_sha256": active_table.portability_matrix_sha256,
    }
    malformed_table_fields = (
        {**valid_table_fields, "repo_root_key": Path("relative")},
        {**valid_table_fields, "canonical_repo_root": ""},
        {**valid_table_fields, "denylist_sha256": "0" * 63},
        {**valid_table_fields, "rows": list(active_table.rows)},
        {
            **valid_table_fields,
            "rows": ([active_table.rows[0][0], True], *active_table.rows[1:]),
        },
        {**valid_table_fields, "emit_root": ""},
        {
            **valid_table_fields,
            "closeout_artifacts": list(active_table.closeout_artifacts),
        },
        {**valid_table_fields, "portability_matrix": ""},
        {**valid_table_fields, "portability_matrix_sha256": "0" * 63},
    )
    for malformed_fields in malformed_table_fields:
        with pytest.raises(TypeError):
            table_type(**malformed_fields)
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
    for path in BOOTSTRAP_EVIDENCE_BLOBS:
        assert blobs[path] is None
    for path, expected in BOOTSTRAP_EVIDENCE_BYTES.items():
        assert len((REPO_ROOT / path).read_bytes()) == expected
    assert ANCHOR_TREE == "3fbb08d6e3d496460e97ca60b83c7667ec518480"
    assert ACCEPTED_BASE_COMMIT == "fbc1259dc276265a8949aad86d9e15b87e4a6dff"
    assert ACCEPTED_BASE_PARENT == "773a4bae0ed6c88fe855d92a69a211f8834c688c"
    assert ACCEPTED_BASE_TREE == "e17b8dd85e6ee4bf299c6dcfc491deb7119253c5"
    assert R2_A2_COMMIT == "7c05c494ce79e84ffeb0d0c912ca3ba5f141f402"
    assert R2_BOOTSTRAP_COMMIT == "3970b4f505b842a76573329aaa526a1af08da7c4"
    assert R3_BOOTSTRAP_COMMIT == "4b0fa1ff2f701b1814a835d3b43f1251a92a3296"
    assert R4_BOOTSTRAP_COMMIT == ACCEPTED_BASE_COMMIT
    assert ORIGINAL_AUTHORITY_COMMIT == "14234e209229931c00615d4b171620ec6d1bbbf5"
    assert ORIGINAL_AUTHORITY_PARENT == "78c12549eb188610977842edbc38e2723d469ba4"
    assert blobs[ACCEPTED_FAILURE_PATH] == ACCEPTED_FAILURE_BLOB
    assert blobs[ORIGINAL_AUTHORITY_PATH] == ORIGINAL_AUTHORITY_BLOB
    assert CONTROL["absent_at_a0"] == {
        path: True for path in ABSENT_AT_ANCHOR
    }
    assert CONTROL["identity_additions"] == [HISTORICAL_IDENTITY_ADDITION]
    assert UNION_ALLOWLIST == EXPECTED_UNION_ALLOWLIST
    assert FROZEN_REFS == {
        "bootstrap": "codex/uprime-u2-u4-development-r6-static-scope-bootstrap",
        "build": "codex/uprime-u2-u4-development-r6-build",
        "closeout": "codex/uprime-u2-u4-development-r6-closeout",
        "failure": "codex/uprime-u2-u4-development-r6-failure-closeout",
        "accepted": "codex/uprime-odlrq-plan",
    }
    assert STAGE_ORDER == ("E1", "E2", "ME0", "S0", "I0")
    assert MAX_BUILD_COMMITS == 6 and MAX_CORRECTIONS == 1
    assert WALL_SECONDS == {
        "B0": 60,
        "E0": 90,
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
    actual_dirty = _governed_dirty(CONTROL)
    assert state["completed"] == list(
        STAGE_ORDER[: len(state["completed"])]
    )
    assert state["corrections"] in (0, 1)
    assert state["pending"] in {
        None,
        "R6-bootstrap",
        "R6-bootstrap-correction",
        *STAGE_ORDER,
        *(stage + "-correction" for stage in STAGE_ORDER),
    }
    if state["terminal"] is not None:
        assert not actual_dirty
        terminal_paths = _changed(state["terminal"])
        assert terminal_paths in (SUCCESS_TERMINAL_PATHS, FAILURE_TERMINAL_PATHS)
        if terminal_paths == SUCCESS_TERMINAL_PATHS:
            assert state["completed"] == list(STAGE_ORDER)
    elif state["pending"] == "R6-bootstrap":
        assert actual_dirty == BOOTSTRAP_PATHS
        assert state["completed"] == [] and state["corrections"] == 0
    elif state["pending"] == "R6-bootstrap-correction":
        assert frozenset(actual_dirty) in BOOTSTRAP_CORRECTION_PATH_SETS
        assert state["completed"] == [] and state["corrections"] == 0
    elif state["pending"] in STAGE_ORDER:
        stage = state["pending"]
        assert actual_dirty <= STAGE_ALLOWLISTS[stage]
        assert bool(actual_dirty & STAGE_MARKERS[stage])
    elif state["pending"] is not None:
        stage = state["pending"].removesuffix("-correction")
        assert state["corrections"] == 0 and state["completed"]
        assert stage == state["completed"][-1]
        assert actual_dirty <= STAGE_ALLOWLISTS[stage]
    else:
        assert not actual_dirty

    head_changed = _changed(_revision_rows(CONTROL)[-1])
    e1_worktree_must_be_exact = state["pending"] == "E1" or (
        state["terminal"] is None
        and state["pending"] is None
        and bool(state["completed"])
        and state["completed"][-1] == "E1"
        and head_changed == STAGE_ALLOWLISTS["E1"]
    )
    if e1_worktree_must_be_exact:
        for path in sorted(STAGE_ALLOWLISTS["E1"]):
            raw = (REPO_ROOT / path).read_bytes()
            assert len(raw) == E1_FROZEN_BYTES[path]
            assert __import__("hashlib").sha256(raw).hexdigest().upper() == (
                E1_FROZEN_SHA256[path]
            )
            assert _worktree_blobs(CONTROL)[path] == E1_FROZEN_BLOBS[path]

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

    def append_e1(source: Mapping[str, Any], commit: str) -> dict[str, Any]:
        return append_row(
            source,
            commit,
            set(STAGE_ALLOWLISTS["E1"]),
            E1_FROZEN_BLOBS,
        )

    actual_interval = CONTROL["first_parent_after_a0"]
    actual_rows = _revision_rows(CONTROL)
    bootstrap_source = (
        _blobs(actual_rows[1]) if actual_interval else _worktree_blobs(CONTROL)
    )
    pending_t0 = copy.deepcopy(CONTROL)
    pending_t0["head"] = ANCHOR_COMMIT
    pending_t0["first_parent_after_a0"] = []
    pending_t0["revisions"] = pending_t0["revisions"][:1]
    pending_t0["status_paths"] = sorted(BOOTSTRAP_PATHS)
    pending_t0["ci_setup_paths"] = []
    pending_t0["worktree_blobs"] = copy.deepcopy(
        pending_t0["revisions"][0]["tree_blobs"]
    )
    for path in BOOTSTRAP_PATHS:
        pending_t0["worktree_blobs"][path] = bootstrap_source[path]
    pending_bootstrap = _validate_epoch_topology(pending_t0)
    assert pending_bootstrap["pending"] == "R6-bootstrap"
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

    pending_e1 = copy.deepcopy(t0)
    pending_e1["status_paths"] = sorted(STAGE_ALLOWLISTS["E1"])
    for path, expected in E1_FROZEN_BLOBS.items():
        pending_e1["worktree_blobs"][path] = expected
    e1_pending_state = _validate_epoch_topology(pending_e1)
    assert e1_pending_state["completed"] == []
    assert e1_pending_state["pending"] == "E1"

    e1_commit = "20" * 20
    e1 = append_e1(t0, e1_commit)
    after_e1 = _validate_epoch_topology(e1)
    assert after_e1["completed"] == ["E1"]
    assert after_e1["counts"]["E1"] == 1

    def rejected(candidate: Mapping[str, Any]) -> None:
        with pytest.raises((AssertionError, KeyError, TypeError, ValueError)):
            _validate_epoch_topology(candidate)

    attacks: list[dict[str, Any]] = []

    missing_e1_path = append_row(
        t0,
        "21" * 20,
        set(STAGE_ALLOWLISTS["E1"]) - {MANIFEST_PATH},
        E1_FROZEN_BLOBS,
    )
    attacks.append(missing_e1_path)
    altered_e1_blob = append_e1(t0, "22" * 20)
    altered_e1_blob["revisions"][-1]["tree_blobs"][
        "lean_rgc/odlrq/envelope.py"
    ] = "00" * 20
    altered_e1_blob["worktree_blobs"]["lean_rgc/odlrq/envelope.py"] = "00" * 20
    attacks.append(altered_e1_blob)
    pending_missing_e1 = copy.deepcopy(pending_e1)
    pending_missing_e1["status_paths"].remove(MANIFEST_PATH)
    attacks.append(pending_missing_e1)
    pending_altered_e1 = copy.deepcopy(pending_e1)
    pending_altered_e1["worktree_blobs"]["lean_rgc/odlrq/envelope.py"] = "00" * 20
    attacks.append(pending_altered_e1)

    wrong_anchor_parent = copy.deepcopy(pending_t0)
    wrong_anchor_parent["revisions"][0]["parents"] = ["00" * 20]
    attacks.append(wrong_anchor_parent)
    changed_anchor_blob = copy.deepcopy(pending_t0)
    changed_anchor_blob["revisions"][0]["tree_blobs"][ANCHOR_FAILURE_PATH] = (
        "00" * 20
    )
    attacks.append(changed_anchor_blob)
    expanded_anchor_change = copy.deepcopy(pending_t0)
    expanded_anchor_change["revisions"][0]["changed_paths"].append(
        "lean_rgc/odlrq/quotient_generator.py"
    )
    attacks.append(expanded_anchor_change)

    clean_anchor_without_bootstrap = copy.deepcopy(pending_t0)
    clean_anchor_without_bootstrap["status_paths"] = []
    clean_anchor_without_bootstrap["worktree_blobs"] = copy.deepcopy(
        clean_anchor_without_bootstrap["revisions"][0]["tree_blobs"]
    )
    attacks.append(clean_anchor_without_bootstrap)

    wrong_t0_parent = copy.deepcopy(t0)
    wrong_t0_parent["revisions"][1]["parents"] = [ANCHOR_PARENT]
    attacks.append(wrong_t0_parent)
    merge_t0 = copy.deepcopy(t0)
    merge_t0["revisions"][1]["parents"].append("ee" * 20)
    attacks.append(merge_t0)

    inserted = copy.deepcopy(t0)
    inserted_row = copy.deepcopy(inserted["revisions"][0])
    inserted_row["commit"] = "11" * 20
    inserted_row["parents"] = [ANCHOR_COMMIT]
    inserted_row["changed_paths"] = ["lean_rgc/odlrq/quotient_generator.py"]
    inserted["revisions"][1]["parents"] = [inserted_row["commit"]]
    inserted["revisions"].insert(1, inserted_row)
    inserted["first_parent_after_a0"].insert(0, inserted_row["commit"])
    attacks.append(inserted)

    extra_t0_path = copy.deepcopy(t0)
    extra_t0_path["revisions"][1]["changed_paths"].append(MANIFEST_PATH)
    attacks.append(extra_t0_path)
    for index, evidence_path in enumerate(BOOTSTRAP_EVIDENCE_BLOBS):
        missing_dirty_evidence = copy.deepcopy(pending_t0)
        missing_dirty_evidence["status_paths"].remove(evidence_path)
        attacks.append(missing_dirty_evidence)
        missing_committed_evidence = copy.deepcopy(t0)
        missing_committed_evidence["revisions"][1]["changed_paths"].remove(
            evidence_path
        )
        attacks.append(missing_committed_evidence)
        changed_t0_evidence = copy.deepcopy(t0)
        changed_t0_evidence["revisions"][1]["tree_blobs"][evidence_path] = (
            f"{index + 1:02x}" * 20
        )
        changed_t0_evidence["worktree_blobs"][evidence_path] = (
            f"{index + 1:02x}" * 20
        )
        attacks.append(changed_t0_evidence)
    first_evidence, second_evidence = tuple(BOOTSTRAP_EVIDENCE_BLOBS)[:2]
    swapped_evidence = copy.deepcopy(t0)
    first_blob = swapped_evidence["revisions"][1]["tree_blobs"][first_evidence]
    second_blob = swapped_evidence["revisions"][1]["tree_blobs"][second_evidence]
    swapped_evidence["revisions"][1]["tree_blobs"][first_evidence] = second_blob
    swapped_evidence["revisions"][1]["tree_blobs"][second_evidence] = first_blob
    swapped_evidence["worktree_blobs"] = copy.deepcopy(
        swapped_evidence["revisions"][1]["tree_blobs"]
    )
    attacks.append(swapped_evidence)
    document_only_bootstrap = append_row(
        pending_t0, "12" * 20, set(BOOTSTRAP_EVIDENCE_BLOBS)
    )
    attacks.append(document_only_bootstrap)
    control_only_bootstrap = append_row(
        pending_t0, "13" * 20, BOOTSTRAP_CONTROL_PATHS
    )
    attacks.append(control_only_bootstrap)
    changed_e0_base = copy.deepcopy(e1)
    changed_e0_base["revisions"][-1]["tree_blobs"][
        "lean_rgc/odlrq/contracts.py"
    ] = "00" * 20
    changed_e0_base["worktree_blobs"]["lean_rgc/odlrq/contracts.py"] = "00" * 20
    attacks.append(changed_e0_base)
    unregistered_dirty = copy.deepcopy(t0)
    unregistered_dirty["status_paths"] = ["unregistered-r6-path.txt"]
    attacks.append(unregistered_dirty)

    success_before_bootstrap = append_row(
        pending_t0, "31" * 20, SUCCESS_TERMINAL_PATHS
    )
    attacks.append(success_before_bootstrap)
    failure_before_bootstrap = append_row(
        pending_t0, "32" * 20, FAILURE_TERMINAL_PATHS
    )
    attacks.append(failure_before_bootstrap)
    second_bootstrap = append_row(t0, "33" * 20, BOOTSTRAP_PATHS)
    attacks.append(second_bootstrap)

    immediate_failure = append_row(t0, "34" * 20, FAILURE_TERMINAL_PATHS)
    immediate_failure_state = _validate_epoch_topology(immediate_failure)
    assert immediate_failure_state["completed"] == []
    assert immediate_failure_state["corrections"] == 0
    assert immediate_failure_state["pending"] is None
    assert immediate_failure_state["terminal"]["commit"] == "34" * 20
    attacks.append(append_row(t0, "36" * 20, SUCCESS_TERMINAL_PATHS))

    failure_terminal = append_row(
        e1, "37" * 20, FAILURE_TERMINAL_PATHS
    )
    after_e1_failure = _validate_epoch_topology(failure_terminal)
    assert after_e1_failure["completed"] == ["E1"]
    assert after_e1_failure["terminal"]["commit"] == "37" * 20
    post_terminal = append_row(
        failure_terminal,
        "38" * 20,
        {"lean_rgc/odlrq/envelope.py"},
    )
    attacks.append(post_terminal)

    skipped_e1 = append_row(
        t0, "41" * 20, {"lean_rgc/odlrq/selection.py"}
    )
    attacks.append(skipped_e1)
    cross_stage_correction = append_row(
        e1, "42" * 20, {"lean_rgc/odlrq/maxent.py"}
    )
    attacks.append(cross_stage_correction)
    correction_one = append_row(
        e1, "43" * 20, {"lean_rgc/odlrq/envelope.py"}
    )
    attacks.append(correction_one)
    correction_two = append_row(
        correction_one,
        "44" * 20,
        {"lean_rgc/odlrq/envelope.py"},
    )
    attacks.append(correction_two)
    e2_for_correction = append_row(
        e1, "67" * 20, STAGE_MARKERS["E2"]
    )
    e2_correction = append_row(
        e2_for_correction, "68" * 20, {"lean_rgc/odlrq/envelope.py"}
    )
    e2_correction_state = _validate_epoch_topology(e2_correction)
    assert e2_correction_state["completed"] == ["E1", "E2"]
    assert e2_correction_state["counts"]["E2"] == 2
    assert e2_correction_state["corrections"] == 1
    attacks.append(
        append_row(
            e2_correction, "69" * 20, {"lean_rgc/odlrq/envelope.py"}
        )
    )
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
    correction_failure = append_row(
        t0_correction, "65" * 20, FAILURE_TERMINAL_PATHS
    )
    correction_failure_state = _validate_epoch_topology(correction_failure)
    assert correction_failure_state["completed"] == []
    assert correction_failure_state["corrections"] == 1
    assert correction_failure_state["pending"] is None
    assert correction_failure_state["terminal"]["commit"] == "65" * 20
    attacks.append(
        append_row(
            correction_failure,
            "66" * 20,
            {"lean_rgc/odlrq/quotient_generator.py"},
        )
    )
    dirty_e1_after_correction = copy.deepcopy(t0_correction)
    dirty_e1_after_correction["status_paths"] = sorted(STAGE_ALLOWLISTS["E1"])
    for path, expected in E1_FROZEN_BLOBS.items():
        dirty_e1_after_correction["worktree_blobs"][path] = expected
    pending_e1_after_correction = _validate_epoch_topology(
        dirty_e1_after_correction
    )
    assert pending_e1_after_correction == {
        "completed": [],
        "counts": {name: 0 for name in STAGE_ORDER},
        "corrections": 1,
        "pending": "E1",
        "terminal": None,
    }
    t0_correction_e1 = append_e1(t0_correction, "46" * 20)
    committed_e1_after_correction = _validate_epoch_topology(t0_correction_e1)
    assert committed_e1_after_correction == {
        "completed": ["E1"],
        "counts": {
            name: (1 if name == "E1" else 0) for name in STAGE_ORDER
        },
        "corrections": 1,
        "pending": None,
        "terminal": None,
    }
    shared_quota_reuse = append_row(
        t0_correction_e1,
        "47" * 20,
        {"lean_rgc/odlrq/envelope.py"},
    )
    attacks.append(shared_quota_reuse)

    wrong_correction_parent = copy.deepcopy(t0_correction)
    wrong_correction_parent["revisions"][2]["parents"] = [ANCHOR_COMMIT]
    attacks.append(wrong_correction_parent)
    merge_correction = copy.deepcopy(t0_correction)
    merge_correction["revisions"][2]["parents"].append("dd" * 20)
    attacks.append(merge_correction)
    attacks.append(append_row(t0, "48" * 20, {IDENTITY_PATH}))
    attacks.append(append_row(t0, "49" * 20, {RUNNER_PATH}))
    non_immediate_correction = append_row(e1, "49" * 20, {GUARD_PATH})
    attacks.append(non_immediate_correction)
    for extra_path in (
        *BOOTSTRAP_EVIDENCE_BLOBS,
        R2_A2_DOCUMENT_PATH,
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
    for prefix_length, (index, stage) in enumerate(
        zip(range(50, 55), STAGE_ORDER[:-1]), start=1
    ):
        through_s0 = (
            append_e1(through_s0, f"{index:02d}" * 20)
            if stage == "E1"
            else append_row(
                through_s0,
                f"{index:02d}" * 20,
                STAGE_MARKERS[stage],
            )
        )
        prefix_failure = append_row(
            through_s0,
            f"{index + 30:02d}" * 20,
            FAILURE_TERMINAL_PATHS,
        )
        prefix_failure_state = _validate_epoch_topology(prefix_failure)
        assert prefix_failure_state["completed"] == list(
            STAGE_ORDER[:prefix_length]
        )
        assert prefix_failure_state["terminal"]["commit"] == f"{index + 30:02d}" * 20
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
    i0_failure = append_row(through_i0, "91" * 20, FAILURE_TERMINAL_PATHS)
    i0_failure_state = _validate_epoch_topology(i0_failure)
    assert i0_failure_state["completed"] == list(STAGE_ORDER)
    assert i0_failure_state["terminal"]["commit"] == "91" * 20
    successful_closeout = append_row(
        through_i0, "61" * 20, SUCCESS_TERMINAL_PATHS
    )
    successful_state = _validate_epoch_topology(successful_closeout)
    assert successful_state["completed"] == list(STAGE_ORDER)
    assert successful_state["corrections"] == 0
    assert successful_state["pending"] is None
    assert successful_state["terminal"]["commit"] == "61" * 20
    attacks.append(
        append_row(
            successful_closeout,
            "62" * 20,
            {"lean_rgc/odlrq/quotient_generator.py"},
        )
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
    wrong_head["head"] = "00" * 20
    attacks.append(wrong_head)
    omitted_interval = copy.deepcopy(t0)
    omitted_interval["first_parent_after_a0"] = []
    attacks.append(omitted_interval)
    duplicate_revision = copy.deepcopy(t0)
    duplicate_revision["revisions"].append(
        copy.deepcopy(duplicate_revision["revisions"][1])
    )
    attacks.append(duplicate_revision)
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
        'B0 = 60; E0 = 90; E1 = 120; E2 = 180; ME0 = 180',
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
        'semantic lane requires accepted branch activation',
        'accepted branch skips or mutates a semantic stage',
        'accepted branch has not completed the prior semantic stages',
        'accepted branch is outside the registered R6 epoch',
        'the shared R6 correction budget is already spent',
        'E1 is an exact import and cannot be corrected',
        'E1 paths or Git blobs differ from the frozen import',
        'accepted E1 history differs from the frozen import',
        'E1 worktree bytes differ from the frozen import',
        'E1 worktree Git blob differs from the frozen import',
        '$ExpectedGuardCoreSha256 = "',
        'guard canonical core differs from the runner binding',
        'B0/E0 identity module is marked, hidden, or plugin-modified',
        'E0 test module is marked, hidden, or plugin-modified',
        'E0 runtime function is not its frozen source definition',
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
    e0_branch = 'if lane == "E0":'
    assert bootstrap.count(e0_branch) == 2
    assert bootstrap.index("guard.install_guard(policy)") < bootstrap.index(e0_branch)
    assert bootstrap.index(e0_branch) < bootstrap.index("import pytest")
    assert bootstrap.count("\nimport types\n") == 1
    assert control.count('"refs/heads/codex/uprime-odlrq-plan"') == 1
    assert control.count('semantic_markers = {') == 1
    assert control.count('semantic_allowlists = {') == 1
    assert control.count('expected_prefix = list(semantic_order[:semantic_order.index(lane)])') == 1
    control_tree = __import__("ast").parse(control)
    literal_update_sets = [
        __import__("ast").literal_eval(node.args[0])
        for node in __import__("ast").walk(control_tree)
        if isinstance(node, __import__("ast").Call)
        and isinstance(node.func, __import__("ast").Attribute)
        and node.func.attr == "update"
        and len(node.args) == 1
        and isinstance(node.args[0], __import__("ast").Set)
    ]
    assert literal_update_sets == [set(BOOTSTRAP_EVIDENCE_BLOBS)]
    control_literals = {}
    for node in control_tree.body:
        if (
            isinstance(node, __import__("ast").Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], __import__("ast").Name)
            and node.targets[0].id in {
                "e1_frozen_blobs",
                "semantic_markers",
                "semantic_allowlists",
            }
        ):
            control_literals[node.targets[0].id] = __import__("ast").literal_eval(
                node.value
            )
    assert control_literals == {
        "e1_frozen_blobs": E1_FROZEN_BLOBS,
        "semantic_markers": {
            stage: next(iter(STAGE_MARKERS[stage])) for stage in STAGE_ORDER
        },
        "semantic_allowlists": STAGE_ALLOWLISTS,
    }
    e1_table_match = __import__("re").search(
        r"\$E1FrozenCanonicalJson = @'\n(.*?)\n'@",
        runner,
        __import__("re").S,
    )
    assert e1_table_match is not None
    e1_rows = json.loads(e1_table_match.group(1))
    assert type(e1_rows) is list and len(e1_rows) == 6
    assert [row["path"] for row in e1_rows] == list(E1_FROZEN_BLOBS)
    assert {row["path"] for row in e1_rows} == STAGE_ALLOWLISTS["E1"]
    for row in e1_rows:
        assert set(row) == {"blob", "bytes", "path", "sha256"}
        path = row["path"]
        assert row == {
            "blob": E1_FROZEN_BLOBS[path],
            "bytes": E1_FROZEN_BYTES[path],
            "path": path,
            "sha256": E1_FROZEN_SHA256[path],
        }
    decode_line = "$decodedE1Frozen = $E1FrozenCanonicalJson | ConvertFrom-Json"
    materialize_line = "$e1Frozen = @($decodedE1Frozen)"
    count_line = (
        'if ($e1Frozen.Count -ne 6) '
        '{ throw "E1 frozen byte table cardinality changed" }'
    )
    decode_block = (
        "    " + decode_line + "\n"
        "    " + materialize_line + "\n"
        "    " + count_line + "\n"
    )
    e1_outer_branch = 'if ($Lane -eq "E1") {'
    e1_outer_end = 'if ($Lane -in @("EMIT", "CLOSEOUT"))'
    assert runner.count(decode_line) == 1
    assert runner.count(materialize_line) == 1
    assert runner.count(count_line) == 1
    assert runner.count(decode_block) == 1
    assert runner.count("$E1FrozenCanonicalJson | ConvertFrom-Json") == 1
    assert runner.count("$decodedE1Frozen") == 2
    assert runner.count("$decodedE1Frozen =") == 1
    assert runner.count("$e1Frozen =") == 1
    assert runner.count(e1_outer_branch) == 1
    assert runner.count(e1_outer_end) == 1
    assert "$e1Frozen = @($E1FrozenCanonicalJson | ConvertFrom-Json)" not in runner
    assert runner.index(decode_line) < runner.index(materialize_line)
    assert runner.index(materialize_line) < runner.index(count_line)
    assert runner.index(count_line) < runner.index(e1_outer_branch)
    assert runner.index(e1_outer_branch) < runner.index(e1_outer_end)
    e1_outer_block = runner[
        runner.index(e1_outer_branch):runner.index(e1_outer_end)
    ]
    resolve_literal = (
        "Resolve-RegularFile -LiteralPath (Join-Path $repoRoot $relative)"
    )
    assert runner.count(resolve_literal) == 2
    assert e1_outer_block.count(resolve_literal) == 1
    for e1_unique_literal in (
        "foreach ($entry in $e1Frozen)",
        "Get-Item -LiteralPath $candidate -Force",
        "Get-Sha256 -LiteralPath $candidate",
        "hash-object $relative",
    ):
        assert runner.count(e1_unique_literal) == 1
        assert e1_outer_block.count(e1_unique_literal) == 1
    assert control.count('if lane in semantic_markers:') == 1
    assert bootstrap.count('"pytestmark" in identity_dict') == 1
    assert bootstrap.count('"pytestmark" in quotient_dict') == 1
    assert bootstrap.count('"pytestmark" in function_dict') == 2
    assert bootstrap.count('"pytest_plugins" in identity_dict') == 1
    assert bootstrap.count('"pytest_plugins" in quotient_dict') == 1
    assert bootstrap.count('function_dict.get("__test__", True) is not True') == 2
    assert bootstrap.count('"__signature__" in function_dict') == 2
    assert bootstrap.count('function_code.co_flags & 0x2AC') == 2
    assert bootstrap.count('safe_type(quotient) is not safe_module_type') == 1
    assert bootstrap.count('function_code != e0_expected_codes[name]') == 1
    assert bootstrap.count('function.__globals__ is not quotient_dict') == 1
    for name in IDENTITY_TEST_NAMES:
        assert bootstrap.count(name) == 1
    for name in E0_DIRECT_TEST_NAMES:
        assert bootstrap.count(name) == 1
    for literal in (
        "pytest.MonkeyPatch",
        "monkeypatch.undo()",
        'function_code.co_varnames[0] != "monkeypatch"',
        "if passed != 14:",
        'payload = {"artifact_sha256": None, "tests_passed": 14}',
    ):
        assert bootstrap.count(literal) >= 1
    assert bootstrap.index(e0_branch) < bootstrap.index("pytest.main")
    assert runner.count('if code == 0 and lane == "E1" and audit.passed != 48:') == 1
    assert runner.count(
        'E1 = @("tests/test_odlrq_quotient_generator.py", '
        '"tests/test_odlrq_envelope.py", '
        '"tests/test_uprime_u2_u4_development.py")'
    ) == 1
    assert runner.count(
        'E1 = @("lean_rgc/odlrq/envelope.py", "class FiberEnvelope")'
    ) == 1
    assert 'test_uprime_u2_u4_development.py")' not in control
    assert '-X "pycache_prefix=$controlPycachePrefix" $controlPath' in runner
    assert '@("-I", "-S", "-X", "pycache_prefix=$childPycachePrefix", $bootstrapPath)' in runner
    assert runner.count('pycache prefix is not empty') == 2
    assert "PYTHONPYCACHEPREFIX" not in runner
    assert runner.count(ANCHOR_COMMIT) == 3
    assert runner.count(ANCHOR_FAILURE_PATH) == 1
    assert runner.count(BOOTSTRAP_DOCUMENT_PATH) == 3
    assert runner.count(SUCCESS_CLOSEOUT_PATH) == 2
    assert runner.count(FAILURE_CLOSEOUT_PATH) == 2
    assert runner.count(R2_A2_DOCUMENT_PATH) == 1
    assert runner.count(R2_BOOTSTRAP_DOCUMENT_PATH) == 1
    assert runner.count(R3_BOOTSTRAP_DOCUMENT_PATH) == 1
    assert runner.count(R3_SUCCESS_CLOSEOUT_PATH) == 2
    assert runner.count(R3_FAILURE_CLOSEOUT_PATH) == 1
    assert runner.count(R4_BOOTSTRAP_DOCUMENT_PATH) == 1
    assert runner.count(R4_SUCCESS_CLOSEOUT_PATH) == 2
    assert runner.count(R5_AMENDMENT_PATH) == 3
    assert runner.count(R5_FAILURE_CLOSEOUT_PATH) == 3
    assert runner.count(R5_SUCCESS_CLOSEOUT_PATH) == 2
    assert runner.count(R1_FAILURE_PATH) == 1

    def git_blob_sha1(raw: bytes) -> str:
        digest = __import__("hashlib").sha1()
        digest.update(f"blob {len(raw)}\0".encode("ascii"))
        digest.update(raw)
        return digest.hexdigest()

    guard_raw = (REPO_ROOT / GUARD_PATH).read_bytes().replace(b"\r\n", b"\n")
    assert b"\r" not in guard_raw
    guard_source = guard_raw.decode("utf-8")
    anchor_identity_core_sha256 = (
        "63BA64835344CA03DBBA7D50B817C5E4BE2E4159655B9CB325D2D1C5D7A2A97E"
    )
    anchor_runner_sha256 = (
        "69D3F5E53FDC4ACEBC61D79AC53D4B318C35C9C2593A5B5C860205F7694F5C8E"
    )
    assert u24_guard.FROZEN_IDENTITY_CORE_SHA256 != anchor_identity_core_sha256
    assert u24_guard.FROZEN_RUNNER_SHA256 != anchor_runner_sha256
    binding_pattern = r'(?m)^FROZEN_RUNNER_SHA256 = "[0-9A-F]{64}"$'
    binding_matches = list(__import__("re").finditer(binding_pattern, guard_source))
    assert len(binding_matches) == 1
    guard_core_source = __import__("re").sub(
        binding_pattern,
        'FROZEN_RUNNER_SHA256 = "' + "0" * 64 + '"',
        guard_source,
    )
    guard_core_sha256 = __import__("hashlib").sha256(
        guard_core_source.encode("utf-8")
    ).hexdigest().upper()
    expected_core_match = __import__("re").search(
        r'^\$ExpectedGuardCoreSha256 = "([0-9A-F]{64})"$',
        runner,
        __import__("re").M,
    )
    assert expected_core_match is not None
    assert expected_core_match.group(1) == guard_core_sha256
    binding_only_change = __import__("re").sub(
        binding_pattern,
        'FROZEN_RUNNER_SHA256 = "' + "1" * 64 + '"',
        guard_source,
    )
    binding_only_core = __import__("re").sub(
        binding_pattern,
        'FROZEN_RUNNER_SHA256 = "' + "0" * 64 + '"',
        binding_only_change,
    )
    assert __import__("hashlib").sha256(
        binding_only_core.encode("utf-8")
    ).hexdigest().upper() == guard_core_sha256
    assert __import__("hashlib").sha256(
        (guard_core_source + "\n# mutation").encode("utf-8")
    ).hexdigest().upper() != guard_core_sha256
    assert git_blob_sha1(guard_raw) != ANCHOR_GUARD_BLOB

    runner_raw = (REPO_ROOT / RUNNER_PATH).read_bytes().replace(b"\r\n", b"\n")
    assert b"\r" not in runner_raw
    runner_sha256 = __import__("hashlib").sha256(runner_raw).hexdigest().upper()
    assert runner_sha256 == u24_guard.FROZEN_RUNNER_SHA256
    assert runner_sha256 != anchor_runner_sha256
    assert __import__("hashlib").sha256(
        runner_raw + b"\n# mutation"
    ).hexdigest().upper() != u24_guard.FROZEN_RUNNER_SHA256
    assert git_blob_sha1(runner_raw) != ANCHOR_RUNNER_BLOB

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
    assert identity_tests == list(IDENTITY_TEST_NAMES)

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
    table = u24_guard._ACTIVE_CANONICAL_DENYLIST  # type: ignore[attr-defined]
    assert table is not None
    emit = u24_guard.GuardPolicy(u24_guard.GuardMode.EMIT, REPO_ROOT)
    closeout = u24_guard.GuardPolicy(u24_guard.GuardMode.CLOSEOUT, REPO_ROOT)
    assert u24_guard._active_canonical_denylist(policy) is table  # type: ignore[attr-defined]
    assert u24_guard._active_canonical_denylist(emit) is table  # type: ignore[attr-defined]
    assert u24_guard._active_canonical_denylist(closeout) is table  # type: ignore[attr-defined]
    different_root = u24_guard.GuardPolicy(
        u24_guard.GuardMode.SEMANTIC, REPO_ROOT.parent
    )
    with pytest.raises(
        u24_guard.U24ResourceOrScopeBlocked,
        match=u24_guard.DENIAL_DISPOSITION,
    ):
        u24_guard._active_canonical_denylist(different_root)  # type: ignore[attr-defined]

    canonical_calls: list[object] = []
    original_canonical_path = u24_guard._canonical_path  # type: ignore[attr-defined]
    monkeypatch = pytest.MonkeyPatch()

    def counted_canonical_path(raw: object, root: Path) -> str | None:
        canonical_calls.append(raw)
        return original_canonical_path(raw, root)

    monkeypatch.setattr(u24_guard, "_canonical_path", counted_canonical_path)
    monkeypatch.setattr(
        u24_guard,
        "_canonical_row",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("installed denylist rows were recanonicalized")
        ),
    )
    try:
        candidate = REPO_ROOT / "pyproject.toml"
        u24_guard._check_path(policy, candidate, read=True)  # type: ignore[attr-defined]
        u24_guard._check_path(policy, candidate, read=True)  # type: ignore[attr-defined]
        assert canonical_calls == [str(candidate), str(candidate)]
    finally:
        monkeypatch.undo()

    class MutablePathLike:
        def __init__(self, values: tuple[str, str]) -> None:
            self.values = values
            self.calls = 0

        def __fspath__(self) -> str:
            value = self.values[min(self.calls, len(self.values) - 1)]
            self.calls += 1
            return value

    mutable = MutablePathLike(
        (
            str(REPO_ROOT / "pyproject.toml"),
            str(REPO_ROOT / u24_guard.DENYLIST_ROWS[0] / "retargeted.json"),
        )
    )
    u24_guard._check_path(policy, mutable, read=True)  # type: ignore[attr-defined]
    with pytest.raises(
        u24_guard.U24ResourceOrScopeBlocked,
        match=u24_guard.DENIAL_DISPOSITION,
    ):
        u24_guard._check_path(policy, mutable, read=True)  # type: ignore[attr-defined]
    assert mutable.calls == 2

    class WrapperFlipPathLike:
        def __init__(self, values: tuple[str, str]) -> None:
            self.values = values
            self.calls = 0

        def __fspath__(self) -> str:
            value = self.values[min(self.calls, len(self.values) - 1)]
            self.calls += 1
            return value

    safe_a = REPO_ROOT / "pyproject.toml"
    safe_b = REPO_ROOT / "README.md"
    expected_safe_a = os.stat(safe_a)
    expected_safe_b = os.stat(safe_b)
    assert expected_safe_a.st_size != expected_safe_b.st_size
    wrapper_flip = WrapperFlipPathLike((str(safe_a), str(safe_b)))
    observed_safe_a = os.stat(wrapper_flip)
    assert wrapper_flip.calls == 1
    assert observed_safe_a.st_size == expected_safe_a.st_size

    original_rows = table.rows

    class RowMutatingPathLike:
        def __fspath__(self) -> str:
            object.__setattr__(table, "rows", ())
            return str(
                REPO_ROOT
                / u24_guard.DENYLIST_ROWS[0]
                / "row-mutation-attack.json"
            )

    try:
        with pytest.raises(
            u24_guard.U24ResourceOrScopeBlocked,
            match=u24_guard.DENIAL_DISPOSITION,
        ):
            u24_guard._check_path(  # type: ignore[attr-defined]
                policy, RowMutatingPathLike(), read=True
            )
    finally:
        object.__setattr__(table, "rows", original_rows)
    u24_guard.require_active_guard(policy)

    original_mode = policy.mode

    class ModeMutatingPathLike:
        def __fspath__(self) -> str:
            object.__setattr__(policy, "mode", u24_guard.GuardMode.EMIT)
            return str(REPO_ROOT / u24_guard.CLOSEOUT_ARTIFACTS[0])

    try:
        with pytest.raises(
            u24_guard.U24ResourceOrScopeBlocked,
            match=u24_guard.DENIAL_DISPOSITION,
        ):
            u24_guard._check_path(  # type: ignore[attr-defined]
                policy, ModeMutatingPathLike(), write=True
            )
    finally:
        object.__setattr__(policy, "mode", original_mode)
    u24_guard.require_active_guard(policy)

    safe_canonical = original_canonical_path(
        REPO_ROOT / "pyproject.toml", REPO_ROOT
    )
    denied_canonical = table.rows[0][0].rstrip("/") + "/retargeted.json"
    retarget_calls = 0

    def retargeted_canonical_path(_raw: object, _root: Path) -> str:
        nonlocal retarget_calls
        retarget_calls += 1
        return safe_canonical if retarget_calls == 1 else denied_canonical

    retarget = pytest.MonkeyPatch()
    retarget.setattr(u24_guard, "_canonical_path", retargeted_canonical_path)
    try:
        operand = "same-lexical-operand"
        u24_guard._check_path(policy, operand, read=True)  # type: ignore[attr-defined]
        with pytest.raises(
            u24_guard.U24ResourceOrScopeBlocked,
            match=u24_guard.DENIAL_DISPOSITION,
        ):
            u24_guard._check_path(policy, operand, read=True)  # type: ignore[attr-defined]
        assert retarget_calls == 2
    finally:
        retarget.undo()

    relative_base = REPO_ROOT

    def based_canonical_path(raw: object, _root: Path) -> str | None:
        return original_canonical_path(relative_base / os.fspath(raw), REPO_ROOT)

    cwd_attack = pytest.MonkeyPatch()
    cwd_attack.setattr(u24_guard, "_canonical_path", based_canonical_path)
    try:
        spelling = "same-relative-name"
        u24_guard._check_path(policy, spelling, read=True)  # type: ignore[attr-defined]
        relative_base = REPO_ROOT / u24_guard.DENYLIST_ROWS[0]
        with pytest.raises(
            u24_guard.U24ResourceOrScopeBlocked,
            match=u24_guard.DENIAL_DISPOSITION,
        ):
            u24_guard._check_path(policy, spelling, read=True)  # type: ignore[attr-defined]
    finally:
        cwd_attack.undo()

    artifact = REPO_ROOT / u24_guard.CLOSEOUT_ARTIFACTS[0]
    emit_root = REPO_ROOT / u24_guard.EMIT_ROOT
    artifact_sibling = emit_root / "unregistered-eighth.json"
    prefix_confusable = Path(str(artifact) + ".extra")
    with pytest.raises(
        u24_guard.U24ResourceOrScopeBlocked,
        match=u24_guard.DENIAL_DISPOSITION,
    ):
        u24_guard._check_path(policy, artifact, read=True)  # type: ignore[attr-defined]
    u24_guard._check_path(emit, artifact, write=True)  # type: ignore[attr-defined]
    u24_guard._check_path(closeout, artifact, read=True)  # type: ignore[attr-defined]
    for attack_policy, flags in (
        (emit, {"read": True}),
        (emit, {"read": True, "write": True}),
        (emit, {"write": True, "enumerate_directory": True}),
        (emit, {"read": True, "enumerate_directory": True}),
        (closeout, {"write": True}),
        (closeout, {"read": True, "write": True}),
        (closeout, {"read": True, "enumerate_directory": True}),
    ):
        with pytest.raises(
            u24_guard.U24ResourceOrScopeBlocked,
            match=u24_guard.DENIAL_DISPOSITION,
        ):
            u24_guard._check_path(attack_policy, artifact, **flags)  # type: ignore[attr-defined]
    for attack_policy in (emit, closeout):
        for raw, flags in (
            (emit_root, {"read": True}),
            (artifact_sibling, {"write": True}),
            (prefix_confusable, {"write": True}),
        ):
            with pytest.raises(
                u24_guard.U24ResourceOrScopeBlocked,
                match=u24_guard.DENIAL_DISPOSITION,
            ):
                u24_guard._check_path(attack_policy, raw, **flags)  # type: ignore[attr-defined]

    table_shape_before = (
        table.rows,
        table.closeout_artifacts,
        tuple(table.__dict__),
        tuple(table.__dict__.values()),
    )
    for index in range(128):
        u24_guard._check_path(  # type: ignore[attr-defined]
            policy, REPO_ROOT / f"safe-caller-path-{index}", read=True
        )
    for descriptor in (0, 1, 2, 2**31 - 1):
        u24_guard._check_path(policy, descriptor, read=True)  # type: ignore[attr-defined]
    assert (
        table.rows,
        table.closeout_artifacts,
        tuple(table.__dict__),
        tuple(table.__dict__.values()),
    ) == table_shape_before

    assert Path.cwd().resolve() == REPO_ROOT
    canonical_root = table.canonical_repo_root.rstrip("/")
    for denied, prefix in table.rows:
        aliases = {denied, denied.swapcase()}
        if denied.startswith(canonical_root + "/"):
            aliases.add(os.path.relpath(denied, canonical_root))
        if os.name == "nt":
            aliases.add(denied.replace("/", "\\"))
        for alias in aliases:
            with pytest.raises(
                u24_guard.U24ResourceOrScopeBlocked,
                match=u24_guard.DENIAL_DISPOSITION,
            ):
                u24_guard._check_path(policy, alias, read=True)  # type: ignore[attr-defined]
        descendant = denied.rstrip("/") + "/descendant"
        descendant_denied = any(
            row_prefix
            and (
                descendant == row_path
                or descendant.startswith(row_path.rstrip("/") + "/")
            )
            for row_path, row_prefix in table.rows
        )
        if prefix or descendant_denied:
            with pytest.raises(
                u24_guard.U24ResourceOrScopeBlocked,
                match=u24_guard.DENIAL_DISPOSITION,
            ):
                u24_guard._check_path(  # type: ignore[attr-defined]
                    policy, descendant, read=True
                )
        else:
            u24_guard._check_path(policy, descendant, read=True)  # type: ignore[attr-defined]

    nested = u24_guard.install_guard(policy)
    assert nested._owns_installation is False
    assert u24_guard._ACTIVE_CANONICAL_DENYLIST is table  # type: ignore[attr-defined]
    nested.close()
    assert u24_guard._ACTIVE_CANONICAL_DENYLIST is table  # type: ignore[attr-defined]
    with pytest.raises(
        u24_guard.U24ResourceOrScopeBlocked,
        match=u24_guard.DENIAL_DISPOSITION,
    ):
        u24_guard.install_guard(emit)

    table_type = type(table)
    first_path, first_prefix = table.rows[0]
    corrupted_tables = (
        table_type(
            repo_root_key=table.repo_root_key,
            canonical_repo_root=table.canonical_repo_root,
            denylist_sha256="0" * 64,
            rows=table.rows,
            emit_root=table.emit_root,
            closeout_artifacts=table.closeout_artifacts,
            portability_matrix=table.portability_matrix,
            portability_matrix_sha256=table.portability_matrix_sha256,
        ),
        table_type(
            repo_root_key=table.repo_root_key,
            canonical_repo_root=table.canonical_repo_root,
            denylist_sha256=table.denylist_sha256,
            rows=tuple(reversed(table.rows)),
            emit_root=table.emit_root,
            closeout_artifacts=table.closeout_artifacts,
            portability_matrix=table.portability_matrix,
            portability_matrix_sha256=table.portability_matrix_sha256,
        ),
        table_type(
            repo_root_key=table.repo_root_key,
            canonical_repo_root=table.canonical_repo_root,
            denylist_sha256=table.denylist_sha256,
            rows=((first_path, not first_prefix), *table.rows[1:]),
            emit_root=table.emit_root,
            closeout_artifacts=table.closeout_artifacts,
            portability_matrix=table.portability_matrix,
            portability_matrix_sha256=table.portability_matrix_sha256,
        ),
        table_type(
            repo_root_key=table.repo_root_key,
            canonical_repo_root=table.canonical_repo_root + "/wrong-root",
            denylist_sha256=table.denylist_sha256,
            rows=table.rows,
            emit_root=table.emit_root,
            closeout_artifacts=table.closeout_artifacts,
            portability_matrix=table.portability_matrix,
            portability_matrix_sha256=table.portability_matrix_sha256,
        ),
        table_type(
            repo_root_key=table.repo_root_key,
            canonical_repo_root=table.canonical_repo_root,
            denylist_sha256=table.denylist_sha256,
            rows=table.rows,
            emit_root=table.emit_root + "/wrong-root",
            closeout_artifacts=table.closeout_artifacts,
            portability_matrix=table.portability_matrix,
            portability_matrix_sha256=table.portability_matrix_sha256,
        ),
        table_type(
            repo_root_key=table.repo_root_key,
            canonical_repo_root=table.canonical_repo_root,
            denylist_sha256=table.denylist_sha256,
            rows=table.rows,
            emit_root=table.emit_root,
            closeout_artifacts=tuple(reversed(table.closeout_artifacts)),
            portability_matrix=table.portability_matrix,
            portability_matrix_sha256=table.portability_matrix_sha256,
        ),
        table_type(
            repo_root_key=table.repo_root_key,
            canonical_repo_root=table.canonical_repo_root,
            denylist_sha256=table.denylist_sha256,
            rows=table.rows,
            emit_root=table.emit_root,
            closeout_artifacts=table.closeout_artifacts,
            portability_matrix=table.portability_matrix + "/wrong",
            portability_matrix_sha256=table.portability_matrix_sha256,
        ),
        table_type(
            repo_root_key=table.repo_root_key,
            canonical_repo_root=table.canonical_repo_root,
            denylist_sha256=table.denylist_sha256,
            rows=table.rows,
            emit_root=table.emit_root,
            closeout_artifacts=table.closeout_artifacts,
            portability_matrix=table.portability_matrix,
            portability_matrix_sha256="0" * 64,
        ),
    )
    for corrupted_table in corrupted_tables:
        u24_guard._ACTIVE_CANONICAL_DENYLIST = corrupted_table  # type: ignore[attr-defined]
        try:
            with pytest.raises(
                u24_guard.U24ResourceOrScopeBlocked,
                match=u24_guard.DENIAL_DISPOSITION,
            ):
                u24_guard._active_canonical_denylist(policy)  # type: ignore[attr-defined]
        finally:
            u24_guard._ACTIVE_CANONICAL_DENYLIST = table  # type: ignore[attr-defined]

    def fresh_equivalent_table() -> object:
        return table_type(
            repo_root_key=table.repo_root_key,
            canonical_repo_root=table.canonical_repo_root,
            denylist_sha256=table.denylist_sha256,
            rows=table.rows,
            emit_root=table.emit_root,
            closeout_artifacts=table.closeout_artifacts,
            portability_matrix=table.portability_matrix,
            portability_matrix_sha256=table.portability_matrix_sha256,
        )

    rollback = pytest.MonkeyPatch()
    rollback.setattr(u24_guard, "_ACTIVE_POLICY", None)
    rollback.setattr(u24_guard, "_ACTIVE_POLICY_FINGERPRINT", None)
    rollback.setattr(u24_guard, "_ACTIVE_PATCHES", None)
    rollback.setattr(u24_guard, "_ACTIVE_CANONICAL_DENYLIST", None)
    rollback.setattr(u24_guard, "_ACTIVE_CANONICAL_DENYLIST_CONTENT", None)
    rollback.setattr(
        u24_guard, "_ACTIVE_CANONICAL_DENYLIST_SCOPE_SHA256", None
    )
    rollback.setattr(u24_guard, "_ACTIVE_CANONICAL_DENYLIST_TOKEN", None)
    rollback.setattr(
        u24_guard, "_build_canonical_denylist_table", lambda _root: fresh_equivalent_table()
    )
    rollback.setattr(
        u24_guard,
        "_install_path_wrappers",
        lambda _policy, _patches: (_ for _ in ()).throw(
            RuntimeError("synthetic install failure")
        ),
    )
    try:
        with pytest.raises(RuntimeError, match="synthetic install failure"):
            u24_guard.install_guard(policy)
        assert u24_guard._ACTIVE_POLICY is None  # type: ignore[attr-defined]
        assert u24_guard._ACTIVE_POLICY_FINGERPRINT is None  # type: ignore[attr-defined]
        assert u24_guard._ACTIVE_PATCHES is None  # type: ignore[attr-defined]
        assert u24_guard._ACTIVE_CANONICAL_DENYLIST is None  # type: ignore[attr-defined]
        assert u24_guard._ACTIVE_CANONICAL_DENYLIST_CONTENT is None  # type: ignore[attr-defined]
        assert u24_guard._ACTIVE_CANONICAL_DENYLIST_SCOPE_SHA256 is None  # type: ignore[attr-defined]
        assert u24_guard._ACTIVE_CANONICAL_DENYLIST_TOKEN is None  # type: ignore[attr-defined]
    finally:
        rollback.undo()
    assert u24_guard._ACTIVE_CANONICAL_DENYLIST is table  # type: ignore[attr-defined]

    reinstall = pytest.MonkeyPatch()
    reinstall.setattr(u24_guard, "_ACTIVE_POLICY", None)
    reinstall.setattr(u24_guard, "_ACTIVE_POLICY_FINGERPRINT", None)
    reinstall.setattr(u24_guard, "_ACTIVE_PATCHES", None)
    reinstall.setattr(u24_guard, "_ACTIVE_CANONICAL_DENYLIST", None)
    reinstall.setattr(u24_guard, "_ACTIVE_CANONICAL_DENYLIST_CONTENT", None)
    reinstall.setattr(
        u24_guard, "_ACTIVE_CANONICAL_DENYLIST_SCOPE_SHA256", None
    )
    reinstall.setattr(u24_guard, "_ACTIVE_CANONICAL_DENYLIST_TOKEN", None)
    reinstall.setattr(
        u24_guard, "_build_canonical_denylist_table", lambda _root: fresh_equivalent_table()
    )
    reinstall.setattr(u24_guard, "_install_path_wrappers", lambda *_args: None)
    reinstall.setattr(u24_guard, "_install_capability_wrappers", lambda *_args: None)
    try:
        damaged_handle = u24_guard.install_guard(policy)
        u24_guard._ACTIVE_CANONICAL_DENYLIST = None  # type: ignore[attr-defined]
        with pytest.raises(RuntimeError, match="guard installation identity changed"):
            damaged_handle.close()
        assert u24_guard._ACTIVE_POLICY is None  # type: ignore[attr-defined]
        assert u24_guard._ACTIVE_POLICY_FINGERPRINT is None  # type: ignore[attr-defined]
        assert u24_guard._ACTIVE_PATCHES is None  # type: ignore[attr-defined]
        assert u24_guard._ACTIVE_CANONICAL_DENYLIST is None  # type: ignore[attr-defined]
        assert u24_guard._ACTIVE_CANONICAL_DENYLIST_CONTENT is None  # type: ignore[attr-defined]
        assert u24_guard._ACTIVE_CANONICAL_DENYLIST_SCOPE_SHA256 is None  # type: ignore[attr-defined]
        assert u24_guard._ACTIVE_CANONICAL_DENYLIST_TOKEN is None  # type: ignore[attr-defined]
        retry_handle = u24_guard.install_guard(policy)
        retry_table = u24_guard._ACTIVE_CANONICAL_DENYLIST  # type: ignore[attr-defined]
        assert retry_table == table and retry_table is not table
        retry_handle.close()
        assert u24_guard._ACTIVE_POLICY is None  # type: ignore[attr-defined]
        assert u24_guard._ACTIVE_POLICY_FINGERPRINT is None  # type: ignore[attr-defined]
        first_handle = u24_guard.install_guard(policy)
        first_table = u24_guard._ACTIVE_CANONICAL_DENYLIST  # type: ignore[attr-defined]
        first_handle.close()
        assert u24_guard._ACTIVE_CANONICAL_DENYLIST is None  # type: ignore[attr-defined]
        second_handle = u24_guard.install_guard(policy)
        second_table = u24_guard._ACTIVE_CANONICAL_DENYLIST  # type: ignore[attr-defined]
        assert second_table == first_table == table
        assert second_table is not first_table
        first_handle.close()
        assert u24_guard._ACTIVE_CANONICAL_DENYLIST is second_table  # type: ignore[attr-defined]
        u24_guard._ACTIVE_CANONICAL_DENYLIST = first_table  # type: ignore[attr-defined]
        try:
            with pytest.raises(
                u24_guard.U24ResourceOrScopeBlocked,
                match=u24_guard.DENIAL_DISPOSITION,
            ):
                u24_guard._active_canonical_denylist(policy)  # type: ignore[attr-defined]
        finally:
            u24_guard._ACTIVE_CANONICAL_DENYLIST = second_table  # type: ignore[attr-defined]
        second_handle.close()
        assert u24_guard._ACTIVE_POLICY is None  # type: ignore[attr-defined]
        assert u24_guard._ACTIVE_POLICY_FINGERPRINT is None  # type: ignore[attr-defined]
        assert u24_guard._ACTIVE_PATCHES is None  # type: ignore[attr-defined]
        assert u24_guard._ACTIVE_CANONICAL_DENYLIST is None  # type: ignore[attr-defined]
        assert u24_guard._ACTIVE_CANONICAL_DENYLIST_CONTENT is None  # type: ignore[attr-defined]
        assert u24_guard._ACTIVE_CANONICAL_DENYLIST_SCOPE_SHA256 is None  # type: ignore[attr-defined]
        assert u24_guard._ACTIVE_CANONICAL_DENYLIST_TOKEN is None  # type: ignore[attr-defined]
    finally:
        reinstall.undo()
    u24_guard.require_active_guard(policy)
    assert u24_guard._ACTIVE_CANONICAL_DENYLIST is table  # type: ignore[attr-defined]

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


def test_u24_i0_authority_bindings_and_unique_terminal_paths_are_exact():
    odlrq = __import__("lean_rgc.odlrq", fromlist=(
        "PipelineEvidenceTier", "PipelineDisposition", "TypedPipelineFactor",
        "NominalPipelineAddendum", "TypedPipelineBound",
        "construct_typed_pipeline_bound", "verify_typed_pipeline_bound"))
    development = __import__("lean_rgc.evals.uprime_u2_u4_development", fromlist=(
        "build_u24_i0_fixture", "build_u24_artifact_wires",
        "verify_u24_artifact_wires", "emit_u24_artifacts"))

    fixture = development.build_u24_i0_fixture()
    manifest = fixture.candidate_authority_manifest
    assert type(manifest) is dict
    assert tuple(manifest) == (
        "schema_version",
        "ordered_bindings",
        "full_runtime_manifest_sha256",
        "s0_runtime_manifest_sha256",
        "s0_authority_identity",
        "i0_activation_identity",
    )
    assert manifest["schema_version"] == "odlrq.i0.candidate-authority-manifest.v1"
    bindings = manifest["ordered_bindings"]
    assert type(bindings) is list and len(bindings) == 12
    binding_ids = tuple(row["binding_id"] for row in bindings)
    assert binding_ids == (
        "E0.pipeline_source_generator",
        "E0.pipeline_target_generator",
        "E1.accepted_qualification_envelope",
        "E2.m0_parent_envelope",
        "E2.p1_cocycle",
        "E2.p2_cocycle",
        "E2.return_memory",
        "E2.support_token",
        "ME0.nontrivial_orbit_windows_result",
        "S0.positive_core",
        "S0.predictive_core",
        "S0.full_similarity_certificate",
    )
    assert len(set(binding_ids)) == len(binding_ids)
    assert all(tuple(row) == (
        "schema_version", "binding_id", "semantic_stage_id",
        "producer_stage_id", "binding_role", "object_schema",
        "digest_domain", "object_sha256", "source_commit", "source_tree",
        "evidence_tier", "hard_eligible",
    ) for row in bindings)
    assert manifest["full_runtime_manifest_sha256"] == (
        "F20A2C1A6556EAAC5371C7438A5F588A3F7E5A76282E2F500614B2E43FF6C05A"
    )
    assert manifest["s0_runtime_manifest_sha256"] == (
        "88FE6E69BB6B0E7BFE2C1C6EB220F420ECA0BE25826D48A90BD318641F3E89C9"
    )
    assert manifest["s0_authority_identity"] == {
        "schema_version": "odlrq.i0.authority-identity.v1",
        "authority_commit_sha": "48e8aa4b2a50d93367027d3c924944c160ef806a",
        "authority_parent_sha": "28749bf2f0fc67bc55a24e9e07fc03ad6c66b98d",
        "authority_document_path": (
            "docs/experiments/uprime_odlrq_post_me0_s0_i0_authority_2026-07-17.md"
        ),
        "authority_document_blob_sha": "f137a5c4f8411e2b68d6c88d6a6d09683a766aa2",
        "authority_ci_run_id": "29557149691",
        "authority_ci_job_id": "87811636093",
    }
    assert manifest["i0_activation_identity"] == {
        "schema_version": "odlrq.i0.authority-identity.v1",
        "authority_commit_sha": "2e6d0b64a88877dd1f1bd87718186c3ac040c2a4",
        "authority_parent_sha": "2376aca8209c38a3a94dfa872334073d86dc4909",
        "authority_document_path": (
            "docs/experiments/uprime_odlrq_post_s0_i0_activation_2026-07-17.md"
        ),
        "authority_document_blob_sha": "a2e7642e132226e50f7f238a7c6fa708f8492ec9",
        "authority_ci_run_id": "29561412405",
        "authority_ci_job_id": "87824486788",
    }

    source_commit = "1" * 40
    source_tree = "2" * 40
    wires = development.build_u24_artifact_wires(
        fixture=fixture, source_commit=source_commit, source_tree=source_tree
    )
    names = tuple(name for name, raw in wires)
    assert names == (
        "envelope_core.json",
        "maxent_fixture.json",
        "local_tower.json",
        "global_measure.json",
        "level_transport.json",
        "similarity_certificate.json",
        "integrated_certificate.json",
    )
    assert len(set(names)) == 7
    assert all(type(raw) is bytes and raw for name, raw in wires)
    integrated = json.loads(dict(wires)["integrated_certificate.json"])
    assert integrated["source_commit"] == source_commit
    assert integrated["payload"]["candidate_manifest"] == manifest
    assert integrated["payload"]["disposition"] == "PASS"


def test_u24_i0_typed_pipeline_pass_recomputes_hard_and_nominal_channels():
    odlrq = __import__("lean_rgc.odlrq", fromlist=(
        "PipelineEvidenceTier", "PipelineDisposition", "TypedPipelineFactor",
        "NominalPipelineAddendum", "TypedPipelineBound",
        "construct_typed_pipeline_bound", "verify_typed_pipeline_bound"))
    development = __import__("lean_rgc.evals.uprime_u2_u4_development", fromlist=(
        "build_u24_i0_fixture", "build_u24_artifact_wires",
        "verify_u24_artifact_wires", "emit_u24_artifacts"))

    fixture = development.build_u24_i0_fixture()
    bound = fixture.pass_bound
    assert type(bound) is odlrq.TypedPipelineBound
    assert odlrq.verify_typed_pipeline_bound(
        bound=bound,
        expected_candidate_authority_manifest=fixture.candidate_authority_manifest,
    ) == bound
    rebuilt = odlrq.construct_typed_pipeline_bound(
        candidate_authority_manifest=fixture.candidate_authority_manifest,
        ordered_hard_factors=bound.ordered_hard_factors,
        initial_residual=bound.initial_residual,
        hard_threshold=bound.hard_threshold,
        nominal_addendum=bound.nominal_addendum,
    )
    assert rebuilt == bound
    wire = bound.to_dict()
    assert tuple(wire) == (
        "schema_version", "candidate_authority_manifest",
        "ordered_hard_factors", "initial_residual", "hard_bound",
        "hard_threshold", "nominal_addendum", "total_bound", "coverage",
        "disposition", "verification_report",
    )
    assert wire["schema_version"] == "odlrq.i0.typed-pipeline-bound.v1"
    assert wire["disposition"] == "PASS"
    assert wire["initial_residual"] == {
        "schema_version": "lean-rgc-odlrq-exact-rational-v1",
        "numerator": "1",
        "denominator": "16",
    }
    assert wire["hard_bound"] == {
        "schema_version": "lean-rgc-odlrq-exact-rational-v1",
        "numerator": "3",
        "denominator": "4",
    }
    assert wire["hard_threshold"] == wire["hard_bound"]
    assert wire["nominal_addendum"]["L"]["numerator"] == "1"
    assert wire["nominal_addendum"]["epsilon"] == {
        "schema_version": "lean-rgc-odlrq-exact-rational-v1",
        "numerator": "1",
        "denominator": "10",
    }
    assert wire["total_bound"] == {
        "schema_version": "odlrq.i0.typed-diagnostic-total.v1",
        "value": {
            "schema_version": "lean-rgc-odlrq-exact-rational-v1",
            "numerator": "17",
            "denominator": "20",
        },
        "evidence_tier": "NOMINAL_DIAGNOSTIC_ONLY",
        "hard_eligible": False,
    }
    report = wire["verification_report"]
    assert report["hard_factor_count"] == 4
    assert report["initial_term"]["numerator"] == "3"
    assert report["initial_term"]["denominator"] == "16"
    assert tuple(row["stage_id"] for row in report["propagated_epsilon_terms"]) == (
        "E0", "E1", "E2", "S0",
    )
    assert tuple(
        (row["downstream_L"]["numerator"], row["downstream_L"]["denominator"])
        for row in report["propagated_epsilon_terms"]
    ) == (("3", "1"), ("3", "2"), ("1", "1"), ("1", "1"))
    assert tuple(
        (row["contribution"]["numerator"], row["contribution"]["denominator"])
        for row in report["propagated_epsilon_terms"]
    ) == (("0", "1"), ("3", "16"), ("1", "4"), ("1", "8"))
    assert report["coverage_complete"] is True
    assert all(report[key] is True for key in (
        "tier_firewall_verified", "domain_chain_verified", "norm_chain_verified",
        "authority_manifest_verified", "disposition_verified",
    ))
    assert report["verification_disposition"] == (
        "CPU_SYNTHETIC_TYPED_PIPELINE_BOUND_VERIFIED"
    )


def test_u24_i0_fail_and_abstain_precedence_are_exact():
    odlrq = __import__("lean_rgc.odlrq", fromlist=(
        "PipelineEvidenceTier", "PipelineDisposition", "TypedPipelineFactor",
        "NominalPipelineAddendum", "TypedPipelineBound",
        "construct_typed_pipeline_bound", "verify_typed_pipeline_bound"))
    development = __import__("lean_rgc.evals.uprime_u2_u4_development", fromlist=(
        "build_u24_i0_fixture", "build_u24_artifact_wires",
        "verify_u24_artifact_wires", "emit_u24_artifacts"))

    fixture = development.build_u24_i0_fixture()
    failed = fixture.fail_bound
    abstained = fixture.abstain_bound
    for bound in (failed, abstained):
        assert odlrq.verify_typed_pipeline_bound(
            bound=bound,
            expected_candidate_authority_manifest=fixture.candidate_authority_manifest,
        ) == bound

    failed_wire = failed.to_dict()
    assert failed_wire["disposition"] == "FAIL_HARD_BOUND_EXCEEDED"
    assert failed_wire["hard_bound"]["numerator"] == "15"
    assert failed_wire["hard_bound"]["denominator"] == "16"
    assert failed_wire["total_bound"]["value"]["numerator"] == "83"
    assert failed_wire["total_bound"]["value"]["denominator"] == "80"
    failed_terms = failed_wire["verification_report"]["propagated_epsilon_terms"]
    assert failed_terms[1]["contribution"]["numerator"] == "3"
    assert failed_terms[1]["contribution"]["denominator"] == "8"

    abstained_wire = abstained.to_dict()
    assert abstained_wire["disposition"] == "ABSTAIN_INCOMPLETE_COVERAGE"
    assert abstained_wire["coverage"] == {
        "schema_version": "odlrq.i0.pipeline-coverage.v1",
        "covered_count": 3,
        "universe_count": 4,
        "coverage_scope": "S0_DECLARED_SIMILARITY_DOMAIN",
        "complete": False,
    }
    assert abstained_wire["hard_bound"] is None
    assert abstained_wire["nominal_addendum"] is None
    assert abstained_wire["total_bound"] is None
    abstained_report = abstained_wire["verification_report"]
    assert abstained_report["initial_term"] is None
    assert abstained_report["propagated_epsilon_terms"] == []
    assert abstained_report["recomputed_hard_bound"] is None
    assert abstained_report["recomputed_nominal_addendum"] is None
    assert abstained_report["recomputed_total_bound"] is None
    assert abstained_report["coverage_complete"] is False
    assert all(abstained_report[key] is True for key in (
        "tier_firewall_verified", "domain_chain_verified", "norm_chain_verified",
        "authority_manifest_verified", "disposition_verified",
    ))

    mixed_factors = list(failed.ordered_hard_factors)
    mixed_factors[-1] = abstained.ordered_hard_factors[-1]
    precedence = odlrq.construct_typed_pipeline_bound(
        candidate_authority_manifest=fixture.candidate_authority_manifest,
        ordered_hard_factors=tuple(mixed_factors),
        initial_residual=failed.initial_residual,
        hard_threshold=failed.hard_threshold,
        nominal_addendum=fixture.pass_bound.nominal_addendum,
    )
    assert precedence.disposition is odlrq.PipelineDisposition.ABSTAIN_INCOMPLETE_COVERAGE
    assert precedence.hard_bound is None
    assert precedence.nominal_addendum is None
    assert precedence.total_bound is None


def test_u24_i0_nominal_maxent_cannot_enter_or_scale_the_hard_channel():
    odlrq = __import__("lean_rgc.odlrq", fromlist=(
        "PipelineEvidenceTier", "PipelineDisposition", "TypedPipelineFactor",
        "NominalPipelineAddendum", "TypedPipelineBound",
        "construct_typed_pipeline_bound", "verify_typed_pipeline_bound"))
    development = __import__("lean_rgc.evals.uprime_u2_u4_development", fromlist=(
        "build_u24_i0_fixture", "build_u24_artifact_wires",
        "verify_u24_artifact_wires", "emit_u24_artifacts"))

    fixture = development.build_u24_i0_fixture()
    bound = fixture.pass_bound
    nominal = bound.nominal_addendum
    assert type(nominal) is odlrq.NominalPipelineAddendum
    nominal_wire = nominal.to_dict()
    assert nominal_wire["stage_id"] == "ME0"
    assert nominal_wire["evidence_tier"] == "NOMINAL_DIAGNOSTIC_ONLY"
    assert nominal_wire["hard_eligible"] is False
    assert nominal_wire["coverage"]["covered_count"] == 2
    assert nominal_wire["coverage"]["universe_count"] == 3
    assert nominal_wire["coverage"]["complete"] is False
    assert all(factor.stage_id != "ME0" for factor in bound.ordered_hard_factors)
    assert tuple(factor.stage_id for factor in bound.ordered_hard_factors) == (
        "E0", "E1", "E2", "S0",
    )
    assert bound.hard_bound.to_dict()["numerator"] == "3"
    assert bound.hard_bound.to_dict()["denominator"] == "4"

    scaled = copy.deepcopy(nominal_wire)
    scaled["L"] = odlrq.ExactRational(2).to_dict()
    with pytest.raises(odlrq.StrictContractError):
        scaled_nominal = odlrq.NominalPipelineAddendum.from_dict(scaled)
        odlrq.construct_typed_pipeline_bound(
            candidate_authority_manifest=fixture.candidate_authority_manifest,
            ordered_hard_factors=bound.ordered_hard_factors,
            initial_residual=bound.initial_residual,
            hard_threshold=bound.hard_threshold,
            nominal_addendum=scaled_nominal,
        )

    promoted = copy.deepcopy(nominal_wire)
    promoted["evidence_tier"] = "CERTIFIED_SYNTHETIC"
    promoted["hard_eligible"] = True
    with pytest.raises(odlrq.StrictContractError):
        promoted_nominal = odlrq.NominalPipelineAddendum.from_dict(promoted)
        odlrq.construct_typed_pipeline_bound(
            candidate_authority_manifest=fixture.candidate_authority_manifest,
            ordered_hard_factors=bound.ordered_hard_factors,
            initial_residual=bound.initial_residual,
            hard_threshold=bound.hard_threshold,
            nominal_addendum=promoted_nominal,
        )

    with pytest.raises(odlrq.StrictContractError):
        odlrq.construct_typed_pipeline_bound(
            candidate_authority_manifest=fixture.candidate_authority_manifest,
            ordered_hard_factors=(
                bound.ordered_hard_factors[0], nominal,
                *bound.ordered_hard_factors[2:],
            ),
            initial_residual=bound.initial_residual,
            hard_threshold=bound.hard_threshold,
            nominal_addendum=nominal,
        )

    contaminated = bound.ordered_hard_factors[-1].to_dict()
    contaminated["authority_bindings"] = ["ME0.nontrivial_orbit_windows_result"]
    with pytest.raises(odlrq.StrictContractError):
        contaminated_factor = odlrq.TypedPipelineFactor.from_dict(contaminated)
        odlrq.construct_typed_pipeline_bound(
            candidate_authority_manifest=fixture.candidate_authority_manifest,
            ordered_hard_factors=(*bound.ordered_hard_factors[:-1], contaminated_factor),
            initial_residual=bound.initial_residual,
            hard_threshold=bound.hard_threshold,
            nominal_addendum=nominal,
        )


def test_u24_i0_domains_norms_tiers_coverage_and_order_fail_closed():
    odlrq = __import__("lean_rgc.odlrq", fromlist=(
        "PipelineEvidenceTier", "PipelineDisposition", "TypedPipelineFactor",
        "NominalPipelineAddendum", "TypedPipelineBound",
        "construct_typed_pipeline_bound", "verify_typed_pipeline_bound"))
    development = __import__("lean_rgc.evals.uprime_u2_u4_development", fromlist=(
        "build_u24_i0_fixture", "build_u24_artifact_wires",
        "verify_u24_artifact_wires", "emit_u24_artifacts"))

    fixture = development.build_u24_i0_fixture()
    bound = fixture.pass_bound
    factor_wires = [factor.to_dict() for factor in bound.ordered_hard_factors]
    assert tuple(row["stage_id"] for row in factor_wires) == ("E0", "E1", "E2", "S0")
    assert tuple(row["domain_id"] for row in factor_wires) == (
        "u24.declared_finite_totalized_snapshot.v1",
        "u24.exact_quotient_coordinates.v1",
        "u24.positive_finite_fiber_envelope.v1",
        "u24.certified_finite_horizon_support_profile.v1",
    )
    assert tuple(row["codomain_id"] for row in factor_wires) == (
        "u24.exact_quotient_coordinates.v1",
        "u24.positive_finite_fiber_envelope.v1",
        "u24.certified_finite_horizon_support_profile.v1",
        "u24.certified_finite_level_similarity_profile.v1",
    )
    assert all(row["norm_id"] == "weighted_l1_exact_rational_v1" for row in factor_wires)
    assert tuple(row["evidence_tier"] for row in factor_wires) == (
        "EXACT", "EXACT_DECLARED_SYNTHETIC", "CERTIFIED_SYNTHETIC",
        "CERTIFIED_SYNTHETIC",
    )
    assert all(row["coverage"] == {
        "schema_version": "odlrq.i0.pipeline-coverage.v1",
        "covered_count": 4,
        "universe_count": 4,
        "coverage_scope": "I0_HARD_DOMAIN_CHAIN",
        "complete": True,
    } for row in factor_wires)

    mutations = (
        (1, "domain_id", "u24.declared_finite_totalized_snapshot.v1"),
        (2, "codomain_id", "u24.certified_finite_level_similarity_profile.v1"),
        (0, "norm_id", "binary64_l2"),
        (0, "evidence_tier", "EXACT_DECLARED_SYNTHETIC"),
        (3, "hard_eligible", False),
        (2, "L", True),
    )
    for index, field, value in mutations:
        mutated_wires = copy.deepcopy(factor_wires)
        mutated_wires[index][field] = value
        with pytest.raises(odlrq.StrictContractError):
            mutated_factors = tuple(
                odlrq.TypedPipelineFactor.from_dict(row) for row in mutated_wires
            )
            odlrq.construct_typed_pipeline_bound(
                candidate_authority_manifest=fixture.candidate_authority_manifest,
                ordered_hard_factors=mutated_factors,
                initial_residual=bound.initial_residual,
                hard_threshold=bound.hard_threshold,
                nominal_addendum=bound.nominal_addendum,
            )

    reduced_coverage = copy.deepcopy(factor_wires)
    reduced_coverage[3]["coverage"] = {
        "schema_version": "odlrq.i0.pipeline-coverage.v1",
        "covered_count": 1,
        "universe_count": 1,
        "coverage_scope": "I0_HARD_DOMAIN_CHAIN",
        "complete": True,
    }
    with pytest.raises(odlrq.StrictContractError):
        reduced_factors = tuple(
            odlrq.TypedPipelineFactor.from_dict(row) for row in reduced_coverage
        )
        odlrq.construct_typed_pipeline_bound(
            candidate_authority_manifest=fixture.candidate_authority_manifest,
            ordered_hard_factors=reduced_factors,
            initial_residual=bound.initial_residual,
            hard_threshold=bound.hard_threshold,
            nominal_addendum=bound.nominal_addendum,
        )

    with pytest.raises(odlrq.StrictContractError):
        odlrq.construct_typed_pipeline_bound(
            candidate_authority_manifest=fixture.candidate_authority_manifest,
            ordered_hard_factors=tuple(reversed(bound.ordered_hard_factors)),
            initial_residual=bound.initial_residual,
            hard_threshold=bound.hard_threshold,
            nominal_addendum=bound.nominal_addendum,
        )

    reordered_bindings = copy.deepcopy(factor_wires)
    reordered_bindings[1]["authority_bindings"].reverse()
    with pytest.raises(odlrq.StrictContractError):
        reordered_factors = tuple(
            odlrq.TypedPipelineFactor.from_dict(row) for row in reordered_bindings
        )
        odlrq.construct_typed_pipeline_bound(
            candidate_authority_manifest=fixture.candidate_authority_manifest,
            ordered_hard_factors=reordered_factors,
            initial_residual=bound.initial_residual,
            hard_threshold=bound.hard_threshold,
            nominal_addendum=bound.nominal_addendum,
        )

    unknown = copy.deepcopy(factor_wires[0])
    unknown["selector"] = "forbidden"
    with pytest.raises(odlrq.StrictContractError):
        odlrq.TypedPipelineFactor.from_dict(unknown)
    reordered = dict(reversed(tuple(factor_wires[0].items())))
    with pytest.raises(odlrq.StrictContractError):
        odlrq.TypedPipelineFactor.from_dict(reordered)


def test_u24_i0_live_e2_token_rebinds_and_candidate_manifest_rejects_splicing():
    odlrq = __import__("lean_rgc.odlrq", fromlist=(
        "PipelineEvidenceTier", "PipelineDisposition", "TypedPipelineFactor",
        "NominalPipelineAddendum", "TypedPipelineBound",
        "construct_typed_pipeline_bound", "verify_typed_pipeline_bound"))
    development = __import__("lean_rgc.evals.uprime_u2_u4_development", fromlist=(
        "build_u24_i0_fixture", "build_u24_artifact_wires",
        "verify_u24_artifact_wires", "emit_u24_artifacts"))

    fixture = development.build_u24_i0_fixture()
    reference = odlrq.bind_e2_support(fixture.e2_support_token)
    reference_wire = reference.to_dict()
    assert reference_wire["certified_support_token_sha256"] == (
        "D01170427E717D543D941740881C937EF5B535E357D67EEFDBF62773AFD6E660"
    )
    assert reference_wire["support_candidate_ids"] == ["c0", "c2"]
    token_wire = fixture.e2_support_token.to_dict()
    assert len(odlrq.canonical_contract_bytes(token_wire)) == 2185

    detached = fixture.candidate_authority_manifest
    detached["ordered_bindings"].reverse()
    fresh = fixture.candidate_authority_manifest
    assert fresh["ordered_bindings"][0]["binding_id"] == "E0.pipeline_source_generator"
    assert fresh["ordered_bindings"][-1]["binding_id"] == (
        "S0.full_similarity_certificate"
    )
    bound = fixture.pass_bound

    splices = []
    reordered = copy.deepcopy(fresh)
    reordered["ordered_bindings"].reverse()
    splices.append(reordered)
    missing = copy.deepcopy(fresh)
    del missing["ordered_bindings"][3]
    splices.append(missing)
    duplicated = copy.deepcopy(fresh)
    duplicated["ordered_bindings"][4] = copy.deepcopy(duplicated["ordered_bindings"][3])
    splices.append(duplicated)
    stale = copy.deepcopy(fresh)
    stale["ordered_bindings"][0]["source_commit"] = "0" * 40
    splices.append(stale)
    digest_splice = copy.deepcopy(fresh)
    digest_splice["ordered_bindings"][9]["object_sha256"] = (
        digest_splice["ordered_bindings"][10]["object_sha256"]
    )
    splices.append(digest_splice)
    sidecar_splice = copy.deepcopy(fresh)
    sidecar_splice["i0_activation_identity"] = copy.deepcopy(
        sidecar_splice["s0_authority_identity"]
    )
    splices.append(sidecar_splice)

    for spliced in splices:
        with pytest.raises(odlrq.StrictContractError):
            odlrq.construct_typed_pipeline_bound(
                candidate_authority_manifest=spliced,
                ordered_hard_factors=bound.ordered_hard_factors,
                initial_residual=bound.initial_residual,
                hard_threshold=bound.hard_threshold,
                nominal_addendum=bound.nominal_addendum,
            )
        with pytest.raises(odlrq.StrictContractError):
            odlrq.verify_typed_pipeline_bound(
                bound=bound, expected_candidate_authority_manifest=spliced
            )


def test_u24_i0_seven_artifact_schemas_orders_roundtrip_and_mutations_fail_closed():
    odlrq = __import__("lean_rgc.odlrq", fromlist=(
        "PipelineEvidenceTier", "PipelineDisposition", "TypedPipelineFactor",
        "NominalPipelineAddendum", "TypedPipelineBound",
        "construct_typed_pipeline_bound", "verify_typed_pipeline_bound"))
    development = __import__("lean_rgc.evals.uprime_u2_u4_development", fromlist=(
        "build_u24_i0_fixture", "build_u24_artifact_wires",
        "verify_u24_artifact_wires", "emit_u24_artifacts"))

    fixture = development.build_u24_i0_fixture()
    source_commit = "3" * 40
    source_tree = "4" * 40
    wires = development.build_u24_artifact_wires(
        fixture=fixture, source_commit=source_commit, source_tree=source_tree
    )
    assert development.verify_u24_artifact_wires(
        fixture=fixture,
        source_commit=source_commit,
        source_tree=source_tree,
        ordered_wires=wires,
    ) == wires
    names = tuple(name for name, raw in wires)
    schemas = (
        "u24_envelope_core_v1",
        "u24_maxent_fixture_v1",
        "u24_local_tower_v1",
        "u24_global_measure_v1",
        "u24_level_transport_v1",
        "u24_similarity_certificate_v1",
        "u24_integrated_certificate_v1",
    )
    payload_orders = (
        ("generator", "source_weights", "target_weights", "fiber_law",
         "transfer_layer", "completeness_witness", "inclusion_witness",
         "envelope", "verification_report"),
        ("support_token", "reference_law", "orbit_law", "statistics", "target",
         "kl_radius", "status", "probabilities", "residuals", "verification_report"),
        ("levels", "restrictions", "cauchy_majorant", "verification_report"),
        ("measures", "predictive_metric", "predictive_upper_bound",
         "positive_representation_distance", "safety_majorant", "verification_report"),
        ("radius_morphism", "word_depth_morphism", "granularity_morphism",
         "composition", "verification_report"),
        ("coverage", "target_residuals", "l_plus_token", "remainder_certificate",
         "verification_report"),
        ("candidate_manifest", "stages", "initial_residual", "hard_bound",
         "nominal_addendum", "total_bound", "coverage", "disposition",
         "verification_report"),
    )
    common_order = (
        "schema_version", "evidence_scope", "source_commit",
        "observation_frame_id", "reachable_domain_id", "response_vocabulary_id",
        "transition_semantics_id", "domain_scope", "runtime_identity_sha256",
        "operator_tier", "operator_sha256", "coverage", "censors",
        "disposition", "payload",
    )
    operator_tiers = (
        "EXACT_DECLARED_SYNTHETIC",
        "NOMINAL_DIAGNOSTIC_ONLY",
        "CERTIFIED_SYNTHETIC",
        "TYPED_MIXED_CONTAINER_NOT_HARD_ELIGIBLE",
        "CERTIFIED_SYNTHETIC",
        "TYPED_HARD_WITH_PREDICTIVE_SIDECAR",
        "TYPED_HARD_WITH_NOMINAL_DIAGNOSTIC",
    )
    total_bytes = 0
    for index, (name, raw) in enumerate(wires):
        assert name == names[index]
        assert type(raw) is bytes and len(raw) <= 1_048_576
        total_bytes += len(raw)
        obj = json.loads(raw)
        assert tuple(obj) == common_order
        assert obj["schema_version"] == schemas[index]
        assert obj["source_commit"] == source_commit
        assert obj["operator_tier"] == operator_tiers[index]
        assert obj["censors"] == []
        assert tuple(obj["payload"]) == payload_orders[index]
        assert json.dumps(
            obj, ensure_ascii=False, allow_nan=False, separators=(",", ":"),
            sort_keys=False,
        ).encode("utf-8") == raw
    assert total_bytes <= 7 * 1_048_576
    assert json.loads(wires[1][1])["coverage"] == {
        "schema_version": "u24_artifact_coverage_v1",
        "covered_count": 2,
        "universe_count": 3,
        "coverage_scope": "E2_CANDIDATE_UNIVERSE_SUPPORT",
        "complete": False,
    }
    assert json.loads(wires[-1][1])["payload"]["hard_bound"]["numerator"] == "3"

    forged_obj = json.loads(wires[0][1])
    forged_obj["operator_sha256"] = "0" * 64
    forged_raw = json.dumps(
        forged_obj, ensure_ascii=False, allow_nan=False, separators=(",", ":"),
        sort_keys=False,
    ).encode("utf-8")
    forged_wires = ((wires[0][0], forged_raw), *wires[1:])
    with pytest.raises(odlrq.StrictContractError):
        development.verify_u24_artifact_wires(
            fixture=fixture,
            source_commit=source_commit,
            source_tree=source_tree,
            ordered_wires=forged_wires,
        )

    reordered_obj = dict(reversed(tuple(json.loads(wires[0][1]).items())))
    reordered_raw = json.dumps(
        reordered_obj, ensure_ascii=False, allow_nan=False, separators=(",", ":"),
        sort_keys=False,
    ).encode("utf-8")
    reordered_wires = ((wires[0][0], reordered_raw), *wires[1:])
    with pytest.raises(odlrq.StrictContractError):
        development.verify_u24_artifact_wires(
            fixture=fixture,
            source_commit=source_commit,
            source_tree=source_tree,
            ordered_wires=reordered_wires,
        )

    with pytest.raises(odlrq.StrictContractError):
        development.verify_u24_artifact_wires(
            fixture=fixture,
            source_commit=source_commit,
            source_tree=source_tree,
            ordered_wires=tuple(reversed(wires)),
        )


def test_u24_i0_temporary_emission_is_exclusive_capped_and_source_commit_bound():
    odlrq = __import__("lean_rgc.odlrq", fromlist=(
        "PipelineEvidenceTier", "PipelineDisposition", "TypedPipelineFactor",
        "NominalPipelineAddendum", "TypedPipelineBound",
        "construct_typed_pipeline_bound", "verify_typed_pipeline_bound"))
    development = __import__("lean_rgc.evals.uprime_u2_u4_development", fromlist=(
        "build_u24_i0_fixture", "build_u24_artifact_wires",
        "verify_u24_artifact_wires", "emit_u24_artifacts"))

    fixture = development.build_u24_i0_fixture()
    source_commit = "5" * 40
    source_tree = "6" * 40
    wires = development.build_u24_artifact_wires(
        fixture=fixture, source_commit=source_commit, source_tree=source_tree
    )
    with tempfile.TemporaryDirectory() as directory:
        parent = Path(directory)
        destination = parent / "published"
        receipt_raw = development.emit_u24_artifacts(
            fixture=fixture,
            source_commit=source_commit,
            source_tree=source_tree,
            destination_root=destination,
        )
        assert type(receipt_raw) is bytes and len(receipt_raw) <= 4096
        receipt = json.loads(receipt_raw)
        assert tuple(receipt) == (
            "schema_version", "source_commit", "source_tree",
            "ordered_artifacts", "disposition",
        )
        assert receipt["schema_version"] == "u24_artifact_emission_receipt_v1"
        assert receipt["source_commit"] == source_commit
        assert receipt["source_tree"] == source_tree
        assert receipt["disposition"] == "CPU_SYNTHETIC_U2_U4_ARTIFACTS_EMITTED"
        assert {path.name for path in destination.iterdir()} == {
            name for name, raw in wires
        }
        for index, (name, raw) in enumerate(wires):
            assert (destination / name).read_bytes() == raw
            assert receipt["ordered_artifacts"][index][0] == name
            assert receipt["ordered_artifacts"][index][1] == len(raw)
            assert type(receipt["ordered_artifacts"][index][2]) is str
            assert len(receipt["ordered_artifacts"][index][2]) == 64
            assert receipt["ordered_artifacts"][index][2] == (
                receipt["ordered_artifacts"][index][2].upper()
            )

        with pytest.raises(odlrq.StrictContractError):
            development.emit_u24_artifacts(
                fixture=fixture,
                source_commit=source_commit,
                source_tree=source_tree,
                destination_root=destination,
            )
        assert all(".staging." not in path.name for path in parent.iterdir())

        invalid_destination = parent / "invalid"
        with pytest.raises(odlrq.StrictContractError):
            development.emit_u24_artifacts(
                fixture=fixture,
                source_commit="A" * 40,
                source_tree=source_tree,
                destination_root=invalid_destination,
            )
        assert not invalid_destination.exists()

    with pytest.raises(odlrq.StrictContractError):
        development.verify_u24_artifact_wires(
            fixture=fixture,
            source_commit="7" * 40,
            source_tree=source_tree,
            ordered_wires=wires,
        )
    oversized = ((wires[0][0], b"{" + b"x" * 1_048_576), *wires[1:])
    with pytest.raises(odlrq.StrictContractError):
        development.verify_u24_artifact_wires(
            fixture=fixture,
            source_commit=source_commit,
            source_tree=source_tree,
            ordered_wires=oversized,
        )


def test_u24_i0_public_surface_has_no_selector_protected_endpoint_or_safety_promotion():
    odlrq = __import__("lean_rgc.odlrq", fromlist=(
        "PipelineEvidenceTier", "PipelineDisposition", "TypedPipelineFactor",
        "NominalPipelineAddendum", "TypedPipelineBound",
        "construct_typed_pipeline_bound", "verify_typed_pipeline_bound"))
    development = __import__("lean_rgc.evals.uprime_u2_u4_development", fromlist=(
        "build_u24_i0_fixture", "build_u24_artifact_wires",
        "verify_u24_artifact_wires", "emit_u24_artifacts"))

    package_names = (
        "PipelineEvidenceTier",
        "PipelineDisposition",
        "TypedPipelineFactor",
        "NominalPipelineAddendum",
        "TypedPipelineBound",
        "construct_typed_pipeline_bound",
        "verify_typed_pipeline_bound",
    )
    module_names = (
        "build_u24_i0_fixture",
        "build_u24_artifact_wires",
        "verify_u24_artifact_wires",
        "emit_u24_artifacts",
    )
    assert tuple(vars(development)["__all__"]) == module_names
    assert all(vars(odlrq)[name] is not None for name in package_names)
    assert all(vars(development)[name] is not None for name in module_names)
    assert tuple(item.value for item in odlrq.PipelineEvidenceTier) == (
        "EXACT", "EXACT_DECLARED_SYNTHETIC", "CERTIFIED_SYNTHETIC",
        "NOMINAL_DIAGNOSTIC_ONLY",
    )
    assert tuple(item.value for item in odlrq.PipelineDisposition) == (
        "PASS", "FAIL_HARD_BOUND_EXCEEDED", "ABSTAIN_INCOMPLETE_COVERAGE",
    )

    construct_signature = inspect.signature(odlrq.construct_typed_pipeline_bound)
    verify_signature = inspect.signature(odlrq.verify_typed_pipeline_bound)
    assert tuple(construct_signature.parameters) == (
        "candidate_authority_manifest", "ordered_hard_factors", "initial_residual",
        "hard_threshold", "nominal_addendum",
    )
    assert tuple(verify_signature.parameters) == (
        "bound", "expected_candidate_authority_manifest",
    )
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        for parameter in construct_signature.parameters.values()
    )
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        for parameter in verify_signature.parameters.values()
    )
    assert tuple(inspect.signature(development.build_u24_i0_fixture).parameters) == ()
    assert tuple(inspect.signature(development.build_u24_artifact_wires).parameters) == (
        "fixture", "source_commit", "source_tree",
    )
    assert tuple(inspect.signature(development.verify_u24_artifact_wires).parameters) == (
        "fixture", "source_commit", "source_tree", "ordered_wires",
    )
    assert tuple(inspect.signature(development.emit_u24_artifacts).parameters) == (
        "fixture", "source_commit", "source_tree", "destination_root",
    )
    for name in (*package_names, *module_names):
        lowered = name.lower()
        assert "selector" not in lowered
        assert "protected" not in lowered
        assert "reserved" not in lowered
        assert "promote" not in lowered
        assert "safety" not in lowered

    fixture = development.build_u24_i0_fixture()
    verified = odlrq.verify_typed_pipeline_bound(
        bound=fixture.pass_bound,
        expected_candidate_authority_manifest=fixture.candidate_authority_manifest,
    )
    assert type(verified) is odlrq.TypedPipelineBound
    assert verified == fixture.pass_bound
    with pytest.raises(TypeError):
        odlrq.construct_typed_pipeline_bound(fixture.candidate_authority_manifest)
    with pytest.raises(TypeError):
        odlrq.verify_typed_pipeline_bound(fixture.pass_bound)
    with pytest.raises((AttributeError, TypeError)):
        setattr(fixture.pass_bound, "hard_bound", odlrq.ExactRational(0))
    with pytest.raises((AttributeError, TypeError)):
        setattr(fixture.pass_bound.ordered_hard_factors[0], "epsilon", odlrq.ExactRational(9))
    with pytest.raises(TypeError):
        odlrq.construct_typed_pipeline_bound(
            candidate_authority_manifest=fixture.candidate_authority_manifest,
            ordered_hard_factors=fixture.pass_bound.ordered_hard_factors,
            initial_residual=fixture.pass_bound.initial_residual,
            hard_threshold=fixture.pass_bound.hard_threshold,
            nominal_addendum=fixture.pass_bound.nominal_addendum,
            endpoint_selector="forbidden",
        )
# U24_I0_TEST_EXTENSION_END
