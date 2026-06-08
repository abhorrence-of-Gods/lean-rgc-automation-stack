from __future__ import annotations

from pathlib import Path
import re


def _sanitize_lean_ident(name: str) -> str:
    """Return a conservative Lean identifier usable as package/lib name."""
    parts = re.split(r"[^A-Za-z0-9_]+", name.strip())
    s = "".join(part[:1].upper() + part[1:] for part in parts if part)
    if not s:
        s = "LeanRGCPlayground"
    if not (s[0].isalpha() or s[0] == "_"):
        s = "LeanRGC" + s
    return s


def write_lake_template(out: str | Path, *, name: str = "LeanRGCPlayground", mathlib: bool = True) -> Path:
    """Write a minimal, buildable Lean/Lake project.

    The v0.4 template deliberately creates both a root module `<Name>.lean`
    and `<Name>/Basic.lean`.  Earlier templates only created the submodule,
    which works in some Lake layouts but is brittle for `lake build` and for
    file-mode audit snippets that rely on project module discovery.
    """
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    name = _sanitize_lean_ident(name)
    (out / "lean-toolchain").write_text("leanprover/lean4:stable\n", encoding="utf-8")
    if mathlib:
        lakefile = f'''import Lake
open Lake DSL

package {name} where
  -- Lean-RGC Mathlib playground.

require mathlib from git
  "https://github.com/leanprover-community/mathlib4.git"

@[default_target]
lean_lib {name} where
  -- add library configuration options here
'''
        basic = "import Mathlib\n\nexample : 1 + 1 = 2 := by\n  norm_num\n"
    else:
        lakefile = f'''import Lake
open Lake DSL

package {name} where
  -- Lean-RGC core-Lean playground with no Mathlib dependency.

@[default_target]
lean_lib {name} where
  -- add library configuration options here
'''
        # Keep this Mathlib-free. Avoid tactics requiring Mathlib imports here.
        basic = "example : True := by\n  trivial\n\nexample (n : Nat) : n = n := by\n  rfl\n"
    (out / "lakefile.lean").write_text(lakefile, encoding="utf-8")
    src = out / name
    src.mkdir(exist_ok=True)
    (src / "Basic.lean").write_text(basic, encoding="utf-8")
    (out / f"{name}.lean").write_text(f"import {name}.Basic\n", encoding="utf-8")
    (out / "README.md").write_text(
        f"# {name}\n\nLean-RGC playground project. Run `lake update` then `lake build`.\n\n"
        f"Mathlib dependency: {'yes' if mathlib else 'no'}\n",
        encoding="utf-8",
    )
    return out
