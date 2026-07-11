from __future__ import annotations

import gc
import json
import os
from pathlib import Path

import pytest

from lean_rgc.evals import uprime_rpc_ledger as ledger

# The frozen M2b profile names this test module.  Keep the larger exact-49
# matrix in a non-collectable support module and import its marked test objects
# here so both the registered profile and default collection execute them once.
from uprime_rpc_ledger_semantics_cases import *  # noqa: F403
from uprime_rpc_contract_oracle_cases import *  # noqa: F403
from uprime_rpc_bundle_reservation_cases import *  # noqa: F403
from uprime_rpc_attempt_manifest_cases import *  # noqa: F403
from uprime_rpc_seed_inventory_cases import *  # noqa: F403


HEADER_BODY = {"phase": "synthetic", "wire_exact": False}
EXPECTED_HEADER_CANONICAL = b'{"phase":"synthetic","wire_exact":false}'
EXPECTED_GENESIS = "59621B9AC506F13EEFA4EB3F18ADF7BA56F10090B0986A2F80978906405CF594"
EXPECTED_HEADER_HASH = "F6DB2F24A1CFC5FCC12118E3E51C456BD98EECA1B674332A0A6F5BE174345928"


def _closed_fixture(path: Path):
    writer = ledger.StandaloneChainWriter.create(path, header_body=HEADER_BODY)
    writer.append_event(
        "request_intent",
        {
            "frame_index": 1,
            "request": {"cmd": "status", "id": "synthetic-1"},
        },
    )
    attestation = writer.close_with_closure(
        {"sequence_status": "aborted", "reason_codes": ["SYNTHETIC"]}
    )
    return attestation


def test_strict_json_golden_unicode_and_chain_vectors():
    assert ledger.canonical_json_bytes(HEADER_BODY) == EXPECTED_HEADER_CANONICAL
    assert ledger.parse_canonical_json_bytes(EXPECTED_HEADER_CANONICAL) == HEADER_BODY
    assert ledger.canonical_json_bytes({"日本語": "λ", "n": -7}) == (
        '{"n":-7,"日本語":"λ"}'.encode("utf-8")
    )
    genesis = ledger.compute_genesis_sha256(HEADER_BODY)
    assert genesis == EXPECTED_GENESIS
    record = ledger.build_chain_record(
        record_index=0,
        record_type="header",
        previous_record_sha256=genesis,
        body=HEADER_BODY,
    )
    assert record["record_sha256"] == EXPECTED_HEADER_HASH
    assert ledger.canonical_chain_record_line(record).endswith(b"\n")
    assert b"\r" not in ledger.canonical_chain_record_line(record)


@pytest.mark.parametrize(
    "raw",
    [
        b'{"b":1,"a":2}',
        b'{"a":1, "b":2}',
        b'{"a":1}\n',
        b'\xef\xbb\xbf{"a":1}',
        b'{"a":-0}',
        b'{"a":"\\u03bb"}',
        b'{"a":1.0}',
        b'{"a":1e0}',
        b'{"a":NaN}',
        b'{"a":Infinity}',
        b'{"a":-Infinity}',
        b'{"a":"\\ud800"}',
        b'{"a":"\xff"}',
    ],
)
def test_strict_json_rejects_noncanonical_or_outside_algebra(raw):
    with pytest.raises(ledger.StandaloneLedgerStructureError):
        ledger.parse_canonical_json_bytes(raw)


@pytest.mark.parametrize(
    "raw",
    [
        b'{"a":1,"a":2}',
        b'{"outer":{"a":1,"a":2}}',
        b'{"a":1,"\\u0061":2}',
    ],
)
def test_strict_json_rejects_duplicate_keys_after_escape_decode(raw):
    with pytest.raises(ledger.StandaloneLedgerStructureError, match="duplicate"):
        ledger.parse_canonical_json_bytes(raw)


def test_strict_json_signed_64_and_depth_boundaries():
    for value in (-(2**63), 2**63 - 1):
        raw = str(value).encode("ascii")
        assert ledger.parse_canonical_json_bytes(raw) == value
    for raw in (str(-(2**63) - 1).encode(), str(2**63).encode()):
        with pytest.raises(ledger.StandaloneLedgerStructureError, match="signed-64"):
            ledger.parse_canonical_json_bytes(raw)

    value = None
    for _ in range(ledger.MAX_JSON_DEPTH):
        value = [value]
    ledger.canonical_json_bytes(value)
    value = [value]
    with pytest.raises(ledger.StandaloneLedgerStructureError, match="depth"):
        ledger.canonical_json_bytes(value)


