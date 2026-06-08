# Lean-RGC v12 Notes: Coker-Driven Context Synthesis

This revision adds the first practical implementation step for the transition:

```text
human-designed chart universe
  -> response-mined quotient universe
  -> coker-driven proof-context synthesis
```

## New command

```bash
lean-rgc synthesize-from-coker \
  --base-responses responses.jsonl \
  --out-actions coker_synthesized_actions.jsonl \
  --out-report coker_synthesis_summary.json \
  --out-profiles coker_profiles.jsonl \
  --out-archetypes response_archetypes.jsonl \
  --out-atoms coker_mined_defects.json
```

The command:

1. groups audited responses by proof state;
2. computes a finite response-cone projection for each state;
3. extracts positive coker residual coordinates and normals;
4. mines response archetypes from audited actions;
5. re-tags useful archetypes as new auditable contexts when their mean response points in the coker-normal direction;
6. emits mined coker residual atom candidates as chart-level defect proposals.

All outputs are explicitly **witnesses/charts pending audit**, not canonical defects. Promotion still requires the POMS rule:

```text
parent non-paid + dual certificate + least repair.
```

## Outputs

- `out-actions`: auditable Lean `TacticAction` rows generated from coker residuals.
- `out-profiles`: per-state projection/residual profiles.
- `out-archetypes`: response-mined action archetypes.
- `out-atoms`: residual-coordinate defect atom candidates.
- `out-report`: summary statistics.

## Meaning

This is not yet fully automatic proof architecture generation. It is the first coker-normal bridge: instead of only using human-designed failure signatures and carrier templates, the system can now propose contexts from response residuals.

The current generator is conservative: it retrieves and re-tags already-audited action archetypes rather than inventing arbitrary Lean syntax. This keeps the implementation audit-safe while exposing the next layer to automate.
