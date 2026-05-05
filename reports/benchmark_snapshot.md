# DriftGuard Benchmark Snapshot

_Generated: 2026-04-23T19:14:51.264729+00:00_

## Benchmark Coverage

- `total_scenarios`: 36
- `dev`: 12 scenarios (adversarial_untrusted_input:3, evidence_synthesis:3, memory_update_conflict:3, tool_state_workflow:3)
- `pilot`: 8 scenarios (adversarial_untrusted_input:2, evidence_synthesis:2, memory_update_conflict:2, tool_state_workflow:2)
- `test`: 8 scenarios (adversarial_untrusted_input:2, evidence_synthesis:2, memory_update_conflict:2, tool_state_workflow:2)
- `validation`: 8 scenarios (adversarial_untrusted_input:2, evidence_synthesis:2, memory_update_conflict:2, tool_state_workflow:2)

## Manifests

### `dev_wave1_baselines`

- `stage`: development
- `scenario_count`: 8
- `splits`: dev

### `dev_wave2_context_ablation`

- `stage`: development
- `scenario_count`: 8
- `splits`: dev

### `dev_wave2_intervention_ablation`

- `stage`: development
- `scenario_count`: 8
- `splits`: dev

### `dev_wave3_context_ablation`

- `stage`: development
- `scenario_count`: 12
- `splits`: dev

### `dev_wave3_intervention_ablation`

- `stage`: development
- `scenario_count`: 12
- `splits`: dev

### `pilot_baselines`

- `stage`: baseline
- `scenario_count`: 8
- `splits`: pilot

### `pilot_live_backend_probe`

- `stage`: baseline
- `scenario_count`: 4
- `splits`: pilot

### `test_wave1_baselines`

- `stage`: test
- `scenario_count`: 4
- `splits`: test

### `test_wave2_baselines`

- `stage`: test
- `scenario_count`: 8
- `splits`: test

### `test_wave2_selected_policy`

- `stage`: test
- `scenario_count`: 8
- `splits`: test

### `validation_wave1_baselines`

- `stage`: selection
- `scenario_count`: 8
- `splits`: validation

### `validation_wave2_context_ablation`

- `stage`: selection
- `scenario_count`: 8
- `splits`: validation

### `validation_wave2_intervention_selection`

- `stage`: selection
- `scenario_count`: 8
- `splits`: validation

## Result Summaries

### `results/dev_wave3_interventions/summary_artifacts`

- `total_runs`: 864
- `success_rate`: 0.56
- `mean_score`: 0.56
- `mean_visible_checkpoint_adherence`: 0.78
- `mean_ledger_checkpoint_adherence`: 0.87

| Context | Runs | Success Rate | Mean Score |
|---|---:|---:|---:|
| ledger_only | 144 | 1.00 | 1.00 |
| ledger_retrieval | 144 | 1.00 | 1.00 |
| ledger_summary_retrieval | 144 | 1.00 | 1.00 |
| raw_transcript | 144 | 0.08 | 0.08 |
| retrieval_only | 144 | 0.08 | 0.08 |
| summary_only | 144 | 0.17 | 0.17 |

### `results/validation_wave2_interventions_v3/summary_artifacts`

- `total_runs`: 576
- `success_rate`: 0.58
- `mean_score`: 0.58
- `mean_visible_checkpoint_adherence`: 0.78
- `mean_ledger_checkpoint_adherence`: 0.88

| Context | Runs | Success Rate | Mean Score |
|---|---:|---:|---:|
| ledger_only | 96 | 1.00 | 1.00 |
| ledger_retrieval | 96 | 1.00 | 1.00 |
| ledger_summary_retrieval | 96 | 1.00 | 1.00 |
| raw_transcript | 96 | 0.17 | 0.17 |
| retrieval_only | 96 | 0.17 | 0.17 |
| summary_only | 96 | 0.17 | 0.17 |

### `results/test_wave2_baselines/summary_artifacts`

- `total_runs`: 48
- `success_rate`: 0.50
- `mean_score`: 0.50
- `mean_visible_checkpoint_adherence`: 0.76
- `mean_ledger_checkpoint_adherence`: 0.86

| Context | Runs | Success Rate | Mean Score |
|---|---:|---:|---:|
| ledger_only | 8 | 1.00 | 1.00 |
| ledger_retrieval | 8 | 1.00 | 1.00 |
| ledger_summary_retrieval | 8 | 1.00 | 1.00 |
| raw_transcript | 8 | 0.00 | 0.00 |
| retrieval_only | 8 | 0.00 | 0.00 |
| summary_only | 8 | 0.00 | 0.00 |

### `results/test_wave2_selected_policy/summary_artifacts`

- `total_runs`: 96
- `success_rate`: 0.75
- `mean_score`: 0.75
- `mean_visible_checkpoint_adherence`: 0.83
- `mean_ledger_checkpoint_adherence`: 0.93

| Context | Runs | Success Rate | Mean Score |
|---|---:|---:|---:|
| ledger_only | 16 | 1.00 | 1.00 |
| ledger_retrieval | 16 | 1.00 | 1.00 |
| ledger_summary_retrieval | 16 | 1.00 | 1.00 |
| raw_transcript | 16 | 0.50 | 0.50 |
| retrieval_only | 16 | 0.50 | 0.50 |
| summary_only | 16 | 0.50 | 0.50 |

### `results/pilot_live_backend_probe_check/summary_artifacts`

- `total_runs`: 8
- `success_rate`: 0.50
- `mean_score`: 0.50
- `mean_visible_checkpoint_adherence`: 0.70
- `mean_ledger_checkpoint_adherence`: 0.91

| Context | Runs | Success Rate | Mean Score |
|---|---:|---:|---:|
| ledger_only | 4 | 1.00 | 1.00 |
| raw_transcript | 4 | 0.00 | 0.00 |

## Perturbation Suites

### `results/perturbations_validation/validation_suite`

- `cases`: 8
- `passed`: 8
- `pass_rate`: 1.00
- `mean_score_delta`: 0.90