def test_strict_json_utf8_string_and_member_limits(monkeypatch):
    monkeypatch.setattr(ledger, "MAX_STRING_UTF8_BYTES", 4)
    assert ledger.canonical_json_bytes("éé") == '"éé"'.encode("utf-8")
    with pytest.raises(ledger.StandaloneLedgerStructureError, match="string byte"):
        ledger.canonical_json_bytes("ééé")

    monkeypatch.setattr(ledger, "MAX_CONTAINER_MEMBERS", 2)
    assert ledger.canonical_json_bytes({"a": 1, "b": 2})
    with pytest.raises(ledger.StandaloneLedgerStructureError, match="member"):
        ledger.canonical_json_bytes({"a": 1, "b": 2, "c": 3})


def test_writer_uses_exclusive_os_append_flags(tmp_path, monkeypatch):
    observed = []
    real_open = ledger.os.open

    def recording_open(path, flags, mode=0o777):
        observed.append(flags)
        return real_open(path, flags, mode)

    monkeypatch.setattr(ledger.os, "open", recording_open)
    path = tmp_path / "ledger.jsonl"
    writer = ledger.StandaloneChainWriter.create(path, header_body=HEADER_BODY)
    writer.abandon_unfinalized()
    flags = observed[0]
    assert flags & os.O_CREAT
    assert flags & os.O_EXCL
    assert flags & os.O_WRONLY
    assert flags & os.O_APPEND
    assert not flags & os.O_TRUNC
    if getattr(os, "O_BINARY", 0):
        assert flags & os.O_BINARY


def test_writer_closed_chain_attestation_is_explicitly_non_authoritative(tmp_path):
    path = tmp_path / "ledger.jsonl"
    attestation = _closed_fixture(path)
    assert attestation.attestation_scope == "standalone_chain_structure_only"
    assert attestation.verifier_schema_version == (
        "lean-rgc-uprime-rpc-chain-structure-verifier-v0.1"
    )
    assert "parsed-ledger-verifier-v1.0" not in attestation.verifier_schema_version
    assert attestation.origin_status == "unknown_may_be_synthetic"
    assert attestation.record_count == 3
    assert attestation.closure_record_index == 2
    assert attestation.genesis_sha256 == EXPECTED_GENESIS
    assert attestation.header_record_sha256 == EXPECTED_HEADER_HASH
    assert attestation.closure_record_sha256 == attestation.final_chain_head
    assert attestation.input_bytes == path.stat().st_size
    assert attestation.authority_scope == "none"
    assert attestation.canonical_run_authority is False
    assert attestation.licenses_execution is False
    assert attestation.licenses_later_stage is False
    assert not hasattr(attestation, "verdict")
    assert not hasattr(attestation, "contracts")
    assert not hasattr(attestation, "verifier_passed")
    assert not hasattr(attestation, "ledger_schema_version")
    assert not hasattr(attestation, "recorded_sequence_status")
    assert path.read_bytes().endswith(b"\n")
    assert b"\r\n" not in path.read_bytes()


def test_writer_exclusive_create_refuses_reuse(tmp_path):
    path = tmp_path / "ledger.jsonl"
    writer = ledger.StandaloneChainWriter.create(path, header_body=HEADER_BODY)
    with pytest.raises(ledger.StandaloneLedgerWriteError, match="exclusive"):
        ledger.StandaloneChainWriter.create(path, header_body=HEADER_BODY)
    writer.abandon_unfinalized()


def test_header_io_failure_closes_owned_fd_exactly_once(tmp_path, monkeypatch):
    path = tmp_path / "ledger.jsonl"
    real_close = ledger.os.close
    close_calls = []

    def recording_close(fd):
        close_calls.append(fd)
        return real_close(fd)

    def failing_fsync(_fd):
        raise OSError("injected header fsync failure")

    monkeypatch.setattr(ledger.os, "close", recording_close)
    monkeypatch.setattr(ledger.os, "fsync", failing_fsync)
    with pytest.raises(ledger.StandaloneLedgerWriteError, match="fsync"):
        ledger.StandaloneChainWriter.create(path, header_body=HEADER_BODY)
    assert len(close_calls) == 1


