import tempfile
import unittest
from pathlib import Path

from driftguard.detector_training import fit_detector_profile
from driftguard.serialization import load_json


class DetectorTrainingTests(unittest.TestCase):
    def test_fit_detector_profile_writes_expected_fields(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "calibrated_ensemble.json"
            profile = fit_detector_profile(
                output_path=output_path,
                splits=["pilot"],
                perturbation_suites=["pilot_suite"],
            )
            loaded = load_json(output_path)
            self.assertEqual(profile["version"], "calibrated_ensemble/v2")
            self.assertEqual(loaded["version"], "calibrated_ensemble/v2")
            self.assertIn("weights", loaded)
            self.assertIn("training_metrics", loaded)
            self.assertGreater(loaded["training_metrics"]["example_count"], 0)
            self.assertIn("rule_based", loaded["weights"])


if __name__ == "__main__":
    unittest.main()
