# U' / ODLRQ theory errata v1

Status: FROZEN FOR THE T0 EXTENSION before its first execution. The Git commit
containing this file is the temporal anchor; its hash is recorded in the
post-execution log. This document repairs the theory source with raw SHA-256
`7E24F7D444A263792A3A717B1C26807D0A15626C2A11D8F38A1DCCB7DE69CD87`.

This is an errata record, not a claim that T0 has passed. Hard claims below are
finite-dimensional/operator statements. Sample estimates remain
statistical-only. When a stated hypothesis or a required provenance object is
missing, the implementation must return `OUT_OF_SCOPE` or an infinite bound;
absence of a counterexample is never a hard certificate.

## E1. Weighted compression and lifting

Replace the inconsistent combination in TeX 746--759 and 826--848 by one
coordinate convention. For positive layer weights `omega_n(T)`, define

```text
(C_{omega,n} x)_Q = sum_{T in Omega_{n,Q}} omega_n(T) x_T
(L_{mu,omega,n} z)_T = mu_{n,Q}(T) z_Q / omega_n(T),
```

where `mu_{n,Q}` is a probability law on the fiber. Then
`C_{omega,n} L_{mu,omega,n} = I`. For raw transfer `A_n`, define

```text
M_n(Q',Q) = sup_{T in Omega_{n,Q}}
  sum_{T' in Omega_{n+1,Q'}}
  |A_n(T',T)| omega_{n+1}(T') / omega_n(T)

K_{mu,n} = C_{omega,n+1} A_n L_{mu,omega,n}.
```

Under absolute convergence,

```text
|K_{mu,n} z| <= M_n |z|
```

componentwise for every fiber law `mu`. If `M^T w <= theta w`, with the norm
fixed as `||z||_{1,w} = sum_Q w_Q |z_Q|`, then
`||K_mu||_{1,w} <= theta`. A spectral-radius conclusion is licensed only for a
stationary finite square operator; finite nonstationary layers use products.

`T0-W` witness: `A=10`, `omega_source=100`, `omega_target=1`, and a point-mass
lifting. The old formula gives envelope `0.1` and reduced gain `10`. The repaired
lifting divides by `omega_source`, giving reduced gain `0.1`.

## E2. Conditional kernels and contextual projections

For coordinate kernels `C_{k<-j}=J_k^* J_j`, withdraw the unconditional
factorization at TeX 557--559. It is exact under an explicit Markov/sufficiency
condition such as

```text
R_0 independent of R_{j+1} conditional on R_j,
```

or an appropriate nested coarsening. Otherwise define

```text
delta_j = ||C_{j+1<-0} - C_{j+1<-j} C_{j<-0}||_{2->2}.
```

Because conditional-expectation kernels are contractions, the corresponding
multi-step factorization defect is bounded by the sum of the transported local
defects; no zero-defect claim is made without its separator witness.

For the TeX definition

```text
P_{v|S} = Pi_{G_{S union {v}}},
```

tower property gives

```text
P_{w|S,v} P_{v|S} = P_{v|S}
P_{v|S,w} P_{w|S} = P_{w|S}.
```

The two sides in TeX 574--576 are therefore equal only when the retained-
information projections themselves agree. The written order-independence
identity is withdrawn. If order-free pruning is intended, use a common coarse
projection in a decreasing filtration, or record the commutator defect
`||Pi_A Pi_B - Pi_B Pi_A||` explicitly.

`T0-P` witness: for independent uniform bits `X,Y`, response `f=2X-1`, and
`R0=X,R1=Y,R2=X`, the direct channel returns `f` while the adjacent product is
zero. The old contextual equality also compares `f` with zero. The repaired
chain refuses a Markov certificate for this fixture. A nested positive fixture
`R0=(X,Y), R1=X, R2=constant` satisfies direct/product equality.

## E3. Full conditional covariance

Replace the diagonal-only identity at TeX 1201--1203. With coefficients `a_v`
measurable under `H_R`, let

```text
A_{v|R} = Cov(zeta_v | H_R)
Gamma_{vw|R} = Cov(zeta_v, zeta_w | H_R).
```

Then

```text
Cov(sum_v a_v zeta_v | H_R)
  = sum_v a_v^2 A_{v|R}
  + sum_{v<w} a_v a_w (Gamma_{vw|R} + Gamma_{vw|R}^T).
```

The old diagonal expression is recovered only after proving both conditional
cross-orthogonality and the asserted local covariance sufficiency. Orthogonality
of a canonical martingale-difference sequence cannot be transported to
arbitrary tree nodes and a new conditioning algebra without proof.

`T0-C` witness: under trivial conditioning, set `zeta_1=zeta_2=Z` for centered
Rademacher `Z` and use unit coefficients. The full variance is `4`, the
diagonal-only value is `2`, and the cross contribution is `2`. Independent
`Z_1,Z_2` form the positive zero-cross-term fixture.

## E4. Projected similarity and the true target

Let `q_R:T->X_R`, projected value `U`, and bisimulation metric `d_*` be fixed.
The projected Lipschitz statement

```text
|U(x)-U(y)| <= d_*(x,y)
```

does not control the true target by itself. Require an independently certified
residual

```text
|V_true(T) - U(q_R(T))| <= e_R(T).
```

Only then may one conclude

```text
|V_true(T)-V_true(S)|
  <= e_R(T) + d_*(q_R(T),q_R(S)) + e_R(S).
```

