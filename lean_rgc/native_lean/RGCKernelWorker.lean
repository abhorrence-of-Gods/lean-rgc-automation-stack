import Lean

/-
Lean-RGC Native Lean-side JSONL worker (experimental v30).

This worker speaks the JSONL protocol used by `LeanServerAdapter`.  Compared
with v29, `apply_tactic` can run an optional Lean-side source-check path: the
worker renders the current task/state/action into a temporary Lean theorem and
asks the project Lean executable to elaborate it.  This is still a conservative
MVP, not a full in-memory `MVarId` tactic-state RPC.  The protocol, state ids,
branch/rollback, and kernel-shaped JSON are intentionally stable so a future
true elaborator/RPC backend can replace the source-check implementation without
changing Python-side RGC artifacts.

Supported commands:
  * load_project
  * register_task / init_state
  * get_state / list_states
  * branch_state / rollback_state
  * kernel_state / structured_state
  * apply_tactic
  * status
  * shutdown
-/

open Lean

namespace RGCLean
namespace KernelWorker

structure WorkerState where
  sessionId : String
  states : Std.HashMap String Json := {}
  tasks : Std.HashMap String Json := {}
  nRequests : Nat := 0
  nFailures : Nat := 0
  loaded : Bool := false
  leanCmd : String := "lake env lean"
  workdir : String := "."
  execMode : String := "source_check" -- source_check | heuristic
  timeoutSec : Nat := 20

abbrev WRef := IO.Ref WorkerState

partial def jsonGetObjVal? (j : Json) (k : String) : Option Json :=
  match j with
  | Json.obj kvs =>
      match kvs.toList.find? (fun kv => kv.fst == k) with
      | some kv => some kv.snd
      | none => none
  | _ => none

partial def jsonGetStr? (j : Json) (k : String) : Option String := do
  match jsonGetObjVal? j k with
  | some (Json.str s) => some s
  | _ => none

partial def jsonGetBool? (j : Json) (k : String) : Option Bool := do
  match jsonGetObjVal? j k with
  | some (Json.bool b) => some b
  | _ => none

partial def jsonGetNat? (j : Json) (k : String) : Option Nat := do
  match jsonGetObjVal? j k with
  | some (Json.num n) =>
      let s := toString n
      match s.toNat? with
      | some v => some v
      | none => none
  | _ => none

partial def jsonGetObj? (j : Json) (k : String) : Option Json := jsonGetObjVal? j k

partial def jsonGetStrArray? (j : Json) (k : String) : Option (List String) :=
  match jsonGetObjVal? j k with
  | some (Json.arr xs) =>
      let vals := xs.toList.filterMap (fun x => match x with | Json.str s => some s | _ => none)
      some vals
  | _ => none

partial def jsonArr (xs : List Json) : Json := Json.arr xs.toArray

partial def obj (xs : List (String × Json)) : Json := Json.mkObj xs

partial def ok (xs : List (String × Json) := []) : Json := obj (("ok", Json.bool true) :: xs)
partial def err (msg : String) : Json := obj [("ok", Json.bool false), ("error", Json.str msg)]

def hashString (s : String) : String :=
  toString s.hash

partial def hasSubstr (s pat : String) : Bool :=
  (s.splitOn pat).length > 1

partial def targetHead (s : String) : String :=
  if hasSubstr s "∀" || hasSubstr s "forall" then "forall"
  else if hasSubstr s "→" || hasSubstr s "->" then "imp"
  else if hasSubstr s "∧" || hasSubstr s " And " then "and"
  else if hasSubstr s "∨" || hasSubstr s " Or " then "or"
  else if hasSubstr s "=" then "eq"
  else if hasSubstr s "≤" || hasSubstr s "<=" || hasSubstr s "<" then "order"
  else "unknown"

partial def carrierAtoms (s : String) : List String :=
  let base := []
  let base := if targetHead s == "forall" then "unintroduced_forall" :: base else base
  let base := if targetHead s == "imp" then "unintroduced_imp" :: base else base
  let base := if targetHead s == "and" then "unsplit_and_target" :: base else base
  let base := if targetHead s == "eq" then "eq_reflexive_goal" :: base else base
  let base := if hasSubstr s "+" || hasSubstr s "*" || hasSubstr s "Nat" || hasSubstr s "≤" || hasSubstr s "<" then "nat_arith_goal" :: base else base
  base.reverse

