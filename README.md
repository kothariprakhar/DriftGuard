# DriftGuard

DriftGuard is a ledger-centric benchmark and reference harness for task-intent drift in long-running agents.

The project focuses on one measurable reliability failure: an agent begins with a clear task contract, then gradually follows irrelevant, stale, adversarial, or conflicting context until its behavior no longer matches the original intent. DriftGuard provides a local benchmark, scenario format, trace ledger, detectors, interventions, graders, and reports for studying that failure mode.

## Current status

DriftGuard is a functional research-engineering repository. It includes a deterministic benchmark spine, a public 36-scenario benchmark, manifest-backed experiments, local scripted agents, optional live-model backends, perturbation suites, annotation packets, comparison utilities, and tests.

It is still incomplete in the sense that it is a benchmark and reference harness, not a production agent platform. The public results are designed to be reproducible and inspectable, but broader claims still require more external model runs, more human calibration, more scenario diversity, and independent replication.

## Why it exists

Long-running agents do not only fail by making one bad call. They often fail because their working context slowly stops representing the original user objective. That drift can come from summarization loss, retrieval noise, untrusted instructions, tool-state changes, memory edits, or intervention policies that create their own side effects.

DriftGuard makes this failure mode measurable. Instead of saying "the agent got confused," it records task contracts, checkpoints, context systems, detector outputs, policy interventions, and final outcomes so teams can ask more precise questions:

- Which context strategy preserved task intent?
- Which detector caught drift early enough to matter?
- Which intervention repaired the workflow without over-stopping?
- Which failures came from ambiguity, missing evidence, or adversarial content?

## What works today

- Versioned schemas for contracts, ledgers, traces, checkpoints, prompts, scenarios, and reports
- Public benchmark splits: `pilot`, `dev`, `validation`, and locked `test`
- Scenario families covering evidence synthesis, tool-state workflow, memory-update conflict, and adversarial input
- Context systems including raw transcript, summary, retrieval, ledger, and hybrid variants
- Detectors including null, rule-based, rubric, evidence alignment, summary faithfulness, and calibrated ensemble profiles
- Intervention policies including none, anchor refresh, ledger regeneration, rollback, safe stop, and adaptive
- Scripted local backend for deterministic regression checks
- Optional OpenAI-compatible and Anthropic live-model backends
- Manifest-backed experiment execution and replayable JSONL traces
- Perturbation suites, failure atlases, technical reports, benchmark cards, and annotation packets
- Unit tests across schemas, policies, graders, runners, experiments, reporting, calibration, and analysis

## Product manager perspective

The strongest product wedge is not a generic "agent safety platform." It is a narrow reliability evaluation product for teams building agents that must run beyond a single turn: support workflows, operations workflows, procurement, compliance review, and internal copilots.

The PM insight is that task-intent drift becomes most costly when the workflow has enough autonomy to save time but not enough observability to earn trust. A ledger gives product teams a way to explain what the agent believed the job was, when that belief changed, and whether an intervention helped or harmed the final outcome.

The repo therefore reads like a research artifact, but the product direction is an evaluation layer: benchmark a candidate agent architecture, compare memory/context strategies, choose intervention thresholds, and produce a report that engineering, risk, and product leaders can inspect together.

## Key trade-offs

- Narrow benchmark vs broad platform: Focusing on task-intent drift keeps the science crisp, but does not cover every agent risk.
- Deterministic local runs vs live-model realism: Scripted agents make results reproducible; live backends make results more realistic but more expensive and less stable.
- Ledger structure vs implementation overhead: A ledger improves auditability, but adds schema and integration work to agent systems.
- Early stopping vs unnecessary interruption: Safe-stop policies can prevent bad outcomes, but too many stops reduce agent usefulness.
- Public benchmark vs contamination risk: Public scenarios aid review and adoption, while locked/hidden splits remain important for credible evaluation.

## Concepts used

- Task-intent drift: Deviation from the original user objective over a long workflow.
- Ledger: Structured record of task contract, evidence, decisions, and checkpoints.
- Context system: Strategy for what information an agent sees at each step.
- Detector: Function that scores or flags potential drift.
- Policy: Intervention strategy triggered by a detector or checkpoint.
- Perturbation: Controlled change to context, memory, or evidence used to test robustness.
- Manifest: Declarative experiment plan that specifies scenarios, contexts, detectors, policies, and seeds.
- Trace replay: Re-running or inspecting a recorded agent trajectory.
- Paired bootstrap: Statistical comparison method for estimating deltas across paired runs.
- Annotation packet: Human-review bundle used to calibrate evaluator judgments.

## Quickstart

From the repository root:

```bash
python3 -m driftguard list-scenarios
python3 -m driftguard list-splits
python3 -m driftguard benchmark-stats
python3 -m driftguard smoke --output-root results/smoke
```

Run a manifest-backed slice:

```bash
python3 -m driftguard run-manifest pilot_baselines \
  --output-root results/experiments \
  --scenario pilot_evidence_brief \
  --context ledger_only \
  --detector rule_based \
  --policy none \
  --agent-backend scripted_local \
  --seed 7
```

Describe a manifest before running:

```bash
python3 -m driftguard describe-manifest validation_wave2_intervention_selection
```

Replay a trace:

```bash
python3 -m driftguard replay results/smoke/pilot_evidence_brief/raw_transcript/scripted_local/rule_based/none/seed-7/trace.jsonl
```

Run tests:

```bash
python3 -m pytest
```

## Live backend probes

Anthropic:

```bash
DRIFTGUARD_ANTHROPIC_API_KEY=... \
DRIFTGUARD_ANTHROPIC_MODEL=claude-3-5-haiku-latest \
python3 -m driftguard run-manifest pilot_baselines \
  --output-root results/live_probe \
  --scenario pilot_evidence_brief \
  --context ledger_only \
  --detector rule_based \
  --policy none \
  --agent-backend anthropic_messages \
  --seed 7
```

OpenAI-compatible:

```bash
DRIFTGUARD_OPENAI_API_KEY=... \
DRIFTGUARD_OPENAI_MODEL=gpt-4.1-mini \
python3 -m driftguard run-manifest pilot_baselines \
  --output-root results/live_probe_openai \
  --scenario pilot_evidence_brief \
  --context ledger_only \
  --detector rule_based \
  --policy none \
  --agent-backend openai_compatible \
  --seed 7
```

## Repository layout

```text
driftguard/                 Python package and CLI implementation
benchmark/                  Scenarios, splits, prompts, manifests, detector profiles
docs/                       Benchmark card, guides, roadmap, reproducibility notes
reports/                    Generated reports, ablations, annotation packets
tests/                      Unit and regression tests
scripts/                    Helper probes and experiment scripts
results/                    Local experiment outputs
```

## Useful report commands

```bash
python3 -m driftguard write-snapshot-report --output reports/benchmark_snapshot.md
python3 -m driftguard write-technical-report --output reports/technical_report.md --manifest validation_wave2_intervention_selection
python3 -m driftguard write-failure-atlas --output reports/failure_atlas.md --result-root results/validation_wave2_interventions_v3/summary_artifacts
python3 -m driftguard write-annotation-packet --annotation-set calibration_wave2 --output-root reports/annotation_wave2 --result-root results/validation_wave2_interventions_v3/summary_artifacts
```

## Next steps

- Expand live-model evaluations across more providers and agent styles.
- Add more enterprise workflow scenario families.
- Harden hidden and locked splits for external validation.
- Improve human annotation UX and agreement analysis.
- Package the benchmark as an easier installable CLI for third-party users.

## License

Apache-2.0. See `LICENSE`.
