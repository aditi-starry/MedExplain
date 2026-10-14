import { useMemo, useState } from 'react';
import { ChevronRight, FileQuestion, Search } from 'lucide-react';
import { useI18n } from '../../i18n';
import type { ExtractedParameter, ParameterExplanation, SourceCitation } from '../../types/medical';
import { formatRange, formatValue, isOutside } from '../../utils/format';
import { StatusBadge } from '../StatusBadge';
import { STATUS_DOT } from '../../utils/status';
import { Card, EmptyState } from '../ui';
import { ParameterDetail } from './ParameterDetail';

interface ResultsPanelProps {
  parameters: ExtractedParameter[];
  explanations: Map<string, ParameterExplanation>;
  sourcesById: Map<string, SourceCitation>;
  numbering: Map<string, number>;
}

export function ResultsPanel({ parameters, explanations, sourcesById, numbering }: ResultsPanelProps) {
  const { t } = useI18n();
  const outsideCount = parameters.filter(isOutside).length;
  const [filter, setFilter] = useState<'all' | 'outside'>(outsideCount ? 'outside' : 'all');
  const [query, setQuery] = useState('');
  const [selected, setSelected] = useState<string | null>(null);

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    return parameters.filter((p) => (filter === 'all' || isOutside(p)) && (!q || p.name.toLowerCase().includes(q)));
  }, [parameters, filter, query]);

  const selectedParam = parameters.find((p) => p.name === selected) ?? visible[0];

  if (!parameters.length) {
    return (
      <Card>
        <EmptyState icon={<FileQuestion className="h-6 w-6" />} title={t('results.none_title')} body={t('results.none_body')} />
      </Card>
    );
  }

  const chip = (active: boolean) =>
    `rounded-full px-3 py-1.5 text-xs font-semibold transition-colors cursor-pointer ${active ? 'bg-ink text-white' : 'bg-white text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50'}`;

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
      <div className="min-w-0 space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <button className={chip(filter === 'all')} onClick={() => setFilter('all')} aria-pressed={filter === 'all'}>
            {t('results.filter_all')} · {parameters.length}
          </button>
          <button className={chip(filter === 'outside')} onClick={() => setFilter('outside')} aria-pressed={filter === 'outside'}>
            {t('results.filter_outside')} · {outsideCount}
          </button>
          <label className="relative ml-auto w-full sm:w-52">
            <span className="sr-only">{t('results.search')}</span>
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden />
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={t('results.search')}
              className="h-9 w-full rounded-xl border border-slate-200 bg-white pl-9 pr-3 text-sm placeholder:text-slate-400"
            />
          </label>
        </div>

        {visible.length === 0 ? (
          <p className="rounded-2xl border border-dashed border-slate-300 bg-white p-6 text-center text-sm text-slate-500">{t('results.no_match')}</p>
        ) : (
          <ul className="space-y-2">
            {visible.map((p) => {
              const active = selectedParam?.name === p.name;
              const range = formatRange(p);
              return (
                <li key={p.name}>
                  <button
                    onClick={() => setSelected(p.name)}
                    aria-expanded={active}
                    className={`flex w-full items-center gap-3 rounded-2xl border bg-white px-4 py-3 text-left transition-all cursor-pointer ${active ? 'border-brand-400 ring-2 ring-brand-100' : 'border-slate-200 hover:border-slate-300 hover:shadow-card'}`}
                  >
                    <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${STATUS_DOT[p.evaluation ?? 'Not Evaluated'] ?? STATUS_DOT['Not Evaluated']}`} aria-hidden />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate font-semibold text-ink" title={p.name}>{p.name}</span>
                      <span className="block truncate text-xs text-slate-500">
                        <span className="font-semibold text-slate-800 sm:hidden">{formatValue(p)} · </span>
                        {t('results.range')}: {range ?? t('results.not_stated')}
                      </span>
                    </span>
                    <span className="hidden text-right sm:block">
                      <span className="block font-display font-bold text-ink">{formatValue(p)}</span>
                    </span>
                    <StatusBadge status={p.evaluation} size="sm" />
                    <ChevronRight className={`h-4 w-4 shrink-0 text-slate-300 transition-transform ${active ? 'rotate-90 lg:rotate-0' : ''}`} aria-hidden />
                  </button>
                  {active && (
                    <div className="mt-2 rounded-2xl border border-slate-200 bg-white p-4 lg:hidden">
                      <ParameterDetail parameter={p} explanation={explanations.get(p.name)} sourcesById={sourcesById} numbering={numbering} />
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </div>

      <div className="hidden lg:block">
        {selectedParam && (
          <Card className="sticky top-24 max-h-[calc(100vh-7rem)] overflow-y-auto p-5 scrollbar-thin">
            <ParameterDetail
              key={selectedParam.name}
              parameter={selectedParam}
              explanation={explanations.get(selectedParam.name)}
              sourcesById={sourcesById}
              numbering={numbering}
            />
          </Card>
        )}
      </div>
    </div>
  );
}