import Lake
open Lake DSL

package «lean_rgc_template» where
  -- A tiny Lake project template for Lean-RGC file-mode audits.

require mathlib from git
  "https://github.com/leanprover-community/mathlib4.git"

@[default_target]
lean_lib RGCLean where
