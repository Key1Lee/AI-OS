"""Initial trainer evidence schema. Existing assessment/training DBs are separate."""
from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("competencies", sa.Column("id",sa.String(),primary_key=True),sa.Column("definition",sa.JSON(),nullable=False))
    op.create_table("exercise_versions",sa.Column("id",sa.String(),primary_key=True),sa.Column("exercise_id",sa.String(),nullable=False),sa.Column("version",sa.Integer(),nullable=False),sa.Column("content_hash",sa.String(),nullable=False),sa.Column("definition",sa.JSON(),nullable=False),sa.UniqueConstraint("exercise_id","version"))
    op.create_index("ix_exercise_versions_exercise_id","exercise_versions",["exercise_id"])
    op.create_table("sessions",sa.Column("id",sa.String(),primary_key=True),sa.Column("mode",sa.String(),nullable=False),sa.Column("created_at",sa.String(),nullable=False),sa.Column("completed_at",sa.String()),sa.Column("status",sa.String(),nullable=False))
    op.create_table("attempts",sa.Column("id",sa.String(),primary_key=True),sa.Column("session_id",sa.String(),sa.ForeignKey("sessions.id"),nullable=False),sa.Column("exercise_version_id",sa.String(),sa.ForeignKey("exercise_versions.id"),nullable=False),sa.Column("parent_attempt_id",sa.String(),sa.ForeignKey("attempts.id")),sa.Column("mode",sa.String(),nullable=False),sa.Column("status",sa.String(),nullable=False),sa.Column("started_at",sa.String(),nullable=False),sa.Column("completed_at",sa.String()),sa.Column("code",sa.Text(),nullable=False),sa.Column("explanation",sa.Text(),nullable=False),sa.Column("external_assistance",sa.Boolean(),nullable=False),sa.Column("solution_seen",sa.Boolean(),nullable=False),sa.Column("hint_count",sa.Integer(),nullable=False),sa.Column("draft_revision",sa.Integer(),nullable=False),sa.Column("timed",sa.Boolean(),nullable=False),sa.Column("result",sa.JSON()),sa.Column("selection",sa.JSON(),nullable=False))
    op.create_table("attempt_submissions",sa.Column("id",sa.String(),primary_key=True),sa.Column("attempt_id",sa.String(),sa.ForeignKey("attempts.id"),nullable=False),sa.Column("created_at",sa.String(),nullable=False),sa.Column("code",sa.Text(),nullable=False),sa.Column("explanation",sa.Text(),nullable=False),sa.Column("external_assistance",sa.Boolean(),nullable=False),sa.Column("status",sa.String(),nullable=False),sa.Column("result",sa.JSON()))
    op.create_table("test_runs",sa.Column("id",sa.String(),primary_key=True),sa.Column("attempt_id",sa.String(),sa.ForeignKey("attempts.id"),nullable=False),sa.Column("kind",sa.String(),nullable=False),sa.Column("code",sa.Text(),nullable=False),sa.Column("created_at",sa.String(),nullable=False),sa.Column("result",sa.JSON(),nullable=False))
    op.create_table("interactions",sa.Column("id",sa.String(),primary_key=True),sa.Column("attempt_id",sa.String(),sa.ForeignKey("attempts.id"),nullable=False),sa.Column("kind",sa.String(),nullable=False),sa.Column("created_at",sa.String(),nullable=False),sa.Column("payload",sa.JSON(),nullable=False))
    op.create_table("mastery",sa.Column("competency_id",sa.String(),sa.ForeignKey("competencies.id"),primary_key=True),sa.Column("state",sa.JSON(),nullable=False))
    op.create_table("mistakes",sa.Column("id",sa.String(),primary_key=True),sa.Column("competency_id",sa.String(),sa.ForeignKey("competencies.id"),nullable=False),sa.Column("category",sa.String(),nullable=False),sa.Column("state",sa.JSON(),nullable=False),sa.UniqueConstraint("competency_id","category"))
    op.create_table("events",sa.Column("id",sa.String(),primary_key=True),sa.Column("attempt_id",sa.String(),sa.ForeignKey("attempts.id")),sa.Column("event_type",sa.String(),nullable=False),sa.Column("created_at",sa.String(),nullable=False),sa.Column("payload",sa.JSON(),nullable=False))
    for table,column in [("attempts","session_id"),("attempt_submissions","attempt_id"),("test_runs","attempt_id"),("interactions","attempt_id"),("mistakes","competency_id"),("events","attempt_id"),("events","event_type")]:
        op.create_index(f"ix_{table}_{column}",table,[column])


def downgrade():
    raise RuntimeError("Training evidence is append-only; restore an explicit backup instead of dropping tables.")
