# CCR Crawler Architecture

**Version:** 1.0  
**Date:** 2026-01-31  
**Status:** Design Complete — Ready for Implementation

---

## Overview

This document defines the architecture for a Breadth-First Search (BFS) crawler that discovers and extracts every CCR Section (§) from https://govt.westlaw.com/calregs.

**Key Design Principles:**
- **Completeness over speed:** Discover every section, not just most sections
- **Resumable:** Crawler can restart from checkpoint after interruption
- **Respectful:** Rate-limited to avoid server overload
- **Observable:** Comprehensive logging for monitoring and debugging

---

## System Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    CCR Crawler System                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────────┐      ┌──────────────────────┐      │
│  │  URL Discovery     │      │  Content Extraction  │      │
│  │  (Phase 3)         │─────▶│  (Phase 4)           │      │
│  │                    │      │                       │      │
│  │  - BFS traversal   │      │  - Parse section HTML│      │
│  │  - Link extraction │      │  - Extract fields    │      │
│  │  - Deduplication   │      │  - Store as JSONL    │      │
│  └────────────────────┘      └──────────────────────┘      │
│           │                            │                     │
│           ▼                            ▼                     │
│  ┌────────────────────┐      ┌──────────────────────┐      │
│  │  State Management  │      │  Error Handling      │      │
│  │                    │      │                       │      │
│  │  - Queue checkpts  │      │  - Retry logic       │      │
│  │  - Visited URLs    │      │  - Failure logging   │      │
│  │  - Section list    │      │  - Graceful recovery │      │
│  └────────────────────┘      └──────────────────────┘      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Phase 3: URL Discovery (BFS Crawler)

### Purpose
Discover all `/calregs/Document/` URLs by traversing navigation (`/Browse/`) pages.

### Algorithm

**Breadth-First Search (BFS)**

```python
# Pseudocode
from collections import deque

queue = deque([START_URL])  # /calregs/Index
visited = set()
discovered_sections = []

while queue:
    url = queue.popleft()  # BFS (FIFO)
    
    if url in visited:
        continue
    
    visited.add(url)
    
    # Fetch page with rate limiting
    html = fetch_with_delay(url, delay=1.5)
    links = extract_links(html)
    
    for link in links:
        if is_navigation_url(link):  # /Browse/
            queue.append(link)
        
        elif is_section_url(link):  # /Document/
            discovered_sections.append(link)
            # Don't queue section URLs (they're leaf nodes)
    
    # Checkpoint every 100 URLs
    if len(visited) % 100 == 0:
        save_checkpoint(queue, visited, discovered_sections)

# Final output
save_file("data/discovered_urls.txt", discovered_sections)
```

### URL Classification

