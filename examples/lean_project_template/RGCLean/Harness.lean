import Std

/-!
Minimal Lean-RGC harness helpers.
This file is intentionally tiny: Python file-mode audits can import it and call
trace_state around candidate tactics. A richer server integration can replace
this later.
-/

open Lean Elab Tactic Meta

elab "trace_state" : tactic => do
  let goals ← getGoals
  logInfo m!"RGC_STATE num_goals={goals.length}"
  for g in goals do
    let decl ← g.getDecl
    let tgt ← instantiateMVars decl.type
    logInfo m!"RGC_GOAL {g.name}: {tgt}"
