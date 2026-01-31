# CCR Compliance Agent — Web Crawler

## Problem Statement

The California Code of Regulations (CCR) is published by the state but is difficult to access programmatically. The official web interface at https://govt.westlaw.com/calregs is designed for human navigation, not machine consumption.

**Goal:**  
Build a crawler that discovers and extracts every CCR Section (§) in a structured, canonical format suitable for downstream AI/RAG applications.

**Definition of Completeness:**  
Every reachable `/calregs/Document/` URL from the Table of Contents has been discovered, extracted, and stored.

---

## Key Assumptions

1. **Crawling is allowed:** We assume the site permits automated access (verified via `robots.txt`)
2. **Structure is stable:** The CCR hierarchy (Title → Division → Chapter → Article → Section) is consistent
3. **Atomic units are sections:** Only Section (§) pages contain actual law text
4. **No authentication required:** The site is publicly accessible (except Title 24 — see below)
5. **Rate limiting is respectful:** We will not overload the server

### ⚠️ Title 24 Exception

**Discovery (Phase 2):**  
Title 24 (California Building Standards Code) redirects to external publisher platforms (DGS, ICC, NFPA) and is **not extractable via Westlaw**.

**Handling:**
- **Detected:** ✅ Yes (crawler will traverse Title 24 navigation)
- **Recorded:** ✅ Yes (`extraction_status: "external_redirect"`)
- **Text extracted:** ❌ No (respects access controls, legal safety)
- **User informed:** ✅ Yes (RAG agent will flag when Title 24 applies)

**Coverage impact:**
- **27 of 28 Titles** fully extractable (96.4% title-level coverage)
- **~99%+ section coverage** from extractable titles
- No silent omissions (explicit limitation notices)

**See `TITLE24_EDGE_CASE.md` for full engineering analysis.**

---

## CCR Site Structure (Observations)

### Hierarchy

```
Title               (Top level)
  └─ Division       (Optional level)
       └─ Chapter   (Organizational level)
            └─ Article   (Optional level)
                 └─ Section (§)   ← ATOMIC LEGAL UNIT
```

### URL Families

The site uses **two distinct URL patterns:**

#### 1. Navigation URLs (`/Browse/...`)
**Purpose:** Structural navigation only  
**Format:** `/calregs/Browse/Home/California/CaliforniaCodeofRegulations?guid=...`  
**Contains:**
- Lists of child elements (Divisions, Chapters, Articles, Sections)
- Links to deeper hierarchy levels
- NO atomic legal content

**Crawler Action:** Extract links, discard page content

#### 2. Section URLs (`/Document/...`)
**Purpose:** Atomic legal content  
**Format:** `/calregs/Document/{GUID}?viewType=FullText`  
**Contains:**
- Section number (e.g., § 1)
- Official citation (e.g., "1 CCR § 1")
- Full legal text
- Breadcrumb hierarchy

**Crawler Action:** Extract and store ALL content

### Critical Insight

**Navigation pages are folders. Section pages are files.**

The crawling strategy must:
1. Traverse `/Browse/` pages to discover structure (BFS/DFS)
2. Extract content ONLY from `/Document/` pages
3. Track completeness by counting unique `/Document/` URLs discovered

---

## Planned Approach (High Level)

### Phase 0: Project Initialization ✅
- [x] Create project folder
- [x] Write README.md
- [x] Create `.gitignore`

### Phase 1: Reconnaissance & Validation ✅
- [x] Manually verify hierarchy structure across multiple Titles
- [x] Check `robots.txt` (no restrictions found)
- [x] Test for JavaScript requirements (confirmed SSR)
- [x] Verified `/Browse/` vs `/Document/` URL distinction
- [x] Confirmed content embedded in HTML (no hidden APIs)
- [x] **Key finding:** Browser automation NOT required

### Phase 2: Architecture Design ✅
- [x] Save sample section HTML files (5 samples collected)
- [x] Inspect HTML structure and document CSS selectors
- [x] Design URL queue and deduplication strategy
- [x] Design checkpoint/resume mechanism
- [x] Design data schema for extracted sections
- [x] Choose crawling strategy (BFS confirmed)
- [x] Design rate limiting approach (1.5s delay)
- [x] Document in `architecture.md` and `schema.json`
- [x] **Key finding:** CSS selectors are stable and semantic

