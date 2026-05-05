"""Annotation calibration scoring and agreement utilities."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from driftguard.serialization import load_json


ANNOTATION_FIELDS = (
    "earliest_visible_drift_step",
    "primary_drift_label",
    "severity",
    "recoverable",
    "final_success",
)

SEVERITY_ORDER = ("none", "low", "medium", "high")


def _normalize_bool_text(value: str) -> str:
    lowered = value.strip().lower()
    if lowered in {"true", "yes", "y", "1"}:
        return "True"
    if lowered in {"false", "no", "n", "0"}:
        return "False"
    return value.strip()


def _normalize_annotation_value(field: str, value: str) -> str:
    raw = value.strip()
    if field in {"recoverable", "final_success"}:
        return _normalize_bool_text(raw)
    if field in {"primary_drift_label", "severity"}:
        return raw.lower()
    if field == "earliest_visible_drift_step":
        return raw.lower()
    return raw


def _read_annotation_csv(path: Path) -> Dict[str, Dict[str, str]]:
    rows: Dict[str, Dict[str, str]] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            example_id = str(row.get("example_id", "")).strip()
            if not example_id:
                continue
            normalized: Dict[str, str] = {}
            for key, value in row.items():
                if not key:
                    continue
                normalized[key] = _normalize_annotation_value(key, str(value))
            rows[example_id] = normalized
    return rows


def _kappa(values_a: Sequence[str], values_b: Sequence[str]) -> float:
    if len(values_a) != len(values_b):
        raise ValueError("value sequences must be the same length")
    if not values_a:
        return 0.0
    observed = sum(1 for left, right in zip(values_a, values_b) if left == right) / len(values_a)
    labels = sorted(set(values_a).union(values_b))
    if not labels:
        return 0.0
    marginal_a = {label: values_a.count(label) / len(values_a) for label in labels}
    marginal_b = {label: values_b.count(label) / len(values_b) for label in labels}
    expected = sum(marginal_a[label] * marginal_b[label] for label in labels)
    if expected >= 1.0:
        return 1.0 if observed >= 1.0 else 0.0
    return round((observed - expected) / (1.0 - expected), 4)


def _weighted_kappa(values_a: Sequence[str], values_b: Sequence[str], ordered_labels: Sequence[str]) -> float:
    if len(values_a) != len(values_b):
        raise ValueError("value sequences must be the same length")
    if not values_a:
        return 0.0
    labels = [label for label in ordered_labels if label in set(values_a).union(values_b)]
    if len(labels) <= 1:
        return 1.0
    index = {label: idx for idx, label in enumerate(labels)}
    size = len(labels)
    observed = [[0.0 for _ in range(size)] for _ in range(size)]
    for left, right in zip(values_a, values_b):
        observed[index[left]][index[right]] += 1.0
    total = float(len(values_a))
    observed = [[cell / total for cell in row] for row in observed]
    marginal_a = [values_a.count(label) / total for label in labels]
    marginal_b = [values_b.count(label) / total for label in labels]
    expected = [[marginal_a[i] * marginal_b[j] for j in range(size)] for i in range(size)]
    if size == 1:
        return 1.0
    weights = [
        [abs(i - j) / (size - 1) for j in range(size)]
        for i in range(size)
    ]
    observed_weighted = sum(weights[i][j] * observed[i][j] for i in range(size) for j in range(size))
    expected_weighted = sum(weights[i][j] * expected[i][j] for i in range(size) for j in range(size))
    if expected_weighted >= 1.0:
        return 1.0 if observed_weighted <= 0.0 else 0.0
    return round(1.0 - (observed_weighted / expected_weighted), 4)


def _confusion_matrix(values_a: Sequence[str], values_b: Sequence[str]) -> Dict[str, Dict[str, int]]:
    labels = sorted(set(values_a).union(values_b))
    matrix: Dict[str, Dict[str, int]] = {left: {right: 0 for right in labels} for left in labels}
    for left, right in zip(values_a, values_b):
        matrix[left][right] += 1
    return matrix


def _parse_step_number(value: str) -> Optional[int]:
    stripped = value.strip().lower()
    if not stripped:
        return None
    if not stripped.startswith("step-"):
        return None
    suffix = stripped.split("-", 1)[1]
    return int(suffix) if suffix.isdigit() else None


def _step_metrics(values_a: Sequence[str], values_b: Sequence[str]) -> Dict[str, float]:
    exact = 0
    within_one = 0
    comparable = 0
    distance_total = 0.0
    for left, right in zip(values_a, values_b):
        if left == right:
            exact += 1
            within_one += 1
            if _parse_step_number(left) is not None:
                comparable += 1
            continue
        left_step = _parse_step_number(left)
        right_step = _parse_step_number(right)
        if left_step is None or right_step is None:
            continue
        comparable += 1
        distance = abs(left_step - right_step)
        distance_total += distance
        if distance <= 1:
            within_one += 1
    count = len(values_a) if values_a else 1
    return {
        "exact_match_rate": round(exact / count, 4),
        "within_one_step_rate": round(within_one / count, 4),
        "comparable_step_pair_count": comparable,
        "mean_step_distance": round(distance_total / comparable, 4) if comparable else 0.0,
    }


def compute_annotation_agreement(response_paths: Sequence[Path]) -> Dict[str, object]:
    if len(response_paths) != 2:
        raise ValueError("compute_annotation_agreement requires exactly two response CSVs")
    left = _read_annotation_csv(response_paths[0])
    right = _read_annotation_csv(response_paths[1])
    common_ids = sorted(set(left).intersection(right))
    if not common_ids:
        raise ValueError("no shared example_ids found across annotation responses")

    field_metrics: Dict[str, Dict[str, object]] = {}
    disagreements: List[Dict[str, object]] = []
    for field in ANNOTATION_FIELDS:
        left_values = [left[example_id].get(field, "") for example_id in common_ids]
        right_values = [right[example_id].get(field, "") for example_id in common_ids]
        exact_match = sum(1 for lval, rval in zip(left_values, right_values) if lval == rval) / len(common_ids)
        metric_bucket: Dict[str, object] = {
            "exact_match_rate": round(exact_match, 4),
            "cohens_kappa": _kappa(left_values, right_values),
        }
        if field == "earliest_visible_drift_step":
            metric_bucket.update(_step_metrics(left_values, right_values))
        if field == "primary_drift_label":
            metric_bucket["confusion_matrix"] = _confusion_matrix(left_values, right_values)
        if field == "severity":
            metric_bucket["weighted_kappa"] = _weighted_kappa(left_values, right_values, SEVERITY_ORDER)
            metric_bucket["confusion_matrix"] = _confusion_matrix(left_values, right_values)
        field_metrics[field] = metric_bucket

    for example_id in common_ids:
        mismatched_fields = [
            field
            for field in ANNOTATION_FIELDS
            if left[example_id].get(field, "") != right[example_id].get(field, "")
        ]
        if not mismatched_fields:
            continue
        disagreements.append(
            {
                "example_id": example_id,
                "mismatched_fields": mismatched_fields,
                "reviewer_a": {field: left[example_id].get(field, "") for field in ANNOTATION_FIELDS},
                "reviewer_b": {field: right[example_id].get(field, "") for field in ANNOTATION_FIELDS},
            }
        )

    mean_exact = sum(float(item["exact_match_rate"]) for item in field_metrics.values()) / len(field_metrics)

    return {
        "response_paths": [str(path) for path in response_paths],
        "shared_example_count": len(common_ids),
        "shared_example_ids": common_ids,
        "field_metrics": field_metrics,
        "overall": {
            "mean_exact_match_rate": round(mean_exact, 4),
            "disagreement_case_count": len(disagreements),
        },
        "disagreements": disagreements,
    }


def score_annotation_response(response_path: Path, answer_key_path: Path) -> Dict[str, object]:
    responses = _read_annotation_csv(response_path)
    answer_key = load_json(answer_key_path)
    answer_cases = {
        str(item["example_id"]): {
            "earliest_visible_drift_step": _normalize_annotation_value(
                "earliest_visible_drift_step",
                str(item.get("expected_earliest_drift_step", "")).strip(),
            ),
            "primary_drift_label": _normalize_annotation_value(
                "primary_drift_label",
                str(item.get("expected_primary_drift_label", "")).strip(),
            ),
            "severity": _normalize_annotation_value("severity", str(item.get("expected_severity", "")).strip()),
            "recoverable": (
                ""
                if item.get("expected_recoverable") is None
                else _normalize_annotation_value("recoverable", str(item.get("expected_recoverable")).strip())
            ),
            "final_success": (
                ""
                if item.get("expected_final_success") is None
                else _normalize_annotation_value("final_success", str(item.get("expected_final_success")).strip())
            ),
        }
        for item in answer_key.get("cases", [])
    }
    shared_ids = sorted(set(responses).intersection(answer_cases))
    if not shared_ids:
        raise ValueError("no shared example_ids found between response and answer key")

    field_accuracy: Dict[str, float] = {}
    supplemental_metrics: Dict[str, object] = {}
    for field in ANNOTATION_FIELDS:
        correct = 0
        response_values: List[str] = []
        answer_values: List[str] = []
        for example_id in shared_ids:
            response_value = responses[example_id].get(field, "")
            answer_value = answer_cases[example_id].get(field, "")
            response_values.append(response_value)
            answer_values.append(answer_value)
            if response_value == answer_value:
                correct += 1
        field_accuracy[field] = round(correct / len(shared_ids), 4)
        if field == "earliest_visible_drift_step":
            supplemental_metrics[field] = _step_metrics(response_values, answer_values)
        if field == "severity":
            supplemental_metrics[field] = {
                "weighted_kappa_against_answer_key": _weighted_kappa(response_values, answer_values, SEVERITY_ORDER)
            }

    return {
        "response_path": str(response_path),
        "answer_key_path": str(answer_key_path),
        "scored_example_count": len(shared_ids),
        "scored_example_ids": shared_ids,
        "field_accuracy": field_accuracy,
        "supplemental_metrics": supplemental_metrics,
    }
