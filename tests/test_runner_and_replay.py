import tempfile
import unittest
from pathlib import Path

from driftguard.experiments import audit_manifest, run_manifest
from driftguard.registry import load_experiment_manifest
from driftguard.runner import run_episode
from driftguard.traces import recompute_metrics, replay_trace


class RunnerAndReplayTests(unittest.TestCase):
    def test_local_end_to_end_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = run_episode(
                scenario_id="pilot_evidence_brief",
                context_system="ledger_only",
                policy="none",
                detector="rule_based",
                output_root=Path(directory),
            )
            self.assertTrue(result.success)
            self.assertEqual(result.score, 1.0)
            self.assertEqual(result.agent_backend, "scripted_local")
            self.assertTrue((Path(result.trace_path).parent / "prompt_pack.json").exists())
            self.assertTrue((Path(result.trace_path).parent / "resource_profile.json").exists())

    def test_replay_matches_cached_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = run_episode(
                scenario_id="pilot_tool_order",
                context_system="summary_only",
                policy="anchor_refresh",
                detector="rule_based",
                output_root=Path(directory),
            )
            replayed_result, records, checkpoints = replay_trace(Path(result.trace_path))
            metrics = recompute_metrics(Path(result.trace_path))
            self.assertEqual(replayed_result.scenario_id, result.scenario_id)
            self.assertTrue(records)
            self.assertTrue(checkpoints)
            self.assertEqual(metrics["decision_accuracy"], result.metrics["decision_accuracy"])
            self.assertEqual(metrics["first_drift_step"], result.metrics["first_drift_step"])
            self.assertEqual(replayed_result.trace_path, result.trace_path)

    def test_detector_runs_do_not_overwrite_each_other(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = run_episode(
                scenario_id="pilot_evidence_brief",
                context_system="raw_transcript",
                policy="none",
                detector="rule_based",
                output_root=root,
                seed=11,
            )
            second = run_episode(
                scenario_id="pilot_evidence_brief",
                context_system="raw_transcript",
                policy="none",
                detector="calibrated_ensemble",
                output_root=root,
                seed=11,
            )
            self.assertNotEqual(first.trace_path, second.trace_path)
            self.assertIn("/scripted_local/", first.trace_path)
            self.assertIn("/rule_based/", first.trace_path)
            self.assertIn("/scripted_local/", second.trace_path)
            self.assertIn("/calibrated_ensemble/", second.trace_path)
            self.assertTrue(Path(first.trace_path).exists())
            self.assertTrue(Path(second.trace_path).exists())

    def test_grader_output_contains_expected_keys(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = run_episode(
                scenario_id="pilot_email_injection",
                context_system="summary_only",
                policy="anchor_refresh",
                detector="rule_based",
                output_root=Path(directory),
            )
            self.assertIn("mean_checkpoint_adherence", result.metrics)
            self.assertIn("mean_detector_score", result.metrics)
            self.assertIn("decision_accuracy", result.metrics)

    def test_manifest_runner_writes_summary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            summary = run_manifest(
                "pilot_baselines",
                output_root=Path(directory),
                seeds=[7],
                scenario_filter=["pilot_evidence_brief"],
                context_filter=["ledger_only"],
                detector_filter=["rule_based"],
                policy_filter=["none"],
            )
            self.assertEqual(summary.total_runs, 1)
            self.assertGreaterEqual(summary.success_rate, 0.0)
            self.assertEqual(summary.successes, 1)
            self.assertTrue((Path(directory) / "pilot_baselines" / "summary.json").exists())

    def test_dev_scenario_shows_ledger_advantage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            raw = run_episode(
                scenario_id="dev_finance_variance_note",
                context_system="raw_transcript",
                policy="none",
                detector="rule_based",
                output_root=Path(directory),
            )
            ledger = run_episode(
                scenario_id="dev_finance_variance_note",
                context_system="ledger_only",
                policy="none",
                detector="rule_based",
                output_root=Path(directory),
            )
            self.assertFalse(raw.success)
            self.assertTrue(ledger.success)

    def test_validation_manifest_audit_and_run(self) -> None:
        manifest = load_experiment_manifest("validation_wave1_baselines")
        audit = audit_manifest(manifest)
        self.assertEqual(audit.manifest_stage, "selection")
        self.assertEqual(audit.splits, ["validation"])
        self.assertFalse(audit.tuning_allowed_splits)
        self.assertEqual(audit.split_counts["validation"], 8)
        with tempfile.TemporaryDirectory() as directory:
            summary = run_manifest(
                "validation_wave1_baselines",
                output_root=Path(directory),
                scenario_filter=["validation_procurement_audit_packet"],
                context_filter=["ledger_only"],
                detector_filter=["rule_based"],
                policy_filter=["none"],
                seeds=[17],
            )
            self.assertEqual(summary.total_runs, 1)
            self.assertEqual(summary.split_counts["validation"], 1)


if __name__ == "__main__":
    unittest.main()
