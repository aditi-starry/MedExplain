import { en } from './en';
import { hi } from './hi';
import { mr } from './mr';
import type { Dictionary, Language, TranslationKey } from './types';

export const DICTIONARIES: Record<Language, Dictionary> = { en, hi, mr };
export const LANGUAGES: { code: Language; label: string; english: string }[] = [
  { code: 'en', label: 'English', english: 'English' },
  { code: 'hi', label: 'हिन्दी', english: 'Hindi' },
  { code: 'mr', label: 'मराठी', english: 'Marathi' },
];

export type TFunction = (key: TranslationKey, vars?: Record<string, string | number>) => string;

export function translate(language: Language, key: TranslationKey, vars?: Record<string, string | number>): string {
  const template = DICTIONARIES[language][key] ?? en[key] ?? key;
  if (!vars) return template;
  return template.replace(/\{(\w+)\}/g, (match, name: string) => (name in vars ? String(vars[name]) : match));
}
