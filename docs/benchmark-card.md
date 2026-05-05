# Benchmark Card

## Name

DriftGuard Public Deterministic Benchmark

## Goal

Measure **task-intent drift** in long-running agent-style workflows using only observable state:

- task contract
- visible context artifacts
- tool-style evidence
- choices and checkpoints
- final outcome

## What is being measured

The benchmark targets whether a system:

- preserves hard constraints
- keeps the correct evidence in view
- preserves ledger state and provenance across checkpoints
- resists adversarial or irrelevant content
- applies the latest state update rather than stale state
- makes the correct action choice at the key decision point

## Current scope

The public repository currently contains 36 local scenarios:

- 8 frozen `pilot` scenarios
- 12 tuning-oriented `dev` scenarios
- 8 frozen `validation` scenarios
- 8 locked `test` scenarios

- evidence synthesis
- tool-state workflow
- memory-update conflict
- adversarial / untrusted input

The repository also includes perturbation suites on both `pilot` and frozen `validation` scenarios for detector-regression checks.

## Non-goals

- This is not a model capability leaderboard.
- This is not a production observability platform benchmark.
- This is not a benchmark of hidden chain-of-thought quality.

## Integrity controls

- all corpora are local
- all scenarios are frozen JSON specs
- split roles are explicit: `pilot` is frozen, `dev` is tuneable, `validation` is frozen for selection, and `shadow_holdout` is private
- all tools are deterministic
- the calibrated ensemble detector profile is fit on local `pilot` and `dev` assets plus the pilot perturbation suite
- checkpoint grading separates visible-state adherence from ledger-state adherence
- perturbation regressions are run on controlled corruptions of real scenario state
- benchmark linting and coverage summaries are available from the CLI
- prompt pack versions are pinned
- resource profiles are pinned
- agent backend identity is pinned in result artifacts
- trace format is deterministic and replayable

## Known limitations

- the current public release still uses a deterministic scripted agent for smoke, regression, and local ablation checks
- live-model backends are available for external validation probes, but those runs are not yet part of the frozen public claim set
- the current release validates the benchmark harness more than frontier-model performance
- the current public `test` split is still small and should be expanded before strong final claims
- the shadow holdout is documented but intentionally not bundled in this public release
