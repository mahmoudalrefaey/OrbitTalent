"""ats v2 schema — 13 stages, candidate ATS fields, stage_events, automation, hiring rules

Revision ID: 9befbebc974b
Revises: 8dfbe6a35a72
Create Date: 2026-06-22

PostgreSQL-only. Idempotent: safe to re-run after a partial failure. It:
  - drops any leftover stage_events / automation_rules from a failed prior run,
  - creates/normalizes the `candidatestage` (13 values) + `rejectionreason` enums,
    remapping the legacy value `interview` -> `interview_scheduled`,
  - adds the new candidate / scoring_criteria columns (skipping any that already
    exist), backfilling applied_at from created_at.

All enum COLUMNS use postgresql.ENUM(..., create_type=False) so SQLAlchemy never
auto-emits CREATE TYPE — the types are managed explicitly with raw SQL here.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "9befbebc974b"
down_revision: Union[str, None] = "8dfbe6a35a72"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

STAGES = (
    "new", "ai_screened", "qualified", "shortlisted", "assessment_pending",
    "assessment_passed", "interview_scheduled", "interview_passed",
    "final_review", "offer_sent", "hired", "rejected", "withdrawn",
)
REJECTION_REASONS = (
    "low_ai_score", "missing_required_skills", "wrong_experience_level",
    "wrong_location", "country_restriction", "duplicate_application",
    "recruiter_decision",
)
STAGE_REMAP = {"interview": "interview_scheduled"}

# Column types: reference the enums WITHOUT creating them (we manage types below).
CANDIDATESTAGE = postgresql.ENUM(*STAGES, name="candidatestage", create_type=False)
REJECTIONREASON = postgresql.ENUM(
    *REJECTION_REASONS, name="rejectionreason", create_type=False
)


def _scalar(sql: str, **params):
    return op.get_bind().execute(sa.text(sql), params).scalar()


def _type_exists(name: str) -> bool:
    return bool(_scalar("SELECT 1 FROM pg_type WHERE typname = :n", n=name))


def _col_exists(table: str, col: str) -> bool:
    insp = sa.inspect(op.get_bind())
    return any(c["name"] == col for c in insp.get_columns(table))


def _enum_values(name: str) -> set[str]:
    rows = op.get_bind().execute(
        sa.text(
            "SELECT e.enumlabel FROM pg_enum e "
            "JOIN pg_type t ON t.oid = e.enumtypid WHERE t.typname = :n"
        ),
        {"n": name},
    ).all()
    return {r[0] for r in rows}


def upgrade() -> None:
    # 0. Remove leftovers from any partially-applied prior run.
    op.execute("DROP TABLE IF EXISTS stage_events CASCADE")
    op.execute("DROP TABLE IF EXISTS automation_rules CASCADE")

    # 1. rejectionreason enum — (re)create cleanly.
    op.execute("DROP TYPE IF EXISTS rejectionreason")
    op.execute(
        "CREATE TYPE rejectionreason AS ENUM ("
        + ", ".join(f"'{v}'" for v in REJECTION_REASONS)
        + ")"
    )

    # 2. candidatestage enum — ensure it exists with the full 13-value set and
    #    the candidates.stage column is migrated onto it (remapping legacy values).
    #    Handle every partial state: only-old exists, both exist, or current type
    #    already has all values.
    if _type_exists("candidatestage_old") and not _type_exists("candidatestage"):
        # A prior run renamed but didn't recreate. Make the new type now.
        op.execute(
            "CREATE TYPE candidatestage AS ENUM ("
            + ", ".join(f"'{v}'" for v in STAGES)
            + ")"
        )
    elif _type_exists("candidatestage") and set(STAGES) <= _enum_values("candidatestage"):
        # Already the full new vocabulary — nothing to do for the type itself.
        pass
    elif _type_exists("candidatestage"):
        # Old (or partial) type in place: rename out of the way, create the new one.
        op.execute("DROP TYPE IF EXISTS candidatestage_old")
        op.execute("ALTER TYPE candidatestage RENAME TO candidatestage_old")
        op.execute(
            "CREATE TYPE candidatestage AS ENUM ("
            + ", ".join(f"'{v}'" for v in STAGES)
            + ")"
        )
    else:
        op.execute(
            "CREATE TYPE candidatestage AS ENUM ("
            + ", ".join(f"'{v}'" for v in STAGES)
            + ")"
        )

    # Migrate candidates.stage: text -> remap -> new enum.
    # The column has a DEFAULT ('new'); Postgres can't auto-cast a text default
    # to the enum type, so DROP the default, convert the type, then re-add the
    # default as a properly-typed enum literal.
    op.execute("ALTER TABLE candidates ALTER COLUMN stage DROP DEFAULT")
    op.execute("ALTER TABLE candidates ALTER COLUMN stage TYPE text USING stage::text")
    for old, new in STAGE_REMAP.items():
        # Values come from our own constant (not user input) — safe to inline.
        op.execute(f"UPDATE candidates SET stage = '{new}' WHERE stage = '{old}'")
    op.execute(
        "ALTER TABLE candidates ALTER COLUMN stage TYPE candidatestage "
        "USING stage::candidatestage"
    )
    op.execute("ALTER TABLE candidates ALTER COLUMN stage SET DEFAULT 'new'::candidatestage")
    op.execute("DROP TYPE IF EXISTS candidatestage_old")

    # 3. New tables (enum columns use create_type=False, so no CREATE TYPE here).
    op.create_table(
        "automation_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("jobs.id"), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("trigger_json", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("action_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_automation_rules_tenant_id", "automation_rules", ["tenant_id"])
    op.create_index("ix_automation_rules_job_id", "automation_rules", ["job_id"])

    op.create_table(
        "stage_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("candidate_id", sa.Integer(), sa.ForeignKey("candidates.id"), nullable=False),
        sa.Column("from_stage", CANDIDATESTAGE, nullable=True),
        sa.Column("to_stage", CANDIDATESTAGE, nullable=False),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_stage_events_tenant_id", "stage_events", ["tenant_id"])
    op.create_index("ix_stage_events_candidate_id", "stage_events", ["candidate_id"])
    op.create_index("ix_stage_events_at", "stage_events", ["at"])

    # 4. candidates: new columns (skip any already present from a partial run).
    cand_cols = [
        ("country", sa.Column("country", sa.String(length=120), nullable=True)),
        ("city", sa.Column("city", sa.String(length=120), nullable=True)),
        ("experience_years", sa.Column("experience_years", sa.Float(), nullable=True)),
        ("education", sa.Column("education", sa.String(length=255), nullable=True)),
        ("certifications", sa.Column("certifications", sa.JSON(), nullable=False, server_default="[]")),
        ("languages", sa.Column("languages", sa.JSON(), nullable=False, server_default="[]")),
        ("expected_salary", sa.Column("expected_salary", sa.Integer(), nullable=True)),
        ("rejection_reason", sa.Column("rejection_reason", REJECTIONREASON, nullable=True)),
        ("assigned_recruiter_id", sa.Column("assigned_recruiter_id", sa.Integer(), nullable=True)),
        ("applied_at", sa.Column("applied_at", sa.DateTime(), nullable=True)),
    ]
    for name, col in cand_cols:
        if not _col_exists("candidates", name):
            op.add_column("candidates", col)

    op.execute("UPDATE candidates SET applied_at = created_at WHERE applied_at IS NULL")
    op.execute("ALTER TABLE candidates ALTER COLUMN applied_at SET NOT NULL")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_candidates_assigned_recruiter_id "
        "ON candidates (assigned_recruiter_id)"
    )
    op.execute(
        "DO $$ BEGIN "
        "IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_candidates_recruiter') THEN "
        "ALTER TABLE candidates ADD CONSTRAINT fk_candidates_recruiter "
        "FOREIGN KEY (assigned_recruiter_id) REFERENCES users(id); "
        "END IF; END $$;"
    )

    # 5. scoring_criteria: hiring rules (skip any already present).
    crit_cols = [
        ("geo_allow", sa.Column("geo_allow", sa.JSON(), nullable=False, server_default="[]")),
        ("geo_block", sa.Column("geo_block", sa.JSON(), nullable=False, server_default="[]")),
        ("min_degree", sa.Column("min_degree", sa.String(length=120), nullable=True)),
        ("preferred_universities", sa.Column("preferred_universities", sa.JSON(), nullable=False, server_default="[]")),
        ("min_experience", sa.Column("min_experience", sa.Integer(), nullable=True)),
        ("max_experience", sa.Column("max_experience", sa.Integer(), nullable=True)),
        ("ranking_weights", sa.Column("ranking_weights", sa.JSON(), nullable=False, server_default="{}")),
    ]
    for name, col in crit_cols:
        if not _col_exists("scoring_criteria", name):
            op.add_column("scoring_criteria", col)


def downgrade() -> None:
    for col in ("ranking_weights", "max_experience", "min_experience",
                "preferred_universities", "min_degree", "geo_block", "geo_allow"):
        op.execute(f"ALTER TABLE scoring_criteria DROP COLUMN IF EXISTS {col}")

    op.execute("ALTER TABLE candidates DROP CONSTRAINT IF EXISTS fk_candidates_recruiter")
    op.execute("DROP INDEX IF EXISTS ix_candidates_assigned_recruiter_id")
    for col in ("applied_at", "assigned_recruiter_id", "rejection_reason",
                "expected_salary", "languages", "certifications", "education",
                "experience_years", "city", "country"):
        op.execute(f"ALTER TABLE candidates DROP COLUMN IF EXISTS {col}")

    op.execute("DROP TABLE IF EXISTS stage_events CASCADE")
    op.execute("DROP TABLE IF EXISTS automation_rules CASCADE")
    op.execute("DROP TYPE IF EXISTS rejectionreason")
    # candidatestage left intact (lossy to revert; not needed for dev).
