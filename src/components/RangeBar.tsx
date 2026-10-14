import type { ExtractedParameter } from '../types/medical';
import { useI18n } from '../i18n';

/**
 * Shows where a value sits relative to the range printed on the report.
 * Only drawn when the report gives at least one numeric bound; nothing is invented.
 */
export function RangeBar({ parameter }: { parameter: ExtractedParameter }) {
  const { t } = useI18n();
  const { value, referenceLow: low, referenceHigh: high, evaluation } = parameter;
  if (value === null || value === undefined || (low === null && high === null)) return null;

  let min: number;
  let max: number;
  if (low !== null && high !== null) {
    const span = Math.max(high - low, Math.abs(high) * 0.1, 1e-6);
    min = Math.min(low - span * 0.5, value);
    max = Math.max(high + span * 0.5, value);
  } else {
    const bound = (low ?? high) as number;
    const span = Math.max(Math.abs(bound) * 0.6, Math.abs(value - bound) * 1.3, 1e-6);
    min = Math.min(bound - span, value);
    max = Math.max(bound + span, value);
  }
  const pos = (v: number) => `${(((v - min) / (max - min)) * 100).toFixed(2)}%`;
  const bandStart = low !== null ? pos(low) : '0%';
  const bandEnd = high !== null ? pos(high) : '100%';
  const marker =
    evaluation === 'Above Range' ? 'bg-amber-500' : evaluation === 'Below Range' ? 'bg-sky-600' : evaluation === 'Within Range' ? 'bg-emerald-600' : 'bg-slate-500';

  return (
    <div className="relative h-2 w-full rounded-full bg-slate-100" role="img" aria-label={t('results.range_bar')}>
      <div className="absolute inset-y-0 rounded-full bg-emerald-100 ring-1 ring-inset ring-emerald-200" style={{ left: bandStart, right: `calc(100% - ${bandEnd})` }} />
      <div className={`absolute top-1/2 h-3.5 w-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-white shadow ${marker}`} style={{ left: pos(value) }} />
    </div>
  );
}