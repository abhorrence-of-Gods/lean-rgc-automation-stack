from __future__ import annotations

from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any
import json
import re

from .schemas import LeanTask, TacticAction, AuditRecord, read_jsonl, write_jsonl, stable_hash
from .lean.executor import LeanExecutor, LeanExecutorConfig


def _sanitize_ident(x: str) -> str:
    y = re.sub(r"[^A-Za-z0-9_]", "_", x or "")
    if not y or y[0].isdigit():
        y = "x_" + y
    return y[:96]


@dataclass
class ProofScript:
    task_id: str
    statement: str
    proof_script: str
    imports: list[str] = field(default_factory=list)
    namespace: str | None = None
    allowed_axioms: list[str] = field(default_factory=list)
    max_heartbeats: int = 200000
    source: str = "trajectory"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ProofScript":
        return cls(
            task_id=str(d.get("task_id", "")),
            statement=str(d.get("statement", "")),
            proof_script=str(d.get("proof_script") or d.get("prefix") or d.get("script") or ""),
            imports=list(d.get("imports") or []),
            namespace=d.get("namespace"),
            allowed_axioms=list(d.get("allowed_axioms") or []),
            max_heartbeats=int(d.get("max_heartbeats") or 200000),
            source=str(d.get("source") or "script"),
            metadata=dict(d.get("metadata") or {}),
        )

    def to_task_action(self, *, action_suffix: str = "replay") -> tuple[LeanTask, TacticAction]:
        task = LeanTask(
            task_id=self.task_id,
            statement=self.statement,
            imports=list(self.imports),
            prefix="",
            namespace=self.namespace,
            max_heartbeats=self.max_heartbeats,
            allowed_axioms=list(self.allowed_axioms),
            metadata={"proof_script_source": self.source, **(self.metadata or {})},
        )
        action = TacticAction(
            action_id="proof_replay_" + stable_hash({"task": self.task_id, "script": self.proof_script, "suffix": action_suffix}, 14),
            tactic=self.proof_script,
            tactic_class="proof_replay",
            carrier_tags=["replay", "audit"],
            cost_estimate=0.0,
            max_heartbeats=self.max_heartbeats,
            metadata={"generated_by": "proof_replay", "source": self.source},
        )
        return task, action


def scripts_from_trajectories(trajectories_path: str | Path, tasks_path: str | Path, out_path: str | Path, *, proved_only: bool = True, include_partial: bool = False) -> dict[str, Any]:
    tasks = {str(r.get("task_id")): LeanTask.from_dict(r) for r in read_jsonl(tasks_path)}
    rows: list[dict[str, Any]] = []
    missing: list[str] = []
    skipped = 0
    for tr in read_jsonl(trajectories_path):
        tid = str(tr.get("task_id", ""))
        final_status = str(tr.get("final_status", ""))
        if proved_only and final_status != "proved":
            skipped += 1
            continue
        if (not proved_only) and (not include_partial) and final_status not in {"proved", "partial", "max_steps"}:
            skipped += 1
            continue
        task = tasks.get(tid)
        if task is None:
            missing.append(tid)
            continue
        proof_script = str(tr.get("prefix") or "").strip()
        if not proof_script:
            skipped += 1
            continue
        ps = ProofScript(
            task_id=tid,
            statement=task.statement,
            imports=list(task.imports),
            namespace=task.namespace,
            allowed_axioms=list(task.allowed_axioms),
            max_heartbeats=task.max_heartbeats,
            proof_script=proof_script,
            source="trajectory",
            metadata={"final_status": final_status, "n_steps": len(tr.get("steps") or []), "trajectory_metadata": tr.get("metadata") or {}},
        )
        rows.append(ps.to_dict())
    write_jsonl(out_path, rows)
    return {"n_scripts": len(rows), "skipped": skipped, "missing_tasks": sorted(set(missing)), "out": str(out_path)}


def replay_proof_scripts(scripts_path: str | Path, out_dir: str | Path, config: LeanExecutorConfig, *, keep_fail_files: bool = True) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    executor = LeanExecutor(config)
    audit_rows: list[dict[str, Any]] = []
    status_counts: dict[str, int] = {}
    for row in read_jsonl(scripts_path):
        ps = ProofScript.from_dict(row)
        task, action = ps.to_task_action()
        rec = executor.run_tactic(task, action)
        d = rec.to_dict()
        d["proof_script"] = ps.to_dict()
        d["replay_ok"] = rec.status == "success"
        audit_rows.append(d)
        status_counts[rec.status] = status_counts.get(rec.status, 0) + 1
    write_jsonl(out / "proof_replay_audit.jsonl", audit_rows)
    ok = status_counts.get("success", 0)
    summary = {
        "n": len(audit_rows),
        "replayed": ok,
        "replay_rate": ok / max(1, len(audit_rows)),
        "statuses": status_counts,
        "scripts": str(scripts_path),
        "out": str(out),
    }
    (out / "proof_replay_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


def export_proof_file(scripts_path: str | Path, out_file: str | Path, *, theorem_prefix: str = "rgc_replay") -> dict[str, Any]:
    rows = [ProofScript.from_dict(r) for r in read_jsonl(scripts_path)]
    imports: list[str] = []
    seen_imports: set[str] = set()
    for ps in rows:
        for imp in ps.imports:
            if imp not in seen_imports:
                seen_imports.add(imp)
                imports.append(imp)
    lines: list[str] = [f"import {imp}" for imp in imports]
    if imports:
        lines.append("")
    for i, ps in enumerate(rows):
        name = _sanitize_ident(f"{theorem_prefix}_{i:04d}_{ps.task_id}")
        lines.append(f"/- RGC_PROOF_SCRIPT task={ps.task_id} source={ps.source} -/")
        lines.append(f"set_option maxHeartbeats {ps.max_heartbeats}")
        if ps.namespace:
            lines.append(f"namespace {ps.namespace}")
        lines.append(f"theorem {name} : {ps.statement} := by")
        for ln in (ps.proof_script or "").splitlines():
            lines.append("  " + ln if ln.strip() else "")
        if ps.namespace:
            lines.append(f"end {ps.namespace}")
        lines.append("")
    Path(out_file).parent.mkdir(parents=True, exist_ok=True)
    Path(out_file).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"n_scripts": len(rows), "out": str(out_file)}


__all__ = ["ProofScript", "scripts_from_trajectories", "replay_proof_scripts", "export_proof_file"]
