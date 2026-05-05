"""Prompt rendering helpers for model-backed agent execution."""

from __future__ import annotations

import json
from typing import Any, Dict, List

from driftguard.schemas import MemoryState, PromptPack, ResourceProfile, ScenarioEvent, ScenarioSpec, VisibleState


def _truncate(items: List[str], limit: int) -> List[str]:
    if limit <= 0:
        return []
    return items[:limit]


def build_decision_packet(
    scenario: ScenarioSpec,
    event: ScenarioEvent,
    visible_state: VisibleState,
    memory_state: MemoryState,
    profile: ResourceProfile,
) -> Dict[str, Any]:
    return {
        "scenario_id": scenario.scenario_id,
        "scenario_title": scenario.title,
        "family": scenario.family,
        "resource_profile": profile.version,
        "intent_contract": scenario.intent_contract.to_dict(),
        "visible_state": {
            "active_subgoal": visible_state.active_subgoal,
            "constraints": _truncate(list(visible_state.visible_constraints), profile.max_visible_events),
            "evidence_ids": _truncate(list(visible_state.visible_evidence_ids), profile.max_visible_events),
            "decisions": _truncate(list(visible_state.visible_decisions), profile.max_visible_events),
            "events": _truncate(list(visible_state.visible_events), profile.max_visible_events),
            "summary_notes": _truncate(list(visible_state.summary_notes), profile.max_visible_events),
        },
        "memory_artifacts": {
            "anchors": list(memory_state.anchors),
            "retrieval_cache": list(memory_state.retrieval_cache),
            "ledger_active_subgoal": memory_state.ledger.active_subgoal,
            "ledger_constraints": memory_state.ledger.find_contents("constraints"),
            "ledger_decisions": memory_state.ledger.find_contents("decisions"),
            "ledger_outstanding_work": memory_state.ledger.find_contents("outstanding_work"),
        },
        "current_event": event.to_dict(),
        "decision_options": list(event.payload.get("options", [])),
        "response_schema": {
            "option_id": "string",
            "reason_codes": ["short_string"],
            "notes": "short_string",
        },
    }


def build_agent_prompt(
    prompt_pack: PromptPack,
    scenario: ScenarioSpec,
    event: ScenarioEvent,
    visible_state: VisibleState,
    memory_state: MemoryState,
    profile: ResourceProfile,
) -> Dict[str, str]:
    packet = build_decision_packet(scenario, event, visible_state, memory_state, profile)
    system_prompt = prompt_pack.get_prompt("base_agent").strip()
    user_prompt = (
        "Choose the best next action under the intent contract.\n"
        "Return only a JSON object with keys option_id, reason_codes, and notes.\n\n"
        f"{json.dumps(packet, indent=2, sort_keys=True)}"
    )
    return {"system": system_prompt, "user": user_prompt}
