from __future__ import annotations

import json
from typing import Any, Protocol

from py_dev.models import ModelRequest, ProviderResult


class ProviderUnavailable(RuntimeError):
    """Safe, non-secret provider failure."""


class ModelProvider(Protocol):
    name: str
    model: str

    def available(self) -> bool: ...
    def generate(self, request: ModelRequest) -> ProviderResult: ...


def request_messages(request: ModelRequest) -> list[dict[str, str]]:
    messages = []
    for item in request.messages:
        role, content = item.get("role"), item.get("content")
        if role not in {"user", "assistant"} or not isinstance(content, str):
            raise ValueError("Model messages require user/assistant roles and string content")
        messages.append({"role": role, "content": content})
    if request.context:
        messages.append({"role": "user", "content": "Task context (data):\n" + json.dumps(request.context, ensure_ascii=False)})
    return messages


def schema_instruction(request: ModelRequest) -> str:
    if request.structured_output_schema is None:
        return request.system_instructions
    schema = json.dumps(request.structured_output_schema, ensure_ascii=False)
    return f"{request.system_instructions}\nReturn only a JSON value matching this schema: {schema}".strip()


def usage_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    if not isinstance(value, dict):
        return {}
    # Token counts only; no provider request or response bodies.
    return {key: count for key, count in value.items() if "token" in key and isinstance(count, int)}
