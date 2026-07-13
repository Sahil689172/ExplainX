"""Project repository — SQL access only."""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.db.models import Project


class ProjectRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, project: Project) -> Project:
        self._session.add(project)
        return project

    def get(self, project_id: str, *, include_deleted: bool = False) -> Project | None:
        stmt = (
            select(Project)
            .options(joinedload(Project.settings))
            .where(Project.project_id == project_id)
        )
        if not include_deleted:
            stmt = stmt.where(Project.deleted_at.is_(None))
        return self._session.scalars(stmt).first()

    def find_by_title(self, title: str) -> Project | None:
        """Return the most recently updated non-deleted project with this title.

        Title match is case-insensitive. Titles are not unique.
        """
        cleaned = title.strip()
        if not cleaned:
            return None
        stmt = (
            select(Project)
            .options(joinedload(Project.settings))
            .where(
                func.lower(Project.title) == cleaned.lower(),
                Project.deleted_at.is_(None),
            )
            .order_by(Project.updated_at.desc())
            .limit(1)
        )
        return self._session.scalars(stmt).first()

    def list(
        self,
        *,
        status: str | None = None,
        q: str | None = None,
        limit: int = 20,
        include_archived: bool = True,
        recent_only: bool = False,
    ) -> list[Project]:
        stmt = (
            select(Project)
            .options(joinedload(Project.settings))
            .where(Project.deleted_at.is_(None))
            .order_by(Project.updated_at.desc())
        )
        if status:
            stmt = stmt.where(Project.status == status)
        elif not include_archived:
            stmt = stmt.where(Project.status != "archived")
        if q:
            pattern = f"%{q.strip().lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(Project.title).like(pattern),
                    func.lower(func.coalesce(Project.description, "")).like(pattern),
                )
            )
        if recent_only:
            limit = min(limit, 10)
        stmt = stmt.limit(limit)
        return list(self._session.scalars(stmt).unique().all())

    def count_active(self) -> int:
        stmt = select(func.count()).select_from(Project).where(Project.deleted_at.is_(None))
        return int(self._session.scalar(stmt) or 0)
