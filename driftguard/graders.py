"""Deterministic checkpoint and outcome graders."""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

from driftguard.schemas import (
    CheckpointState,
    GoldCheckpoint,
    ProvenanceRequirement,
    ScenarioSpec,
    StateLedger,
    StepRecord,
)


def _bucket_contents(ledger: StateLedger, bucket: str) -> List[str]:
    if bucket == "accepted_evidence":
        return ledger.find_contents("accepted_evidence")
    if bucket == "decisions":
        return ledger.find_contents("decisions")
    if bucket == "facts":
        return ledger.find_contents("facts")
    if bucket == "outstanding_work":
        return ledger.find_contents("outstanding_work")
    if bucket == "plan_steps":
        return ledger.find_contents("plan_steps")
    if bucket == "risk_flags":
        return ledger.find_contents("risk_flags")
    if bucket == "assumptions":
        return ledger.find_contents("assumptions")
    if bucket == "constraints":
        return ledger.find_contents("constraints")
    raise ValueError(f"unsupported ledger bucket in grader: {bucket}")


def _items_for_bucket(ledger: StateLedger, bucket: str):
    if bucket not in ledger.BUCKETS:
        raise ValueError(f"unsupported ledger bucket in grader: {bucket}")
    return getattr(ledger, bucket)


def _missing(required: Sequence[str], actual: Sequence[str]) -> List[str]:
    actual_set = set(actual)
    return [item for item in required if item not in actual_set]


def _score_component(required_total: int, missing_total: int) -> float:
    if required_total == 0:
        return 1.0
    return round((required_total - missing_total) / required_total, 4)


def _grade_provenance(ledger: StateLedger, requirements: Sequence[ProvenanceRequirement]) -> Dict[str, object]:
    missing_links: List[Dict[str, object]] = []
    for requirement in requirements:
        candidates = [item for item in _items_for_bucket(ledger, requirement.bucket) if item.content == requirement.content]
        if not candidates:
            missing_links.append(
                {
                    "bucket": requirement.bucket,
                    "content": requirement.content,
                    "missing_evidence_ids": list(requirement.evidence_ids),
                }
            )
            continue
        if not any(set(requirement.evidence_ids).issubset(set(item.evidence_ids)) for item in candidates):
            missing_links.append(
                {
                    "bucket": requirement.bucket,
                    "content": requirement.content,
                    "missing_evidence_ids": list(requirement.evidence_ids),
                }
            )
    score = _score_component(len(requirements), len(missing_links))
    return {
        "provenance_adherence": score,
        "missing_provenance_links": missing_links,
    }


def grade_checkpoint(
    checkpoint: CheckpointState,
    gold: GoldCheckpoint,
    record: Optional[StepRecord] = None,
) -> Dict[str, object]:
    visible_constraints = set(checkpoint.visible_state.visible_constraints)
    visible_evidence = set(checkpoint.visible_state.visible_evidence_ids)
    visible_decisions = set(checkpoint.visible_state.visible_decisions)

    missing_constraints = [item for item in gold.required_constraints if item not in visible_constraints]
    missing_evidence = [item for item in gold.required_evidence_ids if item not in visible_evidence]
    missing_visible_decisions = [item for item in gold.required_decisions if item not in visible_decisions]
    visible_total = len(gold.required_constraints) + len(gold.required_evidence_ids) + len(gold.required_decisions)
    visible_missing = len(missing_constraints) + len(missing_evidence) + len(missing_visible_decisions)
    visible_adherence = _score_component(visible_total, visible_missing)

    ledger = checkpoint.memory_state.ledger
    missing_fact_contents = _missing(gold.required_fact_contents, _bucket_contents(ledger, "facts"))
    missing_ledger_decisions = _missing(gold.required_ledger_decisions, _bucket_contents(ledger, "decisions"))
    missing_outstanding_work = _missing(gold.required_outstanding_work, _bucket_contents(ledger, "outstanding_work"))
    missing_plan_steps = _missing(gold.required_plan_steps, _bucket_contents(ledger, "plan_steps"))
    missing_accepted_evidence = _missing(
        gold.required_accepted_evidence_ids,
        _bucket_contents(ledger, "accepted_evidence"),
    )
    missing_risk_flags = _missing(gold.required_risk_flags, _bucket_contents(ledger, "risk_flags"))
    missing_assumptions = _missing(gold.required_assumptions, _bucket_contents(ledger, "assumptions"))
    missing_active_subgoal: List[str] = []
    if gold.required_active_subgoal and gold.required_active_subgoal != ledger.active_subgoal:
        missing_active_subgoal.append(gold.required_active_subgoal)

    ledger_total = (
        len(gold.required_fact_contents)
        + len(gold.required_ledger_decisions)
        + len(gold.required_outstanding_work)
        + len(gold.required_plan_steps)
        + len(gold.required_accepted_evidence_ids)
        + len(gold.required_risk_flags)
        + len(gold.required_assumptions)
        + (1 if gold.required_active_subgoal else 0)
    )
    ledger_missing = (
        len(missing_fact_contents)
        + len(missing_ledger_decisions)
        + len(missing_outstanding_work)
        + len(missing_plan_steps)
        + len(missing_accepted_evidence)
        + len(missing_risk_flags)
        + len(missing_assumptions)
        + len(missing_active_subgoal)
    )
    ledger_adherence = _score_component(ledger_total, ledger_missing)

    provenance = _grade_provenance(ledger, gold.required_provenance)

    forbidden_drift_violations: List[str] = []
    if record and record.chosen_drift_label and record.chosen_drift_label in gold.forbidden_drift_labels:
        forbidden_drift_violations.append(record.chosen_drift_label)
    drift_adherence = _score_component(len(gold.forbidden_drift_labels), len(forbidden_drift_violations))

    component_scores = [visible_adherence, ledger_adherence, provenance["provenance_adherence"], drift_adherence]
    adherence = round(sum(component_scores) / len(component_scores), 4)

    return {
        "checkpoint_id": checkpoint.checkpoint_id,
        "adherence": adherence,
        "visible_adherence": visible_adherence,
        "ledger_adherence": ledger_adherence,
        "provenance_adherence": provenance["provenance_adherence"],
        "drift_adherence": drift_adherence,
        "missing_constraints": missing_constraints,
        "missing_evidence": missing_evidence,
        "missing_visible_decisions": missing_visible_decisions,
        "missing_fact_contents": missing_fact_contents,
        "missing_ledger_decisions": missing_ledger_decisions,
        "missing_outstanding_work": missing_outstanding_work,
        "missing_plan_steps": missing_plan_steps,
        "missing_accepted_evidence": missing_accepted_evidence,
        "missing_risk_flags": missing_risk_flags,
        "missing_assumptions": missing_assumptions,
        "missing_active_subgoal": missing_active_subgoal,
        "missing_provenance_links": provenance["missing_provenance_links"],
        "forbidden_drift_violations": forbidden_drift_violations,
    }


