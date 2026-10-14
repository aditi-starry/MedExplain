/**
 * Reports opened in this browser tab (sessionStorage only).
 *
 * Access tokens are kept here so a page reload or a report comparison works
 * within the same tab. Nothing is kept after the tab is closed, and nothing is
 * written to localStorage, so other people using the same browser later cannot
 * reopen the reports.
 */
export interface SessionReport {
  reportId: string;
  token: string;
  fileName: string;
  reportDate?: string | null;
  addedAt: number;
}

const KEY = 'medexplain.reports';

export function listSessionReports(): SessionReport[] {
  try {
    const raw = window.sessionStorage.getItem(KEY);
    const parsed = raw ? (JSON.parse(raw) as SessionReport[]) : [];
    return Array.isArray(parsed) ? parsed.filter((r) => r && r.reportId && r.token) : [];
  } catch {
    return [];
  }
}

function save(reports: SessionReport[]): void {
  try {
    window.sessionStorage.setItem(KEY, JSON.stringify(reports.slice(-10)));
  } catch {
    // Storage unavailable: reports simply are not remembered across reloads
  }
}

export function addSessionReport(report: SessionReport): void {
  save([...listSessionReports().filter((r) => r.reportId !== report.reportId), report]);
}

export function updateSessionReport(reportId: string, patch: Partial<SessionReport>): void {
  save(listSessionReports().map((r) => (r.reportId === reportId ? { ...r, ...patch } : r)));
}

export function getSessionReport(reportId: string): SessionReport | undefined {
  return listSessionReports().find((r) => r.reportId === reportId);
}

export function removeSessionReport(reportId: string): void {
  save(listSessionReports().filter((r) => r.reportId !== reportId));
}