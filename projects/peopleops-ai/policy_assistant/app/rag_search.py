from collections import Counter
import hashlib
import math
import re

from app.models import DocumentMetadata
from app.permissions import may_read_document
from app.security import suspicious_instruction

STOP = set("the a an is are was to of for in on with and or what how do does i my our company policy policies process please tell me about can from many much work general".split())
ALIASES = {"vacation": "pto", "holiday": "pto", "holidays": "pto", "requests": "request", "requesting": "request", "apply": "request", "maternity": "parental", "paternity": "parental", "benefit": "benefits", "remotely": "remote", "working": "work", "new": "starter"}


def search_terms(text):
    return [ALIASES.get(t, t) for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in STOP]


def authorized_chunks(conn, principal, as_of, security=None):
    """Select latest governed versions and enforce permissions before loading their chunk text."""
    rows = conn.execute("""SELECT * FROM registry WHERE json_extract(metadata,'$.effective_date')<=?
         ORDER BY document_id,version_order DESC""", (as_of.isoformat(),)).fetchall()
    seen, candidates = set(), []
    for row in rows:
        if row["document_id"] in seen:
            continue
        seen.add(row["document_id"])
        if conn.execute("SELECT 1 FROM inventory_membership WHERE document_id=? AND version=?", (row["document_id"], row["version"])).fetchone() is None:
            continue
        metadata = DocumentMetadata.model_validate_json(row["metadata"])
        if not may_read_document(principal, metadata, as_of, security):
            continue
        source = conn.execute("SELECT full_text,digest FROM indexed_documents WHERE document_id=? AND version=?", (metadata.document_id, metadata.version)).fetchone()
        if not source or hashlib.sha256(source["full_text"].encode()).hexdigest() != row["digest"] or source["digest"] != row["digest"]:
            continue
        chunks = conn.execute("SELECT * FROM chunks WHERE document_id=? AND version=? ORDER BY ordinal", (metadata.document_id, metadata.version)).fetchall()
        for chunk in chunks:
            expected = hashlib.sha256(f"{metadata.document_id}:{metadata.version}:{chunk['ordinal']}:{chunk['body']}".encode()).hexdigest()[:32]
            if expected != chunk["chunk_id"] or chunk["body"] not in source["full_text"] or suspicious_instruction(chunk["body"]):
                continue
            candidates.append({**dict(chunk), "metadata": metadata.model_dump(mode="json"), "title": metadata.title})
    return candidates


def search(conn, question, principal, settings, ranking="tfidf", candidates=None):
    """Rank only authorized chunks with deterministic TF-IDF and return up to top_k."""
    candidates = authorized_chunks(conn, principal, settings.as_of_date) if candidates is None else candidates
    query = set(search_terms(question))
    if not query or not candidates:
        return []
    counts = [Counter(search_terms(p["title"] + " " + p["section"] + " " + p["body"])) for p in candidates]
    frequencies = Counter(t for counts_in_doc in counts for t in counts_in_doc)
    for passage, words in zip(candidates, counts, strict=True):
        overlap = query & words.keys()
        score = sum((1 + math.log(words[t])) * math.log(1 + len(candidates) / frequencies[t]) for t in overlap)
        score /= max(1, math.sqrt(sum(v * v for v in words.values())))
        passage["score"] = len(overlap) / len(query) if ranking == "overlap" else score
        passage["query_coverage"] = len(overlap) / len(query)
    return sorted([p for p in candidates if p["score"] >= settings.min_relevance], key=lambda p: (-p["score"], p["chunk_id"]))[:settings.top_k]
