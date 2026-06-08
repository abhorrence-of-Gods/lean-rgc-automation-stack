from __future__ import annotations

import json
import sys
from pathlib import Path

from lean_rgc.lean_server import LeanServerAdapter, LeanServerConfig, run_server_micro_audit_to_files
from lean_rgc.schemas import LeanTask, ProofState, TacticAction, read_jsonl, write_jsonl
from lean_rgc.cli import main


def test_lean_server_dry_audit_to_files(tmp_path: Path):
    task = LeanTask(task_id='t1', statement='True', imports=[])
    action = TacticAction(action_id='trivial', tactic='trivial', tactic_class='core')
    out = tmp_path / 'server_audit'
    summary = run_server_micro_audit_to_files([task], {'t1': [action]}, out_dir=out, server_config=LeanServerConfig(backend='dry_run'), max_actions=8)
    assert summary['backend'] == 'dry_run'
    assert summary['n'] == 1
    audits = read_jsonl(out / 'micro_audit.jsonl')
    responses = read_jsonl(out / 'responses.jsonl')
    assert audits[0]['status'] == 'success'
    assert responses[0]['action_id'] == 'trivial'
    assert (out / 'server_summary.json').exists()


def test_lean_server_cli_dry(tmp_path: Path):
    tasks = tmp_path / 'tasks.jsonl'
    actions = tmp_path / 'actions.jsonl'
    out = tmp_path / 'out'
    write_jsonl(tasks, [{'task_id': 't1', 'statement': 'True', 'imports': []}])
    write_jsonl(actions, [{'action_id': 'trivial', 'tactic': 'trivial'}])
    rc = main(['lean-server-audit', '--tasks', str(tasks), '--actions', str(actions), '--out', str(out), '--server-backend', 'dry_run', '--import-mode', 'core'])
    assert rc == 0
    summary = json.loads((out / 'summary.json').read_text())
    assert summary['backend'] == 'dry_run'
    assert summary['n'] == 1


def test_jsonl_lean_worker_protocol(tmp_path: Path):
    worker_py = tmp_path / 'fake_worker.py'
    worker_py.write_text(r'''
import json, sys
for line in sys.stdin:
    req=json.loads(line)
    if req.get('cmd')=='load_project':
        print(json.dumps({'id': req.get('id'), 'ok': True, 'loaded': True}), flush=True)
    elif req.get('cmd')=='shutdown':
        print(json.dumps({'id': req.get('id'), 'ok': True}), flush=True); break
    elif req.get('cmd')=='apply_tactic':
        task=req['task']; action=req['action']; state=req.get('state') or {}
        after={'state_id':'closed_'+state.get('state_id','s'), 'task_id':task['task_id'], 'goals_text':'', 'target':'', 'raw_messages':['fake server success']}
        print(json.dumps({'id': req.get('id'), 'ok': True, 'record': {'task_id':task['task_id'], 'action_id':action['action_id'], 'state_id':state.get('state_id'), 'status':'success', 'after_state':after, 'messages':['fake server success'], 'elapsed_ms': 1.0}}), flush=True)
    else:
        print(json.dumps({'id': req.get('id'), 'ok': False, 'error':'unknown cmd'}), flush=True)
''')
    cfg = LeanServerConfig(backend='jsonl', server_cmd=f'{sys.executable} {worker_py}', startup_timeout_s=2.0, fallback_to_file=False)
    with LeanServerAdapter(cfg) as worker:
        task = LeanTask(task_id='t1', statement='True', imports=[])
        action = TacticAction(action_id='a1', tactic='trivial')
        rec = worker.run_tactic(task, action, ProofState.from_task(task))
        assert rec.status == 'success'
        assert rec.after_state is not None
        assert rec.messages == ['fake server success']
        assert worker.status.backend == 'jsonl'
        assert worker.status.n_requests == 1


def test_jsonl_lean_worker_skips_startup_chatter(tmp_path: Path):
    worker_py = tmp_path / 'chatty_worker.py'
    worker_py.write_text(r'''
import json, sys
for line in sys.stdin:
    req=json.loads(line)
    if req.get('cmd')=='load_project':
        print('elan/lake startup chatter that is not JSON', flush=True)
        print(json.dumps({'id': req.get('id'), 'ok': True, 'loaded': True}), flush=True)
    elif req.get('cmd')=='shutdown':
        print(json.dumps({'id': req.get('id'), 'ok': True}), flush=True); break
    elif req.get('cmd')=='apply_tactic':
        task=req['task']; action=req['action']
        print(json.dumps({'id': req.get('id'), 'ok': True, 'record': {'task_id':task['task_id'], 'action_id':action['action_id'], 'state_id':'s', 'status':'success', 'messages':[], 'elapsed_ms': 1.0}}), flush=True)
''')
    cfg = LeanServerConfig(backend='jsonl', server_cmd=f'{sys.executable} {worker_py}', startup_timeout_s=2.0, fallback_to_file=False)
    with LeanServerAdapter(cfg) as worker:
        task = LeanTask(task_id='t1', statement='True', imports=[])
        action = TacticAction(action_id='a1', tactic='trivial')
        rec = worker.apply_tactic(task, action)
        assert rec.status == 'success'