def test_constructor_fstat_failure_closes_factory_fd_exactly_once(
    tmp_path, monkeypatch
):
    path = tmp_path / "ledger.jsonl"
    real_close = ledger.os.close
    close_calls = []

    def recording_close(fd):
        close_calls.append(fd)
        return real_close(fd)

    def failing_fstat(_fd):
        raise OSError("injected constructor fstat failure")

    monkeypatch.setattr(ledger.os, "close", recording_close)
    monkeypatch.setattr(ledger.os, "fstat", failing_fstat)
    with pytest.raises(ledger.StandaloneLedgerWriteError, match="identity"):
        ledger.StandaloneChainWriter.create(path, header_body=HEADER_BODY)
    gc.collect()
    assert len(close_calls) == 1


def test_context_exception_abandons_without_closure_and_closes_fd(tmp_path):
    path = tmp_path / "ledger.jsonl"
    held_fd = None
    with pytest.raises(RuntimeError, match="synthetic exception"):
        with ledger.StandaloneChainWriter.create(
            path, header_body=HEADER_BODY
        ) as writer:
            held_fd = writer._fd
            writer.append_event("request_intent", {"frame_index": 1})
            raise RuntimeError("synthetic exception")
    assert held_fd is not None
    with pytest.raises(OSError):
        os.fstat(held_fd)
    assert ledger.inspect_standalone_chain_prefix(path).status == "unclosed"


def test_lost_writer_finalizer_only_closes_and_never_appends(tmp_path):
    path = tmp_path / "ledger.jsonl"
    writer = ledger.StandaloneChainWriter.create(path, header_body=HEADER_BODY)
    held_fd = writer._fd
    bytes_before = path.read_bytes()
    del writer
    gc.collect()
    with pytest.raises(OSError):
        os.fstat(held_fd)
    assert path.read_bytes() == bytes_before
    assert ledger.inspect_standalone_chain_prefix(path).status == "unclosed"


def test_prewrite_event_limit_failure_keeps_writer_healthy(tmp_path, monkeypatch):
    path = tmp_path / "ledger.jsonl"
    writer = ledger.StandaloneChainWriter.create(path, header_body=HEADER_BODY)
    count_before = writer.record_count
    head_before = writer.chain_head
    original = ledger.MAX_EVENT_LINE_BYTES
    monkeypatch.setattr(ledger, "MAX_EVENT_LINE_BYTES", 1)
    with pytest.raises(ledger.StandaloneLedgerStructureError, match="line limit"):
        writer.append_event("request_intent", {"frame_index": 1})
    assert writer.poisoned is False
    assert writer.record_count == count_before
    assert writer.chain_head == head_before
    monkeypatch.setattr(ledger, "MAX_EVENT_LINE_BYTES", original)
    attestation = writer.close_with_closure({"sequence_status": "aborted"})
    assert attestation.record_count == 2


def test_prewrite_closure_limit_failure_can_retry_smaller_closure(
    tmp_path, monkeypatch
):
    path = tmp_path / "ledger.jsonl"
    writer = ledger.StandaloneChainWriter.create(path, header_body=HEADER_BODY)
    count_before = writer.record_count
    head_before = writer.chain_head
    original = ledger.MAX_CLOSURE_LINE_BYTES
    monkeypatch.setattr(ledger, "MAX_CLOSURE_LINE_BYTES", 1)
    with pytest.raises(ledger.StandaloneLedgerStructureError, match="line limit"):
        writer.close_with_closure({"sequence_status": "aborted"})
    assert writer.poisoned is False
    assert writer.record_count == count_before
    assert writer.chain_head == head_before
    monkeypatch.setattr(ledger, "MAX_CLOSURE_LINE_BYTES", original)
    assert writer.close_with_closure({"sequence_status": "aborted"}).record_count == 2


