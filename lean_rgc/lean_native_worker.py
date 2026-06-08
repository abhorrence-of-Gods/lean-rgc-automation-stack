from __future__ import annotations

"""Launcher and source bundle for the Lean-native JSONL worker.

This module is the Python-side packaging shim for v29.  It writes an in-tree
Lean worker source file to a temporary location (or a requested path) and runs
it through `lake env lean --run`.  The worker speaks the same JSONL protocol as
`persistent_lean_worker.py`.

The bundled Lean program is intentionally conservative: it is a native Lean
process that maintains a state registry and returns kernel-shaped structured
state payloads.  The current in-tree Lean source is a protocol MVP; richer tactic
elaboration / kernel goal extraction can replace the placeholder extraction
without changing the Python adapter contract.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import argparse
import os
import shlex
import subprocess
import sys
import tempfile


LEAN_NATIVE_WORKER_SOURCE = r'''
import Lean
open Lean

/-!
Lean-RGC native JSONL worker MVP.

This is intentionally small and dependency-free.  It keeps a state registry in a
native Lean process and returns kernel-shaped JSON payloads compatible with the
Python v28 structured-state normalizer.  It is not yet a full tactic-state RPC:
`apply_tactic` records a child state and returns a chart-like partial audit.  A
future Lean elaborator integration can replace `applyTacticNative` while keeping
the JSONL protocol stable.
-/

namespace LeanRGCNativeWorker

structure State where
  stateId : String
  taskId : String
  statement : String
  prefix : String
  target : String
  goalsText : String
  parentStateId : Option String := none
  depth : Nat := 0
  closed : Bool := false
  deriving Inhabited

abbrev StateMap := Std.HashMap String State

def jsonObj? (j : Json) : Option (Array (String × Json)) :=
  match j with
  | Json.obj xs => some xs
  | _ => none

def get? (j : Json) (k : String) : Option Json := do
  let xs ← jsonObj? j
  xs.findSome? (fun kv => if kv.fst == k then some kv.snd else none)

def getStrD (j : Json) (k : String) (d : String := "") : String :=
  match get? j k with
  | some (Json.str s) => s
  | some v => Json.compress v
  | none => d

def getBoolD (j : Json) (k : String) (d : Bool := false) : Bool :=
  match get? j k with
  | some (Json.bool b) => b
  | _ => d

def getObjD (j : Json) (k : String) : Json :=
  match get? j k with
  | some v => v
  | none => Json.mkObj []

def arr (xs : List Json) : Json := Json.arr xs.toArray

def strArr (xs : List String) : Json := arr (xs.map Json.str)

def hashish (s : String) : String :=
  -- A small deterministic chart id, not cryptographic.
  let n := s.foldl (fun h c => (h * 131 + c.toNat) % 1000000007) 17
  toString n

def targetHead (target : String) : String :=
  if target.contains '=' then "eq"
  else if target.contains "∀" then "forall"
  else if target.contains "->" || target.contains "→" then "imp"
  else if target.contains "∧" then "and"
  else if target.contains "≤" || target.contains "<" then "order"
  else "unknown"

def domainTags (target : String) : List String :=
  let mut out := []
  if target.contains "Nat" then out := "Nat" :: out
  if target.contains "+" || target.contains "*" || target.contains "≤" then out := "Arith" :: out
  out.reverse

def carrierAtoms (target : String) : List String :=
  let mut out := []
  if target.contains '=' then out := "eq_reflexive_goal" :: out
  if target.contains "∀" then out := "unintroduced_forall" :: out
  if target.contains "∧" then out := "unsplit_and_target" :: out
  if target.contains "Nat" || target.contains "+" || target.contains "*" then out := "nat_arith_goal" :: out
  out.reverse

def mkKernelState (taskId stateId target : String) (prefix : String := "") : Json :=
  let head := targetHead target
  let goal := Json.mkObj [
    ("mvar_id", Json.str ("?m." ++ hashish (taskId ++ stateId))),
    ("target", Json.mkObj [
      ("text", Json.str target),
      ("kind", Json.str "text_chart_native_v29"),
      ("head", Json.str head),
      ("kernel_hash", Json.str (hashish target))
    ]),
    ("local_deps", arr [])
  ]
  Json.mkObj [
    ("schema_version", Json.str "lean-rgc-kernel-state-v28.0"),
    ("extraction_backend", Json.str "lean_native_worker_v29_protocol_mvp"),
    ("canonical_status", Json.str "kernel_backed_structured_state_chart_not_canonical"),
    ("task_id", Json.str taskId),
    ("state_id", Json.str stateId),
    ("prefix", Json.str prefix),
    ("goals", arr [goal]),
    ("local_context", Json.mkObj [("nodes", arr []), ("edges", arr [])]),
    ("metavars", arr [Json.mkObj [("mvar_id", Json.str ("?m." ++ hashish (taskId ++ stateId))), ("type_text", Json.str target)]]),
    ("typeclasses", arr []),
    ("domain_tags", strArr (domainTags target)),
    ("carrier_atoms", strArr (carrierAtoms target)),
    ("kernel_state_hash", Json.str (hashish (taskId ++ stateId ++ target)))
  ]

def stateToJson (s : State) : Json :=
  Json.mkObj [
    ("state_id", Json.str s.stateId),
    ("task_id", Json.str s.taskId),
    ("prefix", Json.str s.prefix),
    ("target", Json.str s.target),
    ("goals_text", Json.str s.goalsText),
    ("parent_state_id", match s.parentStateId with | some p => Json.str p | none => Json.null),
    ("depth", Json.str (toString s.depth)),
    ("closed", Json.bool s.closed),
    ("canonical_status", Json.str "lean_native_worker_state_chart_not_canonical")
  ]

def auditJson (taskId stateId actionId status : String) (afterState : State) : Json :=
  Json.mkObj [
    ("task_id", Json.str taskId),
    ("state_id", Json.str stateId),
    ("action_id", Json.str actionId),
    ("status", Json.str status),
    ("messages", arr []),
    ("after_state", Json.mkObj [
      ("state_id", Json.str afterState.stateId),
      ("task_id", Json.str afterState.taskId),
      ("goals_text", Json.str afterState.goalsText),
      ("local_context", Json.str ""),
      ("target", Json.str afterState.target),
      ("raw_messages", arr []),
      ("features", Json.mkObj [])
    ]),
    ("response", Json.mkObj []),
    ("carrier_delta", Json.mkObj []),
    ("audit_flags", Json.mkObj [
      ("lean_native_worker", Json.bool true),
      ("kernel_native_partial", Json.bool true),
      ("canonical_status", Json.str "native_worker_audit_chart_not_canonical")
    ])
  ]

def reply (id : String) (payload : Json) : IO Unit := do
  let withId := match payload with
    | Json.obj xs => Json.obj (xs.push ("id", Json.str id))
    | _ => Json.mkObj [("id", Json.str id), ("payload", payload)]
  IO.println (Json.compress withId)
  (← IO.getStdout).flush

def initState (req : Json) (states : StateMap) : StateMap × Json :=
  let task := getObjD req "task"
  let taskId := getStrD task "task_id" (getStrD req "task_id" "task")
  let statement := getStrD task "statement" (getStrD req "target" "True")
  let prefix := getStrD task "prefix" ""
  let sid := getStrD req "state_id" ("s_" ++ hashish (taskId ++ statement ++ prefix))
  let st : State := {
    stateId := sid,
    taskId := taskId,
    statement := statement,
    prefix := prefix,
    target := statement,
    goalsText := "⊢ " ++ statement,
    depth := 0
  }
  (states.insert sid st, Json.mkObj [
    ("ok", Json.bool true),
    ("state", stateToJson st),
    ("kernel_state", mkKernelState taskId sid statement prefix),
    ("backend", Json.str "lean_native_worker_v29_protocol_mvp")
  ])

def applyTacticNative (req : Json) (states : StateMap) : StateMap × Json :=
  let action := getObjD req "action"
  let task := getObjD req "task"
  let actionId := getStrD action "action_id" (getStrD action "id" "action")
  let tactic := getStrD action "tactic" ""
  let stateId := getStrD req "state_id" ""
  let parent := states.find? stateId
  let base := match parent with
    | some s => s
    | none =>
      let taskId := getStrD task "task_id" (getStrD req "task_id" "task")
      let statement := getStrD task "statement" "True"
      { stateId := stateId, taskId := taskId, statement := statement, prefix := "", target := statement, goalsText := "⊢ " ++ statement }
  let newPrefix := if base.prefix.isEmpty then tactic else base.prefix ++ "\n" ++ tactic
  let closed := tactic == "rfl" || tactic == "trivial" || tactic == "simp" || tactic == "assumption"
  let newTarget := if closed then "True" else base.target
  let newStateId := "s_" ++ hashish (base.stateId ++ actionId ++ tactic ++ toString base.depth)
  let child : State := {
    stateId := newStateId,
    taskId := base.taskId,
    statement := base.statement,
    prefix := newPrefix,
    target := newTarget,
    goalsText := if closed then "no goals" else base.goalsText,
    parentStateId := some base.stateId,
    depth := base.depth + 1,
    closed := closed
  }
  let status := if closed then "success" else "partial"
  let kernel := mkKernelState child.taskId child.stateId child.target child.prefix
  (states.insert child.stateId child, Json.mkObj [
    ("ok", Json.bool true),
    ("audit", auditJson base.taskId base.stateId actionId status child),
    ("state", stateToJson child),
    ("kernel_state", kernel),
    ("backend", Json.str "lean_native_worker_v29_protocol_mvp"),
    ("limitations", strArr ["protocol_mvp", "not_full_elaborator_tactic_state"])
  ])

partial def loop (states : StateMap) : IO Unit := do
  let stdin ← IO.getStdin
  let line ← stdin.getLine
  if line.isEmpty then
    return ()
  match Json.parse line with
  | Except.error e =>
      reply "" (Json.mkObj [("ok", Json.bool false), ("error", Json.str e)])
      loop states
  | Except.ok req =>
      let id := getStrD req "id" ""
      let cmd := getStrD req "cmd" ""
      match cmd with
      | "load_project" =>
          reply id (Json.mkObj [("ok", Json.bool true), ("backend", Json.str "lean_native_worker_v29_protocol_mvp"), ("loaded", Json.bool true)])
          loop states
      | "init_state" =>
          let (states', out) := initState req states
          reply id out
          loop states'
      | "register_task" =>
          let (states', out) := initState req states
          reply id out
          loop states'
      | "apply_tactic" =>
          let (states', out) := applyTacticNative req states
          reply id out
          loop states'
      | "get_state" =>
          let sid := getStrD req "state_id" ""
          match states.find? sid with
          | some s => reply id (Json.mkObj [("ok", Json.bool true), ("state", stateToJson s)])
          | none => reply id (Json.mkObj [("ok", Json.bool false), ("error", Json.str ("unknown state_id: " ++ sid))])
          loop states
      | "branch_state" =>
          let sid := getStrD req "state_id" ""
          match states.find? sid with
          | some s =>
              let bid := getStrD req "new_state_id" ("branch_" ++ hashish (sid ++ toString s.depth))
              let b := {s with stateId := bid, parentStateId := some sid}
              reply id (Json.mkObj [("ok", Json.bool true), ("state", stateToJson b)])
              loop (states.insert bid b)
          | none =>
              reply id (Json.mkObj [("ok", Json.bool false), ("error", Json.str ("unknown state_id: " ++ sid))])
              loop states
      | "rollback_state" =>
          let sid := getStrD req "state_id" ""
          match states.find? sid with
          | some s =>
              match s.parentStateId with
              | some p =>
                  match states.find? p with
                  | some ps => reply id (Json.mkObj [("ok", Json.bool true), ("state", stateToJson ps)])
                  | none => reply id (Json.mkObj [("ok", Json.bool true), ("state", stateToJson s)])
              | none => reply id (Json.mkObj [("ok", Json.bool true), ("state", stateToJson s)])
          | none => reply id (Json.mkObj [("ok", Json.bool false), ("error", Json.str ("unknown state_id: " ++ sid))])
          loop states
      | "kernel_state" =>
          let sid := getStrD req "state_id" ""
          match states.find? sid with
          | some s => reply id (Json.mkObj [("ok", Json.bool true), ("kernel_state", mkKernelState s.taskId s.stateId s.target s.prefix)])
          | none => reply id (Json.mkObj [("ok", Json.bool false), ("error", Json.str ("unknown state_id: " ++ sid))])
          loop states
      | "structured_state" =>
          let sid := getStrD req "state_id" ""
          match states.find? sid with
          | some s => reply id (Json.mkObj [("ok", Json.bool true), ("kernel_state", mkKernelState s.taskId s.stateId s.target s.prefix)])
          | none => reply id (Json.mkObj [("ok", Json.bool false), ("error", Json.str ("unknown state_id: " ++ sid))])
          loop states
      | "status" =>
          reply id (Json.mkObj [("ok", Json.bool true), ("backend", Json.str "lean_native_worker_v29_protocol_mvp"), ("n_states", Json.str (toString states.size))])
          loop states
      | "shutdown" =>
          reply id (Json.mkObj [("ok", Json.bool true), ("shutdown", Json.bool true)])
          return ()
      | _ =>
          reply id (Json.mkObj [("ok", Json.bool false), ("error", Json.str ("unknown cmd: " ++ cmd))])
          loop states

end LeanRGCNativeWorker

def main : IO Unit := do
  LeanRGCNativeWorker.loop {}
'''


@dataclass
class LeanNativeWorkerConfig:
    lean_cmd: str = "lake env lean"
    workdir: str | None = None
    source_path: str | None = None
    keep_source: bool = False


def write_native_worker_source(path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(LEAN_NATIVE_WORKER_SOURCE, encoding="utf-8")
    return path


def build_native_worker_command(config: LeanNativeWorkerConfig, *, source_path: str | Path | None = None) -> list[str]:
    src = Path(source_path or config.source_path or "LeanRGCNativeWorker.lean")
    lean_parts = shlex.split(config.lean_cmd)
    return lean_parts + ["--run", str(src)]


def run_native_worker(config: LeanNativeWorkerConfig) -> int:
    if config.source_path:
        src = write_native_worker_source(config.source_path)
        cmd = build_native_worker_command(config, source_path=src)
        return subprocess.call(cmd, cwd=config.workdir or os.getcwd(), stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)
    with tempfile.TemporaryDirectory(prefix="lean_rgc_native_worker_") as td:
        src = write_native_worker_source(Path(td) / "LeanRGCNativeWorker.lean")
        cmd = build_native_worker_command(config, source_path=src)
        rc = subprocess.call(cmd, cwd=config.workdir or os.getcwd(), stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)
        if config.keep_source:
            out = Path(os.getcwd()) / "LeanRGCNativeWorker.lean"
            out.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
            print(f"[lean-rgc-native-worker] wrote source to {out}", file=sys.stderr)
        return rc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Run or emit the Lean-RGC native Lean JSONL worker source.")
    ap.add_argument("--lean-cmd", default="lake env lean")
    ap.add_argument("--workdir")
    ap.add_argument("--source-path", help="Write/run the Lean worker from this path instead of a temp file.")
    ap.add_argument("--emit-source", help="Only write the Lean worker source to this path and exit.")
    ap.add_argument("--print-source", action="store_true")
    ap.add_argument("--print-command", action="store_true")
    ap.add_argument("--keep-source", action="store_true")
    args = ap.parse_args(argv)
    cfg = LeanNativeWorkerConfig(lean_cmd=args.lean_cmd, workdir=args.workdir, source_path=args.source_path, keep_source=args.keep_source)
    if args.print_source:
        print(LEAN_NATIVE_WORKER_SOURCE)
        return 0
    if args.emit_source:
        p = write_native_worker_source(args.emit_source)
        print(str(p))
        return 0
    if args.print_command:
        src = Path(args.source_path or "LeanRGCNativeWorker.lean")
        print(shlex.join(build_native_worker_command(cfg, source_path=src)))
        return 0
    return run_native_worker(cfg)


if __name__ == "__main__":
    raise SystemExit(main())
