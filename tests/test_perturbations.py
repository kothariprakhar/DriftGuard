import tempfile
import unittest
from pathlib import Path

from driftguard.perturbations import evaluate_case, run_suite
from driftguard.registry import load_perturbation_suite


class PerturbationTests(unittest.TestCase):
    def test_suite_loading(self) -> None:
        suite = load_perturbation_suite("pilot_suite")
        self.assertEqual(suite.name, "pilot_suite")
        self.assertGreaterEqual(len(suite.cases), 5)

    def test_validation_suite_loading(self) -> None:
        suite = load_perturbation_suite("validation_suite")
        self.assertEqual(suite.name, "validation_suite")
        self.assertGreaterEqual(len(suite.cases), 8)

    def test_rule_based_constraint_drop_case_passes(self) -> None:
        suite = load_perturbation_suite("pilot_suite")
        case = next(item for item in suite.cases if item.perturbation_id == "drop-constraint-brief-rule")
        result = evaluate_case(case)
        self.assertTrue(result.passed_expectations)
        self.assertGreater(result.perturbed_score, result.clean_score)

    def test_validation_adversarial_case_passes(self) -> None:
        suite = load_perturbation_suite("validation_suite")
        case = next(item for item in suite.cases if item.perturbation_id == "validation-inject-adversarial-exec-rule")
        result = evaluate_case(case)
        self.assertTrue(result.passed_expectations)
        self.assertGreater(result.perturbed_score, result.clean_score)

    def test_suite_runner_writes_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            summary = run_suite(
                "pilot_suite",
                output_root=Path(directory),
                case_filter=[
                    "drop-constraint-brief-rule",
                    "drop-evidence-order-ensemble",
                ],
            )
            self.assertEqual(summary["total_cases"], 2)
            self.assertEqual(summary["passed_cases"], 2)
            self.assertTrue((Path(directory) / "pilot_suite" / "summary.json").exists())
            self.assertTrue((Path(directory) / "pilot_suite" / "results.jsonl").exists())

    def test_validation_suite_runner_writes_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            summary = run_suite(
                "validation_suite",
                output_root=Path(directory),
                case_filter=[
                    "validation-drop-constraint-procurement-rule",
                    "validation-inject-adversarial-exec-rule",
                ],
            )
            self.assertEqual(summary["total_cases"], 2)
            self.assertEqual(summary["passed_cases"], 2)
            self.assertTrue((Path(directory) / "validation_suite" / "summary.json").exists())


if __name__ == "__main__":
    unittest.main()
