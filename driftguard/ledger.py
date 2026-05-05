"""Ledger creation and mutation helpers."""

from __future__ import annotations

from typing import Dict, Iterable, List

from driftguard.schemas import IntentContract, LedgerItem, ScenarioEvent, StateLedger


def bootstrap_ledger(contract: IntentContract) -> StateLedger:
    ledger = StateLedger()
    for index, constraint in enumerate(contract.hard_constraints, start=1):
        ledger.add_item(
            "constraints",
            LedgerItem(
                item_id=f"constraint-{index}",
                kind="constraint",
                status="active",
                content=constraint,
                source_step_ids=["contract"],
                created_at="contract",
                updated_at="contract",
            ),
        )
    for index, criterion in enumerate(contract.success_criteria, start=1):
        ledger.add_item(
            "outstanding_work",
            LedgerItem(
                item_id=f"work-{index}",
                kind="outstanding_work",
                status="open",
                content=criterion,
                source_step_ids=["contract"],
                created_at="contract",
                updated_at="contract",
            ),
        )
    ledger.active_subgoal = contract.success_criteria[0]
    return ledger


def _new_item(item_id: str, kind: str, content: str, step_id: str, evidence_ids: Iterable[str] = ()) -> LedgerItem:
    return LedgerItem(
        item_id=item_id,
        kind=kind,
        status="active",
        content=content,
        source_step_ids=[step_id],
        evidence_ids=list(evidence_ids),
        created_at=step_id,
        updated_at=step_id,
    )


def observe_event(ledger: StateLedger, event: ScenarioEvent, step_id: str) -> None:
    payload = event.payload
    if event.kind == "constraint":
        ledger.add_item(
            "constraints",
            _new_item(
                item_id=payload.get("constraint_id", event.event_id),
                kind="constraint",
                content=payload["constraint"],
                step_id=step_id,
            ),
        )
    elif event.kind == "evidence":
        ledger.add_item(
            "facts",
            _new_item(
                item_id=payload.get("evidence_id", event.event_id),
                kind="fact",
                content=payload["summary"],
                step_id=step_id,
                evidence_ids=[payload.get("evidence_id", event.event_id)],
            ),
        )
    elif event.kind == "subgoal":
        ledger.active_subgoal = payload["subgoal"]
        ledger.add_item(
            "plan_steps",
            _new_item(event.event_id, "plan_step", payload["subgoal"], step_id),
        )
    elif event.kind == "risk":
        ledger.add_item(
            "risk_flags",
            _new_item(event.event_id, "risk_flag", payload["risk"], step_id),
        )
    elif event.kind == "note":
        ledger.add_item(
            "assumptions",
            _new_item(event.event_id, "assumption", payload["note"], step_id),
        )


def apply_option_effects(
    ledger: StateLedger,
    option_id: str,
    option_label: str,
    option_updates: Dict[str, List[str]],
    evidence_ids: List[str],
    step_id: str,
) -> None:
    ledger.add_item(
        "decisions",
        LedgerItem(
            item_id=option_id,
            kind="decision",
            status="chosen",
            content=option_label,
            source_step_ids=[step_id],
            evidence_ids=list(evidence_ids),
            created_at=step_id,
            updated_at=step_id,
        ),
    )
    for evidence_id in evidence_ids:
        ledger.add_item(
            "accepted_evidence",
            LedgerItem(
                item_id=f"accepted-{step_id}-{evidence_id}",
                kind="accepted_evidence",
                status="accepted",
                content=evidence_id,
                source_step_ids=[step_id],
                evidence_ids=[evidence_id],
                created_at=step_id,
                updated_at=step_id,
            ),
        )
    for bucket, contents in option_updates.items():
        for offset, content in enumerate(contents, start=1):
            ledger.add_item(
                bucket,
                _new_item(
                    item_id=f"{bucket}-{step_id}-{offset}",
                    kind=bucket[:-1] if bucket.endswith("s") else bucket,
                    content=content,
                    step_id=step_id,
                    evidence_ids=evidence_ids,
                ),
            )


def regenerate_ledger_from_transcript(contract: IntentContract, transcript_events: List[Dict[str, object]]) -> StateLedger:
    ledger = bootstrap_ledger(contract)
    for index, item in enumerate(transcript_events, start=1):
        step_id = f"regen-{index}"
        kind = item["kind"]
        if kind in {"constraint", "evidence", "subgoal", "risk", "note"}:
            observe_event(ledger, ScenarioEvent.from_dict(item), step_id=step_id)
        elif kind == "decision_outcome":
            apply_option_effects(
                ledger=ledger,
                option_id=item["payload"]["option_id"],
                option_label=item["payload"]["label"],
                option_updates=item["payload"].get("ledger_updates", {}),
                evidence_ids=item["payload"].get("evidence_to_accept", []),
                step_id=step_id,
            )
    return ledger
