import hashlib
import json

from app.models import Document, DocumentMetadata


def load_registry(path):
    """Read the separately governed inventory and reject duplicate version authorities."""
    registry = {}
    for line in path.read_text().splitlines():
        entry = json.loads(line)
        metadata = DocumentMetadata.model_validate(entry["metadata"])
        key = (metadata.document_id, metadata.version)
        if key in registry:
            raise ValueError("Duplicate governed document version")
        digest = entry["content_sha256"]
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("Invalid approval digest")
        registry[key] = {"metadata": metadata.model_dump(mode="json"), "content_sha256": digest}
    return registry


def validate_document(raw, registry):
    """Check schema, approved metadata and content digest against the master inventory."""
    document = Document.model_validate(raw)
    expected = registry.get((document.document_id, document.version))
    if expected is None:
        raise ValueError("not_in_registry")
    metadata = document.model_dump(mode="json", exclude={"text"})
    if metadata != expected["metadata"]:
        raise ValueError("metadata_mismatch")
    if hashlib.sha256(document.text.encode()).hexdigest() != expected["content_sha256"]:
        raise ValueError("content_mismatch")
    return document
