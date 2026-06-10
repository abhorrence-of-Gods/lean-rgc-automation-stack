# Lean-RGC v34: Carrier Quotient Mining

v34 adds a first implementation of carrier algebra auto-generation in finite-chart form.

The goal is to move from hand-authored carrier atom labels to carrier quotient-coordinate candidates mined from carrier coker residuals:

```text
carrier residual -> carrier coker normal phi^C -> q_phi^C(c)=<phi^C,c> -> carrier quotient coordinate candidate
```

These outputs are not canonical carrier observables.  They are finite carrier-response chart candidates and remain witness-only until parent non-payment, a dual certificate, and least-repair evidence are supplied through POMS.

## New CLI

```bash
lean-rgc carrier-quotient \
  --responses runs/round_00/audit/responses.jsonl \
  --out runs/round_00/carrier_quotient \
  --validate
```

Alias:

```bash
lean-rgc carrier-quotient-mine --responses ... --out ...
```

Validation:

```bash
lean-rgc carrier-quotient-validate \
  --coordinates runs/round_00/carrier_quotient/carrier_quotient_coordinates.jsonl \
  --responses runs/round_00/audit/responses.jsonl \
  --out-report runs/round_00/carrier_quotient/carrier_quotient_validation_report.json \
  --out-rows runs/round_00/carrier_quotient/carrier_quotient_validation_rows.jsonl
```

## Pipeline / iterate flags

```bash
--carrier-quotient
--carrier-quotient-validate
--audit-carrier-quotient-candidates
--carrier-quotient-accept-coker
--carrier-quotient-robust-coker-accept
--carrier-quotient-merge-actions
--carrier-quotient-merge-policy robust-only|accepted-only|all
```

## Generated artifacts

```text
carrier_quotient/carrier_state_coker_normals.jsonl
carrier_quotient/carrier_quotient_coordinates.jsonl
carrier_quotient/carrier_quotient_action_scores.jsonl
carrier_quotient/carrier_quotient_candidates.jsonl
carrier_quotient/carrier_quotient_defect_registry.json
carrier_quotient/carrier_quotient_defect_atoms.jsonl
carrier_quotient/carrier_quotient_incidence_patches.jsonl
carrier_quotient/carrier_quotient_validation_rows.jsonl
carrier_quotient/carrier_quotient_validation_report.json
```

Optional audit / acceptance artifacts:

```text
carrier_quotient_audit/responses.jsonl
carrier_quotient_action_report.json
carrier_quotient_accepted_actions.jsonl
carrier_quotient_robust_accepted_actions.jsonl
```

## Interpretation

Before v34, the carrier universe was mainly seeded by hand-authored atoms such as `missing_simp_lemma`, `unintroduced_forall`, or `nat_arith_goal`.  v34 does not remove those seeds, but it adds a route for mining carrier-coordinate candidates from carrier coker residuals.

The mined coordinate is a linear finite-chart functional

```text
q_phi^C(c)=<phi^C,c>
```

on carrier-delta coordinates.  It can be used to generate candidate actions, incidence patches, and registry readouts, but it remains a chart/witness until validated and promoted by POMS.
