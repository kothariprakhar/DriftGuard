# DriftGuard Ablation Report

_Generated: 2026-04-23T14:19:38.138140+00:00_

## Evaluated Slice

- `result_root`: results/dev_wave3_contexts/summary_artifacts
- `manifest`: dev_wave3_context_ablation
- `stage`: development
- `splits`: dev
- `runs`: 72

## Context Ablation

| Context | Runs | Success Rate | Mean Score |
|---|---:|---:|---:|
| ledger_only | 12 | 1.00 | 1.00 |
| ledger_retrieval | 12 | 1.00 | 1.00 |
| ledger_summary_retrieval | 12 | 1.00 | 1.00 |
| raw_transcript | 12 | 0.00 | 0.00 |
| retrieval_only | 12 | 0.00 | 0.00 |
| summary_only | 12 | 0.00 | 0.00 |

## Policy Ablation

| Policy | Runs | Success Rate | Mean Score |
|---|---:|---:|---:|
| none | 72 | 0.50 | 0.50 |

## Detector Ablation

| Detector | Runs | Success Rate | Mean Score |
|---|---:|---:|---:|
| rule_based | 72 | 0.50 | 0.50 |

## Context x Policy

| Context | Policy | Runs | Success Rate | Mean Score |
|---|---|---:|---:|---:|
| ledger_only | none | 12 | 1.00 | 1.00 |
| ledger_retrieval | none | 12 | 1.00 | 1.00 |
| ledger_summary_retrieval | none | 12 | 1.00 | 1.00 |
| raw_transcript | none | 12 | 0.00 | 0.00 |
| retrieval_only | none | 12 | 0.00 | 0.00 |
| summary_only | none | 12 | 0.00 | 0.00 |

## Top Configurations

| Context | Detector | Policy | Runs | Success Rate | Mean Score |
|---|---|---|---:|---:|---:|
| ledger_summary_retrieval | rule_based | none | 12 | 1.00 | 1.00 |
| ledger_retrieval | rule_based | none | 12 | 1.00 | 1.00 |
| ledger_only | rule_based | none | 12 | 1.00 | 1.00 |
| summary_only | rule_based | none | 12 | 0.00 | 0.00 |
| retrieval_only | rule_based | none | 12 | 0.00 | 0.00 |
| raw_transcript | rule_based | none | 12 | 0.00 | 0.00 |

## Paired Context Comparisons

| Comparison | Paired Runs | Success Delta | Success 95% CI | Mean Score Delta | Score 95% CI |
|---|---:|---:|---|---:|---|
| ledger_only vs ledger_retrieval | 12 | 0.00 | [0.00, 0.00] | 0.00 | [0.00, 0.00] |
| ledger_only vs ledger_summary_retrieval | 12 | 0.00 | [0.00, 0.00] | 0.00 | [0.00, 0.00] |
| ledger_only vs raw_transcript | 12 | 1.00 | [1.00, 1.00] | 1.00 | [1.00, 1.00] |
| ledger_only vs retrieval_only | 12 | 1.00 | [1.00, 1.00] | 1.00 | [1.00, 1.00] |
| ledger_only vs summary_only | 12 | 1.00 | [1.00, 1.00] | 1.00 | [1.00, 1.00] |