def test_prewrite_byte_and_record_reserves_do_not_poison(tmp_path, monkeypatch):
    for kind in ("bytes", "records"):
        path = tmp_path / f"ledger-{kind}.jsonl"
        writer = ledger.StandaloneChainWriter.create(path, header_body=HEADER_BODY)
        if kind == "bytes":
            original = ledger.MAX_LEDGER_BYTES
            monkeypatch.setattr(
                ledger, "MAX_LEDGER_BYTES", writer._tracked_bytes + 2048
            )
        else:
            original = ledger.MAX_LEDGER_RECORDS
            monkeypatch.setattr(
                ledger, "MAX_LEDGER_RECORDS", writer.record_count + 1
            )
        with pytest.raises(ledger.StandaloneLedgerStructureError, match="reserve"):
            writer.append_event("request_intent", {"frame_index": 1})
        assert writer.poisoned is False
        assert writer.record_count == 1
        if kind == "bytes":
            monkeypatch.setattr(ledger, "MAX_LEDGER_BYTES", original)
        else:
            monkeypatch.setattr(ledger, "MAX_LEDGER_RECORDS", original)
        writer.close_with_closure({"sequence_status": "aborted"})


def test_writer_detects_seek_before_next_append_and_never_repairs(tmp_path):
    path = tmp_path / "ledger.jsonl"
    writer = ledger.StandaloneChainWriter.create(path, header_body=HEADER_BODY)
    os.lseek(writer._fd, 0, os.SEEK_SET)
    with pytest.raises(ledger.StandaloneLedgerWriteError, match="position"):
        writer.append_event("request_intent", {"frame_index": 1})
    assert writer.poisoned is True
    with pytest.raises(ledger.StandaloneLedgerWriteError, match="not appendable"):
        writer.append_event("request_intent", {"frame_index": 1})
    assert ledger.inspect_standalone_chain_prefix(path).status == "unclosed"


def test_short_raw_write_poison_does_not_advance_chain(tmp_path, monkeypatch):
    path = tmp_path / "ledger.jsonl"
    writer = ledger.StandaloneChainWriter.create(path, header_body=HEADER_BODY)
    count_before = writer.record_count
    head_before = writer.chain_head
    real_write = ledger.os.write

    def short_write(fd, payload):
        partial = payload[:-1]
        real_write(fd, partial)
        return len(partial)

    monkeypatch.setattr(ledger.os, "write", short_write)
    with pytest.raises(ledger.StandaloneLedgerWriteError, match="short"):
        writer.append_event("request_intent", {"frame_index": 1})
    assert writer.poisoned is True
    assert writer.record_count == count_before
    assert writer.chain_head == head_before
    assert ledger.inspect_standalone_chain_prefix(path).status == "torn"


def test_explicit_flush_hook_failure_poison_never_advances(tmp_path, monkeypatch):
    path = tmp_path / "ledger.jsonl"
    writer = ledger.StandaloneChainWriter.create(path, header_body=HEADER_BODY)
    count_before = writer.record_count

    def failing_flush(_fd):
        raise OSError("injected flush failure")

    monkeypatch.setattr(ledger, "_flush_raw_fd", failing_flush)
    with pytest.raises(ledger.StandaloneLedgerWriteError, match="flush"):
        writer.append_event("request_intent", {"frame_index": 1})
    assert writer.poisoned is True
    assert writer.record_count == count_before


def test_postwrite_position_drift_poison_never_advances(tmp_path, monkeypatch):
    path = tmp_path / "ledger.jsonl"
    writer = ledger.StandaloneChainWriter.create(path, header_body=HEADER_BODY)
    count_before = writer.record_count
    head_before = writer.chain_head
    real_lseek = ledger.os.lseek
    calls = 0

    def drifting_lseek(fd, offset, whence):
        nonlocal calls
        calls += 1
        value = real_lseek(fd, offset, whence)
        return value - 1 if calls == 2 else value

    monkeypatch.setattr(ledger.os, "lseek", drifting_lseek)
    with pytest.raises(ledger.StandaloneLedgerWriteError, match="durable size"):
        writer.append_event("request_intent", {"frame_index": 1})
    assert writer.poisoned is True
    assert writer.record_count == count_before
    assert writer.chain_head == head_before


