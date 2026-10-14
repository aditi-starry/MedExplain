import { describe, expect, it } from 'vitest';
import { en } from '../i18n/en';
import { hi } from '../i18n/hi';
import { mr } from '../i18n/mr';
import { translate } from '../i18n/core';
import { parseHash, routeToHash } from '../hooks/useHashRoute';
import { formatRange, formatValue, signed } from '../utils/format';
import { PARAMS } from './fixtures';

const placeholders = (s: string) => (s.match(/\{\w+\}/g) ?? []).sort().join(',');

describe('translations', () => {
  it('Hindi and Marathi define exactly the English keys', () => {
    const keys = Object.keys(en).sort();
    expect(Object.keys(hi).sort()).toEqual(keys);
    expect(Object.keys(mr).sort()).toEqual(keys);
  });

  it('keep the same placeholders in every language', () => {
    for (const key of Object.keys(en) as (keyof typeof en)[]) {
      expect(placeholders(hi[key]), key).toBe(placeholders(en[key]));
      expect(placeholders(mr[key]), key).toBe(placeholders(en[key]));
    }
  });

  it('Hindi and Marathi strings are written in Devanagari', () => {
    expect(hi['tabs.results']).toMatch(/[\u0900-\u097f]/);
    expect(mr['report.download_pdf']).toMatch(/[\u0900-\u097f]/);
  });

  it('interpolates values and preserves numbers and names', () => {
    expect(translate('hi', 'chat.s3', { name: 'Hemoglobin' })).toContain('Hemoglobin');
    expect(translate('en', 'upload.formats', { max: 10 })).toBe('PDF, PNG or JPG · up to 10 MB');
  });
});

describe('routing and formatting', () => {
  it('parses report routes and rejects malformed ids', () => {
    expect(parseHash('#/report/rep_0123456789abcdef01234567')).toEqual({ name: 'report', reportId: 'rep_0123456789abcdef01234567' });
    expect(parseHash('#/report/../../etc')).toEqual({ name: 'home' });
    expect(routeToHash({ name: 'upload' })).toBe('#/upload');
  });

  it('formats values and printed ranges without inventing data', () => {
    expect(formatValue(PARAMS[0])).toBe('11.2 g/dL');
    expect(formatRange(PARAMS[0])).toBe('12.0 - 15.5 g/dL');
    expect(formatRange({ ...PARAMS[0], referenceRaw: null, referenceLow: null, referenceHigh: null })).toBeNull();
    expect(signed(-1.2)).toBe('−1.2');
    expect(formatValue({ value: 3.9, unit: 'x10^6/uL' })).toBe('3.9 ×10⁶/µL');
    expect(formatValue({ value: 2.1, unit: 'uIU/mL' })).toBe('2.1 µIU/mL');
  });
});