# DriftGuard Ablation Report

_Generated: 2026-04-23T14:19:38.141010+00:00_

## Evaluated Slice

- `result_root`: results/dev_wave3_interventions/summary_artifacts
- `manifest`: dev_wave3_intervention_ablation
- `stage`: development
- `splits`: dev
- `runs`: 864

## Context Ablation

| Context | Runs | Success Rate | Mean Score |
|---|---:|---:|---:|
| ledger_only | 144 | 1.00 | 1.00 |
| ledger_retrieval | 144 | 1.00 | 1.00 |
| ledger_summary_retrieval | 144 | 1.00 | 1.00 |
| raw_transcript | 144 | 0.08 | 0.08 |
| retrieval_only | 144 | 0.08 | 0.08 |
| summary_only | 144 | 0.17 | 0.17 |

## Policy Ablation

| Policy | Runs | Success Rate | Mean Score |
|---|---:|---:|---:|
| adaptive | 144 | 0.50 | 0.50 |
| anchor_refresh | 144 | 0.83 | 0.83 |
| ledger_regeneration | 144 | 0.50 | 0.50 |
| none | 144 | 0.50 | 0.50 |
| rollback | 144 | 0.50 | 0.50 |
| safe_stop | 144 | 0.50 | 0.50 |

## Detector Ablation

| Detector | Runs | Success Rate | Mean Score |
|---|---:|---:|---:|
| calibrated_ensemble | 432 | 0.53 | 0.53 |
| rule_based | 432 | 0.58 | 0.58 |

## Context x Policy

| Context | Policy | Runs | Success Rate | Mean Score |
|---|---|---:|---:|---:|
| ledger_only | adaptive | 24 | 1.00 | 1.00 |
| ledger_only | anchor_refresh | 24 | 1.00 | 1.00 |
| ledger_only | ledger_regeneration | 24 | 1.00 | 1.00 |
| ledger_only | none | 24 | 1.00 | 1.00 |
| ledger_only | rollback | 24 | 1.00 | 1.00 |
| ledger_only | safe_stop | 24 | 1.00 | 1.00 |
| ledger_retrieval | adaptive | 24 | 1.00 | 1.00 |
| ledger_retrieval | anchor_refresh | 24 | 1.00 | 1.00 |
| ledger_retrieval | ledger_regeneration | 24 | 1.00 | 1.00 |
| ledger_retrieval | none | 24 | 1.00 | 1.00 |
| ledger_retrieval | rollback | 24 | 1.00 | 1.00 |
| ledger_retrieval | safe_stop | 24 | 1.00 | 1.00 |
| ledger_summary_retrieval | adaptive | 24 | 1.00 | 1.00 |
| ledger_summary_retrieval | anchor_refresh | 24 | 1.00 | 1.00 |
| ledger_summary_retrieval | ledger_regeneration | 24 | 1.00 | 1.00 |
| ledger_summary_retrieval | none | 24 | 1.00 | 1.00 |
| ledger_summary_retrieval | rollback | 24 | 1.00 | 1.00 |
| ledger_summary_retrieval | safe_stop | 24 | 1.00 | 1.00 |
| raw_transcript | adaptive | 24 | 0.00 | 0.00 |
| raw_transcript | anchor_refresh | 24 | 0.50 | 0.50 |
| raw_transcript | ledger_regeneration | 24 | 0.00 | 0.00 |
| raw_transcript | none | 24 | 0.00 | 0.00 |
| raw_transcript | rollback | 24 | 0.00 | 0.00 |
| raw_transcript | safe_stop | 24 | 0.00 | 0.00 |
| retrieval_only | adaptive | 24 | 0.00 | 0.00 |
| retrieval_only | anchor_refresh | 24 | 0.50 | 0.50 |
| retrieval_only | ledger_regeneration | 24 | 0.00 | 0.00 |
| retrieval_only | none | 24 | 0.00 | 0.00 |
| retrieval_only | rollback | 24 | 0.00 | 0.00 |
| retrieval_only | safe_stop | 24 | 0.00 | 0.00 |
| summary_only | adaptive | 24 | 0.00 | 0.00 |
| summary_only | anchor_refresh | 24 | 1.00 | 1.00 |
| summary_only | ledger_regeneration | 24 | 0.00 | 0.00 |
| summary_only | none | 24 | 0.00 | 0.00 |
| summary_only | rollback | 24 | 0.00 | 0.00 |
| summary_only | safe_stop | 24 | 0.00 | 0.00 |

