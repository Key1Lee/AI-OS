import json


def version_order(version):
    major, minor = map(int, version.split("."))
    return major * 1000 + minor


def sync_registry(conn, registry):
    """Mirror the governed inventory, including tombstones, before indexing any text."""
    conn.execute("DELETE FROM inventory_membership")
    for (document_id, version), entry in registry.items():
        existing = conn.execute("SELECT digest,metadata FROM registry WHERE document_id=? AND version=?", (document_id, version)).fetchone()
        encoded = json.dumps(entry["metadata"], sort_keys=True)
        if existing and (existing["digest"] != entry["content_sha256"] or existing["metadata"] != encoded):
            raise ValueError("Immutable registry version changed; publish a new version")
        conn.execute("INSERT OR IGNORE INTO registry VALUES(?,?,?,?,?)", (document_id, version, version_order(version), encoded, entry["content_sha256"]))
        conn.execute("INSERT INTO inventory_membership VALUES(?,?)", (document_id, version))


def index_document(conn, document, chunks, digest):
    """Insert one approved version, or update only its derived chunks when chunk settings change."""
    key = (document.document_id, document.version)
    existing = conn.execute("SELECT digest FROM indexed_documents WHERE document_id=? AND version=?", key).fetchone()
    if existing and existing["digest"] != digest:
        raise ValueError("Immutable indexed version conflict")
    previous = [row[0] for row in conn.execute("SELECT chunk_id FROM chunks WHERE document_id=? AND version=? ORDER BY ordinal", key)]
    conn.execute("INSERT OR IGNORE INTO indexed_documents VALUES(?,?,?,?)", (*key, digest, document.text))
    conn.execute("UPDATE indexed_documents SET full_text=? WHERE document_id=? AND version=?", (document.text, *key))
    if previous == [chunk["chunk_id"] for chunk in chunks]:
        return "unchanged"
    conn.execute("DELETE FROM chunks WHERE document_id=? AND version=?", key)
    for chunk in chunks:
        conn.execute("INSERT INTO chunks VALUES(?,?,?,?,?,?)", (chunk["chunk_id"], *key, chunk["section"], chunk["ordinal"], chunk["body"]))
    return "rechunked" if existing else "indexed"
