import tempfile
import unittest
from pathlib import Path

from driftguard.analysis import summarize_results
from driftguard.reporting import build_ablation_report, build_failure_atlas, build_snapshot_report, build_technical_report
from driftguard.runner import run_episode


class ReportingTests(unittest.TestCase):
    def test_build_snapshot_report_writes_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            results_root = root / "results"
            perturbation_root = root / "perturbations" / "suite"
            run_episode(
                scenario_id="pilot_evidence_brief",
                context_system="ledger_only",
                policy="none",
                detector="rule_based",
                output_root=results_root,
            )
            summarize_results(results_root, output_root=results_root / "summary_artifacts")
            perturbation_root.mkdir(parents=True, exist_ok=True)
            (perturbation_root / "summary.json").write_text(
                '{"suite_name":"suite","total_cases":2,"passed_cases":2,"pass_rate":1.0,"mean_score_delta":0.5}\n',
                encoding="utf-8",
            )
            output_path = root / "snapshot.md"
            build_snapshot_report(
                output_path,
                result_roots=[results_root / "summary_artifacts"],
                perturbation_roots=[perturbation_root],
            )
            text = output_path.read_text(encoding="utf-8")
            self.assertIn("# DriftGuard Benchmark Snapshot", text)
            self.assertIn("## Benchmark Coverage", text)
            self.assertIn("## Result Summaries", text)
            self.assertIn("## Perturbation Suites", text)

    def test_build_technical_report_writes_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            results_root = root / "results"
            summary_root = results_root / "summary_artifacts"
            perturbation_root = root / "perturbations" / "suite"
            run_episode(
                scenario_id="pilot_evidence_brief",
                context_system="ledger_only",
                policy="none",
                detector="rule_based",
                output_root=results_root,
            )
            run_episode(
                scenario_id="pilot_evidence_brief",
                context_system="raw_transcript",
                policy="none",
                detector="rule_based",
                output_root=results_root,
            )
            summarize_results(results_root, output_root=summary_root)
            perturbation_root.mkdir(parents=True, exist_ok=True)
            (perturbation_root / "summary.json").write_text(
                '{"suite_name":"suite","total_cases":2,"passed_cases":2,"pass_rate":1.0,"mean_score_delta":0.5}\n',
                encoding="utf-8",
            )
            output_path = root / "technical.md"
            build_technical_report(
                output_path,
                result_root=summary_root,
                perturbation_root=perturbation_root,
                manifest_name="pilot_baselines",
            )
            text = output_path.read_text(encoding="utf-8")
            self.assertIn("# DriftGuard Technical Report", text)
            self.assertIn("## Main Result", text)
            self.assertIn("## Perturbation Regression", text)
            self.assertIn("## Representative Deterministic Failures", text)

    def test_build_failure_atlas_writes_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            results_root = root / "results"
            summary_root = results_root / "summary_artifacts"
            run_episode(
                scenario_id="pilot_evidence_brief",
                context_system="raw_transcript",
                policy="none",
                detector="rule_based",
                output_root=results_root,
            )
            summarize_results(results_root, output_root=summary_root)
            output_path = root / "failure_atlas.md"
            build_failure_atlas(output_path, result_root=summary_root)
            text = output_path.read_text(encoding="utf-8")
            self.assertIn("# DriftGuard Failure Atlas", text)
            self.assertIn("## Representative Failures", text)
            self.assertIn("pilot_evidence_brief", text)

    def test_build_ablation_report_writes_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            results_root = root / "results"
            summary_root = results_root / "summary_artifacts"
            run_episode(
                scenario_id="pilot_evidence_brief",
                context_system="ledger_only",
                policy="none",
                detector="rule_based",
                output_root=results_root,
            )
            run_episode(
                scenario_id="pilot_evidence_brief",
                context_system="raw_transcript",
                policy="anchor_refresh",
                detector="rule_based",
                output_root=results_root,
            )
            run_episode(
                scenario_id="pilot_evidence_brief",
                context_system="raw_transcript",
                policy="anchor_refresh",
                detector="calibrated_ensemble",
                output_root=results_root,
            )
            summarize_results(results_root, output_root=summary_root)
            output_path = root / "ablation.md"
            build_ablation_report(output_path, result_root=summary_root, manifest_name="pilot_baselines")
            text = output_path.read_text(encoding="utf-8")
            self.assertIn("# DriftGuard Ablation Report", text)
            self.assertIn("## Context Ablation", text)
            self.assertIn("## Policy Ablation", text)
            self.assertIn("## Top Configurations", text)
            self.assertIn("## Weak-Context Policy Comparisons", text)
            self.assertIn("## Detector Comparisons", text)


if __name__ == "__main__":
    unittest.main()
