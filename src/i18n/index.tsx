import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { translate } from './core';
import type { TFunction } from './core';
import type { Language } from './types';

// eslint-disable-next-line react-refresh/only-export-components
export { LANGUAGES, translate } from './core';
export type { TFunction } from './core';

const STORAGE_KEY = 'medexplain.language';

function initialLanguage(): Language {
  try {
    const saved = window.localStorage.getItem(STORAGE_KEY);
    if (saved === 'en' || saved === 'hi' || saved === 'mr') return saved;
  } catch {
    // Storage can be unavailable (private mode); fall back to English
  }
  return 'en';
}

interface I18nValue {
  language: Language;
  setLanguage: (language: Language) => void;
  t: TFunction;
}

const I18nContext = createContext<I18nValue | null>(null);

export function I18nProvider({ children, initial }: { children: ReactNode; initial?: Language }) {
  const [language, setLanguageState] = useState<Language>(() => initial ?? initialLanguage());

  const setLanguage = useCallback((next: Language) => {
    setLanguageState(next);
    try {
      window.localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // Preference simply will not persist
    }
  }, []);

  useEffect(() => {
    document.documentElement.lang = language;
  }, [language]);

  const t = useCallback<TFunction>((key, vars) => translate(language, key, vars), [language]);
  const value = useMemo(() => ({ language, setLanguage, t }), [language, setLanguage, t]);
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useI18n(): I18nValue {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error('useI18n must be used inside I18nProvider');
  return ctx;
}