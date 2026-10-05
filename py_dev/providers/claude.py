from __future__ import annotations

import importlib.util
import json
import os
from dataclasses import dataclass
from time import monotonic
from typing import Any

from py_dev.models import ModelRequest, ProviderResult, ToolCall

from .base import ProviderUnavailable, request_messages, schema_instruction, usage_dict


@dataclass
class ClaudeProvider:
    model: str
    client: Any = None
    name: str = "claude"

    def available(self) -> bool:
        return bool(self.model and (self.client is not None or (os.getenv("ANTHROPIC_API_KEY") and importlib.util.find_spec("anthropic"))))

    def generate(self, request: ModelRequest) -> ProviderResult:
        if not self.available():
            raise ProviderUnavailable("Claude model, SDK, or API key is unavailable")
        if self.client is None:
            try:
                from anthropic import Anthropic
                self.client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"], timeout=request.timeout_seconds, max_retries=0)
            except (ImportError, KeyError) as exc:
                raise ProviderUnavailable("Anthropic SDK or API key is unavailable") from exc
        start = monotonic()
        try:
            client = self.client.with_options(timeout=request.timeout_seconds) if hasattr(self.client, "with_options") else self.client
            messages = list(request.provider_state) if request.provider_state is not None else request_messages(request)
            if request.tool_outputs:
                messages.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": output.call_id, "content": json.dumps(output.output, allow_nan=False)} for output in request.tool_outputs]})
            arguments = dict(
                model=self.model,
                max_tokens=request.max_output_tokens or 4096,
                system=schema_instruction(request),
                messages=messages,
            )
            if request.tools:
                arguments["tools"] = [{"name": tool["name"], "description": tool.get("description", ""), "input_schema": dict(tool["parameters"])} for tool in request.tools]
            response = client.messages.create(**arguments)
            content = "".join(part.text for part in response.content if getattr(part, "type", None) == "text")
            calls = []
            blocks = []
            for part in response.content:
                block = part.model_dump(mode="json") if hasattr(part, "model_dump") else dict(vars(part))
                blocks.append(block)
                if block.get("type") == "tool_use":
                    if not isinstance(block.get("input"), dict):
                        raise ValueError("Tool arguments must be an object")
                    calls.append(ToolCall(block["id"], block["name"], block["input"]))
            if not calls and not content:
                raise ValueError("empty content")
            return ProviderResult(content, str(getattr(response, "model", None) or self.model), str(getattr(response, "stop_reason", None) or "unknown"), int((monotonic() - start) * 1000), usage_dict(getattr(response, "usage", None)), tuple(calls), [*messages, {"role": "assistant", "content": blocks}])
        except Exception as exc:
            raise ProviderUnavailable("Claude is unavailable or returned an invalid response") from exc
