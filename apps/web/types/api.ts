export interface ApiMeta {
  request_id: string;
  api_version: string;
  timestamp: string;
}

export interface ApiSuccess<T> {
  success: true;
  data: T;
  meta: ApiMeta;
}

export interface ApiErrorBody {
  code: string;
  message: string;
  details: Record<string, unknown>;
  retriable: boolean;
}

export interface ApiError {
  success: false;
  error: ApiErrorBody;
  meta: ApiMeta;
}
