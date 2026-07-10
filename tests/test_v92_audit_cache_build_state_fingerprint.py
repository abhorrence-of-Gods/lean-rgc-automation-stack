from pathlib import Path

from lean_rgc.audit_job_queue import connect_queue, enqueue_audit_jobs, lease_next_job, mark_job_result
from lean_rgc.audit_result_cache import (
    WORKDIR_FINGERPRINT_SCHEMA,
    apply_cache_to_queue,
    store_queue_results_in_cache,
    workdir_fingerprint,
)
from lean_rgc.schemas import LeanTask, TacticAction, stable_hash


def _write_project(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "lake-manifest.json").write_text('{"packages": []}', encoding="utf-8")
    (root / "lean-toolchain").write_text("leanprover/lean4:v4.9.0\n", encoding="utf-8")


def _build(root: Path, *modules: str, lib_dir: str = ".lake/build/lib/lean") -> None:
    lib = root.joinpath(*lib_dir.split("/"))
    lib.mkdir(parents=True, exist_ok=True)
    for module in modules:
        (lib / f"{module}.olean").write_bytes(b"olean:" + module.encode("utf-8"))


def test_fingerprint_changes_when_project_gets_built(tmp_path: Path):
    root = tmp_path / "proj"
    _write_project(root)
    fp_unbuilt = workdir_fingerprint(str(root))

    _build(root, "Main")
    fp_built = workdir_fingerprint(str(root))

    # Same manifest and toolchain, different build state.
    assert fp_unbuilt != fp_built


def test_fingerprint_tracks_built_module_content_and_set(tmp_path: Path):
    root = tmp_path / "proj"
    _write_project(root)
    _build(root, "Main")
    fp_first_build = workdir_fingerprint(str(root))

    olean = root / ".lake" / "build" / "lib" / "lean" / "Main.olean"
    olean.write_bytes(b"olean:Main")
    assert workdir_fingerprint(str(root)) == fp_first_build

    olean.write_bytes(b"rebuilt with different content")
    fp_changed_content = workdir_fingerprint(str(root))
    assert fp_changed_content != fp_first_build

    _build(root, "Extra")
    assert workdir_fingerprint(str(root)) != fp_changed_content


def test_fingerprint_tracks_nested_olean_content(tmp_path: Path):
    root = tmp_path / "proj"
    _write_project(root)
    nested = root / ".lake" / "build" / "lib" / "lean" / "RGCLean" / "Basic.olean"
    nested.parent.mkdir(parents=True)
    nested.write_bytes(b"nested-v1")
    fp_first = workdir_fingerprint(str(root))

    nested.write_bytes(b"nested-v2")
    assert workdir_fingerprint(str(root)) != fp_first


def test_fingerprint_is_independent_of_artifact_creation_order(tmp_path: Path):
    root = tmp_path / "proj"
    _write_project(root)
    _build(root, "Second", "First")
    fp_first_order = workdir_fingerprint(str(root))

    lib = root / ".lake" / "build" / "lib" / "lean"
    for path in lib.glob("*.olean"):
        path.unlink()
    _build(root, "First", "Second")
    assert workdir_fingerprint(str(root)) == fp_first_order


def test_fingerprint_schema_salt_is_present_even_when_unbuilt(tmp_path: Path):
    root = tmp_path / "proj"
    _write_project(root)
    current = workdir_fingerprint(str(root))
    legacy_payload = {
        "workdir": str(root.resolve()),
        "lake-manifest.json": stable_hash('{"packages": []}', 24),
        "lean-toolchain": stable_hash("leanprover/lean4:v4.9.0\n", 24),
        "build_state": "missing",
    }
    assert WORKDIR_FINGERPRINT_SCHEMA
    assert len(current) == 64
    assert current != stable_hash(legacy_payload, 24)


def test_unreadable_build_content_disables_cross_call_cache_identity(tmp_path: Path, monkeypatch):
    root = tmp_path / "proj"
    _write_project(root)
    _build(root, "Main")
    original_open = Path.open

    def fail_olean_open(path: Path, *args, **kwargs):
        if path.suffix == ".olean":
            raise PermissionError("synthetic unreadable artifact")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", fail_olean_open)
    assert workdir_fingerprint(str(root)) != workdir_fingerprint(str(root))


