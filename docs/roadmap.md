# Implementation Roadmap

## Objective

Move DriftGuard from a strong deterministic benchmark harness to a defensible, hiring-signal research artifact with real evaluation discipline and a clear path to live-model validation.

## Current status

- Phase A is complete.
- Phase B is started.
- Phase C is started.
- The public benchmark now contains 36 scenarios across `pilot`, `dev`, `validation`, and `test`.

## Phase A: Repo Truth And Governance Surface

### Goal

Make the public repository scientifically honest and operationally legible before adding more complexity.

### Deliverables

- reconcile public docs with the actual public benchmark state
- point reproducibility commands at current canonical result slices
- regenerate benchmark snapshot, technical report, and failure atlas from current artifacts
- tighten generated reporting so it reflects mixed-context slices honestly
- document the next execution phases and exit criteria

### Exit criteria

- no public doc still claims 24 scenarios
- no primary doc still points at superseded `validation_wave1` artifacts
- generated report language matches the actual result slice being summarized
- tests pass and benchmark lint remains clean

## Phase B: Evaluation Ladder Completion

### Goal

Close the main scientific-governance gap by adding the missing final evaluation layers.

### Deliverables

- add a public `test` split with balanced scenarios
- add final-evaluation manifests and one-shot execution policy
- keep `shadow_holdout` private but implement the proper loading and run-recording path
- document `dev -> validation -> test -> shadow_holdout` usage clearly
- extend benchmark coverage toward at least 40 scenarios before final selection

### Exit criteria

- the benchmark has a real public `test` split
- manifest policy distinguishes development, selection, test, and holdout stages cleanly
- final-eval artifacts are structurally separated from tuning artifacts
- hidden-run governance is explicit and enforced

## Phase C: Detector And Grader Tightening

### Goal

Make detector naming and methodology match what is actually implemented.

### Deliverables

- replace placeholder “calibrated ensemble” logic with an actual fitted/calibrated detector
- clarify or rename the current rubric detector if it remains deterministic
- add detector-calibration documentation and regression tests
- strengthen trace-grading outputs for drift-label, severity, and recoverability agreement

### Exit criteria

- detector names are not overstating what they do
- calibration artifacts are versioned and reproducible
- detector comparisons are methodologically defensible

## Phase D: Live-Model Execution Path

### Goal

Move from deterministic harness validation to actual model-backed evidence while preserving reproducibility.

### Deliverables

- add a provider-agnostic agent adapter interface
- keep the scripted agent as the deterministic baseline path
- make prompt packs executable, not just registered metadata
- run one cheap primary live-model path with the same trace schema
- reserve Anthropic runs for reduced final holdout validation

### Exit criteria

- one manifest can be executed on both scripted and live-model backends
- traces and result summaries stay schema-compatible across backends
- live-model runs are budgeted and reproducible enough for comparison

## Phase E: Human Calibration And Final Packaging

### Goal

Turn the benchmark into a strong external-facing research artifact.

### Deliverables

- collect two independent reviewer passes on the calibration set
- compute agreement and freeze the annotation rubric
- run final `validation`, `test`, and reduced holdout evaluations
- refresh the technical report, benchmark card, failure atlas, and reproducibility guide
- package the repo around one narrow, defensible claim

### Exit criteria

- real reviewer agreement numbers exist
- final claims are based on the full evaluation ladder
- the repo reads like a research-engineering artifact rather than a scaffold

## Decision Rules

- prefer causal clarity over polish
- do not broaden scope before the evaluation ladder is complete
- do not present deterministic findings as frontier-model findings
- do not add abstractions that are not yet exercised by experiments
