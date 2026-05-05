"""Aggregate benchmark results into lightweight summaries."""

from __future__ import annotations

import csv
import random
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from driftguard.serialization import load_json, write_json


def _collect_result_files(results_root: Path) -> List[Path]:
    return sorted(results_root.glob("**/result.json"))


def _load_rows(results_root: Path) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for path in _collect_result_files(results_root):
        row = load_json(path)
        scenario_path = path.parent / "scenario.json"
        row.setdefault("agent_backend", "scripted_local")
        backend_metadata = row.get("backend_metadata", {})
        usage = backend_metadata.get("usage", {}) if isinstance(backend_metadata, dict) else {}
        row["backend_input_tokens"] = int(usage.get("input_tokens", 0) or 0) if isinstance(usage, dict) else 0
        row["backend_output_tokens"] = int(usage.get("output_tokens", 0) or 0) if isinstance(usage, dict) else 0
        row["backend_total_tokens"] = int(usage.get("total_tokens", 0) or 0) if isinstance(usage, dict) else 0
        row["backend_request_count"] = int(usage.get("request_count", 0) or 0) if isinstance(usage, dict) else 0
        if scenario_path.exists():
            scenario = load_json(scenario_path)
            row["family"] = scenario.get("family", "")
            row["split"] = scenario.get("split", "")
            row.setdefault("prompt_pack_version", scenario.get("prompt_pack_version", ""))
            row.setdefault("resource_profile", scenario.get("resource_profile", ""))
        rows.append(row)
    return rows


def _group_summary(rows: Sequence[Dict[str, object]], key: str) -> Dict[str, Dict[str, float]]:
    grouped: Dict[str, Dict[str, float]] = {}
    for row in rows:
        group_value = str(row.get(key, "unknown"))
        bucket = grouped.setdefault(group_value, {"runs": 0.0, "successes": 0.0, "mean_score_total": 0.0})
        bucket["runs"] += 1
        bucket["successes"] += 1 if row.get("success") else 0
        bucket["mean_score_total"] += float(row.get("score", 0.0))
    return {
        group_value: {
            "runs": int(bucket["runs"]),
            "success_rate": round(bucket["successes"] / bucket["runs"], 4) if bucket["runs"] else 0.0,
            "mean_score": round(bucket["mean_score_total"] / bucket["runs"], 4) if bucket["runs"] else 0.0,
        }
        for group_value, bucket in grouped.items()
    }


def _group_summary_nested(rows: Sequence[Dict[str, object]], first_key: str, second_key: str) -> Dict[str, Dict[str, Dict[str, float]]]:
    grouped: Dict[str, Dict[str, Dict[str, float]]] = {}
    for row in rows:
        first_value = str(row.get(first_key, "unknown"))
        second_value = str(row.get(second_key, "unknown"))
        outer = grouped.setdefault(first_value, {})
        bucket = outer.setdefault(second_value, {"runs": 0.0, "successes": 0.0, "mean_score_total": 0.0})
        bucket["runs"] += 1
        bucket["successes"] += 1 if row.get("success") else 0
        bucket["mean_score_total"] += float(row.get("score", 0.0))
    result: Dict[str, Dict[str, Dict[str, float]]] = {}
    for first_value, inner in grouped.items():
        result[first_value] = {}
        for second_value, bucket in inner.items():
            result[first_value][second_value] = {
                "runs": int(bucket["runs"]),
                "success_rate": round(bucket["successes"] / bucket["runs"], 4) if bucket["runs"] else 0.0,
                "mean_score": round(bucket["mean_score_total"] / bucket["runs"], 4) if bucket["runs"] else 0.0,
            }
    return result


def _read_runs_csv(path: Path) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(dict(row))
    return rows


