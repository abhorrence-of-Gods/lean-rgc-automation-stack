from __future__ import annotations

import argparse
import sys
import types

from .audit import register_audit_commands
from .benchmark import register_benchmark_commands
from .crg import register_crg_commands
from .data import register_data_commands
from .dost import register_dost_commands
from .evalcmd import register_eval_commands
from .common import _actions_for_tasks, _load_actions_grouped
from .experiment import _materialize_total_budget_task_actions, register_experiment_commands
from .lean import register_lean_commands
from .pipeline import register_pipeline_commands
from .poms import register_poms_commands


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lean-rgc", description="Lean-RGC automation stack")
    sub = parser.add_subparsers(dest="cmd", required=True)
    register_audit_commands(sub)
    register_benchmark_commands(sub)
    register_lean_commands(sub)
    register_experiment_commands(sub)
    register_dost_commands(sub)
    register_pipeline_commands(sub)
    register_crg_commands(sub)
    register_poms_commands(sub)
    register_data_commands(sub)
    register_eval_commands(sub)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())


class _CallableMainModule(types.ModuleType):
    def __call__(self, argv: list[str] | None = None) -> int:
        return main(argv)


sys.modules[__name__].__class__ = _CallableMainModule
