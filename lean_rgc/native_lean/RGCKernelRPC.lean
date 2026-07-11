import Lean

/-
Lean-RGC in-memory kernel RPC worker.

This worker keeps real Lean elaborator/metavariable state behind opaque
process-local state ids and applies tactics directly to stored `MVarId`s using
`Lean.Elab.runTactic`.  It returns the strict `lean-rgc-kernel-state-v3`
payload with Expr DAG, local declaration graph, metavariable graph, a
typeclass-obligation readout over synthetic/class metavariables, and persistent
branch/rollback state ids.  v2 added, for every open metavariable, a bounded
pretty-printed `type_text` and the `depends_on` list of metavariables occurring
in its (instantiated) type, plus `target_text` on goals, and replays
`task.prefix` tactics so the initial state is the post-prefix state.  v3 adds
M2 proof-term minimal support: after a tactic application assigns a goal mvar,
`minimal_support` records, per closed goal, the local-context hypotheses that
occur in the instantiated proof term (expanded to their dependency closure in
the local context) and a bounded list of the constants the proof references.
-/
open Lean
open Lean.Elab
open Lean.Meta

namespace RGCLean
namespace KernelRPC

def schemaVersion : String := "lean-rgc-kernel-state-v3"
def transitionVersion : String := "lean-rgc-kernel-transition-v1"
def minimalSupportVersion : String := "lean-rgc-minimal-support-v1"
def rpcProtocolVersion : String := "lean-rgc-jsonl-rpc-v2"
def u05SemanticsVersion : String := "lean-rgc-u05-rpc-semantics-v1"
def u05ReplayVersion : String := "lean-rgc-u05-replay-v1"

partial def jsonArr (xs : List Json) : Json := Json.arr xs.toArray
partial def obj (xs : List (String × Json)) : Json := Json.mkObj xs
partial def ok (xs : List (String × Json) := []) : Json := obj (("ok", Json.bool true) :: xs)
partial def err (msg : String) : Json := obj [("ok", Json.bool false), ("error", Json.str msg)]

def responseEnvelope (requestId payload : Json) : Json :=
  match payload with
  | Json.obj kvs =>
      Json.obj ((kvs.insert "id" requestId).insert
        "rpc_protocol_version" (Json.str rpcProtocolVersion))
  | other => obj [
      ("id", requestId),
      ("rpc_protocol_version", Json.str rpcProtocolVersion),
      ("payload", other)
    ]

def hashString (s : String) : String := toString s.hash

partial def jsonGetObjVal? (j : Json) (k : String) : Option Json :=
  match j with
  | Json.obj kvs =>
      match kvs.toList.find? (fun kv => kv.fst == k) with
      | some kv => some kv.snd
      | none => none
  | _ => none

def requestIdJson (req : Json) : Json :=
  jsonGetObjVal? req "id" |>.getD Json.null

partial def jsonGetStr? (j : Json) (k : String) : Option String :=
  match jsonGetObjVal? j k with
  | some (Json.str s) => some s
  | _ => none

partial def jsonGetBool? (j : Json) (k : String) : Option Bool :=
  match jsonGetObjVal? j k with
  | some (Json.bool b) => some b
  | _ => none

partial def jsonGetNat? (j : Json) (k : String) : Option Nat :=
  match jsonGetObjVal? j k with
  | some (Json.num n) =>
      match (toString n).toNat? with
      | some v => some v
      | none => none
  | _ => none

partial def jsonGetObj? (j : Json) (k : String) : Option Json :=
  jsonGetObjVal? j k

def jsonStrOrNull : Option String → Json
  | some s => Json.str s
  | none => Json.null

def jsonNatOrNull : Option Nat → Json
  | some n => Json.num n
  | none => Json.null

partial def jsonGetStrArray? (j : Json) (k : String) : Option (List String) :=
  match jsonGetObjVal? j k with
  | some (Json.arr xs) =>
      some <| xs.toList.filterMap fun x =>
        match x with
        | Json.str s => some s
        | _ => none
  | _ => none

def nameFromString (s : String) : Name :=
  s.splitOn "." |>.foldl
    (fun acc part =>
      if part.isEmpty then acc
      else if acc.isAnonymous then Name.mkSimple part
      else Name.mkStr acc part)
    Name.anonymous

def defaultImports : List String := ["Lean"]

def importsFrom (task : Json) : List String :=
  match jsonGetStrArray? task "imports" with
  | some [] => defaultImports
  | some xs => xs
  | none => defaultImports

unsafe def loadEnvForImports (imports : List String) : IO Environment := do
  enableInitializersExecution
  let imps := imports.map fun s => ({ module := nameFromString s } : Import)
  importModules (loadExts := true) imps.toArray {}

def binderInfoString : BinderInfo → String
  | .default => "default"
  | .implicit => "implicit"
  | .strictImplicit => "strictImplicit"
  | .instImplicit => "instImplicit"

def localDeclKindString : LocalDeclKind → String
  | .default => "default"
  | .implDetail => "implDetail"
  | .auxDecl => "auxDecl"

def metavarKindString : MetavarKind → String
  | .natural => "natural"
  | .synthetic => "synthetic"
  | .syntheticOpaque => "syntheticOpaque"

def literalString : Literal → String
  | .natVal n => toString n
  | .strVal s => s

def exprKindString : Expr → String
  | .bvar .. => "bvar"
  | .fvar .. => "fvar"
  | .mvar .. => "mvar"
  | .sort .. => "sort"
  | .const .. => "const"
  | .app .. => "app"
  | .lam .. => "lam"
  | .forallE .. => "forallE"
  | .letE .. => "letE"
  | .lit .. => "lit"
  | .mdata .. => "mdata"
  | .proj .. => "proj"

def exprConstName? (e : Expr) : Option Name :=
  match e.getAppFn.consumeMData with
  | .const n _ => some n
  | _ => none

def exprHeadString (e : Expr) : String :=
  match exprConstName? e with
  | some n => toString n
  | none =>
      match e.getAppFn.consumeMData with
      | .fvar id => toString id.name
      | .mvar id => toString id.name
      | .sort .. => "sort"
      | .forallE .. => "forallE"
      | .lam .. => "lam"
      | .lit l => literalString l
      | .proj n idx _ => toString n ++ "." ++ toString idx
      | _ => exprKindString e

partial def collectFVars (e : Expr) (acc : Std.HashSet FVarId := {}) : Std.HashSet FVarId :=
  match e with
  | .fvar id => acc.insert id
  | .app f a => collectFVars a (collectFVars f acc)
  | .lam _ t b _ => collectFVars b (collectFVars t acc)
  | .forallE _ t b _ => collectFVars b (collectFVars t acc)
  | .letE _ t v b _ => collectFVars b (collectFVars v (collectFVars t acc))
  | .mdata _ x => collectFVars x acc
  | .proj _ _ x => collectFVars x acc
  | _ => acc

partial def collectMVars (e : Expr) (acc : Std.HashSet MVarId := {}) : Std.HashSet MVarId :=
  match e with
  | .mvar id => acc.insert id
  | .app f a => collectMVars a (collectMVars f acc)
  | .lam _ t b _ => collectMVars b (collectMVars t acc)
  | .forallE _ t b _ => collectMVars b (collectMVars t acc)
  | .letE _ t v b _ => collectMVars b (collectMVars v (collectMVars t acc))
  | .mdata _ x => collectMVars x acc
  | .proj _ _ x => collectMVars x acc
  | _ => acc

def fvarStrings (s : Std.HashSet FVarId) : List Json :=
  /- Expression-graph references must use the same opaque identifier namespace
  as `serializeLocalContext`.  Emitting the bare internal Lean name here made a
  post-`intro` target refer to `_uniq.*` while its declaration was registered as
  `fvar__uniq.*`, so strict reachable-closure validation correctly rejected the
  native payload. -/
  (s.toList.map fun id => Json.str ("fvar_" ++ toString id.name))

def mvarStrings (s : Std.HashSet MVarId) : List Json :=
  (s.toList.map fun id => Json.str ("?" ++ toString id.name))

structure NormCtx where
  fvars : Std.HashMap FVarId Nat := {}
  mvars : Std.HashMap MVarId Nat := {}

partial def normExprSig (ctx : NormCtx) (e : Expr) : String :=
  match e with
  | .bvar i => "bvar:" ++ toString i
  | .fvar id => "fvar:" ++ toString ((ctx.fvars.get? id).getD 0)
  | .mvar id => "mvar:" ++ toString ((ctx.mvars.get? id).getD 0)
  | .sort u => "sort:" ++ toString u
  | .const n ls => "const:" ++ toString n ++ ":" ++ toString (ls.map toString)
  | .app f a => "app(" ++ normExprSig ctx f ++ "," ++ normExprSig ctx a ++ ")"
  | .lam _ t b bi => "lam:" ++ binderInfoString bi ++ "(" ++ normExprSig ctx t ++ "," ++ normExprSig ctx b ++ ")"
  | .forallE _ t b bi => "forall:" ++ binderInfoString bi ++ "(" ++ normExprSig ctx t ++ "," ++ normExprSig ctx b ++ ")"
  | .letE _ t v b nd => "let:" ++ toString nd ++ "(" ++ normExprSig ctx t ++ "," ++ normExprSig ctx v ++ "," ++ normExprSig ctx b ++ ")"
  | .lit l => "lit:" ++ literalString l
  | .mdata _ x => "mdata(" ++ normExprSig ctx x ++ ")"
  | .proj n i x => "proj:" ++ toString n ++ ":" ++ toString i ++ "(" ++ normExprSig ctx x ++ ")"

