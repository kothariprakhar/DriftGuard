import tempfile
import unittest
from pathlib import Path

from driftguard.graders import grade_checkpoint
from driftguard.registry import load_scenario
from driftguard.runner import run_episode
from driftguard.traces import replay_trace


class GraderTests(unittest.TestCase):
    def test_ledger_only_checkpoint_has_provenance(self) -> None:
        scenario = load_scenario("pilot_evidence_brief")
        with tempfile.TemporaryDirectory() as directory:
            result = run_episode(
                scenario_id="pilot_evidence_brief",
                context_system="ledger_only",
                policy="none",
                detector="rule_based",
                output_root=Path(directory),
            )
            _, records, checkpoints = replay_trace(Path(result.trace_path))
            final_checkpoint = checkpoints[-1]
            final_gold = scenario.gold_checkpoints[-1]
            record = next(item for item in records if item.event_id == final_checkpoint.after_event_id)
            graded = grade_checkpoint(final_checkpoint, final_gold, record)
            self.assertEqual(graded["provenance_adherence"], 1.0)
            self.assertEqual(graded["ledger_adherence"], 1.0)
            self.assertFalse(graded["missing_provenance_links"])

    def test_wrong_decision_triggers_forbidden_drift_violation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = run_episode(
                scenario_id="pilot_evidence_brief",
                context_system="raw_transcript",
                policy="none",
                detector="rule_based",
                output_root=Path(directory),
            )
            self.assertGreater(result.metrics["forbidden_drift_violation_rate"], 0.0)

    def test_ledger_only_scores_above_raw_transcript_on_checkpoint_adherence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            raw = run_episode(
                scenario_id="pilot_evidence_brief",
                context_system="raw_transcript",
                policy="none",
                detector="rule_based",
                output_root=Path(directory),
            )
            ledger = run_episode(
                scenario_id="pilot_evidence_brief",
                context_system="ledger_only",
                policy="none",
                detector="rule_based",
                output_root=Path(directory),
            )
            self.assertGreater(
                ledger.metrics["mean_checkpoint_adherence"],
                raw.metrics["mean_checkpoint_adherence"],
            )


if __name__ == "__main__":
    unittest.main()
