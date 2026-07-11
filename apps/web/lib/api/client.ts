/**
 * Typed API client — frontend talks ONLY to FastAPI /api/v1.
 */

import type { ApiError, ApiSuccess } from "@/types/api";
import type {
  ProjectCreateInput,
  ProjectDetail,
  ProjectListData,
} from "@/types/project";

function getBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";
}

async function parseJson<T>(response: Response): Promise<ApiSuccess<T>> {
  const body = (await response.json()) as ApiSuccess<T> | ApiError;
  if (!response.ok || !body.success) {
    const message =
      !body.success && "error" in body
        ? body.error.message
        : `API request failed: ${response.status}`;
    const code =
      !body.success && "error" in body ? body.error.code : "HTTP_ERROR";
    throw new Error(`${code}: ${message}`);
  }
  return body;
}

export async function apiGet<T>(path: string): Promise<ApiSuccess<T>> {
  const response = await fetch(`${getBaseUrl()}${path}`, {
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  return parseJson<T>(response);
}

export async function apiSend<T>(
  path: string,
  method: string,
  body?: unknown,
): Promise<ApiSuccess<T>> {
  const response = await fetch(`${getBaseUrl()}${path}`, {
    method,
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: "no-store",
  });
  return parseJson<T>(response);
}

export async function fetchHealth(): Promise<
  ApiSuccess<{ status: string; uptime_sec: number; version: string; env: string }>
> {
  return apiGet("/health");
}

export async function listProjects(params?: {
  q?: string;
  status?: string;
  recent?: boolean;
  limit?: number;
}): Promise<ApiSuccess<ProjectListData>> {
  const search = new URLSearchParams();
  if (params?.q) search.set("q", params.q);
  if (params?.status) search.set("status", params.status);
  if (params?.recent) search.set("recent", "true");
  if (params?.limit) search.set("limit", String(params.limit));
  const qs = search.toString();
  return apiGet(`/projects${qs ? `?${qs}` : ""}`);
}

export async function getProject(
  projectId: string,
): Promise<ApiSuccess<ProjectDetail>> {
  return apiGet(`/projects/${projectId}`);
}

export async function createProject(
  input: ProjectCreateInput,
): Promise<ApiSuccess<ProjectDetail>> {
  return apiSend("/projects", "POST", {
    source_type: "topic",
    theme_id: "notebooklm",
    source_language_code: "en",
    target_language_code: "en",
    difficulty: "intermediate",
    ...input,
  });
}

export async function renameProject(
  projectId: string,
  title: string,
): Promise<ApiSuccess<ProjectDetail>> {
  return apiSend(`/projects/${projectId}/rename`, "POST", { title });
}

export async function deleteProject(
  projectId: string,
  mode: "soft" | "hard" = "soft",
): Promise<ApiSuccess<{ project_id: string; deleted: boolean; mode: string }>> {
  const confirm = mode === "hard" ? "&confirm=true" : "";
  return apiSend(`/projects/${projectId}?mode=${mode}${confirm}`, "DELETE");
}

export async function duplicateProject(
  projectId: string,
  title?: string,
): Promise<ApiSuccess<ProjectDetail>> {
  return apiSend(`/projects/${projectId}/duplicate`, "POST", title ? { title } : {});
}

export async function archiveProject(
  projectId: string,
): Promise<ApiSuccess<ProjectDetail>> {
  return apiSend(`/projects/${projectId}/archive`, "POST");
}

export async function saveProject(
  projectId: string,
): Promise<ApiSuccess<ProjectDetail>> {
  return apiSend(`/projects/${projectId}/save`, "POST");
}
