# DriftGuard Technical Report

_Generated: 2026-04-23T19:11:40.677323+00:00_

## Thesis

DriftGuard benchmarks task-intent drift from observable state and tests whether ledger-centric context management preserves the original task contract better than weaker baselines.

## Benchmark

- `public_scenarios`: 36
- `selection_manifest`: validation_wave2_intervention_selection
- `manifest_stage`: selection
- `manifest_splits`: validation
- `selection_scenarios`: 8

## Main Result

On the current evaluated slice, the strongest context systems are `ledger_summary_retrieval` (1.00), `ledger_retrieval` (1.00), `ledger_only` (1.00).
The weakest baselines on the same slice are `raw_transcript` (0.17), `summary_only` (0.17), `retrieval_only` (0.17), which is why the aggregate mixed-context success rate remains `success_rate=0.58`.
On weak contexts only, `anchor_refresh` improves success over `none` by `1.00` with paired bootstrap `95% CI [1.00, 1.00]`.

### Context Performance

| Context | Runs | Success Rate | Mean Score |
|---|---:|---:|---:|
| ledger_only | 96 | 1.00 | 1.00 |
| ledger_retrieval | 96 | 1.00 | 1.00 |
| ledger_summary_retrieval | 96 | 1.00 | 1.00 |
| raw_transcript | 96 | 0.17 | 0.17 |
| retrieval_only | 96 | 0.17 | 0.17 |
| summary_only | 96 | 0.17 | 0.17 |

### Context By Family

| Family | Context | Runs | Success Rate | Mean Score |
|---|---|---:|---:|---:|
| adversarial_untrusted_input | ledger_only | 24 | 1.00 | 1.00 |
| adversarial_untrusted_input | ledger_retrieval | 24 | 1.00 | 1.00 |
| adversarial_untrusted_input | ledger_summary_retrieval | 24 | 1.00 | 1.00 |
| adversarial_untrusted_input | raw_transcript | 24 | 0.17 | 0.17 |
| adversarial_untrusted_input | retrieval_only | 24 | 0.17 | 0.17 |
| adversarial_untrusted_input | summary_only | 24 | 0.17 | 0.17 |
| evidence_synthesis | ledger_only | 24 | 1.00 | 1.00 |
| evidence_synthesis | ledger_retrieval | 24 | 1.00 | 1.00 |
| evidence_synthesis | ledger_summary_retrieval | 24 | 1.00 | 1.00 |
| evidence_synthesis | raw_transcript | 24 | 0.17 | 0.17 |
| evidence_synthesis | retrieval_only | 24 | 0.17 | 0.17 |
| evidence_synthesis | summary_only | 24 | 0.17 | 0.17 |
| memory_update_conflict | ledger_only | 24 | 1.00 | 1.00 |
| memory_update_conflict | ledger_retrieval | 24 | 1.00 | 1.00 |
| memory_update_conflict | ledger_summary_retrieval | 24 | 1.00 | 1.00 |
| memory_update_conflict | raw_transcript | 24 | 0.17 | 0.17 |
| memory_update_conflict | retrieval_only | 24 | 0.17 | 0.17 |
| memory_update_conflict | summary_only | 24 | 0.17 | 0.17 |
| tool_state_workflow | ledger_only | 24 | 1.00 | 1.00 |
| tool_state_workflow | ledger_retrieval | 24 | 1.00 | 1.00 |
| tool_state_workflow | ledger_summary_retrieval | 24 | 1.00 | 1.00 |
| tool_state_workflow | raw_transcript | 24 | 0.17 | 0.17 |
| tool_state_workflow | retrieval_only | 24 | 0.17 | 0.17 |
| tool_state_workflow | summary_only | 24 | 0.17 | 0.17 |

### Pairwise Deltas

| Comparison | Paired Runs | Success Delta | Success 95% CI | Mean Score Delta | Score 95% CI |
|---|---:|---:|---|---:|---|
| ledger_only vs raw_transcript | 96 | 0.83 | [0.76, 0.91] | 0.83 | [0.76, 0.91] |
| ledger_only vs summary_only | 96 | 0.83 | [0.76, 0.91] | 0.83 | [0.76, 0.91] |
| ledger_only vs ledger_retrieval | 96 | 0.00 | [0.00, 0.00] | 0.00 | [0.00, 0.00] |

## Checkpoint Signal

- `mean_visible_checkpoint_adherence`: 0.78
- `mean_ledger_checkpoint_adherence`: 0.88

## Perturbation Regression

- `cases`: 8
- `passed`: 8
- `pass_rate`: 1.00
- `mean_score_delta`: 0.90

## Representative Deterministic Failures

- `validation_billing_chat_escalation` with `raw_transcript` fails at `step-3` and ends with score `0.00`.
- `validation_hr_case_packet` with `raw_transcript` fails at `step-4` and ends with score `0.00`.
- `validation_policy_supersession_credit` with `raw_transcript` fails at `step-3` and ends with score `0.00`.
- `validation_access_review_reactivation` with `raw_transcript` fails at `step-4` and ends with score `0.00`.

## Limitations

- These are deterministic harness results, not frontier-model evaluation results.
- The public benchmark is still smaller than the intended full release.
- Confidence intervals are paired bootstrap intervals over matched scenario/seed runs on the evaluated slice.

## Interpretation

The current evidence supports the narrow claim that this benchmark exposes memory and anchoring failures cleanly and that ledger-centric baselines preserve intent on the included scenarios better than transcript-only or summary-only baselines.
