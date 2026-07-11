from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess

import pytest

from lean_rgc.lean import kernel_state_identity as identity_module
from lean_rgc.lean.kernel_rpc_client import (
    RawStateDelta,
    RawTargetBinding,
    StrictKernelRPCProtocolError,
    parse_apply_tactic_response,
    parse_discard_state_response,
    parse_strict_json_line,
    strict_apply_request_bytes,
    strict_discard_request_bytes,
    strip_replay_transport,
)
from lean_rgc.lean.kernel_state_identity import (
    StateIdentityKey,
    StrictIdentityError,
    canonical_json_bytes,
    debt_readout_from_identity,
    parse_canonical_json_bytes,
    state_identity_from_kernel_state,
)
from lean_rgc.odlrq.contracts import (
    ActionSymbol,
    BoundAction,
    CanonicalStateDelta,
    CapSemantics,
    Censor,
    CensorKind,
    DebtReadout,
    ExactKernelTransitionCore,
    FieldCoverage,
    FieldCoverageStatus,
    PremiseBinding,
    RawTransitionStatus,
    ReplayComparableResponse,
    ReplayStatus,
    ReplayVerification,
    StrictContractError,
    TargetSelector,
    TotalizedStatus,
    U05ProbeTransition,
    canonical_contract_bytes,
)


PLAN_COMMIT = "0da9ff3de91819778761fb087e85e6f83e4c9ea4"
PLAN_PARENT = "df38daea2139b67d9935408c82bfb3297efd9536"
PLAN_BLOBS = {
    "docs/experiments/"
    "uprime_odlrq_upper_stack_implementation_plan_and_u05_amendment_2026-07-11.md":
        "2b2355f49aef149c1a7b5493951fa10e4a254235",
    "lean_rgc/evals/uprime_rpc_litmus.py":
        "9f6d89c3109e8c98520137aee201e79d39858b23",
    "tests/test_uprime_rerun_license.py":
        "d7b95dbc22dc70a642161ffc8550df492840a4c4",
}

IMPLEMENTATION_ALLOWLIST = {
    "lean_rgc/native_lean/RGCKernelRPC.lean",
    "lean_rgc/lean/kernel_state_identity.py",
    "lean_rgc/lean/kernel_rpc_client.py",
    "lean_rgc/lean/native_worker.py",
    "lean_rgc/odlrq/__init__.py",
    "lean_rgc/odlrq/contracts.py",
    "lean_rgc/odlrq/rule_algebra.py",
    "lean_rgc/odlrq/reachable_chart.py",
    "lean_rgc/odlrq/hankel.py",
    "lean_rgc/evals/uprime_u05_kill_probes.py",
    "tests/test_v49_kernel_rpc_worker.py",
    "tests/test_uprime_u05_identity.py",
    "tests/test_uprime_u05_kill_probes.py",
    "tests/tier_manifest.json",
}

RESULT_PATHS = {
    "docs/experiments/uprime_odlrq_u05_execution_2026-07-11.md",
    "docs/experiments/artifacts/uprime_u05_20260711/u05_kill_probes.json",
    "lean_rgc/evals/uprime_rpc_litmus.py",
    "tests/test_uprime_rerun_license.py",
}


