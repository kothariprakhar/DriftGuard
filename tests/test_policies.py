import unittest

from driftguard.contexts import SUMMARY_ONLY
from driftguard.policies import AnchorRefreshPolicy, LedgerRegenerationPolicy, RollbackPolicy
from driftguard.registry import load_resource_profile, load_scenario
from driftguard.schemas import CheckpointState, DriftAssessment


class PolicyTests(unittest.TestCase):
    def test_anchor_refresh_injects_contract_constraints(self) -> None:
        scenario = load_scenario("pilot_email_injection")
        memory_state = SUMMARY_ONLY.bootstrap(scenario.intent_contract)
        assessment = DriftAssessment(
            overall_score=0.5,
            label_scores={"constraint_drift": 0.5},
            severity="medium",
            reason_codes=["missing_required_constraints"],
            recommended_action="anchor_refresh",
            detector_version="test",
        )
        action = AnchorRefreshPolicy().apply(scenario.intent_contract, memory_state, assessment, [])
        self.assertTrue(action.applied)
        self.assertIn("Do not send external email.", memory_state.anchors)

    def test_rollback_restores_checkpoint_memory(self) -> None:
        scenario = load_scenario("pilot_tool_order")
        profile = load_resource_profile("v1_local_pilot")
        memory_state = SUMMARY_ONLY.bootstrap(scenario.intent_contract)
        SUMMARY_ONLY.observe(memory_state, scenario.events[0], profile)
        checkpoint = CheckpointState(
            checkpoint_id="cp",
            step_id="step-1",
            after_event_id=scenario.events[0].event_id,
            memory_state=memory_state.clone(),
            visible_state=SUMMARY_ONLY.build_visible_state(memory_state, scenario.intent_contract, scenario, profile, scenario.events[0]),
        )
        SUMMARY_ONLY.observe(memory_state, scenario.events[1], profile)
        assessment = DriftAssessment(
            overall_score=0.9,
            label_scores={"memory_drift": 0.9},
            severity="high",
            reason_codes=["missing_required_constraints"],
            recommended_action="rollback",
            detector_version="test",
        )
        action = RollbackPolicy().apply(scenario.intent_contract, memory_state, assessment, [checkpoint])
        self.assertTrue(action.applied)
        self.assertEqual(memory_state.transcript_events, checkpoint.memory_state.transcript_events)

    def test_summary_does_not_overwrite_ledger_truth(self) -> None:
        scenario = load_scenario("pilot_travel_update")
        profile = load_resource_profile("v1_local_pilot")
        memory_state = SUMMARY_ONLY.bootstrap(scenario.intent_contract)
        for event in scenario.events[:2]:
            SUMMARY_ONLY.observe(memory_state, event, profile)
        self.assertIn(
            "Use the latest approved budget, not superseded guidance.",
            memory_state.ledger.find_contents("constraints"),
        )
        self.assertGreaterEqual(len(memory_state.summary_notes), 1)

    def test_ledger_regeneration_preserves_contract_constraints(self) -> None:
        scenario = load_scenario("pilot_email_injection")
        profile = load_resource_profile("v1_local_pilot")
        memory_state = SUMMARY_ONLY.bootstrap(scenario.intent_contract)
        for event in scenario.events[:2]:
            SUMMARY_ONLY.observe(memory_state, event, profile)
        memory_state.ledger.replace_bucket("constraints", [])
        assessment = DriftAssessment(
            overall_score=0.7,
            label_scores={"memory_drift": 0.7},
            severity="medium",
            reason_codes=["summary_omitted_constraints"],
            recommended_action="ledger_regeneration",
            detector_version="test",
        )
        action = LedgerRegenerationPolicy().apply(scenario.intent_contract, memory_state, assessment, [])
        self.assertTrue(action.applied)
        self.assertIn("Do not send external email.", memory_state.ledger.find_contents("constraints"))


if __name__ == "__main__":
    unittest.main()