@pytest.mark.parametrize("raise_after_real", [False, True])
def test_fsync_failure_poison_never_promotes_visible_bytes(
    tmp_path, monkeypatch, raise_after_real
):
    path = tmp_path / "ledger.jsonl"
    writer = ledger.StandaloneChainWriter.create(path, header_body=HEADER_BODY)
    count_before = writer.record_count
    real_fsync = ledger.os.fsync

    def failing_fsync(fd):
        if raise_after_real:
            real_fsync(fd)
        raise OSError("injected fsync failure")

    monkeypatch.setattr(ledger.os, "fsync", failing_fsync)
    with pytest.raises(ledger.StandaloneLedgerWriteError, match="fsync"):
        writer.append_event("request_intent", {"frame_index": 1})
    assert writer.poisoned is True
    assert writer.record_count == count_before
    with pytest.raises(ledger.StandaloneLedgerStructureError, match="not closed"):
        ledger.attest_standalone_closed_chain(path)


def test_closure_fsync_after_real_then_raise_has_no_writer_attestation(
    tmp_path, monkeypatch
):
    path = tmp_path / "ledger.jsonl"
    writer = ledger.StandaloneChainWriter.create(path, header_body=HEADER_BODY)
    real_fsync = ledger.os.fsync

    def durable_then_raise(fd):
        real_fsync(fd)
        raise OSError("injected post-fsync failure")

    monkeypatch.setattr(ledger.os, "fsync", durable_then_raise)
    with pytest.raises(ledger.StandaloneLedgerWriteError, match="fsync"):
        writer.close_with_closure({"sequence_status": "aborted"})
    assert writer.poisoned is True
    chain_only = ledger.attest_standalone_closed_chain(path)
    assert chain_only.authority_scope == "none"
    assert chain_only.licenses_execution is False


def test_close_failure_never_returns_attestation(tmp_path, monkeypatch):
    path = tmp_path / "ledger.jsonl"
    writer = ledger.StandaloneChainWriter.create(path, header_body=HEADER_BODY)
    target_fd = writer._fd
    real_close = ledger.os.close

    def failing_close(fd):
        if fd == target_fd:
            raise OSError("injected close failure")
        return real_close(fd)

    monkeypatch.setattr(ledger.os, "close", failing_close)
    try:
        with pytest.raises(ledger.StandaloneLedgerWriteError, match="close failed"):
            writer.close_with_closure({"sequence_status": "aborted"})
        assert writer.poisoned is True
    finally:
        real_close(target_fd)


def test_close_rejects_path_replacement_before_reattestation(tmp_path, monkeypatch):
    target = tmp_path / "target.jsonl"
    replacement = tmp_path / "replacement.jsonl"
    writer = ledger.StandaloneChainWriter.create(target, header_body=HEADER_BODY)
    replacement_writer = ledger.StandaloneChainWriter.create(
        replacement, header_body={"phase": "different", "wire_exact": False}
    )
    replacement_writer.close_with_closure({"sequence_status": "aborted"})
    target_fd = writer._fd
    real_close = ledger.os.close
    swapped = False

    def close_and_swap(fd):
        nonlocal swapped
        result = real_close(fd)
        if fd == target_fd and not swapped:
            swapped = True
            os.replace(replacement, target)
        return result

    monkeypatch.setattr(ledger.os, "close", close_and_swap)
    with pytest.raises(ledger.StandaloneLedgerWriteError, match="reattested"):
        writer.close_with_closure({"sequence_status": "aborted"})
    assert writer.poisoned is True
    assert swapped is True


def test_close_rejects_path_replacement_when_scan_handle_closes(
    tmp_path, monkeypatch
):
    target = tmp_path / "target.jsonl"
    replacement = tmp_path / "replacement.jsonl"
    writer = ledger.StandaloneChainWriter.create(target, header_body=HEADER_BODY)
    replacement_writer = ledger.StandaloneChainWriter.create(
        replacement, header_body={"phase": "replacement", "wire_exact": False}
    )
    replacement_writer.close_with_closure({"sequence_status": "aborted"})
    real_fdopen = ledger.os.fdopen
    swapped = False

    class SwapOnClose:
        def __init__(self, wrapped):
            self.wrapped = wrapped

        def __getattr__(self, name):
            return getattr(self.wrapped, name)

        def close(self):
            nonlocal swapped
            self.wrapped.close()
            if not swapped:
                swapped = True
                os.replace(replacement, target)

    def swapping_fdopen(fd, *args, **kwargs):
        return SwapOnClose(real_fdopen(fd, *args, **kwargs))

    monkeypatch.setattr(ledger.os, "fdopen", swapping_fdopen)
    with pytest.raises(ledger.StandaloneLedgerWriteError, match="reattested"):
        writer.close_with_closure({"sequence_status": "aborted"})
    assert writer.poisoned is True
    assert swapped is True


