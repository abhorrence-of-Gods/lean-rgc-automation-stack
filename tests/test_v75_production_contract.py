import json
import sqlite3
import subprocess
import sys
from pathlib import Path

from lean_rgc.cli import build_parser, main
from lean_rgc.core import (
    PRODUCTION_METADATA_FIELDS,
    PRODUCTION_RECORD_TYPES,
    SCHEMA_CONTRACT_VERSION,
    ArtifactRecord,
    LineageEdgeRecord,
    write_records,
)
from lean_rgc.data.store import RunStore
from lean_rgc.schemas import SCHEMA_CONTRACT_VERSION as FACADE_SCHEMA_CONTRACT_VERSION


ROOT = Path(__file__).resolve().parents[1]


def test_core_metadata_contract_is_canonical_and_facaded(tmp_path: Path):
    assert SCHEMA_CONTRACT_VERSION == "lean-rgc.production-metadata-contract.v1"
    assert FACADE_SCHEMA_CONTRACT_VERSION == SCHEMA_CONTRACT_VERSION
    assert set(PRODUCTION_METADATA_FIELDS) == {"schema_version", "run_id", "parent_ids", "payload_json"}
    assert {"run", "artifact", "response", "lineage_edge"} <= set(PRODUCTION_RECORD_TYPES)

    artifact = ArtifactRecord(
        schema_version=SCHEMA_CONTRACT_VERSION,
        run_id="run_contract",
        parent_ids=["parent"],
        artifact_id="artifact_1",
        artifact_type="responses",
        uri="file:///tmp/responses.jsonl",
        sha256="abc",
    ).to_dict()
    edge = LineageEdgeRecord(
        schema_version=SCHEMA_CONTRACT_VERSION,
        run_id="run_contract",
        edge_id="edge_1",
        src_type="response",
        src_id="r1",
        dst_type="poms_evidence",
        dst_id="ev1",
        edge_type="audit_yields_poms_evidence",
    ).to_dict()
    assert all(field in artifact for field in PRODUCTION_METADATA_FIELDS)
    assert all(field in edge for field in PRODUCTION_METADATA_FIELDS)

    out = tmp_path / "contract.jsonl"
    write_records(out, [{"response_id": "r1"}], schema_version=SCHEMA_CONTRACT_VERSION, run_id="run_contract")
    assert json.loads(out.read_text(encoding="utf-8").splitlines()[0])["schema_version"] == SCHEMA_CONTRACT_VERSION


def test_data_check_cli_reports_invariants_and_nonzero_on_failure(tmp_path: Path):
    db = tmp_path / "runs.db"
    store = RunStore(db)
    conn = store.connect()
    try:
        store.upsert_run(conn, run_id="run_ok", run_dir=tmp_path, status="created")
        conn.commit()
    finally:
        conn.close()

    assert main(["data", "check", "--db", str(db), "--json"]) == 0

    conn = sqlite3.connect(db)
    try:
        conn.execute(
            """
            INSERT INTO artifacts(
                run_dir, rel_path, abs_path, kind, round, sha256, n_rows,
                run_id, artifact_type, schema_version, uri, created_at, payload_json
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (str(tmp_path), "bad.jsonl", str(tmp_path / "bad.jsonl"), "jsonl", 0, "", 0, "", "jsonl", "", "", 0.0, "{}"),
        )
        conn.commit()
    finally:
        conn.close()

    assert main(["data", "check", "--db", str(db), "--json"]) == 1
    assert main(["data", "check", "--db", str(tmp_path / "missing.db"), "--json"]) == 2


def test_data_check_is_registered_under_data_namespace():
    parser = build_parser()
    ns = parser.parse_args(["data", "check", "--db", "runs.db", "--json"])
    assert ns.func.__module__ == "lean_rgc.cli.data"
    assert ns.json is True


def test_inventory_scripts_emit_expected_json_shape(tmp_path: Path):
    cases = [
        ("inventory_imports.py", "imports.json", "modules"),
        ("inventory_cli.py", "cli.json", "commands"),
        ("inventory_tests.py", "tests.json", "files"),
    ]
    for script, filename, collection_key in cases:
        out = tmp_path / filename
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / script), "--root", str(ROOT), "--out", str(out)],
            cwd=ROOT,
            text=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        payload = json.loads(out.read_text(encoding="utf-8"))
        assert payload["schema_version"] == "lean-rgc.inventory.v1"
        assert payload["inventory_type"] == filename.removesuffix(".json")
        assert payload[collection_key]
        assert payload["summary"]


def test_production_docs_and_ci_contract_are_present():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "lean-rgc data check --db runs.db --json" in readme
    for rel in [
        "docs/architecture.md",
        "docs/data_model.md",
        "docs/cli.md",
        "docs/migration_status.md",
        ".github/workflows/ci.yml",
    ]:
        assert (ROOT / rel).exists(), rel
