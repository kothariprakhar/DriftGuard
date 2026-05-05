"""Build reproducible, reviewer-safe annotation packets from frozen benchmark artifacts."""

from __future__ import annotations

import csv
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from driftguard.registry import REPO_ROOT, load_annotation_set, load_scenario
from driftguard.schemas import AnnotationCase, AnnotationSet, CheckpointState, ScenarioSpec, StepRecord
from driftguard.serialization import load_json, load_jsonl, write_json


def _parse_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() == "true"


def _read_runs_csv(path: Path) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(dict(row))
    return rows


def _load_result_rows(result_roots: Sequence[Path]) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for result_root in result_roots:
        runs_path = result_root / "runs.csv"
        if not runs_path.exists():
            raise FileNotFoundError(f"missing runs.csv under {result_root}")
        for row in _read_runs_csv(runs_path):
            enriched = dict(row)
            enriched["_result_root"] = str(result_root)
            rows.append(enriched)
    return rows


def _preference_score(value: str, ordered_preferences: Sequence[str]) -> Optional[int]:
    if not ordered_preferences:
        return 0
    if value not in ordered_preferences:
        return None
    return len(ordered_preferences) - ordered_preferences.index(value)


def _resolve_trace_path(trace_path: str, result_root: Path) -> Path:
    candidate = Path(trace_path)
    if candidate.is_absolute():
        return candidate
    repo_candidate = REPO_ROOT / candidate
    if repo_candidate.exists():
        return repo_candidate
    result_candidate = result_root.parent / candidate
    if result_candidate.exists():
        return result_candidate
    return repo_candidate


def _resolve_run(case: AnnotationCase, rows: Sequence[Dict[str, object]]) -> Dict[str, object]:
    candidates: List[Tuple[Tuple[int, int, int, int, int], Dict[str, object]]] = []
    for row in rows:
        if row.get("scenario_id") != case.scenario_id:
            continue
        context_score = _preference_score(str(row.get("context_system", "")), case.preferred_context_systems)
        if context_score is None:
            continue
        policy_score = _preference_score(str(row.get("policy", "")), case.preferred_policies)
        if policy_score is None:
            continue
        detector_score = _preference_score(str(row.get("detector", "")), case.preferred_detectors)
        if detector_score is None:
            continue
        if case.preferred_seed is not None and int(row.get("seed", 0)) != case.preferred_seed:
            continue
        if case.expected_final_success is not None and _parse_bool(row.get("success")) != case.expected_final_success:
            continue
        drift_step_match = 1 if case.expected_earliest_drift_step and row.get("first_drift_step") == case.expected_earliest_drift_step else 0
        score = (
            context_score or 0,
            policy_score or 0,
            detector_score or 0,
            drift_step_match,
            1 if case.expected_final_success is not None else 0,
        )
        candidates.append((score, dict(row)))
    if not candidates:
        raise ValueError(f"annotation case {case.example_id} could not resolve a matching run")
    candidates.sort(
        key=lambda item: (
            item[0][0],
            item[0][1],
            item[0][2],
            item[0][3],
            item[0][4],
            int(item[1].get("seed", 0)),
        ),
        reverse=True,
    )
    return candidates[0][1]


def _chosen_option_label(record: StepRecord, scenario: ScenarioSpec) -> str:
    if not record.chosen_option_id:
        return ""
    for event in scenario.events:
        if event.event_id != record.event_id or event.kind != "decision":
            continue
        for raw in event.payload.get("options", []):
            if raw.get("option_id") == record.chosen_option_id:
                return str(raw.get("label", ""))
    return ""


def _compact_record(record: StepRecord, scenario: ScenarioSpec) -> Dict[str, object]:
    return {
        "step_id": record.step_id,
        "index": record.index,
        "event_id": record.event_id,
        "kind": record.kind,
        "content": record.content,
        "chosen_option_id": record.chosen_option_id,
        "chosen_option_label": _chosen_option_label(record, scenario),
        "visible_evidence_ids": list(record.visible_state.visible_evidence_ids),
        "visible_constraints": list(record.visible_state.visible_constraints),
        "visible_decisions": list(record.visible_state.visible_decisions),
        "visible_events": list(record.visible_state.visible_events),
        "ledger_facts": record.memory_state.ledger.find_contents("facts"),
        "ledger_decisions": record.memory_state.ledger.find_contents("decisions"),
        "ledger_outstanding_work": record.memory_state.ledger.find_contents("outstanding_work"),
        "ledger_plan_steps": record.memory_state.ledger.find_contents("plan_steps"),
        "ledger_risk_flags": record.memory_state.ledger.find_contents("risk_flags"),
    }


