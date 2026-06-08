from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import json
import re
import shutil
import subprocess

from .schemas import stable_hash, write_jsonl


DEFAULT_MINIF2F_LEAN4_URL = "https://github.com/google-deepmind/miniF2F.git"
SCHEMA_MINIF2F_TASKS = "lean-rgc-minif2f-tasks-v53.0"
SCHEMA_MINIF2F_FETCH = "lean-rgc-minif2f-fetch-v53.0"


@dataclass
class MiniF2FTheorem:
    split: str
    theorem_name: str
    binders: str
    target: str
    statement: str
    source_file: str
    source_line: int
    original_declaration: str
    informal_doc: str = ""


def _json_dump(obj: dict[str, Any], path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def _run_git(args: list[str], *, cwd: str | Path | None = None) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(cwd) if cwd else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "").strip())
    return proc.stdout.strip()


def fetch_minif2f(
    out_dir: str | Path,
    *,
    url: str = DEFAULT_MINIF2F_LEAN4_URL,
    ref: str | None = None,
    depth: int = 1,
    force: bool = False,
    summary_out: str | Path | None = None,
) -> dict[str, Any]:
    """Clone/update the Lean 4 miniF2F repository without vendoring it.

    The default repository is the Lean 4 fork used by recent Lean 4 benchmark
    runs.  The fetched directory remains outside tracked source unless the user
    explicitly adds it.
    """

    out_path = Path(out_dir)
    if out_path.exists() and force:
        shutil.rmtree(out_path)
    if not out_path.exists():
        out_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = ["clone", "--depth", str(depth), url, str(out_path)]
        if ref:
            cmd = ["clone", "--depth", str(depth), "--branch", ref, url, str(out_path)]
        _run_git(cmd)
    elif (out_path / ".git").exists():
        if ref:
            _run_git(["fetch", "--depth", str(depth), "origin", ref], cwd=out_path)
            _run_git(["checkout", ref], cwd=out_path)
        else:
            try:
                _run_git(["pull", "--ff-only"], cwd=out_path)
            except RuntimeError:
                # A shallow checkout may not have upstream tracking.  Keep the
                # existing checkout and report its commit.
                pass
    else:
        raise FileExistsError(f"destination exists but is not a git checkout: {out_path}")

    commit = _run_git(["rev-parse", "HEAD"], cwd=out_path)
    report = {
        "schema_version": SCHEMA_MINIF2F_FETCH,
        "url": url,
        "ref": ref,
        "out_dir": str(out_path),
        "commit": commit,
        "valid_file": str(out_path / "MiniF2F" / "Valid.lean"),
        "test_file": str(out_path / "MiniF2F" / "Test.lean"),
        "lean_toolchain": (out_path / "lean-toolchain").read_text(encoding="utf-8").strip()
        if (out_path / "lean-toolchain").exists()
        else None,
        "canonical_status": "external_benchmark_checkout_not_canonical",
    }
    if summary_out:
        _json_dump(report, summary_out)
    return report


def _split_file_for_name(repo: Path, split: str) -> Path:
    norm = split.lower()
    if norm == "valid":
        return repo / "MiniF2F" / "Valid.lean"
    if norm == "test":
        return repo / "MiniF2F" / "Test.lean"
    raise ValueError(f"unknown miniF2F split: {split}")


def _strip_proof_suffix(decl: str) -> str:
    m = re.search(r":=\s*by\b", decl)
    if not m:
        raise ValueError("theorem declaration does not contain ':= by'")
    return decl[: m.start()].strip()


def _find_top_level_colon(text: str) -> int:
    depth = 0
    pairs = {"(": ")", "[": "]", "{": "}", "⟨": "⟩"}
    closing = {v: k for k, v in pairs.items()}
    stack: list[str] = []
    in_string = False
    escaped = False
    for i, ch in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
            continue
        if ch in pairs:
            stack.append(ch)
            depth += 1
            continue
        if ch in closing and stack and stack[-1] == closing[ch]:
            stack.pop()
            depth = max(0, depth - 1)
            continue
        if ch == ":" and depth == 0:
            return i
    raise ValueError("could not find top-level theorem target colon")


def _normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _parse_declaration(split: str, source_file: Path, source_line: int, decl: str, doc: str) -> MiniF2FTheorem:
    pre = _strip_proof_suffix(decl)
    m = re.match(r"\s*theorem\s+([A-Za-z0-9_'.]+)\s*(.*)\Z", pre, re.S)
    if not m:
        raise ValueError("not a theorem declaration")
    name = m.group(1)
    signature = m.group(2).strip()
    colon = _find_top_level_colon(signature)
    binders = _normalize_ws(signature[:colon])
    target = _normalize_ws(signature[colon + 1 :])
    statement = target if not binders else f"∀ {binders}, {target}"
    return MiniF2FTheorem(
        split=split,
        theorem_name=name,
        binders=binders,
        target=target,
        statement=statement,
        source_file=str(source_file),
        source_line=source_line,
        original_declaration=decl.strip(),
        informal_doc=doc.strip(),
    )


