"""Context-system implementations for local benchmark execution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence

from driftguard.ledger import apply_option_effects, bootstrap_ledger, observe_event
from driftguard.schemas import (
    DecisionOption,
    IntentContract,
    MemoryState,
    ResourceProfile,
    ScenarioEvent,
    ScenarioSpec,
    VisibleState,
)


def _keyword_tokens(text: str) -> List[str]:
    return [token.strip(".,:;!?()[]{}").lower() for token in text.split() if token.strip()]


def _note_for_event(event: ScenarioEvent) -> str:
    payload = event.payload
    if event.kind == "constraint":
        return f"constraint::{payload['constraint']}"
    if event.kind == "evidence":
        return f"evidence::{payload.get('evidence_id', event.event_id)}::{payload['summary']}"
    if event.kind == "adversarial":
        return f"adversarial::{payload['instruction']}"
    if event.kind == "subgoal":
        return f"subgoal::{payload['subgoal']}"
    if event.kind == "risk":
        return f"risk::{payload['risk']}"
    if event.kind == "decision_outcome":
        return f"decision::{payload['option_id']}::{payload['label']}"
    return f"event::{event.event_id}::{event.text}"


def _append_summary_note(memory_state: MemoryState, note: str, salience: int, profile: ResourceProfile) -> None:
    memory_state.summary_notes.append(f"{salience}::{note}")
    while len(memory_state.summary_notes) > profile.summary_capacity:
        ranked = sorted(
            enumerate(memory_state.summary_notes),
            key=lambda item: (int(item[1].split("::", 1)[0]), item[0]),
        )
        drop_index = ranked[0][0]
        memory_state.summary_notes.pop(drop_index)


def _parse_summary_notes(summary_notes: Sequence[str]) -> Dict[str, List[str]]:
    parsed = {"constraints": [], "evidence_ids": [], "decisions": [], "events": []}
    for raw in summary_notes:
        _, note = raw.split("::", 1)
        parts = note.split("::")
        prefix = parts[0]
        if prefix == "constraint":
            parsed["constraints"].append(parts[1])
        elif prefix == "evidence":
            parsed["evidence_ids"].append(parts[1])
        elif prefix == "decision":
            parsed["decisions"].append(parts[1])
        elif prefix in {"adversarial", "risk"}:
            parsed["events"].append(parts[-1])
    return parsed


def _parse_transcript(transcript_events: Sequence[Dict[str, object]], limit: int) -> Dict[str, List[str]]:
    parsed = {"constraints": [], "evidence_ids": [], "decisions": [], "events": []}
    for item in list(transcript_events)[-limit:]:
        kind = item["kind"]
        payload = item.get("payload", {})
        if kind == "constraint":
            parsed["constraints"].append(payload["constraint"])
        elif kind == "evidence":
            parsed["evidence_ids"].append(payload.get("evidence_id", item["event_id"]))
        elif kind == "decision_outcome":
            parsed["decisions"].append(payload["option_id"])
        elif kind == "adversarial":
            parsed["events"].append(payload["instruction"])
        elif kind == "risk":
            parsed["events"].append(payload["risk"])
    return parsed


def _retrieve_corpus_ids(scenario: ScenarioSpec, query_terms: Iterable[str], k: int) -> List[str]:
    scored: List[tuple[int, str]] = []
    query = set(token for token in query_terms if token)
    for item in scenario.corpus:
        text = " ".join([item["title"], item["text"]])
        score = len(set(_keyword_tokens(text)).intersection(query))
        if score:
            scored.append((score, item["doc_id"]))
    scored.sort(reverse=True)
    return [doc_id for _, doc_id in scored[:k]]


@dataclass
class ContextSystem:
    name: str
    use_summary: bool
    use_ledger: bool
    use_retrieval: bool

    def bootstrap(self, contract: IntentContract) -> MemoryState:
        return MemoryState(ledger=bootstrap_ledger(contract))

    def observe(self, memory_state: MemoryState, event: ScenarioEvent, profile: ResourceProfile) -> None:
        memory_state.transcript_events.append(event.to_dict())
        observe_event(memory_state.ledger, event, step_id=event.event_id)
        if self.use_summary and event.kind != "decision":
            _append_summary_note(memory_state, _note_for_event(event), event.salience, profile)

    def observe_decision(
        self,
        memory_state: MemoryState,
        option: DecisionOption,
        option_label: str,
        profile: ResourceProfile,
        event_id: str,
    ) -> None:
        apply_option_effects(
            ledger=memory_state.ledger,
            option_id=option.option_id,
            option_label=option_label,
            option_updates=option.ledger_updates,
            evidence_ids=option.evidence_to_accept,
            step_id=event_id,
        )
        transcript_event = ScenarioEvent(
            event_id=f"{event_id}::decision",
            kind="decision_outcome",
            text=option_label,
            salience=10,
            payload={
                "option_id": option.option_id,
                "label": option_label,
                "ledger_updates": option.ledger_updates,
                "evidence_to_accept": option.evidence_to_accept,
            },
        )
        memory_state.transcript_events.append(transcript_event.to_dict())
        if self.use_summary:
            _append_summary_note(memory_state, _note_for_event(transcript_event), 10, profile)

    def build_visible_state(
        self,
        memory_state: MemoryState,
        contract: IntentContract,
        scenario: ScenarioSpec,
        profile: ResourceProfile,
        current_event: ScenarioEvent,
    ) -> VisibleState:
        constraints: List[str] = []
        evidence_ids: List[str] = []
        decisions: List[str] = []
        events: List[str] = []
        summary_notes: List[str] = []

        if self.use_ledger:
            constraints.extend(memory_state.ledger.find_contents("constraints"))
            for item in memory_state.ledger.facts:
                evidence_ids.extend(item.evidence_ids)
            evidence_ids.extend(memory_state.ledger.find_contents("accepted_evidence"))
            decisions.extend(memory_state.ledger.find_contents("decisions"))

        if self.use_summary:
            parsed = _parse_summary_notes(memory_state.summary_notes)
            constraints.extend(parsed["constraints"])
            evidence_ids.extend(parsed["evidence_ids"])
            decisions.extend(parsed["decisions"])
            events.extend(parsed["events"])
            summary_notes = [note.split("::", 1)[1] for note in memory_state.summary_notes]

        if not self.use_ledger and not self.use_summary:
            parsed_transcript = _parse_transcript(memory_state.transcript_events, profile.transcript_capacity)
            constraints.extend(parsed_transcript["constraints"])
            evidence_ids.extend(parsed_transcript["evidence_ids"])
            decisions.extend(parsed_transcript["decisions"])
            events.extend(parsed_transcript["events"])

        if self.use_retrieval:
            query_terms = _keyword_tokens(contract.task_statement + " " + current_event.text + " " + memory_state.ledger.active_subgoal)
            retrieved = _retrieve_corpus_ids(scenario, query_terms, profile.retrieval_k)
            memory_state.retrieval_cache = retrieved
            evidence_ids.extend(retrieved)

        constraints.extend(memory_state.anchors)
        visible_events = list(dict.fromkeys(events))[-profile.max_visible_events :]
        return VisibleState(
            visible_constraints=list(dict.fromkeys(constraints)),
            visible_evidence_ids=list(dict.fromkeys(evidence_ids)),
            visible_decisions=list(dict.fromkeys(decisions)),
            visible_events=visible_events,
            summary_notes=summary_notes,
            active_subgoal=memory_state.ledger.active_subgoal,
        )


RAW_TRANSCRIPT = ContextSystem("raw_transcript", use_summary=False, use_ledger=False, use_retrieval=False)
SUMMARY_ONLY = ContextSystem("summary_only", use_summary=True, use_ledger=False, use_retrieval=False)
RETRIEVAL_ONLY = ContextSystem("retrieval_only", use_summary=False, use_ledger=False, use_retrieval=True)
LEDGER_ONLY = ContextSystem("ledger_only", use_summary=False, use_ledger=True, use_retrieval=False)
LEDGER_RETRIEVAL = ContextSystem("ledger_retrieval", use_summary=False, use_ledger=True, use_retrieval=True)
LEDGER_SUMMARY_RETRIEVAL = ContextSystem(
    "ledger_summary_retrieval",
    use_summary=True,
    use_ledger=True,
    use_retrieval=True,
)

ALL_CONTEXT_SYSTEMS = {
    system.name: system
    for system in (
        RAW_TRANSCRIPT,
        SUMMARY_ONLY,
        RETRIEVAL_ONLY,
        LEDGER_ONLY,
        LEDGER_RETRIEVAL,
        LEDGER_SUMMARY_RETRIEVAL,
    )
}
