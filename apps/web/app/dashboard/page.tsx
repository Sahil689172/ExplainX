"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { useEffect, useState } from "react";

import { listProjects } from "@/lib/api/client";
import { useUiStore } from "@/lib/store/ui-store";
import type { ProjectSummary } from "@/types/project";

export default function DashboardPage() {
  const apiBaseUrl = useUiStore((s) => s.apiBaseUrl);
  const [recent, setRecent] = useState<ProjectSummary[]>([]);

  useEffect(() => {
    void listProjects({ recent: true, limit: 5 })
      .then((res) => setRecent(res.data.items))
      .catch(() => setRecent([]));
  }, []);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-3xl font-semibold text-ink md:text-4xl">
          Workspace
        </h1>
        <p className="mt-2 max-w-2xl text-ink-muted">
          Manage local ExplainX projects. Generation and rendering arrive in
          later phases.
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
            Create, open, rename, duplicate, archive, and export project
            packages.
          </p>
          <Link
            href="/dashboard/projects"
            className="mt-4 inline-flex text-sm font-medium text-accent hover:text-accent-strong"
          >
            Open projects →
          </Link>
          {recent.length > 0 ? (
            <ul className="mt-4 space-y-1 text-sm text-ink-muted">
              {recent.map((p) => (
                <li key={p.project_id}>
                  <Link
                    href={`/dashboard/projects/${p.project_id}`}
                    className="hover:text-accent"
                  >
                    {p.title}
                  </Link>
                </li>
              ))}
            </ul>
          ) : null}
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
