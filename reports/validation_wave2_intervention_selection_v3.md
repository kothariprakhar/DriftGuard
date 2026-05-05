# DriftGuard Ablation Report

_Generated: 2026-04-23T19:11:40.675432+00:00_

## Evaluated Slice

- `result_root`: results/validation_wave2_interventions_v3/summary_artifacts
- `manifest`: validation_wave2_intervention_selection
- `stage`: selection
- `splits`: validation
- `runs`: 576

## Context Ablation

| Context | Runs | Success Rate | Mean Score |
|---|---:|---:|---:|
| ledger_only | 96 | 1.00 | 1.00 |
| ledger_retrieval | 96 | 1.00 | 1.00 |
| ledger_summary_retrieval | 96 | 1.00 | 1.00 |
| raw_transcript | 96 | 0.17 | 0.17 |
| retrieval_only | 96 | 0.17 | 0.17 |
| summary_only | 96 | 0.17 | 0.17 |

## Policy Ablation

| Policy | Runs | Success Rate | Mean Score |
|---|---:|---:|---:|
| adaptive | 96 | 0.50 | 0.50 |
| anchor_refresh | 96 | 1.00 | 1.00 |
| ledger_regeneration | 96 | 0.50 | 0.50 |
| none | 96 | 0.50 | 0.50 |
| rollback | 96 | 0.50 | 0.50 |
| safe_stop | 96 | 0.50 | 0.50 |

## Detector Ablation

| Detector | Runs | Success Rate | Mean Score |
|---|---:|---:|---:|
| calibrated_ensemble | 288 | 0.58 | 0.58 |
| rule_based | 288 | 0.58 | 0.58 |

## Context x Policy

| Context | Policy | Runs | Success Rate | Mean Score |
|---|---|---:|---:|---:|
| ledger_only | adaptive | 16 | 1.00 | 1.00 |
| ledger_only | anchor_refresh | 16 | 1.00 | 1.00 |
| ledger_only | ledger_regeneration | 16 | 1.00 | 1.00 |
| ledger_only | none | 16 | 1.00 | 1.00 |
| ledger_only | rollback | 16 | 1.00 | 1.00 |
| ledger_only | safe_stop | 16 | 1.00 | 1.00 |
| ledger_retrieval | adaptive | 16 | 1.00 | 1.00 |
| ledger_retrieval | anchor_refresh | 16 | 1.00 | 1.00 |
| ledger_retrieval | ledger_regeneration | 16 | 1.00 | 1.00 |
| ledger_retrieval | none | 16 | 1.00 | 1.00 |
| ledger_retrieval | rollback | 16 | 1.00 | 1.00 |
| ledger_retrieval | safe_stop | 16 | 1.00 | 1.00 |
| ledger_summary_retrieval | adaptive | 16 | 1.00 | 1.00 |
| ledger_summary_retrieval | anchor_refresh | 16 | 1.00 | 1.00 |
| ledger_summary_retrieval | ledger_regeneration | 16 | 1.00 | 1.00 |
| ledger_summary_retrieval | none | 16 | 1.00 | 1.00 |
| ledger_summary_retrieval | rollback | 16 | 1.00 | 1.00 |
| ledger_summary_retrieval | safe_stop | 16 | 1.00 | 1.00 |
| raw_transcript | adaptive | 16 | 0.00 | 0.00 |
| raw_transcript | anchor_refresh | 16 | 1.00 | 1.00 |
| raw_transcript | ledger_regeneration | 16 | 0.00 | 0.00 |
| raw_transcript | none | 16 | 0.00 | 0.00 |
| raw_transcript | rollback | 16 | 0.00 | 0.00 |
| raw_transcript | safe_stop | 16 | 0.00 | 0.00 |
| retrieval_only | adaptive | 16 | 0.00 | 0.00 |
| retrieval_only | anchor_refresh | 16 | 1.00 | 1.00 |
| retrieval_only | ledger_regeneration | 16 | 0.00 | 0.00 |
| retrieval_only | none | 16 | 0.00 | 0.00 |
| retrieval_only | rollback | 16 | 0.00 | 0.00 |
| retrieval_only | safe_stop | 16 | 0.00 | 0.00 |
| summary_only | adaptive | 16 | 0.00 | 0.00 |
| summary_only | anchor_refresh | 16 | 1.00 | 1.00 |
| summary_only | ledger_regeneration | 16 | 0.00 | 0.00 |
| summary_only | none | 16 | 0.00 | 0.00 |
| summary_only | rollback | 16 | 0.00 | 0.00 |
| summary_only | safe_stop | 16 | 0.00 | 0.00 |

