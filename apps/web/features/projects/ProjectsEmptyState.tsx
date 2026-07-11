"use client";

type EmptyStateProps = {
  onCreate: () => void;
};

export function ProjectsEmptyState({ onCreate }: EmptyStateProps) {
  return (
    <div className="rounded-2xl border border-dashed border-line bg-canvas-muted/40 px-6 py-16 text-center">
      <h2 className="font-display text-2xl text-ink">No projects yet</h2>
      <p className="mx-auto mt-2 max-w-md text-sm text-ink-muted">
        Create your first ExplainX project to reserve folders, metadata, and
        configuration. Parsing and rendering arrive in later phases.
      </p>
      <button
        type="button"
        onClick={onCreate}
        className="mt-6 rounded-full bg-accent px-5 py-2.5 text-sm font-semibold text-canvas"
      >
        New project
      </button>
    </div>
  );
}
