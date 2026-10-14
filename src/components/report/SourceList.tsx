import { useState } from 'react';
import { BookOpenCheck, ChevronDown, ExternalLink } from 'lucide-react';
import { useI18n } from '../../i18n';
import type { SourceCitation } from '../../types/medical';

interface SourceListProps {
  sources: SourceCitation[];
  numbering?: Map<string, number>;
  collapsible?: boolean;
  showPassage?: boolean;
}

export function SourceItem({ source, number, showPassage = true }: { source: SourceCitation; number?: number; showPassage?: boolean }) {
  const { t } = useI18n();
  return (
    <li className="rounded-xl border border-slate-200 bg-white p-3">
      <div className="flex items-start gap-2.5">
        {number !== undefined && (
          <span className="mt-0.5 flex h-5 min-w-5 items-center justify-center rounded-md bg-brand-50 px-1 text-[11px] font-bold text-brand-700 ring-1 ring-brand-100">{number}</span>
        )}
        <div className="min-w-0 flex-1">
          <a
            href={source.url}
            target="_blank"
            rel="noopener noreferrer"
            className="group inline-flex items-start gap-1 text-sm font-semibold text-ink hover:text-brand-700"
            title={t('sources.open')}
          >
            <span className="break-words">{source.title}</span>
            <ExternalLink className="mt-0.5 h-3.5 w-3.5 shrink-0 text-slate-400 group-hover:text-brand-600" aria-hidden />
          </a>
          <p className="text-xs text-slate-500">
            {source.publisher}
            {source.lastUpdated ? ` · ${t('sources.updated', { date: source.lastUpdated })}` : ''}
          </p>
          {showPassage && <p className="mt-1.5 text-xs leading-relaxed text-slate-600" lang="en">“{source.text}”</p>}
        </div>
      </div>
    </li>
  );
}

export function SourceList({ sources, numbering, collapsible = false, showPassage = true }: SourceListProps) {
  const { t } = useI18n();
  const [open, setOpen] = useState(!collapsible);
  if (!sources.length) return null;
  return (
    <div>
      {collapsible && (
        <button
          onClick={() => setOpen((o) => !o)}
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-brand-700 hover:text-brand-800 cursor-pointer"
          aria-expanded={open}
        >
          <BookOpenCheck className="h-3.5 w-3.5" aria-hidden />
          {open ? t('sources.hide') : t('sources.show', { count: sources.length })}
          <ChevronDown className={`h-3.5 w-3.5 transition-transform ${open ? 'rotate-180' : ''}`} aria-hidden />
        </button>
      )}
      {open && (
        <ul className={`space-y-2 ${collapsible ? 'mt-2' : ''}`}>
          {sources.map((s) => (
            <SourceItem key={s.id} source={s} number={numbering?.get(s.id)} showPassage={showPassage} />
          ))}
        </ul>
      )}
    </div>
  );
}