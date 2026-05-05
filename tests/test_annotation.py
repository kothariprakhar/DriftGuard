import tempfile
import unittest
from pathlib import Path

from driftguard.analysis import summarize_results
from driftguard.annotation import build_annotation_packet
from driftguard.registry import load_annotation_set
from driftguard.runner import run_episode
from driftguard.serialization import load_json


class AnnotationTests(unittest.TestCase):
    def test_annotation_set_loading(self) -> None:
        annotation_set = load_annotation_set("calibration_wave1")
        self.assertEqual(annotation_set.name, "calibration_wave1")
        self.assertEqual(len(annotation_set.cases), 4)
        wave2 = load_annotation_set("calibration_wave2")
        self.assertEqual(wave2.name, "calibration_wave2")
        self.assertEqual(len(wave2.cases), 16)

    def test_build_annotation_packet_writes_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            results_root = root / "results"
            summary_root = results_root / "summary_artifacts"
            output_root = root / "annotation_packet"
            scenarios = [
                "validation_procurement_audit_packet",
                "validation_hr_case_packet",
                "validation_access_review_reactivation",
                "validation_device_wipe_request",
                "validation_policy_supersession_credit",
                "validation_pricing_override_window",
                "validation_exec_message_injection",
                "validation_billing_chat_escalation",
            ]
            scenario_context_pairs = [(scenario_id, context_system) for scenario_id in scenarios for context_system in ("raw_transcript", "ledger_only")]
            for scenario_id, context_system in scenario_context_pairs:
                run_episode(
                    scenario_id=scenario_id,
                    context_system=context_system,
                    policy="none",
                    detector="rule_based",
                    output_root=results_root,
                    seed=31,
                )
            summarize_results(results_root, output_root=summary_root)
            summary = build_annotation_packet(
                output_root=output_root,
                annotation_set_name="calibration_wave2",
                result_roots=[summary_root],
            )
            self.assertEqual(summary["annotation_set"], "calibration_wave2")
            self.assertEqual(summary["case_count"], 16)
            packet = load_json(output_root / "packet.json")
            answer_key = load_json(output_root / "answer_key.json")
            markdown = (output_root / "packet.md").read_text(encoding="utf-8")
            reviewer_instructions = (output_root / "reviewer_instructions.md").read_text(encoding="utf-8")
            self.assertEqual(len(packet["cases"]), 16)
            self.assertEqual(len(answer_key["cases"]), 16)
            self.assertIn("validation_billing_chat_escalation", markdown)
            self.assertIn("wave2-failure-credit-memory", markdown)
            self.assertNotIn("first_drift_step", markdown)
            self.assertNotIn("forbidden_drift_labels", str(packet))
            self.assertNotIn("gold_outcome", str(packet))
            self.assertIn("no_drift", reviewer_instructions)


if __name__ == "__main__":
    unittest.main()
