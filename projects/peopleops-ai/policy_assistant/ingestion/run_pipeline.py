import json
from uuid import uuid4
from pydantic import ValidationError

from app.mock_store import initialize, transaction
from app.settings import HRSettings
from ingestion.extract_documents import extract_documents
from ingestion.validate_documents import load_registry, validate_document
from ingestion.classify_documents import rejection_reason
from ingestion.chunk_documents import chunk_document
from ingestion.index_documents import index_document, sync_registry


def run_pipeline(settings=None):
    """Execute all ingestion stages atomically and record counts plus safe reject reasons."""
    settings = settings or HRSettings.configured()
    initialize(settings.database_path)
    registry = load_registry(settings.fixture_root / "registry.jsonl")
    report = {"run_id": str(uuid4()), "extracted": 0, "indexed": 0, "unchanged": 0, "rechunked": 0, "rejected": []}
    with transaction(settings.database_path, immediate=True) as conn:
        sync_registry(conn, registry)
        for filename, line, raw, error in extract_documents(settings.fixture_root / "documents"):
            report["extracted"] += 1
            reason = error
            document = None
            if not error:
                try:
                    document = validate_document(raw, registry)
                    reason = rejection_reason(document, settings.as_of_date)
                except ValidationError:
                    reason = "invalid_schema"
                except ValueError as exc:
                    reason = str(exc) if str(exc) in ("not_in_registry", "metadata_mismatch", "content_mismatch") else "invalid_source"
            if reason:
                report["rejected"].append({"source": filename, "line": line, "reason": reason})
                continue
            chunks = chunk_document(document, settings.chunk_chars)
            entry = registry[(document.document_id, document.version)]
            report[index_document(conn, document, chunks, entry["content_sha256"])] += 1
        conn.execute("INSERT INTO ingestion_runs(run_id,report) VALUES(?,?)", (report["run_id"], json.dumps(report)))
    return report


if __name__ == "__main__":
    print(json.dumps(run_pipeline(), indent=2))
