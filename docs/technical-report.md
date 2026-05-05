# Technical Report Draft

## Title

DriftGuard: A Ledger-Centric Benchmark for Task-Intent Drift in Long-Running Agents

## Construct definition

Task-intent drift is the divergence between an agent’s current working state and the accepted task contract.

## Task design

The current public benchmark uses deterministic local scenarios organized into `pilot`, `dev`, `validation`, and `test` splits so benchmark integrity is controlled before frontier-model evaluation begins. The current public inventory is 36 scenarios: 8 `pilot`, 12 `dev`, 8 `validation`, and 8 locked `test`.

The execution harness now supports both the deterministic `scripted_local` backend and optional live-model backends (`anthropic_messages`, `openai_compatible`). Current public benchmark claims remain scripted-local unless a frozen live-model slice is explicitly reported.

## Annotation protocol

The repository now includes:

- gold checkpoints and deterministic graders
- frozen human-calibration packets (`calibration_wave1`, `calibration_wave2`)
- answer-key scoring and pairwise agreement utilities for reviewer calibration

## Baselines

- raw transcript
- summary only
- retrieval only
- ledger only
- ledger + retrieval
- ledger + summary + retrieval

## Current deterministic signal

On the current frozen validation intervention-selection slice, ledger-centric contexts (`ledger_only`, `ledger_retrieval`, `ledger_summary_retrieval`) succeed on all included scenarios, while `raw_transcript` and `retrieval_only` succeed only `8.33%` of the time and `summary_only` succeeds `16.67%` of the time. On the same slice, `anchor_refresh` raises weak-context success from `0.00` to `0.50` for `raw_transcript` and `retrieval_only`, and to `1.00` for `summary_only`. These are still harness-validation results, not frontier-model claims.

## Ablations

The pilot harness supports:

- detector swaps
- policy swaps
- context-system swaps
- replay-based comparison

## Statistical methods

The current repository includes:

- split-aware manifests
- checkpoint metrics
- perturbation regressions
- a fitted calibrated-ensemble detector profile trained on public `pilot` and `dev` assets
- paired bootstrap confidence intervals for context comparisons
- stratified paired comparisons for weak-context policy gains and detector deltas

This is still a deterministic local benchmark, but the reporting is no longer limited to descriptive raw means.

## Negative results

This project explicitly expects negative results. The benchmark should be able to show when:

- summaries fail
- retrieval alone is not enough
- interventions help too late
- measured gains fall within noise

## Threats to validity

- deterministic scripted-agent results do not substitute for frontier-model results
- optional live-model probes are now supported in code, but have not yet been frozen into the public claim set
- the current public benchmark is still smaller than the planned full release, and the current public `test` split is still small
- open-web contamination is avoided by local design, but realism is correspondingly lower
