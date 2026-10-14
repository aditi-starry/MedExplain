# MedExplain AI

MedExplain AI helps people understand their **own laboratory reports**. It reads an uploaded
blood-test report, compares every value with the reference range printed on that report, and
explains the results in plain **English, हिन्दी or मराठी** — with links to the trusted sources
each explanation used.

> **Medical disclaimer.** MedExplain AI is an educational tool. It does not diagnose, treat,
> or replace a qualified healthcare professional, and it is not a medical device. Extracted
> values can contain OCR or parsing errors — always check them against the original report.
> In an emergency, contact your local emergency services. Use fictional or anonymised reports
> with the public demo.

## Features

| Area | What it does |
|---|---|
| Extraction | Digital PDFs via PyMuPDF; scanned PDFs/photos via PaddleOCR when installed. Rule-based extraction of 50+ common tests, values, units and printed ranges. |
| Evaluation | Deterministic Python code labels each result *Within / Above / Below range* or *Not evaluated* using only the report's own range. AI never changes values, units, ranges or statuses. |
| Explanations (RAG) | Each result's evidence is retrieved from a curated MedlinePlus knowledge base, then **one batched Gemini call** writes 1–3 sentence explanations about the actual value. Output is validated (citations, numbers, direction, language, unsafe claims); anything that fails is replaced by a clearly labelled automatic summary. |
| Evidence & traceability | Numbered citations with source title, publisher, URL and update date; report data, AI text and general evidence are visually distinct; missing evidence is stated. |
| Explainable AI | "Why this explanation?" shows the value considered, the range used, the arithmetic comparison, the reasoning rule and limitations — a checkable rationale, not model chain-of-thought. |
| Multi-parameter insights | A small knowledge graph of 18 documented relationships (each citing a source passage) highlights results usually read together, e.g. hemoglobin + ferritin. Patterns are never presented as diagnoses. |
| Chatbot | Report-aware Q&A grounded in the report and retrieved passages, with follow-up context, emergency-message handling, unsafe-answer blocking, sources and retry. |
| Doctor questions | Report-specific discussion prompts (AI, validated; deterministic templates as fallback). |
| Comparison | Compares two reports deterministically: difference, % change, dates, unit compatibility checks; no "better/worse" labels. |
| PDF summary | ReportLab PDF with results, explanations, questions, sources and disclaimers in en/hi/mr (HarfBuzz shaping for Devanagari). Generated on the server; no external PDF service. |
| Languages | Full UI, explanations, chat, questions and PDF in English, Hindi and Marathi. Translations are AI-assisted and **not clinically validated**. |

## Architecture

```
React + Vite + Tailwind (Vercel)                     FastAPI (Render)
┌──────────────────────────┐   X-Report-Token    ┌──────────────────────────────────────────┐
│ Upload → Report workspace │ ───────────────────▶│ storage (per-report token, 24 h retention)│
│ Results · Insights · Ask  │                     │ PyMuPDF / PaddleOCR → parameter_extractor │
│ Compare · PDF · en/hi/mr  │ ◀─────────────────── │ deterministic evaluation (report ranges)  │
└──────────────────────────┘        JSON          │ knowledge_base: BM25 retriever + graph    │
                                                  │ explanation_service / chat_service        │
                                                  │   └─ llm_client → Gemini (JSON mode)       │
                                                  │ safety validators → fallback if needed     │
                                                  │ insights · comparison · pdf_service        │
                                                  └──────────────────────────────────────────┘
```

RAG flow: validated report data → retrieval (parameter names + synonyms + question) →
evidence with source metadata → Gemini → validation → patient-facing output with citations.

**Why BM25 and not a vector database?** The knowledge base is small (78 passages) and curated.
A dependency-free BM25 retriever with synonym expansion from the graph is accurate here,
deterministic, testable, and fits a 512 MB free-tier server, where ChromaDB plus an embedding
model would not. Relevance thresholds give explicit "no evidence found" results.

## Project structure

```
├── src/                         React app
│   ├── components/              UI primitives, header/footer, report/* panels
│   ├── i18n/                    en.ts, hi.ts, mr.ts dictionaries + provider
│   ├── pages/                   HomePage, UploadPage, ReportPage
│   ├── services/                api.ts (client), session.ts, reportFlow.ts
│   └── test/                    Vitest + Testing Library tests
├── public/                      fictional sample reports
├── backend/
│   ├── app/
│   │   ├── routes/              health, reports API
│   │   ├── services/            extraction, evaluation, knowledge_base, explanation, chat,
│   │   │                        insights, comparison, pdf, safety, i18n, llm_client, storage
│   │   ├── assets/fonts/        Noto Sans + Noto Sans Devanagari (SIL OFL)
│   │   ├── security.py          tokens, IDs, rate limiting
│   │   └── main.py
│   ├── knowledge/               curated sources + graph (see knowledge/README.md)
│   ├── scripts/                 make_sample_reports.py, validate_knowledge.py
│   └── test_*.py                pytest suites
├── render.yaml                  backend deployment (Render Blueprint)
└── vercel.json                  frontend deployment
```

