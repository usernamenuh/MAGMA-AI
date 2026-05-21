# Production Readiness Checklist

> Audit date: 2026-05-21  
> Priority: P1 → P2 → P3 → P4 → P5 → P6 → P7 → P8  
> Minimum viable production-safe: complete P1 + P2 + P3.1–P3.5 + P4.1 + P5.1–P5.3 + P6.1

---

## P1 — Stop the Bleeding
> Answers are currently wrong. Fix these first.

- [x] **P1.1** Raise context truncation `pipeline_knowledge.py:86` + `pipeline_en.py:134` — `max_len=2000` → `8000`, truncate after formatting not mid-string
- [x] **P1.2** Remove Google Translate call `pipeline_knowledge.py:103` — LLM already responds in Indonesian, translator mangles output
- [x] **P1.3** Fix `model_chat()` to use its parameters `pipeline_helpers.py:1727` — `model`, `temperature`, `max_tokens`, `stop`, `repetition_penalty` are all hardcoded and ignored
- [x] **P1.4** Fix `KeyError` crash in knowledge error handler `knowledge.py:138` — error response has no `references` or `date` keys, handler blindly accesses them → 500 on every exception
- [x] **P1.5** Fix `endpoints["CCTV"]` KeyError `pipeline_helpers.py:1131` — key does not exist, any query containing "cctv" crashes the pipeline
- [x] **P1.6** Verify `load_volcano_cache` import in `pipeline_en.py:9` — recent commit claims fix, confirm import present and tested end-to-end

---

## P2 — Security & Dead Code Removal
> Required before any external user access.

- [x] **P2.1** Rotate hardcoded LLM API key `pipeline_helpers.py:1550,1748` — `"my-super-secret-admin-key"` move to env var + add to `.env.example` (low urgency if network isolated, but clean it up)
- [ ] **P2.2** Add auth to `/upload` endpoint `knowledge.py:39` — `/delete` requires `api_key`, `/upload` does not; add `Depends(require_api_key)`
- [ ] **P2.3** Sanitize upload filename `knowledge.py:51` — replace `file.filename` with `os.path.basename(file.filename)` to block path traversal
- [ ] **P2.4** Add file size limit to `/upload` — no `Content-Length` check; add max e.g. 50MB

### P2.5 — Remove dead built-in auth (Phase 1: code deletion, no migration)
> Built-in register/login replaced by external auth. Safe to delete now.

- [ ] **P2.5a** Delete `/register`, `/login`, `/forgot-password`, `/refresh-token` routes from `authentication.py` — keep `/validate-token`
- [ ] **P2.5b** Delete `register_user`, `login_user`, `forgot_password`, `refresh_token_service` from `user_service.py`
- [ ] **P2.5c** Delete `DOMAIN_EMAIL` + `allowed_domains` from `core/config.py` — only fed dead route validators
- [ ] **P2.5d** Delete `create_user`, `update_refresh_token`, `update_user_password` from `user_repository.py`

### P2.6 — Remove dead built-in auth (Phase 2: DB migration — do separately)
> Fixes live bug: external auth users can't create API keys due to FK violation on `api_keys.user_id`.

- [ ] **P2.6a** Drop FK on `api_keys.user_id` → convert to plain `String` — fixes API key creation for external auth users (`models/api_keys.py:12`)
- [ ] **P2.6b** Drop `password_hash`, `refresh_token`, `refresh_token_expiry` columns from `users` table — only used by dead auth
- [ ] **P2.6c** Drop `users` table entirely once FK removed and no rows referenced
- [ ] **P2.6d** Add migration file `migrations/V4__drop_builtin_auth.sql`

---

## P3 — RAG Quality
> Core mission is decision support for volcanic hazard. Retrieval quality = life-safety quality.

- [x] **P3.1** Fix PDF chunk size — replaced with docling HybridChunker (max_tokens=512, structure-aware)
- [x] **P3.2** Preserve document structure — docling retains headings, lists, table rows natively
- [x] **P3.3** Replace PyPDF2 with docling — handles PDF + DOCX + DOC in one library
- [x] **P3.4** Normalize DOCX chunking — unified extractor `utils/docling_extractor.py`, old extractors deleted
- [ ] **P3.5** Add similarity score threshold `knowledge_documents_service.py:62` — filter chunks with `score < 0.40` before sending to LLM, expose as config
- [ ] **P3.6** Add BM25 hybrid search alongside semantic search — geological terms (`VONA`, `tingkat siaga`, `Merapi`) are exact-match lookups; add `pg_trgm` full-text + RRF fusion
- [ ] **P3.7** Add pgvector HNSW index `models/document.py` — no vector index exists, sequential scan on every query; `CREATE INDEX ... USING hnsw (embedding vector_cosine_ops)`
- [ ] **P3.8** Enrich chunk metadata during ingestion — extract and store volcano name, document date, report type (VAR/VEN/VONA) in `chunk_metadata` to enable filtered retrieval

---

## P4 — Reliability & Performance
> System must not time out or block under real usage.

