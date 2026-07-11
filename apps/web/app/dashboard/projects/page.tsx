"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { DeleteConfirmDialog } from "@/features/projects/DeleteConfirmDialog";
import { NewProjectDialog } from "@/features/projects/NewProjectDialog";
import { ProjectCard } from "@/features/projects/ProjectCard";
import { ProjectsEmptyState } from "@/features/projects/ProjectsEmptyState";
import {
  createProject,
  deleteProject,
  duplicateProject,
  listProjects,
} from "@/lib/api/client";
import type { ProjectSummary } from "@/types/project";

export default function ProjectsPage() {
  const router = useRouter();
  const [items, setItems] = useState<ProjectSummary[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [pendingDelete, setPendingDelete] = useState<ProjectSummary | null>(
    null,
  );

  const load = useCallback(async (q?: string) => {
    setLoading(true);
    setError(null);
    try {
      const result = await listProjects({ q: q || undefined, limit: 50 });
      setItems(result.data.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load projects");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const recent = useMemo(() => items.slice(0, 5), [items]);

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="font-display text-3xl font-semibold text-ink">
            Projects
          </h1>
          <p className="mt-2 max-w-xl text-ink-muted">
            Open, create, rename, duplicate, and archive local projects.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setDialogOpen(true)}
          className="rounded-full bg-accent px-5 py-2.5 text-sm font-semibold text-canvas"
        >
          New project
        </button>
      </div>

      <div className="flex flex-col gap-3 md:flex-row">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") void load(query);
          }}
          placeholder="Search projects…"
          className="w-full rounded-xl border border-line bg-canvas-elevated px-4 py-2.5 text-sm text-ink outline-none focus:border-accent md:max-w-md"
        />
        <button
          type="button"
          onClick={() => void load(query)}
          className="rounded-full border border-line px-4 py-2 text-sm text-ink-muted hover:border-accent hover:text-accent"
        >
          Search
        </button>
      </div>

      {error ? (
        <p className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
          {error}
        </p>
      ) : null}

      {!loading && items.length === 0 ? (
        <ProjectsEmptyState onCreate={() => setDialogOpen(true)} />
      ) : (
        <>
          {recent.length > 0 && !query ? (
            <section className="space-y-3">
              <h2 className="text-sm uppercase tracking-[0.15em] text-ink-faint">
                Recent
              </h2>
              <div className="flex flex-wrap gap-2">
                {recent.map((p) => (
                  <button
                    key={`recent-${p.project_id}`}
                    type="button"
                    onClick={() =>
                      router.push(`/dashboard/projects/${p.project_id}`)
                    }
                    className="rounded-full border border-line px-3 py-1.5 text-xs text-ink-muted hover:border-accent hover:text-accent"
                  >
                    {p.title}
                  </button>
                ))}
              </div>
            </section>
          ) : null}

          <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {loading
              ? Array.from({ length: 3 }).map((_, i) => (
                  <div
                    key={i}
                    className="h-48 animate-pulse rounded-2xl border border-line bg-canvas-muted/50"
                  />
                ))
              : items.map((project) => (
                  <ProjectCard
                    key={project.project_id}
                    project={project}
                    onDelete={setPendingDelete}
                    onDuplicate={async (p) => {
                      await duplicateProject(p.project_id);
                      await load(query);
                    }}
                  />
                ))}
          </section>
        </>
      )}

      <NewProjectDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        onCreate={async (input) => {
          const created = await createProject(input);
          await load(query);
          router.push(`/dashboard/projects/${created.data.project_id}`);
        }}
      />

      <DeleteConfirmDialog
        open={Boolean(pendingDelete)}
        projectTitle={pendingDelete?.title ?? ""}
        onCancel={() => setPendingDelete(null)}
        onConfirm={async () => {
          if (!pendingDelete) return;
          await deleteProject(pendingDelete.project_id);
          setPendingDelete(null);
          await load(query);
        }}
      />
    </div>
  );
}
