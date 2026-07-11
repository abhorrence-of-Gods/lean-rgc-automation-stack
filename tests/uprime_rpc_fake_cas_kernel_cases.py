"""Noncollectable Phase-2b2c in-memory fake-CAS acceptance cases.

The frozen collector imports only the test functions named by ``__all__``.
Kernel behavior is exercised entirely in memory.  Source reads below are
read-only mutation/AST oracles; no test writes a fixture or contacts a service.
"""

from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, replace
import hashlib
import inspect
from pathlib import Path
import sys
import types
from typing import Any

import pytest

from lean_rgc.evals import uprime_rpc_fake_cas_kernel as cas


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "lean_rgc/evals/uprime_rpc_fake_cas_kernel.py"
REAL_SHA256 = hashlib.sha256

A = bytes.fromhex("11" * 32)
B = bytes.fromhex("22" * 32)
C = bytes.fromhex("33" * 32)
D = bytes.fromhex("44" * 32)

MAX_PAYLOAD_BYTES = 1_048_576
MAX_GENERATION = 9_223_372_036_854_775_807

D_STATE = b"lean-rgc-uprime-u1-in-memory-fake-cas-state-v1\0"
D_INPUT = b"lean-rgc-uprime-u1-in-memory-fake-cas-input-v1\0"
D_DELTA = b"lean-rgc-uprime-u1-in-memory-fake-cas-delta-v1\0"
D_TRANSITION = b"lean-rgc-uprime-u1-in-memory-fake-cas-transition-v1\0"

DIRECTIVES = (
    "apply_intended_acknowledge",
    "apply_intended_lose_ack_then_confirm",
    "apply_intended_lose_ack_confirmation_unavailable",
    "substitute_alternate_then_confirm_wrong_delta",
)
DIRECTIVE_TAGS = {value: bytes((index,)) for index, value in enumerate(DIRECTIVES, 1)}

OUTCOMES = (
    "conflict_no_change",
    "existing_identical_no_change",
    "intended_applied_acknowledged",
    "intended_applied_ack_lost_confirmed",
    "intended_applied_ack_lost_unconfirmed",
    "wrong_delta_confirmed",
)
OUTCOME_TAGS = {value: bytes((index,)) for index, value in enumerate(OUTCOMES, 1)}

STATE_FIELDS = (
    "state_schema_version",
    "state_scope",
    "origin_status",
    "generation",
    "cell_state",
    "cell_payload",
    "cell_payload_bytes",
    "cell_payload_sha256",
    "state_version_sha256",
    "payload_byte_limit",
    "generation_upper_bound",
    "version_scope",
    "raw_equality_scope",
    "state_provenance",
    "lineage_enforcement",
    "fork_handling",
    "deletion_support",
    "persistence_scope",
    "concurrency_scope",
    "remote_cas_authentication",
    "authority_scope",
    "canonical_remote_authority",
    "licenses_execution",
    "licenses_publication",
    "licenses_recovery",
    "licenses_later_stage",
)

TRANSITION_FIELDS = (
    "transition_schema_version",
    "transition_scope",
    "origin_status",
    "before_state",
    "after_state",
    "expected_state_version_sha256",
    "proposed_payload",
    "proposed_payload_bytes",
    "proposed_payload_sha256",
    "synthetic_directive",
    "alternate_payload",
    "alternate_payload_bytes",
    "alternate_payload_sha256",
    "input_sha256",
    "outcome",
    "reason_codes",
    "expected_version_match",
    "proposed_equal_before",
    "directive_reached",
    "alternate_semantics_checked",
    "state_changed",
    "cell_mutation_count",
    "intended_apply_status",
    "intended_after_state_version_sha256",
    "intended_delta_sha256",
    "actual_delta_sha256",
    "transition_sha256",
    "effect_scope",
    "synthetic_acknowledgement_label",
    "same_kernel_confirmation_label",
    "synthetic_client_observation",
    "model_latent_effect",
    "payload_byte_limit",
    "generation_upper_bound",
    "unique_retained_payload_reference_upper_bound_bytes",
    "retained_payload_copy_upper_bound_bytes",
    "state_hash_preimage_upper_bound_bytes",
    "input_hash_preimage_upper_bound_bytes",
    "delta_hash_preimage_upper_bound_bytes",
    "transition_hash_preimage_upper_bound_bytes",
    "hash_preimage_construction",
    "directive_origin",
    "outcome_selection",
    "confirmation_scope",
    "cause_scope",
    "application_attribution",
    "state_provenance",
    "lineage_enforcement",
    "fork_handling",
    "idempotence_scope",
    "exactly_once_scope",
    "persistence_scope",
    "concurrency_scope",
    "filesystem_staging",
    "remote_publication",
    "durability_scope",
    "marker_scope",
    "recovery_scope",
    "witness_scope",
    "manifest_scope",
    "authority_scope",
    "canonical_remote_authority",
    "licenses_execution",
    "licenses_publication",
    "licenses_recovery",
    "licenses_later_stage",
)

STATE_FIXED = {
    "state_schema_version": "lean-rgc-uprime-u1-in-memory-fake-cas-state-v1.0",
    "state_scope": "one_anonymous_in_memory_value_cell",
    "origin_status": "unknown_may_be_synthetic",
    "payload_byte_limit": MAX_PAYLOAD_BYTES,
    "generation_upper_bound": MAX_GENERATION,
    "version_scope": "comparison_value_not_capability",
    "raw_equality_scope": "exact_bytes_not_digest_only",
    "state_provenance": "unauthenticated_forgeable_value_object",
    "lineage_enforcement": "caller_must_thread_returned_state_not_enforced",
    "fork_handling": "forks_allowed_no_global_linearity",
    "deletion_support": "unsupported_proposals_are_exact_bytes",
    "persistence_scope": "none_process_memory_only",
    "concurrency_scope": "none_pure_single_call_transition",
    "remote_cas_authentication": "not_performed",
    "authority_scope": "none",
    "canonical_remote_authority": False,
    "licenses_execution": False,
    "licenses_publication": False,
    "licenses_recovery": False,
    "licenses_later_stage": False,
}

TRANSITION_FIXED = {
    "transition_schema_version": "lean-rgc-uprime-u1-in-memory-fake-cas-transition-v1.0",
    "transition_scope": "pure_single_call_one_cell_cas_derivation",
    "origin_status": "unknown_may_be_synthetic",
    "payload_byte_limit": MAX_PAYLOAD_BYTES,
    "generation_upper_bound": MAX_GENERATION,
    "unique_retained_payload_reference_upper_bound_bytes": 3_145_728,
    "retained_payload_copy_upper_bound_bytes": 0,
    "state_hash_preimage_upper_bound_bytes": 1_048_640,
    "input_hash_preimage_upper_bound_bytes": 2_097_249,
    "delta_hash_preimage_upper_bound_bytes": 1_048_695,
    "transition_hash_preimage_upper_bound_bytes": 467,
    "hash_preimage_construction": "payloads_streamed_no_full_preimage_materialization",
    "directive_origin": "caller_supplied_repeatable_synthetic_choice",
    "outcome_selection": "input_validation_then_conflict_then_exact_identity_then_directive",
    "confirmation_scope": "same_call_same_kernel_not_independent",
    "cause_scope": "not_modeled_no_causal_fault_claim",
    "application_attribution": "not_authenticated",
    "state_provenance": "unauthenticated_forgeable_value_object",
    "lineage_enforcement": "caller_must_thread_returned_state_not_enforced",
    "fork_handling": "forks_allowed_no_global_linearity",
    "idempotence_scope": "not_provided_no_operation_identity",
    "exactly_once_scope": "not_provided",
    "persistence_scope": "none_process_memory_only",
    "concurrency_scope": "none_pure_single_call_transition",
    "filesystem_staging": "not_performed",
    "remote_publication": "not_performed",
    "durability_scope": "not_observed",
    "marker_scope": "not_created_or_observed",
    "recovery_scope": "not_performed",
    "witness_scope": "not_issued_or_verified",
    "manifest_scope": "not_read_or_written",
    "authority_scope": "none",
    "canonical_remote_authority": False,
    "licenses_execution": False,
    "licenses_publication": False,
    "licenses_recovery": False,
    "licenses_later_stage": False,
}

ROWS = {
    "conflict_no_change": (
        "expected_state_version_mismatch", "not_attempted", "no_change",
        "not_attempted", "not_attempted", "conflict", "unchanged",
        False, None, False, False, False, 0,
    ),
    "existing_identical_no_change": (
        "exact_payload_already_current", "not_attempted_existing_identical",
        "no_change_existing_identical", "not_attempted", "not_attempted",
        "existing_identical", "unchanged_existing_identical",
        True, True, False, False, False, 0,
    ),
    "intended_applied_acknowledged": (
        "matched_intended_apply_acknowledged", "applied", "intended_applied",
        "delivered", "not_attempted", "applied", "intended_applied",
        True, False, True, False, True, 1,
    ),
    "intended_applied_ack_lost_confirmed": (
        "matched_intended_apply_ack_lost_confirmed", "applied",
        "intended_applied", "lost", "same_kernel_observed_intended",
        "applied_after_same_kernel_confirmation", "intended_applied",
        True, False, True, False, True, 1,
    ),
    "intended_applied_ack_lost_unconfirmed": (
        "matched_intended_apply_ack_lost_confirmation_unavailable", "applied",
        "intended_applied", "lost", "unavailable", "ambiguous",
        "intended_applied", True, False, True, False, True, 1,
    ),
    "wrong_delta_confirmed": (
        "matched_alternate_substitution_confirmed_wrong_delta",
        "not_applied_alternate_substituted", "alternate_applied",
        "not_applicable_intended_not_applied", "same_kernel_observed_wrong_delta",
        "wrong_delta", "alternate_applied", True, False, True, True, True, 1,
    ),
}

