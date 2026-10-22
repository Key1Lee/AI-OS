CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS policy_documents (
  tenant text NOT NULL,
  policy_id text NOT NULL,
  version integer NOT NULL CHECK (version > 0),
  title text NOT NULL,
  effective_on date NOT NULL,
  expires_on date,
  regions text[] NOT NULL,
  roles text[] NOT NULL,
  withdrawn boolean NOT NULL DEFAULT false,
  source text NOT NULL,
  content_hash text NOT NULL,
  ingested_by text NOT NULL,
  ingested_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant, policy_id, version)
);
CREATE TABLE IF NOT EXISTS policy_chunks (
  tenant text NOT NULL,
  policy_id text NOT NULL,
  version integer NOT NULL,
  chunk_id text NOT NULL,
  ordinal integer NOT NULL,
  section text NOT NULL,
  body text NOT NULL,
  embedding vector NOT NULL,
  embedding_space text NOT NULL,
  PRIMARY KEY (tenant, chunk_id, embedding_space),
  FOREIGN KEY (tenant, policy_id, version) REFERENCES policy_documents (tenant, policy_id, version)
);
CREATE INDEX IF NOT EXISTS policy_chunk_version ON policy_chunks (tenant, policy_id, version, embedding_space);
CREATE TABLE IF NOT EXISTS policy_audit (
  event_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  tenant text NOT NULL,
  actor text NOT NULL,
  action text NOT NULL,
  policy_id text NOT NULL,
  version integer NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