- [ ] **P4.1** Make fastembed a startup singleton `vector_store.py:12` — `VectorStore` created per request, model loaded from disk on every query; initialize once at app startup
- [ ] **P4.2** Cache `load_examples()` at module level `pipeline_helpers.py:1569` — 140KB JSON read + parsed on every chat request; load once
- [ ] **P4.3** Wrap sync HTTP calls in `asyncio.to_thread` `pipeline_id.py`, `pipeline_en.py` — `requests.Session` calls inside async FastAPI handlers block the event loop; convert to `httpx` async or wrap
- [ ] **P4.4** Fix cache reset inside retry loop `pipeline_id.py:410` — `cache=None` on every retry re-embeds entire corpus; pass cache between attempts
- [ ] **P4.5** Add circuit breaker for MAGMA API calls `pipeline_helpers.py:1574` — when `magma.esdm.go.id` is down, every request blocks for 30s; fail fast after N consecutive errors
- [ ] **P4.6** Move volcano list to in-memory cache with TTL `pipeline_helpers.py:1691` — `get_mount_code()` hits external API on every pipeline call; keep hot in memory, refresh every hour

---

## P5 — Observability
> Can't fix what you can't see. Required for a life-safety system.

- [ ] **P5.1** Replace all `print()` with structured logging — ~50+ print calls in pipeline files; use `logging.getLogger(__name__)` + `python-json-logger`
- [ ] **P5.2** Log retrieval quality metrics per request — log `top_k`, `min_score`, `max_score`, `mean_score`, `chunks_above_threshold` per query
- [ ] **P5.3** Add `/health` endpoint with dependency checks — verify Postgres, pgvector, fastembed model, LLM server; return 503 if any critical dep is down
- [ ] **P5.4** Add request correlation ID middleware — add `X-Request-ID` header, pass through all pipeline log lines
- [ ] **P5.5** Log LLM response quality signals — log response length, whether fallback answer triggered, which pipeline path taken (intent, API called, retrieval scores)
- [ ] **P5.6** Complete `ms-esdm/.env.example` — document every required env var with type, valid range, and example value

---

## P6 — Response Quality Validation
> For disaster decision support: you must verify answers are correct before trusting them with lives.

- [ ] **P6.1** Build evaluation dataset — collect 50–100 real questions from PVMBG operators with known correct answers (volcano status, eruption history, VONA, landslide)
- [ ] **P6.2** Add automated eval harness — script that runs eval dataset through pipeline and scores answers; run on every deploy
- [ ] **P6.3** Add citation grounding check — verify LLM answer claims are present in retrieved chunks, not hallucinated
- [ ] **P6.4** Surface confidence signal in UI — when retrieval scores are all low, show warning: "Low confidence — verify with official MAGMA portal"

---

## P7 — Code Maintainability
> Lower priority but required before any future engineer touches this.

- [ ] **P7.1** Split `pipeline_helpers.py` into focused modules — 2000-line god file; split into `api_client.py`, `volcano_detection.py`, `intent_routing.py`, `embedding_utils.py`, `cache.py`, `llm_client.py`
- [ ] **P7.2** Remove duplicate imports `pipeline_id.py:5,7` `pipeline_en.py:5,7` — `detect_volcano_name` imported twice in both files
- [ ] **P7.3** Fix misleading embedding dim comment `models/document.py:37` — `Vector(384)` comment says "OpenAI embedding dimension" (OpenAI is 1536); fix to model name
- [ ] **P7.4** Add integration tests for pipeline — zero tests for RAG pipeline; minimum: ingest fixture doc → retrieve → generate non-empty answer
- [ ] **P7.5** Pin all dependency versions in `requirements.txt` — most packages unpinned; silent breakage on next deploy

---

## P8 — Advanced RAG
> After P1–P6 complete and eval baseline established.

- [ ] **P8.1** Upgrade embedding model to `intfloat/multilingual-e5-base` (768 dims) — better multilingual quality; requires re-embedding all docs + DB migration to `Vector(768)`
- [ ] **P8.2** Add cross-encoder reranker — after BM25+semantic retrieval of top-20, rerank with cross-encoder to select best 5; significant recall improvement
- [ ] **P8.3** Add query expansion for domain terms — expand Indonesian informal to formal geological equivalents before embedding
- [ ] **P8.4** Semantic chunking by document section — detect headings (bold, all-caps, numbered) to chunk by Pendahuluan / Pengamatan / Rekomendasi sections

---

## Progress Summary

| Phase | Items | Done | Status |
|-------|-------|------|--------|
| P1 — Stop the Bleeding | 6 | 6 | 🟢 Done |
| P2 — Security & Dead Code | 12 | 1 | 🟡 In progress |
| P3 — RAG Quality | 8 | 4 | 🟡 In progress |
| P4 — Reliability | 6 | 0 | 🔴 Not started |
| P5 — Observability | 6 | 0 | 🔴 Not started |
| P6 — Validation | 4 | 0 | 🔴 Not started |
| P7 — Maintainability | 5 | 0 | 🔴 Not started |
| P8 — Advanced RAG | 4 | 0 | ⚪ Deferred |
| **Total** | **51** | **0** | |

> Update status emoji: 🔴 Not started → 🟡 In progress → 🟢 Done