partial def domainTags (s : String) : List String :=
  let base := []
  let base := if hasSubstr s "Nat" || hasSubstr s "ℕ" || hasSubstr s "+" || hasSubstr s "*" then "Nat" :: base else base
  let base := if hasSubstr s "List" || hasSubstr s "[]" then "List" :: base else base
  let base := if hasSubstr s "=" then "Eq" :: base else base
  let base := if hasSubstr s "≤" || hasSubstr s "<" || hasSubstr s "+" || hasSubstr s "*" then "Arith" :: base else base
  base.reverse

partial def mkKernelState (state : Json) : Json :=
  let stateId := jsonGetStr? state "state_id" |>.getD "state"
  let taskId := jsonGetStr? state "task_id" |>.getD "task"
  let target := jsonGetStr? state "target" |>.getD ""
  let closed := jsonGetBool? state "closed" |>.getD false
  let envFp := hashString (taskId ++ ":" ++ (jsonGetStr? state "kernel_backend" |>.getD "native_lean_worker"))
  let rawStateHash := hashString (toString state)
  let normStateHash := hashString ((targetHead target) ++ ":" ++ toString (domainTags target) ++ ":" ++ toString closed)
  let proofPrefix := jsonGetStr? state "prefix" |>.getD ""
  let goals := if closed || target.trim.isEmpty then jsonArr [] else jsonArr [
    obj [
      ("goal_id", Json.str "g0"),
      ("mvar_id", Json.str ("?m." ++ stateId)),
      ("target_expr_id", Json.str ("expr_" ++ hashString target)),
      ("target_head", Json.str (targetHead target)),
      ("relation", Json.str (if hasSubstr target "=" then "=" else "")),
      ("local_context_graph_id", Json.str ("lctx_" ++ stateId)),
      ("target_symbols", jsonArr []),
      ("domain_tags", jsonArr ((domainTags target).map Json.str)),
      ("connective_counts", obj []),
      ("carrier_atoms_readout", jsonArr ((carrierAtoms target).map Json.str)),
      ("raw_hash", Json.str (hashString target)),
      ("norm_hash", Json.str (hashString (targetHead target ++ toString (domainTags target)))),
      ("target", obj [
        ("text", Json.str target),
        ("kind", Json.str (jsonGetStr? state "expr_kind" |>.getD "text_expr_chart")),
        ("head", Json.str (targetHead target)),
        ("carrier_atoms", jsonArr ((carrierAtoms target).map Json.str)),
        ("domain_tags", jsonArr ((domainTags target).map Json.str)),
        ("kernel_backed", Json.bool (jsonGetBool? state "elaboration_checked" |>.getD false))
      ]),
      ("local_deps", jsonArr [])
    ]
  ]
  let mvars := if closed || target.trim.isEmpty then jsonArr [] else jsonArr [obj [
    ("mvar_id", Json.str ("?m." ++ stateId)),
    ("user_name", Json.str ""),
    ("type_expr_id", Json.str ("expr_" ++ hashString target)),
    ("type_text", Json.str target),
    ("local_context_fvars", jsonArr []),
    ("assigned", Json.bool false),
    ("assignment_expr_id", Json.null),
    ("kind", Json.str "goal"),
    ("dependencies_mvars", jsonArr []),
    ("dependencies_fvars", jsonArr []),
    ("raw_hash", Json.str (hashString target)),
    ("norm_hash", Json.str (hashString (targetHead target ++ toString (domainTags target))))
  ]]
  obj [
    ("schema_version", Json.str "lean-rgc-kernel-state-v1"),
    ("extraction_backend", Json.str (jsonGetStr? state "kernel_backend" |>.getD "native_lean_worker_v30_source_check")),
    ("state_id", Json.str stateId),
    ("task_id", Json.str taskId),
    ("env_fingerprint", Json.str envFp),
    ("state_hash_raw", Json.str rawStateHash),
    ("state_hash_norm", Json.str normStateHash),
    ("status", Json.str (if closed then "closed" else "open")),
    ("goals", goals),
    ("local_context", obj [("nodes", jsonArr []), ("edges", jsonArr [])]),
    ("local_contexts", jsonArr [obj [
      ("schema_version", Json.str "lean-rgc-local-context-graph-v1"),
      ("local_context_graph_id", Json.str ("lctx_" ++ stateId)),
      ("nodes", jsonArr []),
      ("edges", jsonArr []),
      ("raw_hash", Json.str (hashString stateId)),
      ("norm_hash", Json.str (hashString "empty_lctx"))
    ]]),
    ("metavars", mvars),
    ("typeclasses", jsonArr []),
    ("expr_graph", obj [
      ("schema_version", Json.str "lean-rgc-expr-graph-v1"),
      ("nodes", if closed || target.trim.isEmpty then jsonArr [] else jsonArr [obj [
        ("expr_id", Json.str ("expr_" ++ hashString target)),
        ("kind", Json.str "lean_worker_text_expr_chart"),
        ("head", Json.str (targetHead target)),
        ("text", Json.str target),
        ("role", Json.str "goal_target"),
        ("raw_hash", Json.str (hashString target)),
        ("norm_hash", Json.str (hashString (targetHead target ++ toString (domainTags target))))
      ]]),
      ("edges", jsonArr []),
      ("roots", if closed || target.trim.isEmpty then jsonArr [] else jsonArr [Json.str ("expr_" ++ hashString target)]),
      ("source", Json.str "native_worker_expr_graph_v47_chart")
    ]),
    ("messages", jsonGetObjVal? state "raw_messages" |>.getD (jsonArr [])),
    ("options", obj []),
    ("proof_prefix_hash", Json.str (hashString proofPrefix)),
    ("proof_prefix", Json.str proofPrefix),
    ("object_coverage", obj [
      ("expr_ast", Json.bool false),
      ("local_decl_graph", Json.bool false),
      ("metavariable_graph", Json.bool (!closed)),
      ("typeclass_graph", Json.bool false),
      ("in_memory_state_id", Json.bool true),
      ("tactic_transition_api", Json.bool true),
      ("replay_certificate", Json.bool false),
      ("source", Json.str "native_lean_worker_source_check_chart")
    ]),
    ("closed", Json.bool closed),
    ("canonical_status", Json.str "kernel_structured_state_chart_not_canonical")
  ]

