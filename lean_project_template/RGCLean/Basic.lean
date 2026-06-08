import Mathlib

namespace RGCLean

theorem sanity_nat_zero (n : Nat) : n + 0 = n := by
  simp

theorem sanity_list_length_append {α : Type} (xs ys : List α) : (xs ++ ys).length = xs.length + ys.length := by
  simp

end RGCLean