def rawExprSig (e : Expr) : String := toString (repr e)
def exprIdOf (e : Expr) : String := "expr_" ++ hashString (rawExprSig e)

structure ExprSerState where
  seen : Std.HashMap String String := {}
  nodes : Array Json := #[]
  edges : Array Json := #[]

abbrev SerM := StateT ExprSerState MetaM

partial def serializeExpr (ctx : NormCtx) (e : Expr) : SerM String := do
  let raw := rawExprSig e
  match (← get).seen.get? raw with
  | some id => pure id
  | none => do
      let id := exprIdOf e
      modify fun s => {s with seen := s.seen.insert raw id}
      let childExprs : List (String × Expr) :=
        match e with
        | .app f a => [("fn", f), ("arg", a)]
        | .lam _ t b _ => [("type", t), ("body", b)]
        | .forallE _ t b _ => [("domain", t), ("body", b)]
        | .letE _ t v b _ => [("type", t), ("value", v), ("body", b)]
        | .mdata _ x => [("expr", x)]
        | .proj _ _ x => [("expr", x)]
        | _ => []
      let mut children : Array String := #[]
      for child in childExprs do
        let role := child.fst
        let c := child.snd
        let cid ← serializeExpr ctx c
        children := children.push cid
        modify fun s => {s with edges := s.edges.push (obj [
          ("src", Json.str id), ("dst", Json.str cid), ("role", Json.str role)
        ])}
      let pretty ← try
        pure (toString (← ppExpr e))
      catch _ =>
        pure (rawExprSig e)
      let levels :=
        match e with
        | .const _ ls => jsonArr (ls.map (fun l => Json.str (toString l)))
        | _ => jsonArr []
      let constName :=
        match e with
        | .const n _ => Json.str (toString n)
        | _ => Json.null
      let binderInfo :=
        match e with
        | .lam _ _ _ bi => Json.str (binderInfoString bi)
        | .forallE _ _ _ bi => Json.str (binderInfoString bi)
        | _ => Json.null
      let node := obj [
        ("expr_id", Json.str id),
        ("kind", Json.str (exprKindString e)),
        ("head", Json.str (exprHeadString e)),
        ("const_name", constName),
        ("levels", levels),
        ("binder_info", binderInfo),
        ("children", jsonArr (children.toList.map Json.str)),
        ("type_expr_id", Json.null),
        ("free_fvars", jsonArr (fvarStrings (collectFVars e))),
        ("free_mvars", jsonArr (mvarStrings (collectMVars e))),
        ("pretty", Json.str pretty),
        ("raw_hash", Json.str (hashString raw)),
        ("norm_hash", Json.str (hashString (normExprSig ctx e)))
      ]
      modify fun s => {s with nodes := s.nodes.push node}
      pure id

def mkNormCtx (lctx : LocalContext) (mvars : List MVarId) : NormCtx :=
  let fctx := lctx.foldl
    (fun m d => m.insert d.fvarId d.index)
    ({} : Std.HashMap FVarId Nat)
  let mctx := (mvars.toArray.mapIdx (fun i m => (i, m))).foldl
    (fun m pair => m.insert pair.snd pair.fst)
    ({} : Std.HashMap MVarId Nat)
  { fvars := fctx, mvars := mctx }

def relationOf (e : Expr) : String :=
  match exprConstName? e with
  | some ``Eq => "="
  | some ``Iff => "iff"
  | some n => if toString n == "LE.le" then "<=" else if toString n == "LT.lt" then "<" else ""
  | none => ""

def connectiveCounts (e : Expr) : Json :=
  let h := exprHeadString e
  let forallC := if e.isForall then 1 else 0
  let existsC := if h == "Exists" then 1 else 0
  let andC := if h == "And" then 1 else 0
  let orC := if h == "Or" then 1 else 0
  let impC := 0
  let eqC := if h == "Eq" then 1 else 0
  obj [
    ("forall", Json.num forallC),
    ("exists", Json.num existsC),
    ("and", Json.num andC),
    ("or", Json.num orC),
    ("imp", Json.num impC),
    ("eq", Json.num eqC)
  ]

def carrierAtomsReadout (e : Expr) : List String :=
  Id.run do
    let h := exprHeadString e
    let mut xs : List String := []
    if h == "Eq" then xs := "eq_goal" :: xs
    if h == "And" then xs := "and_goal" :: xs
    if h == "Or" then xs := "or_goal" :: xs
    if e.isForall then xs := "binder_goal" :: xs
    let s := toString (repr e)
    if (s.splitOn "Nat").length > 1 then xs := "nat_arith_goal" :: xs
    return xs.reverse

def domainTagsReadout (e : Expr) : List String :=
  Id.run do
    let s := toString (repr e)
    let mut xs : List String := []
    if (s.splitOn "Nat").length > 1 then xs := "Nat" :: xs
    if (s.splitOn "List").length > 1 then xs := "List" :: xs
    if exprHeadString e == "Eq" then xs := "Eq" :: xs
    return xs.reverse

def isLocalInstance (decl : LocalDecl) (insts : LocalInstances) : Bool :=
  insts.any fun inst =>
    match inst.fvar with
    | .fvar id => id == decl.fvarId
    | _ => false

def localDeclId (d : LocalDecl) : String := "fvar_" ++ toString d.fvarId.name

def declDependsJson (exprs : List Expr) : Json :=
  let fvars := exprs.foldl (fun s e => collectFVars e s) ({} : Std.HashSet FVarId)
  jsonArr ((fvars.toList.map fun id => Json.str ("fvar_" ++ toString id.name)))

def declMVarDepsJson (exprs : List Expr) : Json :=
  let mvars := exprs.foldl (fun s e => collectMVars e s) ({} : Std.HashSet MVarId)
  jsonArr ((mvars.toList.map fun id => Json.str ("?" ++ toString id.name)))

def serializeLocalContext (graphId : String) (lctx : LocalContext) (insts : LocalInstances) (ctx : NormCtx) : SerM Json := do
  let mut nodes : Array Json := #[]
  let mut edges : Array Json := #[]
  for decl in lctx do
    let typeId ← serializeExpr ctx decl.type
    let value? := decl.value? (allowNondep := true)
    let valueId? ←
      match value? with
      | some v => do pure (some (← serializeExpr ctx v))
      | none => pure none
    let exprs := match value? with | some v => [decl.type, v] | none => [decl.type]
    let deps := exprs.foldl (fun s e => collectFVars e s) ({} : Std.HashSet FVarId)
    for src in deps.toList do
      if src != decl.fvarId then
        edges := edges.push (obj [
          ("src", Json.str ("fvar_" ++ toString src.name)),
          ("dst", Json.str (localDeclId decl))
        ])
    let raw := toString (repr decl.type) ++ toString (value?.map rawExprSig)
    let norm := normExprSig ctx decl.type ++ toString (value?.map (normExprSig ctx))
    nodes := nodes.push (obj [
      ("fvar_id", Json.str (localDeclId decl)),
      ("user_name", Json.str (toString decl.userName)),
      ("binder_kind", Json.str (binderInfoString decl.binderInfo)),
      ("local_decl_kind", Json.str (localDeclKindString decl.kind)),
      ("type_expr_id", Json.str typeId),
      ("value_expr_id", match valueId? with | some id => Json.str id | none => Json.null),
      ("is_implementation_detail", Json.bool decl.isImplementationDetail),
      ("is_instance", Json.bool (isLocalInstance decl insts)),
      ("depends_on_fvars", declDependsJson exprs),
      ("depends_on_mvars", declMVarDepsJson exprs),
      ("raw_hash", Json.str (hashString raw)),
      ("norm_hash", Json.str (hashString norm))
    ])
  pure (obj [
    ("schema_version", Json.str "lean-rgc-local-context-graph-v1"),
    ("local_context_graph_id", Json.str graphId),
    ("nodes", Json.arr nodes),
    ("edges", Json.arr edges),
    ("raw_hash", Json.str (hashString (toString nodes ++ toString edges))),
    ("norm_hash", Json.str (hashString (toString (nodes.map toString) ++ toString (edges.map toString))))
  ])

def mvarIdString (id : MVarId) : String := "?" ++ toString id.name

def ppMaxLen : Nat := 512

