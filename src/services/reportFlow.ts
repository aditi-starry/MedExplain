import { ApiError, extractReport, uploadReport } from './api';
import type { ReportAuth } from './api';
import { addSessionReport } from './session';
import type { ReportExtraction } from '../types/medical';
import type { TFunction } from '../i18n';

export type UploadStep = 'upload' | 'extract' | 'done';

export const MAX_UPLOAD_MB = 10;
const ALLOWED = ['pdf', 'png', 'jpg', 'jpeg'];

/** Client-side pre-check (the server validates again). Returns an error message or null. */
export function validateFile(file: File, t: TFunction): string | null {
  const ext = file.name.split('.').pop()?.toLowerCase() ?? '';
  if (!ALLOWED.includes(ext)) return t('upload.err_format');
  if (file.size > MAX_UPLOAD_MB * 1024 * 1024) return t('upload.err_size', { max: MAX_UPLOAD_MB });
  return null;
}

/** Uploads a report, extracts it, and remembers it for this browser tab. */
export async function uploadAndExtract(
  file: File,
  onStep?: (step: UploadStep) => void,
): Promise<{ auth: ReportAuth; extraction: ReportExtraction }> {
  onStep?.('upload');
  const uploaded = await uploadReport(file);
  const auth = { reportId: uploaded.reportId, token: uploaded.accessToken };
  addSessionReport({ reportId: auth.reportId, token: auth.token, fileName: uploaded.fileName, addedAt: Date.now() });
  onStep?.('extract');
  const extraction = await extractReport(auth);
  addSessionReport({
    reportId: auth.reportId,
    token: auth.token,
    fileName: uploaded.fileName,
    reportDate: extraction.reportDate ?? null,
    addedAt: Date.now(),
  });
  onStep?.('done');
  return { auth, extraction };
}

export async function loadSampleFile(path: string, name: string): Promise<File> {
  const response = await fetch(path);
  if (!response.ok) throw new ApiError('Sample not available', 'not_found', response.status);
  const blob = await response.blob();
  return new File([blob], name, { type: 'application/pdf' });
}

export function errorMessage(error: unknown, t: TFunction): string {
  if (error instanceof ApiError) {
    if (error.kind === 'network') return t('common.error_network');
    if (error.kind === 'not_found') return t('common.error_not_found');
    if (error.kind === 'rate_limited') return t('common.error_rate');
    if (error.kind === 'bad_request' && error.message) return error.message;
  }
  return t('common.error_generic');
}