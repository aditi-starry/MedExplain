import { ArrowRight, BookOpenCheck, Clock3, Download, FileSearch, GitCompareArrows, HelpCircle, Layers, Lock, MessageCircle, ScanLine, ShieldCheck, Sparkles, Upload } from 'lucide-react';
import type { ReactNode } from 'react';
import { useI18n } from '../i18n';
import { Button } from '../components/ui';
import { StatusBadge } from '../components/StatusBadge';

interface HomePageProps {
  onUpload: () => void;
  onSample: () => void;
  retentionHours: number;
}

function Feature({ icon, title, body }: { icon: ReactNode; title: string; body: string }) {
  return (
    <div className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-card">
      <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-brand-50 text-brand-700 ring-1 ring-brand-100">{icon}</div>
      <h3 className="font-display font-bold text-ink">{title}</h3>
      <p className="mt-1 text-sm leading-relaxed text-slate-600">{body}</p>
    </div>
  );
}

/** Product preview built from the fictional sample report (labelled as such). */
function PreviewCard() {
  const { t } = useI18n();
  return (
    <div className="relative mx-auto w-full max-w-md" aria-hidden>
      <div className="absolute -inset-4 -z-10 rounded-[2rem] bg-gradient-to-br from-brand-100/70 via-white to-indigo-100/60 blur-2xl" />
      <div className="space-y-3 rounded-3xl border border-slate-200 bg-white p-5 shadow-lift">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Fictional example</span>
          <StatusBadge status="Below Range" size="sm" />
        </div>
        <div>
          <p className="text-sm font-medium text-slate-500">Hemoglobin</p>
          <p className="font-display text-3xl font-extrabold text-ink">11.2 <span className="text-base font-semibold text-slate-500">g/dL</span></p>
          <p className="text-xs text-slate-500">{t('results.range')}: 12.0 – 15.5 g/dL</p>
          <div className="relative mt-3 h-2 rounded-full bg-slate-100">
            <div className="absolute inset-y-0 left-[25%] right-[25%] rounded-full bg-emerald-100 ring-1 ring-inset ring-emerald-200" />
            <div className="absolute left-[17%] top-1/2 h-3.5 w-3.5 -translate-y-1/2 rounded-full border-2 border-white bg-sky-600 shadow" />
          </div>
        </div>
        <div className="rounded-2xl border border-indigo-100 bg-indigo-50/60 p-3.5">
          <p className="mb-1 flex items-center gap-1.5 text-xs font-semibold text-indigo-700">
            <Sparkles className="h-3.5 w-3.5" /> {t('ai.badge_ai')}
          </p>
          <p className="text-sm leading-relaxed text-slate-700">
            Your Hemoglobin of 11.2 g/dL is below the report&apos;s range of 12.0 – 15.5 g/dL. Low hemoglobin can be seen with iron deficiency or other types of anemia. <span className="font-semibold text-indigo-700">[1]</span>
          </p>
        </div>
        <div className="flex items-center gap-2 rounded-xl bg-slate-50 px-3 py-2 text-xs text-slate-600">
          <BookOpenCheck className="h-3.5 w-3.5 text-brand-600" />
          <span className="truncate">[1] Hemoglobin Test — MedlinePlus, U.S. National Library of Medicine</span>
        </div>
      </div>
    </div>
  );
}