**Navigation URLs (traverse, don't extract):**
- Pattern: `/calregs/Browse/Home/California/CaliforniaCodeofRegulations?guid=...`
- Action: Extract links, add to queue

**Section URLs (record for extraction):**
- Pattern: `/calregs/Document/{GUID}?viewType=FullText`
- Action: Add to `discovered_sections`, do NOT queue

### Starting Point
```
https://govt.westlaw.com/calregs/Index
```

### Link Extraction Strategy

Based on HTML inspection, links are found in:
- Main content area: Navigation lists
- Breadcrumb links: For upward navigation (optional)
- TOC links: Table of Contents references

**CSS Selectors for link extraction:**
```python
# To be determined during implementation
# Likely: a[href*="/calregs/Browse/"]
# and:    a[href*="/calregs/Document/"]
```

---

## Phase 4: Content Extraction

### Purpose
Parse discovered section URLs and extract structured data.

### HTML Structure (Validated via samples/)

**Section Title:**
```html
<h1 id="co_docHeaderTitleLine">
  <span id="title">§ 1031.2. Advisory Committee.</span>
</h1>
```
**Selector:** `h1#co_docHeaderTitleLine > span#title`

**Citation:**
```html
<ul id="co_docHeaderCitation">
  <li id="titleDesc">2 CA ADC § 1031.2</li>
  <li id="codeSetName">Barclays Official California Code of Regulations</li>
</ul>
```
**Selectors:**
- Short citation: `#co_docHeaderCitation #titleDesc`
- Publisher: `#co_docHeaderCitation #codeSetName`

**Canonical Citation (preferred):**
```html
<div class="co_contentBlock co_cmdExpandedcite">
  Cal. Admin. Code tit. 2, § 1031.2, 2 CA ADC § 1031.2
</div>
```
**Selector:** `.co_cmdExpandedcite`

**Hierarchy Breadcrumb:**
```html
<div id="co_prelimContainer">
  <div class="co_contentBlock co_prelimHead co_headtext">Title 2. Administration
    <div class="co_contentBlock co_prelimHead co_headtext">Division 2. Financial Operations (Refs & Annos)
      <div class="co_contentBlock co_prelimHead co_headtext">Chapter 2. State Controller
        <div class="co_contentBlock co_prelimHead co_headtext">Subchapter 3. Accounting Procedures for Special Districts
          <div class="co_contentBlock co_prelimHead co_headtext" id="co_prelimGoldenLeaf">Article 1. General Information
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
```
**Selector:** `#co_prelimContainer .co_prelimHead`

**Section Body Text:**
```html
<div class="co_contentBlock co_section">
  <div class="co_contentBlock co_body">
    <div class="co_paragraph">
      <div class="co_paragraphText">
        The requirements herein prescribed have been approved...
      </div>
    </div>
  </div>
</div>
```
**Selector:** `.co_contentBlock.co_section .co_paragraphText`

**Currency Notice (effective date):**
```html
<div class="co_contentBlock co_includeCurrencyBlock">
  This database is current through 1/9/26 Register 2026, No. 2.
</div>
```
**Selector:** `.co_includeCurrencyBlock`

**Hidden Metadata (GUID):**
```html
<input id="co_document_metaInfo_I309E34535A0A11EC8227000D3A7C4BC3" 
       type="hidden" 
       value='{"contentType":"Regulations","docGuid":"I309E34535A0A11EC8227000D3A7C4BC3","getTocData":true,"titleText":"§ 1031.2. Advisory Committee."}'>
```
**Selector:** `input[id^="co_document_metaInfo_"]`  
**Extract:** Parse `value` attribute as JSON

---

## State Management & Persistence

### File Structure

```
ccr_web_crawler/
├── checkpoints/
│   ├── queue_state.json        # BFS queue snapshot
│   ├── visited_urls.txt        # Already crawled URLs
│   └── discovered_urls.txt     # Section URLs found
├── data/
│   ├── sections.jsonl          # Extracted section data (Phase 4)
│   └── failed_urls.txt         # Parse failures
├── logs/
│   ├── discovery.log           # Phase 3 logs
│   └── extraction.log          # Phase 4 logs
```

### Checkpoint Format

**queue_state.json:**
```json
{
  "timestamp": "2026-01-31T12:06:19Z",
  "queue": [
    "https://govt.westlaw.com/calregs/Browse/...",
    "https://govt.westlaw.com/calregs/Browse/..."
  ],
  "visited_count": 1234,
  "discovered_count": 5678
}
```

**visited_urls.txt:**
```
https://govt.westlaw.com/calregs/Index
https://govt.westlaw.com/calregs/Browse/...
https://govt.westlaw.com/calregs/Browse/...
```

**discovered_urls.txt:**
```
https://govt.westlaw.com/calregs/Document/I309E34535A0A11EC8227000D3A7C4BC3?viewType=FullText
https://govt.westlaw.com/calregs/Document/I30A7F8535A0A11EC8227000D3A7C4BC3?viewType=FullText
```

### Resume Logic

```python
def initialize_crawler():
    if checkpoint_exists():
        queue = load_checkpoint("checkpoints/queue_state.json")
        visited = load_file("checkpoints/visited_urls.txt")
        discovered = load_file("checkpoints/discovered_urls.txt")
        print(f"Resuming from checkpoint: {len(visited)} visited, {len(queue)} in queue")
    else:
        queue = deque([START_URL])
        visited = set()
        discovered = []
        print("Starting fresh crawl")
    
    return queue, visited, discovered
```

---

## Rate Limiting & Respectful Crawling

### Strategy
- **Delay:** 1.5 seconds between requests
- **User-Agent:** Custom identifier: `CCR-Crawler/1.0 (Educational Project)`
- **No parallelization:** Single-threaded initially (safer)

### Implementation

```python
import time
import requests

def fetch_with_delay(url, delay=1.5):
    time.sleep(delay)
    
    headers = {
        'User-Agent': 'CCR-Crawler/1.0 (Educational Project)',
    }
    
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    
    return response.text
```

---

## Error Handling

### Failure Categories

1. **Transient errors** (retry-able):
   - Network timeouts
   - HTTP 5xx errors
   - Connection resets

2. **Permanent errors** (skip):
   - HTTP 404 (not found)
   - HTTP 403 (forbidden)
   - Malformed HTML

3. **Parser errors** (log and skip):
   - Missing expected fields
   - Unexpected HTML structure

### Retry Logic

```python
def fetch_with_retry(url, max_retries=3):
    for attempt in range(max_retries):
        try:
            return fetch_with_delay(url)
        except (Timeout, ConnectionError) as e:
            if attempt == max_retries - 1:
                log_error(f"Failed after {max_retries} attempts: {url}")
                raise
            
            # Exponential backoff
            wait_time = 2 ** attempt
            time.sleep(wait_time)
```

### Failure Logging

**logs/discovery.log:**
```
2026-01-31T12:15:00 INFO  Crawling URL: https://govt.westlaw.com/calregs/Index
2026-01-31T12:15:02 INFO  Discovered 27 links (3 sections, 24 navigation)
2026-01-31T12:15:05 ERROR Failed to fetch: https://... - HTTP 404
```

**data/failed_urls.txt:**
```
https://govt.westlaw.com/calregs/Document/DEADBEEF?viewType=FullText (404)
```

---

## Logging & Observability

### Log Levels

- **INFO:** Normal operation (URLs crawled, checkpoints saved)
- **WARNING:** Retryable errors, unexpected patterns
- **ERROR:** Permanent failures, parse errors

### Metrics to Track

- Total URLs visited
- Total sections discovered
- Queue size (current)
- Crawl rate (URLs/minute)
- Error rate (failures/total)

### Log Format

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler('logs/discovery.log'),
        logging.StreamHandler()  # Also print to console
    ]
)
```

---

## Edge Case Handling: Title 24 (Building Standards Code)

### Discovery (Phase 2)

During architecture design, manual testing revealed that **Title 24 behaves differently from all other CCR titles**.

**Observation:**
- Titles 1–23, 25–28: Fully hosted on Westlaw, navigable via standard HTML links
- **Title 24**: Redirects externally to publisher-controlled platforms

**External redirect targets:**
- California Building Standards Commission (DGS): https://www.dgs.ca.gov/BSC
- ICC Digital Codes: https://codes.iccsafe.org/
- NFPA platforms

**Characteristics of external platforms:**
- Publisher-controlled content
- Partially paywalled / login-gated
- **Not part of the Westlaw CCR HTML corpus**
- Cannot be extracted using standard CCR crawling approach

### Design Decision

**Title 24 will be detected, recorded, and reported — but not text-extracted.**

This approach aligns with production system design principles:
> **"A partially correct but well-instrumented system is better than a silent, incomplete one."**

### Implementation Strategy

#### 1. Detection
During URL discovery (Phase 3):
- Crawl Title 24 navigation pages
- Detect external redirect pattern
- Record redirect URL

#### 2. Recording
Store Title 24 references with:
```json
{
  "url": "https://govt.westlaw.com/calregs/...",
  "guid": "...",
  "section_number": "§ ...",
  "section_title": "...",
  "hierarchy": {
    "title": "Title 24. Building Standards Code",
    ...
  },
  "extraction_status": "external_redirect",
  "extraction_note": "Redirects to California Building Standards Commission (DGS) - not extractable via Westlaw",
  "external_url": "https://www.dgs.ca.gov/BSC",
  "text_plain": null,
  "extracted_at": "2026-01-31T12:37:50Z"
}
```

#### 3. Reporting
Coverage reports will show:
- **Total CCR Titles:** 28
- **Fully extracted:** 27 (Titles 1–23, 25–28)
- **External redirects:** 1 (Title 24)
- **Extraction rate:** 96.4% (Titles), ~99%+ (Sections from extractable Titles)

#### 4. Compliance Agent Integration

The RAG-based compliance agent will:
- ✅ Include Title 24 in citation awareness (knows it exists)
- ✅ Explicitly flag when Title 24 applies: *"Title 24 (Building Standards Code) may apply to your facility. Consult the California Building Standards Commission or local building officials."*
- ❌ Never quote or hallucinate Title 24 content
- ❌ Never imply it was extracted

### Downstream Impact

#### Facility Operator Guidance
Compliance queries will still be grounded in fully extracted titles:
- **Title 8** — Cal/OSHA (workplace safety)
- **Title 17** — Public Health
- **Title 22** — Health Facilities (restaurants, theaters, etc.)
- **Title 3** — Food & Agriculture
- **Title 27** — Environmental Protection

**Title 24 obligations** will be surfaced contextually:
- "Your commercial kitchen must also comply with Title 24 Building Standards (fire safety, accessibility). Verify requirements with local building officials."

### Correctness & Legal Safety

This approach ensures:
1. **No silent omissions** — User is explicitly informed of Title 24's status
2. **No unauthorized scraping** — Respects publisher access controls
3. **Citation integrity** — Maintains accurate references
4. **Legal safety** — Avoids quoting unverified external content

### Alternative Approaches Considered (Rejected)

❌ **Scrape external publisher sites**
- Legal risk (unauthorized access, paywalls)
- Unreliable (structure varies by publisher)
- Out of scope (CCR crawler, not multi-source aggregator)

❌ **Manual data entry of Title 24**
- Not scalable
- Maintenance burden (frequent updates)
- Introduces human error

❌ **Silently skip Title 24**
- Non-transparent system behavior
- Potential hallucination risk
- Poor user experience

### Summary

**Title 24 Status:**
- **Detected:** ✅ Yes
- **Recorded:** ✅ Yes (with `extraction_status: "external_redirect"`)
- **Text Extracted:** ❌ No (external publisher redirect)
- **User Informed:** ✅ Yes (explicit limitation notice)

**Engineering Outcome:**
- Discovered limitation **before** implementation (Phase 2)
- Designed explicit handling **before** crawler code
- Formalized in schema, architecture, and documentation
- Zero risk of silent failure or hallucination

---

## Data Schema

See `schema.json` for the complete JSON schema definition.

**Summary of extracted fields:**
- `url` — Full section URL
- `guid` — Document GUID (unique identifier)
- `section_number` — e.g., "§ 1031.2"
- `section_title` — e.g., "Advisory Committee"
- `citation_short` — e.g., "2 CA ADC § 1031.2"
- `citation_canonical` — Full citation string
- `hierarchy` — Object with title, division, chapter, subchapter, article
- `text_html` — Raw HTML of section body
- `text_plain` — Plain text version
- `currency_notice` — Database current-through date
- `extracted_at` — ISO 8601 timestamp

---

## Performance Estimates

**Assumptions:**
- 1.5 second delay per request
- Average 10 child links per navigation page
- Estimated ~50,000 total CCR sections (order of magnitude)

**Estimated crawl time:**
- Navigation pages: ~5,000 × 1.5s = 2 hours
- Section pages: ~50,000 × 1.5s = 21 hours
- **Total: ~24 hours** (single-threaded)

**Optimization opportunities (Phase 6):**
- Concurrent requests (10 workers) → ~3 hours total
- Adaptive rate limiting based on server response times

**For Phase 3/4:** Single-threaded is acceptable (prioritize correctness).

---

## Implementation Checklist

### Phase 3: URL Discovery
- [ ] Implement BFS queue with `collections.deque`
- [ ] Implement URL deduplication with `set()`
- [ ] Implement link extraction (BeautifulSoup)
- [ ] Implement URL classification (`/Browse/` vs `/Document/`)
- [ ] Implement checkpoint save/resume
- [ ] Implement rate limiting (1.5s delay)
- [ ] Implement logging
- [ ] Output: `data/discovered_urls.txt`

### Phase 4: Content Extraction
- [ ] Read `data/discovered_urls.txt`
- [ ] For each URL, fetch and parse HTML
- [ ] Extract fields using CSS selectors
- [ ] Handle hierarchy parsing
- [ ] Convert HTML to plain text
- [ ] Store as JSON Lines (`.jsonl`)
- [ ] Log parse failures
- [ ] Output: `data/sections.jsonl`

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Site structure changes | Validate selectors on random samples during crawl |
| Rate limiting/blocking | Monitor HTTP status codes, adjust delay if needed |
| Incomplete coverage | Log skipped URLs, verify against expected count |
| Data corruption | Validate JSON schema on each extraction |
| Crawler crashes | Checkpoint every 100 URLs, resume on restart |

---

## Success Criteria

**Phase 3 Complete:**
- ✅ All navigation pages visited
- ✅ All `/Document/` URLs discovered
- ✅ No unhandled exceptions
- ✅ `discovered_urls.txt` contains deduplicated section URLs

**Phase 4 Complete:**
- ✅ All discovered sections extracted
- ✅ <1% parse failure rate
- ✅ All JSON validates against schema
- ✅ Manual spot-check of 20 random sections confirms accuracy

---

## Next Steps After Architecture

1. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   ```

2. **Install dependencies**
   ```bash
   pip install requests beautifulsoup4 lxml
   ```

3. **Create `crawler/discovery.py`** (Phase 3)
   - Implement BFS algorithm from this document
   - Test on small subset first (1 Title)

4. **Create `crawler/extraction.py`** (Phase 4)
   - Implement HTML parsing using selectors from this document
   - Test on `samples/` HTML files first

---

**Document Status:** ✅ **Approved for Implementation**
