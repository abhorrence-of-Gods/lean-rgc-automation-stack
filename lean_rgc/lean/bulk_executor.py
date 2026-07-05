from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import json
import os
import re
import shlex
import subprocess
import tempfile
import time
from typing import Any

from ..schemas import AuditRecord, DefectVector, LeanTask, ProofState, TacticAction, stable_hash, write_records
from ..batch import SCHEMA_AUDIT_ROW, SCHEMA_DEFECT_ROW, SCHEMA_RESPONSE_ROW
from ..dataset import summarize_response_rows
from .executor import LeanExecutor, LeanExecutorConfig
from ..defects import ProofDefectExtractor


@dataclass
class BulkAuditConfig:
    lean_cmd: str = "lake env lean"
    workdir: str | None = None
    timeout_s: float = 60.0
    batch_size: int = 64
    keep_files: bool = False
    import_mode: str = "preserve"
    trace_state: bool = False
    # Defect #5 (2026-07-05): batching cannot guarantee isolation against
    # scope-consuming scripts — an unterminated block comment silently
    # comments out the REST of the chunk, mass-producing false successes
    # that no retro attribution can detect. Successes are therefore
    # confirmed by an individual re-audit before they may become labels.
    confirm_successes: bool = True


@dataclass
class BulkBlock:
    task: LeanTask
    action: TacticAction
    start_line: int
    end_line: int
    theorem_name: str


@dataclass
class BulkAuditReport:
    n_blocks: int
    n_success: int
    n_fail: int
    n_batches: int
    elapsed_ms: float
    lean_cmd: str
    status_counts: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _classify_block_failure(text: str) -> str:
    low = text.lower()
    if "timeout" in low or "maxheartbeats" in low or "maximum recursion" in low:
        return "timeout"
    if "unsolved goals" in low or "unsolved goal" in low:
        return "partial"
    if "sorry" in low or "admit" in low or "unsound" in low:
        return "unsafe"
    if "failed to synthesize" in low or "type mismatch" in low or "unknown identifier" in low or "unknown module prefix" in low:
        return "elab_error"
    return "fail"


def _sanitize_ident(x: str) -> str:
    y = re.sub(r"[^A-Za-z0-9_]", "_", x)
    # Mathlib's linter.style.nameCheck flags identifiers containing "__", and
    # a style warning on the generated wrapper name fails the whole audit
    # block (found by the g1 positive control: task_id "__positive_control__").
    y = re.sub(r"_+", "_", y).strip("_")
    if not y:
        y = "x"
    if y[0].isdigit():
        y = "x_" + y
    return y[:80].rstrip("_") or "x"


def _render_bulk_file(pairs: list[tuple[LeanTask, TacticAction]], *, trace_state: bool = False) -> tuple[str, list[BulkBlock]]:
    imports: list[str] = []
    seen: set[str] = set()
    preambles: list[str] = []
    seen_preambles: set[str] = set()
    for task, _ in pairs:
        for imp in task.imports:
            if imp not in seen:
                seen.add(imp)
                imports.append(imp)
        preamble = str((task.metadata or {}).get("top_preamble") or "").strip()
        if preamble and preamble not in seen_preambles:
            seen_preambles.add(preamble)
            preambles.append(preamble)
    lines: list[str] = [f"import {imp}" for imp in imports]
    if preambles:
        if imports:
            lines.append("")
        for preamble in preambles:
            lines.extend(preamble.splitlines())
    if imports:
        lines.append("")
    blocks: list[BulkBlock] = []
    for idx, (task, action) in enumerate(pairs):
        theorem_name = "rgc_bulk_" + _sanitize_ident(task.task_id) + "_" + stable_hash({"task": task.task_id, "action": action.action_id, "idx": idx}, n=10)
        lines.append(f"/- RGC_AUDIT_BEGIN task={task.task_id} action={action.action_id} -/")
        start_line = len(lines) + 1
        max_hb = action.max_heartbeats or task.max_heartbeats
        lines.append(f"set_option maxHeartbeats {max_hb}")
        if task.namespace:
            lines.append(f"namespace {task.namespace}")
        prefix = (task.prefix or "").rstrip()
        lines.append(f"theorem {theorem_name} : {task.statement} := by")
        if prefix:
            for pl in prefix.splitlines():
                lines.append("  " + pl if pl.strip() else "")
        if trace_state:
            lines.append("  try trace_state")
        tac_lines = (action.tactic or "").splitlines() or [""]
        for tl in tac_lines:
            lines.append("  " + tl if tl.strip() else "")
        if trace_state:
            lines.append("  try trace_state")
        if task.namespace:
            lines.append(f"end {task.namespace}")
        end_line = len(lines)
        lines.append(f"/- RGC_AUDIT_END task={task.task_id} action={action.action_id} -/")
        lines.append("")
        blocks.append(BulkBlock(task=task, action=action, start_line=start_line, end_line=end_line, theorem_name=theorem_name))
    return "\n".join(lines) + "\n", blocks


