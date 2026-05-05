"""Trace writing and replay support."""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

from driftguard.graders import aggregate_episode_metrics
from driftguard.schemas import CheckpointState, EpisodeResult, ScenarioSpec, StepRecord
from driftguard.serialization import load_json, load_jsonl, write_json, write_jsonl


def episode_dir(
    output_root: Path,
    scenario_id: str,
    context_system: str,
    agent_backend: str,
    detector: str,
    policy: str,
    seed: int,
) -> Path:
    return output_root / scenario_id / context_system / agent_backend / detector / policy / f"seed-{seed}"


def write_trace(
    output_root: Path,
    scenario: ScenarioSpec,
    result: EpisodeResult,
    records: List[StepRecord],
    checkpoints: List[CheckpointState],
    prompt_pack: dict | None = None,
    resource_profile: dict | None = None,
) -> Path:
    path = episode_dir(
        output_root,
        scenario.scenario_id,
        result.context_system,
        result.agent_backend,
        result.detector,
        result.policy,
        result.seed,
    )
    write_json(path / "result.json", result.to_dict())
    write_json(path / "scenario.json", scenario.to_dict())
    if prompt_pack is not None:
        write_json(path / "prompt_pack.json", prompt_pack)
    if resource_profile is not None:
        write_json(path / "resource_profile.json", resource_profile)
    write_jsonl(path / "trace.jsonl", [record.to_dict() for record in records])
    write_json(path / "checkpoints.json", {"checkpoints": [checkpoint.to_dict() for checkpoint in checkpoints]})
    return path / "trace.jsonl"


def replay_trace(trace_path: Path) -> Tuple[EpisodeResult, List[StepRecord], List[CheckpointState]]:
    base = trace_path.parent
    result = EpisodeResult.from_dict(load_json(base / "result.json"))
    records = [StepRecord.from_dict(item) for item in load_jsonl(trace_path)]
    checkpoints = [
        CheckpointState.from_dict(item) for item in load_json(base / "checkpoints.json")["checkpoints"]
    ]
    return result, records, checkpoints


def recompute_metrics(trace_path: Path) -> dict:
    base = trace_path.parent
    scenario = ScenarioSpec.from_dict(load_json(base / "scenario.json"))
    _, records, checkpoints = replay_trace(trace_path)
    return aggregate_episode_metrics(scenario, records, checkpoints)
