"use client";

import { useState } from "react";

import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";

export function DashboardShell({ children }: { children: React.ReactNode }) {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  return (
    <div className="min-h-screen md:grid md:grid-cols-[240px_1fr]">
      <Sidebar
        mobileOpen={mobileNavOpen}
        onClose={() => setMobileNavOpen(false)}
      />
      <div className="flex min-h-screen flex-col">
        <Header onMenuClick={() => setMobileNavOpen(true)} />
        <main className="flex-1 px-4 py-6 md:px-8 md:py-8">{children}</main>
      </div>
    </div>
  );
}