partial def initialStateFromTask (task : Json) : Json :=
  let taskId := jsonGetStr? task "task_id" |>.getD (hashString (toString task))
  let statement := jsonGetStr? task "statement" |>.getD "True"
  let sid := "native_state_" ++ hashString (taskId ++ statement)
  obj [
    ("state_id", Json.str sid),
    ("task_id", Json.str taskId),
    ("task", task),
    ("prefix", Json.str (jsonGetStr? task "prefix" |>.getD "")),
    ("target", Json.str statement),
    ("goals_text", Json.str ("⊢ " ++ statement)),
    ("local_context", Json.str ""),
    ("raw_messages", jsonArr []),
    ("depth", Json.num 0),
    ("closed", Json.bool false),
    ("kernel_backend", Json.str "native_lean_worker_v30_source_check"),
    ("canonical_status", Json.str "native_worker_state_chart_not_canonical")
  ]

partial def stateIdOf (state : Json) : String := jsonGetStr? state "state_id" |>.getD (hashString (toString state))

partial def indentBlock (text : String) : String :=
  let ls := text.trimRight.splitOn "\n"
  String.intercalate "\n" (ls.map (fun line => if line.trim.isEmpty then line else "  " ++ line))

partial def renderImports (task : Json) : String :=
  let imps := jsonGetStrArray? task "imports" |>.getD ["Mathlib"]
  String.intercalate "\n" (imps.map (fun i => "import " ++ i))

partial def renderOptions (task : Json) (action : Json) : String :=
  let hb := jsonGetNat? action "max_heartbeats" |>.getD (jsonGetNat? task "max_heartbeats" |>.getD 200000)
  "set_option maxHeartbeats " ++ toString hb

partial def theoremName (task : Json) (action : Json) : String :=
  let tid := jsonGetStr? task "task_id" |>.getD "task"
  let aid := jsonGetStr? action "action_id" |>.getD (jsonGetStr? action "tactic" |>.getD "action")
  "rgc_native_probe_" ++ hashString (tid ++ aid)

