"""Project domain types."""

export type ProjectStatus =
  | "draft"
  | "queued"
  | "running"
  | "completed"
  | "failed"
  | "cancelled"
  | "archived";

export type ProjectPhase =
  | "foundation"
  | "document"
  | "knowledge"
  | "content"
  | "presentation"
  | "animation"
  | "multilingual"
  | "rendering"
  | "completed";

export interface ProjectSettings {
  export_width: number;
  export_height: number;
  fps: number;
  quality_profile: string;
  burn_in_subtitles: boolean;
  subtitle_formats: string[];
  speaking_rate: number;
  max_scenes: number | null;
}

export interface ProjectSummary {
  project_id: string;
  title: string;
  description: string | null;
  status: ProjectStatus;
  current_phase: ProjectPhase;
  theme_id: string;
  source_language_code: string;
  target_language_code: string;
  updated_at: string;
  created_at: string;
  actual_duration_sec: number | null;
  thumbnail_url: string | null;
}

export interface ProjectDetail extends ProjectSummary {
  source_type: string;
  source_topic: string | null;
  source_path: string | null;
  voice_id: string | null;
  difficulty: string | null;
  project_root: string;
  assets_directory: string;
  output_directory: string;
  project_version: string;
  dsl_version: string;
  schema_version: string;
  settings: ProjectSettings;
  directories: Record<string, string>;
  configuration: Record<string, unknown>;
}

export interface ProjectListData {
  items: ProjectSummary[];
  page: {
    limit: number;
    next_cursor: string | null;
    total_estimate: number;
  };
}

export interface ProjectCreateInput {
  title: string;
  description?: string;
  source_type?: string;
  source_topic?: string;
  theme_id?: string;
  source_language_code?: string;
  target_language_code?: string;
  difficulty?: string;
}
