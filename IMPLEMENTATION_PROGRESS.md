# MedExplain AI - upgrade progress checklist

Last updated: 2026-10-15

## Done (committed locally on branch `main`)
- [x] Audit and stabilization (missing ProcessingPage, uninstalled deps, uncollected OCR tests, Gemini key in URL)
- [x] RAG: MedlinePlus knowledge base (43 sources / 78 passages), BM25 retriever, graph (18 cited relationships)
- [x] Evidence-grounded Gemini explanations with validation and labelled fallback; explainable rationale
- [x] Chatbot, insights, doctor questions, comparison, PDF (en/hi/mr), security hardening
- [x] Redesigned frontend with i18n (en/hi/mr); verified in a real browser at desktop and mobile widths
- [x] Tests: backend 72 passed; frontend 25 passed; lint clean; production build OK
- [x] README, knowledge/README, .env.example files, .gitignore, render.yaml, vercel.json

## Remaining (needs the owner)
- [ ] Push to GitHub (owner chose not to push yet)
- [ ] Deploy backend on Render (Blueprint) and frontend on Vercel; set env vars; smoke-test live URLs
- [ ] Decide what to do with legacy files in `backend/uploads/` (git-ignored; may contain real patient data)

## Next steps when resuming
1. `gh repo create ashmita-dev/medExplainAI --public --source . --push` (add `-c safe.directory=E:/medExplainAI` to git commands, or add it to git config)
2. Render: New -> Blueprint -> repo; set GEMINI_API_KEY, ALLOWED_ORIGINS
3. Vercel: import repo; set VITE_API_BASE_URL to the Render URL; then update ALLOWED_ORIGINS
4. Smoke test: /api/health, upload fictional sample, explain, chat, PDF
