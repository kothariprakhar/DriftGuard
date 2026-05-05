"""Benchmark linting and coverage summaries."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Set

from driftguard.agent_backends import ALL_AGENT_BACKENDS
from driftguard.contexts import ALL_CONTEXT_SYSTEMS
from driftguard.detectors import ALL_DETECTORS
from driftguard.experiments import audit_manifest
from driftguard.policies import ALL_POLICIES
from driftguard.registry import (
    BENCHMARK_ROOT,
    load_annotation_set,
    load_experiment_manifest,
    load_prompt_pack,
    load_resource_profile,
    load_scenario,
    load_scenario_index,
    load_split_registry,
)


def _scenario_files_on_disk() -> Set[str]:
    return {
        str(path.relative_to(BENCHMARK_ROOT))
        for path in (BENCHMARK_ROOT / "scenarios").glob("*/*.json")
        if path.name not in {"index.json", "splits.json"}
    }


def benchmark_stats() -> Dict[str, object]:
    index = load_scenario_index()
    split_counts: Dict[str, int] = {}
    family_counts: Dict[str, int] = {}
    split_family_counts: Dict[str, Dict[str, int]] = {}
    for item in index:
        split = item["split"]
        family = item["family"]
        split_counts[split] = split_counts.get(split, 0) + 1
        family_counts[family] = family_counts.get(family, 0) + 1
        split_family_counts.setdefault(split, {})
        split_family_counts[split][family] = split_family_counts[split].get(family, 0) + 1

    manifest_stats: Dict[str, Dict[str, object]] = {}
    for path in sorted((BENCHMARK_ROOT / "experiment_manifests").glob("*.json")):
        manifest = load_experiment_manifest(path.stem)
        audit = audit_manifest(manifest)
        manifest_stats[manifest.name] = {
            "stage": manifest.manifest_stage,
            "scenario_count": len(manifest.scenarios),
            "splits": list(audit.splits),
            "agent_backends": list(manifest.agent_backends),
        }

    annotation_set_stats: Dict[str, Dict[str, object]] = {}
    for path in sorted((BENCHMARK_ROOT / "annotation_sets").glob("*.json")):
        annotation_set = load_annotation_set(path.stem)
        annotation_set_stats[annotation_set.name] = {
            "case_count": len(annotation_set.cases),
            "scenario_ids": sorted({case.scenario_id for case in annotation_set.cases}),
        }

    return {
        "total_scenarios": len(index),
        "split_counts": split_counts,
        "family_counts": family_counts,
        "split_family_counts": split_family_counts,
        "manifest_stats": manifest_stats,
        "annotation_set_stats": annotation_set_stats,
    }


def lint_benchmark() -> Dict[str, object]:
    errors: List[str] = []
    warnings: List[str] = []

    split_registry = load_split_registry()
    registered_splits = {item["split"] for item in split_registry.get("splits", [])}
    index = load_scenario_index()
    scenario_ids = [item["scenario_id"] for item in index]
    duplicate_ids = sorted({item for item in scenario_ids if scenario_ids.count(item) > 1})
    for item in duplicate_ids:
        errors.append(f"duplicate scenario_id in index: {item}")

    indexed_paths = {item["path"] for item in index}
    disk_paths = _scenario_files_on_disk()
    for path in sorted(indexed_paths.difference(disk_paths)):
        errors.append(f"indexed scenario path missing on disk: {path}")
    for path in sorted(disk_paths.difference(indexed_paths)):
        errors.append(f"scenario file exists on disk but is not indexed: {path}")

    for entry in index:
        if entry["split"] not in registered_splits:
            errors.append(f"scenario {entry['scenario_id']} uses unregistered split {entry['split']}")
            continue
        try:
            scenario = load_scenario(entry["scenario_id"])
        except Exception as exc:
            errors.append(f"failed to load scenario {entry['scenario_id']}: {exc}")
            continue
        if scenario.split != entry["split"]:
            errors.append(f"scenario {entry['scenario_id']} split mismatch between file and index")
        if scenario.family != entry["family"]:
            errors.append(f"scenario {entry['scenario_id']} family mismatch between file and index")
        try:
            load_prompt_pack(scenario.prompt_pack_version)
        except Exception as exc:
            errors.append(f"scenario {entry['scenario_id']} prompt pack error: {exc}")
        try:
            load_resource_profile(scenario.resource_profile)
        except Exception as exc:
            errors.append(f"scenario {entry['scenario_id']} resource profile error: {exc}")
        if scenario.split in {"dev", "validation"}:
            has_rich_checkpoint = any(
                checkpoint.required_fact_contents
                or checkpoint.required_ledger_decisions
                or checkpoint.required_plan_steps
                or checkpoint.required_provenance
                for checkpoint in scenario.gold_checkpoints
            )
            if not has_rich_checkpoint:
                warnings.append(f"scenario {entry['scenario_id']} lacks richer checkpoint fields")

    split_family_counts = benchmark_stats()["split_family_counts"]
    for split in ("dev", "validation"):
        families = split_family_counts.get(split, {})
        if not families:
            warnings.append(f"split {split} currently has no scenarios")
            continue
        if len(families) < 4:
            warnings.append(f"split {split} does not yet cover all four core families")

    for path in sorted((BENCHMARK_ROOT / "experiment_manifests").glob("*.json")):
        manifest = load_experiment_manifest(path.stem)
        if manifest.prompt_pack_version:
            try:
                load_prompt_pack(manifest.prompt_pack_version)
            except Exception as exc:
                errors.append(f"manifest {manifest.name} prompt pack error: {exc}")
        if manifest.resource_profile:
            try:
                load_resource_profile(manifest.resource_profile)
            except Exception as exc:
                errors.append(f"manifest {manifest.name} resource profile error: {exc}")
        for name in manifest.context_systems:
            if name not in ALL_CONTEXT_SYSTEMS:
                errors.append(f"manifest {manifest.name} references unknown context system {name}")
        for name in manifest.detectors:
            if name not in ALL_DETECTORS:
                errors.append(f"manifest {manifest.name} references unknown detector {name}")
        for name in manifest.policies:
            if name not in ALL_POLICIES:
                errors.append(f"manifest {manifest.name} references unknown policy {name}")
        for name in manifest.agent_backends:
            if name not in ALL_AGENT_BACKENDS:
                errors.append(f"manifest {manifest.name} references unknown agent backend {name}")
        try:
            audit_manifest(manifest)
        except Exception as exc:
            errors.append(f"manifest {manifest.name} audit error: {exc}")

    for path in sorted((BENCHMARK_ROOT / "annotation_sets").glob("*.json")):
        try:
            annotation_set = load_annotation_set(path.stem)
        except Exception as exc:
            errors.append(f"annotation set {path.stem} load error: {exc}")
            continue
        seen_example_ids: Set[str] = set()
        for case in annotation_set.cases:
            if case.example_id in seen_example_ids:
                errors.append(f"annotation set {annotation_set.name} duplicates example_id {case.example_id}")
            seen_example_ids.add(case.example_id)
            if case.scenario_id not in scenario_ids:
                errors.append(
                    f"annotation set {annotation_set.name} references unknown scenario_id {case.scenario_id}"
                )

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "stats": benchmark_stats(),
    }
