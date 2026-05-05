import tempfile
import unittest
from pathlib import Path

from driftguard.registry import (
    load_experiment_manifest,
    load_prompt_pack,
    load_scenario,
    load_scenario_index,
    load_split_metadata,
)
from driftguard.runner import run_episode
from driftguard.schemas import CheckpointState, StepRecord
from driftguard.traces import replay_trace


class RegistryAndSchemaTests(unittest.TestCase):
    def test_prompt_pack_loading(self) -> None:
        prompt_pack = load_prompt_pack("v1")
        self.assertEqual(prompt_pack.version, "v1")
        self.assertIn("base_agent", prompt_pack.prompts)

    def test_scenario_loading(self) -> None:
        scenario = load_scenario("pilot_evidence_brief")
        self.assertEqual(scenario.family, "evidence_synthesis")
        self.assertTrue(scenario.events)
        self.assertTrue(scenario.gold_checkpoints)

    def test_experiment_manifest_loading(self) -> None:
        manifest = load_experiment_manifest("pilot_baselines")
        self.assertEqual(manifest.name, "pilot_baselines")
        self.assertIn("ledger_only", manifest.context_systems)
        self.assertIn("rule_based", manifest.detectors)
        self.assertIn("scripted_local", manifest.agent_backends)

    def test_dev_manifest_loading(self) -> None:
        manifest = load_experiment_manifest("dev_wave1_baselines")
        self.assertEqual(manifest.name, "dev_wave1_baselines")
        self.assertIn("dev_finance_variance_note", manifest.scenarios)
        self.assertEqual(manifest.manifest_stage, "development")

    def test_validation_manifest_loading(self) -> None:
        manifest = load_experiment_manifest("validation_wave1_baselines")
        self.assertEqual(manifest.name, "validation_wave1_baselines")
        self.assertEqual(manifest.manifest_stage, "selection")
        self.assertIn("validation_procurement_audit_packet", manifest.scenarios)
        self.assertIn("validation_billing_chat_escalation", manifest.scenarios)

    def test_test_manifest_loading(self) -> None:
        manifest = load_experiment_manifest("test_wave2_baselines")
        self.assertEqual(manifest.name, "test_wave2_baselines")
        self.assertEqual(manifest.manifest_stage, "test")
        self.assertIn("test_airworthiness_certificate_packet", manifest.scenarios)
        self.assertIn("test_payroll_redirect_injection", manifest.scenarios)

    def test_split_metadata_and_index_filtering(self) -> None:
        metadata = load_split_metadata("dev")
        self.assertTrue(metadata["tuning_allowed"])
        dev_entries = load_scenario_index(split="dev")
        self.assertTrue(dev_entries)
        self.assertTrue(all(item["split"] == "dev" for item in dev_entries))
        evidence_entries = load_scenario_index(split="dev", family="evidence_synthesis")
        self.assertTrue(evidence_entries)
        self.assertTrue(all(item["family"] == "evidence_synthesis" for item in evidence_entries))
        validation_metadata = load_split_metadata("validation")
        self.assertTrue(validation_metadata["frozen"])
        self.assertFalse(validation_metadata["tuning_allowed"])
        test_metadata = load_split_metadata("test")
        self.assertTrue(test_metadata["frozen"])
        self.assertFalse(test_metadata["tuning_allowed"])

    def test_checkpoint_and_step_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = run_episode(
                scenario_id="pilot_tool_order",
                context_system="ledger_only",
                policy="anchor_refresh",
                detector="rule_based",
                output_root=Path(directory),
            )
            self.assertEqual(result.agent_backend, "scripted_local")
            self.assertEqual(result.prompt_pack_version, "v1")
            _, records, checkpoints = replay_trace(Path(result.trace_path))
            self.assertTrue(records)
            self.assertTrue(checkpoints)
            step = StepRecord.from_dict(records[0].to_dict())
            checkpoint = CheckpointState.from_dict(checkpoints[0].to_dict())
            self.assertEqual(step.step_id, records[0].step_id)
            self.assertEqual(checkpoint.checkpoint_id, checkpoints[0].checkpoint_id)
            self.assertEqual(step.agent_backend, "scripted_local")


if __name__ == "__main__":
    unittest.main()