def first_visible_drift(records: List[StepRecord]) -> Optional[str]:
    for record in records:
        if record.chosen_option_id and record.correct_option_id and record.chosen_option_id != record.correct_option_id:
            return record.step_id
    return None


def grade_outcome(scenario: ScenarioSpec, records: List[StepRecord]) -> Dict[str, object]:
    chosen_decisions = [record.chosen_option_id for record in records if record.kind == "decision"]
    correct_decisions = [record.correct_option_id for record in records if record.kind == "decision"]
    correct = [chosen == correct for chosen, correct in zip(chosen_decisions, correct_decisions)]
    success = all(correct) if correct else False
    decision_accuracy = round(sum(1 for item in correct if item) / len(correct), 4) if correct else 0.0
    return {
        "success": success,
        "decision_accuracy": decision_accuracy,
        "num_decisions": len(correct),
        "first_drift_step": first_visible_drift(records),
        "required_decision_ids": scenario.gold_outcome.get("required_decision_ids", []),
    }


def aggregate_episode_metrics(
    scenario: ScenarioSpec,
    records: List[StepRecord],
    checkpoints: List[CheckpointState],
) -> Dict[str, object]:
    outcome = grade_outcome(scenario, records)
    record_by_event = {record.event_id: record for record in records}
    graded = []
    for checkpoint in checkpoints:
        for gold in scenario.gold_checkpoints:
            if gold.after_event_id == checkpoint.after_event_id:
                graded.append(grade_checkpoint(checkpoint, gold, record_by_event.get(checkpoint.after_event_id)))
    mean_adherence = round(sum(item["adherence"] for item in graded) / len(graded), 4) if graded else 1.0
    mean_visible_adherence = round(sum(item["visible_adherence"] for item in graded) / len(graded), 4) if graded else 1.0
    mean_ledger_adherence = round(sum(item["ledger_adherence"] for item in graded) / len(graded), 4) if graded else 1.0
    mean_provenance_adherence = (
        round(sum(item["provenance_adherence"] for item in graded) / len(graded), 4) if graded else 1.0
    )
    drift_violation_rate = (
        round(sum(1 for item in graded if item["forbidden_drift_violations"]) / len(graded), 4) if graded else 0.0
    )
    detector_load = round(
        sum(record.drift_assessment.overall_score for record in records) / max(1, len(records)),
        4,
    )
    return {
        **outcome,
        "mean_checkpoint_adherence": mean_adherence,
        "mean_checkpoint_visible_adherence": mean_visible_adherence,
        "mean_checkpoint_ledger_adherence": mean_ledger_adherence,
        "mean_checkpoint_provenance_adherence": mean_provenance_adherence,
        "forbidden_drift_violation_rate": drift_violation_rate,
        "num_checkpoints": len(graded),
        "mean_detector_score": detector_load,
    }
