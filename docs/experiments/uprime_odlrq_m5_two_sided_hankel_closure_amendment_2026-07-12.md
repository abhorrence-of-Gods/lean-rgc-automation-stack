# U-prime / ODLRQ M5 two-sided Hankel-closure amendment

Status: **CONDITIONAL FREEZE BEFORE COMMIT, PUSH, M5 QUALIFICATION, AND ANY PROTECTED ENDPOINT**
Conditionally frozen at: `2026-07-12T14:50:42+09:00`
Accepted anchor before this amendment:
`9f67edeff33c77a756788c29023f693d1bad8ab8`
Parent lane-isolated amendment blob:
`955872dacb1ebfe6328a178797b68479ebc55069`
Parent CPU-survivor amendment blob:
`f3b991b42228b0f36acaf5aaad6572777aa76b5a`

## 1. Reason and evidence boundary

The M5 synthetic implementation audit found a specification-direction gap
before candidate qualification.  Section 6 of the lane-isolated amendment said
that incomplete `prefix closure` blocks a Hankel realization, but it did not
formally state the dual closure direction for a column whose key is a
right-hand suffix.  Interpreting a column word `v` as left-prefix-closed
(`v[:-1]`) makes an exact noncommutative continuation require either one dense
matrix product per column or one dense state update per row/column pair.  Those
procedures are respectively `O(nc*r^3)` or `O(nr*nc*r^2)` and are not bounded
by the frozen `W_H_pre` expression.

The diagnostic counterexample used only declared synthetic rational atoms.  No
Lean task result, held-out result, kill-probe endpoint, GPU result, LLM output,
or reserved evaluation split was read.  This amendment therefore repairs a
pre-execution engineering contract; it does not tune a scientific endpoint.

## 2. Frozen two-sided closure

The M5 language is henceforth closed in the standard two-sided Hankel sense.
For a task `t`, channel `c`, action symbols `a`, and words `u,v`:

```text
row prefix closure:    (t, u.a) present  => (t, u) present
column tail closure:   (a.v, c) present  => (v, c) present
roots:                 (t, epsilon) and (epsilon, c) are present
```

The column rule removes the first action, not the last action.  It does not
assert commutativity: for `v = a.b`, the required parent is `b`, and the
realization remains `A_a A_b beta_c`.

All response atoms retain the already-frozen split-invariant key

```text
ResponseAtomKey(t, u + v, c).
```

Target declaration, target-read exclusion, censor handling, semantic action
identity, exact rational arithmetic, and every numerical/resource cap are
unchanged.

## 3. Frozen construction and admission check

Let `I` and `J` be the deterministic lexicographic exact-rank basis rows and
columns, `C = H[I,J]`, and `r = r_train`.  M5 constructs and checks

```text
X       = H[:,J] C^-1
Y       = H[I,:]
H       = X Y                         (exact equality on every declared cell)
alpha_t = X[(t,epsilon)]
A_a     = H[I.a,J] C^-1
beta_c  = Y[(epsilon,c)]
X[u.a]  = X[u] A_a                    (every non-root row)
Y[a.v]  = A_a Y[v]                    (every non-root column)
```

Failure of factorization, either shift identity, a required root/tail, or a
basis action shift blocks construction.  By induction on the two closure
relations,

```text
H[(t,u),(v,c)] = alpha_t A_u A_v beta_c
```

for every declared training cell.  This is an admission check for the bounded
rational predictive capability; it is still synthetic development evidence
and is not an `ExactFiniteOperator` or hard Lean certificate.

## 4. Work-envelope adjudication

No cap or threshold changes.  The frozen preflight remains

```text
W_H_pre = nr*nc*min(nr,nc)
        + (na+1)*r_cap^3
        + (nt+nc_channels)*r_cap^2
        + n_targets*r_cap^2*max(1,max_target_word_length)
    <= 2,000,000.
```

The exact rank/cross and `H = X Y` checks use
`O(nr*nc*r)` rational operations.  Row and column shift checks use
`O((nr+nc)*r^2)`.  Since
`r <= r_cap <= min(nr,nc)`, each of `nr*r^2` and `nc*r^2` is bounded by
`nr*nc*min(nr,nc)`.  Action construction remains covered by
`(na+1)*r_cap^3`; task/channel vectors and target prediction remain covered by
the existing remaining terms.  There is no action-word replay and no history
tree allocation.

## 5. Mandatory regression set

The one fixed M5 module must now include all previous tests plus:

1. closure direction at depth two: `{epsilon,b,a.b}` is admissible while
   `{epsilon,a,a.b}` is rejected for a column language;
2. a rank-one row counterexample `H(epsilon)=1, H(a)=2, H(a.a)=99`, rejected by
   row shift consistency;
3. the dual rank-one column counterexample, rejected by column shift
   consistency;
4. a two-action noncommutative suffix counterexample that distinguishes
   `A_a A_b` from `A_b A_a`;
5. a positive nonempty-suffix realization and exact held-out residual;
6. a nonterminal-only target set whose report contains the present typed
   ablation without requiring absent terminal classes.

The last rule also removes an unregistered gate found in the same audit:
typed ablations are emitted for classes present in the frozen target set, and
`terminal_all` is emitted only when a closed- or sink-terminal target exists.
An absent class is not represented by a zero-denominator metric and does not
block an otherwise valid evaluation.

## 6. Topology and stopping rule

This section is the sole narrow successor to the parent clauses that otherwise
freeze the recovery-identity blob and stop the phase on an allowlist escape.
It authorizes exactly the two-path transition below; every other parent
identity, path, lane-order, quota, and stop rule remains in force.

This document and the recovery identity guard form one single-parent,
two-path control-plane correction commit.  Its sole parent is the already
accepted M4 commit
`9f67edeff33c77a756788c29023f693d1bad8ab8`, and its changed paths are exactly:

```text
docs/experiments/uprime_odlrq_m5_two_sided_hankel_closure_amendment_2026-07-12.md
tests/test_odlrq_lane_isolated_recovery_identity.py
```

Before that commit, the identity test accepts only scoped worktree dirt on
those two paths and pins the exact amendment-document blob.  After the commit,
the same test requires exactly one addition of this document, the raw parent
above, and the exact two-path diff.  The identity file cannot contain its own
future Git blob before it is committed; therefore the transition is
self-sealing: the parent identity blob is frozen, the correction commit's new
identity blob is read from that exact commit, and every M5/M6 descendant must
retain both that new identity blob and this document's blob exactly.

The correction is not an M4, M5, or M6 semantic commit and consumes no lane
quota.  The accepted M4 commit, its manifest append, its lane count, and the
nondecreasing M4--M6 ordering remain unchanged.  The correction precedes the
M5 candidate and becomes the new phase anchor after its own commit and hosted
CI are green.  M4 is complete at the fixed parent: no later M4 commit is
permitted, and semantic descendants proceed only in M5-then-M6 order.  The M5
implementation commit remains restricted to the already-frozen five paths:

```text
lean_rgc/odlrq/__init__.py
lean_rgc/odlrq/hankel_predictive.py
tests/test_odlrq_hankel_predictive.py
tools/run_uprime_wp4_h_recovery_tests.ps1
tests/tier_manifest.json
```

After this amendment is pushed, M5 receives one cold dedicated-runner
qualification, combined identity/manifest checks, candidate CI, and accepted
CI.  Any new mathematical closure rule, resource threshold, endpoint, data
source, GPU/SSH use, LLM use, or cross-lane dependency requires another dated
authorization; it may not be inferred from this correction.
