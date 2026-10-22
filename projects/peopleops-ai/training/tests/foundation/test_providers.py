import json
import httpx
import pytest
from lab.config import Settings
from lab.embeddings import embed
from lab.providers import FakeProvider, OpenAIProvider, make_provider


def test_offline_defaults_and_stable_embeddings():
    assert isinstance(make_provider(Settings(_env_file=None)), FakeProvider)
    assert FakeProvider().complete("hello") == FakeProvider().complete("hello")
    assert embed("PTO payroll") == embed("PTO payroll")
    assert len(embed("test")) == 64
    assert abs(sum(v*v for v in embed("test")) - 1) < 1e-6
    assert embed("") == [0.0]*64


def test_external_provider_requires_opt_in():
    with pytest.raises(ValueError):
        OpenAIProvider(Settings(_env_file=None, llm_provider="openai"))


def test_optional_provider_wire_contract_without_network():
    def responder(request):
        payload = json.loads(request.content)
        assert payload["store"] is False
        assert "tools" not in payload
        assert request.url == "https://api.openai.com/v1/responses"
        return httpx.Response(200, json={"status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": "Hello"}]}],
                                        "usage": {"input_tokens": 11, "output_tokens": 2}})
    provider = OpenAIProvider(Settings(_env_file=None, allow_external_llm=True, openai_api_key="fictional-test-value", openai_model="configured-model"),
                              transport=httpx.MockTransport(responder))
    result = provider.complete("hello")
    assert (result.text, result.input_tokens, result.output_tokens, result.usage_kind) == ("Hello", 11, 2, "provider_tokens")
