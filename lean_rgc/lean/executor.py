from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import re
import shlex
import subprocess
import tempfile
import time
from typing import Sequence

from ..schemas import AuditRecord, LeanTask, ProofState, TacticAction, stable_hash
from .state_parser import LeanMessageParser
from ..cache import AuditCache


@dataclass
class LeanExecutorConfig:
    lean_cmd: str = "lake env lean"
    workdir: str | None = None
    timeout_s: float = 20.0
    keep_files: bool = False
    dry_run: bool = False
    extra_set_options: dict[str, str | int | bool] | None = None
    cache_dir: str | None = None
    trace_state: bool = False


class LeanExecutor:
    """File-based Lean micro-audit executor.

    This conservative harness creates a temporary Lean file containing a theorem
    and a candidate tactic proof. It works with either `lake env lean` or `lean`.
    It is intentionally simple: state parsing is delegated to DefectExtractor.

    For step-level experiments, put the previous proof prefix in LeanTask.prefix;
    the tactic is appended after that prefix.
    """

    def __init__(self, config: LeanExecutorConfig | None = None, **kwargs):
        if config is None:
            config = LeanExecutorConfig(**kwargs)
        self.config = config
        self.cache = AuditCache(config.cache_dir) if config.cache_dir else None

    @staticmethod
    def _indent_tactic_block(text: str, spaces: str = "  ") -> str:
        """Indent multi-line tactic blocks for insertion under `by`.

        Earlier versions prefixed only the first line of a generated tactic.
        That is fragile for real Lean because generated actions often look like
        `intros\nrfl` or `constructor <;> simp_all`.  This helper treats
        prefixes and core tactics as blocks and indents every non-empty line.
        """
        lines = (text or "").rstrip().splitlines()
        return "\n".join((spaces + ln if ln.strip() else ln) for ln in lines)

    def _render_file(self, task: LeanTask, action: TacticAction) -> str:
        imports = "\n".join(f"import {imp}" for imp in task.imports)
        top_preamble = str((task.metadata or {}).get("top_preamble") or "").strip()
        options = {
            "maxHeartbeats": action.max_heartbeats or task.max_heartbeats,
        }
        if self.config.extra_set_options:
            options.update(self.config.extra_set_options)
        option_lines = []
        for k, v in options.items():
            if isinstance(v, bool):
                val = "true" if v else "false"
            else:
                val = str(v)
            option_lines.append(f"set_option {k} {val}")
        namespace_open = f"namespace {task.namespace}\n" if task.namespace else ""
        namespace_close = f"end {task.namespace}\n" if task.namespace else ""
        theorem_name = "rgc_probe_" + stable_hash({"task": task.task_id, "action": action.action_id})
        prefix = task.prefix.rstrip()
        body_blocks: list[str] = []
        if prefix:
            body_blocks.append(prefix)
        if self.config.trace_state:
            body_blocks.append("try trace_state")
        if action.tactic.strip():
            body_blocks.append(action.tactic)
        if self.config.trace_state:
            body_blocks.append("try trace_state")
        body = "\n".join(self._indent_tactic_block(block) for block in body_blocks if block.strip())
        return f"""{imports}

{top_preamble}

{chr(10).join(option_lines)}

{namespace_open}theorem {theorem_name} : {task.statement} := by
{body}
{namespace_close}"""

    def run_tactic(self, task: LeanTask, action: TacticAction, state: ProofState | None = None) -> AuditRecord:
        if state is None:
            state = ProofState.from_task(task)
        cache_key = None
        if self.cache is not None:
            cache_key = self.cache.key(task, action, lean_cmd=self.config.lean_cmd, workdir_hash=str(self.config.workdir or ""), version="executor-v2-trace" if self.config.trace_state else "executor-v2")
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached
        if self.config.dry_run:
            rec = self._dry_run(task, action, state)
            if self.cache is not None and cache_key is not None:
                self.cache.put(cache_key, rec)
            return rec

        lean_src = self._render_file(task, action)
        with tempfile.TemporaryDirectory(prefix="lean_rgc_") as td:
            td_path = Path(td)
            lean_file = td_path / f"{task.task_id}_{action.action_id}.lean"
            lean_file.write_text(lean_src, encoding="utf-8")
            cmd = shlex.split(self.config.lean_cmd) + [str(lean_file)]
            t0 = time.time()
            try:
                proc = subprocess.run(
                    cmd,
                    cwd=self.config.workdir or os.getcwd(),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=self.config.timeout_s,
                )
                elapsed = (time.time() - t0) * 1000.0
                stdout = proc.stdout or ""
                stderr = proc.stderr or ""
                status = self._classify_success(stdout + "\n" + stderr) if proc.returncode == 0 else self._classify_failure(stdout + "\n" + stderr)
            except subprocess.TimeoutExpired as e:
                elapsed = (time.time() - t0) * 1000.0
                stdout = e.stdout if isinstance(e.stdout, str) else ""
                stderr = e.stderr if isinstance(e.stderr, str) else ""
                status = "timeout"
            keep_path = None
            if self.config.keep_files:
                out_dir = Path(self.config.workdir or os.getcwd()) / ".lean_rgc_audit_files"
                out_dir.mkdir(parents=True, exist_ok=True)
                keep_path = out_dir / lean_file.name
                keep_path.write_text(lean_src, encoding="utf-8")
            messages = self._split_messages(stdout + "\n" + stderr)
            after_state = self._parse_after_state(task, state, stdout + "\n" + stderr, status)
            rec = AuditRecord(
                task_id=task.task_id,
                state_id=state.state_id,
                action_id=action.action_id,
                status=status,  # type: ignore[arg-type]
                elapsed_ms=elapsed,
                heartbeats=self._parse_heartbeats(stdout + "\n" + stderr),
                stdout=stdout,
                stderr=stderr,
                messages=messages,
                after_state=after_state,
                audit_flags=self._audit_flags(stdout + "\n" + stderr, status),
                lean_file=str(keep_path or lean_file),
            )
            if self.cache is not None and cache_key is not None:
                self.cache.put(cache_key, rec)
            return rec

    def _dry_run(self, task: LeanTask, action: TacticAction, state: ProofState) -> AuditRecord:
        # Deterministic pseudo-audit for CI / Colab without Lean installed.
        txt = (task.statement + "\n" + action.tactic).lower()
        tac = action.tactic.lower()
        easy = any(k in tac for k in ["rfl", "simp", "omega", "norm_num", "trivial"])
        arithmetic = any(k in txt for k in ["nat", "int", "+", "*", "≤", "<", "="])
        needs_intro = ("∀" in task.statement or "->" in task.statement or "→" in task.statement)
        has_intro = "intro" in tac or "intros" in tac
        and_goal = "∧" in task.statement or " and " in txt
        has_constructor = "constructor" in tac
        success = False
        exposed_target = task.statement
        if has_intro and needs_intro:
            exposed_target = self._dry_expose_intros(task.statement)
        if "trivial" in tac and task.statement.strip().lower() == "true":
            success = True
        elif needs_intro and not has_intro:
            success = False
        elif "rfl" in tac and "=" in exposed_target:
            # Treat intro+rfl as closing reflexive equality charts.  This is a
            # dry-run heuristic only; real Lean remains authoritative.
            success = True
        elif easy and arithmetic:
            success = True
        elif and_goal and has_intro and has_constructor and ("assumption" in tac or "simp_all" in tac):
            success = True
        elif "simp" in tac and (arithmetic or needs_intro or and_goal):
            success = True
        elif has_intro and needs_intro and tac.strip() in {"intro", "intros"}:
            # Exposure-only: valid partial progress, not a closed proof.
            success = False
        status = "success" if success else "dry_run"
        msg = "dry-run success heuristic" if success else "dry-run no Lean execution"
        after_target = "" if success else (exposed_target if has_intro and needs_intro else task.statement)
        after = ProofState(
            state_id=stable_hash({"after": state.state_id, "action": action.action_id, "target": after_target}),
            task_id=task.task_id,
            target=after_target,
            goals_text=("⊢ " + after_target) if after_target else "",
            raw_messages=[msg],
        )
        return AuditRecord(
            task_id=task.task_id,
            state_id=state.state_id,
            action_id=action.action_id,
            status=status,  # type: ignore[arg-type]
            elapsed_ms=0.0,
            messages=[msg],
            after_state=after,
            audit_flags={"dry_run": True},
        )

    @staticmethod
    def _dry_expose_intros(statement: str) -> str:
        """Very small dry-run frontier chart for intro exposure.

        This is not a parser for Lean; it only makes Colab/CI dry-runs reflect
        that `intros` exposes forall/imp goals before core tactics are scored.
        """
        s = (statement or "").strip()
        # Strip leading forall binders of the common form `∀ ... , body`.
        if s.startswith("∀") and "," in s:
            s = s.split(",", 1)[1].strip()
        # Strip simple implication antecedents from the left.
        # Keep only the consequent after the last top-level-ish arrow; this is
        # intentionally conservative textual charting.
        for arrow in ["→", "->"]:
            if arrow in s:
                s = s.split(arrow)[-1].strip()
        return s or statement

    @staticmethod
    def _classify_success(text: str) -> str:
        # Defect #6 (2026-07-06): `sorry` (and sorryAx-based macros) elaborate
        # at exit code 0 with only a warning, so a returncode check alone
        # certifies proof holes as successes. Lean 4 emits exactly
        # "declaration uses 'sorry'" for every such hole.
        if "declaration uses 'sorry'" in text.lower():
            return "unsafe"
        return "success"

    @staticmethod
    def _classify_failure(text: str) -> str:
        low = text.lower()
        if "timeout" in low or "maximum recursion" in low or "maxheartbeats" in low:
            return "timeout"
        if "unsolved goals" in low:
            return "partial"
        if "unsolved goals" in low and not any(x in low for x in ["unknown identifier", "type mismatch", "failed to synthesize"]):
            return "partial"
        if "sorry" in low or "admit" in low or "unsound" in low:
            return "unsafe"
        if "failed to synthesize" in low or "type mismatch" in low or "unknown identifier" in low or "unknown module prefix" in low:
            return "elab_error"
        return "fail"

    @staticmethod
    def _parse_heartbeats(text: str) -> int | None:
        m = re.search(r"heartbeats[:=]\s*(\d+)", text, flags=re.IGNORECASE)
        if m:
            return int(m.group(1))
        return None

    @staticmethod
    def _split_messages(text: str) -> list[str]:
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        return lines[-80:]

    @staticmethod
    def _audit_flags(text: str, status: str) -> dict[str, bool]:
        low = text.lower()
        return {
            "uses_sorry": "sorry" in low,
            "uses_admit": "admit" in low,
            "timeout": status == "timeout",
            "elab_error": status == "elab_error",
            "partial_success": "unsolved goals" in low or "unsolved goal" in low,
            "nonreproducible": False,
        }

    @staticmethod
    def _parse_after_state(task: LeanTask, state: ProofState, text: str, status: str) -> ProofState | None:
        if status == "success":
            return ProofState(
                state_id=stable_hash({"closed": state.state_id}),
                task_id=task.task_id,
                goals_text="",
                target="",
                raw_messages=[],
            )
        parsed = LeanMessageParser().parse(text)
        if parsed.goals:
            return parsed.to_proof_state(task.task_id, fallback_target=task.statement)
        goals = "\n".join(text.splitlines()[-30:])
        return ProofState(
            state_id=stable_hash({"after": state.state_id, "text": goals[:1000]}),
            task_id=task.task_id,
            goals_text=goals,
            target=task.statement,
            raw_messages=LeanExecutor._split_messages(text),
            features={"partial_success": float("unsolved goal" in text.lower())},
        )


__all__ = ["LeanExecutor", "LeanExecutorConfig"]
