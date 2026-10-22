import json
import httpx
import pytest

from evals.evaluate_routing import evaluate_routing
from evals.evaluate_grounding import citation_valid
from evals.judges import LocalQwenJudge


@pytest.mark.requirement("HR-012")
def test_evaluation_contract():
    report=evaluate_routing()
    assert report["total"]==42 and report["failed_case_ids"]==[]
    assert report["accuracy"]["denominator"]==42
    sources={("DOC","1.0"):{"title":"Title","text":"Approved passage."}}
    assert citation_valid({"document_id":"DOC","version":"1.0","title":"Title","quote":"Approved passage."},sources)
    assert not citation_valid({"document_id":"DOC","version":"1.0","title":"Title","quote":"Invented amount"},sources)


@pytest.mark.requirement("HR-012", "HR-015")
def test_optional_llm_judge_transport():
    def reply(request):
        assert request.url.host=="127.0.0.1"
        body=json.loads(request.content)
        assert "tools" not in body and body["chat_template_kwargs"]["enable_thinking"] is False
        return httpx.Response(200,json={"choices":[{"finish_reason":"stop","message":{"content":'{"supported":true,"explanation":"Matches source."}'}}]})
    assert LocalQwenJudge(transport=httpx.MockTransport(reply)).judge("PTO?","Source passage",["Source passage"]).supported
    with pytest.raises(ValueError):
        LocalQwenJudge("https://example.com/v1")