partial def renderCandidateSource (task : Json) (state : Json) (action : Json) : String :=
  let statement :=
    let stTarget := jsonGetStr? state "target" |>.getD ""
    if stTarget.trim.isEmpty then jsonGetStr? task "statement" |>.getD "True" else stTarget
  let ns := jsonGetStr? task "namespace"
  let nsOpen := match ns with | some n => "namespace " ++ n ++ "\n" | none => ""
  let nsClose := match ns with | some n => "\nend " ++ n | none => ""
  let taskPrefix := jsonGetStr? task "prefix" |>.getD ""
  let statePrefix := jsonGetStr? state "prefix" |>.getD taskPrefix
  let tactic := jsonGetStr? action "tactic" |>.getD ""
  let body := String.intercalate "\n" (([statePrefix, tactic].filter (fun s => !s.trim.isEmpty)).map indentBlock)
  renderImports task ++ "\n\n" ++ renderOptions task action ++ "\n\n" ++ nsOpen ++ "theorem " ++ theoremName task action ++ " : " ++ statement ++ " := by\n" ++ body ++ nsClose ++ "\n"

partial def shellEscape (s : String) : String :=
  -- Safe enough for generated paths without single quotes; still quote to guard spaces.
  "'" ++ (s.replace "'" "'\\''") ++ "'"

partial def classifyOutput (out : String) (exitCode : UInt32) : String :=
  if exitCode == 0 then "success"
  else if hasSubstr out "unsolved goals" || hasSubstr out "goals" then "partial"
  else if hasSubstr out "timeout" || exitCode == 124 then "timeout"
  else if hasSubstr out "error" || hasSubstr out "failed" then "fail"
  else "elab_error"

partial def splitMessages (s : String) : List Json :=
  (s.splitOn "\n").filterMap (fun line => if line.trim.isEmpty then none else some (Json.str line.trim))

