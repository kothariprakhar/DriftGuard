import csv
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from driftguard.agent_backends import ALL_AGENT_BACKENDS
from driftguard.analysis import compare_agent_backends, compare_contexts
from driftguard.contexts import ALL_CONTEXT_SYSTEMS
from driftguard.prompting import build_agent_prompt, build_decision_packet
from driftguard.registry import load_prompt_pack, load_resource_profile, load_scenario


class _FakeHttpResponse:
    def __init__(self, payload):
        self.payload = payload

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


def _prepare_decision_inputs(scenario_id: str = "pilot_evidence_brief", context_name: str = "ledger_only"):
    scenario = load_scenario(scenario_id)
    profile = load_resource_profile(scenario.resource_profile)
    prompt_pack = load_prompt_pack(scenario.prompt_pack_version)
    context = ALL_CONTEXT_SYSTEMS[context_name]
    memory_state = context.bootstrap(scenario.intent_contract)
    decision_event = None
    for event in scenario.events:
        if event.kind == "decision":
            decision_event = event
            break
        context.observe(memory_state, event, profile)
    assert decision_event is not None
    visible_state = context.build_visible_state(
        memory_state=memory_state,
        contract=scenario.intent_contract,
        scenario=scenario,
        profile=profile,
        current_event=decision_event,
    )
    return scenario, decision_event, visible_state, memory_state, prompt_pack, profile


