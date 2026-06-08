# Lean-RGC v20: Action Geometry Registry

This release adds the first implementation of the Action Geometry / RGC Affine Semidirect System.

The main change is that actions can now be registered and searched by finite response geometry rather than by tactic name alone.

## New commands

### Build an action embedding registry

```bash
lean-rgc action-geometry-registry \
  --responses runs/round_00/audit/responses.jsonl \
  --actions examples/core_tactics.jsonl \
  --transitions runs/round_00/transitions.jsonl \
  --out runs/round_00/action_geometry.jsonl \
  --summary-out runs/round_00/action_geometry_summary.json
```

Each row contains:

- `response_embedding`: mean audited local response chart
- `carrier_embedding`: mean audited carrier response chart
- `gamma_scalar`, `gamma_diag`, `affine_bias`: small finite affine propagation chart from transitions
- `uncertainty`: response/carrier/count uncertainty proxy
- `cost_estimate`, `success_rate`, provenance metadata

The row is explicitly marked as a chart, not a canonical object.

### Retrieve actions by response / carrier normals

```bash
lean-rgc action-geometry-retrieve \
  --registry runs/round_00/action_geometry.jsonl \
  --response-normal '{"goal.eq": 1.0}' \
  --carrier-normal '{"missing_simp_lemma": 0.5}' \
  --out runs/round_00/action_geometry_selected.jsonl \
  --summary-out runs/round_00/action_geometry_selected_summary.json
```

Score:

```text
response_normal · response_embedding
+ carrier_normal · carrier_embedding
- tail_weight * tail_risk(gamma)
- cost_weight * cost
- uncertainty_weight * uncertainty
- audit_weight * audit_risk
```

### Audit affine cocycle / arithmetic composition charts

```bash
lean-rgc action-cocycle-audit \
  --registry runs/round_00/action_geometry.jsonl \
  --compositions compositions.jsonl \
  --out runs/round_00/action_cocycles.jsonl \
  --summary-out runs/round_00/action_cocycles_summary.json
```

A composition row can contain:

```json
{"a":"action_a", "b":"action_b", "ab":"composed_action"}
```

The audit checks finite-chart analogues of:

```text
r_ab ≈ r_a + r_b
gamma_ab ≈ gamma_b gamma_a
bias_ab ≈ gamma_b bias_a + bias_b
carrier_ab ≈ carrier_a + carrier_b
```

### Extract declared arithmetic teacher constraints

```bash
lean-rgc arithmetic-teacher-constraints \
  --actions actions.jsonl \
  --out teacher_constraints.jsonl \
  --summary-out teacher_constraints_summary.json
```

This emits constraints only from explicit action metadata such as:

```json
{"metadata":{"arith":{"expr":"a*(b+c)"}}}
```

or

```json
{"metadata":{"teacher_equiv":["other_action_id"]}}
```

## Theoretical status

The v20 registry is not a canonical action quotient yet. It is a finite action-geometry chart:

```text
E(a) = (r(a), Gamma(a), c(a), cost(a), uncertainty(a))
```

Tactic syntax is metadata. The primitive searched by the new commands is the audited action embedding.

Canonical promotion remains governed by POMS: parent obstruction non-paid + dual certificate + least repair.
