"use client";

type DeleteConfirmDialogProps = {
  open: boolean;
  projectTitle: string;
  onCancel: () => void;
  onConfirm: () => Promise<void>;
};

export function DeleteConfirmDialog({
  open,
  projectTitle,
  onCancel,
  onConfirm,
}: DeleteConfirmDialogProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="w-full max-w-md rounded-2xl border border-line bg-canvas-elevated p-6 shadow-panel">
        <h2 className="font-display text-xl text-ink">Delete project?</h2>
        <p className="mt-2 text-sm text-ink-muted">
          Soft-delete <span className="text-ink">{projectTitle}</span>. You can
          recover from backups later; hard delete is available via API.
        </p>
        <div className="mt-6 flex justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            className="rounded-full border border-line px-4 py-2 text-sm text-ink-muted"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={() => void onConfirm()}
            className="rounded-full bg-red-500/90 px-4 py-2 text-sm font-semibold text-white"
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  );
}