## Local setup

Requirements: Node 20+, Python 3.11.

```bash
# Backend
cd backend
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt   # add requirements-ocr.txt for scanned reports
copy .env.example .env            # macOS/Linux: cp; then set GEMINI_API_KEY
python -m uvicorn app.main:app --reload --port 8000

# Frontend (new terminal, project root)
npm install
npm run dev                       # http://localhost:5173
```

If port 8000 is taken, run the backend on another port and create `.env.local` with
`VITE_API_BASE_URL=http://localhost:<port>`. Without a Gemini key, the app still works and
labels every explanation as an automatic, rule-based summary.

## Environment variables

Backend (`backend/.env`, or the hosting dashboard):

| Name | Purpose |
|---|---|
| `GEMINI_API_KEY` | Gemini API key (secret). Empty = AI disabled. |
| `GEMINI_MODEL`, `GEMINI_FALLBACK_MODELS` | Model and fallbacks (defaults `gemini-3.1-flash-lite`, `gemini-flash-lite-latest`). |
| `ALLOWED_ORIGINS`, `ALLOWED_ORIGIN_REGEX` | CORS: deployed frontend URL(s). |
| `ENVIRONMENT` | `development` / `production`. |
| `DATA_DIR`, `REPORT_RETENTION_HOURS` | Storage location; automatic deletion (default 24 h). |
| `ENABLE_OCR` | `false` on hosts without PaddleOCR. |
| `RATE_LIMIT_UPLOADS_PER_MINUTE`, `RATE_LIMIT_AI_PER_MINUTE` | Per-IP limits. |

Frontend (build time): `VITE_API_BASE_URL` — the backend URL. Never put secrets in `VITE_*` variables.

## Testing

```bash
cd backend && python -m pytest          # 72 tests, AI calls mocked, no key or network needed
python scripts/validate_knowledge.py    # knowledge base consistency
cd .. && npm test                        # 25 Vitest tests (UI flows, i18n, API client)
npm run lint && npm run build
```

## Deployment (free tiers)

**Backend — Render** (free web service: spins down after 15 min idle, ~1 min cold start,
ephemeral disk, 750 free hours/month, no payment method needed):
1. Render dashboard → **New → Blueprint** → select this GitHub repo (uses `render.yaml`).
2. Set `GEMINI_API_KEY` and `ALLOWED_ORIGINS` (your Vercel URL) when prompted.
3. Check `https://<service>.onrender.com/api/health`.

**Frontend — Vercel** (Hobby plan: free, personal/non-commercial use):
1. Vercel → **Add New Project** → import the repo (framework: Vite).
2. Set `VITE_API_BASE_URL=https://<service>.onrender.com` and deploy.
3. Put the Vercel URL in Render's `ALLOWED_ORIGINS` and redeploy the backend.

The free backend does not include OCR (PaddleOCR is too large for 512 MB); scanned reports
receive a clear "OCR not available" message. Because the disk is ephemeral, reports can
disappear when the service sleeps; the UI then asks the user to upload again.

## Security and privacy

- Secrets only in environment variables; `.env` files and `backend/uploads/` are git-ignored.
- Every report gets an unguessable ID and a random access token (only its SHA-256 hash is
  stored). All report endpoints require the token, so knowing an ID is not enough. The browser
  keeps tokens in `sessionStorage` only.
- Upload validation: extension, MIME type, magic bytes, 10 MB size cap, page limit, sanitised
  file names (no path traversal). Malformed IDs and wrong tokens return the same 404.
- Automatic deletion after 24 h, plus a Delete button. No chat transcripts are stored.
- Only test names, values, units and ranges (plus typed chat questions) go to Gemini — never
  the file or patient name. On Gemini's **free tier, Google may use submitted content to improve
  its products and human reviewers may read it**, so do not use real patient reports there.
- Gemini key sent in a header (not the URL); logs never include report content or keys;
  generic 500 responses without stack traces; restricted CORS; rate limits; security headers.
- No regulatory compliance (HIPAA, GDPR, DPDP, etc.) is claimed; a proper assessment would be
  needed before handling real patient data.

## Medical safety design

AI output is accepted only if it: uses the requested language, cites only retrieved passage
ids, contains only numbers present in the report or cited evidence, describes the result in the
same direction as the deterministic status, and contains no diagnosis or medication
instructions. Otherwise it is replaced by deterministic text and labelled. Emergency phrases in
chat get a fixed "contact emergency services" reply without calling the AI.

## Maintenance

- Knowledge sources: see `backend/knowledge/README.md` (add, update, validate).
- Sample reports: `python backend/scripts/make_sample_reports.py` (fictional data only).
- UI text: edit `src/i18n/en.ts`, then `hi.ts` and `mr.ts` (a test enforces identical keys).