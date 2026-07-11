"use client";

import { motion } from "framer-motion";
import Link from "next/link";

import { useUiStore } from "@/lib/store/ui-store";

export default function DashboardPage() {
  const apiBaseUrl = useUiStore((s) => s.apiBaseUrl);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-3xl font-semibold text-ink md:text-4xl">
          Workspace
        </h1>
        <p className="mt-2 max-w-2xl text-ink-muted">
          Project creation, generation jobs, and exports will live here. Phase
          1.1 ships the shell only — no pipeline yet.
        </p>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="grid gap-4 md:grid-cols-2"
      >
        <div className="rounded-2xl border border-line bg-canvas-elevated/80 p-6 shadow-panel">
          <h2 className="font-display text-xl text-ink">Projects</h2>
          <p className="mt-2 text-sm text-ink-muted">
            Placeholder library. CRUD arrives with Core Infrastructure Phase
            1.2.
          </p>
          <Link
            href="/dashboard/projects"
            className="mt-4 inline-flex text-sm font-medium text-accent hover:text-accent-strong"
          >
            View projects →
          </Link>
        </div>
        <div className="rounded-2xl border border-line bg-canvas-elevated/80 p-6 shadow-panel">
          <h2 className="font-display text-xl text-ink">API</h2>
          <p className="mt-2 text-sm text-ink-muted">
            Frontend talks only to the local FastAPI control plane.
          </p>
          <p className="mt-4 break-all font-mono text-xs text-ink-faint">
            {apiBaseUrl}
          </p>
        </div>
      </motion.div>
    </div>
  );
}
