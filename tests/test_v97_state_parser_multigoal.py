from __future__ import annotations

from lean_rgc.lean.state_parser import LeanMessageParser


def test_case_labeled_goals_split_with_names():
    text = (
        "example.lean:3:0: error: unsolved goals\n"
        "case zero\n"
        "⊢ 0 + 0 = 0\n"
        "case succ\n"
        "n : Nat\n"
        "ih : n + 0 = n\n"
        "⊢ n + 1 + 0 = n + 1\n"
    )
    goals = LeanMessageParser().extract_goals(text)
    assert [g.case_name for g in goals] == ["zero", "succ"]
    assert goals[0].target == "0 + 0 = 0"
    assert goals[1].hypotheses == ["n : Nat", "ih : n + 0 = n"]
    assert goals[1].target == "n + 1 + 0 = n + 1"


def test_anonymous_goals_split_when_blocks_start_with_turnstile():
    text = "unsolved goals\n⊢ 1 + 1 = 2\n\n⊢ 2 + 2 = 4\n"
    goals = LeanMessageParser().extract_goals(text)
    assert [g.target for g in goals] == ["1 + 1 = 2", "2 + 2 = 4"]
    assert all(g.case_name is None for g in goals)


def test_anonymous_goals_split_when_blocks_start_with_hypotheses():
    text = (
        "unsolved goals\n"
        "n : Nat\n"
        "⊢ n + 0 = n\n"
        "\n"
        "m : Nat\n"
        "⊢ m * 1 = m\n"
    )
    goals = LeanMessageParser().extract_goals(text)
    assert len(goals) == 2
    assert goals[0].hypotheses == ["n : Nat"]
    assert goals[0].target == "n + 0 = n"
    assert goals[1].hypotheses == ["m : Nat"]
    assert goals[1].target == "m * 1 = m"


def test_blank_separated_chunk_without_turnstile_merges_into_previous_goal():
    text = "unsolved goals\n⊢ f x =\n    g y\n\ncontinuation without turnstile\n"
    goals = LeanMessageParser().extract_goals(text)
    assert len(goals) == 1
    assert goals[0].target == "f x ="
    assert "continuation without turnstile" in goals[0].raw


def test_parse_marks_partial_success_and_counts_goals():
    text = (
        "unsolved goals\n"
        "n : Nat\n"
        "⊢ n + 0 = n\n"
        "\n"
        "m : Nat\n"
        "⊢ m * 1 = m\n"
    )
    state = LeanMessageParser().parse(text)
    assert state.partial_success
    assert len(state.goals) == 2