Similarly, a projected majorant yields true safety only as
`V_true(T) <= U_+(q_R(T)) + e_R(T)`. A held-out residual is
statistical-only. Hard status requires a fiber supremum, structural path-tail
bound, or other all-domain certificate.

`T0-S` witness: two hidden states have the same quotient state, projected value
zero, and true values `+1` and `-1`. The projected distance is zero while the
true gap is two. Residuals `e_R=1` on each state make the repaired bound exact.

## E5. Typed operator telescoping

Withdraw the free scalar addition at TeX 1574--1596. Let common normed spaces
`X_0,...,X_m` and bounded maps `A_j, Ahat_j:X_{j-1}->X_j` be declared. For

```text
F = A_m ... A_1
Fhat = Ahat_m ... Ahat_1,
```

the exact telescoping identity is

```text
F-Fhat = sum_j
  A_m ... A_{j+1} (A_j-Ahat_j) Ahat_{j-1} ... Ahat_1.
```

Consequently,

```text
||F-Fhat|| <= sum_j
  (prod_{k>j} ||A_k||) ||A_j-Ahat_j||
  (prod_{k<j} ||Ahat_k||).
```

Every native projection, boundary, memory, similarity, true-target, and model
bound must have a typed bridge into this same target and norm. Former constants
such as `C_proj` are these explicit transport/operator norms, not free tuning
parameters. `epsilon_model` is admissible only with an independent artifact,
provenance record, and bound; otherwise its value is infinite and the joint
certificate is refused.

`T0-J` witness: over the real line, take `A_1=1`, `Ahat_1=0`, and
`A_2=Ahat_2=10`. Composite error is `10`; the untransported stage-error sum is
`1`, while the typed bound is `10`.

## E6. MaxEnt existence and operator scope

On a finite fiber, the reference law must be strictly positive on its declared
support. If the requested moment lies in the relative interior of the convex
hull of supported statistics, the KL minimizer is unique and has a finite
exponential-family parameterization. Uniqueness of the parameter and positive-
definite Hessian additionally require a minimal family. Boundary moments may
have a primal law without a finite parameter; outside-hull moments are
infeasible.

MaxEnt moment fit is not an operator-accuracy theorem. In weighted coordinates,
write the operator load as `a_Q(T)` so `K_mu(.,Q)=E_mu a_Q(T)`. If

```text
a_Q(T) = a_0 + B C_Q(T) + r(T),  sup_T ||r(T)|| <= eta,
```

and the true and MaxEnt laws match the registered moment, then
`||K_true-K_ME|| <= 2 eta`. With moment mismatch `delta_c`, the bound becomes
`2 eta + ||B|| delta_c`. Alternatively, a separately certified KL bound and
`sup_T ||a_Q(T)|| <= G` yield the Pinsker transport
`G sqrt(2 epsilon)`. The weighted envelope, not MaxEnt, remains the hard safety
source.

`T0-ME` witness: on two atoms, a constant statistic gives identical moments to
both point masses while a load taking values `1` and `0` has operator gap `1`.
The best constant approximation has `eta=1/2`, making `2 eta=1`. An indicator
statistic spanning the load is the positive `eta=0` fixture. The implementation
must also reject an outside-hull moment, distinguish a boundary moment from a
finite parameter, and detect duplicate-statistic Hessian singularity.

## E7. Finite-horizon memory and positive messages

For a finite-dimensional block decomposition with

```text
U(t)=P exp(tL) P,  V(t)=exp(tA)P,  K(s)=B exp(sD) C,
```

define finite-horizon growth constants

```text
M_A(T)=sup_{t<=T} ||exp(tA)||
M_U(T)=sup_{t<=T} ||P exp(tL)P||.
```

The Volterra identity gives

```text
||U(t)-V(t)||
  <= M_A(T) M_U(T) integral_0^t (t-s)||K(s)|| ds
  <= M_A(T) M_U(T) T mu(T),

mu(T)=integral_0^T ||K(s)|| ds.
```

This finite-horizon statement requires neither orthogonal exponential damping
nor spectral contraction. Infinite-horizon claims require a separately stated
decay assumption. For nonstationary positive layers, use the registered finite
product `M_{n+h-1}...M_n` and compare its maximum gain over the episode horizon
with the budget; do not infer transient control from the spectral radius of a
finite DAG.

`T0-H` witness: with `L=[[0,1],[1,0]]`, first-coordinate projection, and
`A=D=0,B=C=1`, the true error at `T=1` is `cosh(1)-1`, while the refined finite
bound is `cosh(1)/2`. No positive decay rate exists, so an infinite-horizon
certificate is refused. A gain-two nilpotent shift with `N` edges on an
`N+1`-dimensional chain has spectral radius zero but finite transient gain
`2^N`, providing the positive-layer regression.

## T0 disposition

The errata is accepted by the executable gate only if every fixture
`T0-W/P/C/S/J/ME/H` demonstrates both sides of its contract:

1. the legacy unconditional claim fails on the frozen negative witness; and
2. the repaired formula passes its positive fixture or explicitly refuses the
   negative witness because a named hypothesis/provenance object is absent.

No fixture may pass solely because all examples were declared out of scope.
The extension is registered in
`uprime_odlrq_t0_extension_preregistration.md`. Passing T0 licenses continued
U'0/U'1 repair only; it does not license K1--K4, U'2--U'5, or GPU construction.
