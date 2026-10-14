import { useRef, useState } from 'react';
import { ArrowDownRight, ArrowRight, ArrowUpRight, FlaskConical, GitCompareArrows, Upload } from 'lucide-react';
import { useI18n } from '../../i18n';
import { compareReports } from '../../services/api';
import type { ReportAuth } from '../../services/api';
import { errorMessage, loadSampleFile, uploadAndExtract, validateFile } from '../../services/reportFlow';
import { listSessionReports } from '../../services/session';
import type { ComparisonResponse, ComparisonRow } from '../../types/medical';
import { formatDate, formatNumber, prettyUnit, signed } from '../../utils/format';
import { StatusBadge } from '../StatusBadge';
import { Alert, Button, Card } from '../ui';

interface ComparePanelProps {
  auth: ReportAuth;
  retentionHours: number;
}

function ChangeCell({ row }: { row: ComparisonRow }) {
  const { t } = useI18n();
  if (row.status !== 'compared') {
    const key = row.status === 'incompatible_units' ? 'compare.incompatible' : row.status === 'missing_value' ? 'compare.missing' : row.status === 'only_in_current' ? 'compare.only_current' : 'compare.only_previous';
    return <span className="text-xs text-slate-500">{t(key)}</span>;
  }
  const Icon = row.direction === 'increased' ? ArrowUpRight : row.direction === 'decreased' ? ArrowDownRight : ArrowRight;
  const label = row.direction === 'increased' ? t('compare.increased') : row.direction === 'decreased' ? t('compare.decreased') : t('compare.unchanged');
  return (
    <span className="inline-flex items-center gap-1.5 text-sm text-slate-800">
      <Icon className="h-4 w-4 text-slate-500" aria-hidden />
      <span className="font-semibold">{signed(row.difference)}</span>
      {row.percentChange !== null && <span className="text-xs text-slate-500">({row.percentChange > 0 ? '+' : ''}{row.percentChange}%)</span>}
      <span className="sr-only">{label}</span>
    </span>
  );
}

function Value({ value, unit, evaluation }: { value: number | null; unit: string | null; evaluation: string | null }) {
  if (value === null) return <span className="text-slate-400">—</span>;
  return (
    <span className="flex flex-col items-start gap-1">
      <span className="font-semibold text-ink">
        {formatNumber(value)} <span className="text-xs font-normal text-slate-500">{unit ? prettyUnit(unit) : null}</span>
      </span>
      {evaluation && <StatusBadge status={evaluation} size="sm" />}
    </span>
  );
}

