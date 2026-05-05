# DriftGuard Ablation Report

_Generated: 2026-04-23T14:09:44.051279+00:00_

## Evaluated Slice

- `result_root`: results/dev_wave2_contexts/summary_artifacts
- `manifest`: dev_wave2_context_ablation
- `stage`: development
- `splits`: dev
- `runs`: 48

## Context Ablation

| Context | Runs | Success Rate | Mean Score |
|---|---:|---:|---:|
| ledger_only | 8 | 1.00 | 1.00 |
| ledger_retrieval | 8 | 1.00 | 1.00 |
| ledger_summary_retrieval | 8 | 1.00 | 1.00 |
| raw_transcript | 8 | 0.00 | 0.00 |
| retrieval_only | 8 | 0.00 | 0.00 |
| summary_only | 8 | 0.00 | 0.00 |

## Policy Ablation

| Policy | Runs | Success Rate | Mean Score |
|---|---:|---:|---:|
| none | 48 | 0.50 | 0.50 |

## Detector Ablation

| Detector | Runs | Success Rate | Mean Score |
|---|---:|---:|---:|
| rule_based | 48 | 0.50 | 0.50 |

## Context x Policy

| Context | Policy | Runs | Success Rate | Mean Score |
|---|---|---:|---:|---:|
| ledger_only | none | 8 | 1.00 | 1.00 |
| ledger_retrieval | none | 8 | 1.00 | 1.00 |
| ledger_summary_retrieval | none | 8 | 1.00 | 1.00 |
| raw_transcript | none | 8 | 0.00 | 0.00 |
| retrieval_only | none | 8 | 0.00 | 0.00 |
| summary_only | none | 8 | 0.00 | 0.00 |

## Top Configurations

| Context | Detector | Policy | Runs | Success Rate | Mean Score |
|---|---|---|---:|---:|---:|
| ledger_summary_retrieval | rule_based | none | 8 | 1.00 | 1.00 |
| ledger_retrieval | rule_based | none | 8 | 1.00 | 1.00 |
| ledger_only | rule_based | none | 8 | 1.00 | 1.00 |
| summary_only | rule_based | none | 8 | 0.00 | 0.00 |
| retrieval_only | rule_based | none | 8 | 0.00 | 0.00 |
| raw_transcript | rule_based | none | 8 | 0.00 | 0.00 |

## Paired Context Comparisons

| Comparison | Paired Runs | Success Delta | Success 95% CI | Mean Score Delta | Score 95% CI |
|---|---:|---:|---|---:|---|
| ledger_only vs ledger_retrieval | 8 | 0.00 | [0.00, 0.00] | 0.00 | [0.00, 0.00] |
| ledger_only vs ledger_summary_retrieval | 8 | 0.00 | [0.00, 0.00] | 0.00 | [0.00, 0.00] |
| ledger_only vs raw_transcript | 8 | 1.00 | [1.00, 1.00] | 1.00 | [1.00, 1.00] |
| ledger_only vs retrieval_only | 8 | 1.00 | [1.00, 1.00] | 1.00 | [1.00, 1.00] |
| ledger_only vs summary_only | 8 | 1.00 | [1.00, 1.00] | 1.00 | [1.00, 1.00] |
