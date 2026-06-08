# Lean-RGC v32: Contextual Probe Generation in the Loop

v32 adds finite contextual probe generation for approximating operation-stable response congruence.

The theoretical target is the contextual congruence

\[
C_1 \sim_R C_2 \iff \mathcal R(A\circ C_1\circ B)=\mathcal R(A\circ C_2\circ B) \quad \forall A,B.
\]

v31 mined congruence classes from existing response rows. v32 generates explicit `A∘C∘B`-style contextual probe actions, audits them, and can mine contextual response congruence from the resulting response rows.

All outputs are finite chart/witness artifacts. They are not canonical observables unless later promoted by POMS evidence: parent non-paid, dual certificate, and least repair.

## Pipeline flags

```bash
lean-rgc pipeline \
  --tasks examples/minimal_theorems.jsonl \
  --actions examples/core_tactics.jsonl \
  --out runs/v32_contextual \
  --dry-run \
  --contextual-probes \
  --contextual-probe-max-left 2 \
  --contextual-probe-max-right 2 \
  --contextual-probe-max-candidates 64 \
  --audit-contextual-probe-candidates \
  --contextual-probe-congruence \
  --contextual-probe-accept-coker \
  --contextual-probe-robust-coker-accept
```

## Iterate flags

```bash
lean-rgc iterate \
  --tasks examples/minimal_theorems.jsonl \
  --actions examples/core_tactics.jsonl \
  --out runs/v32_iter \
  --dry-run \
  --rounds 2 \
  --contextual-probes \
  --audit-contextual-probe-candidates \
  --contextual-probe-congruence \
  --contextual-probe-accept-coker \
  --contextual-probe-robust-coker-accept \
  --contextual-probe-merge-actions
```

## New artifacts

- `contextual_probes/contextual_probe_candidates.jsonl`
- `contextual_probes/contextual_probe_report.json`
- `contextual_probe_audit/responses.jsonl`
- `contextual_probe_action_report.json`
- `contextual_probes/contextual_probe_congruence/response_congruence_classes.jsonl`
- `contextual_probe_accepted_actions.jsonl`
- `contextual_probe_robust_accepted_actions.jsonl`
- `contextual_probe_robust_acceptance_report.json`

## Status

This is a finite contextual response congruence proxy. It samples a finite family of left/right contexts and therefore remains a chart of the true operation-stable quotient.