STATE_GOLDENS = {
    (0, None): "D475431F78A252741905BD00E75E0E97A30326A91046BF9D4A827D4713BAEBB8",
    (1, b""): "BD7CC4F2F5267D91A15B465E390A1EFBD9227000A6588E90293A1E2376902A81",
    (1, A): "ECD95866ABC3D55C1D204027E08BC57FB9ED65836A7996C10F51D1D723240652",
    (2, B): "6B82D8C7DDAD4FA3E1A6618168EE4D37E1662B79CDB4C7A12189376FDCAC7F90",
    (2, C): "1CC27CD54D0062C61AB62D0F238382D9ECF965BC624D7E8347FEC995EB5AA674",
    (3, A): "77DF0F942B14680DBA5459666F99B5C6D0B37FC0648F9C2B47A9839F5315E5A0",
}

CASE_GOLDENS = {
    "conflict_no_change": (
        "9961EFA8D1D509BF324B2C5AA9D56C664F4807B207E620332B39D06A280CFAA7",
        "60D25236487695725CF5C6AAE03B8BD5426085D3B6A89DB8527843E79E3C4F3F",
        270,
    ),
    "existing_identical_no_change": (
        "FAD02517161804E7DA055790547EA5459D8478E0AD9981F31847EBF603AC5E22",
        "914C8A1F12A857E5B9ECD7ED18D3B929D0C3909CC6C794C155D5CD73E570CDA4",
        335,
    ),
    "intended_applied_acknowledged": (
        "19A5C288B0BC9F9A6D363EB59260B1107345FCFFE0FA6E0CF461ADC1244F2CEF",
        "029C6ECD6148EDC6736727E780DE474C7D760B63E650EA22744800547208C44C",
        373,
    ),
    "intended_applied_ack_lost_confirmed": (
        "070021A460A0B3CE68FEA0992D70D2CCCA82A93389692B99A5C8A3119273FD02",
        "AC63C584E6A0B0D852A277D7D27D529DE9A8D1699794C1FA5673ED6510A3409A",
        421,
    ),
    "intended_applied_ack_lost_unconfirmed": (
        "81B5BFC1C59CA065AB32B9B8F9453A55338C70E646923C1C90D36A3CE5133BC0",
        "48157FF56B4FA39161653C29F748878AABA96718EEA19698469397FA92619766",
        389,
    ),
    "wrong_delta_confirmed": (
        "BC14DF5E4C800160838A55C401816DFDEC1618BA4C29D5008FC2D7E9CC06FC04",
        "3D383A27D9410D3605CFDC5E0635A349CB9DF0D5AB159E1846DEE33E8B7BCAA0",
        467,
    ),
}


def _h(raw: bytes) -> str:
    return REAL_SHA256(raw).hexdigest().upper()


def _u16(value: int) -> bytes:
    return value.to_bytes(2, "big")


def _u64(value: int) -> bytes:
    return value.to_bytes(8, "big")


def _p(payload: bytes) -> bytes:
    return _u64(len(payload)) + payload


def _o(payload: bytes | None) -> bytes:
    return b"\x00" if payload is None else b"\x01" + _p(payload)


def _q(value: str | None) -> bytes:
    return b"\x00" if value is None else b"\x01" + bytes.fromhex(value)


def _k(value: str) -> bytes:
    raw = value.encode("ascii")
    return _u16(len(raw)) + raw


def _state_preimage(generation: int, payload: bytes | None) -> bytes:
    return D_STATE + _u64(generation) + _o(payload)


def _state_version(generation: int, payload: bytes | None) -> str:
    return _h(_state_preimage(generation, payload))


def _input_preimage(expected: str, proposal: bytes, directive: str, alternate: bytes | None) -> bytes:
    return (
        D_INPUT + bytes.fromhex(expected) + _p(proposal)
        + DIRECTIVE_TAGS[directive] + _o(alternate)
    )


def _input_hash(expected: str, proposal: bytes, directive: str, alternate: bytes | None) -> str:
    return _h(_input_preimage(expected, proposal, directive, alternate))


def _delta_preimage(before: str, after: str, payload: bytes) -> bytes:
    return D_DELTA + bytes.fromhex(before) + bytes.fromhex(after) + _p(payload)


def _delta_hash(before: str, after: str, payload: bytes) -> str:
    return _h(_delta_preimage(before, after, payload))


def _transition_preimage(
    input_hash: str,
    outcome: str,
    before: str,
    intended_after: str | None,
    intended_delta: str | None,
    actual_delta: str | None,
    after: str,
) -> bytes:
    row = ROWS[outcome]
    return (
        D_TRANSITION + bytes.fromhex(input_hash) + OUTCOME_TAGS[outcome]
        + bytes.fromhex(before) + _q(intended_after) + _q(intended_delta)
        + _q(actual_delta) + bytes.fromhex(after) + _u64(row[12])
        + b"".join(_k(value) for value in row[:7])
    )


def _mapping(record: Any) -> dict[str, Any]:
    return {field.name: getattr(record, field.name) for field in fields(record)}


def _state_for(module: Any, generation: int, payload: bytes | None) -> Any:
    values = dict(STATE_FIXED)
    if payload is None:
        values.update(
            generation=generation,
            cell_state="absent",
            cell_payload=None,
            cell_payload_bytes=None,
            cell_payload_sha256=None,
        )
    else:
        values.update(
            generation=generation,
            cell_state="present",
            cell_payload=payload,
            cell_payload_bytes=len(payload),
            cell_payload_sha256=module._raw_payload_sha256(payload),
        )
    values["state_version_sha256"] = _state_version(generation, payload)
    return module.InMemoryFakeCasStateV10(**values)


def _state(generation: int, payload: bytes | None) -> Any:
    return _state_for(cas, generation, payload)


def _assert_fixed(record: Any, expected: dict[str, Any]) -> None:
    for name, value in expected.items():
        assert getattr(record, name) == value, name


def _assert_transition(
    transition: Any,
    caller_state: Any,
    expected: str,
    proposal: bytes,
    directive: str,
    alternate: bytes | None,
    outcome: str,
) -> None:
    row = ROWS[outcome]
    changed = row[11]
    applied = alternate if outcome == "wrong_delta_confirmed" else proposal
    assert transition.outcome == outcome
    assert transition.reason_codes == (row[0],)
    assert (
        transition.intended_apply_status,
        transition.effect_scope,
        transition.synthetic_acknowledgement_label,
        transition.same_kernel_confirmation_label,
        transition.synthetic_client_observation,
        transition.model_latent_effect,
    ) == row[1:7]
    assert (
        transition.expected_version_match,
        transition.proposed_equal_before,
        transition.directive_reached,
        transition.alternate_semantics_checked,
        transition.state_changed,
        transition.cell_mutation_count,
    ) == row[7:13]
    assert transition.before_state == caller_state
    assert transition.before_state is not caller_state
    assert transition.before_state.cell_payload is caller_state.cell_payload
    assert transition.expected_state_version_sha256 == expected
    assert transition.proposed_payload is proposal
    assert transition.proposed_payload_bytes == len(proposal)
    assert transition.proposed_payload_sha256 == _h(proposal)
    assert transition.synthetic_directive == directive
    assert transition.alternate_payload is alternate
    assert transition.alternate_payload_bytes == (None if alternate is None else len(alternate))
    assert transition.alternate_payload_sha256 == (None if alternate is None else _h(alternate))
    input_hash = _input_hash(expected, proposal, directive, alternate)
    assert transition.input_sha256 == input_hash
    if not changed:
        assert transition.after_state is transition.before_state
        assert transition.intended_after_state_version_sha256 is None
        assert transition.intended_delta_sha256 is None
        assert transition.actual_delta_sha256 is None
    else:
        intended_after = _state_version(caller_state.generation + 1, proposal)
        actual_after = _state_version(caller_state.generation + 1, applied)
        intended_delta = _delta_hash(caller_state.state_version_sha256, intended_after, proposal)
        actual_delta = _delta_hash(caller_state.state_version_sha256, actual_after, applied)
        assert transition.intended_after_state_version_sha256 == intended_after
        assert transition.intended_delta_sha256 == intended_delta
        assert transition.actual_delta_sha256 == actual_delta
        assert transition.after_state.state_version_sha256 == actual_after
        assert transition.after_state.generation == caller_state.generation + 1
        assert transition.after_state.cell_payload is applied
    preimage = _transition_preimage(
        input_hash,
        outcome,
        caller_state.state_version_sha256,
        transition.intended_after_state_version_sha256,
        transition.intended_delta_sha256,
        transition.actual_delta_sha256,
        transition.after_state.state_version_sha256,
    )
    assert transition.transition_sha256 == _h(preimage)
    _assert_fixed(transition, TRANSITION_FIXED)


