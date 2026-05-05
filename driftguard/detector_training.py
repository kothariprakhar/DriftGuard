"""Fit a calibrated detector profile from local benchmark assets."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

from driftguard.agent import choose_option
from driftguard.contexts import ALL_CONTEXT_SYSTEMS
from driftguard.detectors import (
    EvidenceAlignmentDetector,
    RuleBasedDetector,
    RubricDetector,
    SummaryFaithfulnessDetector,
)
from driftguard.perturbations import apply_perturbation, prepare_event_state
from driftguard.registry import BENCHMARK_ROOT, load_perturbation_suite, load_scenario_index
from driftguard.serialization import write_json


FEATURE_ORDER = (
    "rule_based",
    "rubric",
    "evidence_alignment",
    "summary_faithfulness",
)


def _component_detectors():
    return {
        "rule_based": RuleBasedDetector(),
        "rubric": RubricDetector(),
        "evidence_alignment": EvidenceAlignmentDetector(),
        "summary_faithfulness": SummaryFaithfulnessDetector(),
    }


def _sigmoid(value: float) -> float:
    value = max(-20.0, min(20.0, value))
    return 1.0 / (1.0 + math.exp(-value))


def _feature_vector(scenario, visible_state, event) -> Dict[str, float]:
    detectors = _component_detectors()
    return {
        name: detectors[name].assess(scenario, visible_state, event).overall_score
        for name in FEATURE_ORDER
    }


def _decision_examples_for_splits(splits: Sequence[str]) -> List[Tuple[Dict[str, float], int]]:
    examples: List[Tuple[Dict[str, float], int]] = []
    contexts = list(ALL_CONTEXT_SYSTEMS)
    for split in splits:
        for entry in load_scenario_index(split=split):
            scenario_id = entry["scenario_id"]
            for context_system in contexts:
                scenario = None
                context = ALL_CONTEXT_SYSTEMS[context_system]
                memory_state = None
                resource_profile = None
                from driftguard.registry import load_resource_profile, load_scenario

                scenario = load_scenario(scenario_id)
                resource_profile = load_resource_profile(scenario.resource_profile)
                memory_state = context.bootstrap(scenario.intent_contract)
                for event in scenario.events:
                    if event.kind == "decision":
                        visible_state = context.build_visible_state(
                            memory_state=memory_state,
                            contract=scenario.intent_contract,
                            scenario=scenario,
                            profile=resource_profile,
                            current_event=event,
                        )
                        option, _ = choose_option(event, visible_state)
                        label = 0 if option.option_id == event.payload["correct_option_id"] else 1
                        examples.append((_feature_vector(scenario, visible_state, event), label))
                        context.observe_decision(memory_state, option, option.label, resource_profile, event.event_id)
                    else:
                        context.observe(memory_state, event, resource_profile)
    return examples


def _perturbation_examples(suites: Sequence[str]) -> List[Tuple[Dict[str, float], int]]:
    examples: List[Tuple[Dict[str, float], int]] = []
    for suite_name in suites:
        suite = load_perturbation_suite(suite_name)
        for case in suite.cases:
            scenario, event, memory_state, visible_state = prepare_event_state(
                case.scenario_id,
                case.context_system,
                case.target_event_id,
            )
            examples.append((_feature_vector(scenario, visible_state, event), 0))
            _, perturbed_visible = apply_perturbation(case, memory_state, visible_state, event)
            examples.append((_feature_vector(scenario, perturbed_visible, event), 1))
    return examples


def build_training_examples(
    splits: Sequence[str] = ("pilot", "dev"),
    perturbation_suites: Sequence[str] = ("pilot_suite",),
) -> List[Tuple[Dict[str, float], int]]:
    return _decision_examples_for_splits(splits) + _perturbation_examples(perturbation_suites)


def _fit_logistic_profile(
    examples: Sequence[Tuple[Dict[str, float], int]],
    learning_rate: float = 0.35,
    epochs: int = 1200,
    l2: float = 0.05,
) -> Dict[str, object]:
    weights = {name: 0.0 for name in FEATURE_ORDER}
    intercept = 0.0
    count = float(len(examples))

    for _ in range(epochs):
        intercept_gradient = 0.0
        gradients = {name: 0.0 for name in FEATURE_ORDER}
        for feature_map, label in examples:
            logit = intercept + sum(weights[name] * feature_map[name] for name in FEATURE_ORDER)
            probability = _sigmoid(logit)
            error = probability - label
            intercept_gradient += error
            for name in FEATURE_ORDER:
                gradients[name] += error * feature_map[name]
        intercept -= learning_rate * (intercept_gradient / count)
        for name in FEATURE_ORDER:
            weights[name] -= learning_rate * ((gradients[name] / count) + (l2 * weights[name]))

    positives = 0
    correct = 0
    log_loss = 0.0
    for feature_map, label in examples:
        probability = _sigmoid(intercept + sum(weights[name] * feature_map[name] for name in FEATURE_ORDER))
        positives += label
        prediction = 1 if probability >= 0.5 else 0
        if prediction == label:
            correct += 1
        probability = min(max(probability, 1e-6), 1.0 - 1e-6)
        log_loss += -(label * math.log(probability) + (1 - label) * math.log(1 - probability))

    abs_total = sum(abs(value) for value in weights.values()) or 1.0
    label_weights = {name: round(abs(weights[name]) / abs_total, 6) for name in FEATURE_ORDER}

    return {
        "version": "calibrated_ensemble/v2",
        "feature_order": list(FEATURE_ORDER),
        "intercept": round(intercept, 6),
        "weights": {name: round(value, 6) for name, value in weights.items()},
        "label_weights": label_weights,
        "training_metrics": {
            "example_count": len(examples),
            "positive_rate": round(positives / count, 6) if count else 0.0,
            "training_accuracy": round(correct / count, 6) if count else 0.0,
            "log_loss": round(log_loss / count, 6) if count else 0.0,
        },
    }


def fit_detector_profile(
    output_path: Path,
    splits: Sequence[str] = ("pilot", "dev"),
    perturbation_suites: Sequence[str] = ("pilot_suite",),
) -> Dict[str, object]:
    examples = build_training_examples(splits=splits, perturbation_suites=perturbation_suites)
    profile = _fit_logistic_profile(examples)
    profile["trained_on"] = {
        "splits": list(splits),
        "perturbation_suites": list(perturbation_suites),
    }
    profile["generated_at"] = datetime.now(timezone.utc).isoformat()
    write_json(output_path, profile)
    return profile


def default_profile_path() -> Path:
    return BENCHMARK_ROOT / "detectors" / "calibrated_ensemble.json"

