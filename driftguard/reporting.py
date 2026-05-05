"""Generate lightweight markdown reports from benchmark artifacts."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

from driftguard.analysis import compare_contexts, compare_detectors, compare_policies
from driftguard.benchmark_audit import benchmark_stats
from driftguard.experiments import audit_manifest
from driftguard.registry import BENCHMARK_ROOT, load_experiment_manifest
from driftguard.serialization import load_json, load_jsonl


def _manifest_names() -> List[str]:
    return sorted(path.stem for path in (BENCHMARK_ROOT / "experiment_manifests").glob("*.json"))


def _format_context_table(summary: Dict[str, object]) -> List[str]:
    lines = ["| Context | Runs | Success Rate | Mean Score |", "|---|---:|---:|---:|"]
    for context, values in sorted(summary.get("by_context", {}).items()):
        lines.append(
            f"| {context} | {values.get('runs', 0)} | {values.get('success_rate', 0.0):.2f} | {values.get('mean_score', 0.0):.2f} |"
        )
    return lines


def _format_group_table(title_key: str, summary: Dict[str, object], group_key: str) -> List[str]:
    lines = [f"| {title_key} | Runs | Success Rate | Mean Score |", "|---|---:|---:|---:|"]
    for label, values in sorted(summary.get(group_key, {}).items()):
        lines.append(
            f"| {label} | {values.get('runs', 0)} | {values.get('success_rate', 0.0):.2f} | {values.get('mean_score', 0.0):.2f} |"
        )
    return lines


def _best_contexts(summary: Dict[str, object]) -> List[str]:
    contexts = summary.get("by_context", {})
    ranked = sorted(
        contexts.items(),
        key=lambda item: (item[1].get("success_rate", 0.0), item[1].get("mean_score", 0.0), item[0]),
        reverse=True,
    )
    return [name for name, _ in ranked]


def _weak_contexts(summary: Dict[str, object]) -> List[str]:
    contexts = summary.get("by_context", {})
    weak = []
    for name in ("raw_transcript", "summary_only", "retrieval_only"):
        if name in contexts:
            weak.append(name)
    return weak


def _format_suite_summary(summary: Dict[str, object]) -> List[str]:
    return [
        f"- `cases`: {summary.get('total_cases', 0)}",
        f"- `passed`: {summary.get('passed_cases', 0)}",
        f"- `pass_rate`: {summary.get('pass_rate', 0.0):.2f}",
        f"- `mean_score_delta`: {summary.get('mean_score_delta', 0.0):.2f}",
    ]


def _read_runs_csv(path: Path) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(dict(row))
    return rows


def _context_family_table(rows: Sequence[Dict[str, str]]) -> List[str]:
    grouped: Dict[str, Dict[str, Dict[str, float]]] = {}
    for row in rows:
        family = row["family"]
        context = row["context_system"]
        bucket = grouped.setdefault(family, {}).setdefault(context, {"runs": 0.0, "success": 0.0, "score_total": 0.0})
        bucket["runs"] += 1
        bucket["success"] += 1 if row["success"] == "True" else 0
        bucket["score_total"] += float(row["score"])
    lines = [
        "| Family | Context | Runs | Success Rate | Mean Score |",
        "|---|---|---:|---:|---:|",
    ]
    for family in sorted(grouped):
        for context in sorted(grouped[family]):
            bucket = grouped[family][context]
            lines.append(
                f"| {family} | {context} | {int(bucket['runs'])} | {bucket['success'] / bucket['runs']:.2f} | {bucket['score_total'] / bucket['runs']:.2f} |"
            )
    return lines


def _pairwise_delta_table(summary_root: Path, primary_context: str, baseline_contexts: Sequence[str]) -> List[str]:
    comparison = compare_contexts(summary_root, primary_context, baseline_contexts)
    lines = [
        "| Comparison | Paired Runs | Success Delta | Success 95% CI | Mean Score Delta | Score 95% CI |",
        "|---|---:|---:|---|---:|---|",
    ]
    for baseline in baseline_contexts:
        stats = comparison["comparisons"].get(baseline, {})
        if not stats or not stats.get("paired_runs"):
            continue
        success_ci = stats["success_delta_ci"]
        score_ci = stats["mean_score_delta_ci"]
        lines.append(
            f"| {primary_context} vs {baseline} | {stats['paired_runs']} | {stats['success_delta']:.2f} | [{success_ci[0]:.2f}, {success_ci[1]:.2f}] | {stats['mean_score_delta']:.2f} | [{score_ci[0]:.2f}, {score_ci[1]:.2f}] |"
        )
    return lines


def _group_comparison_table(
    comparison: Dict[str, object],
    primary_value: str,
) -> List[str]:
    lines = [
        "| Comparison | Paired Runs | Success Delta | Success 95% CI | Mean Score Delta | Score 95% CI |",
        "|---|---:|---:|---|---:|---|",
    ]
    for baseline, stats in comparison.get("comparisons", {}).items():
        if not stats or not stats.get("paired_runs"):
            continue
        success_ci = stats["success_delta_ci"]
        score_ci = stats["mean_score_delta_ci"]
        lines.append(
            f"| {primary_value} vs {baseline} | {stats['paired_runs']} | {stats['success_delta']:.2f} | [{success_ci[0]:.2f}, {success_ci[1]:.2f}] | {stats['mean_score_delta']:.2f} | [{score_ci[0]:.2f}, {score_ci[1]:.2f}] |"
        )
    return lines


def _failure_examples(rows: Sequence[Dict[str, str]]) -> List[str]:
    examples: List[str] = []
    seen_families: set[str] = set()
    for row in sorted(rows, key=lambda item: (item["family"], item["context_system"], item["scenario_id"])):
        if row["success"] == "True":
            continue
        family = row["family"]
        if family in seen_families:
            continue
        seen_families.add(family)
        drift_step = row["first_drift_step"] or "-"
        examples.append(
            f"- `{row['scenario_id']}` with `{row['context_system']}` fails at `{drift_step}` and ends with score `{float(row['score']):.2f}`."
        )
    return examples


def _context_policy_table(summary: Dict[str, object]) -> List[str]:
    lines = ["| Context | Policy | Runs | Success Rate | Mean Score |", "|---|---|---:|---:|---:|"]
    by_context_policy = summary.get("by_context_policy", {})
    for context, policies in sorted(by_context_policy.items()):
        for policy, values in sorted(policies.items()):
            lines.append(
                f"| {context} | {policy} | {values.get('runs', 0)} | {values.get('success_rate', 0.0):.2f} | {values.get('mean_score', 0.0):.2f} |"
            )
    return lines


def _top_configurations(rows: Sequence[Dict[str, str]], limit: int = 12) -> List[str]:
    grouped: Dict[tuple[str, str, str, str], Dict[str, float]] = {}
    for row in rows:
        key = (row["context_system"], row.get("agent_backend", "scripted_local"), row["detector"], row["policy"])
        bucket = grouped.setdefault(key, {"runs": 0.0, "successes": 0.0, "score_total": 0.0})
        bucket["runs"] += 1
        bucket["successes"] += 1 if row["success"] == "True" else 0
        bucket["score_total"] += float(row["score"])
    ranked = []
    for key, bucket in grouped.items():
        ranked.append(
            (
                bucket["successes"] / bucket["runs"],
                bucket["score_total"] / bucket["runs"],
                key,
                bucket,
            )
        )
    ranked.sort(key=lambda item: (item[0], item[1], item[2][0], item[2][1], item[2][2], item[2][3]), reverse=True)
    lines = [
        "| Context | Backend | Detector | Policy | Runs | Success Rate | Mean Score |",
        "|---|---|---|---|---:|---:|---:|",
    ]
    for _, _, key, bucket in ranked[:limit]:
        context, agent_backend, detector, policy = key
        lines.append(
            f"| {context} | {agent_backend} | {detector} | {policy} | {int(bucket['runs'])} | {bucket['successes'] / bucket['runs']:.2f} | {bucket['score_total'] / bucket['runs']:.2f} |"
        )
    return lines


def _resolve_artifact_path(path_str: str) -> Path:
    candidate = Path(path_str)
    if candidate.is_absolute():
        return candidate
    return BENCHMARK_ROOT.parent / candidate


def _failure_detail_rows(rows: Sequence[Dict[str, str]]) -> List[Dict[str, str]]:
    details: List[Dict[str, str]] = []
    seen_families: set[str] = set()
    for row in sorted(rows, key=lambda item: (item["family"], item["context_system"], item["scenario_id"])):
        if row["success"] == "True":
            continue
        family = row["family"]
        if family in seen_families:
            continue
        seen_families.add(family)
        trace_rows = load_jsonl(_resolve_artifact_path(row["trace_path"]))
        first_drift_step = row["first_drift_step"]
        focus_row = next((item for item in trace_rows if item.get("step_id") == first_drift_step), trace_rows[-1])
        details.append(
            {
                "family": family,
                "scenario_id": row["scenario_id"],
                "context_system": row["context_system"],
                "agent_backend": row.get("agent_backend", "scripted_local"),
                "first_drift_step": first_drift_step,
                "score": row["score"],
                "chosen_drift_label": str(focus_row.get("chosen_drift_label") or "-"),
                "reason_codes": ", ".join(focus_row.get("reason_codes", [])) or "-",
                "content": str(focus_row.get("content", "")),
                "trace_path": str(_resolve_artifact_path(row["trace_path"])),
            }
        )
    return details


def build_snapshot_report(
    output_path: Path,
    result_roots: Sequence[Path],
    perturbation_roots: Sequence[Path],
) -> Path:
    stats = benchmark_stats()
    lines: List[str] = []
    lines.append("# DriftGuard Benchmark Snapshot")
    lines.append("")
    lines.append(f"_Generated: {datetime.now(timezone.utc).isoformat()}_")
    lines.append("")
    lines.append("## Benchmark Coverage")
    lines.append("")
    lines.append(f"- `total_scenarios`: {stats['total_scenarios']}")
    for split, count in sorted(stats["split_counts"].items()):
        families = stats["split_family_counts"].get(split, {})
        family_text = ", ".join(f"{family}:{value}" for family, value in sorted(families.items()))
        lines.append(f"- `{split}`: {count} scenarios ({family_text})")

    lines.append("")
    lines.append("## Manifests")
    lines.append("")
    for manifest_name in _manifest_names():
        manifest = load_experiment_manifest(manifest_name)
        audit = audit_manifest(manifest)
        lines.append(f"### `{manifest_name}`")
        lines.append("")
        lines.append(f"- `stage`: {manifest.manifest_stage}")
        lines.append(f"- `scenario_count`: {len(manifest.scenarios)}")
        lines.append(f"- `splits`: {', '.join(audit.splits)}")
        if audit.hidden_splits:
            lines.append(f"- `hidden_splits`: {', '.join(audit.hidden_splits)}")
        lines.append("")

    if result_roots:
        lines.append("## Result Summaries")
        lines.append("")
        for root in result_roots:
            summary_path = root / "summary.json"
            if not summary_path.exists():
                continue
            summary = load_json(summary_path)
            lines.append(f"### `{root}`")
            lines.append("")
            lines.append(f"- `total_runs`: {summary.get('total_runs', 0)}")
            lines.append(f"- `success_rate`: {summary.get('success_rate', 0.0):.2f}")
            lines.append(f"- `mean_score`: {summary.get('mean_score', 0.0):.2f}")
            lines.append(
                f"- `mean_visible_checkpoint_adherence`: {summary.get('mean_visible_checkpoint_adherence', 0.0):.2f}"
            )
            lines.append(
                f"- `mean_ledger_checkpoint_adherence`: {summary.get('mean_ledger_checkpoint_adherence', 0.0):.2f}"
            )
            lines.append("")
            lines.extend(_format_context_table(summary))
            lines.append("")

    if perturbation_roots:
        lines.append("## Perturbation Suites")
        lines.append("")
        for root in perturbation_roots:
            summary_path = root / "summary.json"
            if not summary_path.exists():
                continue
            summary = load_json(summary_path)
            lines.append(f"### `{root}`")
            lines.append("")
            lines.extend(_format_suite_summary(summary))
            lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return output_path


def build_technical_report(
    output_path: Path,
    result_root: Path,
    perturbation_root: Path,
    manifest_name: str,
) -> Path:
    summary = load_json(result_root / "summary.json")
    runs = _read_runs_csv(result_root / "runs.csv")
    perturbation_summary = load_json(perturbation_root / "summary.json")
    manifest = load_experiment_manifest(manifest_name)
    audit = audit_manifest(manifest)
    stats = benchmark_stats()

    lines: List[str] = []
    lines.append("# DriftGuard Technical Report")
    lines.append("")
    lines.append(f"_Generated: {datetime.now(timezone.utc).isoformat()}_")
    lines.append("")
    lines.append("## Thesis")
    lines.append("")
    lines.append(
        "DriftGuard benchmarks task-intent drift from observable state and tests whether ledger-centric context management preserves the original task contract better than weaker baselines."
    )
    lines.append("")
    lines.append("## Benchmark")
    lines.append("")
    lines.append(f"- `public_scenarios`: {stats['total_scenarios']}")
    lines.append(f"- `selection_manifest`: {manifest.name}")
    lines.append(f"- `manifest_stage`: {manifest.manifest_stage}")
    lines.append(f"- `manifest_splits`: {', '.join(audit.splits)}")
    lines.append(f"- `selection_scenarios`: {len(manifest.scenarios)}")
    lines.append("")
    lines.append("## Main Result")
    lines.append("")
    best_contexts = _best_contexts(summary)[:3]
    weak_contexts = _weak_contexts(summary)
    if best_contexts:
        strong_context_text = ", ".join(
            f"`{context}` ({summary['by_context'][context]['success_rate']:.2f})" for context in best_contexts
        )
        lines.append(
            f"On the current evaluated slice, the strongest context systems are {strong_context_text}."
        )
    if weak_contexts:
        weak_context_text = ", ".join(
            f"`{context}` ({summary['by_context'][context]['success_rate']:.2f})" for context in weak_contexts
        )
        lines.append(
            f"The weakest baselines on the same slice are {weak_context_text}, which is why the aggregate mixed-context success rate remains `success_rate={summary['success_rate']:.2f}`."
        )
    if "anchor_refresh" in summary.get("by_policy", {}) and weak_contexts:
        policy_comparison = compare_policies(
            result_root,
            "anchor_refresh",
            [policy for policy in ("none", "ledger_regeneration", "rollback", "safe_stop", "adaptive") if policy in summary.get("by_policy", {})],
            filters={"context_system": weak_contexts},
        )
        anchor_vs_none = policy_comparison.get("comparisons", {}).get("none")
        if anchor_vs_none and anchor_vs_none.get("paired_runs"):
            success_ci = anchor_vs_none["success_delta_ci"]
            lines.append(
                f"On weak contexts only, `anchor_refresh` improves success over `none` by `{anchor_vs_none['success_delta']:.2f}` with paired bootstrap `95% CI [{success_ci[0]:.2f}, {success_ci[1]:.2f}]`."
            )
    lines.append("")
    lines.append("### Context Performance")
    lines.append("")
    lines.extend(_format_context_table(summary))
    lines.append("")
    lines.append("### Context By Family")
    lines.append("")
    lines.extend(_context_family_table(runs))
    lines.append("")
    lines.append("### Pairwise Deltas")
    lines.append("")
    lines.extend(_pairwise_delta_table(result_root, "ledger_only", ["raw_transcript", "summary_only", "ledger_retrieval"]))
    lines.append("")
    lines.append("## Checkpoint Signal")
    lines.append("")
    lines.append(f"- `mean_visible_checkpoint_adherence`: {summary.get('mean_visible_checkpoint_adherence', 0.0):.2f}")
    lines.append(f"- `mean_ledger_checkpoint_adherence`: {summary.get('mean_ledger_checkpoint_adherence', 0.0):.2f}")
    lines.append("")
    lines.append("## Perturbation Regression")
    lines.append("")
    lines.extend(_format_suite_summary(perturbation_summary))
    lines.append("")
    lines.append("## Representative Deterministic Failures")
    lines.append("")
    lines.extend(_failure_examples(runs))
    lines.append("")
    lines.append("## Limitations")
    lines.append("")
    lines.append("- These are deterministic harness results, not frontier-model evaluation results.")
    lines.append("- The public benchmark is still smaller than the intended full release.")
    lines.append("- Confidence intervals are paired bootstrap intervals over matched scenario/seed runs on the evaluated slice.")
    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append(
        "The current evidence supports the narrow claim that this benchmark exposes memory and anchoring failures cleanly and that ledger-centric baselines preserve intent on the included scenarios better than transcript-only or summary-only baselines."
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return output_path


def build_ablation_report(output_path: Path, result_root: Path, manifest_name: str) -> Path:
    summary = load_json(result_root / "summary.json")
    runs = _read_runs_csv(result_root / "runs.csv")
    manifest = load_experiment_manifest(manifest_name)
    audit = audit_manifest(manifest)

    lines: List[str] = []
    lines.append("# DriftGuard Ablation Report")
    lines.append("")
    lines.append(f"_Generated: {datetime.now(timezone.utc).isoformat()}_")
    lines.append("")
    lines.append("## Evaluated Slice")
    lines.append("")
    lines.append(f"- `result_root`: {result_root}")
    lines.append(f"- `manifest`: {manifest.name}")
    lines.append(f"- `stage`: {manifest.manifest_stage}")
    lines.append(f"- `splits`: {', '.join(audit.splits)}")
    lines.append(f"- `runs`: {summary.get('total_runs', 0)}")
    lines.append("")
    lines.append("## Context Ablation")
    lines.append("")
    lines.extend(_format_group_table("Context", summary, "by_context"))
    lines.append("")
    lines.append("## Policy Ablation")
    lines.append("")
    lines.extend(_format_group_table("Policy", summary, "by_policy"))
    lines.append("")
    lines.append("## Detector Ablation")
    lines.append("")
    lines.extend(_format_group_table("Detector", summary, "by_detector"))
    if summary.get("by_agent_backend"):
        lines.append("")
        lines.append("## Agent Backend Ablation")
        lines.append("")
        lines.extend(_format_group_table("Agent Backend", summary, "by_agent_backend"))
    lines.append("")
    lines.append("## Context x Policy")
    lines.append("")
    lines.extend(_context_policy_table(summary))
    lines.append("")
    lines.append("## Top Configurations")
    lines.append("")
    lines.extend(_top_configurations(runs))
    lines.append("")

    primary_context = "ledger_only" if "ledger_only" in summary.get("by_context", {}) else next(iter(summary.get("by_context", {})), "")
    if primary_context:
        baselines = [context for context in sorted(summary.get("by_context", {})) if context != primary_context]
        if baselines:
            lines.append("## Paired Context Comparisons")
            lines.append("")
            lines.extend(_pairwise_delta_table(result_root, primary_context, baselines))
            lines.append("")

    weak_contexts = [
        context
        for context in ("raw_transcript", "summary_only", "retrieval_only")
        if context in summary.get("by_context", {})
    ]
    if "anchor_refresh" in summary.get("by_policy", {}) and weak_contexts:
        lines.append("## Weak-Context Policy Comparisons")
        lines.append("")
        policy_comparison = compare_policies(
            result_root,
            "anchor_refresh",
            [policy for policy in ("none", "ledger_regeneration", "rollback", "safe_stop", "adaptive") if policy in summary.get("by_policy", {})],
            filters={"context_system": weak_contexts},
        )
        lines.extend(_group_comparison_table(policy_comparison, "anchor_refresh"))
        lines.append("")

    if "rule_based" in summary.get("by_detector", {}) and "calibrated_ensemble" in summary.get("by_detector", {}):
        lines.append("## Detector Comparisons")
        lines.append("")
        detector_comparison = compare_detectors(
            result_root,
            "rule_based",
            ["calibrated_ensemble"],
        )
        lines.extend(_group_comparison_table(detector_comparison, "rule_based"))
        lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return output_path


def build_failure_atlas(output_path: Path, result_root: Path) -> Path:
    summary = load_json(result_root / "summary.json")
    runs = _read_runs_csv(result_root / "runs.csv")
    failures = _failure_detail_rows(runs)

    lines: List[str] = []
    lines.append("# DriftGuard Failure Atlas")
    lines.append("")
    lines.append(f"_Generated: {datetime.now(timezone.utc).isoformat()}_")
    lines.append("")
    lines.append("## Slice Summary")
    lines.append("")
    lines.append(f"- `result_root`: {result_root}")
    lines.append(f"- `total_runs`: {summary.get('total_runs', 0)}")
    lines.append(f"- `success_rate`: {summary.get('success_rate', 0.0):.2f}")
    lines.append(f"- `mean_score`: {summary.get('mean_score', 0.0):.2f}")
    lines.append("")
    lines.append("## Representative Failures")
    lines.append("")
    for item in failures:
        lines.append(f"### `{item['family']}`")
        lines.append("")
        lines.append(f"- `scenario_id`: {item['scenario_id']}")
        lines.append(f"- `context_system`: {item['context_system']}")
        lines.append(f"- `agent_backend`: {item['agent_backend']}")
        lines.append(f"- `first_drift_step`: {item['first_drift_step'] or '-'}")
        lines.append(f"- `chosen_drift_label`: {item['chosen_drift_label']}")
        lines.append(f"- `reason_codes`: {item['reason_codes']}")
        lines.append(f"- `score`: {float(item['score']):.2f}")
        lines.append(f"- `trace`: [{Path(item['trace_path']).name}]({item['trace_path']})")
        lines.append(f"- `failure_content`: {item['content']}")
        lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return output_path
