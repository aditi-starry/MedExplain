# MedExplain knowledge base

The RAG pipeline retrieves only from the curated files in this folder. Nothing is
scraped at runtime, and the AI may only use passages that were retrieved for a request.

```
knowledge/
  documents/*.json   sources and their passages (one file per collection)
  graph.json         knowledge graph: parameter aliases, concepts and cited relationships
```

## Current sources

All 43 sources are MedlinePlus "Medical Tests" pages (U.S. National Library of
Medicine). MedlinePlus medical test information is **public domain**
(<https://medlineplus.gov/about/using/usingcontent/>); attribution: "Source: MedlinePlus,
National Library of Medicine". Each passage is a short **paraphrase** written from
the page, not a verbatim copy. Pages were fetched and read on 2026-10-14
(`retrieved`); `lastUpdated` is the date printed on each page.

## Document format

```json
{
  "collection": "…", "publisher": "…", "license": "…", "retrieved": "YYYY-MM-DD",
  "documents": [{
    "id": "mlp-ferritin",
    "title": "Ferritin Blood Test",
    "url": "https://medlineplus.gov/lab-tests/ferritin-blood-test/",
    "lastUpdated": "2025-03-18",
    "parameters": ["Ferritin"],          // canonical names from graph.json / parameter_extractor.py
    "passages": [{
      "id": "mlp-ferritin-1",            // stable, unique; cited by explanations and graph edges
      "topics": ["definition", "low", "high", "relationship"],
      "text": "One to three plain sentences, max 600 characters."
    }]
  }]
}
```

Topics used by retrieval: `definition`, `high`, `low`, `interpretation`,
`reference range`, `relationship`, `panel`, `doctor`, `test preparation`, `general`.

## Adding or updating a source

1. Use a trustworthy, appropriately licensed source (MedlinePlus, NHS, NIH, official
   public-health bodies). Check the licence/reuse terms first; prefer public-domain or
   explicitly reusable content, and always attribute.
2. Open the page and read the relevant sections yourself. Write short paraphrased
   passages that say **only** what the page says. Do not add causes, numbers or
   advice that are not on the page. Avoid long verbatim quotations.
3. Record `title`, `url`, the page's own "last updated" date and today's `retrieved` date.
4. List the canonical parameter names the document covers in `parameters`.
5. To add a relationship between tests, add it to `graph.json` → `relationships`
   with `evidence` pointing to passage ids that **state** the relationship. Never
   add a causal or diagnostic link that the cited passage does not support.
6. New tests or synonyms: add a node to `graph.json` → `parameters` (aliases may
   include Hindi/Marathi terms), and, if extraction should recognise it, to
   `LAB_TEST_CATALOG` in `app/services/parameter_extractor.py`.
7. Validate and test:

   ```bash
   python scripts/validate_knowledge.py
   python -m pytest test_rag.py
   ```

Review sources at least every 6–12 months: re-check URLs and "last updated" dates and
revise passages if the page changed.
