# Phase 2 Guide — Architecture Design

**Objective:** Design the crawler system architecture on paper before writing code

**Input:** Phase 1 findings (SSR site, `/Browse/` vs `/Document/` URLs)  
**Output:** Architecture document + data schema + HTML samples

---

## What You'll Design

### 1. Crawling Strategy
**Question to answer:** How do we systematically discover every section URL?

**Recommended approach: Breadth-First Search (BFS)**

Why BFS?
- Discovers shallow content first (good for early validation)
- Natural level-by-level progression (Title → Division → Chapter...)
- Easy to checkpoint (save queue state at any level)

**Design decisions you need to make:**
- Starting URL: `/calregs/Index`
- Queue data structure: Python `collections.deque`
- Visited tracking: Python `set()` of URLs
- URL normalization: Strip query params except essential ones?

---

### 2. State Management
**Question to answer:** How do we avoid revisiting URLs and handle crashes?

**Components:**
- **URL queue:** What URLs to visit next
- **Visited set:** What URLs we've already processed
- **Discovered sections:** List of `/Document/` URLs found

**Persistence:**
- Save queue state every N URLs (e.g., every 100)
- Store in JSON: `checkpoints/queue_state.json`
- Enable resume: Load checkpoint if exists, else start fresh

**Files to maintain:**
```
checkpoints/
  ├─ queue_state.json       # Current BFS queue
  ├─ visited_urls.txt       # Already crawled
  └─ discovered_urls.txt    # Section URLs found
```

---

### 3. Rate Limiting
**Question to answer:** How do we crawl respectfully?

**Best practices:**
- Delay between requests: 1-2 seconds
- Respect server load: Don't parallelize initially
- User-Agent header: Identify as a polite bot

**Implementation:**
```python
import time

def fetch_with_delay(url, delay=1.5):
    time.sleep(delay)
    response = requests.get(url, headers={'User-Agent': 'CCR-Crawler/1.0'})
    return response
```

---

### 4. Error Handling
**Question to answer:** What happens when requests fail?

**Failure scenarios:**
- HTTP errors (404, 500, timeouts)
- Malformed HTML (parser errors)
- Network interruptions

**Strategy:**
- Log failures: `logs/errors.log`
- Skip failed URLs: Don't crash the crawler
- Retry transient errors: Max 3 retries with exponential backoff
- Final failures: Write to `data/failed_urls.txt` for later review

---

### 5. Data Schema Design
**Question to answer:** What fields do we extract from each section?

**Inspect sample HTML first!**

Save 2-3 section pages as HTML:
```bash
curl "https://govt.westlaw.com/calregs/Document/{GUID}?viewType=FullText" > samples/section_001.html
```

Then manually inspect and identify:
- Where is the section number? (CSS selector or XPath)
- Where is the citation? (e.g., "1 CCR § 1")
- Where is the full text?
- Where is the hierarchy breadcrumb?

**Proposed schema (to be refined after HTML inspection):**
```json
{
  "url": "https://govt.westlaw.com/calregs/Document/...",
  "guid": "I7A6B47D0FD4311ECBA0CE8BD2C3F45C2",
  "section_number": "§ 1",
  "citation": "1 CCR § 1",
  "title": "Title 1. General Provisions",
  "division": null,
  "chapter": "Chapter 1. ...",
  "subchapter": null,
  "article": null,
  "text_html": "<p>...</p>",
  "text_plain": "...",
  "extracted_at": "2026-01-31T11:48:02Z"
}
```

---

## Concrete Tasks for Phase 2

### Task 1: Save Sample HTML Files (30 min)
1. Visit 3 different section pages in your browser
2. Save each as HTML: Right-click → Save As → "Complete Webpage"
3. Store in `samples/section_001.html`, `section_002.html`, etc.
4. Choose sections from different Titles to test variety

### Task 2: Inspect HTML Structure (45 min)
1. Open one saved HTML file in a text editor
2. Search for the section number, citation, text
3. Note the CSS classes or element IDs
4. Draft CSS selectors:
   ```
   Section number: div.section-header > span.number
   Citation: ...
   Text: ...
   ```
5. Document in `schema_notes.md`

### Task 3: Draft architecture.md (60 min)
Create `architecture.md` with these sections:

```markdown
# Crawler Architecture

## Overview
BFS crawler starting at /calregs/Index...

## Components
### 1. URL Discovery (Phase 3)
- Fetch /Browse/ pages
- Extract links
- Classify as /Browse/ (queue) or /Document/ (store)

### 2. State Persistence
- Queue checkpoint every 100 URLs
- Visited set stored in visited_urls.txt
- Resume from checkpoint if exists

### 3. Rate Limiting
- 1.5 second delay between requests
- User-Agent: CCR-Crawler/1.0

### 4. Error Handling
- Retry transient errors (max 3)
- Log permanent failures
- Continue crawling on errors

## Data Flow
Index → Extract links → Classify → Queue or Store → Checkpoint → Repeat

## Checkpointing
- Frequency: Every 100 URLs
- Format: JSON
- Resume: Load queue_state.json if exists
```

### Task 4: Draft schema.json (30 min)
Based on HTML inspection, create `schema.json`:
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "url": {"type": "string"},
    "guid": {"type": "string"},
    "section_number": {"type": "string"},
    ...
  },
  "required": ["url", "guid", "section_number", "text_plain"]
}
```

---

## What NOT to Do in Phase 2

❌ Don't write the crawler code yet  
❌ Don't install Python libraries yet  
❌ Don't create a database  
❌ Don't test parsing logic  
❌ Don't worry about performance optimization

---

## Phase 2 Deliverables Checklist

- [ ] `samples/section_001.html` (and 2-3 more)
- [ ] `schema_notes.md` (HTML inspection notes)
- [ ] `architecture.md` (system design)
- [ ] `schema.json` (data structure definition)

**Estimated time:** 2-3 hours

---

## When You're Done

Phase 2 is complete when you can answer:
1. ✅ What is the crawler's starting point?
2. ✅ How are URLs queued and deduplicated?
3. ✅ How does the crawler resume after a crash?
4. ✅ What fields are extracted from each section?
5. ✅ Where are those fields located in the HTML?

**Next:** Proceed to Phase 3 (Implementation) only after these are documented.

---

## Need Help?

If you get stuck:
- **HTML structure unclear?** Save more samples, compare patterns
- **Schema design uncertain?** Start simple (fewer fields), expand later
- **Checkpointing complex?** Start without it, add after basic crawler works

The goal is a design document, not perfect code.
