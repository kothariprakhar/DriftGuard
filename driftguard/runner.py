"""Benchmark runner for scripted local scenarios."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from driftguard.agent_backends import ALL_AGENT_BACKENDS
from driftguard.contexts import ALL_CONTEXT_SYSTEMS
from driftguard.detectors import ALL_DETECTORS
from driftguard.graders import aggregate_episode_metrics
from driftguard.policies import ALL_POLICIES
from driftguard.registry import load_prompt_pack, load_resource_profile, load_scenario
from driftguard.schemas import CheckpointState, EpisodeResult, InterventionAction, ScenarioSpec, StepRecord
from driftguard.traces import episode_dir, write_trace


def _checkpoint_for_event(
    scenario: ScenarioSpec,
    event_id: str,
    step_id: str,
    memory_state,
    visible_state,
) -> Optional[CheckpointState]:
    for gold in scenario.gold_checkpoints:
        if gold.after_event_id == event_id:
            return CheckpointState(
                checkpoint_id=gold.checkpoint_id,
                step_id=step_id,
                after_event_id=event_id,
                memory_state=memory_state.clone(),
                visible_state=visible_state,
            )
    return None


def run_episode(
    scenario_id: str,
    context_system: str,
    policy: str,
    detector: str,
    output_root: Path,
    seed: int = 0,
    agent_backend: str = "scripted_local",
    prompt_pack_version: Optional[str] = None,
    resource_profile_version: Optional[str] = None,
) -> EpisodeResult:
    scenario = load_scenario(scenario_id)
    resource_profile_name = resource_profile_version or scenario.resource_profile
    prompt_pack_name = prompt_pack_version or scenario.prompt_pack_version
    resource_profile = load_resource_profile(resource_profile_name)
    prompt_pack = load_prompt_pack(prompt_pack_name)
    context = ALL_CONTEXT_SYSTEMS[context_system]
    policy_obj = ALL_POLICIES[policy]
    detector_obj = ALL_DETECTORS[detector]
    backend = ALL_AGENT_BACKENDS[agent_backend]

    memory_state = context.bootstrap(scenario.intent_contract)
    records: List[StepRecord] = []
    checkpoints: List[CheckpointState] = []
    stopped = False
    usage_totals = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "request_count": 0}

    for index, event in enumerate(scenario.events, start=1):
        step_id = f"step-{index}"
        if event.kind == "decision":
            choice_visible_state = context.build_visible_state(
                memory_state=memory_state,
                contract=scenario.intent_contract,
                scenario=scenario,
                profile=resource_profile,
                current_event=event,
            )
            assessment = detector_obj.assess(scenario, choice_visible_state, event)
            intervention = policy_obj.apply(scenario.intent_contract, memory_state, assessment, checkpoints)
            if intervention.payload.get("stop"):
                stopped = True
            choice_visible_state = context.build_visible_state(
                memory_state=memory_state,
                contract=scenario.intent_contract,
                scenario=scenario,
                profile=resource_profile,
                current_event=event,
            )
            decision = backend.choose_option(
                scenario=scenario,
                event=event,
                visible_state=choice_visible_state,
                memory_state=memory_state.clone(),
                prompt_pack=prompt_pack,
                resource_profile=resource_profile,
                seed=seed or resource_profile.seed,
            )
            option = decision.option
            reasons = decision.reason_codes
            usage = decision.metadata.get("usage", {})
            if isinstance(usage, dict) and usage:
                for key in ("input_tokens", "output_tokens", "total_tokens"):
                    usage_totals[key] += int(usage.get(key, 0) or 0)
                usage_totals["request_count"] += 1
            context.observe_decision(memory_state, option, option.label, resource_profile, event.event_id)
            visible_state = context.build_visible_state(
                memory_state=memory_state,
                contract=scenario.intent_contract,
                scenario=scenario,
                profile=resource_profile,
                current_event=event,
            )
            record = StepRecord(
                step_id=step_id,
                index=index,
                event_id=event.event_id,
                kind=event.kind,
                content=event.text,
                chosen_option_id=option.option_id,
                correct_option_id=event.payload["correct_option_id"],
                chosen_drift_label=option.drift_label_if_chosen,
                visible_state=visible_state,
                drift_assessment=assessment,
                intervention=intervention,
                memory_state=memory_state.clone(),
                agent_backend=agent_backend,
                agent_metadata=decision.metadata,
                reason_codes=reasons,
            )
        else:
            context.observe(memory_state, event, resource_profile)
            visible_state = context.build_visible_state(
                memory_state=memory_state,
                contract=scenario.intent_contract,
                scenario=scenario,
                profile=resource_profile,
                current_event=event,
            )
            record = StepRecord(
                step_id=step_id,
                index=index,
                event_id=event.event_id,
                kind=event.kind,
                content=event.text,
                chosen_option_id=None,
                correct_option_id=None,
                chosen_drift_label=None,
                visible_state=visible_state,
                drift_assessment=detector_obj.assess(scenario, visible_state, event),
                intervention=InterventionAction(action_type="none", applied=False, reason="non_decision_event"),
                memory_state=memory_state.clone(),
                agent_backend=agent_backend,
                agent_metadata={
                    "backend_kind": backend.backend_kind,
                    "prompt_pack_version": prompt_pack.version,
                    "resource_profile": resource_profile.version,
                },
                reason_codes=[],
            )
        records.append(record)
        checkpoint = _checkpoint_for_event(scenario, event.event_id, step_id, memory_state, visible_state)
        if checkpoint:
            checkpoints.append(checkpoint)
        if stopped:
            break

    metrics = aggregate_episode_metrics(scenario, records, checkpoints)
    backend_metadata = backend.describe()
    if usage_totals["request_count"]:
        backend_metadata["usage"] = {
            "input_tokens": usage_totals["input_tokens"],
            "output_tokens": usage_totals["output_tokens"],
            "total_tokens": usage_totals["total_tokens"],
            "request_count": usage_totals["request_count"],
        }
    result = EpisodeResult(
        scenario_id=scenario.scenario_id,
        context_system=context_system,
        policy=policy,
        detector=detector,
        seed=seed or resource_profile.seed,
        success=bool(metrics["success"]),
        score=float(metrics["decision_accuracy"]),
        first_drift_step=metrics["first_drift_step"],
        metrics=metrics,
        trace_path=str(
            episode_dir(
                output_root,
                scenario.scenario_id,
                context_system,
                agent_backend,
                detector,
                policy,
                seed or resource_profile.seed,
            )
            / "trace.jsonl"
        ),
        agent_backend=agent_backend,
        prompt_pack_version=prompt_pack.version,
        resource_profile=resource_profile.version,
        backend_metadata=backend_metadata,
    )
    trace_path = write_trace(
        output_root,
        scenario,
        result,
        records,
        checkpoints,
        prompt_pack=prompt_pack.to_dict(),
        resource_profile=resource_profile.to_dict(),
    )
    result.trace_path = str(trace_path)
    return result
