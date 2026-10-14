import { useState } from 'react';
import { Check, Copy, HelpCircle, Layers, Sparkles } from 'lucide-react';
import { useI18n } from '../../i18n';
import type { RelationshipInsight, SourceCitation } from '../../types/medical';
import { formatValue } from '../../utils/format';
import { StatusBadge } from '../StatusBadge';
import { Button, Card, Skeleton } from '../ui';
import { SourceList } from './SourceList';

interface InsightsPanelProps {
  relationships: RelationshipInsight[];
  questions: string[];
  questionsSource: 'ai' | 'fallback';
  sourcesById: Map<string, SourceCitation>;
  loading: boolean;
}

export function InsightsPanel({ relationships, questions, questionsSource, sourcesById, loading }: InsightsPanelProps) {
  const { t } = useI18n();
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(questions.map((q, i) => `${i + 1}. ${q}`).join('\n'));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  };

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]">
      <section className="space-y-4">
        <div>
          <h2 className="flex items-center gap-2 font-display text-lg font-bold text-ink">
            <Layers className="h-5 w-5 text-brand-600" aria-hidden /> {t('insights.title')}
          </h2>
          <p className="text-sm text-slate-600">{t('insights.subtitle')}</p>
        </div>
        {loading && <Skeleton className="h-40 w-full" />}
        {!loading && relationships.length === 0 && (
          <p className="rounded-2xl border border-dashed border-slate-300 bg-white p-6 text-sm text-slate-500">{t('insights.none')}</p>
        )}
        {!loading &&
          relationships.map((rel) => {
            const sources = rel.evidence.map((id) => sourcesById.get(id)).filter(Boolean) as SourceCitation[];
            return (
              <Card key={rel.id} as="article" className="space-y-3 p-5 animate-rise">
                <div className="flex flex-wrap gap-2">
                  {rel.parameters.map((p) => (
                    <span key={p.name} className="inline-flex items-center gap-2 rounded-xl bg-slate-50 px-2.5 py-1.5 text-sm ring-1 ring-slate-200">
                      <span className="font-semibold text-ink">{p.name}</span>
                      <span className="text-slate-600">{formatValue({ value: p.value, unit: p.unit })}</span>
                      <StatusBadge status={p.evaluation} size="sm" />
                    </span>
                  ))}
                </div>
                {rel.explanation && (
                  <div className="rounded-xl border border-indigo-100 bg-indigo-50/50 p-3">
                    <p className="mb-1 flex items-center gap-1 text-[11px] font-semibold text-indigo-700">
                      <Sparkles className="h-3 w-3" aria-hidden /> {t('insights.ai')}
                    </p>
                    <p className="text-sm leading-relaxed text-slate-800">{rel.explanation}</p>
                  </div>
                )}
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">{t('insights.documented')}</p>
                  <p className="mt-1 text-sm leading-relaxed text-slate-700" lang="en">{rel.description}</p>
                </div>
                {rel.missingRelated.length > 0 && <p className="text-xs text-slate-500">{t('insights.missing', { names: rel.missingRelated.join(', ') })}</p>}
                <p className="rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-900">{rel.caution}</p>
                <SourceList sources={sources} collapsible />
              </Card>
            );
          })}
      </section>

      <section>
        <Card className="space-y-4 p-5 lg:sticky lg:top-24">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="flex items-center gap-2 font-display text-lg font-bold text-ink">
                <HelpCircle className="h-5 w-5 text-brand-600" aria-hidden /> {t('questions.title')}
              </h2>
              <p className="text-sm text-slate-600">{t('questions.subtitle')}</p>
            </div>
          </div>
          {loading ? (
            <Skeleton className="h-32 w-full" />
          ) : (
            <ol className="space-y-2.5">
              {questions.map((q, i) => (
                <li key={q} className="flex gap-3 rounded-xl bg-slate-50 px-3 py-2.5 text-sm leading-relaxed text-slate-800">
                  <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-brand-700 text-[11px] font-bold text-white">{i + 1}</span>
                  {q}
                </li>
              ))}
            </ol>
          )}
          <div className="flex items-center justify-between gap-2">
            <span className="text-xs text-slate-500">{questionsSource === 'ai' ? t('questions.source_ai') : t('questions.source_fallback')}</span>
            <Button variant="outline" size="sm" onClick={copy} disabled={!questions.length} icon={copied ? <Check className="h-3.5 w-3.5" aria-hidden /> : <Copy className="h-3.5 w-3.5" aria-hidden />}>
              {copied ? t('questions.copied') : t('questions.copy')}
            </Button>
          </div>
        </Card>
      </section>
    </div>
  );
}