"use client";

import { useState } from "react";
import type { FormEvent } from "react";

type NewProjectDialogProps = {
  open: boolean;
  onClose: () => void;
  onCreate: (input: {
    title: string;
    description?: string;
    source_topic?: string;
    theme_id?: string;
  }) => Promise<void>;
};

export function NewProjectDialog({
  open,
  onClose,
  onCreate,
}: NewProjectDialogProps) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [topic, setTopic] = useState("");
  const [themeId, setThemeId] = useState("notebooklm");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (!open) return null;

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await onCreate({
        title: title.trim(),
        description: description.trim() || undefined,
        source_topic: topic.trim() || title.trim(),
        theme_id: themeId,
      });
      setTitle("");
      setDescription("");
      setTopic("");
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create project");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="w-full max-w-lg rounded-2xl border border-line bg-canvas-elevated p-6 shadow-panel">
        <h2 className="font-display text-2xl text-ink">New project</h2>
        <p className="mt-1 text-sm text-ink-muted">
          Create a local ExplainX project shell. AI pipeline comes later.
        </p>
        <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
          <label className="block text-sm text-ink-muted">
            Name
            <input
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="mt-1 w-full rounded-xl border border-line bg-canvas px-3 py-2 text-ink outline-none focus:border-accent"
              placeholder="Binary Search Explained"
              maxLength={120}
            />
          </label>
          <label className="block text-sm text-ink-muted">
            Topic
            <input
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              className="mt-1 w-full rounded-xl border border-line bg-canvas px-3 py-2 text-ink outline-none focus:border-accent"
              placeholder="Defaults to project name"
              maxLength={500}
            />
          </label>
          <label className="block text-sm text-ink-muted">
            Description
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="mt-1 w-full rounded-xl border border-line bg-canvas px-3 py-2 text-ink outline-none focus:border-accent"
              rows={3}
              maxLength={2000}
            />
          </label>
          <label className="block text-sm text-ink-muted">
            Theme
            <select
              value={themeId}
              onChange={(e) => setThemeId(e.target.value)}
              className="mt-1 w-full rounded-xl border border-line bg-canvas px-3 py-2 text-ink outline-none focus:border-accent"
            >
              <option value="notebooklm">NotebookLM</option>
              <option value="whiteboard">Whiteboard</option>
              <option value="corporate">Corporate</option>
              <option value="minimal">Minimal</option>
              <option value="comic">Comic</option>
              <option value="dark">Dark</option>
            </select>
          </label>
          {error ? <p className="text-sm text-red-400">{error}</p> : null}
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-full border border-line px-4 py-2 text-sm text-ink-muted"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="rounded-full bg-accent px-4 py-2 text-sm font-semibold text-canvas disabled:opacity-60"
            >
              {submitting ? "Creating…" : "Create"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
