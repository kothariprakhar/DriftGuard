"""Experiment-manifest execution helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional, Sequence, Union

from driftguard.registry import REPO_ROOT, load_experiment_manifest, resolve_scenario_splits
from driftguard.runner import run_episode
from driftguard.schemas import EpisodeResult, ExperimentManifest
from driftguard.serialization import load_json, write_json


@dataclass
class ManifestAudit:
    manifest_name: str
    manifest_stage: str
    splits: List[str]
    hidden_splits: List[str]
    frozen_splits: List[str]
    tuning_allowed_splits: List[str]
    split_counts: Dict[str, int]

    def to_dict(self) -> Dict[str, object]:
        return {
            "manifest_name": self.manifest_name,
            "manifest_stage": self.manifest_stage,
            "splits": list(self.splits),
            "hidden_splits": list(self.hidden_splits),
            "frozen_splits": list(self.frozen_splits),
            "tuning_allowed_splits": list(self.tuning_allowed_splits),
            "split_counts": dict(self.split_counts),
        }


@dataclass
class ExperimentRunSummary:
    manifest_name: str
    manifest_stage: str
    output_root: str
    total_runs: int
    successes: int
    success_rate: float
    scenario_ids: List[str]
    detectors: List[str]
    context_systems: List[str]
    policies: List[str]
    agent_backends: List[str]
    split_counts: Dict[str, int]
    hidden_splits: List[str]
    frozen_splits: List[str]
    per_context_success: Dict[str, Dict[str, Union[float, int]]]
    per_backend_success: Dict[str, Dict[str, Union[float, int]]]

    def to_dict(self) -> Dict[str, object]:
        return {
            "manifest_name": self.manifest_name,
            "manifest_stage": self.manifest_stage,
            "output_root": self.output_root,
            "total_runs": self.total_runs,
            "successes": self.successes,
            "success_rate": self.success_rate,
            "scenario_ids": list(self.scenario_ids),
            "detectors": list(self.detectors),
            "context_systems": list(self.context_systems),
            "policies": list(self.policies),
            "agent_backends": list(self.agent_backends),
            "split_counts": dict(self.split_counts),
            "hidden_splits": list(self.hidden_splits),
            "frozen_splits": list(self.frozen_splits),
            "per_context_success": dict(self.per_context_success),
            "per_backend_success": dict(self.per_backend_success),
        }


def _run_registry_path() -> Path:
    return REPO_ROOT / ".driftguard" / "run_registry.json"


def _load_run_registry() -> Dict[str, object]:
    path = _run_registry_path()
    if not path.exists():
        return {"hidden_runs": [], "locked_runs": []}
    data = load_json(path)
    data.setdefault("hidden_runs", [])
    data.setdefault("locked_runs", [])
    return data


def _save_run_registry(data: Dict[str, object]) -> None:
    write_json(_run_registry_path(), data)


def _record_hidden_run(manifest_name: str, executed_audit: ManifestAudit, run_summary: ExperimentRunSummary) -> None:
    if not executed_audit.hidden_splits:
        return
    registry = _load_run_registry()
    hidden_runs = list(registry.get("hidden_runs", []))
    hidden_runs.append(
        {
            "manifest_name": manifest_name,
            "splits": list(executed_audit.hidden_splits),
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "total_runs": run_summary.total_runs,
            "success_rate": run_summary.success_rate,
            "output_root": run_summary.output_root,
        }
    )
    registry["hidden_runs"] = hidden_runs
    _save_run_registry(registry)


def _record_locked_run(run_summary: ExperimentRunSummary, executed_audit: ManifestAudit) -> None:
    if run_summary.manifest_stage not in {"test", "holdout"}:
        return
    registry = _load_run_registry()
    locked_runs = list(registry.get("locked_runs", []))
    locked_runs.append(
        {
            "manifest_name": run_summary.manifest_name,
            "manifest_stage": run_summary.manifest_stage,
            "splits": list(executed_audit.splits),
            "hidden_splits": list(executed_audit.hidden_splits),
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "total_runs": run_summary.total_runs,
            "success_rate": run_summary.success_rate,
            "output_root": run_summary.output_root,
        }
    )
    registry["locked_runs"] = locked_runs
    _save_run_registry(registry)


def list_hidden_run_records() -> List[Dict[str, object]]:
    registry = _load_run_registry()
    return list(registry.get("hidden_runs", []))


def list_locked_run_records() -> List[Dict[str, object]]:
    registry = _load_run_registry()
    return list(registry.get("locked_runs", []))


def _audit_scenario_ids(manifest_name: str, manifest_stage: str, scenario_ids: Sequence[str]) -> ManifestAudit:
    resolved = resolve_scenario_splits(list(scenario_ids))
    split_counts: Dict[str, int] = {}
    hidden_splits: List[str] = []
    frozen_splits: List[str] = []
    tuning_allowed_splits: List[str] = []
    for metadata in resolved.values():
        split = metadata["split"]
        split_counts[split] = split_counts.get(split, 0) + 1
        if metadata.get("hidden") and split not in hidden_splits:
            hidden_splits.append(split)
        if metadata.get("frozen") and split not in frozen_splits:
            frozen_splits.append(split)
        if metadata.get("tuning_allowed") and split not in tuning_allowed_splits:
            tuning_allowed_splits.append(split)
    return ManifestAudit(
        manifest_name=manifest_name,
        manifest_stage=manifest_stage,
        splits=sorted(split_counts),
        hidden_splits=sorted(hidden_splits),
        frozen_splits=sorted(frozen_splits),
        tuning_allowed_splits=sorted(tuning_allowed_splits),
        split_counts=split_counts,
    )


def audit_manifest(manifest: ExperimentManifest) -> ManifestAudit:
    return _audit_scenario_ids(manifest.name, manifest.manifest_stage, list(manifest.scenarios))


def _enforce_manifest_policy(
    manifest: ExperimentManifest,
    audit: ManifestAudit,
    allow_hidden: bool,
    permit_repeated_hidden: bool,
    permit_repeated_locked: bool,
) -> None:
    if audit.hidden_splits and not allow_hidden:
        raise ValueError(
            f"manifest {manifest.name} includes hidden splits {audit.hidden_splits}; rerun with allow_hidden=True"
        )
    if audit.hidden_splits and not permit_repeated_hidden:
        prior_runs = [item for item in list_hidden_run_records() if item.get("manifest_name") == manifest.name]
        if prior_runs:
            raise ValueError(
                f"hidden manifest {manifest.name} has already been recorded; rerun only with permit_repeated_hidden=True"
            )
    if manifest.manifest_stage == "development":
        disallowed = [split for split in audit.frozen_splits if split not in {"pilot"}]
        if disallowed:
            raise ValueError(
                f"development manifest {manifest.name} should not target frozen selection splits {disallowed}"
            )
    if manifest.manifest_stage == "selection" and audit.tuning_allowed_splits:
        raise ValueError(
            f"selection manifest {manifest.name} should not include tuning-allowed splits {audit.tuning_allowed_splits}"
        )
    if manifest.manifest_stage == "test":
        if audit.tuning_allowed_splits:
            raise ValueError(
                f"test manifest {manifest.name} should not include tuning-allowed splits {audit.tuning_allowed_splits}"
            )
        if audit.hidden_splits:
            raise ValueError(f"test manifest {manifest.name} should not include hidden splits {audit.hidden_splits}")
        prior_runs = [item for item in list_locked_run_records() if item.get("manifest_name") == manifest.name]
        if prior_runs and not permit_repeated_locked:
            raise ValueError(
                f"test manifest {manifest.name} has already been recorded; rerun only with permit_repeated_locked=True"
            )
    if manifest.manifest_stage == "holdout" and not audit.hidden_splits:
        raise ValueError(f"holdout manifest {manifest.name} must target at least one hidden split")
    if manifest.manifest_stage == "holdout":
        prior_runs = [item for item in list_locked_run_records() if item.get("manifest_name") == manifest.name]
        if prior_runs and not permit_repeated_locked:
            raise ValueError(
                f"holdout manifest {manifest.name} has already been recorded; rerun only with permit_repeated_locked=True"
            )


def _iter_combinations(
    manifest: ExperimentManifest,
    seeds: Sequence[int],
    limit: Optional[int],
    scenario_filter: Optional[Sequence[str]],
    context_filter: Optional[Sequence[str]],
    detector_filter: Optional[Sequence[str]],
    policy_filter: Optional[Sequence[str]],
    agent_backend_filter: Optional[Sequence[str]],
) -> Iterable[Dict[str, object]]:
    emitted = 0
    scenarios = [item for item in manifest.scenarios if not scenario_filter or item in scenario_filter]
    contexts = [item for item in manifest.context_systems if not context_filter or item in context_filter]
    detectors = [item for item in manifest.detectors if not detector_filter or item in detector_filter]
    policies = [item for item in manifest.policies if not policy_filter or item in policy_filter]
    agent_backends = [item for item in manifest.agent_backends if not agent_backend_filter or item in agent_backend_filter]
    for scenario_id in scenarios:
        for context_system in contexts:
            for agent_backend in agent_backends:
                for detector in detectors:
                    for policy in policies:
                        for seed in seeds:
                            yield {
                                "scenario_id": scenario_id,
                                "context_system": context_system,
                                "agent_backend": agent_backend,
                                "detector": detector,
                                "policy": policy,
                                "seed": seed,
                            }
                            emitted += 1
                            if limit is not None and emitted >= limit:
                                return


def _aggregate(
    results: Sequence[EpisodeResult],
    manifest: ExperimentManifest,
    output_root: Path,
    audit: ManifestAudit,
) -> ExperimentRunSummary:
    successes = sum(1 for result in results if result.success)
    per_context_success: Dict[str, Dict[str, Union[float, int]]] = {}
    per_backend_success: Dict[str, Dict[str, Union[float, int]]] = {}
    for context_system in manifest.context_systems:
        context_results = [result for result in results if result.context_system == context_system]
        if not context_results:
            continue
        context_successes = sum(1 for result in context_results if result.success)
        per_context_success[context_system] = {
            "runs": len(context_results),
            "success_rate": context_successes / len(context_results),
        }
    for agent_backend in manifest.agent_backends:
        backend_results = [result for result in results if result.agent_backend == agent_backend]
        if not backend_results:
            continue
        backend_successes = sum(1 for result in backend_results if result.success)
        per_backend_success[agent_backend] = {
            "runs": len(backend_results),
            "success_rate": backend_successes / len(backend_results),
        }
    total_runs = len(results)
    return ExperimentRunSummary(
        manifest_name=manifest.name,
        manifest_stage=manifest.manifest_stage,
        output_root=str(output_root),
        total_runs=total_runs,
        successes=successes,
        success_rate=(successes / total_runs) if total_runs else 0.0,
        scenario_ids=list(manifest.scenarios),
        detectors=list(manifest.detectors),
        context_systems=list(manifest.context_systems),
        policies=list(manifest.policies),
        agent_backends=list(manifest.agent_backends),
        split_counts=dict(audit.split_counts),
        hidden_splits=list(audit.hidden_splits),
        frozen_splits=list(audit.frozen_splits),
        per_context_success=per_context_success,
        per_backend_success=per_backend_success,
    )


def run_manifest(
    manifest_name: str,
    output_root: Path,
    seeds: Optional[Sequence[int]] = None,
    limit: Optional[int] = None,
    scenario_filter: Optional[Sequence[str]] = None,
    context_filter: Optional[Sequence[str]] = None,
    detector_filter: Optional[Sequence[str]] = None,
    policy_filter: Optional[Sequence[str]] = None,
    agent_backend_filter: Optional[Sequence[str]] = None,
    allow_hidden: bool = False,
    permit_repeated_hidden: bool = False,
    permit_repeated_locked: bool = False,
) -> ExperimentRunSummary:
    manifest = load_experiment_manifest(manifest_name)
    manifest_audit = audit_manifest(manifest)
    _enforce_manifest_policy(
        manifest,
        manifest_audit,
        allow_hidden,
        permit_repeated_hidden,
        permit_repeated_locked,
    )
    resolved_seeds = list(seeds) if seeds is not None else [0]
    results: List[EpisodeResult] = []
    for combo in _iter_combinations(
        manifest,
        resolved_seeds,
        limit,
        scenario_filter,
        context_filter,
        detector_filter,
        policy_filter,
        agent_backend_filter,
    ):
        results.append(
            run_episode(
                scenario_id=str(combo["scenario_id"]),
                context_system=str(combo["context_system"]),
                policy=str(combo["policy"]),
                detector=str(combo["detector"]),
                output_root=output_root,
                seed=int(combo["seed"]),
                agent_backend=str(combo["agent_backend"]),
                prompt_pack_version=manifest.prompt_pack_version,
                resource_profile_version=manifest.resource_profile,
            )
        )
    executed_scenario_ids = sorted({result.scenario_id for result in results})
    executed_audit = _audit_scenario_ids(manifest.name, manifest.manifest_stage, executed_scenario_ids)
    summary = _aggregate(results, manifest, output_root, executed_audit)
    write_json(output_root / manifest.name / "summary.json", summary.to_dict())
    _record_hidden_run(manifest.name, executed_audit, summary)
    _record_locked_run(summary, executed_audit)
    return summary
