from exercises.e04_chunking import chunk_policy


def test_preserves_section_and_version(fixture_data):
    policy = fixture_data["policies"][0]
    chunks = chunk_policy(policy)
    assert chunks == [{"chunk_id": "PTO:2:1:0", "section_key": "PTO:2:1", "body": policy["sections"][0]["body"]},
                      {"chunk_id": "PTO:2:2:0", "section_key": "PTO:2:2", "body": policy["sections"][1]["body"]}]


def test_long_section_has_bounded_chunks():
    policy = {"policy_id": "TEST", "version": 7, "sections": [{"section_id": "a", "body": "one two three four five"}]}
    chunks = chunk_policy(policy, max_words=2)
    assert [c["body"] for c in chunks] == ["one two", "three four", "five"]
    assert [c["chunk_id"] for c in chunks] == ["TEST:7:a:0", "TEST:7:a:1", "TEST:7:a:2"]
