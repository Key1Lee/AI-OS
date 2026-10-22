from io import BytesIO
from zipfile import ZipFile

from fastapi.testclient import TestClient

from survey_analytics.api import create_app
from survey_analytics.manager_pack_content import BR, REQUIREMENTS, STEPS


def test_guided_architecture_and_requirement_documents_are_accessible(tmp_path):
    with TestClient(create_app(tmp_path / "guide.sqlite3")) as client:
        guide = client.get("/guide")
        assert guide.status_code == 200
        assert "Execute n8n workflow" in guide.text
        for step in STEPS:
            assert step["name"] in guide.text
        for req in REQUIREMENTS:
            assert req["id"] in guide.text
        for identifier, *_ in BR:
            assert identifier in guide.text
        for filename, title in [
            ("BusinessRequirements.docx", "Business requirements document"),
            ("WorkflowRequirements.docx", "Workflow requirements document"),
        ]:
            response = client.get("/guide/download/" + filename)
            assert response.status_code == 200
            with ZipFile(BytesIO(response.content)) as doc:
                xml = doc.read("word/document.xml").decode()
                assert title in xml and "fictional" in xml
        assert "/guide" in client.get("/dashboard").text


def test_guide_downloads_do_not_accept_arbitrary_files(tmp_path):
    with TestClient(create_app(tmp_path / "guide.sqlite3")) as client:
        assert client.get("/guide/download/secret.env").status_code == 422
        assert (
            client.get("/guide/download/architecture.svg")
            .headers["content-type"]
            .startswith("image/svg+xml")
        )
        assert (
            len(client.get("/guide/download/requirements.csv").text.splitlines()) == 13
        )
