"""Initial Phase 1.2 schema: themes, languages, projects, project_settings.

Revision ID: 20260711_001
Revises:
Create Date: 2026-07-11
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260711_001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "themes",
        sa.Column("theme_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("pack_path", sa.String(length=512), nullable=False),
        sa.Column("is_builtin", sa.Integer(), nullable=False),
        sa.Column("is_enabled", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.String(length=32), nullable=False),
        sa.Column("updated_at", sa.String(length=32), nullable=False),
        sa.PrimaryKeyConstraint("theme_id"),
    )
    op.create_table(
        "languages",
        sa.Column("language_code", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("native_name", sa.String(length=128), nullable=True),
        sa.Column("tts_supported", sa.Integer(), nullable=False),
        sa.Column("translation_supported", sa.Integer(), nullable=False),
        sa.Column("default_voice_id", sa.String(length=128), nullable=True),
        sa.Column("is_enabled", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.String(length=32), nullable=False),
        sa.Column("updated_at", sa.String(length=32), nullable=False),
        sa.PrimaryKeyConstraint("language_code"),
    )
    op.create_table(
        "projects",
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("current_phase", sa.String(length=32), nullable=False),
        sa.Column("source_type", sa.String(length=16), nullable=False),
        sa.Column("source_path", sa.String(length=512), nullable=True),
        sa.Column("source_topic", sa.Text(), nullable=True),
        sa.Column("source_hash", sa.String(length=128), nullable=False),
        sa.Column("theme_id", sa.String(length=64), nullable=False),
        sa.Column("source_language_code", sa.String(length=16), nullable=False),
        sa.Column("target_language_code", sa.String(length=16), nullable=False),
        sa.Column("voice_id", sa.String(length=128), nullable=True),
        sa.Column("difficulty", sa.String(length=32), nullable=True),
        sa.Column("current_version_id", sa.String(length=36), nullable=True),
        sa.Column("dsl_path", sa.String(length=512), nullable=True),
        sa.Column("timeline_path", sa.String(length=512), nullable=True),
        sa.Column("project_root", sa.String(length=512), nullable=False),
        sa.Column("project_version", sa.String(length=32), nullable=False),
        sa.Column("dsl_version", sa.String(length=16), nullable=False),
        sa.Column("schema_version", sa.String(length=16), nullable=False),
        sa.Column("estimated_duration_sec", sa.Float(), nullable=True),
        sa.Column("actual_duration_sec", sa.Float(), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.String(length=32), nullable=False),
        sa.Column("updated_at", sa.String(length=32), nullable=False),
        sa.Column("completed_at", sa.String(length=32), nullable=True),
        sa.Column("deleted_at", sa.String(length=32), nullable=True),
        sa.ForeignKeyConstraint(["source_language_code"], ["languages.language_code"]),
        sa.ForeignKeyConstraint(["target_language_code"], ["languages.language_code"]),
        sa.ForeignKeyConstraint(["theme_id"], ["themes.theme_id"]),
        sa.PrimaryKeyConstraint("project_id"),
    )
    op.create_index("ix_projects_deleted_at", "projects", ["deleted_at"], unique=False)
    op.create_index("ix_projects_status", "projects", ["status"], unique=False)
    op.create_index("ix_projects_title", "projects", ["title"], unique=False)
    op.create_index("ix_projects_updated_at", "projects", ["updated_at"], unique=False)
    op.create_table(
        "project_settings",
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("export_width", sa.Integer(), nullable=False),
        sa.Column("export_height", sa.Integer(), nullable=False),
        sa.Column("fps", sa.Float(), nullable=False),
        sa.Column("quality_profile", sa.String(length=32), nullable=False),
        sa.Column("burn_in_subtitles", sa.Integer(), nullable=False),
        sa.Column("subtitle_formats", sa.Text(), nullable=False),
        sa.Column("speaking_rate", sa.Float(), nullable=False),
        sa.Column("max_scenes", sa.Integer(), nullable=True),
        sa.Column("plugin_flags", sa.Text(), nullable=True),
        sa.Column("extra_json", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.project_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("project_id"),
    )


def downgrade() -> None:
    op.drop_table("project_settings")
    op.drop_index("ix_projects_updated_at", table_name="projects")
    op.drop_index("ix_projects_title", table_name="projects")
    op.drop_index("ix_projects_status", table_name="projects")
    op.drop_index("ix_projects_deleted_at", table_name="projects")
    op.drop_table("projects")
    op.drop_table("languages")
    op.drop_table("themes")