def test_manifest_stat_failure_disables_cross_call_cache_identity(tmp_path: Path, monkeypatch):
    root = tmp_path / "proj"
    _write_project(root)
    original_stat = Path.stat

    def fail_manifest_stat(path: Path, *args, **kwargs):
        if path.name == "lake-manifest.json":
            raise PermissionError("synthetic manifest stat failure")
        return original_stat(path, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", fail_manifest_stat)
    assert workdir_fingerprint(str(root)) != workdir_fingerprint(str(root))


def test_manifest_fingerprint_hashes_raw_bytes(tmp_path: Path):
    root = tmp_path / "proj"
    _write_project(root)
    manifest = root / "lake-manifest.json"
    manifest.write_bytes(b"\xff")
    first = workdir_fingerprint(str(root))
    manifest.write_bytes(b"\xfe")
    assert workdir_fingerprint(str(root)) != first


def test_unspecified_workdir_keeps_legacy_cache_lane_stable():
    # This lane remains available for non-project audits whose cache key also
    # includes the resolved Lean version. It is not admissible as a hard U'
    # ObservationFrameId because it has no project-content attestation.
    assert workdir_fingerprint(None) == workdir_fingerprint(None)


def test_fingerprint_detects_legacy_build_layouts(tmp_path: Path):
    for lib_dir in (".lake/build/lib", "build/lib"):
        root = tmp_path / lib_dir.replace("/", "_")
        _write_project(root)
        fp_unbuilt = workdir_fingerprint(str(root))
        _build(root, "Main", lib_dir=lib_dir)
        assert workdir_fingerprint(str(root)) != fp_unbuilt


def test_poisoned_unbuilt_cache_entries_do_not_hit_after_build(tmp_path: Path):
    root = tmp_path / "proj"
    _write_project(root)
    fp_unbuilt = workdir_fingerprint(str(root))

    # An unbuilt environment makes every audit fail with "unknown module
    # prefix"; those results still land in the cross-run cache.
    cache = tmp_path / "cache.sqlite"
    task = LeanTask(task_id="t0", statement="True", imports=["Mathlib"])
    action = TacticAction(action_id="a0", tactic="trivial")
    poisoned = {
        "audit": {"status": "compile_error", "audit_flags": {}, "stderr": "unknown module prefix 'Mathlib'"},
        "response": {"response": {}},
    }
    queue = tmp_path / "q_unbuilt.sqlite"
    enqueue_audit_jobs(
        queue,
        [task],
        [action],
        run_id="r_unbuilt",
        backend="source_check_bulk",
        import_mode="preserve",
        project_fingerprint_value=fp_unbuilt,
    )
    conn = connect_queue(queue)
    job = lease_next_job(conn, worker_id="w0")
    assert job is not None
    mark_job_result(conn, job.job_id, status="succeeded", result=poisoned)
    conn.close()
    stored = store_queue_results_in_cache(
        cache_db=cache,
        queue_db=queue,
        run_id="r_unbuilt",
        lean_version="Lean fake",
        workdir_fingerprint_value=fp_unbuilt,
        import_mode="preserve",
        trace_state=False,
    )
    assert stored["n_stored"] == 1

    _build(root, "Main")
    fp_built = workdir_fingerprint(str(root))

    queue_after_build = tmp_path / "q_built.sqlite"
    enqueue_audit_jobs(
        queue_after_build,
        [task],
        [action],
        run_id="r_built",
        backend="source_check_bulk",
        import_mode="preserve",
        project_fingerprint_value=fp_built,
    )
    applied = apply_cache_to_queue(
        cache_db=cache,
        queue_db=queue_after_build,
        run_id="r_built",
        lean_version="Lean fake",
        workdir_fingerprint_value=fp_built,
        import_mode="preserve",
        trace_state=False,
    )
    assert applied["n_cache_hit"] == 0
    assert applied["n_cache_miss"] == 1

    # Control: the same unbuilt fingerprint still hits, so the miss above is
    # attributable to the build-state component alone.
    queue_still_unbuilt = tmp_path / "q_unbuilt2.sqlite"
    enqueue_audit_jobs(
        queue_still_unbuilt,
        [task],
        [action],
        run_id="r_unbuilt2",
        backend="source_check_bulk",
        import_mode="preserve",
        project_fingerprint_value=fp_unbuilt,
    )
    applied_unbuilt = apply_cache_to_queue(
        cache_db=cache,
        queue_db=queue_still_unbuilt,
        run_id="r_unbuilt2",
        lean_version="Lean fake",
        workdir_fingerprint_value=fp_unbuilt,
        import_mode="preserve",
        trace_state=False,
    )
    assert applied_unbuilt["n_cache_hit"] == 1


def test_cache_misses_after_same_named_olean_content_changes(tmp_path: Path):
    root = tmp_path / "proj"
    _write_project(root)
    _build(root, "Main")
    fp_first = workdir_fingerprint(str(root))

    cache = tmp_path / "cache.sqlite"
    task = LeanTask(task_id="t0", statement="True", imports=["Main"])
    action = TacticAction(action_id="a0", tactic="trivial")
    result = {
        "audit": {"status": "success", "audit_flags": {}},
        "response": {"response": {}},
    }
    first_queue = tmp_path / "q_first.sqlite"
    enqueue_audit_jobs(
        first_queue,
        [task],
        [action],
        run_id="r_first",
        backend="source_check_bulk",
        import_mode="preserve",
        project_fingerprint_value=fp_first,
    )
    conn = connect_queue(first_queue)
    job = lease_next_job(conn, worker_id="w0")
    assert job is not None
    mark_job_result(conn, job.job_id, status="succeeded", result=result)
    conn.close()
    stored = store_queue_results_in_cache(
        cache_db=cache,
        queue_db=first_queue,
        run_id="r_first",
        lean_version="Lean fake",
        workdir_fingerprint_value=fp_first,
        import_mode="preserve",
        trace_state=False,
    )
    assert stored["n_stored"] == 1

    olean = root / ".lake" / "build" / "lib" / "lean" / "Main.olean"
    olean.write_bytes(b"semantic-content-v2")
    fp_second = workdir_fingerprint(str(root))
    assert fp_second != fp_first

    second_queue = tmp_path / "q_second.sqlite"
    enqueue_audit_jobs(
        second_queue,
        [task],
        [action],
        run_id="r_second",
        backend="source_check_bulk",
        import_mode="preserve",
        project_fingerprint_value=fp_second,
    )
    applied = apply_cache_to_queue(
        cache_db=cache,
        queue_db=second_queue,
        run_id="r_second",
        lean_version="Lean fake",
        workdir_fingerprint_value=fp_second,
        import_mode="preserve",
        trace_state=False,
    )
    assert applied["n_cache_hit"] == 0
    assert applied["n_cache_miss"] == 1