def _mutant_module(kind: str) -> Any:
    tree = ast.parse(SOURCE_PATH.read_text(encoding="utf-8"), filename=str(SOURCE_PATH))
    changed = 0

    class DigestOnly(ast.NodeTransformer):
        def visit_Compare(self, node: ast.Compare) -> Any:
            nonlocal changed
            node = self.generic_visit(node)
            if len(node.ops) != 1 or not isinstance(node.ops[0], (ast.Eq, ast.NotEq)):
                return node
            operands = (node.left, node.comparators[0])
            names = tuple(ast.unparse(value) for value in operands)
            identity = any(value.endswith(".cell_payload") for value in names) and "proposed_payload" in names
            alternate = "alternate_payload" in names and (
                "proposed_payload" in names or any(value.endswith(".cell_payload") for value in names)
            )
            if (kind == "identity" and identity) or (kind == "alternate" and alternate):
                node.left = ast.Call(ast.Name("_raw_payload_sha256", ast.Load()), [operands[0]], [])
                node.comparators[0] = ast.Call(
                    ast.Name("_raw_payload_sha256", ast.Load()), [operands[1]], []
                )
                changed += 1
            return node

    tree = DigestOnly().visit(tree)
    ast.fix_missing_locations(tree)
    assert changed >= (1 if kind == "identity" else 2)
    name = f"_uprime_fake_cas_{kind}_mutant"
    module = types.ModuleType(name)
    module.__file__ = str(SOURCE_PATH)
    sys.modules[name] = module
    try:
        exec(compile(tree, str(SOURCE_PATH), "exec"), module.__dict__)
    finally:
        sys.modules.pop(name, None)
    return module


def test_uprime_fake_cas_exact_surface_fields_imports_and_signatures() -> None:
    assert cas.__all__ == [
        "InMemoryFakeCasV10Error",
        "InMemoryFakeCasStateV10",
        "InMemoryFakeCasTransitionV10",
        "initial_in_memory_fake_cas_state_v1_0",
        "step_in_memory_fake_cas_v1_0",
    ]
    assert cas.InMemoryFakeCasV10Error.__bases__ == (ValueError,)
    assert tuple(field.name for field in fields(cas.InMemoryFakeCasStateV10)) == STATE_FIELDS
    assert tuple(field.name for field in fields(cas.InMemoryFakeCasTransitionV10)) == TRANSITION_FIELDS
    assert tuple(cas.InMemoryFakeCasStateV10.__slots__) == STATE_FIELDS
    assert tuple(cas.InMemoryFakeCasTransitionV10.__slots__) == TRANSITION_FIELDS
    assert len(cas.InMemoryFakeCasStateV10.__annotations__) == 26
    assert len(cas.InMemoryFakeCasTransitionV10.__annotations__) == 66
    state_annotations = {name: "str" for name in STATE_FIELDS}
    state_annotations.update(
        generation="int",
        cell_payload="bytes | None",
        cell_payload_bytes="int | None",
        cell_payload_sha256="str | None",
        payload_byte_limit="int",
        generation_upper_bound="int",
        canonical_remote_authority="bool",
        licenses_execution="bool",
        licenses_publication="bool",
        licenses_recovery="bool",
        licenses_later_stage="bool",
    )
    transition_annotations = {name: "str" for name in TRANSITION_FIELDS}
    transition_annotations.update(
        before_state="InMemoryFakeCasStateV10",
        after_state="InMemoryFakeCasStateV10",
        proposed_payload="bytes",
        proposed_payload_bytes="int",
        alternate_payload="bytes | None",
        alternate_payload_bytes="int | None",
        alternate_payload_sha256="str | None",
        reason_codes="tuple[str, ...]",
        expected_version_match="bool",
        proposed_equal_before="bool | None",
        directive_reached="bool",
        alternate_semantics_checked="bool",
        state_changed="bool",
        cell_mutation_count="int",
        intended_after_state_version_sha256="str | None",
        intended_delta_sha256="str | None",
        actual_delta_sha256="str | None",
        payload_byte_limit="int",
        generation_upper_bound="int",
        unique_retained_payload_reference_upper_bound_bytes="int",
        retained_payload_copy_upper_bound_bytes="int",
        state_hash_preimage_upper_bound_bytes="int",
        input_hash_preimage_upper_bound_bytes="int",
        delta_hash_preimage_upper_bound_bytes="int",
        transition_hash_preimage_upper_bound_bytes="int",
        canonical_remote_authority="bool",
        licenses_execution="bool",
        licenses_publication="bool",
        licenses_recovery="bool",
        licenses_later_stage="bool",
    )
    assert cas.InMemoryFakeCasStateV10.__annotations__ == state_annotations
    assert cas.InMemoryFakeCasTransitionV10.__annotations__ == transition_annotations
    for cls in (cas.InMemoryFakeCasStateV10, cas.InMemoryFakeCasTransitionV10):
        assert cls.__dataclass_params__.frozen is True
        assert all(type(field.type) is str for field in fields(cls))
    initial_signature = inspect.signature(cas.initial_in_memory_fake_cas_state_v1_0)
    assert tuple(initial_signature.parameters) == ()
    assert initial_signature.return_annotation == "InMemoryFakeCasStateV10"
    step_signature = inspect.signature(cas.step_in_memory_fake_cas_v1_0)
    assert tuple(step_signature.parameters) == (
        "state", "expected_state_version_sha256", "proposed_payload",
        "synthetic_directive", "alternate_payload",
    )
    assert all(
        value.kind is inspect.Parameter.POSITIONAL_ONLY and value.default is inspect.Parameter.empty
        for value in step_signature.parameters.values()
    )
    assert [value.annotation for value in step_signature.parameters.values()] == [
        "InMemoryFakeCasStateV10",
        "str",
        "bytes",
        "str",
        "bytes | None",
    ]
    assert step_signature.return_annotation == "InMemoryFakeCasTransitionV10"
    seam_signature = inspect.signature(cas._raw_payload_sha256)
    assert tuple(seam_signature.parameters) == ("payload",)
    seam_parameter = next(iter(seam_signature.parameters.values()))
    assert seam_parameter.kind is inspect.Parameter.POSITIONAL_ONLY
    assert seam_parameter.default is inspect.Parameter.empty
    assert seam_parameter.annotation == "bytes"
    assert seam_signature.return_annotation == "str"
    tree = ast.parse(SOURCE_PATH.read_text(encoding="utf-8"), filename=str(SOURCE_PATH))
    imports = [node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))]
    assert [ast.unparse(node) for node in imports] == [
        "from __future__ import annotations",
        "from dataclasses import dataclass",
        "import hashlib",
        "import re",
    ]


def test_uprime_fake_cas_initial_state_present_states_and_state_goldens() -> None:
    assert (len(D_STATE), len(D_INPUT), len(D_DELTA), len(D_TRANSITION)) == (47, 47, 47, 52)
    assert _h(b"") == "E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855"
    assert _h(A) == "02D449A31FBB267C8F352E9968A79E3E5FC95C1BBEAA502FD6454EBDE5A4BEDC"
    assert _h(B) == "9F72EA0CF49536E3C66C787F705186DF9A4378083753AE9536D65B3AD7FCDDC4"
    assert _h(C) == "DEB0E38CED1E41DE6F92E70E80C418D2D356AFAAA99E26F5939DBC7D3EF4772A"
    initial = cas.initial_in_memory_fake_cas_state_v1_0()
    assert initial.generation == 0
    assert initial.cell_state == "absent"
    assert initial.cell_payload is None
    assert initial.cell_payload_bytes is None
    assert initial.cell_payload_sha256 is None
    _assert_fixed(initial, STATE_FIXED)
    for (generation, payload), golden in STATE_GOLDENS.items():
        value = initial if payload is None else _state(generation, payload)
        assert value.state_version_sha256 == golden == _state_version(generation, payload)
        assert len(_state_preimage(generation, payload)) == (
            56 if payload is None else 64 + len(payload)
        )
        if payload is not None:
            assert value.cell_payload is payload
            assert value.cell_payload_bytes == len(payload)
            assert value.cell_payload_sha256 == _h(payload)
    second = cas.initial_in_memory_fake_cas_state_v1_0()
    assert second == initial and second is not initial
    with pytest.raises(FrozenInstanceError):
        initial.generation = 1


