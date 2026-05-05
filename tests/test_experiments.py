import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from driftguard.experiments import (
    ExperimentRunSummary,
    ManifestAudit,
    _enforce_manifest_policy,
    _record_hidden_run,
    _record_locked_run,
    list_hidden_run_records,
    list_locked_run_records,
)
from driftguard.schemas import ExperimentManifest


class ExperimentGovernanceTests(unittest.TestCase):
    def test_hidden_run_registry_records_entries(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            registry_path = Path(directory) / "run_registry.json"
            audit = ManifestAudit(
                manifest_name="hidden_manifest",
                manifest_stage="holdout",
                splits=["shadow_holdout"],
                hidden_splits=["shadow_holdout"],
                frozen_splits=["shadow_holdout"],
                tuning_allowed_splits=[],
                split_counts={"shadow_holdout": 1},
            )
            summary = ExperimentRunSummary(
                manifest_name="hidden_manifest",
                manifest_stage="holdout",
                output_root=str(Path(directory) / "results"),
                total_runs=1,
                successes=1,
                success_rate=1.0,
                scenario_ids=["shadow_case"],
                detectors=["rule_based"],
                context_systems=["ledger_only"],
                policies=["none"],
                agent_backends=["scripted_local"],
                split_counts={"shadow_holdout": 1},
                hidden_splits=["shadow_holdout"],
                frozen_splits=["shadow_holdout"],
                per_context_success={"ledger_only": {"runs": 1, "success_rate": 1.0}},
                per_backend_success={"scripted_local": {"runs": 1, "success_rate": 1.0}},
            )
            with patch("driftguard.experiments._run_registry_path", return_value=registry_path):
                _record_hidden_run("hidden_manifest", audit, summary)
                records = list_hidden_run_records()
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["manifest_name"], "hidden_manifest")

    def test_repeated_hidden_manifest_requires_override(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            registry_path = Path(directory) / "run_registry.json"
            manifest = ExperimentManifest(
                name="hidden_manifest",
                purpose="test",
                prompt_pack_version="v1",
                resource_profile="v1_local_validation",
                scenarios=["shadow_case"],
                context_systems=["ledger_only"],
                detectors=["rule_based"],
                policies=["none"],
                agent_backends=["scripted_local"],
                notes=[],
                manifest_stage="holdout",
            )
            audit = ManifestAudit(
                manifest_name="hidden_manifest",
                manifest_stage="holdout",
                splits=["shadow_holdout"],
                hidden_splits=["shadow_holdout"],
                frozen_splits=["shadow_holdout"],
                tuning_allowed_splits=[],
                split_counts={"shadow_holdout": 1},
            )
            summary = ExperimentRunSummary(
                manifest_name="hidden_manifest",
                manifest_stage="holdout",
                output_root=str(Path(directory) / "results"),
                total_runs=1,
                successes=1,
                success_rate=1.0,
                scenario_ids=["shadow_case"],
                detectors=["rule_based"],
                context_systems=["ledger_only"],
                policies=["none"],
                agent_backends=["scripted_local"],
                split_counts={"shadow_holdout": 1},
                hidden_splits=["shadow_holdout"],
                frozen_splits=["shadow_holdout"],
                per_context_success={"ledger_only": {"runs": 1, "success_rate": 1.0}},
                per_backend_success={"scripted_local": {"runs": 1, "success_rate": 1.0}},
            )
            with patch("driftguard.experiments._run_registry_path", return_value=registry_path):
                _record_hidden_run("hidden_manifest", audit, summary)
                with self.assertRaises(ValueError):
                    _enforce_manifest_policy(
                        manifest,
                        audit,
                        allow_hidden=True,
                        permit_repeated_hidden=False,
                        permit_repeated_locked=False,
                    )
                _enforce_manifest_policy(
                    manifest,
                    audit,
                    allow_hidden=True,
                    permit_repeated_hidden=True,
                    permit_repeated_locked=True,
                )

    def test_repeated_test_manifest_requires_override(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            registry_path = Path(directory) / "run_registry.json"
            manifest = ExperimentManifest(
                name="test_manifest",
                purpose="test",
                prompt_pack_version="v1",
                resource_profile="v1_local_test",
                scenarios=["test_case"],
                context_systems=["ledger_only"],
                detectors=["rule_based"],
                policies=["none"],
                agent_backends=["scripted_local"],
                notes=[],
                manifest_stage="test",
            )
            audit = ManifestAudit(
                manifest_name="test_manifest",
                manifest_stage="test",
                splits=["test"],
                hidden_splits=[],
                frozen_splits=["test"],
                tuning_allowed_splits=[],
                split_counts={"test": 1},
            )
            summary = ExperimentRunSummary(
                manifest_name="test_manifest",
                manifest_stage="test",
                output_root=str(Path(directory) / "results"),
                total_runs=1,
                successes=1,
                success_rate=1.0,
                scenario_ids=["test_case"],
                detectors=["rule_based"],
                context_systems=["ledger_only"],
                policies=["none"],
                agent_backends=["scripted_local"],
                split_counts={"test": 1},
                hidden_splits=[],
                frozen_splits=["test"],
                per_context_success={"ledger_only": {"runs": 1, "success_rate": 1.0}},
                per_backend_success={"scripted_local": {"runs": 1, "success_rate": 1.0}},
            )
            with patch("driftguard.experiments._run_registry_path", return_value=registry_path):
                _record_locked_run(summary, audit)
                records = list_locked_run_records()
                self.assertEqual(len(records), 1)
                with self.assertRaises(ValueError):
                    _enforce_manifest_policy(
                        manifest,
                        audit,
                        allow_hidden=False,
                        permit_repeated_hidden=False,
                        permit_repeated_locked=False,
                    )
                _enforce_manifest_policy(
                    manifest,
                    audit,
                    allow_hidden=False,
                    permit_repeated_hidden=False,
                    permit_repeated_locked=True,
                )


if __name__ == "__main__":
    unittest.main()
