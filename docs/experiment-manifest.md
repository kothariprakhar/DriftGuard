# Experiment Manifest

## Active manifest

- [`benchmark/experiment_manifests/pilot_baselines.json`](/Users/prakharkothari/Documents/DriftGuard/benchmark/experiment_manifests/pilot_baselines.json)
- [`benchmark/experiment_manifests/pilot_live_backend_probe.json`](/Users/prakharkothari/Documents/DriftGuard/benchmark/experiment_manifests/pilot_live_backend_probe.json)
- [`benchmark/experiment_manifests/dev_wave1_baselines.json`](/Users/prakharkothari/Documents/DriftGuard/benchmark/experiment_manifests/dev_wave1_baselines.json)
- [`benchmark/experiment_manifests/dev_wave2_context_ablation.json`](/Users/prakharkothari/Documents/DriftGuard/benchmark/experiment_manifests/dev_wave2_context_ablation.json)
- [`benchmark/experiment_manifests/dev_wave2_intervention_ablation.json`](/Users/prakharkothari/Documents/DriftGuard/benchmark/experiment_manifests/dev_wave2_intervention_ablation.json)
- [`benchmark/experiment_manifests/dev_wave3_context_ablation.json`](/Users/prakharkothari/Documents/DriftGuard/benchmark/experiment_manifests/dev_wave3_context_ablation.json)
- [`benchmark/experiment_manifests/dev_wave3_intervention_ablation.json`](/Users/prakharkothari/Documents/DriftGuard/benchmark/experiment_manifests/dev_wave3_intervention_ablation.json)
- [`benchmark/experiment_manifests/validation_wave1_baselines.json`](/Users/prakharkothari/Documents/DriftGuard/benchmark/experiment_manifests/validation_wave1_baselines.json)
- [`benchmark/experiment_manifests/validation_wave2_context_ablation.json`](/Users/prakharkothari/Documents/DriftGuard/benchmark/experiment_manifests/validation_wave2_context_ablation.json)
- [`benchmark/experiment_manifests/validation_wave2_intervention_selection.json`](/Users/prakharkothari/Documents/DriftGuard/benchmark/experiment_manifests/validation_wave2_intervention_selection.json)
- [`benchmark/experiment_manifests/test_wave1_baselines.json`](/Users/prakharkothari/Documents/DriftGuard/benchmark/experiment_manifests/test_wave1_baselines.json)
- [`benchmark/experiment_manifests/test_wave2_baselines.json`](/Users/prakharkothari/Documents/DriftGuard/benchmark/experiment_manifests/test_wave2_baselines.json)
- [`benchmark/experiment_manifests/test_wave2_selected_policy.json`](/Users/prakharkothari/Documents/DriftGuard/benchmark/experiment_manifests/test_wave2_selected_policy.json)

## Current execution path

Run a filtered slice directly from the registry:

```bash
python3 -m driftguard run-manifest pilot_baselines --scenario pilot_evidence_brief --context ledger_only --detector rule_based --policy none --agent-backend scripted_local --seed 7
```

Run the first dev-wave baseline slice:

```bash
python3 -m driftguard run-manifest dev_wave1_baselines --limit 8 --seed 11
```

Run the broader dev context ablation:

```bash
python3 -m driftguard run-manifest dev_wave3_context_ablation --output-root results/dev_wave3_contexts --seed 29
```

Run the low-cost backend-comparison probe:

```bash
python3 -m driftguard run-manifest pilot_live_backend_probe --output-root results/pilot_live_backend_probe --agent-backend scripted_local --seed 7
```

Inspect a manifest before running it:

```bash
python3 -m driftguard describe-manifest validation_wave2_intervention_selection
```

Inspect supported backends:

```bash
python3 -m driftguard list-agent-backends
```

Inspect locally recorded hidden/holdout runs:

```bash
python3 -m driftguard list-hidden-runs
```

Inspect locally recorded locked `test` and `holdout` runs:

```bash
python3 -m driftguard list-locked-runs
```

Run the frozen validation context-selection slice:

```bash
python3 -m driftguard run-manifest validation_wave2_context_ablation --output-root results/validation_wave2_contexts --seed 29
```

Run the frozen validation intervention-selection matrix:

```bash
python3 -m driftguard run-manifest validation_wave2_intervention_selection --output-root results/validation_wave2_interventions_v3 --seed 31
```

Run the locked public test baseline slice once:

```bash
python3 -m driftguard run-manifest test_wave2_baselines --output-root results/test_wave2_baselines --seed 37
```

Run the locked public selected-policy test slice once:

```bash
python3 -m driftguard run-manifest test_wave2_selected_policy --output-root results/test_wave2_selected_policy --seed 37
```

## Required metadata for future experiments

- dataset / scenario version
- prompt pack version
- resource profile version
- context system
- detector
- policy
- agent backend
- model identifier
- seed
- infra notes

## Backend notes

- Existing manifests default to `scripted_local` unless an `agent_backends` list is provided.
- CLI filtering with `--agent-backend` lets the same manifest be executed under a live backend without changing the scenario set.
- Result artifacts now carry `agent_backend`, `prompt_pack_version`, and `resource_profile`, so mixed runs remain pairwise-safe during analysis.
- Use `compare-agent-backends` on a summary root to measure paired deltas between scripted and live backends under matched scenarios, seeds, contexts, detectors, and policies.

## Selection rule

- tune on `dev`
- select on frozen `validation`
- run `test` once
- report infra noise separately
