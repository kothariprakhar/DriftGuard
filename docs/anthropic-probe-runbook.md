# Anthropic Probe Runbook

## Purpose

Run the smallest governed live-model probe before broader Anthropic evaluation.

This probe compares:

- `scripted_local`
- `anthropic_messages`

on the bundled manifest:

- `pilot_live_backend_probe`

The slice is intentionally small:

- 4 pilot scenarios
- 2 context systems
- 1 detector
- 1 policy
- 1 seed

That keeps spend and debugging surface low while still producing paired backend comparisons.

## What this run gives us

- first real Anthropic trace artifacts in the DriftGuard schema
- backend-aware summaries
- paired backend comparison against the scripted baseline
- token-usage totals for the probe

## Before you run it

You need:

- `ANTHROPIC_API_KEY` or `DRIFTGUARD_ANTHROPIC_API_KEY`
- a checked-out DriftGuard repo
- current benchmark artifacts already present in the repo

Recommended:

- run this in Google Colab Pro or another disposable runner
- save the `results/anthropic_probe` directory back into the repo workspace after the run

## Colab flow

### 1. Clone the repo

```bash
git clone <your-driftguard-repo-url>
cd DriftGuard
```

### 2. Set the Anthropic key

In Colab, set an environment variable in a code cell:

```python
import os
os.environ["ANTHROPIC_API_KEY"] = "YOUR_KEY_HERE"
os.environ["DRIFTGUARD_ANTHROPIC_MODEL"] = "claude-3-5-haiku-latest"
```

### 3. Run the probe

```bash
python3 scripts/run_anthropic_probe.py --output-root results/anthropic_probe --seed 31
```

### 4. Save the artifacts

The important outputs are:

- `results/anthropic_probe/summary_artifacts/summary.json`
- `results/anthropic_probe/summary_artifacts/runs.csv`
- all backend traces under `results/anthropic_probe/...`

Copy or sync the whole `results/anthropic_probe` directory back to your main workspace.

## Expected commands inside the probe

The script runs:

1. scripted baseline on `pilot_live_backend_probe`
2. Anthropic backend on the same slice
3. `summarize-results`
4. `compare-agent-backends`

## Spend discipline

Treat this as a probe, not a benchmark campaign.

Recommended guardrails:

- use one seed only
- do not expand contexts/policies/models yet
- stop after the first clean successful run

## What to do after the run

Once the artifacts are back in the repo, the next steps are:

1. inspect traces for formatting or control-flow failures
2. compare Anthropic vs scripted behavior
3. decide whether a reduced frozen live validation slice is justified
