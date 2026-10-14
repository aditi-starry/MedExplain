import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { AlertTriangle, CalendarDays, Download, FileText, FileX2, Layers, ListChecks, MessageCircle, GitCompareArrows, ScanLine, Trash2, Upload } from 'lucide-react';
import { useI18n } from '../i18n';
import type { Language, TranslationKey } from '../i18n/types';
import { deleteReport, downloadSummaryPdf, explainReport, getInsights, getReport } from '../services/api';
import type { ReportAuth } from '../services/api';
import { errorMessage } from '../services/reportFlow';
import { getSessionReport, removeSessionReport } from '../services/session';
import type { ExplanationResponse, InsightsResponse, ParameterExplanation, ReportExtraction, SourceCitation } from '../types/medical';
import { formatDate, isOutside } from '../utils/format';
import { Alert, Button, Card, EmptyState, Skeleton } from '../components/ui';
import { AiSummary } from '../components/report/AiSummary';
import { ChatPanel } from '../components/report/ChatPanel';
import { ComparePanel } from '../components/report/ComparePanel';
import { InsightsPanel } from '../components/report/InsightsPanel';
import { ResultsPanel } from '../components/report/ResultsPanel';

type Tab = 'results' | 'insights' | 'chat' | 'compare';
const TABS: { id: Tab; label: TranslationKey; icon: ReactNode }[] = [
  { id: 'results', label: 'tabs.results', icon: <ListChecks className="h-4 w-4" aria-hidden /> },
  { id: 'insights', label: 'tabs.insights', icon: <Layers className="h-4 w-4" aria-hidden /> },
  { id: 'chat', label: 'tabs.chat', icon: <MessageCircle className="h-4 w-4" aria-hidden /> },
  { id: 'compare', label: 'tabs.compare', icon: <GitCompareArrows className="h-4 w-4" aria-hidden /> },
];

interface ReportPageProps {
  reportId: string;
  retentionHours: number;
  onUploadNew: () => void;
}

function Stat({ label, value, tone }: { label: string; value: number; tone: string }) {
  return (
    <div className="rounded-2xl border border-slate-200/80 bg-white px-4 py-3 shadow-card">
      <p className="text-xs font-medium text-slate-500">{label}</p>
      <p className={`font-display text-2xl font-extrabold ${tone}`}>{value}</p>
    </div>
  );
}

