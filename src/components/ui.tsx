import type { ButtonHTMLAttributes, ReactNode } from 'react';
import { AlertTriangle, CheckCircle2, Info, Loader2, XCircle } from 'lucide-react';

type Variant = 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger' | 'ai';
type Size = 'sm' | 'md' | 'lg';

const VARIANTS: Record<Variant, string> = {
  primary: 'bg-brand-700 text-white hover:bg-brand-800 shadow-sm',
  secondary: 'bg-ink text-white hover:bg-slate-800 shadow-sm',
  outline: 'border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 hover:border-slate-400',
  ghost: 'text-slate-600 hover:bg-slate-100 hover:text-slate-900',
  danger: 'border border-rose-200 bg-white text-rose-700 hover:bg-rose-50',
  ai: 'bg-indigo-600 text-white hover:bg-indigo-700 shadow-sm',
};

const SIZES: Record<Size, string> = {
  sm: 'h-8 px-3 text-xs gap-1.5',
  md: 'h-10 px-4 text-sm gap-2',
  lg: 'h-12 px-6 text-base gap-2.5',
};

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  icon?: ReactNode;
  loading?: boolean;
}

export function Button({ variant = 'primary', size = 'md', icon, loading, className = '', children, disabled, ...rest }: ButtonProps) {
  return (
    <button
      type="button"
      className={`inline-flex items-center justify-center rounded-xl font-semibold whitespace-nowrap transition-colors disabled:cursor-not-allowed disabled:opacity-60 cursor-pointer ${VARIANTS[variant]} ${SIZES[size]} ${className}`}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...rest}
    >
      {loading ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : icon}
      {children}
    </button>
  );
}

export function Card({ children, className = '', as: Tag = 'section' }: { children: ReactNode; className?: string; as?: 'section' | 'div' | 'article' }) {
  return <Tag className={`rounded-2xl border border-slate-200/80 bg-white shadow-card ${className}`}>{children}</Tag>;
}

type Tone = 'info' | 'success' | 'warning' | 'danger' | 'ai' | 'neutral';

const ALERT_TONES: Record<Tone, string> = {
  info: 'border-sky-200 bg-sky-50 text-sky-900',
  success: 'border-emerald-200 bg-emerald-50 text-emerald-900',
  warning: 'border-amber-200 bg-amber-50 text-amber-900',
  danger: 'border-rose-200 bg-rose-50 text-rose-900',
  ai: 'border-indigo-200 bg-indigo-50 text-indigo-950',
  neutral: 'border-slate-200 bg-slate-50 text-slate-700',
};

const ALERT_ICONS: Record<Tone, ReactNode> = {
  info: <Info className="h-4 w-4 text-sky-600" aria-hidden />,
  success: <CheckCircle2 className="h-4 w-4 text-emerald-600" aria-hidden />,
  warning: <AlertTriangle className="h-4 w-4 text-amber-600" aria-hidden />,
  danger: <XCircle className="h-4 w-4 text-rose-600" aria-hidden />,
  ai: <Info className="h-4 w-4 text-indigo-600" aria-hidden />,
  neutral: <Info className="h-4 w-4 text-slate-500" aria-hidden />,
};

export function Alert({ tone = 'info', title, children, action, className = '' }: { tone?: Tone; title?: ReactNode; children?: ReactNode; action?: ReactNode; className?: string }) {
  return (
    <div role={tone === 'danger' ? 'alert' : 'status'} className={`flex items-start gap-3 rounded-xl border px-4 py-3 text-sm ${ALERT_TONES[tone]} ${className}`}>
      <span className="mt-0.5 shrink-0">{ALERT_ICONS[tone]}</span>
      <div className="min-w-0 flex-1 space-y-0.5">
        {title && <p className="font-semibold">{title}</p>}
        {children && <div className="leading-relaxed opacity-90">{children}</div>}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}

export function Spinner({ label, className = '' }: { label?: string; className?: string }) {
  return (
    <span className={`inline-flex items-center gap-2 text-sm text-slate-600 ${className}`} role="status" aria-live="polite">
      <Loader2 className="h-4 w-4 animate-spin text-brand-600" aria-hidden />
      {label}
    </span>
  );
}

export function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`animate-pulse rounded-lg bg-slate-200/70 ${className}`} aria-hidden />;
}

export function EmptyState({ icon, title, body, action }: { icon: ReactNode; title: string; body?: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center px-6 py-12 text-center">
      <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-50 text-brand-700 ring-1 ring-brand-100">{icon}</div>
      <h3 className="font-display text-lg font-bold text-ink">{title}</h3>
      {body && <p className="mt-1 max-w-md text-sm text-slate-600">{body}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function Pill({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold ${className}`}>{children}</span>;
}