import unittest

from driftguard.benchmark_audit import benchmark_stats, lint_benchmark


class BenchmarkAuditTests(unittest.TestCase):
    def test_benchmark_stats_reports_expected_splits(self) -> None:
        stats = benchmark_stats()
        self.assertIn("pilot", stats["split_counts"])
        self.assertIn("dev", stats["split_counts"])
        self.assertIn("validation", stats["split_counts"])
        self.assertIn("test", stats["split_counts"])
        self.assertEqual(stats["split_counts"]["validation"], 8)
        self.assertEqual(stats["split_counts"]["test"], 8)
        self.assertIn("calibration_wave1", stats["annotation_set_stats"])

    def test_lint_benchmark_passes_without_errors(self) -> None:
        report = lint_benchmark()
        self.assertTrue(report["ok"])
        self.assertFalse(report["errors"])


if __name__ == "__main__":
    unittest.main()