def _parse_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() == "true"


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _percentile(sorted_values: Sequence[float], quantile: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    position = (len(sorted_values) - 1) * quantile
    lower = int(position)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = position - lower
    return sorted_values[lower] * (1.0 - weight) + sorted_values[upper] * weight


def _bootstrap_ci(values: Sequence[float], *, seed: int = 0, samples: int = 1000) -> Tuple[float, float]:
    if not values:
        return (0.0, 0.0)
    generator = random.Random(seed)
    estimates: List[float] = []
    for _ in range(samples):
        sample = [values[generator.randrange(len(values))] for _ in range(len(values))]
        estimates.append(_mean(sample))
    estimates.sort()
    return (round(_percentile(estimates, 0.025), 4), round(_percentile(estimates, 0.975), 4))


def summarize_results(results_root: Path, output_root: Optional[Path] = None) -> Dict[str, object]:
    rows = _load_rows(results_root)
    total_runs = len(rows)
    successes = sum(1 for row in rows if row.get("success"))
    summary = {
        "results_root": str(results_root),
        "total_runs": total_runs,
        "success_rate": round(successes / total_runs, 4) if total_runs else 0.0,
        "mean_score": round(sum(float(row.get("score", 0.0)) for row in rows) / total_runs, 4) if total_runs else 0.0,
        "mean_visible_checkpoint_adherence": (
            round(
                sum(float(row.get("metrics", {}).get("mean_checkpoint_visible_adherence", 0.0)) for row in rows)
                / total_runs,
                4,
            )
            if total_runs
            else 0.0
        ),
        "mean_ledger_checkpoint_adherence": (
            round(
                sum(float(row.get("metrics", {}).get("mean_checkpoint_ledger_adherence", 0.0)) for row in rows)
                / total_runs,
                4,
            )
            if total_runs
            else 0.0
        ),
        "total_backend_input_tokens": sum(int(row.get("backend_input_tokens", 0) or 0) for row in rows),
        "total_backend_output_tokens": sum(int(row.get("backend_output_tokens", 0) or 0) for row in rows),
        "total_backend_tokens": sum(int(row.get("backend_total_tokens", 0) or 0) for row in rows),
        "total_backend_requests": sum(int(row.get("backend_request_count", 0) or 0) for row in rows),
    }
    summary["by_context"] = _group_summary(rows, "context_system")
    summary["by_family"] = _group_summary(rows, "family")
    summary["by_split"] = _group_summary(rows, "split")
    summary["by_policy"] = _group_summary(rows, "policy")
    summary["by_detector"] = _group_summary(rows, "detector")
    summary["by_agent_backend"] = _group_summary(rows, "agent_backend")
    summary["by_prompt_pack_version"] = _group_summary(rows, "prompt_pack_version")
    summary["by_resource_profile"] = _group_summary(rows, "resource_profile")
    summary["by_context_policy"] = _group_summary_nested(rows, "context_system", "policy")
    summary["by_context_detector"] = _group_summary_nested(rows, "context_system", "detector")

    if output_root is None:
        output_root = results_root
    output_root.mkdir(parents=True, exist_ok=True)
    write_json(output_root / "summary.json", summary)

    csv_path = output_root / "runs.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "scenario_id",
                "family",
                "split",
                "context_system",
                "policy",
                "detector",
                "agent_backend",
                "prompt_pack_version",
                "resource_profile",
                "seed",
                "success",
                "score",
                "first_drift_step",
                "mean_checkpoint_visible_adherence",
                "mean_checkpoint_ledger_adherence",
                "mean_checkpoint_provenance_adherence",
                "forbidden_drift_violation_rate",
                "backend_input_tokens",
                "backend_output_tokens",
                "backend_total_tokens",
                "backend_request_count",
                "trace_path",
            ],
        )
        writer.writeheader()
        for row in rows:
            metrics = row.get("metrics", {})
            writer.writerow(
                {
                    "scenario_id": row.get("scenario_id"),
                    "family": row.get("family"),
                    "split": row.get("split"),
                    "context_system": row.get("context_system"),
                    "policy": row.get("policy"),
                    "detector": row.get("detector"),
                    "agent_backend": row.get("agent_backend", "scripted_local"),
                    "prompt_pack_version": row.get("prompt_pack_version", ""),
                    "resource_profile": row.get("resource_profile", ""),
                    "seed": row.get("seed"),
                    "success": row.get("success"),
                    "score": row.get("score"),
                    "first_drift_step": row.get("first_drift_step"),
                    "mean_checkpoint_visible_adherence": metrics.get("mean_checkpoint_visible_adherence"),
                    "mean_checkpoint_ledger_adherence": metrics.get("mean_checkpoint_ledger_adherence"),
                    "mean_checkpoint_provenance_adherence": metrics.get("mean_checkpoint_provenance_adherence"),
                    "forbidden_drift_violation_rate": metrics.get("forbidden_drift_violation_rate"),
                    "backend_input_tokens": row.get("backend_input_tokens", 0),
                    "backend_output_tokens": row.get("backend_output_tokens", 0),
                    "backend_total_tokens": row.get("backend_total_tokens", 0),
                    "backend_request_count": row.get("backend_request_count", 0),
                    "trace_path": row.get("trace_path"),
                }
            )
    return summary


def compare_contexts(
    summary_root: Path,
    primary_context: str,
    baseline_contexts: Sequence[str],
) -> Dict[str, object]:
    return compare_group_values(
        summary_root=summary_root,
        group_key="context_system",
        primary_value=primary_context,
        baseline_values=baseline_contexts,
    )


