# Lean-RGC v33: Response Quotient Registry

v33 adds a finite response-quotient registry built from contextual response congruence classes.

The theoretical target is the operation-stable response congruence

\[
C_1 \sim_R C_2 \iff \mathcal R(A\circ C_1\circ B)=\mathcal R(A\circ C_2\circ B)\quad\forall A,B.
\]

The implementation remains a finite sampled chart: it consumes the contextual congruence classes produced by v31/v32 and writes an explicit

```text
action_id -> quotient_class_id -> representative_action_id
```

registry.  It is not canonical by itself; promotion still requires the POMS conditions: parent non-paid, dual certificate, and least repair.

## New CLI

Build a response quotient registry from a contextual congruence directory:

```bash
lean-rgc response-quotient-registry \
  --congruence-dir runs/round_00/contextual_probes/contextual_probe_congruence \
  --actions runs/round_00/_actions.jsonl \
  --out runs/round_00/response_quotient
```

Project an action file through the registry:

```bash
lean-rgc response-quotient-project-actions \
  --actions actions.jsonl \
  --registry runs/round_00/response_quotient/response_quotient_registry.json \
  --out projected_actions.jsonl
```

## Pipeline / iterate flags

```bash
--response-quotient-registry
--response-quotient-project-actions
--response-quotient-merge-actions
--response-quotient-merge-policy representatives|projected|all
```

The registry is built from contextual probe congruence when available, otherwise from base contextual congruence.  In iterate mode, representatives or projected actions can be merged into the next round action pool.

## Outputs

```text
response_quotient/response_quotient_registry.json
response_quotient/response_quotient_classes.jsonl
response_quotient/response_quotient_members.jsonl
response_quotient/response_quotient_representatives.jsonl
response_quotient/response_quotient_projection.jsonl
response_quotient_projected_actions.jsonl
```

## Status

This is a finite sampled quotient registry, not the full operation-stable quotient.  It upgrades contextual fingerprints into a reusable action-class registry, but still needs contextual closure audits, held-out validation, and POMS promotion before any class can be treated as canonical.
