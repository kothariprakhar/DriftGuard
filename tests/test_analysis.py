import tempfile
import unittest
from pathlib import Path

from driftguard.analysis import compare_contexts, compare_detectors, compare_policies, summarize_results
from driftguard.runner import run_episode


class AnalysisTests(unittest.TestCase):
    def test_summarize_results_writes_summary_and_csv(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run_episode(
                scenario_id="pilot_evidence_brief",
                context_system="ledger_only",
                policy="none",
                detector="rule_based",
                output_root=root,
            )
            summary = summarize_results(root)
            self.assertEqual(summary["total_runs"], 1)
            self.assertEqual(summary["success_rate"], 1.0)
            self.assertIn("evidence_synthesis", summary["by_family"])
            self.assertIn("pilot", summary["by_split"])
            self.assertIn("none", summary["by_policy"])
            self.assertIn("rule_based", summary["by_detector"])
            self.assertIn("scripted_local", summary["by_agent_backend"])
            self.assertTrue((root / "summary.json").exists())
            self.assertTrue((root / "runs.csv").exists())

    def test_compare_contexts_reports_paired_deltas(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run_episode(
                scenario_id="pilot_evidence_brief",
                context_system="ledger_only",
                policy="none",
                detector="rule_based",
                output_root=root,
                seed=7,
            )
            run_episode(
                scenario_id="pilot_evidence_brief",
                context_system="raw_transcript",
                policy="none",
                detector="rule_based",
                output_root=root,
                seed=7,
            )
            summarize_results(root)
            comparison = compare_contexts(root, "ledger_only", ["raw_transcript"])
            raw = comparison["comparisons"]["raw_transcript"]
            self.assertEqual(raw["paired_runs"], 1)
            self.assertGreaterEqual(raw["success_delta"], 0.0)
            self.assertEqual(len(raw["success_delta_ci"]), 2)

    def test_compare_policies_and_detectors_report_paired_deltas(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run_episode(
                scenario_id="pilot_evidence_brief",
                context_system="raw_transcript",
                policy="none",
                detector="rule_based",
                output_root=root,
                seed=9,
            )
            run_episode(
                scenario_id="pilot_evidence_brief",
                context_system="raw_transcript",
                policy="anchor_refresh",
                detector="rule_based",
                output_root=root,
                seed=9,
            )
            run_episode(
                scenario_id="pilot_evidence_brief",
                context_system="raw_transcript",
                policy="anchor_refresh",
                detector="calibrated_ensemble",
                output_root=root,
                seed=9,
            )
            summarize_results(root)
            policy_comparison = compare_policies(
                root,
                "anchor_refresh",
                ["none"],
                filters={"context_system": ["raw_transcript"], "detector": ["rule_based"]},
            )
            none = policy_comparison["comparisons"]["none"]
            self.assertEqual(none["paired_runs"], 1)
            self.assertGreaterEqual(none["success_delta"], 0.0)

            detector_comparison = compare_detectors(
                root,
                "rule_based",
                ["calibrated_ensemble"],
                filters={"context_system": ["raw_transcript"], "policy": ["anchor_refresh"]},
            )
            ensemble = detector_comparison["comparisons"]["calibrated_ensemble"]
            self.assertEqual(ensemble["paired_runs"], 1)
            self.assertEqual(len(ensemble["mean_score_delta_ci"]), 2)

    def test_summarize_results_keeps_multiple_detector_runs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run_episode(
                scenario_id="pilot_evidence_brief",
                context_system="raw_transcript",
                policy="none",
                detector="rule_based",
                output_root=root,
                seed=5,
            )
            run_episode(
                scenario_id="pilot_evidence_brief",
                context_system="raw_transcript",
                policy="none",
                detector="calibrated_ensemble",
                output_root=root,
                seed=5,
            )
            summary = summarize_results(root)
            self.assertEqual(summary["total_runs"], 2)
            self.assertIn("rule_based", summary["by_detector"])
            self.assertIn("calibrated_ensemble", summary["by_detector"])


if __name__ == "__main__":
    unittest.main()
