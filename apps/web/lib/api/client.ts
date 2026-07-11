/**
 * Typed API client stub — frontend talks ONLY to FastAPI /api/v1.
 * No direct model or filesystem access.
 */

import type { ApiSuccess } from "@/types/api";

function getBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";
}

export async function apiGet<T>(path: string): Promise<ApiSuccess<T>> {
  const response = await fetch(`${getBaseUrl()}${path}`, {
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }
  return (await response.json()) as ApiSuccess<T>;
}

export async function fetchHealth(): Promise<
  ApiSuccess<{ status: string; uptime_sec: number; version: string; env: string }>
> {
  // Health is also mounted at /api/v1/health
  return apiGet("/health");
}
