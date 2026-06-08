import json
import sqlite3
from pathlib import Path

from lean_rgc.audit_db import build_audit_db, query_audit_db
from lean_rgc.cli import main


def _write_jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r) + '\n')


def test_audit_db_build_and_query(tmp_path):
    run = tmp_path / 'run'
    audit = run / 'round_00' / 'audit'
    _write_jsonl(audit / 'responses.jsonl', [
        {
            'state_id': 's0',
            'action_id': 'simp',
            'audit_status': 'success',
            'response': {'goal.eq': 1.0, 'carrier.simp': 0.25},
            'carrier_delta': {'missing_simp_lemma': 0.5},
            'defect_before': {'flat': [1.0], 'flat_keys': ['goal.eq']},
            'defect_after': {'flat': [0.0], 'flat_keys': ['goal.eq']},
        }
    ])
    _write_jsonl(audit / 'micro_audit.jsonl', [
        {
            'task_id': 't0',
            'state_id': 's0',
            'action_id': 'simp',
            'status': 'success',
            'elapsed_ms': 1.2,
            'response': {'goal.eq': 1.0},
            'carrier_delta': {'missing_simp_lemma': 0.5},
        }
    ])
    db = run / 'audit.db'
    summary = build_audit_db(run, db)
    assert summary['tables']['response_rows'] >= 1
    assert summary['tables']['response_values'] >= 1
    rows = query_audit_db(db, "SELECT response_key, value FROM response_values WHERE action_id='simp' ORDER BY response_key")
    assert any(r['response_key'] == 'goal.eq' and abs(r['value'] - 1.0) < 1e-9 for r in rows)


def test_cli_audit_db_build_and_query(tmp_path, capsys):
    run = tmp_path / 'run'
    _write_jsonl(run / 'audit' / 'responses.jsonl', [
        {'state_id': 's', 'action_id': 'a', 'audit_status': 'fail', 'response': {'x': -0.1}}
    ])
    db = run / 'audit.db'
    assert main(['audit-db-build', '--run-dir', str(run), '--db', str(db)]) == 0
    assert db.exists()
    out = run / 'query.json'
    assert main(['audit-db-query', '--db', str(db), '--sql', 'SELECT COUNT(*) AS n FROM response_rows', '--out-json', str(out)]) == 0
    obj = json.loads(out.read_text())
    assert obj['rows'][0]['n'] == 1


def test_pipeline_audit_db_flag(tmp_path):
    out = tmp_path / 'pipe'
    tasks = Path('examples/minimal_theorems.jsonl')
    actions = Path('examples/core_tactics.jsonl')
    assert main([
        'pipeline', '--tasks', str(tasks), '--actions', str(actions), '--out', str(out),
        '--dry-run', '--max-actions', '2', '--audit-db'
    ]) == 0
    assert (out / 'audit.db').exists()
    con = sqlite3.connect(out / 'audit.db')
    try:
        n = con.execute('SELECT COUNT(*) FROM artifacts').fetchone()[0]
        assert n > 0
    finally:
        con.close()
