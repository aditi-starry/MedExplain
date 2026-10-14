import type { ExtractedParameter } from '../types/medical';

export function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  if (Number.isInteger(value)) return String(value);
  return String(Number(value.toFixed(6)));
}

const SUPERSCRIPT: Record<string, string> = { '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴', '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹' };

/** Display-only tidying of units as printed (x10^3/uL -> ×10³/µL). Values are never changed. */
export function prettyUnit(unit: string): string {
  return unit
    .replace(/\bx\s*10\^?(\d+)/gi, (_m, exp: string) => `×10${exp.replace(/\d/g, (d) => SUPERSCRIPT[d])}`)
    .replace(/10\^(\d+)/g, (_m, exp: string) => `10${exp.replace(/\d/g, (d) => SUPERSCRIPT[d])}`)
    .replace(/\bu(L|l|IU)\b/g, 'µ$1');
}

export function formatValue(p: Pick<ExtractedParameter, 'value' | 'unit'>): string {
  if (p.value === null || p.value === undefined) return '—';
  return `${formatNumber(p.value)}${p.unit ? ` ${prettyUnit(p.unit)}` : ''}`;
}

/** The reference range exactly as printed on the report (whitespace tidied), or derived bounds. */
export function formatRange(p: ExtractedParameter): string | null {
  if (p.referenceRaw && p.referenceRaw.trim()) {
    const raw = p.referenceRaw.trim().split(/\s+/).join(' ');
    if (p.unit && !raw.includes(p.unit) && !/[a-zA-Z]/.test(raw)) return `${raw} ${prettyUnit(p.unit)}`;
    return prettyUnit(raw);
  }
  const unit = p.unit ? ` ${prettyUnit(p.unit)}` : '';
  if (p.referenceLow !== null && p.referenceHigh !== null) return `${formatNumber(p.referenceLow)} – ${formatNumber(p.referenceHigh)}${unit}`;
  if (p.referenceHigh !== null) return `< ${formatNumber(p.referenceHigh)}${unit}`;
  if (p.referenceLow !== null) return `> ${formatNumber(p.referenceLow)}${unit}`;
  return null;
}

export function isOutside(p: ExtractedParameter): boolean {
  return p.evaluation === 'Above Range' || p.evaluation === 'Below Range';
}

export function formatDate(iso: string | null | undefined, language: string): string | null {
  if (!iso) return null;
  const date = new Date(`${iso}T00:00:00`);
  if (Number.isNaN(date.getTime())) return iso;
  const locale = language === 'hi' ? 'hi-IN' : language === 'mr' ? 'mr-IN' : 'en-GB';
  return date.toLocaleDateString(locale, { day: 'numeric', month: 'short', year: 'numeric' });
}

export function signed(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—';
  const text = formatNumber(Math.abs(value));
  return value > 0 ? `+${text}` : value < 0 ? `−${text}` : text;
}