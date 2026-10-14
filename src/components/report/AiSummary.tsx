import { AlertTriangle, RefreshCw, ShieldAlert, Sparkles, Wand2 } from 'lucide-react';
import { useI18n } from '../../i18n';
import type { ExplanationResponse } from '../../types/medical';
import { Alert, Button, Card, Skeleton } from '../ui';

interface AiSummaryProps {
  explanation: ExplanationResponse | null;
  loading: boolean;
  error: string | null;
  disabled?: boolean;
  onGenerate: (refresh: boolean) => void;
}

export function AiSummary({ explanation, loading, error, disabled, onGenerate }: AiSummaryProps) {
  const { t } = useI18n();
  const sourceLabel =
    explanation?.source === 'ai' ? t('ai.source_ai') : explanation?.source === 'mixed' ? t('ai.source_mixed') : t('ai.source_fallback');
  const isAi = explanation && explanation.source !== 'fallback';

  return (
    <Card className="overflow-hidden">
      <div className="flex flex-col gap-4 border-b border-slate-100 bg-gradient-to-r from-indigo-50/80 via-white to-white p-5 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-3">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-indigo-600 text-white shadow-sm">
            <Sparkles className="h-5 w-5" aria-hidden />
          </span>
          <div>
            <h2 className="font-display text-lg font-bold text-ink">{t('ai.panel_title')}</h2>
            <p className="text-sm text-slate-600">{explanation ? sourceLabel : t('ai.intro')}</p>
          </div>
        </div>
        {explanation ? (
          <Button variant="outline" size="sm" icon={<RefreshCw className="h-3.5 w-3.5" aria-hidden />} onClick={() => onGenerate(true)} loading={loading} disabled={disabled}>
            {t('ai.regenerate')}
          </Button>
        ) : (
          <Button variant="ai" icon={<Sparkles className="h-4 w-4" aria-hidden />} onClick={() => onGenerate(false)} loading={loading} disabled={disabled}>
            {t('ai.generate')}
          </Button>
        )}
      </div>

      <div className="space-y-4 p-5" aria-live="polite">
        {loading && (
          <div className="space-y-3">
            <p className="text-sm font-medium text-indigo-700">{t('ai.generating')}</p>
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-11/12" />
            <Skeleton className="h-4 w-2/3" />
          </div>
        )}

        {!loading && error && (
          <Alert tone="danger" title={t('ai.error')} action={<Button size="sm" variant="outline" onClick={() => onGenerate(false)}>{t('common.retry')}</Button>}>
            {error}
          </Alert>
        )}

        {!loading && explanation && (
          <>
            {explanation.notice && (
              <Alert tone="warning" title={explanation.source === 'fallback' ? t('ai.source_fallback') : t('ai.source_mixed')}>
                {explanation.notice}
              </Alert>
            )}
            <div className="flex items-start gap-2">
              {isAi ? <Sparkles className="mt-1 h-4 w-4 shrink-0 text-indigo-500" aria-hidden /> : <Wand2 className="mt-1 h-4 w-4 shrink-0 text-slate-400" aria-hidden />}
              <p className="text-base leading-relaxed text-slate-800">{explanation.narrativeSummary}</p>
            </div>
            <p className="flex items-start gap-2 text-xs text-slate-500">
              <ShieldAlert className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-600" aria-hidden />
              <span>
                {explanation.disclaimer} {isAi && t('ai.not_verified')}
                {explanation.model ? ` · ${explanation.model}` : ''}
              </span>
            </p>
          </>
        )}

        {!loading && !explanation && !error && (
          <p className="flex items-center gap-2 text-sm text-slate-500">
            <AlertTriangle className="h-4 w-4 text-slate-400" aria-hidden />
            {t('report.check_original')}
          </p>
        )}
      </div>
    </Card>
  );
}