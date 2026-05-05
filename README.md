# DriftGuard

DriftGuard is a ledger-centric benchmark and reference harness for **task-intent drift** in long-running agents.

The project is intentionally narrow:

- It does **not** present itself as a general agent platform.
- It focuses on a single measurable failure mode: when an agent drifts away from the original task contract during a long workflow.
- It ships a **local, reproducible benchmark**, a **reference system**, and **research-facing artifacts** that are designed to be legible to evaluation and research-engineering teams.

## What exists in this repository today

This repository currently implements the **deterministic benchmark spine**, a **36-scenario public benchmark**, and the first round of **selection-quality local ablations**:

- Versioned schemas for contracts, ledgers, traces, checkpoints, prompts, and scenarios
- Deterministic local context systems:
  - `raw_transcript`
  - `summary_only`
  - `retrieval_only`
  - `ledger_only`
  - `ledger_retrieval`
  - `ledger_summary_retrieval`
- Deterministic detectors:
  - `null`
  - `rule_based`
  - `rubric`
  - `evidence_alignment`
  - `summary_faithfulness`
  - `calibrated_ensemble`
- Reference policies:
  - `none`
  - `anchor_refresh`
  - `ledger_regeneration`
  - `rollback`
  - `safe_stop`
  - `adaptive`
- A scripted local agent for smoke tests and regression checks
- Optional live-model backends:
  - `openai_compatible`
  - `anthropic_messages`
- Public benchmark splits:
  - `pilot`: 8 frozen scenarios
  - `dev`: 12 tuneable scenarios
  - `validation`: 8 frozen scenarios
  - `test`: 8 locked scenarios
- Balanced scenario families:
  - evidence synthesis
  - tool-state workflow
  - memory-update conflict
  - adversarial / untrusted input
- Replayable trace artifacts, richer checkpoint graders, offline perturbation suites, annotation packets, and paired-bootstrap comparison utilities

The repository is built to support later LLM-backed evaluations, but it starts with a **fully local benchmark harness** so the initial scientific claims are reproducible and contamination-resistant.

## Quickstart

List bundled scenarios:

```bash
python3 -m driftguard list-scenarios
```

List split metadata:

```bash
python3 -m driftguard list-splits
```

List supported agent backends:

```bash
python3 -m driftguard list-agent-backends
```

Run the pilot smoke benchmark:

```bash
python3 -m driftguard smoke --output-root results/smoke
```

Run a manifest-backed experiment slice:

```bash
python3 -m driftguard run-manifest pilot_baselines --output-root results/experiments --scenario pilot_evidence_brief --context ledger_only --detector rule_based --policy none --agent-backend scripted_local --seed 7
```

Probe the same slice with a live Anthropic backend:

```bash
DRIFTGUARD_ANTHROPIC_API_KEY=... DRIFTGUARD_ANTHROPIC_MODEL=claude-3-5-haiku-latest python3 -m driftguard run-manifest pilot_baselines --output-root results/live_probe --scenario pilot_evidence_brief --context ledger_only --detector rule_based --policy none --agent-backend anthropic_messages --seed 7
```

Probe the same slice with an OpenAI-compatible backend:

```bash
DRIFTGUARD_OPENAI_API_KEY=... DRIFTGUARD_OPENAI_MODEL=gpt-4.1-mini python3 -m driftguard run-manifest pilot_baselines --output-root results/live_probe_openai --scenario pilot_evidence_brief --context ledger_only --detector rule_based --policy none --agent-backend openai_compatible --seed 7
```

Run the bundled low-cost backend-comparison probe manifest:

```bash
python3 -m driftguard run-manifest pilot_live_backend_probe --output-root results/pilot_live_backend_probe --agent-backend scripted_local --seed 7
```

Run the first dev-wave baseline slice:

```bash
python3 -m driftguard run-manifest dev_wave1_baselines --output-root results/dev_wave1 --limit 8 --seed 11
```

Run the broader dev context ablation:

```bash
python3 -m driftguard run-manifest dev_wave2_context_ablation --output-root results/dev_wave2_contexts --seed 23
```

Run the frozen validation intervention-selection matrix:

```bash
python3 -m driftguard run-manifest validation_wave2_intervention_selection --output-root results/validation_wave2_interventions_v3 --seed 31
```

Run the expanded locked public test baseline slice:

```bash
python3 -m driftguard run-manifest test_wave2_baselines --output-root results/test_wave2_baselines --seed 37
```

Run the locked selected-policy test slice:

```bash
python3 -m driftguard run-manifest test_wave2_selected_policy --output-root results/test_wave2_selected_policy --seed 37
```

Describe a manifest before running it:

```bash
python3 -m driftguard describe-manifest validation_wave2_intervention_selection
```

Inspect locally recorded hidden/holdout runs:

```bash
python3 -m driftguard list-hidden-runs
```

Inspect locally recorded locked test/holdout runs:

```bash
python3 -m driftguard list-locked-runs
```

Summarize benchmark coverage:

```bash
python3 -m driftguard benchmark-stats
```

Lint the benchmark assets:

```bash
python3 -m driftguard lint-benchmark
```

Write a markdown snapshot report:

```bash
python3 -m driftguard write-snapshot-report --output reports/benchmark_snapshot.md --result-root results/dev_wave3_interventions/summary_artifacts --result-root results/validation_wave2_interventions_v3/summary_artifacts --result-root results/test_wave2_baselines/summary_artifacts --result-root results/test_wave2_selected_policy/summary_artifacts --perturbation-root results/perturbations_validation/validation_suite
```

