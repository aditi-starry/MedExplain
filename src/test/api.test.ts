import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiError, askQuestion, explainReport, uploadReport } from '../services/api';
import { REPORT_ID, TOKEN } from './fixtures';

const auth = { reportId: REPORT_ID, token: TOKEN };

function mockFetch(status: number, body: unknown) {
  const fn = vi.fn().mockResolvedValue(new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }));
  vi.stubGlobal('fetch', fn);
  return fn;
}

afterEach(() => vi.unstubAllGlobals());

describe('api client', () => {
  it('sends the access token in a header, never in the URL', async () => {
    const fetchMock = mockFetch(200, { source: 'ai' });
    await explainReport(auth, 'mr', true);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).not.toContain(TOKEN);
    expect(new Headers(init.headers).get('X-Report-Token')).toBe(TOKEN);
    expect(JSON.parse(init.body)).toEqual({ language: 'mr', refresh: true });
  });

  it('maps HTTP errors to typed ApiErrors', async () => {
    mockFetch(404, { detail: 'Report not found.' });
    await expect(explainReport(auth, 'en')).rejects.toMatchObject({ kind: 'not_found', status: 404 });
    mockFetch(429, { detail: 'Too many requests.' });
    await expect(askQuestion(auth, 'hi', [], 'en')).rejects.toMatchObject({ kind: 'rate_limited' });
    mockFetch(400, { detail: 'Unsupported file format' });
    await expect(uploadReport(new File(['x'], 'a.txt'))).rejects.toMatchObject({ kind: 'bad_request', message: 'Unsupported file format' });
  });

  it('reports network failures distinctly', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));
    const err = await explainReport(auth, 'en').catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.kind).toBe('network');
  });

  it('limits chat history sent to the server', async () => {
    const fetchMock = mockFetch(200, { answer: 'ok' });
    const history = Array.from({ length: 30 }, (_, i) => ({ role: 'user' as const, content: `q${i}` }));
    await askQuestion(auth, 'next', history, 'hi');
    const body = JSON.parse(fetchMock.mock.calls[0][1].body);
    expect(body.history).toHaveLength(12);
    expect(body.language).toBe('hi');
  });
});