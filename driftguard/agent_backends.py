"""Agent backend implementations for scripted and live-model execution."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List
from urllib import error, request

from driftguard.agent import choose_option as choose_scripted_option
from driftguard.prompting import build_agent_prompt
from driftguard.schemas import (
    DecisionOption,
    MemoryState,
    PromptPack,
    ResourceProfile,
    ScenarioEvent,
    ScenarioSpec,
    VisibleState,
)


@dataclass
class AgentDecision:
    option: DecisionOption
    reason_codes: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


def _decision_options(event: ScenarioEvent) -> Dict[str, DecisionOption]:
    return {
        option.option_id: option
        for option in (DecisionOption.from_dict(item) for item in event.payload.get("options", []))
    }


def _extract_json_object(text: str) -> Dict[str, Any]:
    candidate = text.strip()
    if not candidate:
        raise ValueError("backend returned an empty response")
    try:
        parsed = json.loads(candidate)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("backend response did not contain a JSON object")
    parsed = json.loads(candidate[start : end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("backend JSON response must be an object")
    return parsed


def _normalize_reason_codes(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _extract_usage(provider: str, raw_usage: Any) -> Dict[str, int]:
    if not isinstance(raw_usage, dict):
        return {}
    if provider == "openai_compatible":
        input_tokens = int(raw_usage.get("prompt_tokens", 0) or 0)
        output_tokens = int(raw_usage.get("completion_tokens", 0) or 0)
        total_tokens = int(raw_usage.get("total_tokens", input_tokens + output_tokens) or 0)
        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
        }
    if provider == "anthropic_messages":
        input_tokens = int(raw_usage.get("input_tokens", 0) or 0)
        output_tokens = int(raw_usage.get("output_tokens", 0) or 0)
        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
        }
    return {}


class AgentBackend:
    name = "base"
    backend_kind = "base"

    def describe(self) -> Dict[str, Any]:
        return {"agent_backend": self.name, "backend_kind": self.backend_kind}

    def choose_option(
        self,
        *,
        scenario: ScenarioSpec,
        event: ScenarioEvent,
        visible_state: VisibleState,
        memory_state: MemoryState,
        prompt_pack: PromptPack,
        resource_profile: ResourceProfile,
        seed: int,
    ) -> AgentDecision:
        raise NotImplementedError


class ScriptedLocalBackend(AgentBackend):
    name = "scripted_local"
    backend_kind = "scripted"

    def choose_option(
        self,
        *,
        scenario: ScenarioSpec,
        event: ScenarioEvent,
        visible_state: VisibleState,
        memory_state: MemoryState,
        prompt_pack: PromptPack,
        resource_profile: ResourceProfile,
        seed: int,
    ) -> AgentDecision:
        option, reasons = choose_scripted_option(event, visible_state)
        return AgentDecision(
            option=option,
            reason_codes=reasons,
            metadata={
                "backend_kind": self.backend_kind,
                "prompt_pack_version": prompt_pack.version,
                "resource_profile": resource_profile.version,
            },
        )


class _HttpJsonBackend(AgentBackend):
    timeout_seconds = 60

    def _request_json(self, *, url: str, headers: Dict[str, str], payload: Dict[str, Any]) -> Dict[str, Any]:
        encoded = json.dumps(payload).encode("utf-8")
        http_request = request.Request(url=url, data=encoded, headers=headers, method="POST")
        try:
            with request.urlopen(http_request, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"{self.name} HTTP error {exc.code}: {detail}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"{self.name} request failed: {exc.reason}") from exc
        data = json.loads(body)
        if not isinstance(data, dict):
            raise RuntimeError(f"{self.name} returned a non-object response")
        return data

    def _finish_decision(
        self,
        *,
        scenario: ScenarioSpec,
        event: ScenarioEvent,
        visible_state: VisibleState,
        memory_state: MemoryState,
        prompt_pack: PromptPack,
        resource_profile: ResourceProfile,
        seed: int,
        provider: str,
        model: str,
        response_id: str,
        raw_text: str,
        raw_usage: Any,
    ) -> AgentDecision:
        payload = _extract_json_object(raw_text)
        options = _decision_options(event)
        option_id = str(payload.get("option_id", "")).strip()
        if option_id not in options:
            raise ValueError(f"{self.name} returned unknown option_id {option_id!r} for event {event.event_id}")
        usage = _extract_usage(provider, raw_usage)
        return AgentDecision(
            option=options[option_id],
            reason_codes=_normalize_reason_codes(payload.get("reason_codes", [])),
            metadata={
                "backend_kind": self.backend_kind,
                "provider": provider,
                "model": model,
                "response_id": response_id,
                "prompt_pack_version": prompt_pack.version,
                "resource_profile": resource_profile.version,
                "response_excerpt": raw_text.strip()[:400],
                "notes": str(payload.get("notes", "")).strip(),
                "usage": usage,
            },
        )


class OpenAICompatibleBackend(_HttpJsonBackend):
    name = "openai_compatible"
    backend_kind = "live"

    def _config(self) -> Dict[str, str]:
        api_key = os.environ.get("DRIFTGUARD_OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("openai_compatible backend requires DRIFTGUARD_OPENAI_API_KEY or OPENAI_API_KEY")
        base_url = (os.environ.get("DRIFTGUARD_OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
        model = os.environ.get("DRIFTGUARD_OPENAI_MODEL") or os.environ.get("OPENAI_MODEL") or "gpt-4.1-mini"
        return {"api_key": api_key, "base_url": base_url, "model": model}

    def choose_option(
        self,
        *,
        scenario: ScenarioSpec,
        event: ScenarioEvent,
        visible_state: VisibleState,
        memory_state: MemoryState,
        prompt_pack: PromptPack,
        resource_profile: ResourceProfile,
        seed: int,
    ) -> AgentDecision:
        config = self._config()
        prompt = build_agent_prompt(prompt_pack, scenario, event, visible_state, memory_state, resource_profile)
        response = self._request_json(
            url=f"{config['base_url']}/chat/completions",
            headers={
                "Authorization": f"Bearer {config['api_key']}",
                "Content-Type": "application/json",
            },
            payload={
                "model": config["model"],
                "temperature": 0,
                "messages": [
                    {"role": "system", "content": prompt["system"]},
                    {"role": "user", "content": prompt["user"]},
                ],
            },
        )
        choices = response.get("choices", [])
        if not choices:
            raise RuntimeError("openai_compatible backend returned no choices")
        message = choices[0].get("message", {})
        content = message.get("content", "")
        if isinstance(content, list):
            raw_text = "\n".join(str(item.get("text", "")) for item in content if isinstance(item, dict))
        else:
            raw_text = str(content)
        return self._finish_decision(
            scenario=scenario,
            event=event,
            visible_state=visible_state,
            memory_state=memory_state,
            prompt_pack=prompt_pack,
            resource_profile=resource_profile,
            seed=seed,
            provider="openai_compatible",
            model=config["model"],
            response_id=str(response.get("id", "")),
            raw_text=raw_text,
            raw_usage=response.get("usage", {}),
        )


class AnthropicMessagesBackend(_HttpJsonBackend):
    name = "anthropic_messages"
    backend_kind = "live"

    def _config(self) -> Dict[str, str]:
        api_key = os.environ.get("DRIFTGUARD_ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "anthropic_messages backend requires DRIFTGUARD_ANTHROPIC_API_KEY or ANTHROPIC_API_KEY"
            )
        base_url = (os.environ.get("DRIFTGUARD_ANTHROPIC_BASE_URL") or "https://api.anthropic.com").rstrip("/")
        model = (
            os.environ.get("DRIFTGUARD_ANTHROPIC_MODEL")
            or os.environ.get("ANTHROPIC_MODEL")
            or "claude-3-5-haiku-latest"
        )
        return {"api_key": api_key, "base_url": base_url, "model": model}

    def choose_option(
        self,
        *,
        scenario: ScenarioSpec,
        event: ScenarioEvent,
        visible_state: VisibleState,
        memory_state: MemoryState,
        prompt_pack: PromptPack,
        resource_profile: ResourceProfile,
        seed: int,
    ) -> AgentDecision:
        config = self._config()
        prompt = build_agent_prompt(prompt_pack, scenario, event, visible_state, memory_state, resource_profile)
        response = self._request_json(
            url=f"{config['base_url']}/v1/messages",
            headers={
                "content-type": "application/json",
                "x-api-key": config["api_key"],
                "anthropic-version": "2023-06-01",
            },
            payload={
                "model": config["model"],
                "max_tokens": 300,
                "temperature": 0,
                "system": prompt["system"],
                "messages": [{"role": "user", "content": prompt["user"]}],
            },
        )
        blocks = response.get("content", [])
        raw_text = "\n".join(str(item.get("text", "")) for item in blocks if isinstance(item, dict))
        return self._finish_decision(
            scenario=scenario,
            event=event,
            visible_state=visible_state,
            memory_state=memory_state,
            prompt_pack=prompt_pack,
            resource_profile=resource_profile,
            seed=seed,
            provider="anthropic_messages",
            model=config["model"],
            response_id=str(response.get("id", "")),
            raw_text=raw_text,
            raw_usage=response.get("usage", {}),
        )


ALL_AGENT_BACKENDS = {
    backend.name: backend
    for backend in (
        ScriptedLocalBackend(),
        OpenAICompatibleBackend(),
        AnthropicMessagesBackend(),
    )
}
