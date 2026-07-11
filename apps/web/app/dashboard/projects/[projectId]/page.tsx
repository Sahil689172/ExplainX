"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";

import { DeleteConfirmDialog } from "@/features/projects/DeleteConfirmDialog";
import {
  archiveProject,
  deleteProject,
  duplicateProject,
  getProject,
  renameProject,
  saveProject,
} from "@/lib/api/client";
import type { ProjectDetail } from "@/types/project";

export default function ProjectDetailPage() {
  const params = useParams<{ projectId: string }>();
  const router = useRouter();
  const projectId = params.projectId;

  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      const result = await getProject(projectId);
      setProject(result.data);
      setRenameValue(result.data.title);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load project");
    }
  }, [projectId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleRename(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      const result = await renameProject(projectId, renameValue.trim());
      setProject(result.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Rename failed");
    } finally {
      setBusy(false);
    }
  }

  if (error && !project) {
    return (
      <div className="space-y-4">
        <p className="text-red-300">{error}</p>
        <Link href="/dashboard/projects" className="text-accent">
          ← Back to projects
        </Link>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="h-40 animate-pulse rounded-2xl border border-line bg-canvas-muted/40" />
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <Link
            href="/dashboard/projects"
            className="text-sm text-ink-faint hover:text-accent"
          >
            ← Projects
          </Link>
          <h1 className="mt-2 font-display text-3xl font-semibold text-ink md:text-4xl">
            {project.title}
          </h1>
          <p className="mt-2 max-w-2xl text-ink-muted">
            {project.description || "No description"}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            disabled={busy}
            onClick={async () => {
              setBusy(true);
              try {
                setProject((await saveProject(projectId)).data);
              } finally {
                setBusy(false);
              }
            }}
            className="rounded-full border border-line px-4 py-2 text-sm text-ink-muted hover:border-accent hover:text-accent"
          >
            Save
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={async () => {
              setBusy(true);
              try {
                const dup = await duplicateProject(projectId);
                router.push(`/dashboard/projects/${dup.data.project_id}`);
              } finally {
                setBusy(false);
              }
            }}
            className="rounded-full border border-line px-4 py-2 text-sm text-ink-muted hover:border-accent hover:text-accent"
          >
            Duplicate
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={async () => {
              setBusy(true);
              try {
                setProject((await archiveProject(projectId)).data);
              } finally {
                setBusy(false);
              }
            }}
            className="rounded-full border border-line px-4 py-2 text-sm text-ink-muted hover:border-accent hover:text-accent"
          >
            Archive
          </button>
          <button
            type="button"
            onClick={() => setDeleteOpen(true)}
            className="rounded-full border border-red-400/40 px-4 py-2 text-sm text-red-300"
          >
            Delete
          </button>
        </div>
      </div>

      {error ? <p className="text-sm text-red-300">{error}</p> : null}

      <section className="grid gap-4 md:grid-cols-2">
        <div className="rounded-2xl border border-line bg-canvas-elevated/80 p-5">
          <h2 className="font-display text-lg text-ink">Metadata</h2>
          <dl className="mt-4 space-y-2 text-sm">
            <div className="flex justify-between gap-4">
              <dt className="text-ink-faint">Status</dt>
              <dd>{project.status}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-ink-faint">Phase</dt>
              <dd>{project.current_phase}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-ink-faint">Theme</dt>
              <dd>{project.theme_id}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-ink-faint">Language</dt>
              <dd>{project.source_language_code}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-ink-faint">DSL version</dt>
              <dd>{project.dsl_version}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-ink-faint">Project version</dt>
              <dd>{project.project_version}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-ink-faint">Created</dt>
              <dd>{new Date(project.created_at).toLocaleString()}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-ink-faint">Modified</dt>
              <dd>{new Date(project.updated_at).toLocaleString()}</dd>
            </div>
          </dl>
        </div>

        <div className="rounded-2xl border border-line bg-canvas-elevated/80 p-5">
          <h2 className="font-display text-lg text-ink">Directories</h2>
          <ul className="mt-4 space-y-2 font-mono text-xs text-ink-muted">
            <li>root: {project.project_root}</li>
            <li>assets: {project.assets_directory}</li>
            <li>export: {project.output_directory}</li>
            {Object.entries(project.directories).map(([key, value]) => (
              <li key={key}>
                {key}: {value}
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section className="rounded-2xl border border-line bg-canvas-elevated/80 p-5">
        <h2 className="font-display text-lg text-ink">Rename</h2>
        <form
          onSubmit={handleRename}
          className="mt-4 flex flex-col gap-3 md:flex-row"
        >
          <input
            value={renameValue}
            onChange={(e) => setRenameValue(e.target.value)}
            className="w-full rounded-xl border border-line bg-canvas px-3 py-2 text-ink outline-none focus:border-accent"
            maxLength={120}
          />
          <button
            type="submit"
            disabled={busy}
            className="rounded-full bg-accent px-5 py-2 text-sm font-semibold text-canvas"
          >
            Rename
          </button>
        </form>
      </section>

      <DeleteConfirmDialog
        open={deleteOpen}
        projectTitle={project.title}
        onCancel={() => setDeleteOpen(false)}
        onConfirm={async () => {
          await deleteProject(projectId);
          router.push("/dashboard/projects");
        }}
      />
    </div>
  );
}
