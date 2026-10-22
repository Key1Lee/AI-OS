import hashlib
from app.policies import chunk_sections


def chunk_document(document, max_chars):
    """Split exact source passages while retaining stable document/version citation IDs."""
    chunks = []
    for item in chunk_sections(document.text, max_chars):
        key = f"{document.document_id}:{document.version}:{item['ordinal']}:{item['body']}"
        chunks.append({**item, "chunk_id": hashlib.sha256(key.encode()).hexdigest()[:32]})
    return chunks
