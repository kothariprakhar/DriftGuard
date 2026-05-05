"""Load benchmark assets from the local repository."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from driftguard.schemas import AnnotationSet, ExperimentManifest, PerturbationSuite, PromptPack, ResourceProfile, ScenarioSpec
from driftguard.serialization import load_json


REPO_ROOT = Path(__file__).resolve().parent.parent
BENCHMARK_ROOT = REPO_ROOT / "benchmark"


def load_prompt_pack(version: str) -> PromptPack:
    path = BENCHMARK_ROOT / "prompts" / f"{version}.json"
    return PromptPack.from_dict(load_json(path))


def load_resource_profile(version: str) -> ResourceProfile:
    path = BENCHMARK_ROOT / "resource_profiles" / f"{version}.json"
    return ResourceProfile.from_dict(load_json(path))


def load_experiment_manifest(name: str) -> ExperimentManifest:
    path = BENCHMARK_ROOT / "experiment_manifests" / f"{name}.json"
    return ExperimentManifest.from_dict(load_json(path))


def load_annotation_set(name: str) -> AnnotationSet:
    path = BENCHMARK_ROOT / "annotation_sets" / f"{name}.json"
    return AnnotationSet.from_dict(load_json(path))


def load_perturbation_suite(name: str) -> PerturbationSuite:
    path = BENCHMARK_ROOT / "perturbations" / f"{name}.json"
    return PerturbationSuite.from_dict(load_json(path))


def load_split_registry() -> Dict[str, Any]:
    path = BENCHMARK_ROOT / "scenarios" / "splits.json"
    return load_json(path)


def load_split_metadata(split: str) -> Dict[str, Any]:
    registry = load_split_registry()
    for item in registry.get("splits", []):
        if item["split"] == split:
            return dict(item)
    raise KeyError(f"unknown split: {split}")


def resolve_scenario_splits(scenario_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    index = {item["scenario_id"]: item for item in load_scenario_index()}
    resolved: Dict[str, Dict[str, Any]] = {}
    for scenario_id in scenario_ids:
        if scenario_id not in index:
            raise KeyError(f"unknown scenario_id in manifest: {scenario_id}")
        split = index[scenario_id]["split"]
        resolved[scenario_id] = load_split_metadata(split)
    return resolved


def load_scenario_index(split: Optional[str] = None, family: Optional[str] = None) -> List[Dict[str, str]]:
    path = BENCHMARK_ROOT / "scenarios" / "index.json"
    data = load_json(path)
    scenarios = list(data["scenarios"])
    if split is not None:
        scenarios = [item for item in scenarios if item["split"] == split]
    if family is not None:
        scenarios = [item for item in scenarios if item["family"] == family]
    return scenarios


def load_scenario(scenario_id: str) -> ScenarioSpec:
    index = load_scenario_index()
    for entry in index:
        if entry["scenario_id"] == scenario_id:
            return ScenarioSpec.from_dict(load_json(BENCHMARK_ROOT / entry["path"]))
    raise KeyError(f"unknown scenario_id: {scenario_id}")


def load_split(split: str) -> List[ScenarioSpec]:
    specs: List[ScenarioSpec] = []
    for entry in load_scenario_index():
        if entry["split"] == split:
            specs.append(ScenarioSpec.from_dict(load_json(BENCHMARK_ROOT / entry["path"])))
    return specs