# The optional (?P<tag>...) group catches Lean's tagged diagnostics
# ('error(lean.unknownIdentifier): ...'). Without it, tagged lines were
# stored as continuations under the PREVIOUS plain error's line key —
# and a block whose ONLY errors were tagged carried no messages at all
# and was classified SUCCESS (false-positive labels; found by the S1
# stepwise replay re-auditing claimed pilot successes).
_ERROR_RE = re.compile(r"^(?P<file>.*?\.lean):(?P<line>\d+):(?P<col>\d+):\s*(?P<level>error|warning)(?P<tag>\([^)]*\))?:\s*(?P<msg>.*)$")


def _errors_by_line(output: str) -> dict[int, list[str]]:
    out: dict[int, list[str]] = {}
    current_line: int | None = None
    for raw in output.splitlines():
        m = _ERROR_RE.match(raw.strip())
        if m:
            current_line = int(m.group("line"))
            if m.group("level") == "error":
                out.setdefault(current_line, []).append(raw.strip())
        elif current_line is not None:
            # Attach continuation lines to previous error. Lean messages are multi-line.
            if raw.strip():
                out.setdefault(current_line, []).append(raw.rstrip())
    return out


def _attribute_lines(blocks: list[BulkBlock], line_errors: dict[int, list[str]]) -> tuple[list[list[str]], list[str]]:
    """Ownership-based attribution (defects #3/#4, 2026-07-05).

    A block whose script ends in an incomplete construct (e.g. a bare
    `calc`) absorbs the FOLLOWING block's source until the parser stops —
    the parse error then lands on the next block's set_option line, and
    the offender itself carries no error (false success) while the
    neighbor is poisoned (false failure). Similarly a dangling construct
    in the LAST block errors past every block range and became a global
    message that failed the whole chunk.

    Rule: block k owns [start_k, start_{k+1}] INCLUSIVE of the next
    block's set_option line (which cannot error on its own), and the
    last block owns through EOF. Only lines before the first block
    (imports/environment) remain global.
    """
    per_block: list[list[str]] = [[] for _ in blocks]
    global_msgs: list[str] = []
    if not blocks:
        return per_block, [x for xs in line_errors.values() for x in xs]
    starts = [b.start_line for b in blocks]
    for line in sorted(line_errors):
        xs = line_errors[line]
        if line < starts[0]:
            global_msgs.extend(xs)
            continue
        owner = 0
        for k in range(len(blocks)):
            upper = starts[k + 1] if k + 1 < len(blocks) else float("inf")
            if starts[k] <= line <= upper:
                owner = k
                break
        per_block[owner].extend(xs)
    return [msgs[-80:] for msgs in per_block], global_msgs


def _block_messages(block: BulkBlock, line_errors: dict[int, list[str]]) -> list[str]:
    msgs: list[str] = []
    # Lean sometimes reports theorem-level errors on any line inside the block.
    for line, xs in line_errors.items():
        if block.start_line <= line <= block.end_line:
            msgs.extend(xs)
    return msgs[-80:]


def _global_messages(blocks: list[BulkBlock], line_errors: dict[int, list[str]], combined: str, returncode: int) -> list[str]:
    msgs: list[str] = []
    for line, xs in line_errors.items():
        if not any(block.start_line <= line <= block.end_line for block in blocks):
            msgs.extend(xs)
    if returncode != 0 and not msgs and not line_errors:
        tail = "\n".join(ln for ln in combined.splitlines()[-40:] if ln.strip())
        if tail:
            msgs.append(tail)
        else:
            msgs.append(f"Lean process exited with code {returncode}")
    return msgs[-80:]