def test_same_handle_snapshot_retains_attested_bytes_without_authority(tmp_path):
    path = tmp_path / "snapshot.jsonl"
    _closed_fixture(path)

    snapshot = ledger.load_standalone_closed_chain_snapshot(path)

    assert snapshot.snapshot_scope == "standalone_same_handle_chain_snapshot_only"
    assert len(snapshot.canonical_record_bytes) == snapshot.attestation.record_count
    assert b"\n".join(snapshot.canonical_record_bytes) + b"\n" == path.read_bytes()
    assert snapshot.authority_scope == "none"
    assert snapshot.canonical_run_authority is False
    assert snapshot.licenses_execution is False
    assert snapshot.licenses_later_stage is False


def test_snapshot_rejects_path_replacement_when_its_scan_handle_closes(
    tmp_path, monkeypatch
):
    target = tmp_path / "snapshot-target.jsonl"
    replacement = tmp_path / "snapshot-replacement.jsonl"
    _closed_fixture(target)
    replacement_writer = ledger.StandaloneChainWriter.create(
        replacement, header_body={"phase": "replacement", "wire_exact": False}
    )
    replacement_writer.close_with_closure({"sequence_status": "aborted"})
    real_fdopen = ledger.os.fdopen
    swapped = False

    class SwapOnClose:
        def __init__(self, wrapped):
            self.wrapped = wrapped

        def __getattr__(self, name):
            return getattr(self.wrapped, name)

        def close(self):
            nonlocal swapped
            self.wrapped.close()
            if not swapped:
                swapped = True
                os.replace(replacement, target)

    def swapping_fdopen(fd, *args, **kwargs):
        return SwapOnClose(real_fdopen(fd, *args, **kwargs))

    monkeypatch.setattr(ledger.os, "fdopen", swapping_fdopen)
    with pytest.raises(ledger.StandaloneLedgerStructureError, match="not closed"):
        ledger.load_standalone_closed_chain_snapshot(target)
    assert swapped is True


def test_same_size_mutation_during_scan_is_detected(tmp_path, monkeypatch):
    path = tmp_path / "ledger.jsonl"
    _closed_fixture(path)
    real_parse = ledger.parse_canonical_json_bytes
    mutated = False

    def parse_then_mutate(raw):
        nonlocal mutated
        value = real_parse(raw)
        if not mutated:
            mutated = True
            file_bytes = path.read_bytes()
            marker = file_bytes.index(b"synthetic")
            changed = file_bytes[:marker] + b"S" + file_bytes[marker + 1 :]
            assert len(changed) == len(file_bytes)
            with path.open("r+b", buffering=0) as handle:
                handle.write(changed)
                handle.flush()
                os.fsync(handle.fileno())
        return value

    monkeypatch.setattr(ledger, "parse_canonical_json_bytes", parse_then_mutate)
    with pytest.raises(ledger.StandaloneLedgerStructureError, match="not closed"):
        ledger.attest_standalone_closed_chain(path)
    assert mutated is True
    assert ledger.inspect_standalone_chain_prefix(path).status == "corrupt"


def test_snapshot_rejects_same_size_mutation_during_retained_scan(
    tmp_path, monkeypatch
):
    path = tmp_path / "snapshot-mutation.jsonl"
    _closed_fixture(path)
    real_parse = ledger.parse_canonical_json_bytes
    mutated = False

    def parse_then_mutate(raw):
        nonlocal mutated
        value = real_parse(raw)
        if not mutated:
            mutated = True
            file_bytes = path.read_bytes()
            marker = file_bytes.index(b"synthetic")
            changed = file_bytes[:marker] + b"S" + file_bytes[marker + 1 :]
            assert len(changed) == len(file_bytes)
            with path.open("r+b", buffering=0) as handle:
                handle.write(changed)
                handle.flush()
                os.fsync(handle.fileno())
        return value

    monkeypatch.setattr(ledger, "parse_canonical_json_bytes", parse_then_mutate)
    with pytest.raises(ledger.StandaloneLedgerStructureError, match="not closed"):
        ledger.load_standalone_closed_chain_snapshot(path)
    assert mutated is True