def parse_minif2f_lean_file(path: str | Path, *, split: str) -> list[MiniF2FTheorem]:
    """Extract theorem statements from miniF2F Lean 4 aggregate files."""

    p = Path(path)
    lines = p.read_text(encoding="utf-8").splitlines()
    out: list[MiniF2FTheorem] = []
    pending_doc: list[str] = []
    collecting_doc = False
    current: list[str] = []
    current_line = 0

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not current:
            if stripped.startswith("/--"):
                collecting_doc = True
                pending_doc = [line]
                if "-/" in stripped:
                    collecting_doc = False
                continue
            if collecting_doc:
                pending_doc.append(line)
                if "-/" in stripped:
                    collecting_doc = False
                continue
            if re.match(r"^\s*theorem\s+[A-Za-z0-9_'.]+\b", line):
                current = [line]
                current_line = idx
                if re.search(r":=\s*by\b", line):
                    doc = "\n".join(pending_doc)
                    out.append(_parse_declaration(split, p, current_line, "\n".join(current), doc))
                    current = []
                    pending_doc = []
                continue
            if stripped and not stripped.startswith("--"):
                pending_doc = []
            continue

        current.append(line)
        if re.search(r":=\s*by\b", line):
            doc = "\n".join(pending_doc)
            out.append(_parse_declaration(split, p, current_line, "\n".join(current), doc))
            current = []
            pending_doc = []

    return out


def _domain_tags(thm: MiniF2FTheorem) -> list[str]:
    text = (thm.theorem_name + " " + thm.statement).lower()
    tags = ["minif2f", thm.split]
    for needle, tag in [
        ("nat", "nat"),
        ("int", "int"),
        ("real", "real"),
        ("complex", "complex"),
        ("finset", "finset"),
        ("polynomial", "polynomial"),
        ("log", "analysis"),
        ("sqrt", "analysis"),
        ("∧", "logic"),
        ("->", "logic"),
        ("→", "logic"),
        ("=", "eq"),
    ]:
        if needle in text and tag not in tags:
            tags.append(tag)
    prefix = thm.theorem_name.split("_", 1)[0]
    if prefix and prefix not in tags:
        tags.append(prefix)
    return tags


def _task_from_theorem(
    thm: MiniF2FTheorem,
    *,
    imports: list[str],
    max_heartbeats: int,
    repo: Path,
    commit: str | None,
) -> dict[str, Any]:
    task_id = f"minif2f_{thm.split}_{thm.theorem_name}"
    return {
        "schema_version": SCHEMA_MINIF2F_TASKS,
        "task_id": task_id,
        "statement": thm.statement,
        "imports": imports,
        "prefix": "",
        "domain_tags": _domain_tags(thm),
        "max_heartbeats": max_heartbeats,
        "metadata": {
            "benchmark": "miniF2F",
            "benchmark_split": thm.split,
            "theorem_name": thm.theorem_name,
            "source_file": thm.source_file,
            "source_line": thm.source_line,
            "source_repo": str(repo),
            "source_commit": commit,
            "binder_prefix": thm.binders,
            "target": thm.target,
            "informal_doc": thm.informal_doc,
            "original_declaration": thm.original_declaration,
            "task_statement_mode": "kernel_rpc_term_type",
            "canonical_status": "external_benchmark_task_chart_not_canonical",
        },
    }


def build_minif2f_tasks(
    repo: str | Path,
    out: str | Path,
    *,
    split: str = "valid",
    limit: int | None = None,
    offset: int = 0,
    imports: list[str] | None = None,
    max_heartbeats: int = 400000,
    summary_out: str | Path | None = None,
    name_regex: str | None = None,
) -> dict[str, Any]:
    repo_path = Path(repo)
    splits = ["valid", "test"] if split.lower() in {"all", "*"} else [split.lower()]
    all_theorems: list[MiniF2FTheorem] = []
    for sp in splits:
        file_path = _split_file_for_name(repo_path, sp)
        if not file_path.exists():
            raise FileNotFoundError(file_path)
        all_theorems.extend(parse_minif2f_lean_file(file_path, split=sp))
    if name_regex:
        rx = re.compile(name_regex)
        all_theorems = [t for t in all_theorems if rx.search(t.theorem_name)]
    selected = all_theorems[int(offset) :]
    if limit is not None:
        selected = selected[: int(limit)]
    commit = None
    if (repo_path / ".git").exists():
        try:
            commit = _run_git(["rev-parse", "HEAD"], cwd=repo_path)
        except Exception:
            commit = None
    imps = imports or ["MiniF2F.ProblemImports"]
    rows = [
        _task_from_theorem(
            thm,
            imports=imps,
            max_heartbeats=max_heartbeats,
            repo=repo_path,
            commit=commit,
        )
        for thm in selected
    ]
    write_jsonl(out, rows)
    report = {
        "schema_version": SCHEMA_MINIF2F_TASKS,
        "repo": str(repo_path),
        "split": split,
        "out": str(out),
        "n_total_parsed": len(all_theorems),
        "offset": int(offset),
        "limit": limit,
        "n_tasks": len(rows),
        "imports": imps,
        "max_heartbeats": max_heartbeats,
        "source_commit": commit,
        "task_statement_mode": "kernel_rpc_term_type",
        "canonical_status": "miniF2F_task_adapter_chart_not_canonical",
    }
    if summary_out:
        _json_dump(report, summary_out)
    return report


__all__ = [
    "DEFAULT_MINIF2F_LEAN4_URL",
    "fetch_minif2f",
    "parse_minif2f_lean_file",
    "build_minif2f_tasks",
]