def test_uprime_fake_cas_six_outcomes_exact_rows_hashes_and_identity() -> None:
    absent = cas.initial_in_memory_fake_cas_state_v1_0()
    a1 = _state(1, A)
    cases = (
        (a1, absent.state_version_sha256, B, DIRECTIVES[0], None, OUTCOMES[0]),
        (a1, a1.state_version_sha256, A, DIRECTIVES[3], A, OUTCOMES[1]),
        (a1, a1.state_version_sha256, B, DIRECTIVES[0], None, OUTCOMES[2]),
        (a1, a1.state_version_sha256, B, DIRECTIVES[1], None, OUTCOMES[3]),
        (a1, a1.state_version_sha256, B, DIRECTIVES[2], None, OUTCOMES[4]),
        (a1, a1.state_version_sha256, B, DIRECTIVES[3], C, OUTCOMES[5]),
    )
    observed: dict[str, Any] = {}
    for state, expected, proposal, directive, alternate, outcome in cases:
        transition = cas.step_in_memory_fake_cas_v1_0(
            state, expected, proposal, directive, alternate
        )
        observed[outcome] = transition
        _assert_transition(transition, state, expected, proposal, directive, alternate, outcome)
        input_golden, transition_golden, preimage_length = CASE_GOLDENS[outcome]
        assert transition.input_sha256 == input_golden
        assert transition.transition_sha256 == transition_golden
        assert len(_transition_preimage(
            transition.input_sha256, transition.outcome,
            transition.before_state.state_version_sha256,
            transition.intended_after_state_version_sha256,
            transition.intended_delta_sha256, transition.actual_delta_sha256,
            transition.after_state.state_version_sha256,
        )) == preimage_length
    intended = [observed[name] for name in OUTCOMES[2:5]]
    assert intended[0].after_state == intended[1].after_state == intended[2].after_state
    assert len({value.intended_after_state_version_sha256 for value in intended}) == 1
    assert len({value.intended_delta_sha256 for value in intended}) == 1
    assert len({value.actual_delta_sha256 for value in intended}) == 1
    empty = b""
    absent_to_empty = cas.step_in_memory_fake_cas_v1_0(
        absent, absent.state_version_sha256, empty, DIRECTIVES[0], None
    )
    _assert_transition(
        absent_to_empty, absent, absent.state_version_sha256,
        empty, DIRECTIVES[0], None, OUTCOMES[2],
    )
    assert absent_to_empty.input_sha256 == "585819082B18EAEA705AC995E9D8EADFC7333E7012096227D9AA3FFDF9A1378E"
    assert absent_to_empty.transition_sha256 == "194FC9297D81669BDE36952C414D47F013FD0DBF4A51DA175B2649447DEE1AAF"
    assert absent_to_empty.actual_delta_sha256 == "20AD941541E39F3946D29013EFCA76B3A4BB928CB028A9AA254F60BAE1A39B76"


def test_uprime_fake_cas_conflict_identity_and_alternate_precedence() -> None:
    absent = cas.initial_in_memory_fake_cas_state_v1_0()
    a1 = _state(1, A)
    for index, directive in enumerate(DIRECTIVES):
        alternate = C if index == 3 else None
        conflict = cas.step_in_memory_fake_cas_v1_0(
            a1, absent.state_version_sha256, B, directive, alternate
        )
        assert conflict.outcome == OUTCOMES[0]
        identity_alternate = A if index == 3 else None
        identical = cas.step_in_memory_fake_cas_v1_0(
            a1, a1.state_version_sha256, A, directive, identity_alternate
        )
        assert identical.outcome == OUTCOMES[1]
    stale_exact = cas.step_in_memory_fake_cas_v1_0(
        a1, absent.state_version_sha256, A, DIRECTIVES[3], A
    )
    assert stale_exact.outcome == OUTCOMES[0]
    stale_relationally_invalid = cas.step_in_memory_fake_cas_v1_0(
        a1, absent.state_version_sha256, B, DIRECTIVES[3], B
    )
    assert stale_relationally_invalid.outcome == OUTCOMES[0]
    for bad_alternate in (B, A):
        with pytest.raises(cas.InMemoryFakeCasV10Error):
            cas.step_in_memory_fake_cas_v1_0(
                a1, a1.state_version_sha256, B, DIRECTIVES[3], bad_alternate
            )
    with pytest.raises(cas.InMemoryFakeCasV10Error):
        cas.step_in_memory_fake_cas_v1_0(
            a1, a1.state_version_sha256, B, DIRECTIVES[0], C
        )


def test_uprime_fake_cas_max_generation_no_wrap_and_no_seventh_outcome() -> None:
    maximum = _state(MAX_GENERATION, A)
    stale = cas.step_in_memory_fake_cas_v1_0(
        maximum, STATE_GOLDENS[(0, None)], B, DIRECTIVES[0], None
    )
    assert stale.outcome == OUTCOMES[0]
    identical = cas.step_in_memory_fake_cas_v1_0(
        maximum, maximum.state_version_sha256, A, DIRECTIVES[0], None
    )
    assert identical.outcome == OUTCOMES[1]
    before = _mapping(maximum)
    with pytest.raises(cas.InMemoryFakeCasV10Error):
        cas.step_in_memory_fake_cas_v1_0(
            maximum, maximum.state_version_sha256, B, DIRECTIVES[0], None
        )
    assert _mapping(maximum) == before
    penultimate = _state(MAX_GENERATION - 1, A)
    final = cas.step_in_memory_fake_cas_v1_0(
        penultimate, penultimate.state_version_sha256, B, DIRECTIVES[0], None
    )
    assert final.after_state.generation == MAX_GENERATION
    assert set(OUTCOMES) == {
        "conflict_no_change", "existing_identical_no_change",
        "intended_applied_acknowledged", "intended_applied_ack_lost_confirmed",
        "intended_applied_ack_lost_unconfirmed", "wrong_delta_confirmed",
    }


def test_uprime_fake_cas_aba_forks_and_snapshot_isolation() -> None:
    a1 = _state(1, A)
    to_b = cas.step_in_memory_fake_cas_v1_0(
        a1, a1.state_version_sha256, B, DIRECTIVES[0], None
    )
    to_c = cas.step_in_memory_fake_cas_v1_0(
        a1, a1.state_version_sha256, C, DIRECTIVES[0], None
    )
    assert to_b.after_state.generation == to_c.after_state.generation == 2
    assert to_b.after_state.state_version_sha256 != to_c.after_state.state_version_sha256
    cross = cas.step_in_memory_fake_cas_v1_0(
        to_c.after_state, to_b.after_state.state_version_sha256, D, DIRECTIVES[0], None
    )
    assert cross.outcome == OUTCOMES[0]
    back_to_a = cas.step_in_memory_fake_cas_v1_0(
        to_b.after_state, to_b.after_state.state_version_sha256, A, DIRECTIVES[0], None
    )
    assert back_to_a.after_state.state_version_sha256 == STATE_GOLDENS[(3, A)]
    assert back_to_a.after_state.cell_payload == a1.cell_payload
    assert back_to_a.after_state.state_version_sha256 != a1.state_version_sha256
    old_expected = cas.step_in_memory_fake_cas_v1_0(
        back_to_a.after_state, a1.state_version_sha256, C, DIRECTIVES[0], None
    )
    assert old_expected.outcome == OUTCOMES[0]
    caller = _state(1, A)
    transition = cas.step_in_memory_fake_cas_v1_0(
        caller, caller.state_version_sha256, B, DIRECTIVES[0], None
    )
    object.__setattr__(caller, "generation", 999)
    object.__setattr__(caller, "cell_payload", C)
    assert transition.before_state.generation == 1
    assert transition.before_state.cell_payload is A
    assert transition.after_state.cell_payload is B


def test_uprime_fake_cas_forced_raw_sha_collision_seam_preserves_raw_semantics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    collision = "A" * 64
    with monkeypatch.context() as context:
        context.setattr(cas, "_raw_payload_sha256", lambda payload, /: collision)
        a1 = _state(1, A)
        intended = cas.step_in_memory_fake_cas_v1_0(
            a1, a1.state_version_sha256, B, DIRECTIVES[0], None
        )
        wrong = cas.step_in_memory_fake_cas_v1_0(
            a1, a1.state_version_sha256, B, DIRECTIVES[3], C
        )
        assert a1.cell_payload_sha256 == intended.proposed_payload_sha256 == collision
        assert wrong.alternate_payload_sha256 == collision
        assert intended.outcome == OUTCOMES[2]
        assert wrong.outcome == OUTCOMES[5]
        assert intended.after_state.cell_payload is B
        assert wrong.after_state.cell_payload is C
        assert a1.state_version_sha256 == STATE_GOLDENS[(1, A)]
        assert intended.after_state.state_version_sha256 == STATE_GOLDENS[(2, B)]
        assert wrong.after_state.state_version_sha256 == STATE_GOLDENS[(2, C)]
    assert cas._raw_payload_sha256(A) == _h(A)


