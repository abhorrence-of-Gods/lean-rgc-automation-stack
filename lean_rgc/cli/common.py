from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

from ..candidates import CandidateGeneratorConfig, TacticCandidateGenerator
from ..carrier_exposure import StateDependentCandidateGenerator
from ..lean.executor import LeanExecutor, LeanExecutorConfig
from ..lean.server import LeanServerConfig
from ..schemas import LeanTask, ProofState, TacticAction, read_jsonl


def _json_dump(value: Any) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False)


def _load_tasks(path: str | Path) -> list[LeanTask]:
    return [LeanTask.from_dict(x) for x in read_jsonl(path)]


def _load_actions(path: str | Path | None) -> list[TacticAction]:
    if not path:
        return []
    return [TacticAction.from_dict(x) for x in read_jsonl(path)]


def _load_actions_grouped(path: str | Path | None) -> tuple[list[TacticAction], dict[str, list[TacticAction]]]:
    if not path:
        return [], {}
    global_actions: list[TacticAction] = []
    by_task: dict[str, list[TacticAction]] = {}
    for row in read_jsonl(path):
        task_id = row.get("task_id") or (row.get("metadata") or {}).get("task_id")
        action = TacticAction.from_dict(row)
        if task_id:
            by_task.setdefault(str(task_id), []).append(action)
        else:
            global_actions.append(action)
    return global_actions, by_task


def _detect_import_mode(mode: str, workdir: str | None = None, lean_cmd: str | None = None) -> str:
    mode = mode or "preserve"
    if mode != "auto":
        return mode
    if workdir:
        lake = Path(workdir) / "lakefile.lean"
        if lake.exists():
            text = lake.read_text(encoding="utf-8", errors="ignore").lower()
            return "mathlib" if "mathlib" in text else "core"
    if lean_cmd and "lake" not in lean_cmd:
        return "core"
    return "preserve"


def _normalize_tasks_imports(
    tasks: list[LeanTask],
    mode: str = "preserve",
    workdir: str | None = None,
    lean_cmd: str | None = None,
) -> list[LeanTask]:
    resolved = _detect_import_mode(mode, workdir, lean_cmd)
    if resolved == "preserve":
        return tasks
    out: list[LeanTask] = []
    for task in tasks:
        imports = list(task.imports)
        if resolved == "core":
            imports = [imp for imp in imports if not (imp == "Mathlib" or imp.startswith("Mathlib."))]
        elif resolved == "mathlib":
            if not any(imp == "Mathlib" or imp.startswith("Mathlib.") for imp in imports):
                imports = ["Mathlib"] + imports
        else:
            raise ValueError(f"unknown import mode: {mode}")
        out.append(replace(task, imports=imports))
    return out


def _actions_for_tasks(
    tasks: list[LeanTask],
    base_actions: list[TacticAction],
    task_actions: dict[str, list[TacticAction]] | None = None,
    *,
    state_candidates: bool = False,
    candidate_mode: str = "state",
    max_candidates: int = 64,
):
    task_actions = task_actions or {}
    if not state_candidates and base_actions and not task_actions:
        return base_actions
    gen = (
        StateDependentCandidateGenerator(max_exposures=4)
        if candidate_mode == "state"
        else TacticCandidateGenerator(CandidateGeneratorConfig(use_carrier_exposure=False, max_candidates=max_candidates))
    )
    by_task: dict[str, list[TacticAction]] = {}
    for task in tasks:
        state = ProofState.from_task(task)
        acts: list[TacticAction] = list(base_actions) + list(task_actions.get(task.task_id, []))
        if state_candidates or not acts:
            if isinstance(gen, StateDependentCandidateGenerator):
                acts.extend(gen.candidates(task, state, max_candidates=max_candidates))
            else:
                acts.extend(gen.candidates(task, state))
        seen: set[str] = set()
        dedup: list[TacticAction] = []
        for action in acts:
            if action.tactic not in seen:
                seen.add(action.tactic)
                dedup.append(action)
            if len(dedup) >= max_candidates:
                break
        by_task[task.task_id] = dedup
    return by_task


def _executor_from_args(args: argparse.Namespace) -> LeanExecutor:
    return LeanExecutor(
        LeanExecutorConfig(
            lean_cmd=args.lean_cmd,
            timeout_s=args.timeout_s,
            dry_run=args.dry_run,
            keep_files=args.keep_files,
            workdir=args.workdir,
            cache_dir=args.cache_dir,
            trace_state=args.trace_state,
        )
    )


def _server_config_from_args(args: argparse.Namespace) -> LeanServerConfig:
    backend = getattr(args, "server_backend", None) or getattr(args, "lean_server_backend", None)
    if backend in {None, "auto"}:
        if getattr(args, "dry_run", False):
            backend = "dry_run"
        elif getattr(args, "server_cmd", None):
            backend = "jsonl"
        else:
            backend = "file_fallback"
    if backend == "dry":
        backend = "dry_run"
    if backend == "file":
        backend = "file_fallback"
    return LeanServerConfig(
        lean_cmd=getattr(args, "lean_cmd", "lake env lean"),
        workdir=getattr(args, "workdir", None),
        timeout_s=float(getattr(args, "timeout_s", 20.0)),
        dry_run=bool(getattr(args, "dry_run", False)),
        keep_files=bool(getattr(args, "keep_files", False)),
        cache_dir=getattr(args, "cache_dir", None),
        trace_state=bool(getattr(args, "trace_state", False)),
        backend=backend,
        server_cmd=getattr(args, "server_cmd", None),
        request_timeout_s=getattr(args, "request_timeout_s", None),
        fallback_to_file=not bool(getattr(args, "server_no_fallback", False)),
        native_exec_mode=getattr(args, "native_exec_mode", "source_check"),
    )


def add_exec_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--lean-cmd", default="lake env lean")
    parser.add_argument("--workdir")
    parser.add_argument("--timeout-s", type=float, default=20.0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--keep-files", action="store_true")
    parser.add_argument("--cache-dir")
    parser.add_argument("--trace-state", action="store_true")
    parser.add_argument("--import-mode", choices=["preserve", "auto", "core", "mathlib"], default="auto")
    parser.add_argument("--lean-server", action="store_true")
    parser.add_argument(
        "--lean-server-backend",
        choices=["auto", "dry_run", "file_fallback", "file", "dry", "jsonl", "persistent", "native"],
        default=None,
    )
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--flush-every", type=int, default=50)
    parser.add_argument("--max-actions", type=int, default=64)
    parser.add_argument("--candidate-mode", choices=["basic", "state"], default="state")
    parser.add_argument("--state-candidates", action="store_true")


__all__ = [
    "_actions_for_tasks",
    "_executor_from_args",
    "_json_dump",
    "_load_actions",
    "_load_actions_grouped",
    "_load_tasks",
    "_normalize_tasks_imports",
    "_server_config_from_args",
    "add_exec_args",
]