## Top Configurations

| Context | Detector | Policy | Runs | Success Rate | Mean Score |
|---|---|---|---:|---:|---:|
| summary_only | rule_based | anchor_refresh | 12 | 1.00 | 1.00 |
| summary_only | calibrated_ensemble | anchor_refresh | 12 | 1.00 | 1.00 |
| retrieval_only | rule_based | anchor_refresh | 12 | 1.00 | 1.00 |
| raw_transcript | rule_based | anchor_refresh | 12 | 1.00 | 1.00 |
| ledger_summary_retrieval | rule_based | safe_stop | 12 | 1.00 | 1.00 |
| ledger_summary_retrieval | rule_based | rollback | 12 | 1.00 | 1.00 |
| ledger_summary_retrieval | rule_based | none | 12 | 1.00 | 1.00 |
| ledger_summary_retrieval | rule_based | ledger_regeneration | 12 | 1.00 | 1.00 |
| ledger_summary_retrieval | rule_based | anchor_refresh | 12 | 1.00 | 1.00 |
| ledger_summary_retrieval | rule_based | adaptive | 12 | 1.00 | 1.00 |
| ledger_summary_retrieval | calibrated_ensemble | safe_stop | 12 | 1.00 | 1.00 |
| ledger_summary_retrieval | calibrated_ensemble | rollback | 12 | 1.00 | 1.00 |

## Paired Context Comparisons

| Comparison | Paired Runs | Success Delta | Success 95% CI | Mean Score Delta | Score 95% CI |
|---|---:|---:|---|---:|---|
| ledger_only vs ledger_retrieval | 144 | 0.00 | [0.00, 0.00] | 0.00 | [0.00, 0.00] |
| ledger_only vs ledger_summary_retrieval | 144 | 0.00 | [0.00, 0.00] | 0.00 | [0.00, 0.00] |
| ledger_only vs raw_transcript | 144 | 0.92 | [0.87, 0.96] | 0.92 | [0.87, 0.96] |
| ledger_only vs retrieval_only | 144 | 0.92 | [0.87, 0.96] | 0.92 | [0.87, 0.96] |
| ledger_only vs summary_only | 144 | 0.83 | [0.77, 0.89] | 0.83 | [0.77, 0.89] |

## Weak-Context Policy Comparisons

| Comparison | Paired Runs | Success Delta | Success 95% CI | Mean Score Delta | Score 95% CI |
|---|---:|---:|---|---:|---|
| anchor_refresh vs none | 72 | 0.67 | [0.56, 0.78] | 0.67 | [0.56, 0.78] |
| anchor_refresh vs ledger_regeneration | 72 | 0.67 | [0.56, 0.78] | 0.67 | [0.56, 0.78] |
| anchor_refresh vs rollback | 72 | 0.67 | [0.56, 0.78] | 0.67 | [0.56, 0.78] |
| anchor_refresh vs safe_stop | 72 | 0.67 | [0.56, 0.78] | 0.67 | [0.56, 0.78] |
| anchor_refresh vs adaptive | 72 | 0.67 | [0.56, 0.78] | 0.67 | [0.56, 0.78] |

## Detector Comparisons

| Comparison | Paired Runs | Success Delta | Success 95% CI | Mean Score Delta | Score 95% CI |
|---|---:|---:|---|---:|---|
| rule_based vs calibrated_ensemble | 432 | 0.06 | [0.03, 0.08] | 0.06 | [0.03, 0.08] |
