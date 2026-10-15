# MedExplain AI 🩺

[![React 19](https://img.shields.io/badge/React-19.2-blue?logo=react)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-6.0-blue?logo=typescript)](https://www.typescriptlang.org/)
[![Vite](https://img.shields.io/badge/Vite-8.3-646CFF?logo=vite)](https://vitejs.dev/)
[![Tailwind CSS v4](https://img.shields.io/badge/Tailwind-v4.3-38B2AC?logo=tailwind-css)](https://tailwindcss.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.143-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?logo=python)](https://www.python.org/)
[![Gemini AI](https://img.shields.io/badge/Google_Gemini-Flash_Lite-4285F4?logo=google)](https://deepmind.google/technologies/gemini/)
[![Languages](https://img.shields.io/badge/Languages-EN%20%7C%20%E0%A4%B9%E0%A4%BF%E0%A4%A8%E0%A5%8D%E0%A4%A6%E0%A5%80%20%7C%20%E0%A4%AE%E0%A4%B0%E0%A4%BE%E0%A4%A0%E0%A5%80-orange)](#multilingual-support)
[![License](https://img.shields.io/badge/License-MIT%20%2F%20Educational-green)](#license)

**MedExplain AI** is an open-source, evidence-grounded laboratory report analysis system. It empowers patients and caregivers to interpret their **blood tests and diagnostic lab panels** by comparing extracted test values against the laboratory's specific printed reference ranges and providing plain-language explanations in **English, Hindi (हिन्दी), and Marathi (मराठी)**.

Every AI-generated insight is grounded in a verified **MedlinePlus (National Library of Medicine)** clinical knowledge base, with full citation traceability, safety validation, explainable decision rationales, and emergency escalation mechanisms.

---

> ### ⚠️ Critical Medical & Legal Disclaimer
> **MedExplain AI is strictly an educational tool and does not provide medical diagnoses, treatment recommendations, clinical decisions, or replace qualified healthcare providers.**
> - Diagnostic lab interpretation requires comprehensive clinical context, patient history, physical examination, and professional judgment.
> - Optical Character Recognition (OCR) and document parsing can occasionally misread values, decimals, or units. Users must always verify extracted values against their physical laboratory document.
> - **In case of a medical emergency, acute symptoms, or critical health concerns, immediately contact your local emergency services (e.g., 911, 112) or visit the nearest emergency department.**

---

## 📑 Table of Contents

- [Core Capabilities](#-core-capabilities)
- [System Architecture](#-system-architecture)
- [RAG & Clinical Knowledge Base](#-rag--clinical-knowledge-base)
- [Medical Safety & Validation Pipeline](#-medical-safety--validation-pipeline)
- [Project Structure](#-project-structure)
- [REST API Reference](#-rest-api-reference)
- [Getting Started](#-getting-started)
  - [Prerequisites](#prerequisites)
  - [Backend Setup](#backend-setup)
  - [Frontend Setup](#frontend-setup)
  - [OCR Setup (Optional)](#ocr-setup-optional)
- [Configuration & Environment Variables](#-configuration--environment-variables)
- [Testing & Quality Assurance](#-testing--quality-assurance)
- [Deployment Guide](#-deployment-guide)
  - [Backend on Render](#backend-on-render)
  - [Frontend on Vercel](#frontend-on-vercel)
- [Security, Privacy & Data Lifecycle](#-security-privacy--data-lifecycle)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🌟 Core Capabilities

| Capability | Technical Details |
|---|---|
| **Intelligent Document Parsing** | Dual-engine document extraction: native vector parsing for digital PDFs via **PyMuPDF**, and OCR fallback for scanned reports and photos via **PaddleOCR**. Extracts 50+ blood parameters, extracted values, units, and printed reference ranges. |
| **Deterministic Range Evaluation** | Pure rule-based Python logic evaluates each parameter against the report's printed reference range: `Within range`, `Above range`, `Below range`, or `Not evaluated`. **AI is never permitted to modify or infer values, units, or statuses.** |
| **Evidence-Grounded Explanations (RAG)** | Retrieves authoritative passages from a curated MedlinePlus repository using BM25 and synonym graph expansion. A single batched Google Gemini call generates concise, 1–3 sentence patient-friendly summaries grounded strictly in retrieved evidence. |
| **Full Citation Traceability** | Explanations feature numbered, clickable citations detailing source title, publisher (e.g., MedlinePlus / NLM), direct URL, and revision date. Unsubstantiated claims are purged. |
| **Explainable AI Rationale** | Transparent *"Why this explanation?"* inspector surfaces the exact input value, the laboratory-printed range, the arithmetic comparison rule, and known clinical boundary limitations. |
| **Multi-Parameter Knowledge Graph** | Clinical relationship graph (18 documented interactions across common panels) highlights correlated biomarkers (e.g., Hemoglobin + Ferritin, ALT + AST, BUN + Creatinine) without asserting synthetic diagnoses. |
| **Context-Aware Report Chatbot** | Conversational assistant bound to the parsed report metrics and retrieved reference literature. Supports follow-up inquiries, rejects unsafe diagnostic/prescriptive prompts, and detects emergency keywords. |
| **Doctor Discussion Prompts** | Synthesizes clinically relevant, non-alarmist questions for patients to ask their physician during their next consultation. |
| **Longitudinal Report Comparison** | Compare two distinct lab dates deterministically: computes absolute deltas, percentage changes, and verifies unit compatibility. Avoids misleading "better/worse" value judgments. |
| **Server-Side PDF Report Generation** | Generates localized, print-ready PDF summaries via **ReportLab** with **HarfBuzz** font shaping for Devanagari scripts (Hindi & Marathi) using open-source Noto Sans fonts. |
| **Multilingual Support (EN, HI, MR)** | Full native localization for UI labels, test names, explanations, chat dialogue, doctor questions, and downloadable PDF summaries in English, Hindi (हिन्दी), and Marathi (मराठी). |

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    React 19 + TypeScript                    │
│      Tailwind CSS v4 · Lucide Icons · i18n (EN/HI/MR)       │
│  [ Home / Upload ] ─── [ Report Dashboard ] ─── [ Compare ] │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTPS / REST (JSON)
                               │ Header: X-Report-Token
┌──────────────────────────────▼──────────────────────────────┐
│                    FastAPI Backend (Python)                 │
│                                                             │
│  ┌───────────────────────┐       ┌───────────────────────┐  │
│  │   Document Extractor  │       │  Deterministic Engine │  │
│  │ PyMuPDF · PaddleOCR   │ ────▶ │  Parameter Extractor  │  │
│  │ Magic-byte validation │       │  Range Evaluator      │  │
│  └───────────────────────┘       └───────────┬───────────┘  │
│                                              │              │
│  ┌───────────────────────┐       ┌───────────▼───────────┐  │
│  │  Curated Knowledge    │       │     RAG Retriever     │  │
│  │  43 MedlinePlus Files │ ────▶ │  BM25 + Graph Synonyms│  │
│  │  78 Curated Passages  │       │  Zero-Vector Memory   │  │
│  └───────────────────────┘       └───────────┬───────────┘  │
│                                              │ Context      │
│  ┌───────────────────────────────────────────▼───────────┐  │
│  │           Gemini LLM Client (Batched JSON)            │  │
│  └───────────────────────────┬───────────────────────────┘  │
│                              │ Generated Output             │
│  ┌───────────────────────────▼───────────────────────────┐  │
│  │             Safety & Verification Guardrails          │  │
│  │  • Number cross-check         • Direction alignment   │  │
│  │  • Citation existence check   • Language check        │  │
│  │  • Prescriptive language filter                       │  │
│  │  ↳ If failed: Fallback to Deterministic Template      │  │
│  └───────────────────────────┬───────────────────────────┘  │
│                              │                              │
│  ┌───────────────────────────▼───────────────────────────┐  │
│  │  Storage (SHA-256 Auth, 24h Expiry) · PDF (HarfBuzz)  │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔍 RAG & Clinical Knowledge Base

MedExplain AI avoids hallucinations by pairing generative AI with a strictly curated clinical retrieval-augmented generation (RAG) system:

1. **Curated Medical Corpus**: Located in [`backend/knowledge/sources/`](backend/knowledge/sources/), featuring 43 verified medical topics (78 individual clinical passages) from **MedlinePlus (U.S. National Library of Medicine)**.
2. **Deterministic BM25 Retrieval**:
   - Matches test identifiers, aliases, and synonyms against curated text segments.
   - **Why BM25 instead of a Vector DB?** Medical laboratory parameters require high lexical precision rather than loose semantic embeddings. BM25 is fully deterministic, introduces zero external vector database dependencies, and consumes less than 50MB of RAM—allowing reliable deployment on memory-constrained 512MB hosting tiers.
3. **Graph-Enhanced Expansion**: [`backend/knowledge/graph.json`](backend/knowledge/graph.json) defines 18 verified clinical relationships connecting interdependent biomarkers (e.g., Microcytic anemia clusters: Ferritin + Hemoglobin + MCV).
4. **Offline Validation**: All knowledge sources are validated for schema consistency and citation accuracy using `python backend/scripts/validate_knowledge.py`.

---

## 🛡️ Medical Safety & Validation Pipeline

Before any AI-generated explanation or conversational response reaches the patient, it passes through programmatic validation filters ([`backend/app/services/safety.py`](backend/app/services/safety.py)):

```
          [ Gemini Raw Output ]
                    │
                    ▼
       ┌─────────────────────────┐
       │   Hallucination Filter  │ ── Fails ──┐
       │ Only numbers from report│            │
       └────────────┬────────────┘            │
                    │ Passes                  │
                    ▼                         │
       ┌─────────────────────────┐            │
       │ Directional Consistency │ ── Fails ──┤
       │ Must match High/Low/Norm│            │
       └────────────┬────────────┘            │
                    │ Passes                  │
                    ▼                         │
       ┌─────────────────────────┐            │
       │     Citation Verifier   │ ── Fails ──┤
       │ IDs must exist in RAG   │            │
       └────────────┬────────────┘            │
                    │ Passes                  │
                    ▼                         │
       ┌─────────────────────────┐            │
       │   No Prescriptive Claims│ ── Fails ──┤
       │ Disallows dosage/drugs  │            │
       └────────────┬────────────┘            │
                    │ Passes                  │
                    ▼                         ▼
             [ Approved Output ]     [ Deterministic Fallback ]
             (Grounded with URLs)    (Rule-based label summary)
```

- **Emergency Interceptor**: If a chat query contains emergent symptoms (e.g., chest pain, shortness of breath, severe hemorrhage), the LLM is bypassed entirely, immediately serving an emergency hotline advisory.
- **Fail-Safe Fallbacks**: If Gemini is offline, times out, rate-limited, or fails safety validation, MedExplain AI seamlessly degrades to deterministic, rule-based medical summaries—ensuring zero downtime.

---

## 📁 Project Structure

```text
medExplainAI/
├── backend/
│   ├── app/
│   │   ├── assets/fonts/            # SIL OFL Noto Sans & Devanagari fonts for PDF
│   │   ├── routes/
│   │   │   ├── health.py            # /api/health monitoring endpoint
│   │   │   └── reports.py           # Upload, explain, chat, compare, PDF endpoints
│   │   ├── services/
│   │   │   ├── chat_service.py      # Context-grounded conversational agent
│   │   │   ├── comparison.py        # Longitudinal multi-report comparison
│   │   │   ├── document_extractor.py# PyMuPDF & OCR extraction router
│   │   │   ├── explanation_service.py# Batched RAG explanation builder
│   │   │   ├── i18n.py              # Server-side translations & localized templates
│   │   │   ├── insights.py          # Multi-parameter knowledge graph engine
│   │   │   ├── knowledge_base.py    # In-memory BM25 index & passage retriever
│   │   │   ├── llm_client.py        # Google Gemini API client with fallback models
│   │   │   ├── ocr_service.py       # PaddleOCR integration for scanned images
│   │   │   ├── parameter_extractor.py# Regex & lexical extractor for 50+ lab tests
│   │   │   ├── pdf_service.py       # ReportLab PDF generator with HarfBuzz shaping
│   │   │   ├── safety.py            # Anti-hallucination & clinical safety validators
│   │   │   └── storage.py           # Report metadata store with token hashing
│   │   ├── main.py                  # FastAPI application entrypoint & middleware
│   │   └── security.py              # Cryptographic tokens, rate-limiting, sanitation
│   ├── knowledge/                   # Curated MedlinePlus clinical repository
│   │   ├── sources/                 # 43 structured markdown reference articles
│   │   ├── graph.json               # 18 documented multi-parameter clinical links
│   │   └── README.md                # Knowledge base curation protocol
│   ├── scripts/
│   │   ├── make_sample_reports.py   # Generates fictional sample PDFs for testing
│   │   └── validate_knowledge.py    # Schema & citation validation script
│   ├── requirements.txt             # Core production dependencies
│   ├── requirements-dev.txt         # Dev & test dependencies (pytest, etc.)
│   └── requirements-ocr.txt         # Optional PaddleOCR dependencies
├── src/                             # React 19 Frontend
│   ├── components/
│   │   ├── report/                  # Dashboard tabs & clinical visualization
│   │   │   ├── AiSummary.tsx        # High-level overview card
│   │   │   ├── ChatPanel.tsx        # Interactive Q&A chat interface
│   │   │   ├── ComparePanel.tsx     # Historical report comparison view
│   │   │   ├── InsightsPanel.tsx    # Multi-parameter correlation cards
│   │   │   ├── ParameterDetail.tsx  # Modal with explainability & rationale
│   │   │   ├── ResultsPanel.tsx     # Categorized test results table
│   │   │   └── SourceList.tsx       # Verified reference citations list
│   │   ├── Footer.tsx               # Footer with legal & medical disclaimers
│   │   ├── Header.tsx               # Navigation bar & language switcher
│   │   ├── RangeBar.tsx             # Visual reference range slider
│   │   ├── StatusBadge.tsx          # High / Low / Normal status pill
│   │   └── ui.tsx                   # Reusable UI primitives (Button, Modal, etc.)
│   ├── i18n/                        # Localization dictionaries
│   │   ├── en.ts                    # English dictionary
│   │   ├── hi.ts                    # Hindi dictionary (हिन्दी)
│   │   ├── mr.ts                    # Marathi dictionary (मराठी)
│   │   └── LanguageContext.tsx      # Language provider & switcher hook
│   ├── pages/
│   │   ├── HomePage.tsx             # Landing page with demo reports & feature list
│   │   ├── ReportPage.tsx           # Main analysis workspace
│   │   └── UploadPage.tsx           # Drag-and-drop document upload form
│   ├── services/
│   │   ├── api.ts                   # Strongly-typed Axios/Fetch API client
│   │   ├── reportFlow.ts            # State synchronization helper
│   │   └── session.ts               # Secure sessionStorage token management
│   └── test/                        # Vitest suites (UI tests, i18n key checks)
├── public/                          # Static assets and fictional sample reports
├── render.yaml                      # Render Blueprint infrastructure definition
├── vercel.json                      # Vercel SPA routing & security headers
├── package.json                     # Node.js project manifest & scripts
└── vite.config.ts                   # Vite configuration
```

---

## 📡 REST API Reference

All report endpoints enforce security via the `X-Report-Token` HTTP header, verified against a SHA-256 hash stored on the server.

### 1. Upload & Parse Report
- **`POST /api/reports`**
- **Content-Type**: `multipart/form-data`
- **Body**: `file` (PDF, PNG, or JPEG, max 10MB)
- **Response** `201 Created`:
  ```json
  {
    "report_id": "rep_9f83a2...",
    "report_token": "tok_e4b1...",
    "parameters": [
      {
        "name": "Hemoglobin",
        "value": 11.2,
        "unit": "g/dL",
        "reference_range": {"low": 12.0, "high": 15.5},
        "status": "below_range"
      }
    ],
    "expires_at": "2026-10-16T10:00:00Z"
  }
  ```

### 2. Generate Evidence-Grounded Explanations
- **`POST /api/reports/{report_id}/explain`**
- **Headers**: `X-Report-Token: <token>`
- **Body**: `{"language": "en" | "hi" | "mr"}`
- **Response** `200 OK`:
  ```json
  {
    "explanations": {
      "Hemoglobin": {
        "text": "Your hemoglobin level is slightly below the reference range...",
        "citations": [{"id": "hemoglobin_overview", "title": "Hemoglobin Test", "url": "https://medlineplus.gov/..."}],
        "is_ai": true,
        "rationale": "Value 11.2 g/dL < printed lower bound 12.0 g/dL"
      }
    },
    "doctor_questions": ["What dietary adjustments or supplements are recommended for low hemoglobin?"]
  }
  ```

### 3. Contextual Chatbot
- **`POST /api/reports/{report_id}/chat`**
- **Headers**: `X-Report-Token: <token>`
- **Body**: `{"message": "What does a high neutrophil count mean?", "language": "en"}`
- **Response** `200 OK`:
  ```json
  {
    "reply": "Neutrophils are white blood cells that fight infection...",
    "citations": [{"id": "cbc_overview", "title": "Complete Blood Count", "url": "..."}],
    "is_emergency": false
  }
  ```

### 4. Longitudinal Report Comparison
- **`POST /api/reports/compare`**
- **Body**: `{"report_id_a": "rep_1", "token_a": "tok_1", "report_id_b": "rep_2", "token_b": "tok_2"}`
- **Response** `200 OK`:
  ```json
  {
    "comparisons": [
      {
        "parameter": "Platelets",
        "value_a": 180000,
        "value_b": 220000,
        "delta": 40000,
        "percent_change": 22.2,
        "unit": "cells/mcL",
        "compatible": true
      }
    ]
  }
  ```

### 5. Download Localized PDF Summary
- **`GET /api/reports/{report_id}/pdf?lang=en`**
- **Headers**: `X-Report-Token: <token>`
- **Response**: `application/pdf` binary stream.

---

## 🚀 Getting Started

### Prerequisites
- **Node.js**: v20.x or higher
- **Python**: v3.11.x
- **Package Managers**: `npm` and `pip`
- **Google Gemini API Key**: Obtain a key from [Google AI Studio](https://aistudio.google.com/)

---

### Backend Setup

1. **Navigate to the backend directory**:
   ```bash
   cd backend
   ```

2. **Create and activate a virtual environment**:
   - **Windows**:
     ```powershell
     python -m venv .venv
     .venv\Scripts\activate
     ```
   - **macOS / Linux**:
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements-dev.txt
   ```

4. **Configure environment variables**:
   ```bash
   cp .env.example .env
   ```
   Open `.env` and set your `GEMINI_API_KEY`:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

5. **Start the FastAPI backend server**:
   ```bash
   python -m uvicorn app.main:app --reload --port 8000
   ```
   Verify the health endpoint at `http://localhost:8000/api/health`.

---

### Frontend Setup

1. **Open a new terminal in the project root**:
   ```bash
   npm install
   ```

2. **Configure local environment (optional)**:
   If your backend is running on a port other than 8000, create a `.env.local` file in the root directory:
   ```env
   VITE_API_BASE_URL=http://localhost:8000
   ```

3. **Start Vite development server**:
   ```bash
   npm run dev
   ```
   Open your browser at `http://localhost:5173`.

---

### OCR Setup (Optional)

To enable OCR for scanned documents and mobile photographs:
1. Install OCR-specific requirements in your backend virtual environment:
   ```bash
   pip install -r backend/requirements-ocr.txt
   ```
2. Enable OCR in `backend/.env`:
   ```env
   ENABLE_OCR=true
   ```
*(Note: PaddleOCR requires ~1.5 GB disk space and is recommended for local workstations or dedicated server tiers).*

---

## ⚙️ Configuration & Environment Variables

### Backend Configuration (`backend/.env`)

| Variable | Type | Default | Description |
|---|---|---|---|
| `GEMINI_API_KEY` | String | *None* | Google Gemini API secret. If left empty, deterministic fallbacks will be used. |
| `GEMINI_MODEL` | String | `gemini-3.1-flash-lite` | Primary LLM model identifier. |
| `GEMINI_FALLBACK_MODELS`| String | `gemini-flash-lite-latest` | Comma-separated list of fallback models if primary model is unavailable. |
| `ALLOWED_ORIGINS` | String | `http://localhost:5173,http://localhost:3000` | Comma-delimited CORS allowed origins. |
| `ALLOWED_ORIGIN_REGEX` | String | `None` | Regex pattern for matching dynamic client origins (e.g., Vercel previews). |
| `ENVIRONMENT` | String | `development` | Environment mode (`development` or `production`). |
| `DATA_DIR` | String | `uploads` | Directory for temporary report storage. |
| `REPORT_RETENTION_HOURS`| Integer| `24` | Automated report lifespan before permanent deletion. |
| `ENABLE_OCR` | Boolean| `false` | Enable PaddleOCR fallback for non-digital files. |
| `RATE_LIMIT_UPLOADS_PER_MINUTE` | Integer | `10` | Maximum uploads allowed per IP per minute. |
| `RATE_LIMIT_AI_PER_MINUTE` | Integer | `30` | Maximum AI requests allowed per IP per minute. |

### Frontend Configuration (`.env.local` or hosting provider)

| Variable | Description |
|---|---|
| `VITE_API_BASE_URL` | Public base URL for the backend API (e.g., `https://your-backend.onrender.com`). |

---

## 🧪 Testing & Quality Assurance

MedExplain AI maintains strict automated testing for medical deterministic logic, UI components, and localization consistency:

```bash
# 1. Run Backend Pytest Suite (72 unit tests with mocked AI responses)
cd backend
python -m pytest

# 2. Validate Curated Knowledge Base Consistency
python scripts/validate_knowledge.py

# 3. Run Frontend Unit & Integration Tests (Vitest + Testing Library)
cd ..
npm test

# 4. Perform TypeScript Check & Code Quality Linting
npm run lint
npm run build
```

---

## 🌐 Deployment Guide

### Backend on Render (Free Web Service)
1. In your **Render Dashboard**, select **New → Blueprint**.
2. Connect your repository: Render will automatically detect [`render.yaml`](render.yaml).
3. Fill in required environment variables in the Render console:
   - `GEMINI_API_KEY`: Your Google AI Studio API key.
   - `ALLOWED_ORIGINS`: Your Vercel frontend URL (e.g., `https://your-app.vercel.app`).
4. Trigger the deployment. Your API will be live at `https://<service-name>.onrender.com`.

### Frontend on Vercel
1. In your **Vercel Dashboard**, select **Add New Project** and import the repository.
2. Select framework preset: **Vite**.
3. In **Environment Variables**, add:
   - `VITE_API_BASE_URL`: `https://<your-render-service>.onrender.com`
4. Click **Deploy**.
5. Copy your assigned Vercel URL and add it to `ALLOWED_ORIGINS` on Render.

---

## 🔒 Security, Privacy & Data Lifecycle

MedExplain AI was built with strict privacy and security hygiene:

1. **Zero Persistent PII Storage**:
   - Patient names, clinic details, and raw demographic metadata are neither extracted nor stored in analytical tables.
   - Files are stored using cryptographic random tokens (`secrets.token_urlsafe`), and only the **SHA-256 hash** is persisted.
2. **Short-Lived Retention**:
   - Reports are automatically purged from disk after **24 hours**.
   - Users can manually click **"Delete Report"** at any time to purge data immediately.
3. **Restricted External API Exposure**:
   - Raw report PDFs are **never uploaded to third-party AI APIs**.
   - Only isolated, anonymized medical test tokens (e.g., `"Hemoglobin: 11.2 g/dL"`) and retrieved MedlinePlus passages are sent to Google Gemini.
4. **Header-Based Authorization**:
   - All session actions require the `X-Report-Token` header stored exclusively in the browser's transient `sessionStorage`. Closing the tab discards access.

---

## 🤝 Contributing

Contributions to improve extraction accuracy, expand the curated knowledge base, or translate into additional regional languages are warmly welcomed!

1. Fork the Project repository.
2. Create your Feature Branch (`git checkout -b feature/NewBiomarker`).
3. Commit your Changes (`git commit -m "feat: add ferritin multi-parameter link"`).
4. Push to the Branch (`git push origin feature/NewBiomarker`).
5. Open a Pull Request.

---

## 📄 License

Distributed under the **MIT License**. See `LICENSE` for more information.

*Curated medical summaries in `backend/knowledge/sources/` are adapted from MedlinePlus, a service of the National Library of Medicine (NLM), U.S. National Institutes of Health.*