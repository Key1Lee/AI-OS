from __future__ import annotations

import importlib.util
import os
from dataclasses import dataclass
from time import monotonic
from typing import Any

from py_dev.models import ModelRequest, ProviderResult

from .base import ProviderUnavailable, request_messages, schema_instruction, usage_dict


@dataclass
class OpenAIProvider:
    model: str
    client: Any = None
    name: str = "openai"

    def available(self) -> bool:
        return bool(self.model and (self.client is not None or (os.getenv("OPENAI_API_KEY") and importlib.util.find_spec("openai"))))

    def generate(self, request: ModelRequest) -> ProviderResult:
        if not self.available():
            raise ProviderUnavailable("OpenAI model, SDK, or API key is unavailable")
        if self.client is None:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=os.environ["OPENAI_API_KEY"], timeout=request.timeout_seconds, max_retries=0)
            except (ImportError, KeyError) as exc:
                raise ProviderUnavailable("OpenAI SDK or API key is unavailable") from exc
        arguments: dict[str, Any] = {
            "model": self.model,
            "instructions": schema_instruction(request),
            "input": request_messages(request),
            "store": False,
        }
        if request.reasoning_level:
            arguments["reasoning"] = {"effort": request.reasoning_level}
        if request.max_output_tokens is not None:
            arguments["max_output_tokens"] = request.max_output_tokens
        if request.structured_output_schema is not None:
            # JSON mode accepts the shared schema subset across configured models;
            # router validation remains authoritative.
            arguments["text"] = {"format": {"type": "json_object"}}
        start = monotonic()
        try:
            client = self.client.with_options(timeout=request.timeout_seconds) if hasattr(self.client, "with_options") else self.client
            response = client.responses.create(**arguments)
            content = response.output_text
            if not isinstance(content, str) or not content.strip():
                raise ValueError("empty content")
            return ProviderResult(content, str(getattr(response, "model", None) or self.model), str(getattr(response, "status", None) or "unknown"), int((monotonic() - start) * 1000), usage_dict(getattr(response, "usage", None)))
        except Exception as exc:
            raise ProviderUnavailable("OpenAI is unavailable or returned an invalid response") from exc
