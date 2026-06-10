from __future__ import annotations

__all__ = [
    "main",
    "build_parser",
    "_load_actions_grouped",
    "_actions_for_tasks",
    "_materialize_total_budget_task_actions",
]


def build_parser():
    from .main import build_parser as _build_parser

    return _build_parser()


def main(argv: list[str] | None = None) -> int:
    from .main import main as _main

    return _main(argv)


def __getattr__(name: str):
    if name in {"_load_actions_grouped", "_actions_for_tasks"}:
        from .common import _actions_for_tasks, _load_actions_grouped

        return {
            "_actions_for_tasks": _actions_for_tasks,
            "_load_actions_grouped": _load_actions_grouped,
        }[name]
    if name == "_materialize_total_budget_task_actions":
        from .experiment import _materialize_total_budget_task_actions

        return _materialize_total_budget_task_actions
    raise AttributeError(name)