def _git(*args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", "--no-replace-objects", *args],
        check=check,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _raw_parents(commit: str) -> list[str]:
    raw = _git("cat-file", "-p", commit).stdout.decode("utf-8")
    headers = raw.split("\n\n", 1)[0].splitlines()
    return [line[7:] for line in headers if line.startswith("parent ")]


def test_first_implementation_commit_freezes_exact_plan_anchor_topology():
    """Seal A in full history, shallow CI, and the pre-commit worktree."""

    plan_available = (
        _git("cat-file", "-e", f"{PLAN_COMMIT}^{{commit}}", check=False).returncode
        == 0
    )
    head = _git("rev-parse", "HEAD").stdout.decode("ascii").strip()
    if plan_available:
        assert _raw_parents(PLAN_COMMIT) == [PLAN_PARENT]
        for path, expected_blob in PLAN_BLOBS.items():
            row = _git("ls-tree", PLAN_COMMIT, "--", path).stdout.decode(
                "utf-8"
            ).split()
            assert row == ["100644", "blob", expected_blob, path]

        parent_available = (
            _git("cat-file", "-e", f"{PLAN_PARENT}^{{commit}}", check=False).returncode
            == 0
        )
        if parent_available:
            changed = tuple(
                sorted(
                    _git(
                        "diff-tree",
                        "--no-commit-id",
                        "--name-only",
                        "--no-renames",
                        "-r",
                        PLAN_COMMIT,
                    )
                    .stdout.decode("utf-8")
                    .splitlines()
                )
            )
            assert changed == tuple(sorted(PLAN_BLOBS))
        else:
            assert (
                _git("rev-parse", "--is-shallow-repository")
                .stdout.decode("ascii")
                .strip()
                == "true"
            )

        if head == PLAN_COMMIT:
            # The first implementation test must run before it is committed.
            # Only its own path is required here; the other agents' allowlisted
            # files may be present in the same uncommitted implementation bundle.
            status = _git(
                "status", "--porcelain=v1", "--", "tests/test_uprime_u05_identity.py"
            ).stdout.decode("utf-8")
            assert status[:2] in {"??", "A ", "AM"}
        else:
            assert (
                _git(
                    "merge-base", "--is-ancestor", PLAN_COMMIT, head, check=False
                ).returncode
                == 0
            )
            additions = (
                _git(
                    "log",
                    "--diff-filter=A",
                    "--format=%H",
                    "--",
                    "tests/test_uprime_u05_identity.py",
                )
                .stdout.decode("ascii")
                .splitlines()
            )
            assert len(additions) == 1
            implementation_commit = additions[0]
            assert _raw_parents(implementation_commit) == [PLAN_COMMIT]
            changed = set(
                _git(
                    "diff-tree",
                    "--no-commit-id",
                    "--name-only",
                    "--no-renames",
                    "-r",
                    implementation_commit,
                )
                .stdout.decode("utf-8")
                .splitlines()
            )
            assert "tests/test_uprime_u05_identity.py" in changed
            assert changed <= IMPLEMENTATION_ALLOWLIST
            plan_path = next(iter(PLAN_BLOBS))
            plan_blob = _git(
                "rev-parse", f"{implementation_commit}:{plan_path}"
            ).stdout.decode("ascii").strip()
            assert plan_blob == PLAN_BLOBS[plan_path]

            interval_head = head
            head_changed = set(
                _git(
                    "diff-tree",
                    "--no-commit-id",
                    "--name-only",
                    "--no-renames",
                    "-r",
                    head,
                )
                .stdout.decode("utf-8")
                .splitlines()
            )
            if head_changed == RESULT_PATHS:
                result_parents = _raw_parents(head)
                assert len(result_parents) == 1
                interval_head = result_parents[0]

            commits = (
                _git(
                    "rev-list",
                    "--first-parent",
                    "--reverse",
                    f"{PLAN_COMMIT}..{interval_head}",
                )
                .stdout.decode("ascii")
                .splitlines()
            )
            assert 1 <= len(commits) <= 4
            previous = PLAN_COMMIT
            for commit in commits:
                assert _raw_parents(commit) == [previous]
                changed = set(
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
                assert changed and changed <= IMPLEMENTATION_ALLOWLIST
                assert (
                    _git("rev-parse", f"{commit}:{plan_path}")
                    .stdout.decode("ascii")
                    .strip()
                    == PLAN_BLOBS[plan_path]
                )
                previous = commit
    else:
        assert (
            _git("rev-parse", "--is-shallow-repository")
            .stdout.decode("ascii")
            .strip()
            == "true"
        )
        # A shallow descendant cannot prove the missing parent edge, but it can
        # and must retain every exact anchored blob in its current tree.
        for path, expected_blob in PLAN_BLOBS.items():
            actual = _git("rev-parse", f"HEAD:{path}").stdout.decode("ascii").strip()
            assert actual == expected_blob


def _expr(
    expr_id: str,
    kind: str,
    *,
    head: str,
    const_name: str | None = None,
    levels: list[str] | None = None,
    binder_info: str | None = None,
    children: list[str] | None = None,
    free_fvars: list[str] | None = None,
    free_mvars: list[str] | None = None,
) -> dict[str, object]:
    return {
        "expr_id": expr_id,
        "kind": kind,
        "head": head,
        "const_name": const_name,
        "levels": levels or [],
        "binder_info": binder_info,
        "children": children or [],
        "type_expr_id": None,
        "free_fvars": free_fvars or [],
        "free_mvars": free_mvars or [],
        "pretty": f"pretty:{expr_id}",
        "raw_hash": f"raw:{expr_id}",
        "norm_hash": f"norm:{expr_id}",
    }


def _kernel_state_fixture(
    tag: str,
    *,
    universe_name: str,
    user_name: str,
    carrier_atoms: list[str] | None = None,
    target_constant: str = "Eq",
) -> dict[str, object]:
    m_goal = f"?m.goal.{tag}"
    m_history = f"?m.history.{tag}"
    f_local = f"fvar_local.{tag}"
    lctx = f"lctx_{tag}"
    e_target = f"expr_target_{tag}"
    e_eq = f"expr_eq_{tag}"
    e_arg = f"expr_arg_{tag}"
    e_sort = f"expr_sort_{tag}"
    e_history_value = f"expr_history_value_{tag}"
    nodes = [
        _expr(
            e_target,
            "app",
            head=target_constant,
            children=[e_eq, e_arg],
            free_fvars=[f_local],
        ),
        _expr(
            e_eq,
            "const",
            head=target_constant,
            const_name=target_constant,
            levels=[universe_name],
        ),
        _expr(e_arg, "fvar", head=f_local, free_fvars=[f_local]),
        _expr(e_sort, "sort", head="sort", levels=[universe_name]),
        _expr(
            e_history_value,
            "const",
            head="True.intro",
            const_name="True.intro",
        ),
    ]
    edges = [
        {"src": e_target, "dst": e_eq, "role": "fn"},
        {"src": e_target, "dst": e_arg, "role": "arg"},
    ]
    local_node = {
        "fvar_id": f_local,
        "user_name": user_name,
        "binder_kind": "default",
        "local_decl_kind": "default",
        "type_expr_id": e_sort,
        "value_expr_id": None,
        "is_implementation_detail": False,
        "is_instance": False,
        "depends_on_fvars": [],
        "depends_on_mvars": [],
        "raw_hash": f"local-raw-{tag}",
        "norm_hash": f"local-norm-{tag}",
    }
    goal_mvar = {
        "mvar_id": m_goal,
        "user_name": f"goal_{tag}",
        "type_text": f"{user_name} = {user_name}",
        "depends_on": [],
        "type_expr_id": e_target,
        "local_context_fvars": [f_local],
        "assigned": False,
        "assignment_expr_id": None,
        "kind": "natural",
        "dependencies_mvars": [],
        "dependencies_fvars": [f_local],
        "raw_hash": f"goal-raw-{tag}",
        "norm_hash": f"goal-norm-{tag}",
    }
    unreachable_history = {
        "mvar_id": m_history,
        "user_name": f"historical_{tag}",
        "type_text": "",
        "depends_on": [],
        "type_expr_id": e_sort,
        "local_context_fvars": [],
        "assigned": True,
        "assignment_expr_id": e_history_value,
        "kind": "natural",
        "dependencies_mvars": [],
        "dependencies_fvars": [],
        "raw_hash": f"history-raw-{tag}",
        "norm_hash": f"history-norm-{tag}",
    }
    return {
        "schema_version": "lean-rgc-kernel-state-v3",
        "extraction_backend": "lean_kernel_rpc_in_memory_v1",
        "state_id": f"process_state_{tag}",
        "task_id": f"task_{tag}",
        "env_fingerprint": f"legacy_env_{tag}",
        "state_hash_raw": f"state_raw_{tag}",
        "state_hash_norm": f"state_norm_{tag}",
        "status": "open",
        "goals": [
            {
                "goal_id": "g0",
                "mvar_id": m_goal,
                "target_text": f"{user_name} = {user_name}",
                "target_expr_id": e_target,
                "target_head": target_constant,
                "relation": "=" if target_constant == "Eq" else "",
                "local_context_graph_id": lctx,
                "target_symbols": [user_name],
                "domain_tags": ["Eq"],
                "connective_counts": {
                    "forall": 0,
                    "exists": 0,
                    "and": 0,
                    "or": 0,
                    "imp": 0,
                    "eq": 1,
                },
                "carrier_atoms_readout": (
                    ["eq_goal"] if carrier_atoms is None else carrier_atoms
                ),
                "raw_hash": f"target-raw-{tag}",
                "norm_hash": f"target-norm-{tag}",
            }
        ],
        "expr_graph": {
            "schema_version": "lean-rgc-expr-graph-v1",
            "nodes": nodes,
            "edges": edges,
            "roots": [e_target],
            "source": "lean_kernel_rpc_expr_dag",
        },
        "local_contexts": [
            {
                "schema_version": "lean-rgc-local-context-graph-v1",
                "local_context_graph_id": lctx,
                "nodes": [local_node],
                "edges": [],
                "raw_hash": f"lctx-raw-{tag}",
                "norm_hash": f"lctx-norm-{tag}",
            }
        ],
        "local_context": {"nodes": [], "edges": [], "source": "see_local_contexts"},
        "metavars": [goal_mvar, unreachable_history],
        "typeclasses": [],
        "messages": [f"ignored-message-{tag}"],
        "options": {"maxHeartbeats": "20000"},
        "proof_prefix_hash": f"prefix-hash-{tag}",
        "proof_prefix": f"ignored prefix {tag}",
        "parent_state_id": f"ignored_parent_{tag}",
        "object_coverage": {
            "expr_ast": True,
            "local_decl_graph": True,
            "metavariable_graph": True,
            "typeclass_graph": True,
            "in_memory_state_id": True,
            "tactic_transition_api": True,
            "branch_rollback": True,
            "replay_certificate": True,
            "minimal_support": True,
            "source": "lean_kernel_rpc",
        },
        "minimal_support": {
            "schema_version": "lean-rgc-minimal-support-v1",
            "goals": [],
            "source": "lean_kernel_rpc_proof_term_v1",
        },
        "closed": False,
        "canonical_status": "kernel_structured_state_chart_not_canonical",
    }


ENVIRONMENT_DIGEST = "A" * 64
TYPE_DIGEST = "B" * 64


def _identity(tag: str, **kwargs: object) -> StateIdentityKey:
    return state_identity_from_kernel_state(
        _kernel_state_fixture(tag, **kwargs),
        environment_content_digest=ENVIRONMENT_DIGEST,
        baseline_semantic_options={"maxHeartbeats": "20000"},
    )


def test_path_alpha_universe_and_unreachable_history_normalize_by_first_occurrence():
    left = _identity("left", universe_name="?u.17", user_name="h")
    right_state = _kernel_state_fixture(
        "right",
        universe_name="?u.999",
        user_name="renamed",
        carrier_atoms=["legacy", "readout", "is", "not", "identity"],
    )
    right_state["expr_graph"]["nodes"].reverse()
    right_state["expr_graph"]["edges"].reverse()
    right_state["metavars"].reverse()
    right = state_identity_from_kernel_state(
        right_state,
        environment_content_digest=ENVIRONMENT_DIGEST,
        baseline_semantic_options={"maxHeartbeats": "20000"},
    )
    assert left == right
    assert left.index_sha256 == right.index_sha256
    assert left.canonical_bytes == right.canonical_bytes
    assert debt_readout_from_identity(left) == (1, 1, 0, 1, 4)
    signature = left.full_signature
    assert [row["id"] for row in signature["metavars"]] == ["m0"]
    assert [row["id"] for row in signature["expressions"]] == [
        "e0",
        "e1",
        "e2",
        "e3",
    ]
    assert "process_state" not in left.canonical_bytes.decode("utf-8")
    assert "history" not in left.canonical_bytes.decode("utf-8")
    assert "renamed" not in right.canonical_bytes.decode("utf-8")


def test_unreachable_raw_history_cannot_change_identity_or_debt():
    with_history = _kernel_state_fixture(
        "history", universe_name="?u.1", user_name="h"
    )
    without_history = copy.deepcopy(with_history)
    history_mvar = next(
        row for row in without_history["metavars"] if row["assigned"]
    )
    history_expr_id = history_mvar["assignment_expr_id"]
    without_history["metavars"] = [
        row for row in without_history["metavars"] if row is not history_mvar
    ]
    without_history["expr_graph"]["nodes"] = [
        row
        for row in without_history["expr_graph"]["nodes"]
        if row["expr_id"] != history_expr_id
    ]
    left = state_identity_from_kernel_state(
        with_history, environment_content_digest=ENVIRONMENT_DIGEST
    )
    right = state_identity_from_kernel_state(
        without_history, environment_content_digest=ENVIRONMENT_DIGEST
    )
    assert left == right
    assert debt_readout_from_identity(left) == debt_readout_from_identity(right)


@pytest.mark.parametrize("field_name,prefix", [("expressions", "e"), ("local_declarations", "f"), ("metavars", "m")])
def test_signature_rejects_appended_unreferenced_sequential_objects(
    field_name: str, prefix: str
):
    key = _identity("closure", universe_name="?u.1", user_name="h")
    signature = key.full_signature
    rows = signature[field_name]
    appended = copy.deepcopy(rows[-1])
    appended["id"] = f"{prefix}{len(rows)}"
    rows.append(appended)
    with pytest.raises(StrictIdentityError, match="first-occurrence closure"):
        StateIdentityKey.from_signature(signature)


@pytest.mark.parametrize(
    "section,row_index,field_name,reference",
    [
        ("expressions", 0, "free_fvars", "f0"),
        ("expressions", 0, "free_mvars", "m0"),
        ("local_declarations", 0, "depends_on_fvars", "f0"),
        ("local_declarations", 0, "depends_on_mvars", "m0"),
        ("metavars", 0, "local_context_fvars", "f0"),
        ("metavars", 0, "depends_on_mvars", "m0"),
        ("metavars", 0, "depends_on_fvars", "f0"),
    ],
)
def test_signature_rejects_duplicate_canonical_reference_arrays(
    section: str, row_index: int, field_name: str, reference: str
):
    key = _identity("duplicate_refs", universe_name="?u.1", user_name="h")
    signature = key.full_signature
    signature[section][row_index][field_name] = [reference, reference]
    with pytest.raises(StrictIdentityError, match="duplicate canonical references"):
        StateIdentityKey.from_signature(signature)


def test_structured_universe_sharing_is_preserved_not_flattened():
    shared = _kernel_state_fixture("shared", universe_name="?u.1", user_name="h")
    split = _kernel_state_fixture("split", universe_name="?u.9", user_name="x")
    # The target constant and local declaration sort use distinct universe
    # metavariables in this state, rather than one alpha-renamed shared level.
    sort_node = next(
        row for row in split["expr_graph"]["nodes"] if row["kind"] == "sort"
    )
    sort_node["levels"] = ["?u.10"]
    shared_key = state_identity_from_kernel_state(
        shared, environment_content_digest=ENVIRONMENT_DIGEST
    )
    split_key = state_identity_from_kernel_state(
        split, environment_content_digest=ENVIRONMENT_DIGEST
    )
    assert shared_key != split_key


def test_different_observation_response_is_not_same_identity():
    left = _identity("a", universe_name="?u.1", user_name="h")
    right = _identity(
        "b",
        universe_name="?u.2",
        user_name="x",
        target_constant="True",
        carrier_atoms=[],
    )
    assert left != right
    assert debt_readout_from_identity(left) != debt_readout_from_identity(right)


def test_hash_collision_still_performs_full_canonical_byte_comparison(monkeypatch):
    monkeypatch.setattr(identity_module, "_sha256_upper", lambda _payload: "0" * 64)
    left = _identity("a", universe_name="?u.1", user_name="h")
    right = _identity(
        "b",
        universe_name="?u.2",
        user_name="x",
        target_constant="True",
        carrier_atoms=[],
    )
    assert left.index_sha256 == right.index_sha256 == "0" * 64
    assert hash(left) == hash(right)
    assert left != right


@pytest.mark.parametrize(
    "mutation,match",
    [
        (lambda state: state.update({"unknown": 1}), "unknown fields"),
        (
            lambda state: state["object_coverage"].update({"expr_ast": False}),
            "coverage is incomplete",
        ),
        (
            lambda state: state["expr_graph"]["nodes"][0].update({"truncated": True}),
            "unknown fields",
        ),
        (
            lambda state: state["expr_graph"]["edges"].clear(),
            "role edges disagree",
        ),
    ],
)
def test_identity_rejects_unknown_or_incomplete_required_graph(mutation, match):
    state = _kernel_state_fixture("bad", universe_name="?u.1", user_name="h")
    mutation(state)
    with pytest.raises(StrictIdentityError, match=match):
        state_identity_from_kernel_state(
            state,
            environment_content_digest=ENVIRONMENT_DIGEST,
        )


def test_identity_and_canonical_json_round_trip_are_strict():
    key = _identity("rt", universe_name="?u.1", user_name="h")
    assert StateIdentityKey.from_dict(key.to_dict()) == key
    assert parse_canonical_json_bytes(key.canonical_bytes) == key.full_signature
    with pytest.raises(StrictIdentityError, match="not canonical"):
        parse_canonical_json_bytes(b'{"b":2, "a":1}')
    with pytest.raises(StrictIdentityError, match="duplicate"):
        parse_canonical_json_bytes(b'{"a":1,"a":1}')
    bad_status = key.full_signature
    bad_status["status"] = "garbage"
    with pytest.raises(StrictIdentityError, match="open or closed"):
        StateIdentityKey.from_signature(bad_status)
    bad_nested = key.full_signature
    bad_nested["goals"][0]["unknown"] = True
    with pytest.raises(StrictIdentityError, match="unknown fields"):
        StateIdentityKey.from_signature(bad_nested)


def _action() -> ActionSymbol:
    return ActionSymbol(
        action_id="a00_constructor_first",
        opcode="constructor",
        target_selector=TargetSelector.FIRST,
        premise_slot_rule_id=None,
        premise_selector_ordinal=None,
        expected_normalized_type_pattern=None,
        global_constant=None,
        opaque_hyperedge_source=None,
        opaque_hyperedge_digest=None,
        cap_profile_id="u05-hb-20000-cache-bypass-v1",
    )


def _bound(runtime_mvar: str) -> BoundAction:
    return BoundAction(
        symbol=_action(),
        canonical_target_ordinal=0,
        target_normalized_type_hash=TYPE_DIGEST,
        runtime_target_mvar_id=runtime_mvar,
        rendered_tactic="constructor",
    )


def _delta() -> CanonicalStateDelta:
    return CanonicalStateDelta(
        before_goals=("m0",),
        after_goals=("m0",),
        before_mvars=("m0",),
        after_mvars=("m0",),
        before_assigned_mvars=(),
        after_assigned_mvars=(),
        closed_goals=(),
        new_goals=(),
        assigned_mvars=(),
        new_mvars=(),
    )


def _cap() -> CapSemantics:
    return CapSemantics(
        requested_max_heartbeats_option=20_000,
        effective_max_heartbeats_option=20_000,
        effective_max_heartbeats_counter=20_000_000,
        unlimited=False,
        source="explicit_action",
        cache_policy="bypass",
        cache_lookup_performed=False,
        consumption_reported=False,
        episode_budget="NOT_ENFORCED_DEVELOPMENT_ONLY",
    )


def _coverage() -> tuple[FieldCoverage, ...]:
    return tuple(
        FieldCoverage(name, FieldCoverageStatus.COMPLETE, "unit_fixture")
        for name in (
            "state_identity",
            "target_binding",
            "transition_delta",
            "replay",
            "cap_semantics",
            "debt_readout",
        )
    )


def _exact_core_for_bound(
    state: StateIdentityKey, bound: BoundAction
) -> ExactKernelTransitionCore:
    comparable = ReplayComparableResponse(
        raw_status=RawTransitionStatus.OPEN,
        totalized_status=TotalizedStatus.OPEN,
        after_state=state,
        delta=_delta(),
        action_symbol=bound.symbol,
        canonical_binding=bound.semantic_binding_dict(),
        ordinary_failure_class=None,
    )
    replay = ReplayVerification(
        replay_status=ReplayStatus.VERIFIED,
        reexecution_performed=True,
        verification_method="fresh_from_immutable_before_state",
        semantic_response_match=True,
        post_state_match=True,
        delta_match=True,
        target_match=True,
        cap_match=True,
        error=None,
        primary=comparable,
        replay=comparable,
    )
    return ExactKernelTransitionCore(
        source_state=state,
        target_state=state,
        bound_action=bound,
        cap_semantics=_cap(),
        raw_status=RawTransitionStatus.OPEN,
        totalized_status=TotalizedStatus.OPEN,
        delta=_delta(),
        debt_before=DebtReadout.from_identity(state),
        debt_after=DebtReadout.from_identity(state),
        replay=replay,
        field_coverage=_coverage(),
    )


def _local_bindable_state() -> StateIdentityKey:
    state = _identity("local_bind", universe_name="?u.1", user_name="h")
    signature = state.full_signature
    # Synthetic exact-local fixture: declaration f0 has normalized type f0.
    signature["local_declarations"][0]["type_expr"] = "e2"
    signature["expressions"] = [
        row for row in signature["expressions"] if row["id"] != "e3"
    ]
    return StateIdentityKey.from_signature(signature)


def test_action_symbol_is_separate_from_runtime_bound_action():
    left = _bound("?m.process.1")
    right = _bound("?m.process.999")
    assert left.symbol == right.symbol
    assert left.semantic_binding_dict() == right.semantic_binding_dict()
    assert left != right
    assert "process" not in canonical_json_bytes(left.semantic_binding_dict()).decode()


def test_exact_core_requires_verified_reexecution_and_u05_remains_nonpromotable():
    source = _identity("src", universe_name="?u.1", user_name="h")
    target = _identity("dst", universe_name="?u.2", user_name="renamed")
    bound = BoundAction.bind_to_state(
        _action(), source, runtime_goal_mvar_ids=["?m.runtime.target"]
    )
    comparable = ReplayComparableResponse(
        raw_status=RawTransitionStatus.OPEN,
        totalized_status=TotalizedStatus.OPEN,
        after_state=target,
        delta=_delta(),
        action_symbol=bound.symbol,
        canonical_binding=bound.semantic_binding_dict(),
        ordinary_failure_class=None,
    )
    replay = ReplayVerification(
        replay_status=ReplayStatus.VERIFIED,
        reexecution_performed=True,
        verification_method="fresh_from_immutable_before_state",
        semantic_response_match=True,
        post_state_match=True,
        delta_match=True,
        target_match=True,
        cap_match=True,
        error=None,
        primary=comparable,
        replay=comparable,
    )
    core = ExactKernelTransitionCore(
        source_state=source,
        target_state=target,
        bound_action=bound,
        cap_semantics=_cap(),
        raw_status=RawTransitionStatus.OPEN,
        totalized_status=TotalizedStatus.OPEN,
        delta=_delta(),
        debt_before=DebtReadout.from_identity(source),
        debt_after=DebtReadout.from_identity(target),
        replay=replay,
        field_coverage=_coverage(),
    )
    probe = U05ProbeTransition(
        core,
        locality_coverage=(
            FieldCoverage(
                "m3_read_set",
                FieldCoverageStatus.INCOMPLETE,
                "u05",
                "M3 is outside the probe admission boundary",
            ),
        ),
    )
    assert probe.m3_read_set_complete is False
    assert probe.promotable_to_exact_oracle is False
    assert U05ProbeTransition.from_dict(probe.to_dict()) == probe
    assert canonical_contract_bytes(probe) == canonical_json_bytes(probe.to_dict())

    bad = probe.to_dict()
    bad["unknown"] = True
    with pytest.raises(StrictContractError, match="unknown"):
        U05ProbeTransition.from_dict(bad)


def test_exact_core_readmits_public_bound_action_against_source_identity():
    state = _identity("admission", universe_name="?u.1", user_name="h")
    valid = BoundAction.bind_to_state(
        _action(), state, runtime_goal_mvar_ids=["?m.runtime.goal"]
    )
    core = _exact_core_for_bound(state, valid)

    wrong_ordinal = BoundAction(
        symbol=valid.symbol,
        canonical_target_ordinal=99,
        target_normalized_type_hash=valid.target_normalized_type_hash,
        runtime_target_mvar_id=valid.runtime_target_mvar_id,
        rendered_tactic="constructor",
    )
    with pytest.raises(StrictContractError, match="target ordinal"):
        _exact_core_for_bound(state, wrong_ordinal)

    wrong_target_hash = BoundAction(
        symbol=valid.symbol,
        canonical_target_ordinal=0,
        target_normalized_type_hash="F" * 64,
        runtime_target_mvar_id=valid.runtime_target_mvar_id,
        rendered_tactic="constructor",
    )
    with pytest.raises(StrictContractError, match="target hash"):
        _exact_core_for_bound(state, wrong_target_hash)

    forged_dict = core.to_dict()
    forged_dict["bound_action"]["target_normalized_type_hash"] = "E" * 64
    with pytest.raises(StrictContractError, match="target hash"):
        ExactKernelTransitionCore.from_dict(forged_dict)

    local_state = _local_bindable_state()
    local_symbol = ActionSymbol.from_frozen_action_record(
        {
            "action_id": "unit_exact_local_admission",
            "opcode": "exact_local",
            "target_selector": "first",
            "premise_slot_rule_id": "local_decl_0_type_local_0",
            "premise_selector_ordinal": 0,
            "expected_normalized_type_signature": "FVAR_TYPE(local:0)",
            "global_constant": None,
            "opaque_hyperedge_source": None,
            "opaque_hyperedge_digest": None,
            "max_heartbeats": 20_000,
        }
    )
    local_valid = BoundAction.bind_to_state(
        local_symbol,
        local_state,
        runtime_goal_mvar_ids=["?m.runtime.goal"],
        runtime_local_fvar_ids=["runtime_h"],
    )
    forged_premise = PremiseBinding(
        premise_slot_rule_id=local_symbol.premise_slot_rule_id,
        canonical_ordinal=0,
        normalized_type_hash="D" * 64,
        runtime_fvar_id="runtime_h",
    )
    wrong_premise_hash = BoundAction(
        symbol=local_symbol,
        canonical_target_ordinal=local_valid.canonical_target_ordinal,
        target_normalized_type_hash=local_valid.target_normalized_type_hash,
        runtime_target_mvar_id=local_valid.runtime_target_mvar_id,
        premises=(forged_premise,),
        rendered_tactic="exact runtime_h",
    )
    with pytest.raises(StrictContractError, match="premise hash"):
        _exact_core_for_bound(local_state, wrong_premise_hash)


def test_ordinary_failure_is_sink_but_resource_failure_is_external_censor():
    source = _identity("src", universe_name="?u.1", user_name="h")
    bound = BoundAction.bind_to_state(
        _action(), source, runtime_goal_mvar_ids=["?m.runtime.target"]
    )
    comparable = ReplayComparableResponse(
        raw_status=RawTransitionStatus.ORDINARY_FAILURE,
        totalized_status=TotalizedStatus.SINK,
        after_state=None,
        delta=_delta(),
        action_symbol=bound.symbol,
        canonical_binding=bound.semantic_binding_dict(),
        ordinary_failure_class="target_resolution",
    )
    replay = ReplayVerification(
        replay_status=ReplayStatus.VERIFIED,
        reexecution_performed=True,
        verification_method="fresh_from_immutable_before_state",
        semantic_response_match=True,
        post_state_match=True,
        delta_match=True,
        target_match=True,
        cap_match=True,
        error=None,
        primary=comparable,
        replay=comparable,
    )
    core = ExactKernelTransitionCore(
        source_state=source,
        target_state=None,
        bound_action=bound,
        cap_semantics=_cap(),
        raw_status=RawTransitionStatus.ORDINARY_FAILURE,
        totalized_status=TotalizedStatus.SINK,
        delta=_delta(),
        debt_before=DebtReadout.from_identity(source),
        debt_after=None,
        replay=replay,
        field_coverage=_coverage(),
    )
    assert core.totalized_status is TotalizedStatus.SINK
    censor = Censor(
        CensorKind.WALL_TIMEOUT,
        stage="rpc_transport",
        message="30-second wall timeout",
    )
    assert censor.kind is CensorKind.WALL_TIMEOUT
    assert not hasattr(censor, "target_state")


def test_assigned_mvars_must_be_before_after_difference_not_cumulative():
    RawStateDelta.from_dict(
        {
            "closed_goals": ["?m.tail"],
            "new_goals": [],
            "assigned_mvars": ["?m.tail"],
            "new_mvars": [],
            "before_goals": ["?m.head", "?m.tail"],
            "after_goals": ["?m.head"],
            "before_mvars": ["?m.root", "?m.head", "?m.tail"],
            "after_mvars": ["?m.root", "?m.head", "?m.tail"],
            "before_assigned_mvars": ["?m.root"],
            "after_assigned_mvars": ["?m.root", "?m.tail"],
            "minimal_support": {},
        }
    )
    cumulative = {
        "closed_goals": ["?m.tail"],
        "new_goals": [],
        "assigned_mvars": ["?m.root", "?m.tail"],
        "new_mvars": [],
        "before_goals": ["?m.head", "?m.tail"],
        "after_goals": ["?m.head"],
        "before_mvars": ["?m.root", "?m.head", "?m.tail"],
        "after_mvars": ["?m.root", "?m.head", "?m.tail"],
        "before_assigned_mvars": ["?m.root"],
        "after_assigned_mvars": ["?m.root", "?m.tail"],
        "minimal_support": {},
    }
    with pytest.raises(StrictKernelRPCProtocolError, match="cumulative"):
        RawStateDelta.from_dict(cumulative)


def test_strict_rpc_boundary_rejects_unknown_duplicate_and_cap_drift():
    with pytest.raises(StrictKernelRPCProtocolError, match="duplicate"):
        parse_strict_json_line('{"ok":true,"ok":false}')
    with pytest.raises(StrictKernelRPCProtocolError, match="floating"):
        parse_strict_json_line('{"x":1.5}')
    with pytest.raises(StrictKernelRPCProtocolError, match="unknown"):
        RawTargetBinding.from_dict(
            {
                "requested_target_mvar_id": None,
                "requested_target_selector": "first",
                "effective_target_mvar_id": "?m.1",
                "effective_target_goal_index": 0,
                "source": "action_target_selector",
                "unknown": 1,
            }
        )
    with pytest.raises(StrictContractError, match="counter-unit"):
        CapSemantics(
            requested_max_heartbeats_option=20_000,
            effective_max_heartbeats_option=20_000,
            effective_max_heartbeats_counter=20_000,
            unlimited=False,
            source="explicit_action",
            cache_policy="bypass",
            cache_lookup_performed=False,
            consumption_reported=False,
            episode_budget="NOT_ENFORCED_DEVELOPMENT_ONLY",
        )
    with pytest.raises(StrictContractError, match="frozen 20000"):
        CapSemantics(
            requested_max_heartbeats_option=1,
            effective_max_heartbeats_option=1,
            effective_max_heartbeats_counter=1_000,
            unlimited=False,
            source="explicit_action",
            cache_policy="bypass",
            cache_lookup_performed=False,
            consumption_reported=False,
            episode_budget="NOT_ENFORCED_DEVELOPMENT_ONLY",
        )


def test_strict_apply_request_is_canonical_and_has_no_cache_or_legacy_adapter():
    raw = strict_apply_request_bytes(
        request_id="u05-1",
        state_id="krpc_state_1",
        action={
            "action_id": "a00_constructor_first",
            "tactic": "constructor",
            "target_selector": "first",
            "max_heartbeats": 20_000,
        },
    )
    assert raw.endswith(b"\n")
    parsed = parse_canonical_json_bytes(raw[:-1])
    assert parsed["cmd"] == "apply_tactic"
    assert parsed["action"]["max_heartbeats"] == 20_000
    source = Path("lean_rgc/lean/kernel_rpc_client.py").read_text(encoding="utf-8")
    assert "AuditRecord" not in source
    assert "from_dict" in source


def _native_budget() -> dict[str, object]:
    return {
        "requested_max_heartbeats_option": 20_000,
        "effective_max_heartbeats_option": 20_000,
        "effective_max_heartbeats_counter": 20_000_000,
        "unlimited": False,
        "source": "explicit_action",
        "cache_policy": "bypass",
        "cache_lookup_performed": False,
        "consumption_reported": False,
        "episode_budget": "NOT_ENFORCED_DEVELOPMENT_ONLY",
    }


def _rpc_action() -> dict[str, object]:
    return {
        "action_id": "a00_constructor_first",
        "tactic": "constructor",
        "target_selector": "first",
        "max_heartbeats": 20_000,
    }


def _valid_apply_response() -> dict[str, object]:
    before = _kernel_state_fixture("rpc", universe_name="?u.1", user_name="h")
    before_id = before["state_id"]
    after = copy.deepcopy(before)
    after["state_id"] = "process_state_rpc_after"
    after["parent_state_id"] = before_id
    after["state_hash_raw"] = "after_raw"
    after["state_hash_norm"] = "after_norm"
    goal_id = before["goals"][0]["mvar_id"]
    mvars = [row["mvar_id"] for row in before["metavars"]]
    assigned = [row["mvar_id"] for row in before["metavars"] if row["assigned"]]
    delta = {
        "closed_goals": [],
        "new_goals": [],
        "assigned_mvars": [],
        "new_mvars": [],
        "before_goals": [goal_id],
        "after_goals": [goal_id],
        "before_mvars": mvars,
        "after_mvars": mvars,
        "before_assigned_mvars": assigned,
        "after_assigned_mvars": assigned,
        "minimal_support": copy.deepcopy(before["minimal_support"]),
    }
    target = {
        "requested_target_mvar_id": None,
        "requested_target_selector": "first",
        "effective_target_mvar_id": goal_id,
        "effective_target_goal_index": 0,
        "source": "action_target_selector",
    }
    budget = _native_budget()
    comparable = {
        "semantic_status": "open",
        "post_kernel_state": strip_replay_transport(after),
        "state_delta": strip_replay_transport(delta),
        "action_id": _rpc_action()["action_id"],
        "target_binding": copy.deepcopy(target),
        "budget": copy.deepcopy(budget),
        "normalized_failure_class": None,
    }
    replay = {
        "schema_version": "lean-rgc-u05-replay-v1",
        "replay_status": "verified",
        "reexecution_performed": True,
        "verification_method": "fresh_from_immutable_before_state",
        "semantic_response_match": True,
        "post_state_match": True,
        "delta_match": True,
        "target_match": True,
        "cap_match": True,
        "error": None,
        "primary_comparable": copy.deepcopy(comparable),
        "replay_comparable": copy.deepcopy(comparable),
    }
    after_id = after["state_id"]
    audit_flags = {
        "kernel_rpc_worker": True,
        "execution_backend": "lean_kernel_rpc_in_memory_v1",
        "kernel_state_before": copy.deepcopy(before),
        "kernel_state_after": copy.deepcopy(after),
        "state_delta": copy.deepcopy(delta),
        "replay": copy.deepcopy(replay),
        "heartbeat_telemetry": copy.deepcopy(budget),
        "target_binding": copy.deepcopy(target),
        "before_persistent_state_id": before_id,
        "after_persistent_state_id": after_id,
    }
    return {
        "id": "u05-unit",
        "rpc_protocol_version": "lean-rgc-jsonl-rpc-v2",
        "ok": True,
        "u05_semantics_version": "lean-rgc-u05-rpc-semantics-v1",
        "status": "partial",
        "censor_reason": None,
        "before_state_id": before_id,
        "after_state_id": after_id,
        "after_state_retained": True,
        "target_mvar_id": goal_id,
        "target_binding": target,
        "budget": budget,
        "state_delta": delta,
        "kernel_state_before": before,
        "kernel_state_after": after,
        "kernel_state": copy.deepcopy(after),
        "state": {
            "state_id": after_id,
            "task_id": after["task_id"],
            "status": "open",
            "goal_count": 1,
            "parent_state_id": before_id,
            "proof_prefix": after["proof_prefix"],
            "canonical_status": "lean_kernel_rpc_in_memory_state",
        },
        "audit": {
            "task_id": after["task_id"],
            "state_id": before_id,
            "action_id": _rpc_action()["action_id"],
            "status": "partial",
            "elapsed_ms": 7,
            "heartbeats": None,
            "stdout": "",
            "stderr": "",
            "messages": [],
            "after_state": {},
            "audit_flags": audit_flags,
        },
        "replay": replay,
        "replay_certificate": copy.deepcopy(replay),
        "messages": [],
        "elapsed_ms": 7,
        "heartbeats": None,
    }


def _parse_unit_apply(response: dict[str, object]):
    return parse_apply_tactic_response(
        response,
        expected_request_id="u05-unit",
        expected_state_id="process_state_rpc",
        expected_action=_rpc_action(),
    )


def test_strict_apply_response_is_bound_to_request_and_all_semantic_mirrors():
    assert _parse_unit_apply(_valid_apply_response()).status == "partial"

    wrong_state = _valid_apply_response()
    wrong_state["before_state_id"] = "forged"
    with pytest.raises(StrictKernelRPCProtocolError, match="differs from request"):
        _parse_unit_apply(wrong_state)

    wrong_action = _valid_apply_response()
    for comparable_name in ("primary_comparable", "replay_comparable"):
        wrong_action["replay"][comparable_name]["action_id"] = "forged_action"
        wrong_action["replay_certificate"][comparable_name]["action_id"] = "forged_action"
    wrong_action["audit"]["audit_flags"]["replay"] = copy.deepcopy(wrong_action["replay"])
    with pytest.raises(StrictKernelRPCProtocolError, match="action_id differs"):
        _parse_unit_apply(wrong_action)

    wrong_audit = _valid_apply_response()
    wrong_audit["audit"]["audit_flags"]["state_delta"]["after_goals"] = []
    with pytest.raises(StrictKernelRPCProtocolError, match="audit delta"):
        _parse_unit_apply(wrong_audit)

    wrong_cap = _valid_apply_response()
    for budget in (
        wrong_cap["budget"],
        wrong_cap["replay"]["primary_comparable"]["budget"],
        wrong_cap["replay"]["replay_comparable"]["budget"],
        wrong_cap["replay_certificate"]["primary_comparable"]["budget"],
        wrong_cap["replay_certificate"]["replay_comparable"]["budget"],
        wrong_cap["audit"]["audit_flags"]["heartbeat_telemetry"],
        wrong_cap["audit"]["audit_flags"]["replay"]["primary_comparable"]["budget"],
        wrong_cap["audit"]["audit_flags"]["replay"]["replay_comparable"]["budget"],
    ):
        budget["requested_max_heartbeats_option"] = 10_000
        budget["effective_max_heartbeats_option"] = 10_000
        budget["effective_max_heartbeats_counter"] = 10_000_000
    with pytest.raises(StrictKernelRPCProtocolError, match="invalid explicit U05 budget"):
        _parse_unit_apply(wrong_cap)


def test_unverified_ordinary_failure_is_converted_to_external_censor():
    response = _valid_apply_response()
    response["status"] = "censor"
    response["censor_reason"] = "replay_mismatch"
    response["after_state_retained"] = False
    response["audit"].pop("heartbeats")
    response["audit"]["status"] = "fail"
    response["audit"]["audit_flags"]["after_persistent_state_id"] = None
    for replay_key in ("replay", "replay_certificate"):
        replay = response[replay_key]
        replay["replay_status"] = "mismatch"
        replay["semantic_response_match"] = False
        replay["error"] = "replayed failure class differed"
        replay["primary_comparable"]["semantic_status"] = "ordinary_failure"
        replay["primary_comparable"]["post_kernel_state"] = strip_replay_transport(
            response["kernel_state_before"]
        )
        replay["primary_comparable"]["state_delta"] = None
        replay["primary_comparable"]["normalized_failure_class"] = "ordinary_failure"
        replay["replay_comparable"] = copy.deepcopy(replay["primary_comparable"])
        replay["replay_comparable"]["normalized_failure_class"] = "different_failure"
    response["audit"]["audit_flags"]["replay"] = copy.deepcopy(response["replay"])
    parsed = _parse_unit_apply(response)
    assert parsed.wire_status == "censor"
    assert parsed.status == "censor"
    assert parsed.censor_reason == "replay_mismatch"


def test_discard_request_response_are_jointly_bound_and_exact():
    raw = strict_discard_request_bytes(request_id="discard-1", state_id="krpc_state_7")
    assert parse_canonical_json_bytes(raw[:-1]) == {
        "cmd": "discard_state",
        "id": "discard-1",
        "state_id": "krpc_state_7",
    }
    response = {
        "id": "discard-1",
        "rpc_protocol_version": "lean-rgc-jsonl-rpc-v2",
        "ok": True,
        "u05_semantics_version": "lean-rgc-u05-rpc-semantics-v1",
        "state_id": "krpc_state_7",
        "discarded": True,
        "n_states_before": 4,
        "n_states_after": 3,
    }
    parsed = parse_discard_state_response(
        response,
        expected_request_id="discard-1",
        expected_state_id="krpc_state_7",
    )
    assert parsed.n_states_before == parsed.n_states_after + 1
    response["state_id"] = "wrong"
    with pytest.raises(StrictKernelRPCProtocolError, match="differs from request"):
        parse_discard_state_response(
            response,
            expected_request_id="discard-1",
            expected_state_id="krpc_state_7",
        )


def test_opaque_action_digest_is_bound_to_frozen_source():
    symbol = ActionSymbol.from_frozen_action_record(
        {
            "action_id": "a10_simp_Nat_add_zero_first",
            "opcode": "opaque_tactic",
            "target_selector": "first",
            "premise_slot_rule_id": None,
            "premise_selector_ordinal": None,
            "expected_normalized_type_signature": None,
            "global_constant": None,
            "opaque_hyperedge_source": "simp only [Nat.add_zero]",
            "opaque_hyperedge_digest": (
                "CE264CA0DB8A2B6CD05AFAB00A3C4E3572BB83007BA043E8331ECC681400380D"
            ),
            "max_heartbeats": 20_000,
        }
    )
    assert symbol.opcode == "opaque_tactic"
    assert symbol.opaque_hyperedge_source == "simp only [Nat.add_zero]"
    assert symbol.opaque_hyperedge_digest is not None
    assert ActionSymbol.from_dict(symbol.to_dict()) == symbol
    bad = {
        "action_id": "bad",
        "opcode": "opaque_tactic",
        "target_selector": "first",
        "premise_slot_rule_id": None,
        "premise_selector_ordinal": None,
        "expected_normalized_type_signature": None,
        "global_constant": None,
        "opaque_hyperedge_source": "simp only [Nat.add_zero] ",
        "opaque_hyperedge_digest": symbol.opaque_hyperedge_digest,
        "max_heartbeats": 20_000,
    }
    with pytest.raises(StrictContractError, match="digest mismatch"):
        ActionSymbol.from_frozen_action_record(bad)


def test_frozen_local_constant_and_opaque_actions_bind_and_render_deterministically():
    state = _identity("bind", universe_name="?u.1", user_name="h")
    local_state = _local_bindable_state()
    local_symbol = ActionSymbol.from_frozen_action_record(
        {
            "action_id": "unit_exact_local",
            "opcode": "exact_local",
            "target_selector": "first",
            "premise_slot_rule_id": "local_decl_0_type_local_0",
            "premise_selector_ordinal": 0,
            "expected_normalized_type_signature": "FVAR_TYPE(local:0)",
            "global_constant": None,
            "opaque_hyperedge_source": None,
            "opaque_hyperedge_digest": None,
            "max_heartbeats": 20_000,
        }
    )
    assert local_symbol.premise_selector_ordinal == 0
    local_bound = BoundAction.bind_to_state(
        local_symbol,
        local_state,
        runtime_goal_mvar_ids=["?m.runtime.goal"],
        runtime_local_fvar_ids=["runtime_h"],
    )
    assert local_bound.premises[0].canonical_ordinal == 0
    assert local_bound.rendered_tactic == "exact runtime_h"
    assert local_bound.to_rpc_action() == {
        "action_id": "unit_exact_local",
        "tactic": "exact runtime_h",
        "target_selector": "first",
        "max_heartbeats": 20_000,
    }

    const_symbol = ActionSymbol.from_frozen_action_record(
        {
            "action_id": "unit_exact_const",
            "opcode": "exact_const",
            "target_selector": "first",
            "premise_slot_rule_id": None,
            "premise_selector_ordinal": None,
            "expected_normalized_type_signature": "CONST(Eq)",
            "global_constant": "Eq.refl",
            "opaque_hyperedge_source": None,
            "opaque_hyperedge_digest": None,
            "max_heartbeats": 20_000,
        }
    )
    assert const_symbol.global_constant == "Eq.refl"
    const_bound = BoundAction.bind_to_state(
        const_symbol,
        state,
        runtime_goal_mvar_ids=["?m.runtime.goal"],
    )
    assert const_bound.rendered_tactic == "exact Eq.refl"
    assert const_bound.to_rpc_action()["tactic"] == "exact Eq.refl"

    opaque_symbol = ActionSymbol.from_frozen_action_record(
        {
            "action_id": "unit_opaque",
            "opcode": "opaque_tactic",
            "target_selector": "first",
            "premise_slot_rule_id": None,
            "premise_selector_ordinal": None,
            "expected_normalized_type_signature": None,
            "global_constant": None,
            "opaque_hyperedge_source": "simp only [Nat.add_zero]",
            "opaque_hyperedge_digest": (
                "CE264CA0DB8A2B6CD05AFAB00A3C4E3572BB83007BA043E8331ECC681400380D"
            ),
            "max_heartbeats": 20_000,
        }
    )
    opaque_bound = BoundAction.bind_to_state(
        opaque_symbol,
        state,
        runtime_goal_mvar_ids=["?m.runtime.goal"],
    )
    assert opaque_bound.rendered_tactic == opaque_symbol.opaque_hyperedge_source
    assert opaque_bound.to_rpc_action()["tactic"] == "simp only [Nat.add_zero]"

    wrong_ordinal = copy.copy(local_bound.premises[0])
    object.__setattr__(wrong_ordinal, "canonical_ordinal", 1)
    with pytest.raises(StrictContractError, match="symbolic premise slot"):
        BoundAction(
            symbol=local_symbol,
            canonical_target_ordinal=0,
            target_normalized_type_hash=TYPE_DIGEST,
            runtime_target_mvar_id="?m.runtime.goal",
            premises=(wrong_ordinal,),
            rendered_tactic="exact runtime_h",
        )
