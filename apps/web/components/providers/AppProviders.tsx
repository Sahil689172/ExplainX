"use client";

import { useEffect } from "react";

import { useUiStore } from "@/lib/store/ui-store";

export function AppProviders({ children }: { children: React.ReactNode }) {
  const hydrateFromEnv = useUiStore((s) => s.hydrateFromEnv);

  useEffect(() => {
    hydrateFromEnv();
  }, [hydrateFromEnv]);

  return <>{children}</>;
}