def test_unclosed_and_closed_prefix_inspection_never_grants_authority(tmp_path):
    path = tmp_path / "ledger.jsonl"
    writer = ledger.StandaloneChainWriter.create(path, header_body=HEADER_BODY)
    writer.abandon_unfinalized()
    inspection = ledger.inspect_standalone_chain_prefix(path)
    assert inspection.status == "unclosed"
    assert inspection.finalized is False
    assert inspection.authority_scope == "none"
    assert inspection.canonical_run_authority is False
    assert inspection.licenses_execution is False

    _closed_fixture(tmp_path / "closed.jsonl")
    closed_inspection = ledger.inspect_standalone_chain_prefix(
        tmp_path / "closed.jsonl"
    )
    assert closed_inspection.status == "closed_chain"
    assert closed_inspection.finalized is False
    assert closed_inspection.authority_scope == "none"


def test_every_fixture_cut_is_unclosed_at_boundary_or_torn_inside_line(tmp_path):
    source = tmp_path / "source.jsonl"
    _closed_fixture(source)
    raw = source.read_bytes()
    boundaries = {0}
    cursor = 0
    for line in raw.splitlines(keepends=True):
        cursor += len(line)
        boundaries.add(cursor)
    for cut in range(len(raw)):
        path = tmp_path / f"cut-{cut}.jsonl"
        path.write_bytes(raw[:cut])
        status = ledger.inspect_standalone_chain_prefix(path).status
        assert status == ("unclosed" if cut in boundaries else "torn")


def test_complete_line_corruption_dominates_later_bytes(tmp_path):
    path = tmp_path / "ledger.jsonl"
    _closed_fixture(path)
    lines = path.read_bytes().splitlines(keepends=True)
    first = bytearray(lines[0])
    marker = first.index(b"synthetic")
    first[marker] = ord("S")
    path.write_bytes(bytes(first) + b"".join(lines[1:]))
    assert ledger.inspect_standalone_chain_prefix(path).status == "corrupt"
    with pytest.raises(ledger.StandaloneLedgerStructureError, match="not closed"):
        ledger.attest_standalone_closed_chain(path)


@pytest.mark.parametrize(
    "mutation",
    [
        "schema",
        "body",
        "previous",
        "stored_hash",
        "lower_hash",
        "index",
        "wrong_genesis",
        "duplicate",
        "reorder",
        "trailing",
        "delete",
        "crlf",
        "invalid_utf8",
    ],
)
def test_chain_mutations_are_not_attested(tmp_path, mutation):
    path = tmp_path / "ledger.jsonl"
    _closed_fixture(path)
    lines = path.read_bytes().splitlines(keepends=True)
    if mutation == "schema":
        value = json.loads(lines[1])
        value["schema_version"] = "wrong"
        lines[1] = ledger.canonical_json_bytes(value) + b"\n"
    elif mutation == "body":
        value = json.loads(lines[1])
        value["body"]["frame_index"] = 2
        lines[1] = ledger.canonical_json_bytes(value) + b"\n"
    elif mutation == "previous":
        value = json.loads(lines[1])
        value["previous_record_sha256"] = "A" * 64
        lines[1] = ledger.canonical_json_bytes(value) + b"\n"
    elif mutation == "stored_hash":
        value = json.loads(lines[1])
        value["record_sha256"] = "B" * 64
        lines[1] = ledger.canonical_json_bytes(value) + b"\n"
    elif mutation == "lower_hash":
        value = json.loads(lines[1])
        value["record_sha256"] = value["record_sha256"].lower()
        lines[1] = ledger.canonical_json_bytes(value) + b"\n"
    elif mutation == "index":
        value = json.loads(lines[1])
        value["record_index"] = 7
        lines[1] = ledger.canonical_json_bytes(value) + b"\n"
    elif mutation == "wrong_genesis":
        value = json.loads(lines[0])
        value["previous_record_sha256"] = "C" * 64
        lines[0] = ledger.canonical_json_bytes(value) + b"\n"
    elif mutation == "duplicate":
        lines.insert(2, lines[1])
    elif mutation == "reorder":
        lines[1], lines[2] = lines[2], lines[1]
    elif mutation == "trailing":
        lines.append(b"x")
    elif mutation == "delete":
        del lines[1]
    elif mutation == "crlf":
        lines[0] = lines[0][:-1] + b"\r\n"
    elif mutation == "invalid_utf8":
        changed = bytearray(lines[1])
        changed[changed.index(b"synthetic")] = 0xFF
        lines[1] = bytes(changed)
    path.write_bytes(b"".join(lines))
    assert ledger.inspect_standalone_chain_prefix(path).status == "corrupt"
    with pytest.raises(ledger.StandaloneLedgerStructureError, match="not closed"):
        ledger.attest_standalone_closed_chain(path)