## Top Configurations

| Context | Backend | Detector | Policy | Runs | Success Rate | Mean Score |
|---|---|---|---|---:|---:|---:|
| summary_only | scripted_local | rule_based | anchor_refresh | 8 | 1.00 | 1.00 |
| summary_only | scripted_local | calibrated_ensemble | anchor_refresh | 8 | 1.00 | 1.00 |
| retrieval_only | scripted_local | rule_based | anchor_refresh | 8 | 1.00 | 1.00 |
| retrieval_only | scripted_local | calibrated_ensemble | anchor_refresh | 8 | 1.00 | 1.00 |
| raw_transcript | scripted_local | rule_based | anchor_refresh | 8 | 1.00 | 1.00 |
| raw_transcript | scripted_local | calibrated_ensemble | anchor_refresh | 8 | 1.00 | 1.00 |
| ledger_summary_retrieval | scripted_local | rule_based | safe_stop | 8 | 1.00 | 1.00 |
| ledger_summary_retrieval | scripted_local | rule_based | rollback | 8 | 1.00 | 1.00 |
| ledger_summary_retrieval | scripted_local | rule_based | none | 8 | 1.00 | 1.00 |
| ledger_summary_retrieval | scripted_local | rule_based | ledger_regeneration | 8 | 1.00 | 1.00 |
| ledger_summary_retrieval | scripted_local | rule_based | anchor_refresh | 8 | 1.00 | 1.00 |
| ledger_summary_retrieval | scripted_local | rule_based | adaptive | 8 | 1.00 | 1.00 |

## Paired Context Comparisons

| Comparison | Paired Runs | Success Delta | Success 95% CI | Mean Score Delta | Score 95% CI |
|---|---:|---:|---|---:|---|
| ledger_only vs ledger_retrieval | 96 | 0.00 | [0.00, 0.00] | 0.00 | [0.00, 0.00] |
| ledger_only vs ledger_summary_retrieval | 96 | 0.00 | [0.00, 0.00] | 0.00 | [0.00, 0.00] |
| ledger_only vs raw_transcript | 96 | 0.83 | [0.76, 0.91] | 0.83 | [0.76, 0.91] |
| ledger_only vs retrieval_only | 96 | 0.83 | [0.76, 0.91] | 0.83 | [0.76, 0.91] |
| ledger_only vs summary_only | 96 | 0.83 | [0.76, 0.91] | 0.83 | [0.76, 0.91] |

## Weak-Context Policy Comparisons

| Comparison | Paired Runs | Success Delta | Success 95% CI | Mean Score Delta | Score 95% CI |
|---|---:|---:|---|---:|---|
| anchor_refresh vs none | 48 | 1.00 | [1.00, 1.00] | 1.00 | [1.00, 1.00] |
| anchor_refresh vs ledger_regeneration | 48 | 1.00 | [1.00, 1.00] | 1.00 | [1.00, 1.00] |
| anchor_refresh vs rollback | 48 | 1.00 | [1.00, 1.00] | 1.00 | [1.00, 1.00] |
| anchor_refresh vs safe_stop | 48 | 1.00 | [1.00, 1.00] | 1.00 | [1.00, 1.00] |
| anchor_refresh vs adaptive | 48 | 1.00 | [1.00, 1.00] | 1.00 | [1.00, 1.00] |

## Detector Comparisons

| Comparison | Paired Runs | Success Delta | Success 95% CI | Mean Score Delta | Score 95% CI |
|---|---:|---:|---|---:|---|
| rule_based vs calibrated_ensemble | 288 | 0.00 | [0.00, 0.00] | 0.00 | [0.00, 0.00] |
