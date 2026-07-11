"use client";

import Link from "next/link";

import type { ProjectSummary } from "@/types/project";

type ProjectCardProps = {
  project: ProjectSummary;
  onDelete: (project: ProjectSummary) => void;
  onDuplicate: (project: ProjectSummary) => void;
};

export function ProjectCard({
  project,
  onDelete,
  onDuplicate,
}: ProjectCardProps) {
  return (
    <article className="flex flex-col rounded-2xl border border-line bg-canvas-elevated/80 p-5 shadow-panel transition hover:border-accent/40">
      <div className="flex items-start justify-between gap-3">
        <div>
          <Link
            href={`/dashboard/projects/${project.project_id}`}
            className="font-display text-xl text-ink hover:text-accent"
          >
            {project.title}
          </Link>
          <p className="mt-1 line-clamp-2 text-sm text-ink-muted">
            {project.description || "No description"}
          </p>
        </div>
        <span className="rounded-full border border-line px-2 py-0.5 text-xs uppercase tracking-wide text-ink-faint">
          {project.status}
        </span>
      </div>
      <dl className="mt-4 grid grid-cols-2 gap-2 text-xs text-ink-faint">
        <div>
          <dt>Theme</dt>
          <dd className="text-ink-muted">{project.theme_id}</dd>
        </div>
        <div>
          <dt>Phase</dt>
          <dd className="text-ink-muted">{project.current_phase}</dd>
        </div>
        <div>
          <dt>Updated</dt>
          <dd className="text-ink-muted">
            {new Date(project.updated_at).toLocaleString()}
          </dd>
        </div>
        <div>
          <dt>Language</dt>
          <dd className="text-ink-muted">{project.source_language_code}</dd>
        </div>
      </dl>
      <div className="mt-4 flex flex-wrap gap-2">
        <Link
          href={`/dashboard/projects/${project.project_id}`}
          className="rounded-full border border-line px-3 py-1.5 text-xs text-ink-muted hover:border-accent hover:text-accent"
        >
          Open
        </Link>
        <button
          type="button"
          onClick={() => onDuplicate(project)}
          className="rounded-full border border-line px-3 py-1.5 text-xs text-ink-muted hover:border-accent hover:text-accent"
        >
          Duplicate
        </button>
        <button
          type="button"
          onClick={() => onDelete(project)}
          className="rounded-full border border-line px-3 py-1.5 text-xs text-red-300/80 hover:border-red-400 hover:text-red-300"
        >
          Delete
        </button>
      </div>
    </article>
  );
}
