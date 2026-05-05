"""Deterministic scripted agent used for local smoke benchmarks."""

from __future__ import annotations

from typing import List, Tuple

from driftguard.schemas import DecisionOption, ScenarioEvent, VisibleState


def score_option(option: DecisionOption, visible_state: VisibleState, event: ScenarioEvent) -> Tuple[int, List[str]]:
    score = option.appeal
    reasons: List[str] = []

    if option.supports_goal:
        score += 2
        reasons.append("supports_goal")
    else:
        score -= 1

    visible_evidence = set(visible_state.visible_evidence_ids)
    evidence_overlap = len(set(option.supported_by).intersection(visible_evidence))
    score += evidence_overlap * 2
    if evidence_overlap:
        reasons.append("supported_by_visible_evidence")

    visible_constraints = set(visible_state.visible_constraints)
    violated = set(option.violates_constraints).intersection(visible_constraints)
    if violated:
        score -= len(violated) * 4
        reasons.append("violates_visible_constraints")

    payload = event.payload
    required_constraints = set(payload.get("required_constraints", []))
    required_evidence = set(payload.get("required_evidence", []))
    if required_constraints.difference(visible_constraints) and option.option_id == payload.get("bias_if_constraints_missing"):
        score += 3
        reasons.append("bias_from_missing_constraints")
    if required_evidence.difference(visible_evidence) and option.option_id == payload.get("bias_if_evidence_missing"):
        score += 3
        reasons.append("bias_from_missing_evidence")
    if visible_state.visible_events and option.option_id == payload.get("bias_if_adversarial_visible"):
        score += 2
        reasons.append("adversarial_bias")

    return score, reasons


def choose_option(event: ScenarioEvent, visible_state: VisibleState) -> Tuple[DecisionOption, List[str]]:
    options = [DecisionOption.from_dict(raw) for raw in event.payload["options"]]
    ranked = []
    for option in options:
        score, reasons = score_option(option, visible_state, event)
        ranked.append((score, option.option_id, option, reasons))
    ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
    _, _, option, reasons = ranked[0]
    return option, reasons
