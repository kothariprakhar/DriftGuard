# Reproducibility Guide

## Local benchmark

The pilot benchmark is intentionally local-first.

Reproduce the smoke run with:

```bash
python3 -m driftguard smoke --output-root results/smoke
```

## Replay check

Replay any trace with:

```bash
python3 -m driftguard replay <trace.jsonl>
```

## Agent backends

Inspect supported backends with:

```bash
python3 -m driftguard list-agent-backends
```

The current public claims are still based on the deterministic `scripted_local` backend. Optional live-model runs can be executed with `anthropic_messages` or `openai_compatible`, but those results should be treated as external-validation probes until they are frozen into a governed evaluation slice.

## Split discipline

- `pilot` is frozen for smoke and regression checks.
- `dev` is the only public split intended for iteration.
- `validation` is frozen and intended for selection-time comparisons.
- `test` is a locked public split intended for one-shot final baseline evaluation.
- `shadow_holdout` remains private and should be run only once for final sanity checks.

Inspect split metadata with:

```bash
python3 -m driftguard list-splits
```

Inspect manifest governance with:

```bash
python3 -m driftguard describe-manifest validation_wave2_intervention_selection
```

Inspect locally recorded hidden/holdout runs with:

```bash
python3 -m driftguard list-hidden-runs
```

Inspect locally recorded locked `test` and `holdout` runs with:

```bash
python3 -m driftguard list-locked-runs
```

Summarize benchmark coverage with:

```bash
python3 -m driftguard benchmark-stats
```

Lint the benchmark assets with:

```bash
python3 -m driftguard lint-benchmark
```

Generate a markdown benchmark snapshot with:

```bash
python3 -m driftguard write-snapshot-report --output reports/benchmark_snapshot.md --result-root results/dev_wave3_interventions/summary_artifacts --result-root results/validation_wave2_interventions_v3/summary_artifacts --result-root results/test_wave2_baselines/summary_artifacts --result-root results/test_wave2_selected_policy/summary_artifacts --perturbation-root results/perturbations_validation/validation_suite
```

Generate a markdown technical report with:

```bash
python3 -m driftguard write-technical-report --output reports/technical_report.md --result-root results/validation_wave2_interventions_v3/summary_artifacts --perturbation-root results/perturbations_validation/validation_suite --manifest validation_wave2_intervention_selection
```

Generate a frozen human-calibration packet with:

```bash
python3 -m driftguard write-annotation-packet --annotation-set calibration_wave2 --output-root reports/annotation_wave2 --result-root results/validation_wave2_interventions_v3/summary_artifacts
```

Measure reviewer agreement with:

```bash
python3 -m driftguard compute-annotation-agreement --response reports/annotation_wave2/reviewer_a.csv --response reports/annotation_wave2/reviewer_b.csv
```

Score one reviewer response with:

```bash
python3 -m driftguard score-annotation-response --response reports/annotation_wave2/reviewer_a.csv --answer-key reports/annotation_wave2/answer_key.json
```

Compute paired bootstrap deltas with:

```bash
python3 -m driftguard compare-contexts --summary-root results/validation_wave2_interventions_v3/summary_artifacts --primary-context ledger_only --baseline-context raw_transcript --baseline-context summary_only --baseline-context ledger_retrieval
```

Compute weak-context policy deltas with:

```bash
python3 -m driftguard compare-policies --summary-root results/validation_wave2_interventions_v3/summary_artifacts --primary-policy anchor_refresh --baseline-policy none --baseline-policy ledger_regeneration --baseline-policy adaptive --context raw_transcript --context summary_only --context retrieval_only --detector rule_based --detector calibrated_ensemble
```

Compute detector deltas with:

```bash
python3 -m driftguard compare-detectors --summary-root results/validation_wave2_interventions_v3/summary_artifacts --primary-detector calibrated_ensemble --baseline-detector rule_based --policy none --policy anchor_refresh --policy ledger_regeneration --policy rollback --policy safe_stop --policy adaptive
```

Generate a failure atlas with:

```bash
python3 -m driftguard write-failure-atlas --output reports/failure_atlas.md --result-root results/validation_wave2_interventions_v3/summary_artifacts
```

Generate an ablation report with:

```bash
python3 -m driftguard write-ablation-report --output reports/validation_wave2_intervention_selection_v3.md --result-root results/validation_wave2_interventions_v3/summary_artifacts --manifest validation_wave2_intervention_selection
```

Fit the calibrated detector profile with:

```bash
python3 -m driftguard fit-detector-profile --split pilot --split dev --perturbation-suite pilot_suite
```

## What is pinned

- scenario specs
- prompt pack version
- resource profile version
- trace schema
- agent backend identity
- deterministic scripted-agent policy

## Live-model probe examples

Anthropic:

```bash
DRIFTGUARD_ANTHROPIC_API_KEY=... DRIFTGUARD_ANTHROPIC_MODEL=claude-3-5-haiku-latest python3 -m driftguard run-manifest pilot_baselines --output-root results/live_probe_anthropic --scenario pilot_evidence_brief --context ledger_only --detector rule_based --policy none --agent-backend anthropic_messages --seed 7
```

OpenAI-compatible:

```bash
DRIFTGUARD_OPENAI_API_KEY=... DRIFTGUARD_OPENAI_MODEL=gpt-4.1-mini python3 -m driftguard run-manifest pilot_baselines --output-root results/live_probe_openai --scenario pilot_evidence_brief --context ledger_only --detector rule_based --policy none --agent-backend openai_compatible --seed 7
```

Bundled low-cost backend comparison slice:

```bash
python3 -m driftguard run-manifest pilot_live_backend_probe --output-root results/pilot_live_backend_probe --agent-backend scripted_local --seed 7
```

## What is not yet part of the public release

- shadow holdout data
- live-model and Anthropic cross-provider holdout runs
- final larger `test` split and broader selected-policy test manifests