def test_uprime_fake_cas_ast_raw_comparisons_and_digest_only_mutants_die() -> None:
    tree = ast.parse(SOURCE_PATH.read_text(encoding="utf-8"), filename=str(SOURCE_PATH))
    comparisons = [node for node in ast.walk(tree) if isinstance(node, ast.Compare)]
    rendered = [ast.unparse(node) for node in comparisons]
    assert any(".cell_payload == proposed_payload" in value for value in rendered)
    assert any(
        "alternate_payload == proposed_payload" in value
        or "alternate_payload != proposed_payload" in value
        for value in rendered
    )
    assert not any("cell_payload_sha256" in value for value in rendered)
    for kind in ("identity", "alternate"):
        mutant = _mutant_module(kind)
        mutant._raw_payload_sha256 = lambda payload, /: "A" * 64
        a1 = _state_for(mutant, 1, A)
        if kind == "identity":
            result = mutant.step_in_memory_fake_cas_v1_0(
                a1, a1.state_version_sha256, B, DIRECTIVES[0], None
            )
            assert result.outcome != OUTCOMES[2]
        else:
            with pytest.raises(mutant.InMemoryFakeCasV10Error):
                mutant.step_in_memory_fake_cas_v1_0(
                    a1, a1.state_version_sha256, B, DIRECTIVES[3], C
                )


def _forged_value(name: str, value: Any) -> Any:
    if name in {"before_state", "after_state"}:
        return cas.initial_in_memory_fake_cas_state_v1_0()
    if value is None:
        if name.endswith("payload"):
            return b"forged"
        if name.endswith("bytes"):
            return 0
        return "A" * 64
    if type(value) is bool:
        return not value
    if type(value) is int:
        return value + 1
    if type(value) is str:
        return value + "_forged"
    if type(value) is bytes:
        return value + b"_forged"
    if type(value) is tuple:
        return value + ("forged",)
    raise AssertionError((name, type(value)))