export function ReportPage({ reportId, retentionHours, onUploadNew }: ReportPageProps) {
  const { t, language } = useI18n();
  const session = getSessionReport(reportId);
  const token = session?.token;
  const auth: ReportAuth | null = useMemo(() => (token ? { reportId, token } : null), [reportId, token]);

  const [extraction, setExtraction] = useState<ReportExtraction | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>('results');
  const [explanations, setExplanations] = useState<Partial<Record<Language, ExplanationResponse>>>({});
  const [explaining, setExplaining] = useState(false);
  const [explainError, setExplainError] = useState<string | null>(null);
  const [insights, setInsights] = useState<InsightsResponse | null>(null);
  const [insightsLoading, setInsightsLoading] = useState(false);
  const [pdfBusy, setPdfBusy] = useState(false);
  const [pdfError, setPdfError] = useState<string | null>(null);
  const [deleted, setDeleted] = useState(false);
  const requestedAi = useRef(false);

  useEffect(() => {
    if (!auth) return;
    let cancelled = false;
    setExtraction(null);
    setLoadError(null);
    setExplanations({});
    requestedAi.current = false;
    getReport(auth)
      .then((data) => !cancelled && setExtraction(data))
      .catch((err) => !cancelled && setLoadError(errorMessage(err, t)));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [auth]);

  useEffect(() => {
    if (!auth || !extraction) return;
    let cancelled = false;
    setInsightsLoading(true);
    getInsights(auth, language)
      .then((data) => !cancelled && setInsights(data))
      .catch(() => !cancelled && setInsights(null))
      .finally(() => !cancelled && setInsightsLoading(false));
    return () => {
      cancelled = true;
    };
  }, [auth, extraction, language]);

  const generate = useCallback(
    async (refresh: boolean) => {
      if (!auth) return;
      requestedAi.current = true;
      setExplaining(true);
      setExplainError(null);
      try {
        const data = await explainReport(auth, language, refresh);
        setExplanations((prev) => ({ ...prev, [language]: data }));
      } catch (err) {
        setExplainError(errorMessage(err, t));
      } finally {
        setExplaining(false);
      }
    },
    [auth, language, t],
  );

  // Keep the chosen language consistent: once explanations were requested, fetch them in the new language too
  useEffect(() => {
    if (requestedAi.current && !explanations[language] && !explaining) void generate(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [language]);

  const explanation = explanations[language] ?? null;
  const explanationMap = useMemo(() => {
    const map = new Map<string, ParameterExplanation>();
    explanation?.explanations.forEach((e) => map.set(e.name, e));
    return map;
  }, [explanation]);

  const sourcesById = useMemo(() => {
    const map = new Map<string, SourceCitation>();
    [...(insights?.sources ?? []), ...(explanation?.sources ?? [])].forEach((s) => map.set(s.id, s));
    return map;
  }, [insights, explanation]);

  const numbering = useMemo(() => {
    const map = new Map<string, number>();
    (explanation?.sources ?? []).forEach((s, i) => map.set(s.id, i + 1));
    return map;
  }, [explanation]);

  const downloadPdf = async () => {
    if (!auth) return;
    setPdfBusy(true);
    setPdfError(null);
    try {
      const blob = await downloadSummaryPdf(auth, language);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `MedExplain_Summary_${language}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch {
      setPdfError(t('report.pdf_error'));
    } finally {
      setPdfBusy(false);
    }
  };

  const remove = async () => {
    if (!auth || !window.confirm(t('report.delete_confirm'))) return;
    try {
      await deleteReport(auth);
    } catch {
      // Already gone on the server is fine; forget it locally either way
    }
    removeSessionReport(reportId);
    setDeleted(true);
  };

  if (deleted || !auth) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-16 sm:px-6">
        <Card>
          <EmptyState
            icon={<FileX2 className="h-6 w-6" />}
            title={deleted ? t('report.deleted') : t('report.empty_title')}
            body={deleted ? undefined : t('report.empty_body')}
            action={<Button icon={<Upload className="h-4 w-4" aria-hidden />} onClick={onUploadNew}>{t('home.cta_upload')}</Button>}
          />
        </Card>
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-16 sm:px-6">
        <Alert tone="danger" title={loadError} action={<Button size="sm" variant="outline" onClick={onUploadNew}>{t('report.new')}</Button>} />
      </div>
    );
  }

  if (!extraction) {
    return (
      <div className="mx-auto max-w-6xl space-y-4 px-4 py-10 sm:px-6" aria-busy="true">
        <Skeleton className="h-24 w-full" />
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-20" />)}
        </div>
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  const params = extraction.parameters;
  const within = params.filter((p) => p.evaluation === 'Within Range').length;
  const outside = params.filter(isOutside).length;
  const isOcr = extraction.extractionMethod === 'paddleocr';
  const relationships = explanation?.relationships ?? insights?.relationships ?? [];
  const questions = explanation?.doctorQuestions ?? insights?.doctorQuestions ?? [];
  const questionsSource = explanation?.doctorQuestionsSource ?? 'fallback';

  return (
    <div className="mx-auto max-w-6xl animate-fade-in space-y-6 px-4 py-8 sm:px-6">
      <Card className="p-5">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="flex min-w-0 items-start gap-3">
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-700 ring-1 ring-brand-100">
              <FileText className="h-5 w-5" aria-hidden />
            </span>
            <div className="min-w-0">
              <h1 className="truncate font-display text-xl font-bold text-ink sm:text-2xl" title={extraction.fileName ?? session?.fileName}>
                {extraction.fileName ?? session?.fileName}
              </h1>
              <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
                <span className="inline-flex items-center gap-1">
                  <CalendarDays className="h-3.5 w-3.5" aria-hidden /> {t('report.date')}: {formatDate(extraction.reportDate, language) ?? extraction.reportDateRaw ?? t('report.date_unknown')}
                </span>
                <span className="inline-flex items-center gap-1">
                  <ScanLine className="h-3.5 w-3.5" aria-hidden /> {t('report.method')}: {isOcr ? t('report.method_ocr') : t('report.method_digital')}
                </span>
                <span>{t('report.retention', { hours: retentionHours })}</span>
              </div>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" size="sm" icon={<Download className="h-4 w-4" aria-hidden />} onClick={downloadPdf} loading={pdfBusy}>
              {pdfBusy ? t('report.downloading') : t('report.download_pdf')}
            </Button>
            <Button variant="danger" size="sm" icon={<Trash2 className="h-4 w-4" aria-hidden />} onClick={remove}>
              {t('report.delete')}
            </Button>
            <Button variant="ghost" size="sm" icon={<Upload className="h-4 w-4" aria-hidden />} onClick={onUploadNew}>
              {t('report.new')}
            </Button>
          </div>
        </div>
        {pdfError && <Alert tone="danger" className="mt-4">{pdfError}</Alert>}
        {isOcr && (
          <Alert tone="warning" className="mt-4">
            <span className="inline-flex items-center gap-1"><AlertTriangle className="h-3.5 w-3.5" aria-hidden />{t('report.ocr_warning')}</span>
          </Alert>
        )}
      </Card>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label={t('stats.total')} value={params.length} tone="text-ink" />
        <Stat label={t('stats.within')} value={within} tone="text-emerald-700" />
        <Stat label={t('stats.outside')} value={outside} tone="text-amber-700" />
        <Stat label={t('stats.not_evaluated')} value={params.length - within - outside} tone="text-slate-500" />
      </div>

      {params.length > 0 && (
        <AiSummary explanation={explanation} loading={explaining} error={explainError} onGenerate={generate} />
      )}

      <div>
        <div role="tablist" aria-label="Report sections" className="flex gap-1 overflow-x-auto rounded-2xl border border-slate-200 bg-white p-1 shadow-card scrollbar-thin">
          {TABS.map((item) => (
            <button
              key={item.id}
              role="tab"
              id={`tab-${item.id}`}
              aria-selected={tab === item.id}
              aria-controls={`panel-${item.id}`}
              onClick={() => setTab(item.id)}
              className={`inline-flex flex-1 items-center justify-center gap-2 whitespace-nowrap rounded-xl px-4 py-2.5 text-sm font-semibold transition-colors cursor-pointer ${tab === item.id ? 'bg-ink text-white shadow-sm' : 'text-slate-600 hover:bg-slate-100'}`}
            >
              {item.icon}
              {t(item.label)}
            </button>
          ))}
        </div>

        {/* Panels stay mounted so the chat conversation and comparison survive tab switches */}
        <div role="tabpanel" id="panel-results" aria-labelledby="tab-results" hidden={tab !== 'results'} className="mt-6">
          <ResultsPanel parameters={params} explanations={explanationMap} sourcesById={sourcesById} numbering={numbering} />
        </div>
        <div role="tabpanel" id="panel-insights" aria-labelledby="tab-insights" hidden={tab !== 'insights'} className="mt-6">
          <InsightsPanel relationships={relationships} questions={questions} questionsSource={questionsSource} sourcesById={sourcesById} loading={insightsLoading && !insights} />
        </div>
        <div role="tabpanel" id="panel-chat" aria-labelledby="tab-chat" hidden={tab !== 'chat'} className="mt-6">
          <ChatPanel auth={auth} parameters={params} />
        </div>
        <div role="tabpanel" id="panel-compare" aria-labelledby="tab-compare" hidden={tab !== 'compare'} className="mt-6">
          <ComparePanel auth={auth} retentionHours={retentionHours} />
        </div>
      </div>
    </div>
  );
}