export function ComparePanel({ auth, retentionHours }: ComparePanelProps) {
  const { t, language } = useI18n();
  const inputRef = useRef<HTMLInputElement>(null);
  const [, setVersion] = useState(0); // bumped after an upload to re-read the session list
  const others = listSessionReports().filter((r) => r.reportId !== auth.reportId).reverse();
  const [selected, setSelected] = useState<string>('');
  const [busy, setBusy] = useState<'upload' | 'compare' | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ComparisonResponse | null>(null);

  const chosen = others.find((r) => r.reportId === (selected || others[0]?.reportId));

  const run = async (previous: ReportAuth) => {
    setBusy('compare');
    setError(null);
    try {
      setResult(await compareReports(auth, previous));
    } catch (err) {
      setError(errorMessage(err, t));
    } finally {
      setBusy(null);
    }
  };

  const addPrevious = async (file: File | undefined | null) => {
    if (!file) return;
    const problem = validateFile(file, t);
    if (problem) {
      setError(problem);
      return;
    }
    setBusy('upload');
    setError(null);
    try {
      const { auth: previous } = await uploadAndExtract(file);
      setVersion((v) => v + 1);
      setSelected(previous.reportId);
      await run(previous);
    } catch (err) {
      setError(errorMessage(err, t));
      setBusy(null);
    }
  };

  const useSample = async () => {
    try {
      await addPrevious(await loadSampleFile('/sample_lab_report_previous.pdf', 'Fictional_Sample_Earlier_Report.pdf'));
    } catch (err) {
      setError(errorMessage(err, t));
    }
  };

  const warnings = result?.warnings.map((w) => (w.startsWith('The report chosen') ? t('compare.warning_order') : w.startsWith('A report date') ? t('compare.warning_dates') : w));

  return (
    <div className="space-y-6">
      <Card className="space-y-4 p-5">
        <div>
          <h2 className="flex items-center gap-2 font-display text-lg font-bold text-ink">
            <GitCompareArrows className="h-5 w-5 text-brand-600" aria-hidden /> {t('compare.title')}
          </h2>
          <p className="text-sm text-slate-600">{t('compare.subtitle')}</p>
        </div>

        <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
          {others.length > 0 ? (
            <label className="min-w-0 flex-1">
              <span className="mb-1 block text-xs font-semibold text-slate-500">{t('compare.choose')}</span>
              <select
                value={chosen?.reportId ?? ''}
                onChange={(e) => setSelected(e.target.value)}
                className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm"
              >
                {others.map((r) => (
                  <option key={r.reportId} value={r.reportId}>
                    {r.fileName} · {formatDate(r.reportDate, language) ?? t('compare.date_unknown')}
                  </option>
                ))}
              </select>
            </label>
          ) : (
            <p className="flex-1 text-sm text-slate-500">{t('compare.none')}</p>
          )}
          {chosen && (
            <Button onClick={() => run({ reportId: chosen.reportId, token: chosen.token })} loading={busy === 'compare'} disabled={busy !== null}>
              {t('compare.run')}
            </Button>
          )}
        </div>

        <div className="flex flex-wrap gap-2 border-t border-slate-100 pt-4">
          <Button variant="outline" size="sm" icon={<Upload className="h-3.5 w-3.5" aria-hidden />} onClick={() => inputRef.current?.click()} loading={busy === 'upload'} disabled={busy !== null}>
            {busy === 'upload' ? t('compare.uploading') : t('compare.upload_previous')}
          </Button>
          <Button variant="ghost" size="sm" icon={<FlaskConical className="h-3.5 w-3.5" aria-hidden />} onClick={useSample} disabled={busy !== null}>
            {t('compare.sample_previous')}
          </Button>
          <input
            ref={inputRef}
            type="file"
            accept=".pdf,.png,.jpg,.jpeg"
            className="sr-only"
            aria-label={t('compare.upload_previous')}
            onChange={(e) => {
              void addPrevious(e.target.files?.[0]);
              e.target.value = '';
            }}
          />
        </div>
        <p className="text-xs text-slate-500">{t('compare.session_note', { hours: retentionHours })}</p>
      </Card>

      {error && <Alert tone="danger">{error}</Alert>}

      {result && (
        <Card className="overflow-hidden">
          {warnings && warnings.length > 0 && (
            <div className="space-y-2 p-4">
              {warnings.map((w) => (
                <Alert key={w} tone="warning">{w}</Alert>
              ))}
            </div>
          )}
          <div className="overflow-x-auto scrollbar-thin">
            <table className="w-full min-w-[36rem] text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase tracking-wider text-slate-500">
                <tr>
                  <th scope="col" className="px-4 py-3 font-semibold">{t('compare.col_test')}</th>
                  <th scope="col" className="px-4 py-3 font-semibold">
                    {t('compare.col_previous')}
                    <span className="block font-normal normal-case tracking-normal">{formatDate(result.previousDate, language) ?? t('compare.date_unknown')}</span>
                  </th>
                  <th scope="col" className="px-4 py-3 font-semibold">
                    {t('compare.col_current')}
                    <span className="block font-normal normal-case tracking-normal">{formatDate(result.currentDate, language) ?? t('compare.date_unknown')}</span>
                  </th>
                  <th scope="col" className="px-4 py-3 font-semibold">{t('compare.col_change')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {result.rows.map((row) => (
                  <tr key={row.name} className={row.status === 'compared' ? '' : 'bg-slate-50/50'}>
                    <th scope="row" className="px-4 py-3 font-semibold text-ink">{row.name}</th>
                    <td className="px-4 py-3"><Value value={row.previousValue} unit={row.previousUnit} evaluation={row.previousEvaluation} /></td>
                    <td className="px-4 py-3"><Value value={row.currentValue} unit={row.currentUnit} evaluation={row.currentEvaluation} /></td>
                    <td className="px-4 py-3"><ChangeCell row={row} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}