class LeanBulkAuditor:
    """Batch-file Lean executor.

    This is not a persistent Lean server. It is a production-oriented bridge
    between one-process-per-audit and a true server: many theorem/action probes
    are placed into one Lean file, compiled once, and then mapped back to blocks
    via source line numbers. It is faster and more reproducible for 1k--10k
    pilot audits, while preserving the same AuditRecord / ResponseRecord schema.
    """

    def __init__(self, config: BulkAuditConfig | None = None):
        self.config = config or BulkAuditConfig()
        self.extractor = ProofDefectExtractor()

    def run_pairs(self, pairs: list[tuple[LeanTask, TacticAction]]) -> tuple[list[AuditRecord], BulkAuditReport]:
        all_records: list[AuditRecord] = []
        t0 = time.time()
        n_batches = 0
        for i in range(0, len(pairs), max(1, self.config.batch_size)):
            chunk = pairs[i:i + max(1, self.config.batch_size)]
            n_batches += 1
            recs = self._run_chunk(chunk, batch_index=n_batches)
            all_records.extend(recs)
        if self.config.confirm_successes and self.config.batch_size > 1:
            # Isolation confirmation: the isolated verdict wins. Successes
            # are rare, so this costs a handful of single-block audits.
            for idx, (pair, rec) in enumerate(zip(pairs, all_records)):
                if rec.status != "success":
                    continue
                n_batches += 1
                iso = self._run_chunk([pair], batch_index=n_batches)[0]
                iso.audit_flags = dict(iso.audit_flags or {})
                iso.audit_flags["isolation_confirmed"] = iso.status == "success"
                if iso.status != "success":
                    iso.audit_flags["batch_claimed_success"] = True
                all_records[idx] = iso
        status_counts: dict[str, int] = {}
        for r in all_records:
            status_counts[r.status] = status_counts.get(r.status, 0) + 1
        elapsed = (time.time() - t0) * 1000.0
        report = BulkAuditReport(
            n_blocks=len(pairs),
            n_success=status_counts.get("success", 0),
            n_fail=len(pairs) - status_counts.get("success", 0),
            n_batches=n_batches,
            elapsed_ms=elapsed,
            lean_cmd=self.config.lean_cmd,
            status_counts=status_counts,
        )
        return all_records, report

    def _run_chunk(self, pairs: list[tuple[LeanTask, TacticAction]], *, batch_index: int) -> list[AuditRecord]:
        lean_src, blocks = _render_bulk_file(pairs, trace_state=self.config.trace_state)
        with tempfile.TemporaryDirectory(prefix="lean_rgc_bulk_") as td:
            td_path = Path(td)
            lean_file = td_path / f"rgc_bulk_{batch_index:04d}.lean"
            lean_file.write_text(lean_src, encoding="utf-8")
            cmd = shlex.split(self.config.lean_cmd) + [str(lean_file)]
            t0 = time.time()
            timed_out = False
            try:
                proc = subprocess.run(cmd, cwd=self.config.workdir or os.getcwd(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=self.config.timeout_s)
                stdout, stderr = proc.stdout or "", proc.stderr or ""
                returncode = int(proc.returncode)
            except subprocess.TimeoutExpired as e:
                timed_out = True
                stdout = e.stdout if isinstance(e.stdout, str) else ""
                stderr = e.stderr if isinstance(e.stderr, str) else ""
                returncode = -1
            elapsed = (time.time() - t0) * 1000.0
            combined = stdout + "\n" + stderr
            line_errors = _errors_by_line(combined)
            per_block_msgs, global_msgs = _attribute_lines(blocks, line_errors)
            if not global_msgs and not line_errors and returncode != 0:
                # Legacy env-failure detection: nonzero exit without any
                # parseable location fails the whole chunk (e.g. crash).
                global_msgs = _global_messages([], {}, combined, returncode)
            keep_path = None
            if self.config.keep_files:
                out_dir = Path(self.config.workdir or os.getcwd()) / ".lean_rgc_bulk_files"
                out_dir.mkdir(parents=True, exist_ok=True)
                keep_path = out_dir / lean_file.name
                keep_path.write_text(lean_src, encoding="utf-8")
            records: list[AuditRecord] = []
            for bi, block in enumerate(blocks):
                state = ProofState.from_task(block.task)
                msgs = global_msgs + per_block_msgs[bi]
                if timed_out:
                    status = "timeout"
                    if not msgs:
                        msgs = ["bulk Lean process timed out"]
                elif msgs:
                    status = _classify_block_failure("\n".join(msgs))
                else:
                    status = "success"
                after_state = ProofState(state_id=stable_hash({"closed": state.state_id, "bulk": True}), task_id=block.task.task_id, goals_text="", target="", raw_messages=[]) if status == "success" else ProofState(state_id=stable_hash({"after": state.state_id, "msgs": msgs[:5]}), task_id=block.task.task_id, goals_text="\n".join(msgs[-30:]), target=block.task.statement, raw_messages=msgs)
                records.append(AuditRecord(
                    task_id=block.task.task_id,
                    state_id=state.state_id,
                    action_id=block.action.action_id,
                    status=status,  # type: ignore[arg-type]
                    elapsed_ms=elapsed / max(1, len(blocks)),
                    stdout="" if status == "success" else "\n".join(msgs[-80:]),
                    stderr="",
                    messages=msgs[-80:],
                    after_state=after_state,
                    audit_flags={
                        "bulk_file": True,
                        "lean_returncode": returncode,
                        "global_error": bool(global_msgs),
                        "timeout": status == "timeout",
                        "partial_success": status == "partial",
                        # Error lines in messages are absolute within the bulk
                        # file; these offsets are what makes the verified-prefix
                        # length of a failed script recoverable from the row.
                        "block_start_line": block.start_line,
                        "block_end_line": block.end_line,
                    },
                    lean_file=str(keep_path or lean_file),
                ))
            return records


def bulk_audit_to_files(
    tasks: list[LeanTask],
    actions_by_task: dict[str, list[TacticAction]],
    out_dir: str | Path,
    config: BulkAuditConfig,
    *,
    run_id: str | None = None,
    parent_ids: list[str] | None = None,
) -> dict[str, Any]:
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    pairs: list[tuple[LeanTask, TacticAction]] = []
    for task in tasks:
        for action in actions_by_task.get(task.task_id, []):
            pairs.append((task, action))
    auditor = LeanBulkAuditor(config)
    audits, report = auditor.run_pairs(pairs)
    extractor = ProofDefectExtractor()
    responses: list[dict[str, Any]] = []
    defects_by_state: dict[str, dict[str, Any]] = {}
    for rec in audits:
        # Find corresponding task/action.
        task = next(t for t, a in pairs if t.task_id == rec.task_id and a.action_id == rec.action_id)
        action = next(a for t, a in pairs if t.task_id == rec.task_id and a.action_id == rec.action_id)
        state = ProofState.from_task(task)
        before = extractor.extract(state)
        after = extractor.extract(rec.after_state or state, rec)
        resp, flat, keys = extractor.response(before, after)
        rec.defect_before = before.to_dict(); rec.defect_after = after.to_dict(); rec.response = resp
        rec.carrier_delta = {k: before.carrier.get(k, 0.0)-after.carrier.get(k, 0.0) for k in sorted(set(before.carrier)|set(after.carrier))}
        defects_by_state[state.state_id] = {"state_id": state.state_id, "task_id": task.task_id, "target": task.statement, **before.to_dict()}
        responses.append({
            "state_id": state.state_id,
            "task_id": task.task_id,
            "action_id": action.action_id,
            "target": task.statement,
            "action": action.to_dict(),
            "response": resp,
            "response_flat": flat,
            "response_keys": keys,
            "defect_before": before.to_dict(),
            "defect_after": after.to_dict(),
            "audit_status": rec.status,
            "carrier_delta": rec.carrier_delta,
        })
    write_records(out / "micro_audit.jsonl", [r.to_dict() for r in audits], schema_version=SCHEMA_AUDIT_ROW, run_id=run_id, parent_ids=parent_ids)
    write_records(out / "responses.jsonl", responses, schema_version=SCHEMA_RESPONSE_ROW, run_id=run_id, parent_ids=parent_ids)
    write_records(out / "defects.jsonl", list(defects_by_state.values()), schema_version=SCHEMA_DEFECT_ROW, run_id=run_id, parent_ids=parent_ids)
    bulk_summary = report.to_dict()
    response_summary = summarize_response_rows(responses).to_dict()
    summary = {**bulk_summary, **response_summary, "backend": "bulk"}
    (out / "bulk_summary.json").write_text(json.dumps(bulk_summary, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


__all__ = [
    "BulkAuditConfig",
    "BulkAuditReport",
    "BulkBlock",
    "LeanBulkAuditor",
    "_block_messages",
    "_classify_block_failure",
    "_errors_by_line",
    "_render_bulk_file",
    "_sanitize_ident",
    "bulk_audit_to_files",
]
