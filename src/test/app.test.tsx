import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ReactNode } from 'react';
import { I18nProvider } from '../i18n';
import { LanguageSelector } from '../components/Header';
import { UploadPage } from '../pages/UploadPage';
import { ReportPage } from '../pages/ReportPage';
import { ParameterDetail } from '../components/report/ParameterDetail';
import { addSessionReport } from '../services/session';
import * as api from '../services/api';
import { EXTRACTION, INSIGHTS, PARAMS, REPORT_ID, TOKEN, explanation } from './fixtures';

vi.mock('../services/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../services/api')>();
  return {
    ...actual,
    getHealth: vi.fn(),
    uploadReport: vi.fn(),
    extractReport: vi.fn(),
    getReport: vi.fn(),
    explainReport: vi.fn(),
    getInsights: vi.fn(),
    askQuestion: vi.fn(),
    compareReports: vi.fn(),
    downloadSummaryPdf: vi.fn(),
    deleteReport: vi.fn(),
  };
});

const mocked = vi.mocked(api);

function wrap(ui: ReactNode, initial: 'en' | 'hi' | 'mr' = 'en') {
  return render(
    <I18nProvider initial={initial}>
      <LanguageSelector />
      {ui}
    </I18nProvider>,
  );
}

function openReport() {
  addSessionReport({ reportId: REPORT_ID, token: TOKEN, fileName: EXTRACTION.fileName!, addedAt: Date.now() });
  mocked.getReport.mockResolvedValue(EXTRACTION);
  mocked.getInsights.mockResolvedValue(INSIGHTS);
  return wrap(<ReportPage reportId={REPORT_ID} retentionHours={24} onUploadNew={() => {}} />);
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('upload flow', () => {
  it('uploads, extracts and opens the report', async () => {
    const user = userEvent.setup();
    const onDone = vi.fn();
    mocked.uploadReport.mockResolvedValue({ reportId: REPORT_ID, fileName: 'r.pdf', status: 'uploaded', message: '', accessToken: TOKEN, retentionHours: 24 });
    mocked.extractReport.mockResolvedValue(EXTRACTION);
    wrap(<UploadPage onDone={onDone} retentionHours={24} ocrAvailable />);

    await user.upload(screen.getByLabelText('browse files'), new File(['%PDF-1.4'], 'r.pdf', { type: 'application/pdf' }));
    expect(screen.getByText('r.pdf')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Analyze report' }));

    await waitFor(() => expect(onDone).toHaveBeenCalledWith(REPORT_ID));
    expect(mocked.extractReport).toHaveBeenCalledWith({ reportId: REPORT_ID, token: TOKEN });
    expect(JSON.parse(window.sessionStorage.getItem('medexplain.reports')!)[0].token).toBe(TOKEN);
  });

  it('rejects unsupported files before uploading', async () => {
    const user = userEvent.setup({ applyAccept: false });
    wrap(<UploadPage onDone={vi.fn()} retentionHours={24} ocrAvailable />);
    await user.upload(screen.getByLabelText('browse files'), new File(['x'], 'notes.txt', { type: 'text/plain' }));
    expect(screen.getByRole('alert')).toHaveTextContent('This file type is not supported');
    expect(mocked.uploadReport).not.toHaveBeenCalled();
  });

  it('shows server errors clearly', async () => {
    const user = userEvent.setup();
    mocked.uploadReport.mockRejectedValue(new api.ApiError('Network error', 'network'));
    wrap(<UploadPage onDone={vi.fn()} retentionHours={24} ocrAvailable />);
    await user.upload(screen.getByLabelText('browse files'), new File(['%PDF'], 'r.pdf', { type: 'application/pdf' }));
    await user.click(screen.getByRole('button', { name: 'Analyze report' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Cannot reach the MedExplain server');
  });
});

describe('report dashboard', () => {
  it('shows results, stats and empty explanation state', async () => {
    openReport();
    expect(await screen.findByRole('heading', { name: EXTRACTION.fileName! })).toBeInTheDocument();
    expect(screen.getAllByText('Hemoglobin').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Explain my results').length).toBeGreaterThan(0);
  });

  it('loads AI explanations and labels them as AI', async () => {
    const user = userEvent.setup();
    mocked.explainReport.mockResolvedValue(explanation('en', 'ai'));
    openReport();
    await user.click(await screen.findByRole('button', { name: 'Explain my results' }));
    expect(await screen.findByText('Two results on this report are below the printed range.')).toBeInTheDocument();
    expect(mocked.explainReport).toHaveBeenCalledWith({ reportId: REPORT_ID, token: TOKEN }, 'en', false);
    expect(screen.getAllByText(/Written by Gemini AI/).length).toBeGreaterThan(0);
  });

  it('clearly marks fallback content', async () => {
    const user = userEvent.setup();
    mocked.explainReport.mockResolvedValue(explanation('en', 'fallback'));
    openReport();
    await user.click(await screen.findByRole('button', { name: 'Explain my results' }));
    expect(await screen.findByText('The AI service could not be reached.')).toBeInTheDocument();
    expect(screen.getAllByText(/Automatic summary/).length).toBeGreaterThan(0);
  });

  it('shows an error with retry when explanations fail', async () => {
    const user = userEvent.setup();
    mocked.explainReport.mockRejectedValueOnce(new api.ApiError('boom', 'server', 500)).mockResolvedValueOnce(explanation());
    openReport();
    await user.click(await screen.findByRole('button', { name: 'Explain my results' }));
    expect(await screen.findByText('Explanations could not be generated.')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Try again' }));
    expect(await screen.findByText('Two results on this report are below the printed range.')).toBeInTheDocument();
  });

  it('switching language translates the UI and re-requests explanations in that language', async () => {
    const user = userEvent.setup();
    mocked.explainReport.mockImplementation(async (_auth, language) => explanation(language));
    openReport();
    await user.click(await screen.findByRole('button', { name: 'Explain my results' }));
    await screen.findByText('Two results on this report are below the printed range.');

    await user.selectOptions(screen.getByRole('combobox', { name: 'Language' }), 'hi');
    expect(await screen.findByText('इस रिपोर्ट में दो परिणाम सीमा से कम हैं।')).toBeInTheDocument();
    expect(mocked.explainReport).toHaveBeenLastCalledWith({ reportId: REPORT_ID, token: TOKEN }, 'hi', false);
    expect(screen.getByRole('tab', { name: /परिणाम/ })).toBeInTheDocument();
    expect(document.documentElement.lang).toBe('hi');
    await waitFor(() => expect(mocked.getInsights).toHaveBeenLastCalledWith(expect.anything(), 'hi'));
  });

  it('downloads the PDF in the selected language', async () => {
    const user = userEvent.setup();
    mocked.downloadSummaryPdf.mockResolvedValue(new Blob(['%PDF'], { type: 'application/pdf' }));
    const createUrl = vi.fn(() => 'blob:x');
    Object.assign(URL, { createObjectURL: createUrl, revokeObjectURL: vi.fn() });
    openReport();
    await user.click(await screen.findByRole('button', { name: 'Download PDF' }));
    await waitFor(() => expect(mocked.downloadSummaryPdf).toHaveBeenCalledWith({ reportId: REPORT_ID, token: TOKEN }, 'en'));
    expect(createUrl).toHaveBeenCalled();
  });

  it('reports PDF errors', async () => {
    const user = userEvent.setup();
    mocked.downloadSummaryPdf.mockRejectedValue(new api.ApiError('fail', 'server', 500));
    openReport();
    await user.click(await screen.findByRole('button', { name: 'Download PDF' }));
    expect(await screen.findByText('The PDF could not be created. Please try again.')).toBeInTheDocument();
  });

  it('chat keeps the conversation across tab switches and sends history', async () => {
    const user = userEvent.setup();
    mocked.askQuestion.mockResolvedValue({ answer: 'Your Ferritin is below the range.', source: 'ai', citations: [], usedParameters: ['Ferritin'], evidenceStatus: 'limited' });
    openReport();
    await user.click(await screen.findByRole('tab', { name: /Ask/ }));
    const box = screen.getByRole('textbox', { name: /Ask a question/ });
    await user.type(box, 'What about my ferritin?{Enter}');
    expect(await screen.findByText('Your Ferritin is below the range.')).toBeInTheDocument();

    await user.click(screen.getByRole('tab', { name: /Results/ }));
    await user.click(screen.getByRole('tab', { name: /Ask/ }));
    expect(screen.getByText('Your Ferritin is below the range.')).toBeInTheDocument();

    await user.type(screen.getByRole('textbox', { name: /Ask a question/ }), 'Why?{Enter}');
    await waitFor(() => expect(mocked.askQuestion).toHaveBeenCalledTimes(2));
    const [, question, history, language] = mocked.askQuestion.mock.calls[1];
    expect(question).toBe('Why?');
    expect(history).toEqual([
      { role: 'user', content: 'What about my ferritin?' },
      { role: 'assistant', content: 'Your Ferritin is below the range.' },
    ]);
    expect(language).toBe('en');
  });

  it('chat shows an error with retry', async () => {
    const user = userEvent.setup();
    mocked.askQuestion.mockRejectedValueOnce(new api.ApiError('x', 'rate_limited', 429)).mockResolvedValueOnce({ answer: 'Answer after retry', source: 'fallback', notice: 'AI unavailable', citations: [], usedParameters: [], evidenceStatus: 'none' });
    openReport();
    await user.click(await screen.findByRole('tab', { name: /Ask/ }));
    await user.click(screen.getByRole('button', { name: 'Which results should I discuss with my doctor?' }));
    expect(await screen.findByText(/Too many requests/)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Try again' }));
    expect(await screen.findByText('Answer after retry')).toBeInTheDocument();
    expect(screen.getByText('Automatic answer')).toBeInTheDocument();
  });

  it('insights tab shows relationships, caution and doctor questions', async () => {
    const user = userEvent.setup();
    openReport();
    await user.click(await screen.findByRole('tab', { name: /Insights/ }));
    const panel = screen.getByRole('tabpanel', { name: /Insights/ });
    expect(within(panel).getByText('Iron is needed to make hemoglobin.')).toBeInTheDocument();
    expect(within(panel).getByText('This is an observed pattern in your report, not a diagnosis.')).toBeInTheDocument();
    expect(within(panel).getByText('My Ferritin was 9 ng/mL. What could this mean for me?')).toBeInTheDocument();
  });

  it('shows an empty state when the report is not in this session', () => {
    wrap(<ReportPage reportId="rep_ffffffffffffffffffffffff" retentionHours={24} onUploadNew={() => {}} />);
    expect(screen.getByText('No report open')).toBeInTheDocument();
    expect(mocked.getReport).not.toHaveBeenCalled();
  });
});

describe('sources and explainability', () => {
  it('distinguishes report data, AI text and clickable sources', async () => {
    const user = userEvent.setup();
    const exp = explanation('en', 'ai');
    const sources = new Map(exp.sources.map((s) => [s.id, s]));
    wrap(<ParameterDetail parameter={PARAMS[0]} explanation={exp.explanations[0]} sourcesById={sources} numbering={new Map([['mlp-hemoglobin-2', 1]])} />);

    expect(screen.getByText('From your report')).toBeInTheDocument();
    expect(screen.getByText('AI explanation')).toBeInTheDocument();
    expect(screen.getByText('[1]')).toBeInTheDocument();
    const link = screen.getByRole('link', { name: /Hemoglobin Test/ });
    expect(link).toHaveAttribute('href', 'https://medlineplus.gov/lab-tests/hemoglobin-test/');
    expect(link).toHaveAttribute('rel', expect.stringContaining('noopener'));

    await user.click(screen.getByText('Why this explanation?'));
    expect(screen.getByText('11.2 < 12')).toBeInTheDocument();
    expect(screen.getByText('Reference ranges differ between laboratories.')).toBeInTheDocument();
  });
});