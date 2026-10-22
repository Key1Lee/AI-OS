from conftest import headers, ingest_files


def test_pto_vertical_slice(client):
    first = ingest_files(client, "pto-v1.md", "pto-v2.md")
    assert all(d["status"] == "created" for d in first["documents"])
    replay = ingest_files(client, "pto-v1.md", "pto-v2.md")
    assert all(d["status"] == "unchanged" for d in replay["documents"])
    response = client.post("/ask", headers=headers(), json={"question": "How do I request PTO?"})
    assert response.status_code == 200
    answer = response.json()
    assert answer["status"] == "answered", answer
    assert "five business days" in answer["answer"]
    assert "old paper form" not in answer["answer"]
    assert {c["section"] for c in answer["citations"]} == {"PTO / Requests"}
    assert all(c["policy_id"] == "pto" and c["version"] == 2 for c in answer["citations"])
