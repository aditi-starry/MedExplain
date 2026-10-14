import { Activity, Languages, Upload } from 'lucide-react';
import { LANGUAGES, useI18n } from '../i18n';
import type { Language } from '../i18n/types';
import type { Route } from '../hooks/useHashRoute';

interface HeaderProps {
  route: Route;
  onNavigate: (route: Route) => void;
  currentReportId?: string | null;
}

export function LanguageSelector({ compact = false }: { compact?: boolean }) {
  const { language, setLanguage, t } = useI18n();
  return (
    <label className="relative inline-flex items-center">
      <span className="sr-only">{t('nav.language')}</span>
      <Languages className="pointer-events-none absolute left-2.5 h-4 w-4 text-slate-500" aria-hidden />
      <select
        value={language}
        onChange={(e) => setLanguage(e.target.value as Language)}
        className={`h-9 cursor-pointer appearance-none rounded-xl border border-slate-200 bg-white pl-8 text-sm font-medium text-slate-700 shadow-sm hover:border-slate-300 ${compact ? 'pr-2' : 'pr-8'}`}
        aria-label={t('nav.language')}
      >
        {LANGUAGES.map((l) => (
          <option key={l.code} value={l.code} lang={l.code}>
            {l.label}
          </option>
        ))}
      </select>
    </label>
  );
}

export function Header({ route, onNavigate, currentReportId }: HeaderProps) {
  const { t } = useI18n();
  const link = (active: boolean) =>
    `rounded-lg px-3 py-1.5 text-sm font-medium transition-colors cursor-pointer ${active ? 'bg-brand-50 text-brand-800' : 'text-slate-600 hover:bg-slate-100 hover:text-ink'}`;

  return (
    <header className="sticky top-0 z-40 border-b border-slate-200/80 bg-white/85 backdrop-blur supports-[backdrop-filter]:bg-white/70">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-3 focus:rounded-lg focus:bg-white focus:px-3 focus:py-2 focus:shadow">
        {t('nav.skip')}
      </a>
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-3 px-4 sm:px-6">
        <button onClick={() => onNavigate({ name: 'home' })} className="flex min-w-0 items-center gap-2.5 cursor-pointer" aria-label={t('nav.home')}>
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-brand-700 text-white shadow-sm">
            <Activity className="h-5 w-5" aria-hidden />
          </span>
          <span className="truncate font-display text-lg font-extrabold tracking-tight text-ink">
            MedExplain <span className="text-brand-600">AI</span>
          </span>
        </button>

        <nav className="hidden items-center gap-1 md:flex" aria-label="Main">
          <button className={link(route.name === 'home')} onClick={() => onNavigate({ name: 'home' })} aria-current={route.name === 'home' ? 'page' : undefined}>
            {t('nav.home')}
          </button>
          <button className={link(route.name === 'upload')} onClick={() => onNavigate({ name: 'upload' })} aria-current={route.name === 'upload' ? 'page' : undefined}>
            {t('nav.upload')}
          </button>
          {currentReportId && (
            <button
              className={link(route.name === 'report')}
              onClick={() => onNavigate({ name: 'report', reportId: currentReportId })}
              aria-current={route.name === 'report' ? 'page' : undefined}
            >
              {t('nav.report')}
            </button>
          )}
        </nav>

        <div className="flex items-center gap-2">
          <LanguageSelector />
          <button
            onClick={() => onNavigate({ name: 'upload' })}
            className="hidden h-9 items-center gap-1.5 rounded-xl bg-brand-700 px-3.5 text-sm font-semibold text-white shadow-sm hover:bg-brand-800 sm:inline-flex cursor-pointer"
          >
            <Upload className="h-4 w-4" aria-hidden />
            {t('nav.upload')}
          </button>
        </div>
      </div>
      <nav className="flex gap-1 overflow-x-auto border-t border-slate-100 px-3 py-1.5 md:hidden" aria-label="Main mobile">
        <button className={link(route.name === 'home')} onClick={() => onNavigate({ name: 'home' })} aria-current={route.name === 'home' ? 'page' : undefined}>
          {t('nav.home')}
        </button>
        <button className={link(route.name === 'upload')} onClick={() => onNavigate({ name: 'upload' })} aria-current={route.name === 'upload' ? 'page' : undefined}>
          {t('nav.upload')}
        </button>
        {currentReportId && (
          <button className={link(route.name === 'report')} onClick={() => onNavigate({ name: 'report', reportId: currentReportId })} aria-current={route.name === 'report' ? 'page' : undefined}>
            {t('nav.report')}
          </button>
        )}
      </nav>
    </header>
  );
}