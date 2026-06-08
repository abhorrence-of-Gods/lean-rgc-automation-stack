from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import json

from .cli import main as cli_main


@dataclass
class PipelineConfig:
    tasks: str
    actions: str | None
    out: str
    dry_run: bool = True
    jobs: int = 1
    max_actions: int = 32
    quotient_tolerance: float = 0.25
    carrier_threshold: float = 0.1
    lean_cmd: str = "lake env lean"
    workdir: str | None = None
    timeout_s: float = 20.0
    keep_files: bool = False
    cache_dir: str | None = None
    trace_state: bool = False
    import_mode: str = "auto"
    resume: bool = False
    flush_every: int = 50
    fit_gamma: bool = False
    gamma_horizon: int = 4

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_basic_pipeline(cfg: PipelineConfig) -> dict[str, Any]:
    """Run the same real/dry Lean pipeline exposed by the CLI."""
    out = Path(cfg.out)
    out.mkdir(parents=True, exist_ok=True)
    audit_dir = out / "audit"
    args = [
        "batch-audit",
        "--tasks", cfg.tasks,
        "--out", str(audit_dir),
        "--jobs", str(cfg.jobs),
        "--max-actions", str(cfg.max_actions),
        "--lean-cmd", cfg.lean_cmd,
        "--timeout-s", str(cfg.timeout_s),
        "--import-mode", cfg.import_mode,
        "--flush-every", str(cfg.flush_every),
    ]
    if cfg.actions:
        args += ["--actions", cfg.actions]
    if cfg.workdir:
        args += ["--workdir", cfg.workdir]
    if cfg.dry_run:
        args += ["--dry-run"]
    if cfg.keep_files:
        args += ["--keep-files"]
    if cfg.cache_dir:
        args += ["--cache-dir", cfg.cache_dir]
    if cfg.trace_state:
        args += ["--trace-state"]
    if cfg.resume:
        args += ["--resume"]
    cli_main(args)

    train_args = ["train-response", "--responses", str(audit_dir / "responses.jsonl"), "--out", str(out / "response_model.json")]
    if cfg.actions:
        train_args += ["--actions", cfg.actions]
    cli_main(train_args)
    cli_main(["quotient", "--responses", str(audit_dir / "responses.jsonl"), "--out", str(out / "response_components.jsonl"), "--tolerance", str(cfg.quotient_tolerance)])
    if cfg.actions:
        cli_main(["carrier-coker", "--defects", str(audit_dir / "defects.jsonl"), "--actions", cfg.actions, "--out", str(out / "carrier_coker.jsonl")])
    cli_main(["carrier-generate", "--defects", str(audit_dir / "defects.jsonl"), "--out", str(out / "carrier_generated_contexts.jsonl"), "--threshold", str(cfg.carrier_threshold)])
    cli_main(["make-transitions", "--responses", str(audit_dir / "responses.jsonl"), "--out", str(out / "transitions.jsonl")])
    gamma_args = ["gamma-audit", "--transitions", str(out / "transitions.jsonl"), "--out", str(out / "gamma_audit.jsonl"), "--horizon", str(cfg.gamma_horizon)]
    if cfg.fit_gamma:
        gamma_args += ["--fit-gamma"]
    cli_main(gamma_args)
    cli_main(["report", "--run-dir", str(audit_dir), "--out", str(out / "pipeline_report.json")])
    summary = {"config": cfg.to_dict(), "files": {"audit_dir": str(audit_dir), "response_model": str(out / "response_model.json"), "components": str(out / "response_components.jsonl"), "carrier_generated": str(out / "carrier_generated_contexts.jsonl"), "transitions": str(out / "transitions.jsonl"), "gamma_audit": str(out / "gamma_audit.jsonl")}}
    (out / "pipeline_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary
