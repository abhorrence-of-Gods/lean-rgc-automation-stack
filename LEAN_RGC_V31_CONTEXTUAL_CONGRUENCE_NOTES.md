# Lean-RGC v31: Contextual Response Congruence Proxy

v31 adds finite contextual response fingerprints and action quotient-class mining.

The ideal operation-stable congruence is

```text
C1 ~ C2 iff R(A ∘ C1 ∘ B) = R(A ∘ C2 ∘ B) for all safe A,B.
```

The implementation is a finite chart proxy:

```text
responses.jsonl -> contextual fingerprints -> response congruence classes -> action quotient registry
```

New commands:

```bash
lean-rgc contextual-response-congruence \
  --responses audit/responses.jsonl \
  --out contextual_congruence
```

Pipeline / iterate:

```bash
lean-rgc pipeline ... --contextual-congruence
lean-rgc iterate ... --contextual-congruence
```

Artifacts:

```text
contextual_response_congruence_report.json
contextual_fingerprints.jsonl
response_congruence_classes.jsonl
response_congruence_representatives.jsonl
```

Status: finite contextual response congruence proxy only; not canonical without parent non-paid + dual certificate + least repair.