def test_fully_rehashed_semantic_rewrite_is_only_a_new_unauthorized_chain(tmp_path):
    original_path = tmp_path / "original.jsonl"
    original = _closed_fixture(original_path)
    values = [json.loads(line) for line in original_path.read_bytes().splitlines()]
    values[1]["body"]["request"]["cmd"] = "different"
    previous = values[0]["record_sha256"]
    values[1] = ledger.build_chain_record(
        record_index=1,
        record_type="request_intent",
        previous_record_sha256=previous,
        body=values[1]["body"],
    )
    values[2] = ledger.build_chain_record(
        record_index=2,
        record_type="closure",
        previous_record_sha256=values[1]["record_sha256"],
        body=values[2]["body"],
    )
    rewritten_path = tmp_path / "rewritten.jsonl"
    rewritten_path.write_bytes(
        b"".join(ledger.canonical_chain_record_line(value) for value in values)
    )
    rewritten = ledger.attest_standalone_closed_chain(rewritten_path)
    assert rewritten.input_sha256 != original.input_sha256
    assert rewritten.final_chain_head != original.final_chain_head
    assert rewritten.authority_scope == "none"
    assert rewritten.canonical_run_authority is False
    assert rewritten.licenses_execution is False


def test_missing_terminal_lf_is_torn(tmp_path):
    path = tmp_path / "ledger.jsonl"
    _closed_fixture(path)
    path.write_bytes(path.read_bytes()[:-1])
    inspection = ledger.inspect_standalone_chain_prefix(path)
    assert inspection.status == "torn"
    assert inspection.finalized is False


@pytest.mark.parametrize("bound", ["event_line", "closure_line", "file", "records"])
def test_scanner_enforces_each_frozen_outer_bound(tmp_path, monkeypatch, bound):
    path = tmp_path / "ledger.jsonl"
    _closed_fixture(path)
    lines = path.read_bytes().splitlines(keepends=True)
    if bound == "event_line":
        monkeypatch.setattr(ledger, "MAX_EVENT_LINE_BYTES", len(lines[0]) - 1)
        expected = "LINE_SIZE_LIMIT"
    elif bound == "closure_line":
        monkeypatch.setattr(ledger, "MAX_CLOSURE_LINE_BYTES", len(lines[-1]) - 1)
        expected = "CLOSURE_SIZE_LIMIT"
    elif bound == "file":
        monkeypatch.setattr(ledger, "MAX_LEDGER_BYTES", path.stat().st_size - 1)
        expected = "FILE_SIZE_LIMIT"
    else:
        monkeypatch.setattr(ledger, "MAX_LEDGER_RECORDS", 2)
        expected = "RECORD_LIMIT"
    inspection = ledger.inspect_standalone_chain_prefix(path)
    assert inspection.status == "corrupt"
    assert inspection.error_code == expected


def test_append_event_rejects_non_event_type_without_touching_writer(tmp_path):
    path = tmp_path / "ledger.jsonl"
    writer = ledger.StandaloneChainWriter.create(path, header_body=HEADER_BODY)
    with pytest.raises(ledger.StandaloneLedgerStructureError, match="record type"):
        writer.append_event("closure", {})
    assert writer.poisoned is False
    assert writer.record_count == 1
    writer.abandon_unfinalized()
