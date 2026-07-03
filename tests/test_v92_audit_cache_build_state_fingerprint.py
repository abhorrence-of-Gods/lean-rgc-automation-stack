from pathlib import Path

from lean_rgc.audit_job_queue import connect_queue, enqueue_audit_jobs, lease_next_job, mark_job_result
from lean_rgc.audit_result_cache import (
    apply_cache_to_queue,
    store_queue_results_in_cache,
    workdir_fingerprint,
)
from lean_rgc.schemas import LeanTask, TacticAction


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


def test_fingerprint_tracks_built_module_set_not_rebuild_noise(tmp_path: Path):
    root = tmp_path / "proj"
    _write_project(root)
    _build(root, "Main")
    fp_first_build = workdir_fingerprint(str(root))

    olean = root / ".lake" / "build" / "lib" / "lean" / "Main.olean"
    olean.write_bytes(b"rebuilt with different content")
    assert workdir_fingerprint(str(root)) == fp_first_build

    _build(root, "Extra")
    assert workdir_fingerprint(str(root)) != fp_first_build


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
