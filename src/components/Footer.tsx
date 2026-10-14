import { ShieldAlert } from 'lucide-react';
import { useI18n } from '../i18n';

export function Footer() {
  const { t, language } = useI18n();
  return (
    <footer className="mt-16 border-t border-slate-200 bg-white">
      <div className="mx-auto max-w-6xl space-y-3 px-4 py-8 text-sm text-slate-600 sm:px-6">
        <p className="flex items-start gap-2">
          <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" aria-hidden />
          <span>{t('footer.disclaimer')}</span>
        </p>
        <p className="text-xs text-slate-500">{t('footer.sources')}</p>
        {language !== 'en' && <p className="text-xs text-slate-500">{t('footer.translation')}</p>}
        <p className="text-xs text-slate-400">© {new Date().getFullYear()} MedExplain AI</p>
      </div>
    </footer>
  );
}