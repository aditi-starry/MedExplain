import { useEffect, useRef, useState } from 'react';
import type { FormEvent, KeyboardEvent } from 'react';
import { Bot, Eraser, Send, ShieldAlert, User, Wand2 } from 'lucide-react';
import { useI18n } from '../../i18n';
import { askQuestion } from '../../services/api';
import type { ReportAuth } from '../../services/api';
import { errorMessage } from '../../services/reportFlow';
import type { ChatResponse, ChatTurn, ExtractedParameter } from '../../types/medical';
import { isOutside } from '../../utils/format';
import { Alert, Button, Card, Spinner } from '../ui';
import { SourceList } from './SourceList';

const MAX_LEN = 1000;

interface Message {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  response?: ChatResponse;
}

// A conversation belongs to exactly one report: ReportPage is keyed by report ID, so a new report starts a new chat.
export function ChatPanel({ auth, parameters }: { auth: ReportAuth; parameters: ExtractedParameter[] }) {
  const { t, language } = useI18n();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<{ text: string; retry: string } | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const nextId = useRef(1);

  useEffect(() => {
    endRef.current?.scrollIntoView?.({ behavior: 'smooth', block: 'nearest' });
  }, [messages, pending]);

  const outside = parameters.filter(isOutside);
  const example = (outside[0] ?? parameters[0])?.name;
  const suggestions = [t('chat.s1'), t('chat.s2')];
  if (example) suggestions.push(outside.length ? t('chat.s3', { name: example }) : t('chat.s4', { name: example }));

  const send = async (text: string) => {
    const question = text.trim().slice(0, MAX_LEN);
    if (!question || pending) return;
    const history: ChatTurn[] = messages.map((m) => ({ role: m.role, content: m.content }));
    setMessages((prev) => [...prev, { id: nextId.current++, role: 'user', content: question }]);
    setInput('');
    setError(null);
    setPending(true);
    try {
      const response = await askQuestion(auth, question, history, language);
      setMessages((prev) => [...prev, { id: nextId.current++, role: 'assistant', content: response.answer, response }]);
    } catch (err) {
      // Remove the unanswered question so a retry does not duplicate it
      setMessages((prev) => prev.slice(0, -1));
      setError({ text: errorMessage(err, t), retry: question });
    } finally {
      setPending(false);
    }
  };

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    void send(input);
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      void send(input);
    }
  };

  return (
    <Card className="flex min-h-[32rem] flex-col overflow-hidden">
      <div className="flex items-start justify-between gap-3 border-b border-slate-100 p-5">
        <div>
          <h2 className="font-display text-lg font-bold text-ink">{t('chat.title')}</h2>
          <p className="text-sm text-slate-600">{t('chat.subtitle')}</p>
        </div>
        {messages.length > 0 && (
          <Button variant="ghost" size="sm" onClick={() => setMessages([])} icon={<Eraser className="h-3.5 w-3.5" aria-hidden />}>
            {t('chat.clear')}
          </Button>
        )}
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto bg-canvas/60 p-5 scrollbar-thin" aria-live="polite">
        {messages.length === 0 && (
          <div className="space-y-3">
            <p className="text-sm text-slate-600">{t('chat.empty')}</p>
            <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap">
              {suggestions.map((s) => (
                <button
                  key={s}
                  onClick={() => void send(s)}
                  className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-left text-sm text-slate-700 shadow-sm hover:border-brand-300 hover:text-brand-800 cursor-pointer"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m) =>
          m.role === 'user' ? (
            <div key={m.id} className="flex justify-end gap-2 animate-rise">
              <div className="max-w-[85%] rounded-2xl rounded-tr-sm bg-brand-700 px-4 py-2.5 text-sm leading-relaxed text-white">
                <span className="sr-only">{t('chat.you')}: </span>
                {m.content}
              </div>
              <span className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-brand-100 text-brand-800" aria-hidden>
                <User className="h-4 w-4" />
              </span>
            </div>
          ) : (
            <div key={m.id} className="flex gap-2 animate-rise">
              <span className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-indigo-700" aria-hidden>
                <Bot className="h-4 w-4" />
              </span>
              <div className="max-w-[85%] space-y-2 rounded-2xl rounded-tl-sm border border-slate-200 bg-white px-4 py-3 text-sm leading-relaxed text-slate-800 shadow-sm">
                <span className="sr-only">{t('chat.assistant')}: </span>
                {m.response?.source === 'safety' && (
                  <span className="mb-1 inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-semibold text-amber-900">
                    <ShieldAlert className="h-3 w-3" aria-hidden /> {t('chat.label_safety')}
                  </span>
                )}
                {m.response?.source === 'fallback' && (
                  <span className="mb-1 inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-700">
                    <Wand2 className="h-3 w-3" aria-hidden /> {t('chat.label_fallback')}
                  </span>
                )}
                <p className="whitespace-pre-line">{m.content}</p>
                {m.response?.notice && <p className="text-xs text-slate-500">{m.response.notice}</p>}
                {m.response && m.response.citations.length > 0 && <SourceList sources={m.response.citations} collapsible />}
              </div>
            </div>
          ),
        )}

        {pending && <Spinner label={t('chat.thinking')} className="pl-9" />}
        {error && (
          <Alert tone="danger" title={t('chat.error')} action={<Button size="sm" variant="outline" onClick={() => void send(error.retry)}>{t('common.retry')}</Button>}>
            {error.text}
          </Alert>
        )}
        <div ref={endRef} />
      </div>

      <form onSubmit={onSubmit} className="border-t border-slate-100 bg-white p-3">
        <div className="flex items-end gap-2">
          <label className="min-w-0 flex-1">
            <span className="sr-only">{t('chat.placeholder')}</span>
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value.slice(0, MAX_LEN))}
              onKeyDown={onKeyDown}
              rows={2}
              placeholder={t('chat.placeholder')}
              className="block max-h-40 min-h-[2.75rem] w-full resize-y rounded-xl border border-slate-200 px-3 py-2.5 text-sm placeholder:text-slate-400"
            />
          </label>
          <Button type="submit" icon={<Send className="h-4 w-4" aria-hidden />} disabled={!input.trim() || pending} aria-label={t('chat.send')}>
            <span className="hidden sm:inline">{t('chat.send')}</span>
          </Button>
        </div>
        <p className="mt-1 text-right text-[11px] text-slate-400">{t('chat.limit', { count: input.length, max: MAX_LEN })}</p>
      </form>
    </Card>
  );
}