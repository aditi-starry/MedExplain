import { ArrowDown, ArrowUp, Check, Minus } from 'lucide-react';
import { useI18n } from '../i18n';
import type { TranslationKey } from '../i18n/types';

const STYLES: Record<string, { cls: string; icon: typeof Check }> = {
  'Within Range': { cls: 'bg-emerald-50 text-emerald-800 ring-emerald-200', icon: Check },
  'Above Range': { cls: 'bg-amber-50 text-amber-900 ring-amber-200', icon: ArrowUp },
  'Below Range': { cls: 'bg-sky-50 text-sky-900 ring-sky-200', icon: ArrowDown },
  'Not Evaluated': { cls: 'bg-slate-100 text-slate-700 ring-slate-200', icon: Minus },
};

export function StatusBadge({ status, size = 'md' }: { status?: string | null; size?: 'sm' | 'md' }) {
  const { t } = useI18n();
  const key = status && STYLES[status] ? status : 'Not Evaluated';
  const { cls, icon: Icon } = STYLES[key];
  const sizing = size === 'sm' ? 'px-2 py-0.5 text-[11px]' : 'px-2.5 py-1 text-xs';
  return (
    <span className={`inline-flex shrink-0 items-center gap-1 rounded-full font-semibold ring-1 ring-inset ${cls} ${sizing}`}>
      <Icon className="h-3 w-3" aria-hidden />
      {t(`status.${key}` as TranslationKey)}
    </span>
  );
}
