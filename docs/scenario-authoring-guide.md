# Scenario Authoring Guide

## Design principles

- Make verification easier than discovery.
- Make drift possible for an understandable reason.
- Keep the gold action objectively defensible.
- Encode at least one failure mode cleanly:
  - constraint loss
  - stale memory
  - evidence substitution
  - adversarial hijack

## Required fields

Every scenario must define:

- `intent_contract`
- `budget_ceiling`
- `corpus`
- `events`
- `gold_checkpoints`
- `gold_outcome`

Every scenario must also belong to an explicit split:

- `pilot`: frozen public regression slice
- `dev`: public tuning slice
- `shadow_holdout`: private final-check slice

## Event types used in the pilot

- `subgoal`
- `constraint`
- `evidence`
- `risk`
- `adversarial`
- `decision`

## Decision design

Each decision should include:

- one correct option
- at least one plausible distractor
- explicit `required_constraints`
- explicit `required_evidence`
- optional bias hooks for:
  - missing constraints
  - missing evidence
  - visible adversarial text

## Gold checkpoints

Use checkpoints only at meaningful state transitions:

- after crucial evidence arrival
- after a policy update
- after a decision

Do not create checkpoints for every trivial event.

For stronger checkpoint truth, prefer filling these richer fields when possible:

- `required_fact_contents`
- `required_ledger_decisions`
- `required_outstanding_work`
- `required_plan_steps`
- `required_accepted_evidence_ids`
- `required_active_subgoal`
- `required_provenance`
