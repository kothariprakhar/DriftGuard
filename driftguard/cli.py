"""CLI entry point."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, List, Optional

from driftguard.agent_backends import ALL_AGENT_BACKENDS
from driftguard.analysis import compare_agent_backends, compare_contexts, compare_detectors, compare_policies, summarize_results
from driftguard.annotation import build_annotation_packet
from driftguard.benchmark_audit import benchmark_stats, lint_benchmark
from driftguard.calibration import compute_annotation_agreement, score_annotation_response
from driftguard.detector_training import default_profile_path, fit_detector_profile
from driftguard.experiments import audit_manifest, list_hidden_run_records, list_locked_run_records, run_manifest
from driftguard.perturbations import run_suite
from driftguard.reporting import build_ablation_report, build_failure_atlas, build_snapshot_report, build_technical_report
from driftguard.registry import load_annotation_set, load_experiment_manifest, load_scenario_index, load_split_registry
from driftguard.runner import run_episode
from driftguard.traces import recompute_metrics, replay_trace
from driftguard.version import __version__


def _print_table(rows: List[List[str]]) -> None:
    widths = [max(len(row[index]) for row in rows) for index in range(len(rows[0]))]
    for row in rows:
        print("  ".join(value.ljust(widths[index]) for index, value in enumerate(row)))


def command_list_scenarios(split: Optional[str], family: Optional[str]) -> int:
    rows = [["scenario_id", "split", "family", "path"]]
    for item in load_scenario_index(split=split, family=family):
        rows.append([item["scenario_id"], item["split"], item["family"], item["path"]])
    _print_table(rows)
    return 0


def command_list_splits() -> int:
    registry = load_split_registry()
    rows = [["split", "public", "frozen", "tuning_allowed", "hidden", "notes"]]
    for item in registry.get("splits", []):
        rows.append(
            [
                item["split"],
                "yes" if item.get("public") else "no",
                "yes" if item.get("frozen") else "no",
                "yes" if item.get("tuning_allowed") else "no",
                "yes" if item.get("hidden") else "no",
                item.get("notes", ""),
            ]
        )
    _print_table(rows)
    return 0


def command_list_agent_backends() -> int:
    rows = [["agent_backend", "backend_kind"]]
    for name, backend in sorted(ALL_AGENT_BACKENDS.items()):
        rows.append([name, backend.backend_kind])
    _print_table(rows)
    return 0


def command_smoke(output_root: Path) -> int:
    matrix = [
        ("pilot_evidence_brief", "raw_transcript", "none"),
        ("pilot_evidence_brief", "summary_only", "none"),
        ("pilot_evidence_brief", "ledger_only", "none"),
        ("pilot_tool_order", "raw_transcript", "anchor_refresh"),
        ("pilot_tool_order", "summary_only", "anchor_refresh"),
        ("pilot_tool_order", "ledger_only", "anchor_refresh"),
    ]
    rows = [["scenario", "context", "policy", "success", "score", "first_drift_step"]]
    for scenario_id, context_system, policy in matrix:
        result = run_episode(
            scenario_id=scenario_id,
            context_system=context_system,
            policy=policy,
            detector="rule_based",
            output_root=output_root,
        )
        rows.append(
            [
                scenario_id,
                context_system,
                policy,
                "yes" if result.success else "no",
                f"{result.score:.2f}",
                result.first_drift_step or "-",
            ]
        )
    _print_table(rows)
    return 0


def command_replay(trace_path: Path) -> int:
    result, _, _ = replay_trace(trace_path)
    metrics = recompute_metrics(trace_path)
    print(f"scenario_id: {result.scenario_id}")
    print(f"context_system: {result.context_system}")
    print(f"policy: {result.policy}")
    print(f"success: {result.success}")
    print(f"score: {result.score:.2f}")
    print(f"recomputed_metrics: {metrics}")
    return 0


def command_run_manifest(
    manifest_name: str,
    output_root: Path,
    limit: Optional[int],
    seeds: List[int],
    scenarios: List[str],
    contexts: List[str],
    detectors: List[str],
    policies: List[str],
    agent_backends: List[str],
    allow_hidden: bool,
    permit_repeated_hidden: bool,
    permit_repeated_locked: bool,
) -> int:
    summary = run_manifest(
        manifest_name,
        output_root=output_root,
        seeds=seeds or None,
        limit=limit,
        scenario_filter=scenarios or None,
        context_filter=contexts or None,
        detector_filter=detectors or None,
        policy_filter=policies or None,
        agent_backend_filter=agent_backends or None,
        allow_hidden=allow_hidden,
        permit_repeated_hidden=permit_repeated_hidden,
        permit_repeated_locked=permit_repeated_locked,
    )
    rows = [["manifest", "stage", "runs", "successes", "success_rate", "splits", "agent_backends", "output_root"]]
    rows.append(
        [
            summary.manifest_name,
            summary.manifest_stage,
            str(summary.total_runs),
            str(summary.successes),
            f"{summary.success_rate:.2f}",
            ",".join(sorted(summary.split_counts)),
            ",".join(summary.agent_backends),
            summary.output_root,
        ]
    )
    _print_table(rows)
    return 0


def command_run_perturbations(
    suite_name: str,
    output_root: Path,
    limit: Optional[int],
    case_ids: List[str],
) -> int:
    summary = run_suite(suite_name, output_root=output_root, limit=limit, case_filter=case_ids or None)
    rows = [["suite", "cases", "passed", "pass_rate", "mean_score_delta"]]
    rows.append(
        [
            summary["suite_name"],
            str(summary["total_cases"]),
            str(summary["passed_cases"]),
            f"{summary['pass_rate']:.2f}",
            f"{summary['mean_score_delta']:.2f}",
        ]
    )
    _print_table(rows)
    return 0


def command_describe_manifest(manifest_name: str) -> int:
    manifest = load_experiment_manifest(manifest_name)
    audit = audit_manifest(manifest)
    rows = [["manifest", "stage", "splits", "hidden", "frozen", "tuneable", "backends", "scenarios"]]
    rows.append(
        [
            audit.manifest_name,
            audit.manifest_stage,
            ",".join(audit.splits),
            ",".join(audit.hidden_splits) or "-",
            ",".join(audit.frozen_splits) or "-",
            ",".join(audit.tuning_allowed_splits) or "-",
            ",".join(manifest.agent_backends),
            str(sum(audit.split_counts.values())),
        ]
    )
    _print_table(rows)
    return 0


def command_list_hidden_runs() -> int:
    records = list_hidden_run_records()
    rows = [["manifest", "recorded_at", "splits", "runs", "success_rate", "output_root"]]
    for item in records:
        rows.append(
            [
                str(item.get("manifest_name", "")),
                str(item.get("recorded_at", "")),
                ",".join(item.get("splits", [])) if isinstance(item.get("splits"), list) else str(item.get("splits", "")),
                str(item.get("total_runs", "")),
                f"{float(item.get('success_rate', 0.0)):.2f}",
                str(item.get("output_root", "")),
            ]
        )
    if len(rows) == 1:
        rows.append(["-", "-", "-", "0", "0.00", "-"])
    _print_table(rows)
    return 0


def command_list_locked_runs() -> int:
    records = list_locked_run_records()
    rows = [["manifest", "stage", "recorded_at", "splits", "runs", "success_rate", "output_root"]]
    for item in records:
        rows.append(
            [
                str(item.get("manifest_name", "")),
                str(item.get("manifest_stage", "")),
                str(item.get("recorded_at", "")),
                ",".join(item.get("splits", [])) if isinstance(item.get("splits"), list) else str(item.get("splits", "")),
                str(item.get("total_runs", "")),
                f"{float(item.get('success_rate', 0.0)):.2f}",
                str(item.get("output_root", "")),
            ]
        )
    if len(rows) == 1:
        rows.append(["-", "-", "-", "-", "0", "0.00", "-"])
    _print_table(rows)
    return 0


def command_benchmark_stats() -> int:
    stats = benchmark_stats()
    rows = [["split", "scenario_count", "families"]]
    split_family_counts = stats["split_family_counts"]
    split_counts = stats["split_counts"]
    for split in sorted(split_counts):
        families = split_family_counts.get(split, {})
        family_label = ",".join(f"{family}:{count}" for family, count in sorted(families.items()))
        rows.append([split, str(split_counts[split]), family_label])
    _print_table(rows)
    return 0


def command_lint_benchmark() -> int:
    report = lint_benchmark()
    rows = [["status", "errors", "warnings", "total_scenarios"]]
    rows.append(
        [
            "ok" if report["ok"] else "fail",
            str(len(report["errors"])),
            str(len(report["warnings"])),
            str(report["stats"]["total_scenarios"]),
        ]
    )
    _print_table(rows)
    for error in report["errors"]:
        print(f"ERROR: {error}")
    for warning in report["warnings"]:
        print(f"WARNING: {warning}")
    return 0 if report["ok"] else 1


def command_summarize_results(results_root: Path, output_root: Path) -> int:
    summary = summarize_results(results_root, output_root=output_root)
    rows = [["runs", "success_rate", "mean_score", "mean_visible_cp", "mean_ledger_cp", "agent_backends", "backend_tokens", "backend_requests"]]
    rows.append(
        [
            str(summary["total_runs"]),
            f"{summary['success_rate']:.2f}",
            f"{summary['mean_score']:.2f}",
            f"{summary['mean_visible_checkpoint_adherence']:.2f}",
            f"{summary['mean_ledger_checkpoint_adherence']:.2f}",
            ",".join(sorted(summary.get("by_agent_backend", {}))),
            str(summary.get("total_backend_tokens", 0)),
            str(summary.get("total_backend_requests", 0)),
        ]
    )
    _print_table(rows)
    return 0


def command_write_snapshot_report(output_path: Path, result_roots: List[str], perturbation_roots: List[str]) -> int:
    resolved_results = [Path(item) for item in result_roots]
    resolved_perturbations = [Path(item) for item in perturbation_roots]
    build_snapshot_report(output_path, resolved_results, resolved_perturbations)
    print(str(output_path))
    return 0


def command_write_technical_report(
    output_path: Path,
    result_root: Path,
    perturbation_root: Path,
    manifest_name: str,
) -> int:
    build_technical_report(output_path, result_root=result_root, perturbation_root=perturbation_root, manifest_name=manifest_name)
    print(str(output_path))
    return 0


def command_write_annotation_packet(annotation_set_name: str, output_root: Path, result_roots: List[str]) -> int:
    if not result_roots:
        raise ValueError("write-annotation-packet requires at least one --result-root")
    load_annotation_set(annotation_set_name)
    summary = build_annotation_packet(
        output_root=output_root,
        annotation_set_name=annotation_set_name,
        result_roots=[Path(item) for item in result_roots],
    )
    rows = [["annotation_set", "cases", "packet", "answer_key", "markdown", "response_template", "reviewer_instructions"]]
    rows.append(
        [
            str(summary["annotation_set"]),
            str(summary["case_count"]),
            str(summary["packet_path"]),
            str(summary["answer_key_path"]),
            str(summary["markdown_path"]),
            str(summary["response_template_path"]),
            str(summary["reviewer_instructions_path"]),
        ]
    )
    _print_table(rows)
    return 0


def command_compute_annotation_agreement(response_paths: List[str]) -> int:
    summary = compute_annotation_agreement([Path(item) for item in response_paths])
    rows = [["field", "exact_match_rate", "cohens_kappa", "extra"]]
    for field, values in summary["field_metrics"].items():
        extra = "-"
        if field == "earliest_visible_drift_step":
            extra = f"within_1={values['within_one_step_rate']:.2f}"
        elif field == "severity":
            extra = f"weighted_kappa={values['weighted_kappa']:.2f}"
        rows.append([field, f"{values['exact_match_rate']:.2f}", f"{values['cohens_kappa']:.2f}", extra])
    _print_table(rows)
    return 0


def command_score_annotation_response(response_path: Path, answer_key_path: Path) -> int:
    summary = score_annotation_response(response_path, answer_key_path)
    rows = [["field", "accuracy"]]
    for field, accuracy in summary["field_accuracy"].items():
        rows.append([field, f"{accuracy:.2f}"])
    _print_table(rows)
    return 0


def command_compare_contexts(summary_root: Path, primary_context: str, baselines: List[str]) -> int:
    summary = compare_contexts(summary_root, primary_context, baselines)
    rows = [["comparison", "paired_runs", "success_delta", "success_ci", "score_delta", "score_ci"]]
    for baseline, values in summary["comparisons"].items():
        success_ci = values["success_delta_ci"]
        score_ci = values["mean_score_delta_ci"]
        rows.append(
            [
                f"{primary_context} vs {baseline}",
                str(values["paired_runs"]),
                f"{values['success_delta']:.2f}",
                f"[{success_ci[0]:.2f}, {success_ci[1]:.2f}]",
                f"{values['mean_score_delta']:.2f}",
                f"[{score_ci[0]:.2f}, {score_ci[1]:.2f}]",
            ]
        )
    _print_table(rows)
    return 0


def command_compare_policies(summary_root: Path, primary_policy: str, baselines: List[str], contexts: List[str], detectors: List[str]) -> int:
    filters = {}
    if contexts:
        filters["context_system"] = contexts
    if detectors:
        filters["detector"] = detectors
    summary = compare_policies(summary_root, primary_policy, baselines, filters=filters or None)
    rows = [["comparison", "paired_runs", "success_delta", "success_ci", "score_delta", "score_ci"]]
    for baseline, values in summary["comparisons"].items():
        success_ci = values["success_delta_ci"]
        score_ci = values["mean_score_delta_ci"]
        rows.append(
            [
                f"{primary_policy} vs {baseline}",
                str(values["paired_runs"]),
                f"{values['success_delta']:.2f}",
                f"[{success_ci[0]:.2f}, {success_ci[1]:.2f}]",
                f"{values['mean_score_delta']:.2f}",
                f"[{score_ci[0]:.2f}, {score_ci[1]:.2f}]",
            ]
        )
    _print_table(rows)
    return 0


def command_compare_detectors(summary_root: Path, primary_detector: str, baselines: List[str], contexts: List[str], policies: List[str]) -> int:
    filters = {}
    if contexts:
        filters["context_system"] = contexts
    if policies:
        filters["policy"] = policies
    summary = compare_detectors(summary_root, primary_detector, baselines, filters=filters or None)
    rows = [["comparison", "paired_runs", "success_delta", "success_ci", "score_delta", "score_ci"]]
    for baseline, values in summary["comparisons"].items():
        success_ci = values["success_delta_ci"]
        score_ci = values["mean_score_delta_ci"]
        rows.append(
            [
                f"{primary_detector} vs {baseline}",
                str(values["paired_runs"]),
                f"{values['success_delta']:.2f}",
                f"[{success_ci[0]:.2f}, {success_ci[1]:.2f}]",
                f"{values['mean_score_delta']:.2f}",
                f"[{score_ci[0]:.2f}, {score_ci[1]:.2f}]",
            ]
        )
    _print_table(rows)
    return 0


def command_compare_agent_backends(
    summary_root: Path,
    primary_backend: str,
    baselines: List[str],
    contexts: List[str],
    detectors: List[str],
    policies: List[str],
) -> int:
    filters = {}
    if contexts:
        filters["context_system"] = contexts
    if detectors:
        filters["detector"] = detectors
    if policies:
        filters["policy"] = policies
    summary = compare_agent_backends(summary_root, primary_backend, baselines, filters=filters or None)
    rows = [["comparison", "paired_runs", "success_delta", "success_ci", "score_delta", "score_ci"]]
    for baseline, values in summary["comparisons"].items():
        success_ci = values["success_delta_ci"]
        score_ci = values["mean_score_delta_ci"]
        rows.append(
            [
                f"{primary_backend} vs {baseline}",
                str(values["paired_runs"]),
                f"{values['success_delta']:.2f}",
                f"[{success_ci[0]:.2f}, {success_ci[1]:.2f}]",
                f"{values['mean_score_delta']:.2f}",
                f"[{score_ci[0]:.2f}, {score_ci[1]:.2f}]",
            ]
        )
    _print_table(rows)
    return 0


def command_write_failure_atlas(output_path: Path, result_root: Path) -> int:
    build_failure_atlas(output_path, result_root)
    print(str(output_path))
    return 0


def command_write_ablation_report(output_path: Path, result_root: Path, manifest_name: str) -> int:
    build_ablation_report(output_path, result_root, manifest_name)
    print(str(output_path))
    return 0


def command_fit_detector_profile(output_path: Path, splits: List[str], perturbation_suites: List[str]) -> int:
    profile = fit_detector_profile(
        output_path=output_path,
        splits=splits or ["pilot", "dev"],
        perturbation_suites=perturbation_suites or ["pilot_suite"],
    )
    rows = [["profile", "version", "examples", "positive_rate", "training_accuracy", "log_loss"]]
    metrics = profile["training_metrics"]
    rows.append(
        [
            str(output_path),
            str(profile["version"]),
            str(metrics["example_count"]),
            f"{metrics['positive_rate']:.2f}",
            f"{metrics['training_accuracy']:.2f}",
            f"{metrics['log_loss']:.4f}",
        ]
    )
    _print_table(rows)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="driftguard", description="DriftGuard benchmark CLI")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scenarios = subparsers.add_parser("list-scenarios", help="List bundled benchmark scenarios")
    scenarios.add_argument("--split", default=None, help="Optional split filter")
    scenarios.add_argument("--family", default=None, help="Optional family filter")

    subparsers.add_parser("list-splits", help="List benchmark split metadata")
    subparsers.add_parser("list-agent-backends", help="List supported agent backends")

    smoke = subparsers.add_parser("smoke", help="Run the pilot smoke benchmark")
    smoke.add_argument("--output-root", default="results/smoke", help="Directory for benchmark outputs")

    replay = subparsers.add_parser("replay", help="Replay a recorded trace")
    replay.add_argument("trace_path", help="Path to trace.jsonl")

    manifest = subparsers.add_parser("run-manifest", help="Run an experiment manifest")
    manifest.add_argument("manifest_name", help="Manifest name without .json suffix")
    manifest.add_argument("--output-root", default="results/experiments", help="Directory for experiment outputs")
    manifest.add_argument("--limit", type=int, default=None, help="Optional max number of runs")
    manifest.add_argument(
        "--seed",
        dest="seeds",
        action="append",
        type=int,
        default=[],
        help="Seed override. Repeat to run multiple seeds.",
    )
    manifest.add_argument(
        "--scenario",
        dest="scenarios",
        action="append",
        default=[],
        help="Optional scenario filter. Repeat to include multiple scenarios.",
    )
    manifest.add_argument(
        "--context",
        dest="contexts",
        action="append",
        default=[],
        help="Optional context-system filter. Repeat to include multiple contexts.",
    )
    manifest.add_argument(
        "--detector",
        dest="detectors",
        action="append",
        default=[],
        help="Optional detector filter. Repeat to include multiple detectors.",
    )
    manifest.add_argument(
        "--policy",
        dest="policies",
        action="append",
        default=[],
        help="Optional policy filter. Repeat to include multiple policies.",
    )
    manifest.add_argument(
        "--agent-backend",
        dest="agent_backends",
        action="append",
        default=[],
        help="Optional agent-backend filter. Repeat to include multiple backends.",
    )
    manifest.add_argument(
        "--allow-hidden",
        action="store_true",
        help="Allow manifests that include hidden splits.",
    )
    manifest.add_argument(
        "--permit-repeated-hidden",
        action="store_true",
        help="Permit rerunning hidden/holdout manifests even if a prior run was already recorded.",
    )
    manifest.add_argument(
        "--permit-repeated-locked",
        action="store_true",
        help="Permit rerunning locked test/holdout manifests even if a prior run was already recorded.",
    )

    describe_manifest = subparsers.add_parser("describe-manifest", help="Describe manifest split coverage")
    describe_manifest.add_argument("manifest_name", help="Manifest name without .json suffix")

    subparsers.add_parser("list-hidden-runs", help="List locally recorded hidden-split runs")
    subparsers.add_parser("list-locked-runs", help="List locally recorded test/holdout runs")
    subparsers.add_parser("benchmark-stats", help="Summarize benchmark coverage by split and family")
    subparsers.add_parser("lint-benchmark", help="Lint scenarios, splits, and manifests")

    perturbations = subparsers.add_parser("run-perturbations", help="Run a perturbation suite")
    perturbations.add_argument("suite_name", help="Perturbation suite name without .json suffix")
    perturbations.add_argument(
        "--output-root",
        default="results/perturbations",
        help="Directory for perturbation outputs",
    )
    perturbations.add_argument("--limit", type=int, default=None, help="Optional max number of cases")
    perturbations.add_argument(
        "--case",
        dest="case_ids",
        action="append",
        default=[],
        help="Optional perturbation-case filter. Repeat to include multiple cases.",
    )

    summarize = subparsers.add_parser("summarize-results", help="Aggregate episode result artifacts")
    summarize.add_argument("results_root", help="Directory containing result.json artifacts")
    summarize.add_argument(
        "--output-root",
        default=None,
        help="Directory for summary outputs. Defaults to the results root.",
    )

    snapshot = subparsers.add_parser("write-snapshot-report", help="Generate a markdown snapshot report")
    snapshot.add_argument(
        "--output",
        required=True,
        help="Markdown file to write.",
    )
    snapshot.add_argument(
        "--result-root",
        dest="result_roots",
        action="append",
        default=[],
        help="Result summary directory to include. Repeat for multiple roots.",
    )
    snapshot.add_argument(
        "--perturbation-root",
        dest="perturbation_roots",
        action="append",
        default=[],
        help="Perturbation suite directory to include. Repeat for multiple roots.",
    )

    tech = subparsers.add_parser("write-technical-report", help="Generate a markdown technical report")
    tech.add_argument("--output", required=True, help="Markdown file to write.")
    tech.add_argument("--result-root", required=True, help="Result summary directory to include.")
    tech.add_argument("--perturbation-root", required=True, help="Perturbation suite directory to include.")
    tech.add_argument("--manifest", required=True, help="Manifest name that defines the evaluated slice.")

    annotation = subparsers.add_parser("write-annotation-packet", help="Generate an annotation calibration packet")
    annotation.add_argument("--annotation-set", required=True, help="Annotation set name without .json suffix.")
    annotation.add_argument("--output-root", required=True, help="Directory for packet outputs.")
    annotation.add_argument(
        "--result-root",
        dest="result_roots",
        action="append",
        default=[],
        help="Result summary directory with runs.csv. Repeat for multiple roots.",
    )

    agreement = subparsers.add_parser("compute-annotation-agreement", help="Compute agreement across two reviewer CSVs")
    agreement.add_argument(
        "--response",
        dest="responses",
        action="append",
        default=[],
        help="Reviewer response CSV. Provide exactly two.",
    )

    score_annotation = subparsers.add_parser("score-annotation-response", help="Score one reviewer CSV against an answer key")
    score_annotation.add_argument("--response", required=True, help="Reviewer response CSV.")
    score_annotation.add_argument("--answer-key", required=True, help="Annotation answer key JSON.")

    compare = subparsers.add_parser("compare-contexts", help="Compute paired context deltas from a summary root")
    compare.add_argument("--summary-root", required=True, help="Summary directory containing runs.csv.")
    compare.add_argument("--primary-context", required=True, help="Primary context system.")
    compare.add_argument(
        "--baseline-context",
        dest="baseline_contexts",
        action="append",
        default=[],
        help="Baseline context system. Repeat for multiple baselines.",
    )

    compare_policy = subparsers.add_parser("compare-policies", help="Compute paired policy deltas from a summary root")
    compare_policy.add_argument("--summary-root", required=True, help="Summary directory containing runs.csv.")
    compare_policy.add_argument("--primary-policy", required=True, help="Primary policy.")
    compare_policy.add_argument(
        "--baseline-policy",
        dest="baseline_policies",
        action="append",
        default=[],
        help="Baseline policy. Repeat for multiple baselines.",
    )
    compare_policy.add_argument(
        "--context",
        dest="contexts",
        action="append",
        default=[],
        help="Optional context filter. Repeat for multiple contexts.",
    )
    compare_policy.add_argument(
        "--detector",
        dest="detectors",
        action="append",
        default=[],
        help="Optional detector filter. Repeat for multiple detectors.",
    )

    compare_detector = subparsers.add_parser("compare-detectors", help="Compute paired detector deltas from a summary root")
    compare_detector.add_argument("--summary-root", required=True, help="Summary directory containing runs.csv.")
    compare_detector.add_argument("--primary-detector", required=True, help="Primary detector.")
    compare_detector.add_argument(
        "--baseline-detector",
        dest="baseline_detectors",
        action="append",
        default=[],
        help="Baseline detector. Repeat for multiple baselines.",
    )
    compare_detector.add_argument(
        "--context",
        dest="contexts",
        action="append",
        default=[],
        help="Optional context filter. Repeat for multiple contexts.",
    )
    compare_detector.add_argument(
        "--policy",
        dest="policies",
        action="append",
        default=[],
        help="Optional policy filter. Repeat for multiple policies.",
    )

    compare_backend = subparsers.add_parser("compare-agent-backends", help="Compute paired backend deltas from a summary root")
    compare_backend.add_argument("--summary-root", required=True, help="Summary directory containing runs.csv.")
    compare_backend.add_argument("--primary-backend", required=True, help="Primary agent backend.")
    compare_backend.add_argument(
        "--baseline-backend",
        dest="baseline_backends",
        action="append",
        default=[],
        help="Baseline backend. Repeat for multiple baselines.",
    )
    compare_backend.add_argument(
        "--context",
        dest="contexts",
        action="append",
        default=[],
        help="Optional context filter. Repeat for multiple contexts.",
    )
    compare_backend.add_argument(
        "--detector",
        dest="detectors",
        action="append",
        default=[],
        help="Optional detector filter. Repeat for multiple detectors.",
    )
    compare_backend.add_argument(
        "--policy",
        dest="policies",
        action="append",
        default=[],
        help="Optional policy filter. Repeat for multiple policies.",
    )

    failure_atlas = subparsers.add_parser("write-failure-atlas", help="Generate a markdown failure atlas")
    failure_atlas.add_argument("--output", required=True, help="Markdown file to write.")
    failure_atlas.add_argument("--result-root", required=True, help="Result summary directory to include.")

    ablation = subparsers.add_parser("write-ablation-report", help="Generate a markdown ablation report")
    ablation.add_argument("--output", required=True, help="Markdown file to write.")
    ablation.add_argument("--result-root", required=True, help="Result summary directory to include.")
    ablation.add_argument("--manifest", required=True, help="Manifest name that defines the evaluated slice.")

    fit_detector = subparsers.add_parser("fit-detector-profile", help="Fit the calibrated ensemble profile from local assets")
    fit_detector.add_argument(
        "--output",
        default=str(default_profile_path()),
        help="Output JSON path for the fitted detector profile.",
    )
    fit_detector.add_argument(
        "--split",
        dest="splits",
        action="append",
        default=[],
        help="Benchmark split to include for clean training examples. Repeat for multiple splits.",
    )
    fit_detector.add_argument(
        "--perturbation-suite",
        dest="perturbation_suites",
        action="append",
        default=[],
        help="Perturbation suite to include for positive training examples. Repeat for multiple suites.",
    )

    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.command == "list-scenarios":
        return command_list_scenarios(args.split, args.family)
    if args.command == "list-splits":
        return command_list_splits()
    if args.command == "list-agent-backends":
        return command_list_agent_backends()
    if args.command == "smoke":
        return command_smoke(Path(args.output_root))
    if args.command == "replay":
        return command_replay(Path(args.trace_path))
    if args.command == "run-manifest":
        return command_run_manifest(
            args.manifest_name,
            Path(args.output_root),
            args.limit,
            args.seeds,
            args.scenarios,
            args.contexts,
            args.detectors,
            args.policies,
            args.agent_backends,
            args.allow_hidden,
            args.permit_repeated_hidden,
            args.permit_repeated_locked,
        )
    if args.command == "describe-manifest":
        return command_describe_manifest(args.manifest_name)
    if args.command == "list-hidden-runs":
        return command_list_hidden_runs()
    if args.command == "list-locked-runs":
        return command_list_locked_runs()
    if args.command == "benchmark-stats":
        return command_benchmark_stats()
    if args.command == "lint-benchmark":
        return command_lint_benchmark()
    if args.command == "run-perturbations":
        return command_run_perturbations(args.suite_name, Path(args.output_root), args.limit, args.case_ids)
    if args.command == "summarize-results":
        output_root = Path(args.output_root) if args.output_root else Path(args.results_root)
        return command_summarize_results(Path(args.results_root), output_root)
    if args.command == "write-snapshot-report":
        return command_write_snapshot_report(Path(args.output), args.result_roots, args.perturbation_roots)
    if args.command == "write-technical-report":
        return command_write_technical_report(
            Path(args.output),
            Path(args.result_root),
            Path(args.perturbation_root),
            args.manifest,
        )
    if args.command == "write-annotation-packet":
        return command_write_annotation_packet(args.annotation_set, Path(args.output_root), args.result_roots)
    if args.command == "compute-annotation-agreement":
        return command_compute_annotation_agreement(args.responses)
    if args.command == "score-annotation-response":
        return command_score_annotation_response(Path(args.response), Path(args.answer_key))
    if args.command == "compare-contexts":
        return command_compare_contexts(Path(args.summary_root), args.primary_context, args.baseline_contexts)
    if args.command == "compare-policies":
        return command_compare_policies(
            Path(args.summary_root),
            args.primary_policy,
            args.baseline_policies,
            args.contexts,
            args.detectors,
        )
    if args.command == "compare-detectors":
        return command_compare_detectors(
            Path(args.summary_root),
            args.primary_detector,
            args.baseline_detectors,
            args.contexts,
            args.policies,
        )
    if args.command == "compare-agent-backends":
        return command_compare_agent_backends(
            Path(args.summary_root),
            args.primary_backend,
            args.baseline_backends,
            args.contexts,
            args.detectors,
            args.policies,
        )
    if args.command == "write-failure-atlas":
        return command_write_failure_atlas(Path(args.output), Path(args.result_root))
    if args.command == "write-ablation-report":
        return command_write_ablation_report(Path(args.output), Path(args.result_root), args.manifest)
    if args.command == "fit-detector-profile":
        return command_fit_detector_profile(Path(args.output), args.splits, args.perturbation_suites)
    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
