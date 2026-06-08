from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any

from .schemas import ProofState, stable_hash


@dataclass
class ParsedGoal:
    raw: str
    hypotheses: list[str] = field(default_factory=list)
    target: str = ""
    case_name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"raw": self.raw, "hypotheses": self.hypotheses, "target": self.target, "case_name": self.case_name}


@dataclass
class ParsedLeanState:
    goals: list[ParsedGoal]
    messages: list[str]
    partial_success: bool = False

    def to_proof_state(self, task_id: str, fallback_target: str = "") -> ProofState:
        goals_text = "\n\n".join(g.raw for g in self.goals)
        target = self.goals[0].target if self.goals and self.goals[0].target else fallback_target
        return ProofState(
            state_id=stable_hash({"task_id": task_id, "goals": goals_text[:4000], "messages": self.messages[-10:]}),
            task_id=task_id,
            goals_text=goals_text,
            target=target,
            raw_messages=self.messages[-80:],
            features={"parsed_num_goals": float(len(self.goals)), "partial_success": float(self.partial_success)},
        )


class LeanMessageParser:
    """Best-effort parser for Lean 4 textual messages.

    This is a chart, not a canonical proof-state representation. It is useful
    for file-mode audits before a persistent server exposes structured goals.
    """

    def parse(self, text: str) -> ParsedLeanState:
        messages = [ln.rstrip() for ln in (text or "").splitlines() if ln.strip()]
        low = text.lower()
        partial = "unsolved goals" in low or "unsolved goal" in low
        goals = self.extract_goals(text)
        return ParsedLeanState(goals=goals, messages=messages, partial_success=partial)

    def extract_goals(self, text: str) -> list[ParsedGoal]:
        if not text:
            return []
        # Lean often prints `unsolved goals` then one or more goal blocks.
        m = re.search(r"unsolved goals?(?P<body>.*)", text, flags=re.IGNORECASE | re.DOTALL)
        body = m.group("body") if m else text
        # Drop leading file location prefixes where possible.
        body = re.sub(r"^.*?:\d+:\d+:\s*error:\s*", "", body, flags=re.MULTILINE)
        # Split on `case foo` but keep case labels.
        parts: list[tuple[str | None, str]] = []
        case_matches = list(re.finditer(r"(?:^|\n)case\s+([^\n]+)\n", body))
        if case_matches:
            for i, cm in enumerate(case_matches):
                start = cm.end()
                end = case_matches[i + 1].start() if i + 1 < len(case_matches) else len(body)
                parts.append((cm.group(1).strip(), body[start:end].strip()))
        else:
            # Split by repeated turnstile blocks heuristically.
            chunks = re.split(r"\n\s*\n(?=.*⊢)", body.strip())
            parts = [(None, c.strip()) for c in chunks if "⊢" in c or c.strip()]
        goals: list[ParsedGoal] = []
        for case_name, raw in parts:
            if not raw:
                continue
            hyps: list[str] = []
            target = ""
            if "⊢" in raw:
                before, after = raw.split("⊢", 1)
                target = after.strip().splitlines()[0].strip() if after.strip() else ""
                for ln in before.splitlines():
                    if re.match(r"\s*[A-Za-z_][A-Za-z0-9_']*\s*:", ln):
                        hyps.append(ln.strip())
            goals.append(ParsedGoal(raw=raw, hypotheses=hyps, target=target, case_name=case_name))
        return goals

# Compatibility aliases for earlier scaffold imports.
ParsedProofState = ParsedLeanState

def parse_proof_state(text: str, *, task_id: str = "parsed", fallback_target: str = "") -> ProofState:
    return LeanMessageParser().parse(text).to_proof_state(task_id, fallback_target=fallback_target)
