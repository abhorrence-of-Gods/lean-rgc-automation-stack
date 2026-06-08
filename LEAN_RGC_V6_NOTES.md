# Lean-RGC Automation Stack v0.6

This release connects focused carrier exposure and AutoDefectMiner to the candidate-generation loop.

## Added / stabilized

- `lean-rgc registry-candidates`: generate task-specific tactic candidates from a mined defect registry.
- `lean-rgc carrier-actions`: convert generated carrier contexts into auditable tactic actions.
- `lean-rgc merge-actions`: merge fixed, state-dependent, registry, and carrier-generated action charts.
- `lean-rgc state-ir`: write a structured proof-state IR chart from tasks or audits.
- `lean-rgc exposure-report`: summarize exposure prefixes and core actions in audited responses.
- `lean-rgc audit-defect-atoms`: score mined defect atoms after audit.
- Pipeline integration for:
  - state IR extraction,
  - exposure reports,
  - defect mining,
  - registry-guided candidates,
  - optional registry candidate audit,
  - carrier actions,
  - carrier coker,
  - gamma audit.

## Important status

This is still file-based and pilot-grade. The system now closes the loop:

```
state-dependent audit -> mine defect registry -> registry candidates -> optional micro-audit
```

Tactic labels and goal strings remain charts. The main objects are proof-state defects, response classes, carrier residuals, and quotient-safe generated contexts.
