"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV = [
  { href: "/dashboard", label: "Overview" },
  { href: "/dashboard/projects", label: "Projects" },
];

type SidebarProps = {
  mobileOpen: boolean;
  onClose: () => void;
};

export function Sidebar({ mobileOpen, onClose }: SidebarProps) {
  const pathname = usePathname();

  const nav = (
    <nav className="flex flex-col gap-1 p-4">
      {NAV.map((item) => {
        const active =
          pathname === item.href ||
          (item.href !== "/dashboard" && pathname.startsWith(item.href));
        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onClose}
            className={`rounded-xl px-3 py-2 text-sm transition ${
              active
                ? "bg-accent/15 text-accent"
                : "text-ink-muted hover:bg-canvas-muted hover:text-ink"
            }`}
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );

  return (
    <>
      <aside className="hidden border-r border-line bg-canvas-elevated/60 md:block">
        <div className="sticky top-0 flex h-screen flex-col">
          <div className="border-b border-line px-5 py-5">
            <Link href="/" className="font-display text-xl font-semibold text-ink">
              ExplainX
            </Link>
            <p className="mt-1 text-xs text-ink-faint">Local workspace</p>
          </div>
          {nav}
          <div className="mt-auto border-t border-line p-4 text-xs text-ink-faint">
            Phase 1.1 foundation
          </div>
        </div>
      </aside>

      {mobileOpen ? (
        <div className="fixed inset-0 z-40 md:hidden">
          <button
            type="button"
            className="absolute inset-0 bg-black/50"
            aria-label="Close navigation"
            onClick={onClose}
          />
          <motion.aside
            initial={{ x: -280 }}
            animate={{ x: 0 }}
            className="relative z-50 flex h-full w-64 flex-col border-r border-line bg-canvas-elevated"
          >
            <div className="border-b border-line px-5 py-5">
              <Link
                href="/"
                className="font-display text-xl font-semibold text-ink"
                onClick={onClose}
              >
                ExplainX
              </Link>
            </div>
            {nav}
          </motion.aside>
        </div>
      ) : null}
    </>
  );
}
