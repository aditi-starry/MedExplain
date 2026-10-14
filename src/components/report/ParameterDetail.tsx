import { BookOpen, ChevronDown, ClipboardList, FileText, Lightbulb, Sparkles, Wand2 } from 'lucide-react';
import { useI18n } from '../../i18n';
import type { ExtractedParameter, ParameterExplanation, SourceCitation } from '../../types/medical';
import { formatRange, formatValue } from '../../utils/format';
import { RangeBar } from '../RangeBar';
import { StatusBadge } from '../StatusBadge';
import { SourceList } from './SourceList';

interface ParameterDetailProps {
  parameter: ExtractedParameter;
  explanation?: ParameterExplanation;
  sourcesById: Map<string, SourceCitation>;
  numbering: Map<string, number>;
}

export function ParameterDetail({ parameter, explanation, sourcesById, numbering }: ParameterDetailProps) {
  const { t } = useI18n();
  const range = formatRange(parameter);
  const cited = (explanation?.citations ?? []).map((id) => sourcesById.get(id)).filter(Boolean) as SourceCitation[];
  const related = explanation && !explanation.citations.length
    ? (explanation.rationale.evidenceIds.map((id) => sourcesById.get(id)).filter(Boolean) as SourceCitation[])
    : [];
  const isAi = explanation?.source === 'ai';

  return (
    <div className="space-y-4 animate-rise">
      <div className="flex items-start justify-between gap-3">
        <h3 className="min-w-0 break-words font-display text-xl font-bold text-ink">{parameter.name}</h3>
        <StatusBadge status={parameter.evaluation} />
      </div>

      {/* Report-derived facts */}
      <div className="rounded-2xl border border-slate-200 bg-slate-50/70 p-4">
        <p className="mb-2 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
          <FileText className="h-3.5 w-3.5" aria-hidden /> {t('detail.from_report')}
        </p>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <p className="text-xs text-slate-500">{t('detail.your_result')}</p>
            <p className="font-display text-2xl font-extrabold text-ink break-words">{formatValue(parameter)}</p>
          </div>
          <div>
            <p className="text-xs text-slate-500">{t('detail.report_range')}</p>
            <p className="text-sm font-semibold text-slate-800 break-words">{range ?? t('results.not_stated')}</p>
          </div>
        </div>
        <div className="mt-3">
          <RangeBar parameter={parameter} />
        </div>
      </div>

      {/* AI or automatic explanation */}
      {explanation ? (
        <div className={`rounded-2xl border p-4 ${isAi ? 'border-indigo-200 bg-indigo-50/50' : 'border-slate-200 bg-white'}`}>
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold ${isAi ? 'bg-indigo-100 text-indigo-800' : 'bg-slate-100 text-slate-700'}`}>
              {isAi ? <Sparkles className="h-3 w-3" aria-hidden /> : <Wand2 className="h-3 w-3" aria-hidden />}
              {isAi ? t('ai.badge_ai') : t('ai.badge_fallback')}
            </span>
            <span className="text-[11px] text-slate-500">
              {explanation.evidenceStatus === 'supported' ? t('detail.evidence_supported') : explanation.evidenceStatus === 'limited' ? t('detail.evidence_limited') : t('detail.evidence_none')}
            </span>
          </div>
          <p className="leading-relaxed text-slate-800">
            {explanation.summary}
            {explanation.citations.map((id) =>
              numbering.has(id) ? (
                <sup key={id} className="ml-0.5 font-semibold text-indigo-700">[{numbering.get(id)}]</sup>
              ) : null,
            )}
          </p>
          {explanation.nextStep && (
            <p className="mt-3 flex items-start gap-2 rounded-xl bg-white/80 px-3 py-2 text-sm text-slate-700 ring-1 ring-slate-200">
              <Lightbulb className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" aria-hidden />
              <span>
                <span className="font-semibold">{t('detail.next_step')}: </span>
                {explanation.nextStep}
              </span>
            </p>
          )}
        </div>
      ) : (
        <p className="rounded-2xl border border-dashed border-slate-300 p-4 text-sm text-slate-500">{t('detail.no_explanation')}</p>
      )}

      {/* Explainability: inspectable rationale, not model chain-of-thought */}
      {explanation && (
        <details className="group rounded-2xl border border-slate-200 bg-white">
          <summary className="flex cursor-pointer list-none items-center justify-between gap-2 px-4 py-3 text-sm font-semibold text-ink">
            <span className="flex items-center gap-2">
              <ClipboardList className="h-4 w-4 text-brand-600" aria-hidden /> {t('detail.why')}
            </span>
            <ChevronDown className="h-4 w-4 text-slate-400 transition-transform group-open:rotate-180" aria-hidden />
          </summary>
          <dl className="space-y-3 border-t border-slate-100 px-4 py-3 text-sm">
            <div>
              <dt className="text-xs font-semibold text-slate-500">{t('detail.value_considered')}</dt>
              <dd className="text-slate-800">{explanation.rationale.valueConsidered}</dd>
            </div>
            <div>
              <dt className="text-xs font-semibold text-slate-500">{t('detail.range_used')}</dt>
              <dd className="text-slate-800">{explanation.rationale.rangeUsed}</dd>
            </div>
            <div>
              <dt className="text-xs font-semibold text-slate-500">{t('detail.comparison')}</dt>
              <dd className="font-mono text-slate-800">{explanation.rationale.comparison}</dd>
            </div>
            <div>
              <dt className="text-xs font-semibold text-slate-500">{t('detail.reason')}</dt>
              <dd className="text-slate-800">{explanation.rationale.reason}</dd>
            </div>
            {explanation.rationale.uncertainty.length > 0 && (
              <div>
                <dt className="text-xs font-semibold text-slate-500">{t('detail.uncertainty')}</dt>
                <dd>
                  <ul className="mt-1 list-disc space-y-1 pl-5 text-slate-700">
                    {explanation.rationale.uncertainty.map((u) => (
                      <li key={u}>{u}</li>
                    ))}
                  </ul>
                </dd>
              </div>
            )}
            {parameter.rawLine && (
              <div>
                <dt className="text-xs font-semibold text-slate-500">{t('detail.raw_line')}</dt>
                <dd className="mt-1 overflow-x-auto rounded-lg bg-slate-50 px-2 py-1 font-mono text-xs text-slate-700 scrollbar-thin">{parameter.rawLine}</dd>
              </div>
            )}
          </dl>
        </details>
      )}

      {cited.length > 0 && (
        <div className="space-y-2">
          <p className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-slate-500">
            <BookOpen className="h-3.5 w-3.5" aria-hidden /> {t('detail.evidence')}
          </p>
          <SourceList sources={cited} numbering={numbering} />
        </div>
      )}
      {related.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">{t('detail.related_reading')}</p>
          <SourceList sources={related} showPassage={false} />
        </div>
      )}
    </div>
  );
}