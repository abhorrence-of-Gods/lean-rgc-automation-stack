import Mathlib

/-!
Minimal Lean-RGC harness module.
The Python file-mode executor writes temporary theorem files; importing this
module pins Mathlib and gives a place for future structured state tracing.
-/

namespace RGCLean

def ok : True := by trivial

end RGCLean