Write a technical report from current artifacts:

```bash
python3 -m driftguard write-technical-report --output reports/technical_report.md --result-root results/validation_wave2_interventions_v3/summary_artifacts --perturbation-root results/perturbations_validation/validation_suite --manifest validation_wave2_intervention_selection
```

Write a human-calibration packet with an answer key:

```bash
python3 -m driftguard write-annotation-packet --annotation-set calibration_wave2 --output-root reports/annotation_wave2 --result-root results/validation_wave2_interventions_v3/summary_artifacts
```

Compute reviewer agreement from two filled response CSVs:

```bash
python3 -m driftguard compute-annotation-agreement --response reports/annotation_wave2/reviewer_a.csv --response reports/annotation_wave2/reviewer_b.csv
```

Score one reviewer against the answer key:

```bash
python3 -m driftguard score-annotation-response --response reports/annotation_wave2/reviewer_a.csv --answer-key reports/annotation_wave2/answer_key.json
```

Compute paired bootstrap deltas across context systems:

```bash
python3 -m driftguard compare-contexts --summary-root results/validation_wave2_interventions_v3/summary_artifacts --primary-context ledger_only --baseline-context raw_transcript --baseline-context summary_only --baseline-context ledger_retrieval
```

Compute paired policy deltas on weak contexts:

```bash
python3 -m driftguard compare-policies --summary-root results/validation_wave2_interventions_v3/summary_artifacts --primary-policy anchor_refresh --baseline-policy none --baseline-policy ledger_regeneration --baseline-policy adaptive --context raw_transcript --context summary_only --context retrieval_only --detector rule_based --detector calibrated_ensemble
```

Compute paired detector deltas:

```bash
python3 -m driftguard compare-detectors --summary-root results/validation_wave2_interventions_v3/summary_artifacts --primary-detector calibrated_ensemble --baseline-detector rule_based --policy none --policy anchor_refresh --policy ledger_regeneration --policy rollback --policy safe_stop --policy adaptive
```

Compute paired backend deltas:

```bash
python3 -m driftguard compare-agent-backends --summary-root results/pilot_live_backend_probe/summary_artifacts --primary-backend scripted_local --baseline-backend anthropic_messages --baseline-backend openai_compatible --context ledger_only --detector rule_based --policy none
```

Generate a failure atlas from a result slice:

```bash
python3 -m driftguard write-failure-atlas --output reports/failure_atlas.md --result-root results/validation_wave2_interventions_v3/summary_artifacts
```

Generate an ablation report from a result slice:

```bash
python3 -m driftguard write-ablation-report --output reports/validation_wave2_intervention_selection_v3.md --result-root results/validation_wave2_interventions_v3/summary_artifacts --manifest validation_wave2_intervention_selection
```

Fit the calibrated detector profile from local training assets:

```bash
python3 -m driftguard fit-detector-profile --split pilot --split dev --perturbation-suite pilot_suite
```

Replay a recorded trace:

```bash
python3 -m driftguard replay results/smoke/pilot_evidence_brief/raw_transcript/scripted_local/rule_based/none/seed-7/trace.jsonl
```

Run the perturbation regression suite:

```bash
python3 -m driftguard run-perturbations pilot_suite --output-root results/perturbations
```

Run the frozen validation perturbation suite:

```bash
python3 -m driftguard run-perturbations validation_suite --output-root results/perturbations_validation
```

## Execution provenance

Every run now records:

- `agent_backend`
- `prompt_pack_version`
- `resource_profile`
- backend metadata in `result.json`
- backend-aware trace paths and summary CSV rows

That makes mixed scripted/live runs analyzable without accidentally pairing different backends as the same condition.

Summarize recorded run artifacts:

```bash
python3 -m driftguard summarize-results results/smoke --output-root results/smoke/summary_artifacts
```

Run the test suite:

```bash
python3 -m unittest discover -s tests -v
```

## Repository layout

- [benchmark/](/Users/prakharkothari/Documents/DriftGuard/benchmark): prompts, resource profiles, scenario specs, manifests
- [docs/](/Users/prakharkothari/Documents/DriftGuard/docs): benchmark card, authoring guide, annotation guide, reproducibility guide, roadmap, failure atlas, technical report draft
- [driftguard/](/Users/prakharkothari/Documents/DriftGuard/driftguard): reference implementation
- [tests/](/Users/prakharkothari/Documents/DriftGuard/tests): unit and integration tests

## Current milestone

The repository currently covers **the deterministic benchmark spine, checkpoint/perturbation grading, public `dev`/`validation` selection slices, and the first intervention-selection pass**:

- benchmark spine
- pilot scenarios
- first public `dev` wave with split metadata and baseline manifest
- first public frozen `validation` wave with selection manifest governance
- expanded public locked `test` wave for final baseline and selected-policy comparison
- deterministic replay
- experiment-manifest execution
- richer checkpoint grading for visible state, ledger state, and provenance
- offline perturbation regression suite
- smoke tests, summaries, and CI coverage

The full 60-scenario benchmark, human calibration set, and final hiring-facing report are intentionally left for later phases so the current artifact stays small, reproducible, and scientifically legible.

## Scientific stance

DriftGuard’s working thesis is:

1. Task-intent drift can be benchmarked from **observable trace state**.
2. A structured `StateLedger` is more testable than freeform summaries.
3. Detector-triggered interventions can be evaluated under fixed budgets.

The current implementation is a **deterministic public benchmark release**, not the final model-backed 60-scenario release. The docs and manifests are versioned so later phases can extend the benchmark without rewriting the core artifact format.