def test_jsonl_lean_worker_reports_non_json_stdout_on_exit(tmp_path: Path):
    worker_py = tmp_path / 'broken_worker.py'
    worker_py.write_text(r'''
import sys
for line in sys.stdin:
    print('Lean compilation failed before JSON protocol started', flush=True)
    print('example stderr detail', file=sys.stderr, flush=True)
    sys.exit(7)
''')
    cfg = LeanServerConfig(backend='jsonl', server_cmd=f'{sys.executable} {worker_py}', startup_timeout_s=2.0, fallback_to_file=False)
    try:
        LeanServerAdapter(cfg).start()
    except RuntimeError as e:
        msg = str(e)
        assert 'Lean compilation failed before JSON protocol started' in msg
        assert 'example stderr detail' in msg
    else:
        raise AssertionError('expected JSONL startup failure')


def test_kernel_rpc_audit_uses_stateful_branch_apply(tmp_path: Path):
    worker_py = tmp_path / 'stateful_worker.py'
    log = tmp_path / 'commands.jsonl'
    worker_py.write_text(r'''
import json, sys
from pathlib import Path

log = Path(sys.argv[1])
next_id = 0

def write_log(req):
    with log.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"cmd": req.get("cmd"), "state_id": req.get("state_id")}) + "\n")

for line in sys.stdin:
    req = json.loads(line)
    write_log(req)
    cmd = req.get("cmd")
    if cmd == "load_project":
        print(json.dumps({"ok": True, "loaded": True, "backend": "lean_kernel_rpc_in_memory_v1"}), flush=True)
    elif cmd in {"register_task", "init_state"}:
        task = req["task"]
        state = {"state_id": "krpc_state_0", "task_id": task["task_id"], "status": "open", "goal_count": 1}
        kernel = {"schema_version": "lean-rgc-kernel-state-v1", "state_id": "krpc_state_0", "goals": [{"goal_id": "g0"}], "expr_graph": {"nodes": [], "roots": []}, "local_contexts": [], "metavars": [], "typeclasses": [], "status": "open"}
        print(json.dumps({"ok": True, "state": state, "kernel_state": kernel}), flush=True)
    elif cmd == "branch_state":
        next_id += 1
        state = {"state_id": f"krpc_branch_{next_id}", "task_id": "t1", "status": "open", "goal_count": 1}
        print(json.dumps({"ok": True, "state": state, "new_state_id": state["state_id"], "parent_state_id": req.get("state_id")}), flush=True)
    elif cmd == "apply_tactic":
        task = req["task"]; action = req["action"]; sid = req["state_id"]
        after_id = sid + "_after"
        after = {"state_id": after_id, "task_id": task["task_id"], "goals_text": "", "target": task["statement"], "raw_messages": []}
        kernel = {"schema_version": "lean-rgc-kernel-state-v1", "state_id": after_id, "goals": [], "expr_graph": {"nodes": [], "roots": []}, "local_contexts": [], "metavars": [], "typeclasses": [], "status": "closed"}
        audit = {"task_id": task["task_id"], "state_id": sid, "action_id": action["action_id"], "status": "success", "elapsed_ms": 1.0, "messages": [], "after_state": after, "audit_flags": {"execution_backend": "lean_kernel_rpc_in_memory_v1"}}
        print(json.dumps({"ok": True, "status": "success", "audit": audit, "kernel_state": kernel, "kernel_state_after": kernel, "after_state_id": after_id}), flush=True)
    elif cmd == "structured_state":
        print(json.dumps({"ok": False, "error": "not implemented"}), flush=True)
    elif cmd == "shutdown":
        print(json.dumps({"ok": True, "shutdown": True}), flush=True)
        break
    else:
        print(json.dumps({"ok": False, "error": "unknown"}), flush=True)
''')
    tasks = [LeanTask(task_id='t1', statement='True', imports=[])]
    actions = [
        TacticAction(action_id='a1', tactic='trivial'),
        TacticAction(action_id='a2', tactic='simp'),
    ]
    cfg = LeanServerConfig(
        backend='jsonl',
        server_cmd=f'"{sys.executable}" "{worker_py}" "{log}"',
        startup_timeout_s=2.0,
        fallback_to_file=False,
        native_exec_mode='kernel_rpc',
    )
    out = tmp_path / 'audit'
    summary = run_server_micro_audit_to_files(tasks, {'t1': actions}, out_dir=out, server_config=cfg, max_actions=8)
    assert summary["stateful_kernel_rpc_audit"] is True
    assert summary["stateful_kernel_rpc_tasks"] == 1
    assert summary["stateful_kernel_rpc_actions"] == 2
    commands = [json.loads(line) for line in log.read_text().splitlines()]
    assert [c["cmd"] for c in commands].count("register_task") == 1
    assert [c["cmd"] for c in commands].count("branch_state") == 2
    assert [c["cmd"] for c in commands].count("apply_tactic") == 2
    apply_state_ids = [c["state_id"] for c in commands if c["cmd"] == "apply_tactic"]
    assert all(s.startswith("krpc_branch_") for s in apply_state_ids)
    audits = read_jsonl(out / "micro_audit.jsonl")
    assert all((a["audit_flags"] or {}).get("stateful_kernel_rpc_audit") is True for a in audits)