def compare_group_values(
    summary_root: Path,
    group_key: str,
    primary_value: str,
    baseline_values: Sequence[str],
    filters: Optional[Dict[str, Sequence[str]]] = None,
) -> Dict[str, object]:
    rows = _read_runs_csv(summary_root / "runs.csv")
    if filters:
        filtered_rows = []
        for row in rows:
            keep = True
            for field, values in filters.items():
                if str(row.get(field, "")) not in set(values):
                    keep = False
                    break
            if keep:
                filtered_rows.append(row)
        rows = filtered_rows

    group_fields = {"context_system", "policy", "detector", "agent_backend"}
    if group_key not in group_fields:
        raise ValueError(f"unsupported group_key: {group_key}")
    pairing_fields = [
        "scenario_id",
        "seed",
        "family",
        "split",
        "prompt_pack_version",
        "resource_profile",
    ]
    if group_key != "agent_backend":
        pairing_fields.append("agent_backend")
    pairing_fields.extend(sorted(group_fields.difference({group_key})))

    keyed: Dict[Tuple[str, ...], Dict[str, str]] = {}
    for row in rows:
        pair_key = tuple(str(row.get(field, "")) for field in pairing_fields)
        keyed[pair_key + (str(row.get(group_key, "")),)] = row

    primary_pairs = sorted(
        {
            tuple(str(row.get(field, "")) for field in pairing_fields)
            for row in rows
            if str(row.get(group_key, "")) == primary_value
        }
    )
    comparisons: Dict[str, Dict[str, object]] = {}
    for baseline in baseline_values:
        success_deltas: List[float] = []
        score_deltas: List[float] = []
        visible_deltas: List[float] = []
        ledger_deltas: List[float] = []
        paired_count = 0
        for pair_key in primary_pairs:
            left = keyed.get(pair_key + (primary_value,))
            right = keyed.get(pair_key + (baseline,))
            if left is None or right is None:
                continue
            paired_count += 1
            success_deltas.append((1.0 if _parse_bool(left.get("success")) else 0.0) - (1.0 if _parse_bool(right.get("success")) else 0.0))
            score_deltas.append(float(left.get("score", 0.0)) - float(right.get("score", 0.0)))
            visible_deltas.append(
                float(left.get("mean_checkpoint_visible_adherence", 0.0))
                - float(right.get("mean_checkpoint_visible_adherence", 0.0))
            )
            ledger_deltas.append(
                float(left.get("mean_checkpoint_ledger_adherence", 0.0))
                - float(right.get("mean_checkpoint_ledger_adherence", 0.0))
            )
        comparisons[baseline] = {
            "paired_runs": paired_count,
            "success_delta": round(_mean(success_deltas), 4),
            "success_delta_ci": list(_bootstrap_ci(success_deltas)),
            "mean_score_delta": round(_mean(score_deltas), 4),
            "mean_score_delta_ci": list(_bootstrap_ci(score_deltas)),
            "visible_checkpoint_delta": round(_mean(visible_deltas), 4),
            "visible_checkpoint_delta_ci": list(_bootstrap_ci(visible_deltas)),
            "ledger_checkpoint_delta": round(_mean(ledger_deltas), 4),
            "ledger_checkpoint_delta_ci": list(_bootstrap_ci(ledger_deltas)),
        }
    return {
        "summary_root": str(summary_root),
        "group_key": group_key,
        "primary_value": primary_value,
        "filters": {key: list(values) for key, values in (filters or {}).items()},
        "comparisons": comparisons,
    }


def compare_policies(
    summary_root: Path,
    primary_policy: str,
    baseline_policies: Sequence[str],
    filters: Optional[Dict[str, Sequence[str]]] = None,
) -> Dict[str, object]:
    return compare_group_values(
        summary_root=summary_root,
        group_key="policy",
        primary_value=primary_policy,
        baseline_values=baseline_policies,
        filters=filters,
    )


def compare_detectors(
    summary_root: Path,
    primary_detector: str,
    baseline_detectors: Sequence[str],
    filters: Optional[Dict[str, Sequence[str]]] = None,
) -> Dict[str, object]:
    return compare_group_values(
        summary_root=summary_root,
        group_key="detector",
        primary_value=primary_detector,
        baseline_values=baseline_detectors,
        filters=filters,
    )


def compare_agent_backends(
    summary_root: Path,
    primary_backend: str,
    baseline_backends: Sequence[str],
    filters: Optional[Dict[str, Sequence[str]]] = None,
) -> Dict[str, object]:
    return compare_group_values(
        summary_root=summary_root,
        group_key="agent_backend",
        primary_value=primary_backend,
        baseline_values=baseline_backends,
        filters=filters,
    )
