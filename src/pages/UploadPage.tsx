import { useRef, useState } from 'react';
import type { DragEvent } from 'react';
import { Check, FileText, FlaskConical, Loader2, ShieldCheck, UploadCloud, X } from 'lucide-react';
import { useI18n } from '../i18n';
import { Alert, Button, Card } from '../components/ui';
import { MAX_UPLOAD_MB, errorMessage, loadSampleFile, uploadAndExtract, validateFile } from '../services/reportFlow';
import type { UploadStep } from '../services/reportFlow';

interface UploadPageProps {
  onDone: (reportId: string) => void;
  retentionHours: number;
  ocrAvailable: boolean | null;
}

const STEPS: { key: UploadStep | 'evaluate'; label: 'steps.upload' | 'steps.extract' | 'steps.evaluate' }[] = [
  { key: 'upload', label: 'steps.upload' },
  { key: 'extract', label: 'steps.extract' },
  { key: 'evaluate', label: 'steps.evaluate' },
];

function formatSize(bytes: number): string {
  return bytes < 1024 * 1024 ? `${Math.max(1, Math.round(bytes / 1024))} KB` : `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function UploadPage({ onDone, retentionHours, ocrAvailable }: UploadPageProps) {
  const { t } = useI18n();
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [step, setStep] = useState<UploadStep | null>(null);
  const busy = step !== null && step !== 'done';

  const choose = (candidate: File | undefined | null) => {
    if (!candidate) return;
    const problem = validateFile(candidate, t);
    setError(problem);
    setFile(problem ? null : candidate);
  };

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragging(false);
    if (!busy) choose(e.dataTransfer.files?.[0]);
  };

  const analyze = async (target: File | null = file) => {
    if (!target) return;
    setError(null);
    try {
      const { auth } = await uploadAndExtract(target, setStep);
      onDone(auth.reportId);
    } catch (err) {
      setStep(null);
      setError(errorMessage(err, t));
    }
  };

  const useSample = async () => {
    try {
      const sample = await loadSampleFile('/sample_lab_report.pdf', 'Fictional_Sample_Lab_Report.pdf');
      setFile(sample);
      await analyze(sample);
    } catch (err) {
      setError(errorMessage(err, t));
    }
  };

  const stepIndex = step === 'upload' ? 0 : step === 'extract' ? 1 : step === 'done' ? 3 : -1;

  return (
    <div className="mx-auto max-w-3xl animate-fade-in space-y-6 px-4 py-10 sm:px-6">
      <div className="space-y-2">
        <h1 className="font-display text-3xl font-extrabold tracking-tight text-ink sm:text-4xl">{t('upload.title')}</h1>
        <p className="text-slate-600">{t('upload.subtitle')}</p>
      </div>

      {error && <Alert tone="danger" title={t('upload.error_title')}>{error}</Alert>}

      {!file ? (
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          className={`rounded-3xl border-2 border-dashed p-8 text-center transition-colors sm:p-12 ${dragging ? 'border-brand-500 bg-brand-50' : 'border-slate-300 bg-white hover:border-brand-400'}`}
        >
          <div className={`mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl ${dragging ? 'bg-brand-700 text-white' : 'bg-brand-50 text-brand-700 ring-1 ring-brand-100'}`}>
            <UploadCloud className="h-7 w-7" aria-hidden />
          </div>
          <p className="font-display text-lg font-bold text-ink">{t('upload.drop_title')}</p>
          <p className="mt-1 text-sm text-slate-600">
            {t('upload.drop_or')}{' '}
            <button type="button" onClick={() => inputRef.current?.click()} className="font-semibold text-brand-700 underline underline-offset-4 hover:text-brand-800 cursor-pointer">
              {t('upload.browse')}
            </button>
          </p>
          <p className="mt-4 text-xs text-slate-500">{t('upload.formats', { max: MAX_UPLOAD_MB })}</p>
          {ocrAvailable === false && <p className="mx-auto mt-3 max-w-md text-xs text-amber-800">{t('upload.ocr_unavailable')}</p>}
          <input
            ref={inputRef}
            type="file"
            accept=".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg"
            className="sr-only"
            aria-label={t('upload.browse')}
            onChange={(e) => {
              choose(e.target.files?.[0]);
              e.target.value = '';
            }}
          />
        </div>
      ) : (
        <Card className="p-5">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">{t('upload.selected')}</p>
          <div className="mt-3 flex items-center gap-3">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-700">
              <FileText className="h-5 w-5" aria-hidden />
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate font-semibold text-ink" title={file.name}>{file.name}</p>
              <p className="text-xs text-slate-500">{formatSize(file.size)}</p>
            </div>
            {!busy && (
              <button onClick={() => { setFile(null); setStep(null); }} className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-700 cursor-pointer" aria-label={t('upload.remove')}>
                <X className="h-4 w-4" />
              </button>
            )}
          </div>

          {step && (
            <ol className="mt-5 space-y-2.5" aria-live="polite">
              {STEPS.map((s, i) => {
                const state = stepIndex > i || (s.key === 'evaluate' && stepIndex === 3) ? 'done' : stepIndex === i ? 'active' : 'pending';
                return (
                  <li key={s.key} className="flex items-center gap-3 text-sm">
                    <span className={`flex h-6 w-6 items-center justify-center rounded-full ${state === 'done' ? 'bg-emerald-500 text-white' : state === 'active' ? 'bg-brand-100 text-brand-700' : 'bg-slate-100 text-slate-400'}`}>
                      {state === 'done' ? <Check className="h-3.5 w-3.5" /> : state === 'active' ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <span className="h-1.5 w-1.5 rounded-full bg-current" />}
                    </span>
                    <span className={state === 'pending' ? 'text-slate-400' : 'text-slate-700'}>{t(s.label)}</span>
                  </li>
                );
              })}
            </ol>
          )}

          <div className="mt-5 flex justify-end">
            <Button onClick={() => analyze()} loading={busy} size="lg">
              {t('upload.analyze')}
            </Button>
          </div>
        </Card>
      )}

      {!file && (
        <div className="flex flex-col items-start justify-between gap-3 rounded-2xl border border-slate-200 bg-white px-5 py-4 sm:flex-row sm:items-center">
          <span className="flex items-center gap-2 text-sm text-slate-600">
            <FlaskConical className="h-4 w-4 text-brand-600" aria-hidden /> {t('upload.sample_hint')}
          </span>
          <Button variant="outline" size="sm" onClick={useSample} loading={busy}>
            {t('upload.sample_btn')}
          </Button>
        </div>
      )}

      <Card className="p-5">
        <h2 className="flex items-center gap-2 font-display font-bold text-ink">
          <ShieldCheck className="h-4 w-4 text-brand-600" aria-hidden /> {t('upload.privacy_title')}
        </h2>
        <ul className="mt-3 space-y-2 text-sm leading-relaxed text-slate-600">
          <li className="flex gap-2"><span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-brand-500" />{t('upload.privacy_1')}</li>
          <li className="flex gap-2"><span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-brand-500" />{t('upload.privacy_2')}</li>
          <li className="flex gap-2"><span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-brand-500" />{t('upload.privacy_3', { hours: retentionHours })}</li>
        </ul>
      </Card>
    </div>
  );
}