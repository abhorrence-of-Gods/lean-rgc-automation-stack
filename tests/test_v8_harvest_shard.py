from pathlib import Path
import json

from lean_rgc.project_harvest import parse_lean_file, harvest_lean_project
from lean_rgc.sharding import shard_jsonl, merge_jsonl
from lean_rgc.schemas import read_jsonl


def test_parse_and_harvest_project(tmp_path: Path):
    p = tmp_path / 'Foo.lean'
    p.write_text('''import Init\nnamespace Foo\n\ntheorem id_nat (n : Nat) : n = n := by\n  rfl\n\nlemma and_swap (p q : Prop) : p ∧ q → q ∧ p := by\n  intro h\n  exact And.intro h.right h.left\n\nexample : True := by\n  trivial\nend Foo\n''', encoding='utf-8')
    decls = parse_lean_file(p, root=tmp_path)
    assert len(decls) == 3
    assert any(d.name == 'id_nat' for d in decls)
    out_tasks = tmp_path / 'tasks.jsonl'
    out_prems = tmp_path / 'premises.jsonl'
    meta = harvest_lean_project(tmp_path, out_tasks=out_tasks, out_premises=out_prems)
    assert meta['n_decls'] == 3
    tasks = read_jsonl(out_tasks)
    prems = read_jsonl(out_prems)
    assert len(tasks) == 3
    assert len(prems) == 2
    assert any('nat' in t.get('domain_tags', []) for t in tasks)


def test_shard_and_merge_jsonl(tmp_path: Path):
    inp = tmp_path / 'rows.jsonl'
    rows = [{'task_id': f't{i}', 'x': i} for i in range(10)]
    inp.write_text('\n'.join(json.dumps(r) for r in rows) + '\n', encoding='utf-8')
    outd = tmp_path / 'shards'
    meta = shard_jsonl(inp, outd, shards=3, key='task_id')
    assert meta['shards'] == 3
    files = [f['path'] for f in meta['files']]
    merged = tmp_path / 'merged.jsonl'
    mm = merge_jsonl(files, merged, dedup_key='task_id')
    assert mm['n_rows'] == 10
    assert sorted(r['x'] for r in read_jsonl(merged)) == list(range(10))
