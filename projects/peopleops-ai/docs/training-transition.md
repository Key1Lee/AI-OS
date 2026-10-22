# Training platform transition

## Source and target

The existing Python 3.13, SQLite, vanilla-browser simulation stays runnable at
the project root. Its data, API on port 8765, tests, and completed business
logic are preserved. The new primary learning environment lives in `training/`:
Python 3.12, FastAPI/Pydantic, SQLAlchemy, PostgreSQL/pgvector, Streamlit, and
Docker Compose. No legacy records are migrated or shared.

## Sequence and acceptance

1. Add isolated dependencies, containers, deterministic fixtures, normalized
   models, mock HTTP services, and health/UI plumbing.
2. Add exercise signatures and deliberately failing tests for business logic;
   keep them outside the default foundation test suite. Never import the old
   solutions into the training path.
3. Add evaluation tooling, operational evidence, and interview documentation.
4. Verify real PostgreSQL/vector storage, full Compose startup, foundation
   tests, mock fault scenarios, UI, and the unchanged legacy suite.
5. Hand off the first exercise. Functional business phases are pending learner
   work; foundation completion is not evidence of interview mastery.

## Invariants and recovery

The two databases, environments, ports, and API contracts are independent.
The training app returns an explicit exercise-pending outcome, without data or
side effects, when a business exercise is unimplemented. Mock services contain
only synthetic records. The optional external LLM is disabled by default.
All host-published container ports bind to loopback.

This is additive and reversible: stop `training/` with `docker compose down`
(without `-v`) and run the original launcher. Named volumes retain training
state. No destructive migration, backfill, or production rollout is included.
Retain the old demo as a reference until the user requests retirement. Keep
assessment separate from the AI-generated reference implementation.