partial def runSourceCheck (st : WorkerState) (task : Json) (state : Json) (action : Json) : IO Json := do
  let src := renderCandidateSource task state action
  let dir := st.workdir ++ "/.lean_rgc_native_checks"
  IO.FS.createDirAll (System.FilePath.mk dir)
  let fname := "rgc_native_" ++ hashString (src) ++ ".lean"
  let fpath := dir ++ "/" ++ fname
  IO.FS.writeFile (System.FilePath.mk fpath) src
  let timeoutPrefix := if st.timeoutSec == 0 then "" else "timeout " ++ toString st.timeoutSec ++ "s "
  let shell := "cd " ++ shellEscape st.workdir ++ " && " ++ timeoutPrefix ++ st.leanCmd ++ " " ++ shellEscape fpath
  let t0 ← IO.monoMsNow
  let proc ← IO.Process.output { cmd := "bash", args := #["-lc", shell] }
  let t1 ← IO.monoMsNow
  let combined := proc.stdout ++ "\n" ++ proc.stderr
  let status := classifyOutput combined proc.exitCode
  pure (obj [
    ("status", Json.str status),
    ("return_code", Json.num proc.exitCode.toNat),
    ("stdout", Json.str proc.stdout),
    ("stderr", Json.str proc.stderr),
    ("messages", jsonArr (splitMessages combined)),
    ("elapsed_ms", Json.num (t1 - t0)),
    ("proof_source_sha", Json.str (hashString src)),
    ("proof_source_path", Json.str fpath),
    ("execution_backend", Json.str "native_lean_source_check_v30"),
    ("elaboration_checked", Json.bool true)
  ])

partial def statusJson (st : WorkerState) : Json :=
  ok [
    ("session_id", Json.str st.sessionId),
    ("backend", Json.str "native_lean_jsonl_worker_v30"),
    ("loaded", Json.bool st.loaded),
    ("n_states", Json.num st.states.size),
    ("n_tasks", Json.num st.tasks.size),
    ("n_requests", Json.num st.nRequests),
    ("n_failures", Json.num st.nFailures),
    ("exec_mode", Json.str st.execMode),
    ("lean_cmd", Json.str st.leanCmd),
    ("workdir", Json.str st.workdir),
    ("canonical_status", Json.str "native_lean_worker_protocol_chart_not_canonical")
  ]

partial def childStateFromApply (s : Json) (task : Json) (action : Json) (status : String) (check : Json) : IO Json := do
  let oldTarget := jsonGetStr? s "target" |>.getD ""
  let closes := status == "success"
  let newTarget := if closes then "" else oldTarget
  let actionId := jsonGetStr? action "action_id" |>.getD (hashString (jsonGetStr? action "tactic" |>.getD ""))
  let tactic := jsonGetStr? action "tactic" |>.getD ""
  let nsid := "native_after_" ++ hashString (stateIdOf s ++ actionId ++ tactic ++ oldTarget ++ status)
  let proofPrefix := (jsonGetStr? s "prefix" |>.getD "") ++ "\n" ++ tactic
  pure (obj [
    ("state_id", Json.str nsid),
    ("task_id", Json.str (jsonGetStr? s "task_id" |>.getD "task")),
    ("task", jsonGetObj? s "task" |>.getD task),
    ("prefix", Json.str proofPrefix),
    ("target", Json.str newTarget),
    ("goals_text", Json.str (if newTarget == "" then "" else "⊢ " ++ newTarget)),
    ("parent_state_id", Json.str (stateIdOf s)),
    ("applied_action_id", Json.str actionId),
    ("applied_tactic", Json.str tactic),
    ("depth", Json.num 1),
    ("closed", Json.bool closes),
    ("elaboration_checked", jsonGetObjVal? check "elaboration_checked" |>.getD (Json.bool false)),
    ("kernel_backend", Json.str (jsonGetStr? check "execution_backend" |>.getD "native_lean_worker_v30")),
    ("canonical_status", Json.str "native_worker_state_chart_not_canonical")
  ])

partial def handle (ref : WRef) (req : Json) : IO Json := do
  let cmd := jsonGetStr? req "cmd" |>.getD ""
  let st0 ← ref.get
  ref.set {st0 with nRequests := st0.nRequests + 1}
  match cmd with
  | "load_project" =>
      let st ← ref.get
      let leanCmd := jsonGetStr? req "lean_cmd" |>.getD st.leanCmd
      let workdir := jsonGetStr? req "workdir" |>.getD st.workdir
      let execMode := jsonGetStr? req "native_exec_mode" |>.getD (jsonGetStr? req "exec_mode" |>.getD st.execMode)
      let timeoutSec := jsonGetNat? req "timeout_s" |>.getD st.timeoutSec
      let st' := {st with loaded := true, leanCmd := leanCmd, workdir := workdir, execMode := execMode, timeoutSec := timeoutSec}
      ref.set st'
      pure (statusJson st')
  | "status" => do pure (statusJson (← ref.get))
  | "register_task" | "init_state" => do
      match jsonGetObj? req "task" with
      | none => pure (err "register_task requires task")
      | some task =>
          let state := initialStateFromTask task
          let sid := stateIdOf state
          let taskId := jsonGetStr? task "task_id" |>.getD sid
          let st ← ref.get
          ref.set {st with tasks := st.tasks.insert taskId task, states := st.states.insert sid state, loaded := true}
          pure (ok [("state", state), ("kernel_state", mkKernelState state), ("status", statusJson (← ref.get))])
  | "get_state" => do
      let sid := jsonGetStr? req "state_id" |>.getD ""
      match (← ref.get).states.get? sid with
      | some s => pure (ok [("state", s), ("kernel_state", mkKernelState s)])
      | none => pure (err ("unknown state_id: " ++ sid))
  | "list_states" => do
      let vals := (← ref.get).states.toList.map (fun kv => kv.snd)
      pure (ok [("states", jsonArr vals)])
  | "branch_state" => do
      let sid := jsonGetStr? req "state_id" |>.getD ""
      match (← ref.get).states.get? sid with
      | none => pure (err ("unknown state_id: " ++ sid))
      | some s =>
          let now ← IO.monoMsNow
          let nsid := jsonGetStr? req "new_state_id" |>.getD ("native_branch_" ++ hashString (sid ++ toString now))
          let child := obj [
            ("state_id", Json.str nsid),
            ("task_id", Json.str (jsonGetStr? s "task_id" |>.getD "task")),
            ("task", jsonGetObj? s "task" |>.getD Json.null),
            ("prefix", jsonGetObjVal? s "prefix" |>.getD (Json.str "")),
            ("target", jsonGetObjVal? s "target" |>.getD (Json.str "")),
            ("goals_text", jsonGetObjVal? s "goals_text" |>.getD (Json.str "")),
            ("parent_state_id", Json.str sid),
            ("depth", Json.num 0),
            ("closed", Json.bool false),
            ("kernel_backend", Json.str "native_lean_worker_v30_branch"),
            ("canonical_status", Json.str "native_worker_state_chart_not_canonical")
          ]
          let st ← ref.get
          ref.set {st with states := st.states.insert nsid child}
          pure (ok [("state", child), ("kernel_state", mkKernelState child)])
  | "rollback_state" => do
      let sid := jsonGetStr? req "state_id" |>.getD ""
      match (← ref.get).states.get? sid with
      | none => pure (err ("unknown state_id: " ++ sid))
      | some s =>
          let psid := jsonGetStr? s "parent_state_id"
          let st ← ref.get
          match psid.bind (fun p => st.states.get? p) with
          | some p => pure (ok [("state", p), ("kernel_state", mkKernelState p)])
          | none => pure (ok [("state", s), ("kernel_state", mkKernelState s)])
  | "kernel_state" => do
      let sid := jsonGetStr? req "state_id" |>.getD ""
      match (← ref.get).states.get? sid with
      | some s => pure (ok [("kernel_state", mkKernelState s)])
      | none => pure (err ("unknown state_id: " ++ sid))
  | "structured_state" => do
      let sid := jsonGetStr? req "state_id" |>.getD ""
      match (← ref.get).states.get? sid with
      | some s => pure (ok [("kernel_state", mkKernelState s)])
      | none => pure (err ("unknown state_id: " ++ sid))
  | "apply_tactic" => do
      let action := jsonGetObj? req "action" |>.getD Json.null
      let actionId := jsonGetStr? action "action_id" |>.getD (hashString (jsonGetStr? action "tactic" |>.getD ""))
      let tactic := jsonGetStr? action "tactic" |>.getD ""
      let task := jsonGetObj? req "task" |>.getD Json.null
      let stForBase ← ref.get
      let baseState ←
        match jsonGetStr? req "state_id" with
        | some sid => pure (stForBase.states.get? sid)
        | none =>
            match jsonGetObj? req "state" with
            | some s => pure (some s)
            | none =>
                match jsonGetObj? req "task" with
                | some t => pure (some (initialStateFromTask t))
                | none => pure none
      match baseState with
      | none => pure (err "apply_tactic requires state_id, state, or task")
      | some s =>
          let st ← ref.get
          let check ←
            if st.execMode == "heuristic" then
              pure (obj [("status", Json.str "heuristic"), ("messages", jsonArr [Json.str "native heuristic mode"]), ("elapsed_ms", Json.num 0), ("execution_backend", Json.str "native_lean_heuristic_v30"), ("elaboration_checked", Json.bool false)])
            else
              try runSourceCheck st (if task == Json.null then (jsonGetObj? s "task" |>.getD Json.null) else task) s action
              catch e => pure (obj [("status", Json.str "elab_error"), ("messages", jsonArr [Json.str (toString e)]), ("stderr", Json.str (toString e)), ("elapsed_ms", Json.num 0), ("execution_backend", Json.str "native_lean_source_check_v30_error"), ("elaboration_checked", Json.bool false)])
          let status := jsonGetStr? check "status" |>.getD "elab_error"
          let child ← childStateFromApply s (if task == Json.null then (jsonGetObj? s "task" |>.getD Json.null) else task) action status check
          let st ← ref.get
          ref.set {st with states := st.states.insert (stateIdOf child) child}
          let beforeKernel := mkKernelState s
          let afterKernel := mkKernelState child
          let stateDelta := obj [
            ("schema_version", Json.str "lean-rgc-goal-state-transition-v47.0"),
            ("before_state_id", Json.str (stateIdOf s)),
            ("after_state_id", Json.str (stateIdOf child)),
            ("action_id", Json.str actionId),
            ("tactic", Json.str tactic),
            ("goal_count_before", if (jsonGetBool? s "closed" |>.getD false) then Json.num 0 else Json.num 1),
            ("goal_count_after", if (jsonGetBool? child "closed" |>.getD false) then Json.num 0 else Json.num 1),
            ("mvar_response", if (jsonGetBool? child "closed" |>.getD false) then Json.num 1 else Json.num 0),
            ("progress_status", if (jsonGetBool? child "closed" |>.getD false) then Json.str "closed" else Json.str "open"),
            ("canonical_status", Json.str "native_worker_goal_state_transition_chart_not_canonical")
          ]
          let audit := obj [
            ("task_id", Json.str (jsonGetStr? child "task_id" |>.getD "task")),
            ("state_id", Json.str (stateIdOf s)),
            ("action_id", Json.str actionId),
            ("status", Json.str (if status == "heuristic" then "partial" else status)),
            ("elapsed_ms", jsonGetObjVal? check "elapsed_ms" |>.getD (Json.num 0)),
            ("stdout", jsonGetObjVal? check "stdout" |>.getD (Json.str "")),
            ("stderr", jsonGetObjVal? check "stderr" |>.getD (Json.str "")),
            ("messages", jsonGetObjVal? check "messages" |>.getD (jsonArr [])),
            ("after_state", child),
            ("audit_flags", obj [
              ("native_lean_worker", Json.bool true),
              ("backend", Json.str "native_lean_jsonl_worker_v30"),
              ("native_exec_mode", Json.str st.execMode),
              ("elaboration_checked", jsonGetObjVal? check "elaboration_checked" |>.getD (Json.bool false)),
              ("execution_backend", jsonGetObjVal? check "execution_backend" |>.getD (Json.str "native_lean_worker_v30")),
              ("proof_source_sha", jsonGetObjVal? check "proof_source_sha" |>.getD (Json.str "")),
              ("proof_source_path", jsonGetObjVal? check "proof_source_path" |>.getD (Json.str "")),
              ("return_code", jsonGetObjVal? check "return_code" |>.getD (Json.num 0)),
              ("kernel_state_schema", Json.str "lean-rgc-kernel-state-v1"),
              ("kernel_state_before", beforeKernel),
              ("kernel_state_after", afterKernel),
              ("state_delta", stateDelta),
              ("goal_state_transition_api", Json.bool true),
              ("before_persistent_state_id", Json.str (stateIdOf s)),
              ("after_persistent_state_id", Json.str (stateIdOf child)),
              ("canonical_status", Json.str "native_worker_audit_chart_not_canonical")
            ])
          ]
          pure (ok [("audit", audit), ("kernel_state", mkKernelState child), ("state", child)])
  | "shutdown" => pure (ok [("shutdown", Json.bool true)])
  | _ => pure (err ("unknown cmd: " ++ cmd))

partial def loop (ref : WRef) : IO Unit := do
  let stdin ← IO.getStdin
  let stdout ← IO.getStdout
  let rec go : IO Unit := do
    let line ← stdin.getLine
    if line.trim.isEmpty then go else
      let rep ←
        match Json.parse line with
        | Except.error e => pure (err ("json parse error: " ++ e))
        | Except.ok j => handle ref j
      stdout.putStrLn (Json.compress rep)
      stdout.flush
      if jsonGetBool? rep "shutdown" |>.getD false then pure () else go
  try go catch _ => pure ()

partial def argAfter (args : List String) (name : String) : Option String :=
  match args with
  | [] => none
  | x :: y :: rest => if x == name then some y else argAfter (y :: rest) name
  | _ :: rest => argAfter rest name

end KernelWorker
end RGCLean

def main (args : List String) : IO Unit := do
  let execMode := RGCLean.KernelWorker.argAfter args "--exec-mode" |>.getD "source_check"
  let leanCmd := RGCLean.KernelWorker.argAfter args "--lean-cmd" |>.getD "lake env lean"
  let workdir := RGCLean.KernelWorker.argAfter args "--workdir" |>.getD "."
  let now ← IO.monoMsNow
  let ref ← IO.mkRef ({ sessionId := "native_lean_worker_" ++ toString now, execMode := execMode, leanCmd := leanCmd, workdir := workdir } : RGCLean.KernelWorker.WorkerState)
  RGCLean.KernelWorker.loop ref
