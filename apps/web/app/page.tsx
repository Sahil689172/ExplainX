"use client";

import { motion } from "framer-motion";
import Link from "next/link";

export default function LandingPage() {
  return (
    <main className="relative min-h-screen overflow-hidden bg-hero-glow">
      <div className="mx-auto flex min-h-screen max-w-6xl flex-col px-6 pb-16 pt-8 md:px-10">
        <header className="flex items-center justify-between">
          <span className="font-display text-2xl font-semibold tracking-tight text-ink">
            ExplainX
          </span>
          <Link
            href="/dashboard"
            className="rounded-full border border-line px-4 py-2 text-sm text-ink-muted transition hover:border-accent hover:text-accent"
          >
            Open dashboard
          </Link>
        </header>

        <section className="flex flex-1 flex-col justify-center gap-8 py-16 md:max-w-3xl">
          <motion.p
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="text-sm uppercase tracking-[0.2em] text-accent"
          >
            Offline presentation → video
          </motion.p>
          <motion.h1
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.55, delay: 0.05 }}
            className="font-display text-5xl font-semibold leading-[1.05] tracking-tight text-ink md:text-7xl"
          >
            ExplainX
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.55, delay: 0.12 }}
            className="max-w-xl text-lg text-ink-muted md:text-xl"
          >
            Turn educational documents into clear, narrated explainer videos —
            locally, offline, without generative video models.
          </motion.p>
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.55, delay: 0.18 }}
            className="flex flex-wrap gap-3"
          >
            <Link
              href="/dashboard"
              className="rounded-full bg-accent px-6 py-3 text-sm font-semibold text-canvas transition hover:bg-accent-strong"
            >
              Enter workspace
            </Link>
            <a
              href="https://github.com"
              className="rounded-full border border-line px-6 py-3 text-sm text-ink-muted transition hover:border-ink-faint hover:text-ink"
              onClick={(e) => e.preventDefault()}
            >
              Architecture first
            </a>
          </motion.div>
        </section>

        <footer className="text-sm text-ink-faint">
          Phase 1.1 foundation — agents and rendering arrive later.
        </footer>
      </div>
    </main>
  );
}