export function HomePage({ onUpload, onSample, retentionHours }: HomePageProps) {
  const { t } = useI18n();
  return (
    <div className="animate-fade-in">
      <section className="mx-auto grid max-w-6xl items-center gap-12 px-4 pb-16 pt-12 sm:px-6 lg:grid-cols-[1.1fr_1fr] lg:pt-20">
        <div className="space-y-6">
          <span className="inline-flex items-center gap-2 rounded-full border border-brand-200 bg-brand-50 px-3 py-1 text-xs font-semibold text-brand-800">
            <ShieldCheck className="h-3.5 w-3.5" aria-hidden /> {t('home.badge')}
          </span>
          <h1 className="font-display text-4xl font-extrabold leading-[1.1] tracking-tight text-ink sm:text-5xl lg:text-6xl">
            {t('home.title_1')} <span className="text-brand-600">{t('home.title_2')}</span>
          </h1>
          <p className="max-w-xl text-lg leading-relaxed text-slate-600">{t('home.subtitle')}</p>
          <div className="flex flex-col gap-3 sm:flex-row">
            <Button size="lg" icon={<Upload className="h-5 w-5" aria-hidden />} onClick={onUpload}>
              {t('home.cta_upload')}
            </Button>
            <Button size="lg" variant="outline" icon={<FileSearch className="h-5 w-5" aria-hidden />} onClick={onSample}>
              {t('home.cta_sample')}
            </Button>
          </div>
          <p className="text-sm text-slate-500">{t('home.languages')}</p>
        </div>
        <PreviewCard />
      </section>

      <section className="border-y border-slate-200/80 bg-white">
        <div className="mx-auto max-w-6xl px-4 py-14 sm:px-6">
          <h2 className="font-display text-2xl font-bold text-ink sm:text-3xl">{t('home.how_title')}</h2>
          <ol className="mt-8 grid gap-6 md:grid-cols-3">
            {[
              { icon: <Upload className="h-5 w-5" />, title: t('home.step1_title'), body: t('home.step1_body') },
              { icon: <ScanLine className="h-5 w-5" />, title: t('home.step2_title'), body: t('home.step2_body') },
              { icon: <BookOpenCheck className="h-5 w-5" />, title: t('home.step3_title'), body: t('home.step3_body') },
            ].map((step, i) => (
              <li key={step.title} className="relative rounded-2xl bg-canvas p-6">
                <span className="absolute right-5 top-5 font-display text-4xl font-extrabold text-slate-200">{i + 1}</span>
                <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-brand-700 text-white">{step.icon}</div>
                <h3 className="font-display text-lg font-bold text-ink">{step.title}</h3>
                <p className="mt-1 text-sm leading-relaxed text-slate-600">{step.body}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-14 sm:px-6">
        <h2 className="font-display text-2xl font-bold text-ink sm:text-3xl">{t('home.trust_title')}</h2>
        <div className="mt-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          <Feature icon={<Lock className="h-5 w-5" />} title={t('home.trust1_title')} body={t('home.trust1_body')} />
          <Feature icon={<BookOpenCheck className="h-5 w-5" />} title={t('home.trust2_title')} body={t('home.trust2_body')} />
          <Feature icon={<HelpCircle className="h-5 w-5" />} title={t('home.trust3_title')} body={t('home.trust3_body')} />
          <Feature icon={<Clock3 className="h-5 w-5" />} title={t('home.trust4_title')} body={t('home.trust4_body', { hours: retentionHours })} />
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 sm:px-6">
        <div className="rounded-3xl bg-ink px-6 py-10 text-white sm:px-10">
          <h2 className="font-display text-2xl font-bold">{t('home.features_title')}</h2>
          <ul className="mt-6 grid gap-x-8 gap-y-4 sm:grid-cols-2 lg:grid-cols-3">
            {[
              { icon: <Sparkles className="h-4 w-4" />, text: t('home.feature_explain') },
              { icon: <MessageCircle className="h-4 w-4" />, text: t('home.feature_chat') },
              { icon: <Layers className="h-4 w-4" />, text: t('home.feature_insights') },
              { icon: <HelpCircle className="h-4 w-4" />, text: t('home.feature_questions') },
              { icon: <GitCompareArrows className="h-4 w-4" />, text: t('home.feature_compare') },
              { icon: <Download className="h-4 w-4" />, text: t('home.feature_pdf') },
            ].map((f) => (
              <li key={f.text} className="flex items-center gap-3 text-sm text-slate-200">
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-white/10 text-brand-200">{f.icon}</span>
                {f.text}
              </li>
            ))}
          </ul>
          <Button className="mt-8" variant="outline" icon={<ArrowRight className="h-4 w-4" aria-hidden />} onClick={onUpload}>
            {t('home.cta_upload')}
          </Button>
        </div>
      </section>
    </div>
  );
}