def _compact_checkpoint(checkpoint: CheckpointState) -> Dict[str, object]:
    ledger = checkpoint.memory_state.ledger
    return {
        "checkpoint_id": checkpoint.checkpoint_id,
        "after_event_id": checkpoint.after_event_id,
        "step_id": checkpoint.step_id,
        "active_subgoal": checkpoint.visible_state.active_subgoal,
        "visible_constraints": list(checkpoint.visible_state.visible_constraints),
        "visible_evidence_ids": list(checkpoint.visible_state.visible_evidence_ids),
        "visible_decisions": list(checkpoint.visible_state.visible_decisions),
        "ledger_facts": ledger.find_contents("facts"),
        "ledger_decisions": ledger.find_contents("decisions"),
        "ledger_outstanding_work": ledger.find_contents("outstanding_work"),
        "ledger_plan_steps": ledger.find_contents("plan_steps"),
        "ledger_accepted_evidence": ledger.find_contents("accepted_evidence"),
        "ledger_risk_flags": ledger.find_contents("risk_flags"),
    }


def _gold_checkpoint_summary(scenario: ScenarioSpec) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for checkpoint in scenario.gold_checkpoints:
        rows.append(
            {
                "checkpoint_id": checkpoint.checkpoint_id,
                "after_event_id": checkpoint.after_event_id,
                "required_constraints": list(checkpoint.required_constraints),
                "required_evidence_ids": list(checkpoint.required_evidence_ids),
                "required_fact_contents": list(checkpoint.required_fact_contents),
                "required_plan_steps": list(checkpoint.required_plan_steps),
                "required_active_subgoal": checkpoint.required_active_subgoal,
            }
        )
    return rows


def _event_timeline(scenario: ScenarioSpec) -> List[Dict[str, object]]:
    return [
        {
            "event_id": event.event_id,
            "kind": event.kind,
            "text": event.text,
            "salience": event.salience,
        }
        for event in scenario.events
    ]


def build_annotation_packet(
    output_root: Path,
    annotation_set_name: str,
    result_roots: Sequence[Path],
) -> Dict[str, object]:
    annotation_set = load_annotation_set(annotation_set_name)
    rows = _load_result_rows(result_roots)
    cases: List[Dict[str, object]] = []
    answer_key_cases: List[Dict[str, object]] = []

    for case in annotation_set.cases:
        scenario = load_scenario(case.scenario_id)
        selected_run = _resolve_run(case, rows)
        result_root = Path(str(selected_run["_result_root"]))
        trace_path = _resolve_trace_path(str(selected_run["trace_path"]), result_root)
        trace_rows = [StepRecord.from_dict(item) for item in load_jsonl(trace_path)]
        checkpoints_path = trace_path.parent / "checkpoints.json"
        checkpoints = [
            CheckpointState.from_dict(item) for item in load_json(checkpoints_path).get("checkpoints", [])
        ]
        cases.append(
            {
                "example_id": case.example_id,
                "focus": case.focus,
                "scenario": {
                    "scenario_id": scenario.scenario_id,
                    "title": scenario.title,
                    "family": scenario.family,
                    "split": scenario.split,
                    "tags": list(scenario.tags),
                },
                "contract": scenario.intent_contract.to_dict(),
                "gold_checkpoints": _gold_checkpoint_summary(scenario),
                "event_timeline": _event_timeline(scenario),
                "selected_run": {
                    "context_system": selected_run["context_system"],
                    "policy": selected_run["policy"],
                    "detector": selected_run["detector"],
                    "seed": int(selected_run["seed"]),
                },
                "trace_excerpt": [_compact_record(record, scenario) for record in trace_rows],
                "checkpoint_excerpt": [_compact_checkpoint(checkpoint) for checkpoint in checkpoints],
                "review_questions": [
                    "What is the earliest visible drift point?",
                    "What is the primary drift label?",
                    "What severity should this drift receive?",
                    "Is the drift recoverable from the current or a nearby checkpoint?",
                    "Did the final outcome satisfy the contract?",
                ],
                "notes": list(case.notes),
            }
        )
        answer_key_cases.append(
            {
                "example_id": case.example_id,
                "scenario_id": case.scenario_id,
                "expected_primary_drift_label": case.expected_primary_drift_label,
                "expected_earliest_drift_step": case.expected_earliest_drift_step,
                "expected_severity": case.expected_severity,
                "expected_recoverable": case.expected_recoverable,
                "expected_final_success": case.expected_final_success,
                "resolved_run": {
                    "result_root": str(result_root),
                    "context_system": selected_run["context_system"],
                    "policy": selected_run["policy"],
                    "detector": selected_run["detector"],
                    "seed": int(selected_run["seed"]),
                    "success": _parse_bool(selected_run["success"]),
                    "first_drift_step": selected_run.get("first_drift_step", ""),
                    "trace_path": str(trace_path),
                },
            }
        )

    random.Random(annotation_set.name).shuffle(cases)

    generated_at = datetime.now(timezone.utc).isoformat()
    packet = {
        "annotation_set": annotation_set.to_dict(),
        "generated_at": generated_at,
        "result_roots": [str(path) for path in result_roots],
        "cases": cases,
    }
    answer_key = {
        "annotation_set": annotation_set.name,
        "generated_at": generated_at,
        "cases": answer_key_cases,
    }
    output_root.mkdir(parents=True, exist_ok=True)
    write_json(output_root / "packet.json", packet)
    write_json(output_root / "answer_key.json", answer_key)
    (output_root / "packet.md").write_text(_build_packet_markdown(annotation_set, cases, result_roots), encoding="utf-8")
    _write_response_template(output_root / "response_template.csv", cases)
    (output_root / "reviewer_instructions.md").write_text(
        _build_reviewer_instructions(annotation_set, result_roots),
        encoding="utf-8",
    )
    return {
        "annotation_set": annotation_set.name,
        "case_count": len(cases),
        "packet_path": str(output_root / "packet.json"),
        "answer_key_path": str(output_root / "answer_key.json"),
        "markdown_path": str(output_root / "packet.md"),
        "response_template_path": str(output_root / "response_template.csv"),
        "reviewer_instructions_path": str(output_root / "reviewer_instructions.md"),
    }