def truncateText (s : String) (maxLen : Nat := ppMaxLen) : String :=
  if s.length ≤ maxLen then s
  else (s.toList.take maxLen).foldl (fun acc c => acc.push c) "" ++ "…"

/-- Bounded pretty-print of an mvar's instantiated type inside its own local
context, together with the metavariables occurring in that type.  Assigned
mvars carry no residual freedom, so callers skip them to bound payload size. -/
def mvarTypeReadout (decl : MetavarDecl) : MetaM (String × List MVarId) := do
  try
    let type ← instantiateMVars decl.type
    let text ←
      try
        withLCtx decl.lctx decl.localInstances do
          pure (toString (← ppExpr type))
      catch _ =>
        pure (toString (repr type))
    pure (truncateText text, (collectMVars type).toList)
  catch _ =>
    pure ("", [])

def mvarDeclJson (id : MVarId) (decl : MetavarDecl) (ctx : NormCtx) : SerM Json := do
  let typeId ← serializeExpr ctx decl.type
  let assignment? ← getExprMVarAssignment? id
  let assignmentId? ←
    match assignment? with
    | some a => do pure (some (← serializeExpr ctx a))
    | none => pure none
  let exprs := match assignment? with | some a => [decl.type, a] | none => [decl.type]
  let (typeText, typeMVars) ←
    if assignment?.isSome then pure ("", ([] : List MVarId))
    else (mvarTypeReadout decl : MetaM (String × List MVarId))
  pure (obj [
    ("mvar_id", Json.str (mvarIdString id)),
    ("user_name", Json.str (toString decl.userName)),
    ("type_text", Json.str typeText),
    ("depends_on", jsonArr (typeMVars.map (fun m => Json.str (mvarIdString m)))),
    ("type_expr_id", Json.str typeId),
    ("local_context_fvars", jsonArr ((decl.lctx.foldl (fun xs d => Json.str (localDeclId d) :: xs) []).reverse)),
    ("assigned", Json.bool assignment?.isSome),
    ("assignment_expr_id", match assignmentId? with | some eid => Json.str eid | none => Json.null),
    ("kind", Json.str (metavarKindString decl.kind)),
    ("dependencies_mvars", declMVarDepsJson exprs),
    ("dependencies_fvars", declDependsJson exprs),
    ("raw_hash", Json.str (hashString (toString id.name ++ toString (repr decl.type) ++ toString (assignment?.map rawExprSig)))),
    ("norm_hash", Json.str (hashString (normExprSig ctx decl.type ++ toString (assignment?.map (normExprSig ctx)))))
  ])

def typeclassObligationJson (id : MVarId) (decl : MetavarDecl) (ctx : NormCtx) : SerM (Option Json) := do
  let type ← instantiateMVars decl.type
  let className? ← try isClass? type catch _ => pure none
  let classHead := className?.getD ((exprConstName? type).getD Name.anonymous)
  let classHeadString := toString classHead
  let isLogicalHead :=
    classHeadString == "Eq" || classHeadString == "Iff" ||
    classHeadString == "And" || classHeadString == "Or" ||
    classHeadString == "Exists" || classHeadString == "True" ||
    classHeadString == "False" || classHead.isAnonymous
  let includeNode := className?.isSome && !isLogicalHead
  if !includeNode then
    pure none
  else
    let typeId ← serializeExpr ctx type
    let assignment? ← getExprMVarAssignment? id
    let status :=
      if assignment?.isSome then "synthesized"
      else if (match decl.kind with | .syntheticOpaque => true | _ => false) then "pending"
      else "pending"
    pure (some (obj [
      ("obligation_id", Json.str ("tc_" ++ hashString (mvarIdString id))),
      ("mvar_id", Json.str (mvarIdString id)),
      ("class_head", Json.str classHeadString),
      ("target_expr_id", Json.str typeId),
      ("arguments", jsonArr ((type.getAppArgs.toList.map fun a => Json.str (exprIdOf a)))),
      ("local_instances", jsonArr ((decl.localInstances.toList.map fun inst => Json.str (toString inst.className)))),
      ("status", Json.str status),
      ("messages", jsonArr [])
    ]))

/-! ## M2: proof-term minimal support

After a tactic application SUCCEEDS (a goal mvar becomes assigned), the
instantiated assignment is a proof term whose free fvars name exactly the
hypotheses the proof actually used — the anti-overfit canonicalization gauge
for the S6 lemma foundry and the exact rung of the M1 reuse ladder. -/

def maxUsedConstants : Nat := 64

partial def collectConstNames (e : Expr) (acc : Std.HashSet Name := {}) : Std.HashSet Name :=
  match e with
  | .const n _ => acc.insert n
  | .app f a => collectConstNames a (collectConstNames f acc)
  | .lam _ t b _ => collectConstNames b (collectConstNames t acc)
  | .forallE _ t b _ => collectConstNames b (collectConstNames t acc)
  | .letE _ t v b _ => collectConstNames b (collectConstNames v (collectConstNames t acc))
  | .mdata _ x => collectConstNames x acc
  | .proj n _ x => collectConstNames x (acc.insert n)
  | _ => acc

def lctxDeclCount (lctx : LocalContext) : Nat :=
  lctx.foldl (fun n _ => n + 1) 0

/-- Dependency closure of a seed fvar set inside one local context: a used
hypothesis drags in the fvars occurring in its type (and value, for let
declarations), transitively.  The outer loop runs |lctx|+1 times, which bounds
any dependency chain, so the fixpoint is reached without a termination proof. -/
def fvarSupportClosure (lctx : LocalContext) (seed : List FVarId) : Std.HashSet FVarId := Id.run do
  let mut support : Std.HashSet FVarId := {}
  for id in seed do
    if lctx.contains id then
      support := support.insert id
  for _ in [0:lctxDeclCount lctx + 1] do
    for id in support.toList do
      match lctx.find? id with
      | some d =>
          let exprs := match d.value? (allowNondep := true) with
            | some v => [d.type, v]
            | none => [d.type]
          let deps := exprs.foldl (fun s e => collectFVars e s) ({} : Std.HashSet FVarId)
          for dep in deps.toList do
            if lctx.contains dep then
              support := support.insert dep
      | none => pure ()
  return support

def emptyMinimalSupport : Json := obj [
  ("schema_version", Json.str minimalSupportVersion),
  ("goals", jsonArr []),
  ("source", Json.str "lean_kernel_rpc_proof_term_v1")
]

/-- Minimal support of one just-assigned goal mvar: instantiate its assignment
and report (a) `used_hypotheses` — the goal-lctx fvars occurring in the proof
term expanded to their dependency closure, in local-context order, and (b)
`used_constants` — the constants the proof references, sorted, bounded to
`maxUsedConstants`.  Returns `none` when the mvar is unknown or unassigned. -/
def minimalSupportForGoal (g : MVarId) : MetaM (Option Json) := do
  let mctx ← getMCtx
  match mctx.decls.find? g with
  | none => pure none
  | some decl => do
      let proof ← instantiateMVars (mkMVar g)
      if proof == mkMVar g then
        pure none
      else
        let lctx := decl.lctx
        let seed := (collectFVars proof).toList.filter (fun id => lctx.contains id)
        let support := fvarSupportClosure lctx seed
        let mut hyps : Array Json := #[]
        for d in lctx do
          if support.contains d.fvarId then
            let typeText ←
              try
                withLCtx lctx decl.localInstances do
                  pure (truncateText (toString (← ppExpr (← instantiateMVars d.type))))
              catch _ =>
                pure (truncateText (toString (repr d.type)))
            hyps := hyps.push (obj [
              ("fvar_id", Json.str (localDeclId d)),
              ("user_name", Json.str (toString d.userName)),
              ("type_text", Json.str typeText),
              ("is_implementation_detail", Json.bool d.isImplementationDetail)
            ])
        let constNames := ((collectConstNames proof).toList.map toString).toArray.qsort
          (fun a b => decide (a < b))
        let residual := collectMVars proof
        pure (some (obj [
          ("mvar_id", Json.str (mvarIdString g)),
          ("used_hypotheses", Json.arr hyps),
          ("used_constants", jsonArr ((constNames.toList.take maxUsedConstants).map Json.str)),
          ("n_constants_total", Json.num constNames.size),
          ("constants_truncated", Json.bool (decide (constNames.size > maxUsedConstants))),
          ("residual_mvars", jsonArr (mvarStrings residual)),
          ("fully_closed", Json.bool residual.isEmpty),
          ("proof_hash_raw", Json.str (hashString (rawExprSig proof)))
        ]))

structure KState where
  id : String
  env : Environment
  opts : Options
  coreState : Core.State
  metaState : Meta.State
  termState : Term.State
  goals : List MVarId
  task : Json
  proofPrefix : String
  parent? : Option String := none
  status : String := "open"
  minimalSupport : Json := emptyMinimalSupport

structure TargetBinding where
  target : MVarId
  index : Nat
  requestedMVar? : Option String
  requestedSelector? : Option String
  source : String

