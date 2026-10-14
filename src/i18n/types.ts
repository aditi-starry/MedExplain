import type { TranslationKey } from './en';

export type Language = 'en' | 'hi' | 'mr';
export type Dictionary = Record<TranslationKey, string>;
export type { TranslationKey };