# Prompt Pack Manifest

## Current prompt pack

- version: `v1`

## Prompt roles

- `base_agent`
- `ledger_update`
- `summary_update`
- `retrieval_query`
- `detector_rubric`
- `trace_grader`
- `outcome_grader`

## Versioning rule

Any semantically meaningful prompt change must:

- bump the prompt pack version
- be recorded in experiment metadata
- not be changed after validation lock for a named experiment