structure WorkerState where
  sessionId : String
  states : Std.HashMap String KState := {}
  nextId : Nat := 0
  loaded : Bool := false
  defaultEnv? : Option Environment := none
  opts : Options := {}
  imports : List String := defaultImports
  nRequests : Nat := 0
  nFailures : Nat := 0
  nPrimaryExecutions : Nat := 0
  nReplayExecutions : Nat := 0

abbrev WRef := IO.Ref WorkerState

/-- Lean's option unit used by the frozen U05 task/prefix/action contract.  The
worker protocol and the legacy structured-state schema stay unchanged; the
effective value is echoed by `kernel_state.options.maxHeartbeats`. -/
def u05MaxHeartbeatsOption : Nat := 20000

def defaultMaxHeartbeatsOption : Nat := 200000

def taskMaxHeartbeats? (ks : KState) : Option Nat :=
  jsonGetNat? ks.task "max_heartbeats"

def stateMaxHeartbeats (ks : KState) : Nat :=
  ks.opts.get `maxHeartbeats defaultMaxHeartbeatsOption

/-- A task-declared cap is part of the persistent KState contract.  Checking it
at serialization and status boundaries prevents a later project/default option
from silently replacing the cap used for task-prefix elaboration. -/
def heartbeatCapInvariantError? (ks : KState) : Option String :=
  match taskMaxHeartbeats? ks with
  | none => none
  | some declared =>
      let effective := stateMaxHeartbeats ks
      if effective == declared then none
      else some ("state " ++ ks.id ++ " declares max_heartbeats=" ++ toString declared ++
        " but stores maxHeartbeats=" ++ toString effective)

def firstHeartbeatCapInvariantError? : List (String × KState) → Option String
  | [] => none
  | (_, ks) :: rest =>
      match heartbeatCapInvariantError? ks with
      | some e => some e
      | none => firstHeartbeatCapInvariantError? rest

def ensureHeartbeatCapInvariant (where_ : String) (ks : KState) : IO Unit := do
  match heartbeatCapInvariantError? ks with
  | none => pure ()
  | some e => throw <| IO.userError (where_ ++ ": heartbeat cap invariant failed: " ++ e)

def isU05HeartbeatState (ks : KState) : Bool :=
  taskMaxHeartbeats? ks == some u05MaxHeartbeatsOption

def ensureU05ActionCap (base : KState) (action : Json) : IO Unit := do
  if isU05HeartbeatState base then
    match jsonGetNat? action "max_heartbeats" with
    | some requested =>
        if requested != u05MaxHeartbeatsOption then
          throw <| IO.userError ("U05 cap mismatch: action requested " ++
            toString requested ++ " but task/prefix cap is " ++
            toString u05MaxHeartbeatsOption)
    | none => pure ()

def freshId (st : WorkerState) (tag : String := "krpc_state") : String × WorkerState :=
  (tag ++ "_" ++ toString st.nextId, {st with nextId := st.nextId + 1})

def coreCtx (_env : Environment) (opts : Options) (input : String := "") : Core.Context := {
  fileName := "<lean-rgc-kernel-rpc>",
  fileMap := FileMap.ofString input,
  options := opts
}

def termCtx : Term.Context := {}
def metaCtx : Meta.Context := {}

def prefixTacticLines (s : String) : List String :=
  (s.splitOn "\n").map (fun l => toString l.trimAscii) |>.filter (fun l => !l.isEmpty)

def goalAt? : List MVarId → Nat → Option MVarId
  | [], _ => none
  | g :: _, 0 => some g
  | _ :: gs, n + 1 => goalAt? gs n

def findGoalByString? (goals : List MVarId) (needle : String) : Option (Nat × MVarId) :=
  let rec go (rest : List MVarId) (index : Nat) : Option (Nat × MVarId) :=
    match rest with
    | [] => none
    | g :: gs =>
        if mvarIdString g == needle then some (index, g)
        else go gs (index + 1)
  go goals 0

def targetBindingJson (binding : TargetBinding) : Json :=
  obj [
    ("requested_target_mvar_id", jsonStrOrNull binding.requestedMVar?),
    ("requested_target_selector", jsonStrOrNull binding.requestedSelector?),
    ("effective_target_mvar_id", Json.str (mvarIdString binding.target)),
    ("effective_target_goal_index", Json.num binding.index),
    ("source", Json.str binding.source)
  ]

def unresolvedTargetBindingJson (requestedMVar? requestedSelector? : Option String) : Json :=
  obj [
    ("requested_target_mvar_id", jsonStrOrNull requestedMVar?),
    ("requested_target_selector", jsonStrOrNull requestedSelector?),
    ("effective_target_mvar_id", Json.null),
    ("effective_target_goal_index", Json.null),
    ("source", Json.str "unresolved")
  ]

def resolveTarget (base : KState) (action : Json) (requestTarget? : Option String) : Except String TargetBinding := do
  if base.goals.isEmpty then
    throw "target resolution failed: state has no open goals"
  let actionTarget? := jsonGetStr? action "target_mvar_id"
  let selector? := jsonGetStr? action "target_selector"
  let requestedMVar? ←
    match requestTarget?, actionTarget? with
    | some lhs, some rhs =>
        if lhs == rhs then pure (some lhs)
        else throw "target resolution failed: request/action target_mvar_id disagree"
    | some lhs, none => pure (some lhs)
    | none, some rhs => pure (some rhs)
    | none, none => pure none
  let resolved ←
    match requestedMVar? with
    | some raw =>
        match findGoalByString? base.goals raw with
        | some pair => pure pair
        | none => throw ("target resolution failed: target_mvar_id is not an open goal: " ++ raw)
    | none =>
        match selector? with
        | some "first" => pure (0, base.goals.head!)
        | some "last" =>
            let index := base.goals.length - 1
            match goalAt? base.goals index with
            | some g => pure (index, g)
            | none => throw "target resolution failed: last goal is unavailable"
        | some other => throw ("target resolution failed: unknown target_selector: " ++ other)
        | none => pure (0, base.goals.head!)
  let index := resolved.fst
  let goal := resolved.snd
  match selector? with
  | some "first" =>
      if index != 0 then
        throw "target resolution failed: target_mvar_id disagrees with target_selector=first"
  | some "last" =>
      if index + 1 != base.goals.length then
        throw "target resolution failed: target_mvar_id disagrees with target_selector=last"
  | some other => throw ("target resolution failed: unknown target_selector: " ++ other)
  | none => pure ()
  let source :=
    if requestTarget?.isSome then "request_target_mvar_id"
    else if actionTarget?.isSome then "action_target_mvar_id"
    else if selector?.isSome then "action_target_selector"
    else "legacy_default_first"
  pure {target := goal, index := index, requestedMVar? := requestedMVar?, requestedSelector? := selector?, source := source}

def effectiveOptions (base : KState) (action : Json) : Options :=
  /- U05 always executes from the cap stored by `initGoalState`; the explicit
  action field is an equality witness checked by `ensureU05ActionCap`, not a
  second control knob.  Non-U05 callers retain the legacy override behavior. -/
  if isU05HeartbeatState base then base.opts
  else
    match jsonGetNat? action "max_heartbeats" with
    | some hb => base.opts.set `maxHeartbeats hb
    | none => base.opts

