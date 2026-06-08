from pathlib import Path

from lean_rgc.cli import main as cli_main
from lean_rgc.minif2f_adapter import build_minif2f_tasks, parse_minif2f_lean_file
from lean_rgc.schemas import read_jsonl


def _mini_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "miniF2F"
    src = repo / "MiniF2F"
    src.mkdir(parents=True)
    (repo / "lean-toolchain").write_text("leanprover/lean4:v4.27.0\n", encoding="utf-8")
    (src / "ProblemImports.lean").write_text("import Mathlib\n", encoding="utf-8")
    valid = """import MiniF2F.ProblemImports

/-- A tiny equality. -/
theorem tiny_eq (n : Nat) : n = n := by
  sorry

/-- A dependent implication. -/
theorem tiny_dep
    (x y : Nat) (h₀ : x = y) :
    y = x := by
  sorry
"""
    test = """import MiniF2F.ProblemImports

theorem test_true : True := by
  trivial
"""
    (src / "Valid.lean").write_text(valid, encoding="utf-8")
    (src / "Test.lean").write_text(test, encoding="utf-8")
    return repo


def test_parse_minif2f_lean_file_to_term_targets(tmp_path: Path):
    repo = _mini_repo(tmp_path)
    rows = parse_minif2f_lean_file(repo / "MiniF2F" / "Valid.lean", split="valid")
    assert [r.theorem_name for r in rows] == ["tiny_eq", "tiny_dep"]
    assert rows[0].statement == "∀ (n : Nat), n = n"
    assert rows[1].statement == "∀ (x y : Nat) (h₀ : x = y), y = x"
    assert "A tiny equality" in rows[0].informal_doc


def test_build_minif2f_tasks_and_cli(tmp_path: Path):
    repo = _mini_repo(tmp_path)
    out = tmp_path / "tasks.jsonl"
    report = build_minif2f_tasks(
        repo,
        out,
        split="valid",
        limit=1,
        imports=["MiniF2F.ProblemImports"],
        summary_out=tmp_path / "report.json",
    )
    assert report["n_total_parsed"] == 2
    assert report["n_tasks"] == 1
    rows = read_jsonl(out)
    assert rows[0]["task_id"] == "minif2f_valid_tiny_eq"
    assert rows[0]["statement"] == "∀ (n : Nat), n = n"
    assert rows[0]["imports"] == ["MiniF2F.ProblemImports"]
    assert rows[0]["metadata"]["task_statement_mode"] == "kernel_rpc_term_type"

    cli_out = tmp_path / "tasks_cli.jsonl"
    assert (
        cli_main(
            [
                "minif2f-tasks",
                "--repo",
                str(repo),
                "--split",
                "all",
                "--name-regex",
                "true|dep",
                "--out",
                str(cli_out),
            ]
        )
        == 0
    )
    cli_rows = read_jsonl(cli_out)
    assert {r["task_id"] for r in cli_rows} == {"minif2f_valid_tiny_dep", "minif2f_test_test_true"}
