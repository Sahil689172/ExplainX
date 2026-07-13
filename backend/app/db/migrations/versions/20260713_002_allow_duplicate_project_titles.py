"""Document that project titles are not unique (UUID is the primary key).

Revision ID: 20260713_002
Revises: 20260711_001
Create Date: 2026-07-13

The initial schema already created ``ix_projects_title`` with unique=False.
Uniqueness was enforced only in application code (now removed). This revision
records that contract explicitly and is a no-op on the physical schema.
"""

from __future__ import annotations

from typing import Sequence, Union

revision: str = "20260713_002"
down_revision: Union[str, None] = "20260711_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # No UNIQUE constraint existed on projects.title.
    # Application-level DUPLICATE_PROJECT checks were removed separately.
    pass


def downgrade() -> None:
    # Do not reintroduce title uniqueness at the database layer.
    pass