def _bullet_list(values: Sequence[str], fallback: str = "-") -> str:
    if not values:
        return fallback
    return ", ".join(f"`{value}`" for value in values)


def _format_path(path: str) -> str:
    return f"[{Path(path).name}]({path})"


def _build_packet_markdown(
    annotation_set: AnnotationSet,
    cases: Sequence[Dict[str, object]],
    result_roots: Sequence[Path],
) -> str:
    lines: List[str] = []
    lines.append("# DriftGuard Annotation Packet")
    lines.append("")
    lines.append(f"- `annotation_set`: {annotation_set.name}")
    lines.append(f"- `purpose`: {annotation_set.purpose}")
    lines.append(f"- `result_roots`: {', '.join(str(path) for path in result_roots)}")
    lines.append("- `response_template`: `response_template.csv` in the same output directory")
    lines.append("- `reviewer_instructions`: `reviewer_instructions.md` in the same output directory")
    lines.append("")
    lines.append("This packet is reviewer-safe by design:")
    lines.append("- it omits automated detector scores")
    lines.append("- it omits internal first-drift labels")
    lines.append("- it omits final success labels and answer-key metadata")
    lines.append("")
    lines.append("Use the annotation guide to label each case:")
    lines.append("- earliest visible drift point")
    lines.append("- primary drift label")
    lines.append("- severity")
    lines.append("- recoverability")
    lines.append("- final contract satisfaction")
    lines.append("")
    for case in cases:
        scenario = case["scenario"]
        selected_run = case["selected_run"]
        contract = case["contract"]
        lines.append(f"## `{case['example_id']}`")
        lines.append("")
        lines.append(f"- `scenario_id`: {scenario['scenario_id']}")
        lines.append(f"- `title`: {scenario['title']}")
        lines.append(f"- `family`: {scenario['family']}")
        lines.append(f"- `split`: {scenario['split']}")
        lines.append(f"- `focus`: {case['focus']}")
        lines.append(
            f"- `run`: context=`{selected_run['context_system']}` policy=`{selected_run['policy']}` detector=`{selected_run['detector']}` seed=`{selected_run['seed']}`"
        )
        lines.append("")
        lines.append("### Contract")
        lines.append("")
        lines.append(f"- `task_statement`: {contract['task_statement']}")
        lines.append(f"- `success_criteria`: {_bullet_list(contract['success_criteria'])}")
        lines.append(f"- `hard_constraints`: {_bullet_list(contract['hard_constraints'])}")
        lines.append(f"- `forbidden_actions`: {_bullet_list(contract['forbidden_actions'])}")
        lines.append(f"- `evidence_requirements`: {_bullet_list(contract['evidence_requirements'])}")
        lines.append("")
        lines.append("### Event Timeline")
        lines.append("")
        lines.append("| Event | Kind | Salience | Text |")
        lines.append("|---|---|---:|---|")
        for event in case["event_timeline"]:
            lines.append(
                f"| `{event['event_id']}` | `{event['kind']}` | {event['salience']} | {event['text']} |"
            )
        lines.append("")
        lines.append("### Gold Checkpoints")
        lines.append("")
        lines.append("| Checkpoint | After Event | Required Evidence | Active Subgoal |")
        lines.append("|---|---|---|---|")
        for checkpoint in case["gold_checkpoints"]:
            lines.append(
                f"| `{checkpoint['checkpoint_id']}` | `{checkpoint['after_event_id']}` | {_bullet_list(checkpoint['required_evidence_ids'])} | {checkpoint['required_active_subgoal'] or '-'} |"
            )
        lines.append("")
        lines.append("### Trace Excerpt")
        lines.append("")
        lines.append("| Step | Kind | Chosen Option | Visible Evidence | Visible Constraints | Content |")
        lines.append("|---|---|---|---|---|---|")
        for record in case["trace_excerpt"]:
            chosen_option = record["chosen_option_label"] or record["chosen_option_id"] or "-"
            lines.append(
                f"| `{record['step_id']}` | `{record['kind']}` | {chosen_option} | {_bullet_list(record['visible_evidence_ids'])} | {_bullet_list(record['visible_constraints'])} | {record['content']} |"
            )
        lines.append("")
        lines.append("### Checkpoint Excerpt")
        lines.append("")
        lines.append("| Checkpoint | After Event | Visible Evidence | Ledger Decisions | Outstanding Work |")
        lines.append("|---|---|---|---|---|")
        for checkpoint in case["checkpoint_excerpt"]:
            lines.append(
                f"| `{checkpoint['checkpoint_id']}` | `{checkpoint['after_event_id']}` | {_bullet_list(checkpoint['visible_evidence_ids'])} | {_bullet_list(checkpoint['ledger_decisions'])} | {_bullet_list(checkpoint['ledger_outstanding_work'])} |"
            )
        if case["notes"]:
            lines.append("")
            lines.append("### Notes")
            lines.append("")
            for note in case["notes"]:
                lines.append(f"- {note}")
        lines.append("")
        lines.append("### Reviewer Response")
        lines.append("")
        for question in case["review_questions"]:
            lines.append(f"- {question}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _build_reviewer_instructions(annotation_set: AnnotationSet, result_roots: Sequence[Path]) -> str:
    lines: List[str] = []
    lines.append("# DriftGuard Reviewer Instructions")
    lines.append("")
    lines.append(f"- `annotation_set`: {annotation_set.name}")
    lines.append(f"- `purpose`: {annotation_set.purpose}")
    lines.append(f"- `result_roots`: {', '.join(str(path) for path in result_roots)}")
    lines.append("")
    lines.append("## What to fill in")
    lines.append("")
    lines.append("For each row in `response_template.csv`, fill:")
    lines.append("- `reviewer_id`")
    lines.append("- `earliest_visible_drift_step`")
    lines.append("- `primary_drift_label`")
    lines.append("- `severity`")
    lines.append("- `recoverable`")
    lines.append("- `final_success`")
    lines.append("- `notes`")
    lines.append("")
    lines.append("## Allowed values")
    lines.append("")
    lines.append("- `primary_drift_label`: `no_drift`, `goal_drift`, `constraint_drift`, `plan_drift`, `evidence_drift`, `memory_drift`, `stagnation_drift`")
    lines.append("- `severity`: `none`, `low`, `medium`, `high`")
    lines.append("- `recoverable`: `True`, `False`, or blank if no drift is present")
    lines.append("- `final_success`: `True` or `False`")
    lines.append("")
    lines.append("## Earliest drift rule")
    lines.append("")
    lines.append("- Use the earliest observable step where the run materially diverges from the task contract.")
    lines.append("- If no visible drift occurs, leave `earliest_visible_drift_step` blank and use `primary_drift_label=no_drift` with `severity=none`.")
    lines.append("- Use only the visible packet contents. Do not infer hidden reasoning.")
    lines.append("")
    lines.append("## Packet hygiene")
    lines.append("")
    lines.append("- This packet intentionally omits internal detector scores and answer-key labels.")
    lines.append("- Please do not inspect raw benchmark result files; use the provided packet only.")
    return "\n".join(lines).rstrip() + "\n"


def _write_response_template(path: Path, cases: Sequence[Dict[str, object]]) -> None:
    fieldnames = [
        "example_id",
        "scenario_id",
        "family",
        "reviewer_id",
        "earliest_visible_drift_step",
        "primary_drift_label",
        "severity",
        "recoverable",
        "final_success",
        "notes",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for case in cases:
            scenario = case["scenario"]
            writer.writerow(
                {
                    "example_id": case["example_id"],
                    "scenario_id": scenario["scenario_id"],
                    "family": scenario["family"],
                    "reviewer_id": "",
                    "earliest_visible_drift_step": "",
                    "primary_drift_label": "",
                    "severity": "",
                    "recoverable": "",
                    "final_success": "",
                    "notes": "",
                }
            )