def budgetJson (base : KState) (action : Json) : Json :=
  let requested := jsonGetNat? action "max_heartbeats"
  let effective : Nat := (effectiveOptions base action).get `maxHeartbeats 200000
  let effectiveCounter : Nat := effective * 1000
  obj [
    ("requested_max_heartbeats_option", jsonNatOrNull requested),
    ("effective_max_heartbeats_option", Json.num effective),
    ("effective_max_heartbeats_counter", if effective == 0 then Json.null else Json.num effectiveCounter),
    ("unlimited", Json.bool (effective == 0)),
    ("source", Json.str (if requested.isSome then "explicit_action" else "inherited_state")),
    ("cache_policy", Json.str "bypass"),
    ("cache_lookup_performed", Json.bool false),
    ("consumption_reported", Json.bool false),
    ("episode_budget", Json.str "NOT_ENFORCED_DEVELOPMENT_ONLY")
  ]

/-- Apply one tactic string to an explicitly resolved open goal, threading
Core/Meta/Term state and sweeping every goal assigned as a side effect. -/
unsafe def stepTacticAt (base : KState) (tactic : String) (opts : Options) (binding : TargetBinding) : IO KState := do
  let goal := binding.target
  let stx ←
    match Parser.runParserCategory base.env `tactic tactic with
    | .ok stx => pure stx
    | .error e => throw <| IO.userError e
  let run : MetaM (List MVarId × Term.State) := Lean.Elab.runTactic goal stx {} base.termState
  let ((newGoalsHead, termState'), coreState', metaState') ←
    run.toIO (coreCtx base.env opts tactic) {base.coreState with env := base.env} metaCtx {base.metaState with mctx := base.metaState.mctx}
  let candidates := base.goals.take binding.index ++ newGoalsHead ++ base.goals.drop (binding.index + 1)
  let mctx := metaState'.mctx
  let goals' := candidates.foldl (fun acc g =>
    if mctx.eAssignment.contains g then acc
    else if (mctx.decls.find? g).isNone then acc
    else if acc.contains g then acc
    else acc ++ [g]) []
  pure {base with
    env := coreState'.env,
    opts := opts,
    coreState := coreState',
    metaState := metaState',
    termState := termState',
    goals := goals',
    status := if goals'.isEmpty then "closed" else "open"}

/-- Legacy first-goal wrapper used only for frozen task-prefix tactics. -/
unsafe def stepTactic (base : KState) (tactic : String) (opts : Options) : IO KState := do
  match resolveTarget base (obj []) none with
  | .error e => throw <| IO.userError e
  | .ok binding => stepTacticAt base tactic opts binding

/-- Replay `task.prefix` tactic lines so the stored initial state is the
post-prefix state (mirrors how the persistent worker audits
`state.prefix + tactic`). -/
unsafe def replayPrefix (ks : KState) (proofPrefix : String) : IO KState := do
  let mut cur := ks
  ensureHeartbeatCapInvariant "prefix entry" cur
  for line in prefixTacticLines proofPrefix do
    if cur.goals.isEmpty then
      throw <| IO.userError ("prefix replay: no open goals before tactic '" ++ line ++ "'")
    let next ←
      try
        stepTactic cur line cur.opts
      catch e =>
        throw <| IO.userError ("prefix replay failed on '" ++ line ++ "': " ++ toString e)
    ensureHeartbeatCapInvariant "prefix step" next
    cur := next
  pure {cur with proofPrefix := proofPrefix}

unsafe def initGoalState (id : String) (task : Json) (env : Environment) (opts : Options) : IO KState := do
  let opts :=
    match jsonGetNat? task "max_heartbeats" with
    | some hb => opts.set `maxHeartbeats hb
    | none => opts
  let statement := jsonGetStr? task "statement" |>.getD "True"
  let cctx := coreCtx env opts statement
  let cstate : Core.State := { env := env }
  let mstate : Meta.State := {}
  let tstate : Term.State := {}
  let stx ←
    match Parser.runParserCategory env `term statement with
    | .ok stx => pure stx
    | .error e => throw <| IO.userError e
  let make : Term.TermElabM (Expr × MVarId) := do
    let ty ← Term.elabType stx
    let mv ← mkFreshExprMVar (some ty)
    pure (ty, mv.mvarId!)
  let ((_ty, mvarId), cstate', mstate', tstate') ←
    make.toIO cctx cstate metaCtx mstate termCtx tstate
  let proofPrefix := jsonGetStr? task "prefix" |>.getD ""
  let base : KState := {
    id := id,
    env := cstate'.env,
    opts := opts,
    coreState := cstate',
    metaState := mstate',
    termState := tstate',
    goals := [mvarId],
    task := task,
    proofPrefix := "",
    status := "open"
  }
  ensureHeartbeatCapInvariant "init_state" base
  let result ←
    if (prefixTacticLines proofPrefix).isEmpty then
      pure base
    else
      replayPrefix base proofPrefix
  ensureHeartbeatCapInvariant "init_state result" result
  pure result

unsafe def serializeKernelState (ks : KState) : IO Json := do
  ensureHeartbeatCapInvariant "kernel_state" ks
  let serialize : MetaM Json := do
    let openGoals := ks.goals
    let mctx ← getMCtx
    let declEntries := (mctx.decls.toList.toArray.qsort (fun a b => a.snd.index < b.snd.index)).toList
    let mvarOrder := declEntries.map Prod.fst
    let mut ser : ExprSerState := {}
    let mut goalObjs : Array Json := #[]
    let mut lctxObjs : Array Json := #[]
    let mut allMVarObjs : Array Json := #[]
    let mut tcObjs : Array Json := #[]
    let mut roots : Array String := #[]
    for pair in openGoals.toArray.mapIdx (fun i g => (i, g)) do
      let idx := pair.fst
      let gid := pair.snd
      if let some decl := mctx.decls.find? gid then
        let lctx := decl.lctx
        let nctx := mkNormCtx lctx mvarOrder
        let graphId := "lctx_" ++ hashString (ks.id ++ "_" ++ toString idx)
        let ((targetId, lctxJson), ser') ←
          ((do
            let tid ← serializeExpr nctx decl.type
            let lc ← serializeLocalContext graphId lctx decl.localInstances nctx
            pure (tid, lc)) : SerM (String × Json)).run ser
        ser := ser'
        roots := roots.push targetId
        lctxObjs := lctxObjs.push lctxJson
        let targetSyms := collectFVars decl.type |>.toList.map (fun id => Json.str (toString id.name))
        let raw := toString (repr decl.type)
        let (targetText, _) ← mvarTypeReadout decl
        goalObjs := goalObjs.push (obj [
          ("goal_id", Json.str ("g" ++ toString idx)),
          ("mvar_id", Json.str (mvarIdString gid)),
          ("target_text", Json.str targetText),
          ("target_expr_id", Json.str targetId),
          ("target_head", Json.str (exprHeadString decl.type)),
          ("relation", Json.str (relationOf decl.type)),
          ("local_context_graph_id", Json.str graphId),
          ("target_symbols", jsonArr targetSyms),
          ("domain_tags", jsonArr ((domainTagsReadout decl.type).map Json.str)),
          ("connective_counts", connectiveCounts decl.type),
          ("carrier_atoms_readout", jsonArr ((carrierAtomsReadout decl.type).map Json.str)),
          ("raw_hash", Json.str (hashString raw)),
          ("norm_hash", Json.str (hashString (normExprSig nctx decl.type)))
        ])
    for entry in declEntries do
      let mid := entry.fst
      let decl := entry.snd
      let nctx := mkNormCtx decl.lctx mvarOrder
      let (mjson, ser') ← (mvarDeclJson mid decl nctx).run ser
      ser := ser'
      allMVarObjs := allMVarObjs.push mjson
      let (tc?, ser'') ← (typeclassObligationJson mid decl nctx).run ser
      ser := ser''
      match tc? with
      | some tc => tcObjs := tcObjs.push tc
      | none => pure ()
    let graph := obj [
      ("schema_version", Json.str "lean-rgc-expr-graph-v1"),
      ("nodes", Json.arr ser.nodes),
      ("edges", Json.arr ser.edges),
      ("roots", Json.arr (roots.map Json.str)),
      ("source", Json.str "lean_kernel_rpc_expr_dag")
    ]
    let status := if ks.goals.isEmpty then "closed" else ks.status
    let rawHash := hashString (ks.id ++ toString (goalObjs.map toString) ++ toString (allMVarObjs.map toString))
    let normHash := hashString (toString (goalObjs.map (fun j => jsonGetStr? j "norm_hash")) ++ toString (allMVarObjs.map (fun j => jsonGetStr? j "norm_hash")))
    pure (obj [
      ("schema_version", Json.str schemaVersion),
      ("extraction_backend", Json.str "lean_kernel_rpc_in_memory_v1"),
      ("state_id", Json.str ks.id),
      ("task_id", Json.str (jsonGetStr? ks.task "task_id" |>.getD ks.id)),
      ("env_fingerprint", Json.str (hashString (toString ks.env.header.moduleNames ++ toString (importsFrom ks.task)))),
      ("state_hash_raw", Json.str rawHash),
      ("state_hash_norm", Json.str normHash),
      ("status", Json.str status),
      ("goals", Json.arr goalObjs),
      ("expr_graph", graph),
      ("local_contexts", Json.arr lctxObjs),
      ("local_context", obj [
        ("nodes", jsonArr []),
        ("edges", jsonArr []),
        ("source", Json.str "see_local_contexts")
      ]),
      ("metavars", Json.arr allMVarObjs),
      ("typeclasses", Json.arr tcObjs),
      ("messages", jsonArr []),
      ("options", obj [
        ("maxHeartbeats", Json.str (toString (stateMaxHeartbeats ks)))
      ]),
      ("proof_prefix_hash", Json.str (hashString ks.proofPrefix)),
      ("proof_prefix", Json.str ks.proofPrefix),
      ("parent_state_id", match ks.parent? with | some p => Json.str p | none => Json.null),
      ("object_coverage", obj [
        ("expr_ast", Json.bool true),
        ("local_decl_graph", Json.bool true),
        ("metavariable_graph", Json.bool true),
        ("typeclass_graph", Json.bool true),
        ("in_memory_state_id", Json.bool true),
        ("tactic_transition_api", Json.bool true),
        ("branch_rollback", Json.bool true),
        ("replay_certificate", Json.bool true),
        ("minimal_support", Json.bool true),
        ("source", Json.str "lean_kernel_rpc")
      ]),
      ("minimal_support", ks.minimalSupport),
      ("closed", Json.bool ks.goals.isEmpty),
      ("canonical_status", Json.str "kernel_structured_state_chart_not_canonical")
    ])
  let cctx := coreCtx ks.env ks.opts
  let (payload, _, _) ← serialize.toIO cctx ks.coreState metaCtx ks.metaState
  pure payload

/-- Run `minimalSupportForGoal` for every goal closed by a transition inside
the post-tactic Core/Meta state.  Extraction failures never fail the
transition: they degrade to an empty support object carrying `error`. -/
def minimalSupportJson (ks : KState) (closedGoals : List MVarId) : IO Json := do
  if closedGoals.isEmpty then
    pure emptyMinimalSupport
  else
    let compute : MetaM Json := do
      let mut goalObjs : Array Json := #[]
      for g in closedGoals do
        try
          match ← minimalSupportForGoal g with
          | some j => goalObjs := goalObjs.push j
          | none => pure ()
        catch _ => pure ()
      pure (obj [
        ("schema_version", Json.str minimalSupportVersion),
        ("goals", Json.arr goalObjs),
        ("source", Json.str "lean_kernel_rpc_proof_term_v1")
      ])
    try
      let cctx := coreCtx ks.env ks.opts
      let (j, _, _) ← compute.toIO cctx ks.coreState metaCtx ks.metaState
      pure j
    catch e =>
      pure (obj [
        ("schema_version", Json.str minimalSupportVersion),
        ("goals", jsonArr []),
        ("source", Json.str "lean_kernel_rpc_proof_term_v1"),
        ("error", Json.str (toString e))
      ])

partial def stripReplayTransport : Json → Json
  | Json.obj kvs =>
      Json.mkObj <| kvs.toList.filterMap fun kv =>
        let key := kv.fst
        if key == "state_id" || key == "parent_state_id" ||
            key == "state_hash_raw" || key == "state_hash_norm" ||
            key == "graph_id" || key == "local_context_graph_id" then
          none
        else
          some (key, stripReplayTransport kv.snd)
  | Json.arr xs => Json.arr (xs.map stripReplayTransport)
  | other => other

def jsonExactEq (lhs rhs : Json) : Bool :=
  Json.compress lhs == Json.compress rhs

def mvarsOf (ks : KState) : List MVarId :=
  ks.metaState.mctx.decls.toList.map Prod.fst

def assignedMvarsOf (ks : KState) : List MVarId :=
  (mvarsOf ks).filter fun m => ks.metaState.mctx.eAssignment.contains m

def mvarIdJson (xs : List MVarId) : Json :=
  jsonArr (xs.map (fun m => Json.str (mvarIdString m)))

structure TransitionExecution where
  child : KState
  delta : Json
  targetBinding : Json
  budget : Json
  kernelState : Json
  comparable : Json

def transitionComparableJson
    (action childKernel delta targetBinding budget : Json)
    (status : String) : Json :=
  obj [
    ("semantic_status", Json.str status),
    ("post_kernel_state", stripReplayTransport childKernel),
    ("state_delta", stripReplayTransport delta),
    ("action_id", Json.str (jsonGetStr? action "action_id" |>.getD "")),
    ("target_binding", targetBinding),
    ("budget", budget),
    ("normalized_failure_class", Json.null)
  ]

unsafe def executeTacticCore
    (base : KState) (action : Json) (requestTarget? : Option String)
    (newId : String) : IO TransitionExecution := do
  ensureHeartbeatCapInvariant "apply source" base
  ensureU05ActionCap base action
  let binding ←
    match resolveTarget base action requestTarget? with
    | .ok binding => pure binding
    | .error e => throw <| IO.userError e
  let tactic := jsonGetStr? action "tactic" |>.getD ""
  let opts := effectiveOptions base action
  let beforeMvars := mvarsOf base
  let beforeAssigned := assignedMvarsOf base
  let stepped ← stepTacticAt base tactic opts binding
  ensureHeartbeatCapInvariant "apply result" stepped
  let afterMvars := mvarsOf stepped
  let afterAssigned := assignedMvarsOf stepped
  let newlyAssigned := afterAssigned.filter fun m => !(beforeAssigned.contains m)
  let closedGoals := base.goals.filter fun g => newlyAssigned.contains g
  let newGoals := stepped.goals.filter fun m => !(base.goals.contains m)
  let newMvars := afterMvars.filter fun m => !(beforeMvars.contains m)
  let minimalSupport ← minimalSupportJson stepped closedGoals
  let child : KState := {stepped with
    id := newId,
    proofPrefix := if base.proofPrefix.trimAscii.isEmpty then tactic else base.proofPrefix ++ "\n" ++ tactic,
    parent? := some base.id,
    minimalSupport := minimalSupport
  }
  let delta := obj [
    ("closed_goals", mvarIdJson closedGoals),
    ("new_goals", mvarIdJson newGoals),
    ("assigned_mvars", mvarIdJson newlyAssigned),
    ("new_mvars", mvarIdJson newMvars),
    ("before_goals", mvarIdJson base.goals),
    ("after_goals", mvarIdJson child.goals),
    ("before_mvars", mvarIdJson beforeMvars),
    ("after_mvars", mvarIdJson afterMvars),
    ("before_assigned_mvars", mvarIdJson beforeAssigned),
    ("after_assigned_mvars", mvarIdJson afterAssigned),
    ("minimal_support", minimalSupport)
  ]
  let targetBinding := targetBindingJson binding
  let budget := budgetJson base action
  let kernelState ← serializeKernelState child
  let status := if child.goals.isEmpty then "closed" else "open"
  let comparable := transitionComparableJson action kernelState delta targetBinding budget status
  pure ({
    child := child
    delta := delta
    targetBinding := targetBinding
    budget := budget
    kernelState := kernelState
    comparable := comparable
  } : TransitionExecution)

def replayCertificateJson
    (primaryComparable replayComparable : Json)
    (postStateMatch deltaMatch targetMatch capMatch : Bool)
    (error? : Option String := none) : Json :=
  let responseMatch := jsonExactEq primaryComparable replayComparable
  obj [
    ("schema_version", Json.str u05ReplayVersion),
    ("replay_status", Json.str (if responseMatch && postStateMatch && deltaMatch && targetMatch && capMatch then "verified" else "mismatch")),
    ("reexecution_performed", Json.bool true),
    ("verification_method", Json.str "fresh_from_immutable_before_state"),
    ("semantic_response_match", Json.bool responseMatch),
    ("post_state_match", Json.bool postStateMatch),
    ("delta_match", Json.bool deltaMatch),
    ("target_match", Json.bool targetMatch),
    ("cap_match", Json.bool capMatch),
    ("error", jsonStrOrNull error?),
    ("primary_comparable", primaryComparable),
    ("replay_comparable", replayComparable)
  ]

unsafe def successReplayCertificate
    (base : KState) (action : Json) (requestTarget? : Option String)
    (newId : String) (primary : TransitionExecution) : IO Json := do
  try
    let replay ← executeTacticCore base action requestTarget? newId
    pure <| replayCertificateJson primary.comparable replay.comparable
      (jsonExactEq (stripReplayTransport primary.kernelState) (stripReplayTransport replay.kernelState))
      (jsonExactEq primary.delta replay.delta)
      (jsonExactEq primary.targetBinding replay.targetBinding)
      (jsonExactEq primary.budget replay.budget)
  catch e =>
    pure <| replayCertificateJson primary.comparable Json.null false false false false (some (toString e))

def normalizedFailureClass (message : String) : String :=
  if (message.splitOn "heartbeat").length > 1 || (message.splitOn "maximum heartbeats").length > 1 then
    "heartbeat_exhaustion"
  else if (message.splitOn "target resolution failed").length > 1 then
    "target_resolution"
  else
    "ordinary_failure"

def failureComparableJson
    (base : KState) (action : Json) (requestTarget? : Option String)
    (beforeKernel : Json) (message : String) : Json :=
  let selector? := jsonGetStr? action "target_selector"
  let actionTarget? := jsonGetStr? action "target_mvar_id"
  let requestedMVar? := requestTarget?.orElse fun _ => actionTarget?
  let targetBinding :=
    match resolveTarget base action requestTarget? with
    | .ok binding => targetBindingJson binding
    | .error _ => unresolvedTargetBindingJson requestedMVar? selector?
  obj [
    ("semantic_status", Json.str (normalizedFailureClass message)),
    ("post_kernel_state", stripReplayTransport beforeKernel),
    ("state_delta", Json.null),
    ("action_id", Json.str (jsonGetStr? action "action_id" |>.getD "")),
    ("target_binding", targetBinding),
    ("budget", budgetJson base action),
    ("normalized_failure_class", Json.str (normalizedFailureClass message))
  ]

unsafe def failureReplayCertificate
    (base : KState) (action : Json) (requestTarget? : Option String)
    (newId : String) (beforeKernel : Json) (primaryMessage : String) : IO Json := do
  let primaryComparable := failureComparableJson base action requestTarget? beforeKernel primaryMessage
  try
    let replay ← executeTacticCore base action requestTarget? newId
    pure <| replayCertificateJson primaryComparable replay.comparable false false false
      (jsonExactEq (budgetJson base action) replay.budget)
      (some "primary failed but replay succeeded")
  catch e =>
    let replayMessage := toString e
    let replayComparable := failureComparableJson base action requestTarget? beforeKernel replayMessage
    let classMatch := normalizedFailureClass primaryMessage == normalizedFailureClass replayMessage
    pure <| replayCertificateJson primaryComparable replayComparable true classMatch true true
      (if classMatch then none else some replayMessage)

unsafe def applyTacticCore
    (base : KState) (action : Json) (requestTarget? : Option String)
    (newId : String) : IO (TransitionExecution × Json) := do
  let primary ← executeTacticCore base action requestTarget? newId
  let replay ← successReplayCertificate base action requestTarget? newId primary
  pure (primary, replay)

def unchangedDeltaJson (base : KState) : Json :=
  let mvars := mvarsOf base
  let assigned := assignedMvarsOf base
  obj [
    ("closed_goals", jsonArr []),
    ("new_goals", jsonArr []),
    ("assigned_mvars", jsonArr []),
    ("new_mvars", jsonArr []),
    ("before_goals", mvarIdJson base.goals),
    ("after_goals", mvarIdJson base.goals),
    ("before_mvars", mvarIdJson mvars),
    ("after_mvars", mvarIdJson mvars),
    ("before_assigned_mvars", mvarIdJson assigned),
    ("after_assigned_mvars", mvarIdJson assigned),
    ("minimal_support", emptyMinimalSupport)
  ]

def auditStatusFromTransitionStatus (s : String) : String :=
  if s == "success" then "success"
  else if s == "partial" then "partial"
  else if s == "timeout" then "timeout"
  else if s == "elab_error" then "elab_error"
  else "fail"

def failureTransitionStatus (failedStatus replayStatus : String) : String :=
  if replayStatus != "verified" then "censor"
  else if failedStatus == "timeout" then "timeout"
  else "failure"

def proofStateJson (ks : KState) : Json :=
  obj [
    ("state_id", Json.str ks.id),
    ("task_id", Json.str (jsonGetStr? ks.task "task_id" |>.getD ks.id)),
    ("goals_text", Json.str (if ks.goals.isEmpty then "" else toString (ks.goals.map mvarIdString))),
    ("local_context", Json.str ""),
    ("target", Json.str (jsonGetStr? ks.task "statement" |>.getD "")),
    ("raw_messages", jsonArr []),
    ("features", obj [])
  ]

def stateSummaryJson (ks : KState) : Json :=
  obj [
    ("state_id", Json.str ks.id),
    ("task_id", Json.str (jsonGetStr? ks.task "task_id" |>.getD ks.id)),
    ("status", Json.str (if ks.goals.isEmpty then "closed" else ks.status)),
    ("goal_count", Json.num ks.goals.length),
    ("parent_state_id", match ks.parent? with | some p => Json.str p | none => Json.null),
    ("proof_prefix", Json.str ks.proofPrefix),
    ("canonical_status", Json.str "lean_kernel_rpc_in_memory_state")
  ]

unsafe def handle (ref : WRef) (req : Json) : IO Json := do
  let cmd := jsonGetStr? req "cmd" |>.getD ""
  let st0 ← ref.get
  ref.set {st0 with nRequests := st0.nRequests + 1}
  match cmd with
  | "load_project" => do
      let imps :=
        match jsonGetStrArray? req "imports" with
        | some [] => defaultImports
        | some xs => xs
        | none => defaultImports
      try
        let env ← loadEnvForImports imps
        let st ← ref.get
        let st' := {st with loaded := true, defaultEnv? := some env, imports := imps}
        ref.set st'
        pure (ok [
          ("backend", Json.str "lean_kernel_rpc_in_memory_v1"),
          ("loaded", Json.bool true),
          ("imports", jsonArr (imps.map Json.str)),
          ("session_id", Json.str st'.sessionId),
          ("n_states", Json.num st'.states.size)
        ])
      catch e =>
        let st ← ref.get
        ref.set {st with nFailures := st.nFailures + 1}
        pure (err ("load_project failed: " ++ toString e))
  | "status" => do
      let st ← ref.get
      match firstHeartbeatCapInvariantError? st.states.toList with
      | some capError =>
          pure (err ("status heartbeat cap invariant failed: " ++ capError))
      | none =>
          /- Keep the legacy status field set byte-compatible.  The check
          above binds it to the effective values echoed by each v3
          `kernel_state.options.maxHeartbeats` record. -/
          pure (ok [
            ("backend", Json.str "lean_kernel_rpc_in_memory_v1"),
            ("loaded", Json.bool st.loaded),
            ("session_id", Json.str st.sessionId),
            ("n_states", Json.num st.states.size),
            ("n_requests", Json.num st.nRequests),
            ("n_failures", Json.num st.nFailures),
            ("n_primary_executions", Json.num st.nPrimaryExecutions),
            ("n_replay_executions", Json.num st.nReplayExecutions),
            ("imports", jsonArr (st.imports.map Json.str))
          ])
  | "register_task" | "init_state" => do
      match jsonGetObj? req "task" with
      | none => pure (err "register_task requires task")
      | some task => do
          try
            let imps := importsFrom task
            let env ← loadEnvForImports imps
            let st ← ref.get
            let (sid, st1) := freshId st
            let ks ← initGoalState sid task env st.opts
            ref.set {st1 with loaded := true, defaultEnv? := some env, imports := imps, states := st1.states.insert sid ks}
            let kernel ← serializeKernelState ks
            pure (ok [("state", stateSummaryJson ks), ("kernel_state", kernel)])
          catch e =>
            let st ← ref.get
            ref.set {st with nFailures := st.nFailures + 1}
            pure (err ("register_task failed: " ++ toString e))
  | "get_state" => do
      let sid := jsonGetStr? req "state_id" |>.getD ""
      match (← ref.get).states.get? sid with
      | some ks => pure (ok [("state", stateSummaryJson ks), ("kernel_state", ← serializeKernelState ks)])
      | none => pure (err ("unknown state_id: " ++ sid))
  | "kernel_state" | "structured_state" => do
      let sid := jsonGetStr? req "state_id" |>.getD ""
      match (← ref.get).states.get? sid with
      | some ks => pure (ok [("kernel_state", ← serializeKernelState ks)])
      | none => pure (err ("unknown state_id: " ++ sid))
  | "list_states" => do
      let states := (← ref.get).states.toList.map fun kv => stateSummaryJson kv.snd
      pure (ok [("states", jsonArr states)])
  | "discard_state" => do
      let sid := jsonGetStr? req "state_id" |>.getD ""
      let st ← ref.get
      match st.states.get? sid with
      | none => pure (err ("unknown state_id: " ++ sid))
      | some _ =>
          let before := st.states.size
          let states := st.states.erase sid
          ref.set {st with states := states}
          pure (ok [
            ("u05_semantics_version", Json.str u05SemanticsVersion),
            ("state_id", Json.str sid),
            ("discarded", Json.bool true),
            ("n_states_before", Json.num before),
            ("n_states_after", Json.num states.size)
          ])
  | "branch_state" => do
      let sid := jsonGetStr? req "state_id" |>.getD ""
      match (← ref.get).states.get? sid with
      | none => pure (err ("unknown state_id: " ++ sid))
      | some ks => do
          let st ← ref.get
          let (bid, st1) := freshId st "krpc_branch"
          let child := {ks with id := bid, parent? := some sid}
          ref.set {st1 with states := st1.states.insert bid child}
          pure (ok [
            ("new_state_id", Json.str bid),
            ("parent_state_id", Json.str sid),
            ("state", stateSummaryJson child),
            ("kernel_state", ← serializeKernelState child)
          ])
  | "rollback_state" => do
      let sid := jsonGetStr? req "state_id" |>.getD ""
      match (← ref.get).states.get? sid with
      | none => pure (err ("unknown state_id: " ++ sid))
      | some ks =>
          match ks.parent? with
          | some pid =>
              match (← ref.get).states.get? pid with
              | some parent => pure (ok [("state", stateSummaryJson parent), ("kernel_state", ← serializeKernelState parent)])
              | none => pure (ok [("state", stateSummaryJson ks), ("kernel_state", ← serializeKernelState ks)])
          | none => pure (ok [("state", stateSummaryJson ks), ("kernel_state", ← serializeKernelState ks)])
  | "apply_tactic" => do
      let action := jsonGetObj? req "action" |>.getD Json.null
      let actionId := jsonGetStr? action "action_id" |>.getD (hashString (jsonGetStr? action "tactic" |>.getD ""))
      let requestTarget? := jsonGetStr? req "target_mvar_id"
      let sid? := jsonGetStr? req "state_id"
      let base? ←
        match sid? with
        | some sid => pure ((← ref.get).states.get? sid)
        | none =>
            match jsonGetObj? req "task" with
            | none => pure none
            | some task => do
                let imps := importsFrom task
                let env ← loadEnvForImports imps
                let st ← ref.get
                let (sid, st1) := freshId st
                let ks ← initGoalState sid task env st.opts
                ref.set {st1 with loaded := true, defaultEnv? := some env, imports := imps, states := st1.states.insert sid ks}
                pure (some ks)
      match base? with
      | none => pure (err "apply_tactic requires state_id or task")
      | some base => do
          let beforeKernel ← serializeKernelState base
          let t0 ← IO.monoMsNow
          let st ← ref.get
          let (newId, st1) := freshId st
          let result ←
            try
              let (primary, replay) ← applyTacticCore base action requestTarget? newId
              pure (Except.ok (primary, replay))
            catch e =>
              let msg := toString e
              let failureClass := normalizedFailureClass msg
              let failed : KState := {base with
                id := newId
                parent? := some base.id
                status := if failureClass == "heartbeat_exhaustion" then "timeout" else "failed"
                minimalSupport := emptyMinimalSupport}
              let replay ← failureReplayCertificate base action requestTarget? newId beforeKernel msg
              let selector? := jsonGetStr? action "target_selector"
              let actionTarget? := jsonGetStr? action "target_mvar_id"
              let requestedMVar? := requestTarget?.orElse fun _ => actionTarget?
              let targetBinding :=
                match resolveTarget base action requestTarget? with
                | .ok binding => targetBindingJson binding
                | .error _ => unresolvedTargetBindingJson requestedMVar? selector?
              pure (Except.error (failed, msg, replay, targetBinding, budgetJson base action))
          let t1 ← IO.monoMsNow
          let stExec := {st1 with
            nPrimaryExecutions := st1.nPrimaryExecutions + 1
            nReplayExecutions := st1.nReplayExecutions + 1}
          match result with
          | .ok (primary, replay) =>
              let child := primary.child
              let delta := primary.delta
              let afterKernel := primary.kernelState
              let replayVerified := jsonGetStr? replay "replay_status" == some "verified"
              let status :=
                if !replayVerified then "censor"
                else if child.goals.isEmpty then "success"
                else "partial"
              if replayVerified then
                ref.set {stExec with states := stExec.states.insert child.id child}
              else
                ref.set {stExec with nFailures := stExec.nFailures + 1}
              let audit := obj [
                ("task_id", Json.str (jsonGetStr? child.task "task_id" |>.getD child.id)),
                ("state_id", Json.str base.id),
                ("action_id", Json.str actionId),
                ("status", Json.str (if replayVerified then auditStatusFromTransitionStatus status else "fail")),
                ("elapsed_ms", Json.num (t1 - t0)),
                ("heartbeats", Json.null),
                ("stdout", Json.str ""),
                ("stderr", Json.str ""),
                ("messages", jsonArr []),
                ("after_state", proofStateJson child),
                ("audit_flags", obj [
                  ("kernel_rpc_worker", Json.bool true),
                  ("execution_backend", Json.str "lean_kernel_rpc_in_memory_v1"),
                  ("kernel_state_before", beforeKernel),
                  ("kernel_state_after", afterKernel),
                  ("state_delta", delta),
                  ("replay", replay),
                  ("heartbeat_telemetry", primary.budget),
                  ("target_binding", primary.targetBinding),
                  ("before_persistent_state_id", Json.str base.id),
                  ("after_persistent_state_id", if replayVerified then Json.str child.id else Json.null)
                ])
              ]
              pure (ok [
                ("u05_semantics_version", Json.str u05SemanticsVersion),
                ("status", Json.str status),
                ("censor_reason", if replayVerified then Json.null else Json.str "replay_mismatch"),
                ("before_state_id", Json.str base.id),
                ("after_state_id", Json.str child.id),
                ("after_state_retained", Json.bool replayVerified),
                ("target_mvar_id", jsonGetObjVal? primary.targetBinding "effective_target_mvar_id" |>.getD Json.null),
                ("target_binding", primary.targetBinding),
                ("budget", primary.budget),
                ("state_delta", delta),
                ("kernel_state_before", beforeKernel),
                ("kernel_state_after", afterKernel),
                ("kernel_state", afterKernel),
                ("state", stateSummaryJson child),
                ("audit", audit),
                ("replay", replay),
                ("replay_certificate", replay),
                ("messages", jsonArr []),
                ("elapsed_ms", Json.num (t1 - t0)),
                ("heartbeats", Json.null)
              ])
          | .error (failed, msg, replay, targetBinding, budget) =>
              ref.set {stExec with nFailures := stExec.nFailures + 1}
              let afterKernel ← serializeKernelState failed
              let replayStatus := jsonGetStr? replay "replay_status" |>.getD "missing"
              let replayVerified := replayStatus == "verified"
              let status := failureTransitionStatus failed.status replayStatus
              let delta := unchangedDeltaJson base
              let audit := obj [
                ("task_id", Json.str (jsonGetStr? failed.task "task_id" |>.getD failed.id)),
                ("state_id", Json.str base.id),
                ("action_id", Json.str actionId),
                ("status", Json.str (if status == "timeout" then "timeout" else "fail")),
                ("elapsed_ms", Json.num (t1 - t0)),
                ("stdout", Json.str ""),
                ("stderr", Json.str msg),
                ("messages", jsonArr [Json.str msg]),
                ("after_state", proofStateJson failed),
                ("audit_flags", obj [
                  ("kernel_rpc_worker", Json.bool true),
                  ("execution_backend", Json.str "lean_kernel_rpc_in_memory_v1"),
                  ("kernel_state_before", beforeKernel),
                  ("kernel_state_after", afterKernel),
                  ("state_delta", delta),
                  ("replay", replay),
                  ("heartbeat_telemetry", budget),
                  ("target_binding", targetBinding),
                  ("before_persistent_state_id", Json.str base.id),
                  ("after_persistent_state_id", Json.null)
                ])
              ]
              let statusDetail :=
                if replayVerified then
                  [("normalized_failure_class", Json.str (normalizedFailureClass msg))]
                else
                  [("censor_reason", Json.str "replay_mismatch")]
              pure (ok ([
                ("u05_semantics_version", Json.str u05SemanticsVersion),
                ("status", Json.str status),
              ] ++ statusDetail ++ [
                ("before_state_id", Json.str base.id),
                ("after_state_id", Json.str failed.id),
                ("after_state_retained", Json.bool false),
                ("target_mvar_id", jsonGetObjVal? targetBinding "effective_target_mvar_id" |>.getD Json.null),
                ("target_binding", targetBinding),
                ("budget", budget),
                ("state_delta", delta),
                ("kernel_state_before", beforeKernel),
                ("kernel_state_after", afterKernel),
                ("kernel_state", afterKernel),
                ("state", stateSummaryJson failed),
                ("audit", audit),
                ("replay", replay),
                ("replay_certificate", replay),
                ("messages", jsonArr [Json.str msg]),
                ("elapsed_ms", Json.num (t1 - t0)),
                ("heartbeats", Json.null)
              ]))
  | "shutdown" => pure (ok [("shutdown", Json.bool true)])
  | _ => pure (err ("unknown cmd: " ++ cmd))

unsafe def handleLine (ref : WRef) (line : String) : IO Json := do
  match Json.parse line with
  | .error e =>
      pure (responseEnvelope Json.null (err ("json parse error: " ++ e)))
  | .ok req => do
      let rep ← handle ref req
      pure (responseEnvelope (requestIdJson req) rep)

unsafe def loop (ref : WRef) : IO Unit := do
  let stdin ← IO.getStdin
  let stdout ← IO.getStdout
  let rec go : IO Unit := do
    let line ← stdin.getLine
    if line.trimAscii.isEmpty then go else
      let rep ← handleLine ref line
      stdout.putStrLn (Json.compress rep)
      stdout.flush
      if jsonGetBool? rep "shutdown" |>.getD false then pure () else go
  try go catch _ => pure ()

partial def argAfter (args : List String) (name : String) : Option String :=
  match args with
  | [] => none
  | x :: y :: rest => if x == name then some y else argAfter (y :: rest) name
  | _ :: rest => argAfter rest name

end KernelRPC
end RGCLean

unsafe def main (args : List String) : IO Unit := do
  let imports :=
    match RGCLean.KernelRPC.argAfter args "--imports" with
    | some s => if s.trimAscii.isEmpty then RGCLean.KernelRPC.defaultImports else s.splitOn ","
    | none => RGCLean.KernelRPC.defaultImports
  let env? ←
    try
      let env ← RGCLean.KernelRPC.loadEnvForImports imports
      pure (some env)
    catch _ =>
      pure none
  let ref ← IO.mkRef ({
    sessionId := "lean_kernel_rpc_" ++ toString (← IO.monoMsNow),
    loaded := env?.isSome,
    defaultEnv? := env?,
    imports := imports
  } : RGCLean.KernelRPC.WorkerState)
  RGCLean.KernelRPC.loop ref