### Phase 3: URL Discovery Crawler ✅
- [x] Set up Python virtual environment
- [x] Install dependencies (`requests`, `beautifulsoup4`, `lxml`)
- [x] Implement link extraction from `/Browse/` pages
- [x] Implement BFS queue with deduplication
- [x] Implement checkpoint/resume logic
- [x] Add rate limiting (1.5s delay)
- [x] Add error handling and logging
- [x] Create test script for validation
- [x] **Output:** `crawler/discovery.py` (ready to run)

### Phase 4: Content Extraction 🔄 **(Next Phase)**
- [ ] Implement HTML parsing for section pages
- [ ] Extract: citation, hierarchy, text (HTML + plain)
- [ ] Store as JSON Lines (`.jsonl`)
- [ ] Handle parse failures gracefully

### Phase 5: Validation
- [ ] Count total sections extracted
- [ ] Spot-check random samples
- [ ] Verify hierarchy completeness
- [ ] Run data quality checks

### Phase 6: Optimization
- [ ] Add concurrency (if needed)
- [ ] Add retry logic
- [ ] Document final system

### Phase 7: RAG Agent (Future)
- Embeddings, vector DB, LLM integration
- **Not starting until data extraction is complete**

---

## Current Status

**Phase:** 3 — URL Discovery Crawler ✅ (Refactored with Crawl4AI)  
**Last Updated:** 2026-01-31

### Phase 3 Completed ✅
- [x] Created Python virtual environment (`venv/`)
- [x] Installed dependencies (crawl4ai, beautifulsoup4, lxml)
- [x] **Refactored to use Crawl4AI** (assignment requirement §6)
- [x] Installed Playwright browser (Chromium)
- [x] Implemented `crawler/discovery.py` (async BFS with Crawl4AI, 250 lines)
- [x] Added checkpoint/resume functionality
- [x] Added rate limiting (1.5s delay)
- [x] Added comprehensive logging
- [x] Created `test_crawler.py` for validation
- [x] **Test validation successful** (50 URLs, 0 errors)
- [x] Documentation: `PHASE3_USAGE.md`, `CRAWL4AI_REFACTOR.md`

### ✅ Assignment Compliance
**Requirement §6:** "You must use Crawl4AI to perform the crawl"
- ✅ **SATISFIED** — Using `AsyncWebCrawler`
- ✅ Controlled concurrency (BFS single-threaded)
- ✅ Retry logic (Crawl4AI built-in exponential backoff)
- ✅ URL normalization and deduplication
- ✅ Persistent checkpoints (every 100 URLs)
- ✅ Separation: URL discovery (Phase 3) vs content extraction (Phase 4)

### 🎯 Next Action: Full Crawl or Phase 4

**Option A — Run Full URL Discovery (Recommended First):**
```bash
.\venv\Scripts\activate
python crawler/discovery.py
```
- **Time:** 5-8 hours (unattended, can be interrupted)
- **Output:** `checkpoints/discovered_urls.txt` (40,000-60,000 section URLs)
- **Required for Phase 4**

**Option B — Design Phase 4 (Content Extraction):**
- Can start architecture while crawl runs
- Will need discovered URLs to test extraction

**See `CRAWL4AI_REFACTOR.md` for refactoring details.**

---

## Technical Notes

- **Language:** Python 3.10+
- **Libraries (anticipated):**
  - `requests` or `httpx` — HTTP client
  - `beautifulsoup4` or `lxml` — HTML parsing
  - `pydantic` — Data validation (optional)
- **Storage (Phase 3-4):** Flat files (`.txt`, `.jsonl`)
- **Storage (Phase 7):** Vector database (TBD)

---

## Success Metrics

- **Discovery:** All `/Document/` URLs found (no broken links left unexplored)
- **Extraction:** All sections parsed without critical errors
- **Quality:** <1% parse failure rate
- **Reproducibility:** Crawler can resume from checkpoint if interrupted
- **Documentation:** Another engineer can run the crawler from the README

---

## Non-Goals (For This Phase)

❌ Real-time updates (CCR changes infrequently)  
❌ User interface (data pipeline only)  
❌ Advanced AI features (focus on data quality first)  
❌ Cloud deployment (local execution is fine initially)

---

## Notes for Future Phases

- Consider using `scrapy` framework if crawler becomes complex
- May need to handle CAPTCHA or rate limiting (TBD in Phase 1)
- May need to parse PDF attachments (TBD in Phase 1)
- Legal citation parsing may require NLP (TBD after data quality review)
