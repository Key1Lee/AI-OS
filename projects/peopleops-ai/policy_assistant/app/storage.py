from contextlib import contextmanager
import hashlib
import json
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from app.policies import parse_policy


class VersionConflict(ValueError):
    pass


@contextmanager
def connect(settings):
    """Open a short database transaction that commits on success and rolls back on failure."""
    with psycopg.connect(settings.database_url.get_secret_value(), row_factory=dict_row, connect_timeout=3,
                         options="-c statement_timeout=15000 -c lock_timeout=10000") as conn:
        yield conn


def initialize(settings):
    """Create the initial schema in the dedicated app database. This never touches the training database."""
    with connect(settings) as conn:
        conn.execute(Path(__file__).with_name("schema.sql").read_text())


def ingest(conn, documents, identity, providers, settings) -> list[dict]:
    """Atomically store immutable policy versions and their embeddings. Repeating a delivery returns unchanged; changing an existing version is a conflict."""
    policies = [parse_policy(document) for document in documents]
    results = []
    # A tenant lock serializes concurrent ingestion and prevents duplicate embedding work.
    conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (identity.tenant,))
    for policy in policies:
        meta = policy.metadata
        key = (identity.tenant, meta.policy_id, meta.version)
        existing = conn.execute("SELECT content_hash FROM policy_documents WHERE tenant=%s AND policy_id=%s AND version=%s", key).fetchone()
        if existing and existing["content_hash"] != policy.content_hash:
            raise VersionConflict("An existing version has different content; publish a new version")
        indexed = conn.execute("SELECT count(*) AS n FROM policy_chunks WHERE tenant=%s AND policy_id=%s AND version=%s AND embedding_space=%s", (*key, settings.embedding_space)).fetchone()["n"]
        if existing and indexed:
            results.append({"policy_id": meta.policy_id, "version": meta.version, "status": "unchanged", "chunks": indexed})
            continue
        vectors = providers.embed([meta.title + "\n" + c["section"] + "\n" + c["body"] for c in policy.chunks])
        if not existing:
            conn.execute("""INSERT INTO policy_documents
              (tenant,policy_id,version,title,effective_on,expires_on,regions,roles,withdrawn,source,content_hash,ingested_by)
              VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
              (*key, meta.title, meta.effective_on, meta.expires_on, meta.regions, meta.roles, meta.withdrawn, policy.source, policy.content_hash, identity.subject))
        for chunk, vector in zip(policy.chunks, vectors, strict=True):
            chunk_id = hashlib.sha256(f"{identity.tenant}:{meta.policy_id}:{meta.version}:{chunk['ordinal']}:{policy.content_hash}".encode()).hexdigest()[:32]
            conn.execute("""INSERT INTO policy_chunks (tenant,policy_id,version,chunk_id,ordinal,section,body,embedding,embedding_space)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s::vector,%s)""",
                         (*key, chunk_id, chunk["ordinal"], chunk["section"], chunk["body"], json.dumps(vector), settings.embedding_space))
        action = "reindexed" if existing else "created"
        conn.execute("INSERT INTO policy_audit (tenant,actor,action,policy_id,version) VALUES (%s,%s,%s,%s,%s)",
                     (identity.tenant, identity.subject, action, meta.policy_id, meta.version))
        results.append({"policy_id": meta.policy_id, "version": meta.version, "status": action, "chunks": len(policy.chunks)})
    return results


RETRIEVE_SQL = """
WITH latest AS MATERIALIZED (
  SELECT DISTINCT ON (policy_id) * FROM policy_documents
  WHERE tenant = %(tenant)s AND effective_on <= %(as_of)s
  ORDER BY policy_id, version DESC
), authorized AS MATERIALIZED (
  SELECT * FROM latest
  WHERE NOT withdrawn AND (expires_on IS NULL OR expires_on > %(as_of)s)
    AND (%(region)s = ANY(regions) OR '*' = ANY(regions))
    AND %(role)s = ANY(roles)
), allowed_chunks AS MATERIALIZED (
  SELECT c.chunk_id,c.body,c.section,d.policy_id,d.version,d.title,d.source,d.effective_on,c.embedding
  FROM authorized d JOIN policy_chunks c USING (tenant,policy_id,version)
  WHERE c.embedding_space = %(space)s
)
SELECT chunk_id,body,section,policy_id,version,title,source,effective_on,
       1 - (embedding <=> %(vector)s::vector) AS similarity
FROM allowed_chunks
WHERE 1 - (embedding <=> %(vector)s::vector) >= %(threshold)s
ORDER BY embedding <=> %(vector)s::vector, chunk_id
LIMIT %(top_k)s
"""


def retrieve(conn, question, identity, providers, settings, as_of) -> list[dict]:
    """Filter current documents by tenant, region and role before cosine ranking in pgvector. Superseded or withdrawn versions cannot reappear through a broader old ACL."""
    vector = providers.embed([question])[0]
    return conn.execute(RETRIEVE_SQL, {"tenant": identity.tenant, "region": identity.region, "role": identity.role,
                                      "as_of": as_of, "space": settings.embedding_space, "vector": json.dumps(vector),
                                      "threshold": settings.min_similarity, "top_k": settings.top_k}).fetchall()
