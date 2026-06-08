from lean_rgc.cli import build_parser


def test_cli_builds_and_iterate_parses_minimal():
    parser = build_parser()
    ns = parser.parse_args([
        'iterate', '--tasks', 'tasks.jsonl', '--out', 'out', '--dry-run',
        '--audit-mode', 'batch', '--frontier-normalize', '--ir-candidates'
    ])
    assert ns.cmd == 'iterate'
    assert ns.audit_mode == 'batch'
    assert ns.frontier_normalize is True
    assert ns.ir_candidates is True


def test_cli_pipeline_bulk_flag_parses():
    parser = build_parser()
    ns = parser.parse_args([
        'pipeline', '--tasks', 'tasks.jsonl', '--out', 'out', '--audit-mode', 'bulk', '--bulk-batch-size', '8'
    ])
    assert ns.cmd == 'pipeline'
    assert ns.audit_mode == 'bulk'
    assert ns.bulk_batch_size == 8
