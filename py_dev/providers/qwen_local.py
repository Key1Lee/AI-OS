from __future__ import annotations

import ipaddress
import json
from dataclasses import dataclass
from time import monotonic
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from py_dev.models import ModelRequest, ProviderResult

from .base import ProviderUnavailable, request_messages, schema_instruction


def _local_base_url(value: str) -> str:
    parsed = urlsplit(value)
    host = parsed.hostname or ""
    try:
        loopback = ipaddress.ip_address(host).is_loopback
    except ValueError:
        loopback = host == "localhost"
    if parsed.scheme != "http" or not loopback or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("Qwen base URL must be a local HTTP loopback endpoint")
    if parsed.path not in {"", "/", "/v1", "/v1/"}:
        raise ValueError("Qwen base URL must end at the local /v1 API")
    return value.rstrip("/") + ("" if parsed.path.rstrip("/") == "/v1" else "/v1")


@dataclass
class QwenLocalProvider:
    model: str
    base_url: str
    name: str = "qwen_local"

    def __post_init__(self) -> None:
        self.base_url = _local_base_url(self.base_url)

    def available(self) -> bool:
        return bool(self.model)

    def generate(self, request: ModelRequest) -> ProviderResult:
        if not self.available():
            raise ProviderUnavailable("Qwen model is not configured")
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": schema_instruction(request)}, *request_messages(request)],
            "temperature": 0,
            "stream": False,
        }
        if request.max_output_tokens is not None:
            payload["max_tokens"] = request.max_output_tokens
        if request.thinking_enabled is not None:
            payload["chat_template_kwargs"] = {"enable_thinking": request.thinking_enabled}
        if request.reasoning_budget_tokens is not None:
            payload["reasoning_budget_tokens"] = request.reasoning_budget_tokens
        if request.structured_output_schema is not None:
            payload["response_format"] = {"type": "json_object", "schema": dict(request.structured_output_schema)}
        wire = Request(
            self.base_url + "/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        start = monotonic()
        try:
            with urlopen(wire, timeout=request.timeout_seconds) as response:
                result = json.load(response)
            choice = result["choices"][0]
            content = choice["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise ValueError("empty content")
            usage = result.get("usage") or {}
            counts = {k: v for k, v in usage.items() if "token" in k and isinstance(v, int)}
            return ProviderResult(content, str(result.get("model") or self.model), str(choice.get("finish_reason") or "unknown"), int((monotonic() - start) * 1000), counts)
        except (HTTPError, URLError, TimeoutError, OSError, ValueError, KeyError, IndexError, TypeError) as exc:
            raise ProviderUnavailable("Qwen local runtime is unavailable or returned an invalid response") from exc