class AgentBackendTests(unittest.TestCase):
    def test_decision_packet_and_prompt_include_expected_fields(self) -> None:
        scenario, event, visible_state, memory_state, prompt_pack, profile = _prepare_decision_inputs()
        packet = build_decision_packet(scenario, event, visible_state, memory_state, profile)
        prompt = build_agent_prompt(prompt_pack, scenario, event, visible_state, memory_state, profile)
        self.assertEqual(packet["scenario_id"], scenario.scenario_id)
        self.assertIn("decision_options", packet)
        self.assertIn("intent_contract", packet)
        self.assertIn("Return only a JSON object", prompt["user"])
        self.assertIn(scenario.intent_contract.task_statement, prompt["user"])

    def test_openai_compatible_backend_parses_structured_choice(self) -> None:
        scenario, event, visible_state, memory_state, prompt_pack, profile = _prepare_decision_inputs()
        backend = ALL_AGENT_BACKENDS["openai_compatible"]
        correct_option_id = event.payload["correct_option_id"]
        fake_payload = {
            "id": "chatcmpl-test",
            "usage": {
                "prompt_tokens": 123,
                "completion_tokens": 17,
                "total_tokens": 140,
            },
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "option_id": correct_option_id,
                                "reason_codes": ["contract_aligned", "evidence_visible"],
                                "notes": "Uses the visible constraint and evidence.",
                            }
                        )
                    }
                }
            ],
        }
        env = {
            "DRIFTGUARD_OPENAI_API_KEY": "test-key",
            "DRIFTGUARD_OPENAI_MODEL": "gpt-test-mini",
            "DRIFTGUARD_OPENAI_BASE_URL": "https://example.test/v1",
        }
        with patch.dict(os.environ, env, clear=False):
            with patch("driftguard.agent_backends.request.urlopen", return_value=_FakeHttpResponse(fake_payload)):
                decision = backend.choose_option(
                    scenario=scenario,
                    event=event,
                    visible_state=visible_state,
                    memory_state=memory_state,
                    prompt_pack=prompt_pack,
                    resource_profile=profile,
                    seed=0,
                )
        self.assertEqual(decision.option.option_id, correct_option_id)
        self.assertIn("contract_aligned", decision.reason_codes)
        self.assertEqual(decision.metadata["provider"], "openai_compatible")
        self.assertEqual(decision.metadata["model"], "gpt-test-mini")
        self.assertEqual(decision.metadata["usage"]["total_tokens"], 140)

    def test_anthropic_backend_parses_content_blocks(self) -> None:
        scenario, event, visible_state, memory_state, prompt_pack, profile = _prepare_decision_inputs()
        backend = ALL_AGENT_BACKENDS["anthropic_messages"]
        correct_option_id = event.payload["correct_option_id"]
        fake_payload = {
            "id": "msg_test",
            "usage": {
                "input_tokens": 88,
                "output_tokens": 22,
            },
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "option_id": correct_option_id,
                            "reason_codes": ["constraint_preserved"],
                            "notes": "Avoids the drift-inducing option.",
                        }
                    ),
                }
            ],
        }
        env = {
            "DRIFTGUARD_ANTHROPIC_API_KEY": "test-key",
            "DRIFTGUARD_ANTHROPIC_MODEL": "claude-test-haiku",
            "DRIFTGUARD_ANTHROPIC_BASE_URL": "https://example.anthropic.test",
        }
        with patch.dict(os.environ, env, clear=False):
            with patch("driftguard.agent_backends.request.urlopen", return_value=_FakeHttpResponse(fake_payload)):
                decision = backend.choose_option(
                    scenario=scenario,
                    event=event,
                    visible_state=visible_state,
                    memory_state=memory_state,
                    prompt_pack=prompt_pack,
                    resource_profile=profile,
                    seed=0,
                )
        self.assertEqual(decision.option.option_id, correct_option_id)
        self.assertEqual(decision.metadata["provider"], "anthropic_messages")
        self.assertEqual(decision.metadata["model"], "claude-test-haiku")
        self.assertEqual(decision.metadata["usage"]["total_tokens"], 110)

    def test_compare_contexts_does_not_pair_across_backends(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runs_path = root / "runs.csv"
            with runs_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "scenario_id",
                        "family",
                        "split",
                        "context_system",
                        "policy",
                        "detector",
                        "agent_backend",
                        "prompt_pack_version",
                        "resource_profile",
                        "seed",
                        "success",
                        "score",
                        "first_drift_step",
                        "mean_checkpoint_visible_adherence",
                        "mean_checkpoint_ledger_adherence",
                        "mean_checkpoint_provenance_adherence",
                        "forbidden_drift_violation_rate",
                        "trace_path",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "scenario_id": "pilot_evidence_brief",
                        "family": "evidence_synthesis",
                        "split": "pilot",
                        "context_system": "ledger_only",
                        "policy": "none",
                        "detector": "rule_based",
                        "agent_backend": "scripted_local",
                        "prompt_pack_version": "v1",
                        "resource_profile": "v1_local_pilot",
                        "seed": 7,
                        "success": True,
                        "score": 1.0,
                        "first_drift_step": "",
                        "mean_checkpoint_visible_adherence": 1.0,
                        "mean_checkpoint_ledger_adherence": 1.0,
                        "mean_checkpoint_provenance_adherence": 1.0,
                        "forbidden_drift_violation_rate": 0.0,
                        "trace_path": "trace-a.jsonl",
                    }
                )
                writer.writerow(
                    {
                        "scenario_id": "pilot_evidence_brief",
                        "family": "evidence_synthesis",
                        "split": "pilot",
                        "context_system": "raw_transcript",
                        "policy": "none",
                        "detector": "rule_based",
                        "agent_backend": "openai_compatible",
                        "prompt_pack_version": "v1",
                        "resource_profile": "v1_local_pilot",
                        "seed": 7,
                        "success": False,
                        "score": 0.0,
                        "first_drift_step": "step-1",
                        "mean_checkpoint_visible_adherence": 0.0,
                        "mean_checkpoint_ledger_adherence": 0.0,
                        "mean_checkpoint_provenance_adherence": 0.0,
                        "forbidden_drift_violation_rate": 1.0,
                        "trace_path": "trace-b.jsonl",
                    }
                )
            comparison = compare_contexts(root, "ledger_only", ["raw_transcript"])
            self.assertEqual(comparison["comparisons"]["raw_transcript"]["paired_runs"], 0)

    def test_compare_agent_backends_pairs_matching_runs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runs_path = root / "runs.csv"
            with runs_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "scenario_id",
                        "family",
                        "split",
                        "context_system",
                        "policy",
                        "detector",
                        "agent_backend",
                        "prompt_pack_version",
                        "resource_profile",
                        "seed",
                        "success",
                        "score",
                        "first_drift_step",
                        "mean_checkpoint_visible_adherence",
                        "mean_checkpoint_ledger_adherence",
                        "mean_checkpoint_provenance_adherence",
                        "forbidden_drift_violation_rate",
                        "trace_path",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "scenario_id": "pilot_evidence_brief",
                        "family": "evidence_synthesis",
                        "split": "pilot",
                        "context_system": "ledger_only",
                        "policy": "none",
                        "detector": "rule_based",
                        "agent_backend": "scripted_local",
                        "prompt_pack_version": "v1",
                        "resource_profile": "v1_local_pilot",
                        "seed": 7,
                        "success": True,
                        "score": 1.0,
                        "first_drift_step": "",
                        "mean_checkpoint_visible_adherence": 1.0,
                        "mean_checkpoint_ledger_adherence": 1.0,
                        "mean_checkpoint_provenance_adherence": 1.0,
                        "forbidden_drift_violation_rate": 0.0,
                        "trace_path": "trace-scripted.jsonl",
                    }
                )
                writer.writerow(
                    {
                        "scenario_id": "pilot_evidence_brief",
                        "family": "evidence_synthesis",
                        "split": "pilot",
                        "context_system": "ledger_only",
                        "policy": "none",
                        "detector": "rule_based",
                        "agent_backend": "openai_compatible",
                        "prompt_pack_version": "v1",
                        "resource_profile": "v1_local_pilot",
                        "seed": 7,
                        "success": False,
                        "score": 0.0,
                        "first_drift_step": "step-4",
                        "mean_checkpoint_visible_adherence": 0.0,
                        "mean_checkpoint_ledger_adherence": 0.0,
                        "mean_checkpoint_provenance_adherence": 0.0,
                        "forbidden_drift_violation_rate": 1.0,
                        "trace_path": "trace-openai.jsonl",
                    }
                )
            comparison = compare_agent_backends(root, "scripted_local", ["openai_compatible"])
            self.assertEqual(comparison["comparisons"]["openai_compatible"]["paired_runs"], 1)
            self.assertGreater(comparison["comparisons"]["openai_compatible"]["success_delta"], 0.0)


if __name__ == "__main__":
    unittest.main()
