import unittest

from driftguard.ledger import bootstrap_ledger, regenerate_ledger_from_transcript
from driftguard.registry import load_scenario


class LedgerTests(unittest.TestCase):
    def test_bootstrap_ledger_contains_contract_constraints(self) -> None:
        scenario = load_scenario("pilot_evidence_brief")
        ledger = bootstrap_ledger(scenario.intent_contract)
        constraints = ledger.find_contents("constraints")
        self.assertIn("Use only internal operations evidence.", constraints)
        self.assertEqual(ledger.active_subgoal, scenario.intent_contract.success_criteria[0])

    def test_regeneration_preserves_constraints_and_decisions(self) -> None:
        scenario = load_scenario("pilot_tool_order")
        transcript = [
            scenario.events[0].to_dict(),
            scenario.events[1].to_dict(),
            {
                "event_id": "order-decision::decision",
                "kind": "decision_outcome",
                "text": "Do not cancel; offer the return flow instead.",
                "salience": 10,
                "payload": {
                    "option_id": "offer_return",
                    "label": "Do not cancel; offer the return flow instead.",
                    "ledger_updates": {
                        "plan_steps": [
                            "Offer the return path for shipped order 714."
                        ]
                    },
                    "evidence_to_accept": [
                        "fulfillment_order_714"
                    ]
                }
            }
        ]
        ledger = regenerate_ledger_from_transcript(scenario.intent_contract, transcript)
        self.assertIn("Never cancel shipped orders.", ledger.find_contents("constraints"))
        self.assertIn("Do not cancel; offer the return flow instead.", ledger.find_contents("decisions"))
        self.assertIn("fulfillment_order_714", ledger.find_contents("accepted_evidence"))


if __name__ == "__main__":
    unittest.main()
