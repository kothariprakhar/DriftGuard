import csv
import tempfile
import unittest
from pathlib import Path

from driftguard.analysis import summarize_results
from driftguard.annotation import build_annotation_packet
from driftguard.calibration import compute_annotation_agreement, score_annotation_response
from driftguard.runner import run_episode


class CalibrationTests(unittest.TestCase):
    def test_compute_annotation_agreement_and_scoring(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            results_root = root / "results"
            summary_root = results_root / "summary_artifacts"
            packet_root = root / "annotation_packet"
            scenarios = [
                "validation_procurement_audit_packet",
                "validation_access_review_reactivation",
                "validation_policy_supersession_credit",
                "validation_billing_chat_escalation",
            ]
            for scenario_id in scenarios:
                run_episode(
                    scenario_id=scenario_id,
                    context_system="raw_transcript",
                    policy="none",
                    detector="rule_based",
                    output_root=results_root,
                    seed=31,
                )
            summarize_results(results_root, output_root=summary_root)
            build_annotation_packet(
                output_root=packet_root,
                annotation_set_name="calibration_wave1",
                result_roots=[summary_root],
            )

            reviewer_a = packet_root / "reviewer_a.csv"
            reviewer_b = packet_root / "reviewer_b.csv"
            rows = []
            with (packet_root / "response_template.csv").open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    rows.append(dict(row))

            answer_rows = {
                "calibration-evidence-drift": ("step-4", "evidence_drift"),
                "calibration-constraint-drift": ("step-4", "constraint_drift"),
                "calibration-memory-drift": ("step-3", "memory_drift"),
                "calibration-goal-drift": ("step-3", "goal_drift"),
            }
            for row in rows:
                drift_step, drift_label = answer_rows[row["example_id"]]
                row["earliest_visible_drift_step"] = drift_step
                row["primary_drift_label"] = drift_label
                row["severity"] = "high"
                row["recoverable"] = "True"
                row["final_success"] = "False"

            fieldnames = list(rows[0].keys())
            with reviewer_a.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)

            reviewer_b_rows = [dict(row) for row in rows]
            for row in reviewer_b_rows:
                if row["example_id"] == "calibration-evidence-drift":
                    row["primary_drift_label"] = "constraint_drift"
                    break
            with reviewer_b.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(reviewer_b_rows)

            agreement = compute_annotation_agreement([reviewer_a, reviewer_b])
            self.assertEqual(agreement["shared_example_count"], 4)
            self.assertLess(agreement["field_metrics"]["primary_drift_label"]["exact_match_rate"], 1.0)
            self.assertIn("confusion_matrix", agreement["field_metrics"]["primary_drift_label"])
            self.assertIn("weighted_kappa", agreement["field_metrics"]["severity"])
            self.assertIn("within_one_step_rate", agreement["field_metrics"]["earliest_visible_drift_step"])
            self.assertEqual(agreement["overall"]["disagreement_case_count"], 1)
            self.assertEqual(len(agreement["disagreements"]), 1)

            score = score_annotation_response(reviewer_a, packet_root / "answer_key.json")
            self.assertEqual(score["scored_example_count"], 4)
            self.assertEqual(score["field_accuracy"]["primary_drift_label"], 1.0)
            self.assertEqual(score["field_accuracy"]["severity"], 1.0)
            self.assertIn("earliest_visible_drift_step", score["supplemental_metrics"])
            self.assertIn("severity", score["supplemental_metrics"])


if __name__ == "__main__":
    unittest.main()
