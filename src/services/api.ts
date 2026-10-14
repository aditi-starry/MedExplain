/**
 * API client for the MedExplain FastAPI backend.
 *
 * Every report request carries the report's access token in the X-Report-Token
 * header. The token is returned once at upload and kept only in this browser tab
 * (sessionStorage), never in the URL.
 */
import type { Language } from '../i18n/types';
import type {
  ChatResponse,
  ChatTurn,
  ComparisonResponse,
  ExplanationResponse,
  HealthResponse,
  InsightsResponse,
  ReportExtraction,
  UploadResponse,
} from '../types/medical';

export const API_BASE_URL: string = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/+$/, '');

export type ApiErrorKind = 'network' | 'not_found' | 'rate_limited' | 'bad_request' | 'server';

export class ApiError extends Error {
  status?: number;
  kind: ApiErrorKind;

  constructor(message: string, kind: ApiErrorKind, status?: number) {
    super(message);
    this.name = 'ApiError';
    this.kind = kind;
    this.status = status;
  }
}

export interface ReportAuth {
  reportId: string;
  token: string;
}

function kindForStatus(status: number): ApiErrorKind {
  if (status === 404) return 'not_found';
  if (status === 429) return 'rate_limited';
  if (status >= 400 && status < 500) return 'bad_request';
  return 'server';
}

async function request<T>(path: string, init: RequestInit = {}, auth?: ReportAuth, timeoutMs = 90_000): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set('Accept', 'application/json');
  if (auth) headers.set('X-Report-Token', auth.token);

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers, signal: controller.signal });
  } catch {
    throw new ApiError('Network error', 'network');
  } finally {
    clearTimeout(timer);
  }

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = typeof body?.detail === 'string' ? body.detail : `Request failed (${response.status})`;
    throw new ApiError(detail, kindForStatus(response.status), response.status);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

function jsonInit(method: string, body: unknown): RequestInit {
  return { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) };
}

export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>('/api/health', {}, undefined, 60_000);
}

export function uploadReport(file: File): Promise<UploadResponse> {
  const form = new FormData();
  form.append('file', file);
  return request<UploadResponse>('/api/reports/upload', { method: 'POST', body: form });
}

export function extractReport(auth: ReportAuth): Promise<ReportExtraction> {
  return request<ReportExtraction>(`/api/reports/${encodeURIComponent(auth.reportId)}/extract`, { method: 'POST' }, auth, 180_000);
}

export function getReport(auth: ReportAuth): Promise<ReportExtraction> {
  return request<ReportExtraction>(`/api/reports/${encodeURIComponent(auth.reportId)}`, {}, auth);
}

export function explainReport(auth: ReportAuth, language: Language, refresh = false): Promise<ExplanationResponse> {
  return request<ExplanationResponse>(
    `/api/reports/${encodeURIComponent(auth.reportId)}/explain`,
    jsonInit('POST', { language, refresh }),
    auth,
    120_000,
  );
}

export function getInsights(auth: ReportAuth, language: Language): Promise<InsightsResponse> {
  return request<InsightsResponse>(`/api/reports/${encodeURIComponent(auth.reportId)}/insights?language=${language}`, {}, auth);
}

export function askQuestion(auth: ReportAuth, message: string, history: ChatTurn[], language: Language): Promise<ChatResponse> {
  return request<ChatResponse>(
    `/api/reports/${encodeURIComponent(auth.reportId)}/chat`,
    jsonInit('POST', { message, history: history.slice(-12), language }),
    auth,
    90_000,
  );
}

export function compareReports(current: ReportAuth, previous: ReportAuth): Promise<ComparisonResponse> {
  return request<ComparisonResponse>(
    `/api/reports/${encodeURIComponent(current.reportId)}/compare`,
    jsonInit('POST', { previousReportId: previous.reportId, previousToken: previous.token }),
    current,
  );
}

export async function downloadSummaryPdf(auth: ReportAuth, language: Language): Promise<Blob> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 90_000);
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/reports/${encodeURIComponent(auth.reportId)}/summary.pdf?language=${language}`, {
      headers: { 'X-Report-Token': auth.token },
      signal: controller.signal,
    });
  } catch {
    throw new ApiError('Network error', 'network');
  } finally {
    clearTimeout(timer);
  }
  if (!response.ok) throw new ApiError(`PDF request failed (${response.status})`, kindForStatus(response.status), response.status);
  return response.blob();
}

export function deleteReport(auth: ReportAuth): Promise<void> {
  return request<void>(`/api/reports/${encodeURIComponent(auth.reportId)}`, { method: 'DELETE' }, auth);
}