def test_uprime_fake_cas_state_and_transition_constructors_revalidate_every_field(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    initial = cas.initial_in_memory_fake_cas_state_v1_0()
    a1 = _state(1, A)
    initial_mapping = _mapping(initial)
    rebuilt_initial = cas.InMemoryFakeCasStateV10(**initial_mapping)
    assert rebuilt_initial == initial and rebuilt_initial is not initial
    for base in (initial, a1):
        base_mapping = _mapping(base)
        for name in STATE_FIELDS:
            forged = dict(base_mapping)
            forged[name] = _forged_value(name, forged[name])
            with pytest.raises(cas.InMemoryFakeCasV10Error):
                cas.InMemoryFakeCasStateV10(**forged)
            with pytest.raises(cas.InMemoryFakeCasV10Error):
                replace(base, **{name: forged[name]})

    transition = cas.step_in_memory_fake_cas_v1_0(
        a1, a1.state_version_sha256, B, DIRECTIVES[0], None
    )
    conflict = cas.step_in_memory_fake_cas_v1_0(
        a1, initial.state_version_sha256, B, DIRECTIVES[0], None
    )
    wrong = cas.step_in_memory_fake_cas_v1_0(
        a1, a1.state_version_sha256, B, DIRECTIVES[3], C
    )
    for base in (transition, conflict, wrong):
        transition_mapping = _mapping(base)
        rebuilt_transition = cas.InMemoryFakeCasTransitionV10(**transition_mapping)
        assert rebuilt_transition == base and rebuilt_transition is not base
        if base.state_changed:
            assert rebuilt_transition.after_state.cell_payload is (
                base.alternate_payload if base.outcome == OUTCOMES[5] else base.proposed_payload
            )
        else:
            assert rebuilt_transition.after_state is rebuilt_transition.before_state
        assert replace(base) == base
        for name in TRANSITION_FIELDS:
            forged = dict(transition_mapping)
            forged[name] = _forged_value(name, forged[name])
            with pytest.raises(cas.InMemoryFakeCasV10Error):
                cas.InMemoryFakeCasTransitionV10(**forged)
            with pytest.raises(cas.InMemoryFakeCasV10Error):
                replace(base, **{name: forged[name]})

    transition_mapping = _mapping(transition)

    bypass = _state(1, A)
    object.__setattr__(bypass, "cell_payload_sha256", "A" * 64)
    with pytest.raises(cas.InMemoryFakeCasV10Error):
        cas.step_in_memory_fake_cas_v1_0(
            bypass, bypass.state_version_sha256, B, DIRECTIVES[0], None
        )
    nested_bypass = transition.before_state
    object.__setattr__(nested_bypass, "generation", 99)
    forged_nested = dict(transition_mapping)
    forged_nested["before_state"] = nested_bypass
    with pytest.raises(cas.InMemoryFakeCasV10Error):
        cas.InMemoryFakeCasTransitionV10(**forged_nested)

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("Transition validation called a public function")

    monkeypatch.setattr(cas, "initial_in_memory_fake_cas_state_v1_0", forbidden)
    monkeypatch.setattr(cas, "step_in_memory_fake_cas_v1_0", forbidden)
    clean_mapping = _mapping(transition)
    # The original nested state above was bypass-mutated; replace it with a clean snapshot.
    clean = _state(1, A)
    clean_transition = cas.InMemoryFakeCasTransitionV10(
        **{
            **clean_mapping,
            "before_state": clean,
            "after_state": _state(2, B),
        }
    )
    assert clean_transition.outcome == OUTCOMES[2]


def test_uprime_fake_cas_exact_type_call_shape_and_boundary_rejection() -> None:
    class StrSubclass(str):
        pass

    class BytesSubclass(bytes):
        pass

    initial = cas.initial_in_memory_fake_cas_state_v1_0()
    a1 = _state(1, A)

    class StateSubclass(cas.InMemoryFakeCasStateV10):
        pass

    state_subclass = object.__new__(StateSubclass)
    for name, value in _mapping(a1).items():
        object.__setattr__(state_subclass, name, value)
    with pytest.raises(cas.InMemoryFakeCasV10Error):
        cas.step_in_memory_fake_cas_v1_0(
            state_subclass, state_subclass.state_version_sha256, B, DIRECTIVES[0], None
        )
    with pytest.raises(cas.InMemoryFakeCasV10Error):
        StateSubclass(**_mapping(a1))

    base_transition = cas.step_in_memory_fake_cas_v1_0(
        a1, a1.state_version_sha256, B, DIRECTIVES[0], None
    )

    class TransitionSubclass(cas.InMemoryFakeCasTransitionV10):
        pass

    with pytest.raises(cas.InMemoryFakeCasV10Error):
        TransitionSubclass(**_mapping(base_transition))
    with pytest.raises(cas.InMemoryFakeCasV10Error):
        replace(base_transition, reason_codes=list(base_transition.reason_codes))
    with pytest.raises(TypeError):
        cas.step_in_memory_fake_cas_v1_0(a1, a1.state_version_sha256, B, DIRECTIVES[0])
    with pytest.raises(TypeError):
        cas.step_in_memory_fake_cas_v1_0(
            state=a1,
            expected_state_version_sha256=a1.state_version_sha256,
            proposed_payload=B,
            synthetic_directive=DIRECTIVES[0],
            alternate_payload=None,
        )
    invalid_calls = (
        (object(), a1.state_version_sha256, B, DIRECTIVES[0], None),
        (a1, 1, B, DIRECTIVES[0], None),
        (a1, StrSubclass(a1.state_version_sha256), B, DIRECTIVES[0], None),
        (a1, a1.state_version_sha256.lower(), B, DIRECTIVES[0], None),
        (a1, "a" + a1.state_version_sha256[1:], B, DIRECTIVES[0], None),
        (a1, "A" * 63, B, DIRECTIVES[0], None),
        (a1, a1.state_version_sha256, bytearray(B), DIRECTIVES[0], None),
        (a1, a1.state_version_sha256, memoryview(B), DIRECTIVES[0], None),
        (a1, a1.state_version_sha256, BytesSubclass(B), DIRECTIVES[0], None),
        (a1, a1.state_version_sha256, B, StrSubclass(DIRECTIVES[0]), None),
        (a1, a1.state_version_sha256, B, "invalid_directive", None),
        (a1, a1.state_version_sha256, B, DIRECTIVES[0], b"unexpected"),
        (a1, a1.state_version_sha256, B, DIRECTIVES[3], None),
        (a1, a1.state_version_sha256, B, DIRECTIVES[3], bytearray(C)),
        (a1, a1.state_version_sha256, B, DIRECTIVES[3], memoryview(C)),
        (a1, a1.state_version_sha256, B, DIRECTIVES[3], BytesSubclass(C)),
    )
    for args in invalid_calls:
        with pytest.raises(cas.InMemoryFakeCasV10Error):
            cas.step_in_memory_fake_cas_v1_0(*args)

    for name, value in (
        ("generation", True),
        ("generation", -1),
        ("generation", 0),
        ("generation", MAX_GENERATION + 1),
        ("cell_payload", bytearray(A)),
        ("cell_payload", memoryview(A)),
        ("cell_payload", BytesSubclass(A)),
        ("cell_payload_bytes", True),
        ("cell_payload_sha256", _h(A).lower()),
        ("canonical_remote_authority", 0),
        ("state_scope", StrSubclass(STATE_FIXED["state_scope"])),
    ):
        mapping = _mapping(a1)
        mapping[name] = value
        with pytest.raises(cas.InMemoryFakeCasV10Error):
            cas.InMemoryFakeCasStateV10(**mapping)

    maximum_minus_one = b"x" * (MAX_PAYLOAD_BYTES - 1)
    maximum = b"y" * MAX_PAYLOAD_BYTES
    assert _state(1, maximum_minus_one).cell_payload_bytes == MAX_PAYLOAD_BYTES - 1
    assert _state(1, maximum).cell_payload_bytes == MAX_PAYLOAD_BYTES
    with pytest.raises(cas.InMemoryFakeCasV10Error):
        _state(1, b"z" * (MAX_PAYLOAD_BYTES + 1))
    max_proposal = cas.step_in_memory_fake_cas_v1_0(
        initial, initial.state_version_sha256, maximum, DIRECTIVES[0], None
    )
    assert max_proposal.after_state.cell_payload is maximum
    with pytest.raises(cas.InMemoryFakeCasV10Error):
        cas.step_in_memory_fake_cas_v1_0(
            initial, initial.state_version_sha256,
            b"z" * (MAX_PAYLOAD_BYTES + 1), DIRECTIVES[0], None,
        )
    assert _state(MAX_GENERATION - 1, A).generation == MAX_GENERATION - 1
    assert _state(MAX_GENERATION, A).generation == MAX_GENERATION


def test_uprime_fake_cas_equal_valued_wrong_types_and_deleted_slots_reject(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class StrSubclass(str):
        pass

    class IntSubclass(int):
        pass

    class BytesSubclass(bytes):
        pass

    class TupleSubclass(tuple):
        pass

    a1 = _state(1, bytes(bytearray(b"A")))
    state_annotations = cas.InMemoryFakeCasStateV10.__annotations__
    state_variants: list[tuple[str, Any]] = []
    for name in STATE_FIELDS:
        value = getattr(a1, name)
        annotation = state_annotations[name]
        if annotation == "str":
            state_variants.append((name, StrSubclass(value)))
        elif annotation == "int":
            state_variants.append((name, IntSubclass(value)))
        elif annotation == "bool":
            state_variants.append((name, int(value)))
        elif annotation == "bytes | None" and value is not None:
            state_variants.append((name, BytesSubclass(value)))
        elif annotation == "int | None" and value is not None:
            state_variants.append((name, IntSubclass(value)))
        elif annotation == "str | None" and value is not None:
            state_variants.append((name, StrSubclass(value)))
    state_variants.extend((('generation', True), ('cell_payload_bytes', True)))
    for name, wrong_type_equal_value in state_variants:
        assert wrong_type_equal_value == getattr(a1, name)
        with pytest.raises(cas.InMemoryFakeCasV10Error):
            cas.InMemoryFakeCasStateV10(
                **{**_mapping(a1), name: wrong_type_equal_value}
            )
        with pytest.raises(cas.InMemoryFakeCasV10Error):
            replace(a1, **{name: wrong_type_equal_value})

    proposal = bytes(bytearray(b"B"))
    alternate = bytes(bytearray(b"C"))
    transition = cas.step_in_memory_fake_cas_v1_0(
        a1, a1.state_version_sha256, proposal, DIRECTIVES[3], alternate
    )
    annotations = cas.InMemoryFakeCasTransitionV10.__annotations__
    variants: list[tuple[str, Any]] = []
    for name in TRANSITION_FIELDS:
        value = getattr(transition, name)
        annotation = annotations[name]
        if annotation == "str":
            variants.append((name, StrSubclass(value)))
        elif annotation == "int":
            variants.append((name, IntSubclass(value)))
        elif annotation == "bool":
            variants.append((name, int(value)))
        elif annotation == "bytes":
            variants.append((name, BytesSubclass(value)))
        elif annotation == "str | None" and value is not None:
            variants.append((name, StrSubclass(value)))
        elif annotation == "int | None" and value is not None:
            variants.append((name, IntSubclass(value)))
        elif annotation == "bool | None" and value is not None:
            variants.append((name, int(value)))
        elif annotation == "bytes | None" and value is not None:
            variants.append((name, BytesSubclass(value)))
        elif annotation == "tuple[str, ...]":
            variants.append((name, TupleSubclass(value)))
    # Explicit bool-as-int cases are equality-indistinguishable from integer 1.
    variants.extend(
        (
            ("proposed_payload_bytes", True),
            ("cell_mutation_count", True),
            ("alternate_payload_bytes", True),
        )
    )
    assert {name for name, _ in variants}.issuperset(
        {
            "transition_schema_version",
            "proposed_payload",
            "proposed_payload_bytes",
            "alternate_payload",
            "alternate_payload_bytes",
            "reason_codes",
            "expected_version_match",
            "proposed_equal_before",
            "cell_mutation_count",
            "payload_byte_limit",
            "canonical_remote_authority",
        }
    )
    for name, wrong_type_equal_value in variants:
        assert wrong_type_equal_value == getattr(transition, name)
        with pytest.raises(cas.InMemoryFakeCasV10Error):
            cas.InMemoryFakeCasTransitionV10(
                **{**_mapping(transition), name: wrong_type_equal_value}
            )
        with pytest.raises(cas.InMemoryFakeCasV10Error):
            replace(transition, **{name: wrong_type_equal_value})

    class StateSubclass(cas.InMemoryFakeCasStateV10):
        pass

    nested_subclass = object.__new__(StateSubclass)
    for name, value in _mapping(transition.before_state).items():
        object.__setattr__(nested_subclass, name, value)
    with pytest.raises(cas.InMemoryFakeCasV10Error):
        cas.InMemoryFakeCasTransitionV10(
            **{**_mapping(transition), "before_state": nested_subclass}
        )
    with pytest.raises(cas.InMemoryFakeCasV10Error):
        replace(transition, before_state=nested_subclass)

    class ExplosiveStr(str):
        def __eq__(self, other: object) -> bool:
            raise AssertionError("oversized reason tuple traversed an element")

        def __hash__(self) -> int:
            raise AssertionError("oversized reason tuple hashed an element")

    two_reasons = (transition.reason_codes[0], transition.reason_codes[0])
    huge_reasons = (ExplosiveStr(transition.reason_codes[0]),) * 100_000
    with monkeypatch.context() as context:

        def forbidden_derivation(*args: Any, **kwargs: Any) -> Any:
            raise AssertionError("invalid reason tuple reached semantic derivation")

        context.setattr(cas, "_derive_transition_values", forbidden_derivation)
        for invalid_reasons in (two_reasons, huge_reasons):
            with pytest.raises(cas.InMemoryFakeCasV10Error):
                cas.InMemoryFakeCasTransitionV10(
                    **{**_mapping(transition), "reason_codes": invalid_reasons}
                )
            with pytest.raises(cas.InMemoryFakeCasV10Error):
                replace(transition, reason_codes=invalid_reasons)

    deleted = _state(1, A)
    object.__delattr__(deleted, "cell_state")
    with pytest.raises(cas.InMemoryFakeCasV10Error):
        cas.step_in_memory_fake_cas_v1_0(
            deleted, deleted.state_version_sha256, B, DIRECTIVES[0], None
        )


def test_uprime_fake_cas_outcome_table_same_length_mutation_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frozen_rows = cas._OUTCOME_ROWS
    rows = [list(row) for row in frozen_rows]
    original = rows[2][0]
    rows[2][0] = original[:-1] + ("X" if original[-1] != "X" else "Y")
    assert len(rows[2][0]) == len(original) and rows[2][0] != original
    same_length_cell_mutation = tuple(tuple(row) for row in rows)

    class StrSubclass(str):
        pass

    class TupleSubclass(tuple):
        pass

    wrong_row_type = (list(frozen_rows[0]),) + frozen_rows[1:]
    wrong_row_subclass = (TupleSubclass(frozen_rows[0]),) + frozen_rows[1:]
    wrong_row_length = (frozen_rows[0][:-1],) + frozen_rows[1:]
    wrong_cell_type = ((1,) + frozen_rows[0][1:],) + frozen_rows[1:]
    wrong_cell_subclass = (
        (StrSubclass(frozen_rows[0][0]),) + frozen_rows[0][1:],
    ) + frozen_rows[1:]
    malformed_tables = (
        None,
        list(frozen_rows),
        TupleSubclass(frozen_rows),
        frozen_rows[:-1],
        (None,) * 6,
        wrong_row_type,
        wrong_row_subclass,
        wrong_row_length,
        wrong_cell_type,
        wrong_cell_subclass,
        same_length_cell_mutation,
    )

    valid_state = _state(1, A)
    valid_transition = cas.step_in_memory_fake_cas_v1_0(
        valid_state, valid_state.state_version_sha256, B, DIRECTIVES[0], None
    )
    state_mapping = _mapping(valid_state)
    transition_mapping = _mapping(valid_transition)
    for malformed in malformed_tables:
        with monkeypatch.context() as context:
            context.setattr(cas, "_OUTCOME_ROWS", malformed)

            def forbidden_hash(*args: Any, **kwargs: Any) -> Any:
                raise AssertionError("hashing occurred before outcome-table validation")

            def forbidden_preimage_iteration(*args: Any, **kwargs: Any) -> Any:
                raise AssertionError(
                    "preimage-length iteration occurred before outcome-table validation"
                )

            context.setattr(cas.hashlib, "sha256", forbidden_hash)
            context.setattr(
                cas,
                "_transition_preimage_lengths",
                forbidden_preimage_iteration,
            )
            operations = (
                lambda: cas.initial_in_memory_fake_cas_state_v1_0(),
                lambda: cas.step_in_memory_fake_cas_v1_0(
                    valid_state,
                    valid_state.state_version_sha256,
                    C,
                    DIRECTIVES[0],
                    None,
                ),
                lambda: cas.InMemoryFakeCasStateV10(**state_mapping),
                lambda: cas.InMemoryFakeCasTransitionV10(**transition_mapping),
            )
            for operation in operations:
                with pytest.raises(cas.InMemoryFakeCasV10Error):
                    operation()


def test_uprime_fake_cas_structural_invalids_precede_conflict_and_identity() -> None:
    absent = cas.initial_in_memory_fake_cas_state_v1_0()
    a1 = _state(1, A)
    stale = absent.state_version_sha256
    bad_state = _state(1, A)
    object.__setattr__(bad_state, "cell_payload_bytes", 31)
    cases = (
        (bad_state, stale, B, DIRECTIVES[0], None),
        (a1, "a" * 64, B, DIRECTIVES[0], None),
        (a1, stale, bytearray(B), DIRECTIVES[0], None),
        (a1, stale, B, "invalid_directive", None),
        (a1, stale, B, DIRECTIVES[0], C),
        (a1, stale, B, DIRECTIVES[3], None),
    )
    for args in cases:
        with pytest.raises(cas.InMemoryFakeCasV10Error):
            cas.step_in_memory_fake_cas_v1_0(*args)
    for args in (
        (a1, a1.state_version_sha256, A, "invalid_directive", None),
        (a1, a1.state_version_sha256, A, DIRECTIVES[0], C),
        (a1, a1.state_version_sha256, A, DIRECTIVES[3], None),
    ):
        with pytest.raises(cas.InMemoryFakeCasV10Error):
            cas.step_in_memory_fake_cas_v1_0(*args)


def test_uprime_fake_cas_hash_framing_mutation_and_resource_arithmetic() -> None:
    assert (MAX_PAYLOAD_BYTES, MAX_GENERATION) == (1_048_576, 9_223_372_036_854_775_807)
    assert 47 + 8 + 1 + 8 + MAX_PAYLOAD_BYTES == 1_048_640
    assert 47 + 32 + 8 + MAX_PAYLOAD_BYTES + 1 + 1 + 8 + MAX_PAYLOAD_BYTES == 2_097_249
    assert 47 + 32 + 32 + 8 + MAX_PAYLOAD_BYTES == 1_048_695
    assert _o(None) != _o(b"") and _q(None) != _q("A" * 64)
    assert len(_state_preimage(0, None)) == 56
    assert len(_state_preimage(1, b"")) == 64
    assert len(_state_preimage(1, A)) == 96
    assert _delta_hash(STATE_GOLDENS[(1, A)], STATE_GOLDENS[(2, B)], B) == (
        "C9721CC95913641245C355752E2DCD70541926FADC02681BEF26920E11FD23C6"
    )
    assert _delta_hash(STATE_GOLDENS[(1, A)], STATE_GOLDENS[(2, C)], C) == (
        "5FA97222CD85C7DCA8284AEE6314270822D45681EC32AA39094E10B8CB857B23"
    )
    baseline = _input_hash(STATE_GOLDENS[(1, A)], B, DIRECTIVES[3], C)
    mutations = {
        _input_hash(STATE_GOLDENS[(0, None)], B, DIRECTIVES[3], C),
        _input_hash(STATE_GOLDENS[(1, A)], D, DIRECTIVES[3], C),
        _input_hash(STATE_GOLDENS[(1, A)], B, DIRECTIVES[2], None),
        _input_hash(STATE_GOLDENS[(1, A)], B, DIRECTIVES[3], D),
    }
    assert baseline not in mutations and len(mutations) == 4
    a1 = _state(1, A)
    transition = cas.step_in_memory_fake_cas_v1_0(
        a1, a1.state_version_sha256, B, DIRECTIVES[3], C
    )
    for field_name in (
        "input_sha256", "outcome", "reason_codes", "intended_apply_status",
        "effect_scope", "synthetic_acknowledgement_label",
        "same_kernel_confirmation_label", "synthetic_client_observation",
        "model_latent_effect", "intended_delta_sha256", "actual_delta_sha256",
        "transition_sha256",
    ):
        with pytest.raises(cas.InMemoryFakeCasV10Error):
            replace(transition, **{field_name: _forged_value(field_name, getattr(transition, field_name))})


def test_uprime_fake_cas_resource_constants_fail_before_hashing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = {
        "_MAX_PAYLOAD_BYTES": 1_048_576,
        "_MAX_GENERATION": 9_223_372_036_854_775_807,
        "_MAX_UNIQUE_RETAINED_PAYLOAD_REFERENCE_BYTES": 3_145_728,
        "_MAX_RETAINED_PAYLOAD_COPY_BYTES": 0,
        "_MAX_STATE_HASH_PREIMAGE_BYTES": 1_048_640,
        "_MAX_INPUT_HASH_PREIMAGE_BYTES": 2_097_249,
        "_MAX_DELTA_HASH_PREIMAGE_BYTES": 1_048_695,
        "_MAX_TRANSITION_HASH_PREIMAGE_BYTES": 467,
    }
    for name, value in expected.items():
        assert getattr(cas, name) == value
        with monkeypatch.context() as context:
            context.setattr(cas, name, True if value != 1 else value + 1)

            def forbidden(*args: Any, **kwargs: Any) -> Any:
                raise AssertionError("hashing occurred before resource validation")

            context.setattr(cas.hashlib, "sha256", forbidden)
            with pytest.raises(cas.InMemoryFakeCasV10Error):
                cas.initial_in_memory_fake_cas_state_v1_0()
    valid_state = _state(1, A)
    valid_transition = cas.step_in_memory_fake_cas_v1_0(
        valid_state, valid_state.state_version_sha256, B, DIRECTIVES[0], None
    )
    with monkeypatch.context() as context:
        context.setattr(cas, "_MAX_PAYLOAD_BYTES", True)

        def forbidden(*args: Any, **kwargs: Any) -> Any:
            raise AssertionError("hashing occurred before resource validation")

        context.setattr(cas.hashlib, "sha256", forbidden)
        with pytest.raises(cas.InMemoryFakeCasV10Error):
            cas.InMemoryFakeCasStateV10(**_mapping(valid_state))
        with pytest.raises(cas.InMemoryFakeCasV10Error):
            cas.InMemoryFakeCasTransitionV10(**_mapping(valid_transition))
        with pytest.raises(cas.InMemoryFakeCasV10Error):
            cas.step_in_memory_fake_cas_v1_0(
                valid_state, valid_state.state_version_sha256, C, DIRECTIVES[0], None
            )
    deleted = _state(1, A)
    object.__delattr__(deleted, "cell_state")
    for invalid_state in (object(), deleted):
        with monkeypatch.context() as context:
            context.setattr(cas, "_MAX_PAYLOAD_BYTES", True)

            def forbidden_snapshot(*args: Any, **kwargs: Any) -> Any:
                raise AssertionError("State snapshot preceded resource validation")

            def forbidden_hash(*args: Any, **kwargs: Any) -> Any:
                raise AssertionError("hashing preceded resource validation")

            context.setattr(cas, "_snapshot_state", forbidden_snapshot)
            context.setattr(cas.hashlib, "sha256", forbidden_hash)
            with pytest.raises(cas.InMemoryFakeCasV10Error):
                cas.step_in_memory_fake_cas_v1_0(
                    invalid_state, "A" * 64, B, DIRECTIVES[0], None
                )


def test_uprime_fake_cas_hashing_is_incremental_and_retains_no_payload_copy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    instances: list[Any] = []

    class SpyHash:
        def __init__(self, data: bytes = b"", **kwargs: Any) -> None:
            self.inner = REAL_SHA256()
            self.chunks: list[bytes] = []
            instances.append(self)
            if data:
                self.update(data)

        def update(self, data: bytes) -> None:
            assert type(data) is bytes
            self.chunks.append(data)
            self.inner.update(data)

        def hexdigest(self) -> str:
            return self.inner.hexdigest()

        def digest(self) -> bytes:
            return self.inner.digest()

        def copy(self) -> Any:
            copied = object.__new__(SpyHash)
            copied.inner = self.inner.copy()
            copied.chunks = list(self.chunks)
            instances.append(copied)
            return copied

    a1 = _state(1, A)
    with monkeypatch.context() as context:
        context.setattr(cas.hashlib, "sha256", SpyHash)
        transition = cas.step_in_memory_fake_cas_v1_0(
            a1, a1.state_version_sha256, B, DIRECTIVES[3], C
        )
    assert transition.outcome == OUTCOMES[5]
    totals = [(sum(len(chunk) for chunk in value.chunks), value.chunks) for value in instances]
    for expected_total in (96, 161, 151, 467):
        matching = [chunks for total, chunks in totals if total == expected_total]
        assert matching, expected_total
        assert all(len(chunks) > 1 for chunks in matching)
    assert max(len(chunk) for _, chunks in totals for chunk in chunks) <= len(D_TRANSITION)
    observed_chunks = [chunk for _, chunks in totals for chunk in chunks]
    assert any(chunk is A for chunk in observed_chunks)
    assert any(chunk is B for chunk in observed_chunks)
    assert any(chunk is C for chunk in observed_chunks)
    assert transition.before_state.cell_payload is A
    assert transition.proposed_payload is B
    assert transition.alternate_payload is C
    assert transition.after_state.cell_payload is C


def test_uprime_fake_cas_forbidden_capability_and_raw_equality_ast_sentinels() -> None:
    source = SOURCE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(SOURCE_PATH))
    assert not any(isinstance(node, (ast.Global, ast.Nonlocal, ast.AsyncFunctionDef)) for node in ast.walk(tree))
    public_functions = [
        node.name for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_")
    ]
    assert public_functions == [
        "initial_in_memory_fake_cas_state_v1_0",
        "step_in_memory_fake_cas_v1_0",
    ]
    assert [node.name for node in tree.body if isinstance(node, ast.ClassDef)] == [
        "InMemoryFakeCasV10Error",
        "InMemoryFakeCasStateV10",
        "InMemoryFakeCasTransitionV10",
    ]
    forbidden_calls = {
        "open", "__import__", "eval", "exec", "input",
        "sleep", "time", "perf_counter", "random", "randint", "uuid4",
        "Popen", "run", "call", "Thread", "Process", "Lock", "connect",
        "send", "recv", "read_text", "read_bytes", "write_text", "write_bytes",
        "unlink", "rename", "replace", "mkdir", "makedirs", "system",
    }
    calls = []
    direct_calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.append(node.func.id)
                direct_calls.append(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.append(node.func.attr)
    assert forbidden_calls.isdisjoint(calls)
    assert "compile" not in direct_calls
    forbidden_identifiers = {
        "store", "history", "callback", "retry", "timeout", "clock",
        "socket", "filesystem", "worker", "scanner", "writer", "publisher",
        "recovery", "witness", "manifest", "registered_run", "operation_log",
    }
    assigned_or_called = {
        node.id for node in ast.walk(tree) if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)
    }.union(calls)
    assert forbidden_identifiers.isdisjoint(assigned_or_called)
    assert "cell_payload_sha256 == proposed_payload_sha256" not in source
    assert "alternate_payload_sha256 == proposed_payload_sha256" not in source
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "bytes":
            arguments = " ".join(ast.unparse(argument) for argument in node.args)
            assert not any(
                token in arguments
                for token in ("payload", "proposal", "alternate", "cell_payload")
            )


def _exposure_marker_paths() -> tuple[str, ...]:
    markers: list[str] = []
    for relative_root in (
        "docs/experiments",
        "runs/uprime_u1_rpc_20260710",
    ):
        root = ROOT / relative_root
        if not root.exists():
            continue
        for path in root.rglob("*"):
            folded = path.name.casefold()
            if any(
                token in folded
                for token in ("exposure", "burn", "retir", "read_ledger")
            ):
                markers.append(path.relative_to(ROOT).as_posix())
    return tuple(sorted(markers))


def test_uprime_fake_cas_registry_runs_and_repository_exposure_snapshot_unchanged() -> None:
    registry = ROOT / "docs/experiments/uprime_odlrq_u1_rerun_license_registry.json"
    raw = registry.read_bytes()
    assert raw == (
        b'{"default_allow":false,"licenses":{},"schema_version":'
        b'"lean-rgc-uprime-u1-rerun-registry-v1.0"}\n'
    )
    assert _h(raw) == "ADBE0AB6FBE3F455E03120F2074543F15C1D75D1F7B52E1BD628A91ADB33B31B"
    git_preimage = b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    assert hashlib.sha1(git_preimage).hexdigest() == "13ffca6de484effc66f0e628d2e46823277271c6"

    def snapshot() -> tuple[tuple[str, int, int], ...]:
        runs = ROOT / "runs"
        if not runs.exists():
            return ()
        return tuple(
            sorted(
                (
                    path.relative_to(ROOT).as_posix(),
                    path.stat().st_size,
                    path.stat().st_mtime_ns,
                )
                for path in runs.rglob("*")
                if path.is_file()
            )
        )

    before = snapshot()
    before_markers = _exposure_marker_paths()
    assert before_markers == ()
    initial = cas.initial_in_memory_fake_cas_state_v1_0()
    transition = cas.step_in_memory_fake_cas_v1_0(
        initial, initial.state_version_sha256, A, DIRECTIVES[0], None
    )
    assert transition.after_state.cell_payload is A
    assert snapshot() == before
    assert _exposure_marker_paths() == before_markers == ()
    assert registry.read_bytes() == raw


def test_uprime_fake_cas_support_exports_exact_ordered_tests_only() -> None:
    expected = [
        "test_uprime_fake_cas_exact_surface_fields_imports_and_signatures",
        "test_uprime_fake_cas_initial_state_present_states_and_state_goldens",
        "test_uprime_fake_cas_six_outcomes_exact_rows_hashes_and_identity",
        "test_uprime_fake_cas_conflict_identity_and_alternate_precedence",
        "test_uprime_fake_cas_max_generation_no_wrap_and_no_seventh_outcome",
        "test_uprime_fake_cas_aba_forks_and_snapshot_isolation",
        "test_uprime_fake_cas_forced_raw_sha_collision_seam_preserves_raw_semantics",
        "test_uprime_fake_cas_ast_raw_comparisons_and_digest_only_mutants_die",
        "test_uprime_fake_cas_state_and_transition_constructors_revalidate_every_field",
        "test_uprime_fake_cas_exact_type_call_shape_and_boundary_rejection",
        "test_uprime_fake_cas_equal_valued_wrong_types_and_deleted_slots_reject",
        "test_uprime_fake_cas_outcome_table_same_length_mutation_fails_closed",
        "test_uprime_fake_cas_structural_invalids_precede_conflict_and_identity",
        "test_uprime_fake_cas_hash_framing_mutation_and_resource_arithmetic",
        "test_uprime_fake_cas_resource_constants_fail_before_hashing",
        "test_uprime_fake_cas_hashing_is_incremental_and_retains_no_payload_copy",
        "test_uprime_fake_cas_forbidden_capability_and_raw_equality_ast_sentinels",
        "test_uprime_fake_cas_registry_runs_and_repository_exposure_snapshot_unchanged",
        "test_uprime_fake_cas_support_exports_exact_ordered_tests_only",
    ]
    assert __all__ == expected
    assert len(__all__) == len(set(__all__))
    assert all(name.startswith("test_uprime_fake_cas_") for name in __all__)
    assert all(callable(globals()[name]) for name in __all__)
    collector = (ROOT / "tests/test_uprime_rpc_ledger.py").read_text(encoding="utf-8")
    import_line = "from uprime_rpc_fake_cas_kernel_cases import *  # noqa: F403"
    assert collector.splitlines().count(import_line) == 1
    assert collector.count("uprime_rpc_fake_cas_kernel_cases") == 1


__all__ = [
    "test_uprime_fake_cas_exact_surface_fields_imports_and_signatures",
    "test_uprime_fake_cas_initial_state_present_states_and_state_goldens",
    "test_uprime_fake_cas_six_outcomes_exact_rows_hashes_and_identity",
    "test_uprime_fake_cas_conflict_identity_and_alternate_precedence",
    "test_uprime_fake_cas_max_generation_no_wrap_and_no_seventh_outcome",
    "test_uprime_fake_cas_aba_forks_and_snapshot_isolation",
    "test_uprime_fake_cas_forced_raw_sha_collision_seam_preserves_raw_semantics",
    "test_uprime_fake_cas_ast_raw_comparisons_and_digest_only_mutants_die",
    "test_uprime_fake_cas_state_and_transition_constructors_revalidate_every_field",
    "test_uprime_fake_cas_exact_type_call_shape_and_boundary_rejection",
    "test_uprime_fake_cas_equal_valued_wrong_types_and_deleted_slots_reject",
    "test_uprime_fake_cas_outcome_table_same_length_mutation_fails_closed",
    "test_uprime_fake_cas_structural_invalids_precede_conflict_and_identity",
    "test_uprime_fake_cas_hash_framing_mutation_and_resource_arithmetic",
    "test_uprime_fake_cas_resource_constants_fail_before_hashing",
    "test_uprime_fake_cas_hashing_is_incremental_and_retains_no_payload_copy",
    "test_uprime_fake_cas_forbidden_capability_and_raw_equality_ast_sentinels",
    "test_uprime_fake_cas_registry_runs_and_repository_exposure_snapshot_unchanged",
    "test_uprime_fake_cas_support_exports_exact_ordered_tests_only",
]
