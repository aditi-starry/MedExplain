# MedExplain AI - upgrade progress checklist

Last updated: 2026-10-14

## Done
- [x] Audit: backend deps were not installed anywhere; frontend imported a missing `ProcessingPage` (build broken);
      Sprint 3 OCR tests were never collected by pytest; Gemini key was sent in the URL query string.
- [x] Backend venv (`backend/.venv`, Python 3.11) and baseline tests.
- [x] Knowledge base: 43 MedlinePlus sources / 78 paraphrased passages (`backend/knowledge/documents`), graph with 18 cited relationships (`backend/knowledge/graph.json`).
- [x] BM25 retriever + synonym expansion + missing-evidence threshold (`app/services/knowledge_base.py`).
- [x] Explanations rewritten: RAG + one batched Gemini call + validation + labelled fallback (`explanation_service.py`, `safety.py`, `insights.py`).
- [x] Chat (`chat_service.py`), insights + doctor questions, comparison + report date, PDF (ReportLab + HarfBuzz, en/hi/mr).
- [x] Security: per-report access tokens, unguessable IDs, magic-byte checks, retention purge, delete endpoint, rate limits, CORS from env, no stack traces.
- [x] Backend tests: 71 passing (mocked AI).

## Remaining
- [ ] Frontend: api client with tokens, i18n (en/hi/mr), redesign, chat, insights, sources, compare, PDF download, vitest tests, build.
- [ ] README, .env.example, .gitignore, git init + commit, GitHub publish, Render/Vercel deployment configs, smoke tests.

## Notes
- `backend/uploads/` holds files from earlier versions, including a real-looking 19-page lab report. Never commit; owner should delete if real.
