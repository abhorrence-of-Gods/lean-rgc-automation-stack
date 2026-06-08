from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .schemas import LeanTask, write_jsonl, stable_hash


@dataclass
class CoreBenchSpec:
    n_nat: int = 20
    n_prop: int = 20
    n_bool: int = 10
    n_eq: int = 10
    imports: list[str] = field(default_factory=list)
    prefix: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _task(task_id: str, statement: str, *, imports: list[str], tags: list[str]) -> LeanTask:
    return LeanTask(task_id=task_id, statement=statement, imports=list(imports), domain_tags=tags)


def generate_core_tasks(spec: CoreBenchSpec) -> list[LeanTask]:
    """Generate a tiny but expandable Lean-core benchmark.

    The statements intentionally avoid Mathlib.  They are meant for instrumentation,
    not as a public theorem-proving benchmark.  The generated set stresses exposure
    carriers (forall/imp/and), equality carriers, and simple Nat/Bool simplification.
    """
    tasks: list[LeanTask] = []
    imports = list(spec.imports)

    # Equality / forall exposure.
    for i in range(spec.n_eq):
        typ = "Nat" if i % 2 == 0 else "Bool"
        st = f"∀ x : {typ}, x = x"
        tasks.append(_task(f"core_eq_refl_{i:04d}", st, imports=imports, tags=[typ.lower(), "eq", "forall"]))

    # Nat simp/reflexive-ish goals.  These are mostly solvable by intros+simp.
    nat_templates = [
        "∀ n : Nat, n + 0 = n",
        "∀ n : Nat, 0 + n = n",
        "∀ n : Nat, n * 1 = n",
        "∀ n : Nat, 1 * n = n",
        "∀ n : Nat, n - 0 = n",
        "∀ n : Nat, n ≤ n",
        "∀ n : Nat, Nat.succ n = n + 1",
    ]
    for i in range(spec.n_nat):
        st = nat_templates[i % len(nat_templates)]
        tasks.append(_task(f"core_nat_{i:04d}_{stable_hash(st,6)}", st, imports=imports, tags=["nat", "arith", "forall"]))

    # Prop implication/conjunction carriers.  Solvable by intros/constructor/simp_all.
    prop_templates = [
        "∀ p : Prop, p → p",
        "∀ p q : Prop, p ∧ q → p",
        "∀ p q : Prop, p ∧ q → q",
        "∀ p q : Prop, p ∧ q → q ∧ p",
        "∀ p q r : Prop, p ∧ q ∧ r → r ∧ p",
        "∀ p q : Prop, p → q → p ∧ q",
        "∀ p q : Prop, p ∧ q → p ∧ q",
    ]
    for i in range(spec.n_prop):
        st = prop_templates[i % len(prop_templates)]
        tasks.append(_task(f"core_prop_{i:04d}_{stable_hash(st,6)}", st, imports=imports, tags=["prop", "and", "imp", "forall"]))

    # Bool goals, mostly intro+simp/rfl.
    bool_templates = [
        "∀ b : Bool, b = b",
        "∀ b : Bool, b && true = b",
        "∀ b : Bool, true && b = b",
        "∀ b : Bool, b || false = b",
        "∀ b : Bool, false || b = b",
    ]
    for i in range(spec.n_bool):
        st = bool_templates[i % len(bool_templates)]
        tasks.append(_task(f"core_bool_{i:04d}_{stable_hash(st,6)}", st, imports=imports, tags=["bool", "simp", "forall"]))

    # Stable unique ordering / de-dup by statement+task prefix.
    seen: set[str] = set(); out: list[LeanTask] = []
    for t in tasks:
        key = t.task_id
        if key not in seen:
            seen.add(key); out.append(t)
    return out


def write_corebench(out: str | Path, *, n_nat: int = 20, n_prop: int = 20, n_bool: int = 10, n_eq: int = 10, imports: list[str] | None = None) -> dict[str, Any]:
    spec = CoreBenchSpec(n_nat=n_nat, n_prop=n_prop, n_bool=n_bool, n_eq=n_eq, imports=imports or [])
    tasks = generate_core_tasks(spec)
    write_jsonl(out, [t.to_dict() for t in tasks])
    return {"out": str(out), "n_tasks": len(tasks), "spec": spec.to_dict()}


__all__ = ["CoreBenchSpec", "generate_core_tasks", "write_corebench"]
