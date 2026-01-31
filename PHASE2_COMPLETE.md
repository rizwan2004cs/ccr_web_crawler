# Phase 2 Complete — Architecture Design Summary

**Date:** 2026-01-31  
**Phase:** Architecture Design  
**Status:** ✅ Complete

---

## Deliverables Created

### ✅ architecture.md
Comprehensive crawler design document including:
- BFS crawling algorithm (pseudocode)
- State management and checkpoint strategy
- Rate limiting implementation (1.5s delay)
- Error handling and retry logic
- Validated CSS selectors for content extraction
- Performance estimates (~24 hours single-threaded)
- Implementation checklist

### ✅ schema.json
JSON Schema definition for extracted section data:
- 11 fields (6 required, 5 optional)
- Hierarchy object supporting variable-depth paths
- Both HTML and plain text formats
- ISO 8601 timestamp for tracking
- Validates against all sample data

### ✅ samples/ directory
5 real HTML section pages collected:
- § 1031.2 (Title 2)
- § 1031.7 (Title 2)
- § 1031.12 (Title 2)
- § 100405 (Title 24)
- 1 Title-level navigation page

### ✅ Updated Documentation
- `observations.md` — CSS selectors and structural patterns
- `README.md` — Phase 2 marked complete

---

## Key Technical Decisions

### 1. Crawling Strategy: BFS (Breadth-First Search)
**Rationale:**
- Discovers shallow content first (good for early validation)
- Natural level-by-level progression
- Easy to checkpoint at any level
- Prevents deep recursion issues

### 2. State Persistence: JSON + Text Files
**Rationale:**
- Simple, human-readable formats
- Easy to inspect and debug
- No database overhead for Phase 3/4
- Checkpoint every 100 URLs for safety

### 3. Rate Limiting: 1.5 Second Delay
**Rationale:**
- Respectful to server (no robots.txt restrictions doesn't mean "spam")
- Avoids IP blocking
- ~24 hour total crawl time is acceptable
- Can be optimized in Phase 6 if needed

### 4. Data Format: JSON Lines (.jsonl)
**Rationale:**
- Streaming-friendly (append-only)
- Resilient to crashes (partial file is valid)
- Easy to process line-by-line
- Compatible with downstream tools (jq, pandas, etc.)

### 5. Error Handling: Retry + Log + Continue
**Rationale:**
- Transient errors (timeouts) are retried (max 3)
- Permanent errors (404) are logged and skipped
- Crawler doesn't crash on single failure
- Failed URLs tracked for later review

---

## Critical Findings

### ✅ CSS Selector Stability
All 5 samples use **identical, semantic class names**:
- `h1#co_docHeaderTitleLine > span#title` — Section title
- `.co_cmdExpandedcite` — Canonical citation
- `#co_prelimContainer .co_prelimHead` — Hierarchy
- `.co_contentBlock.co_section .co_paragraphText` — Body text

**Implication:** Parser is unlikely to break due to structural changes.

### ✅ Hidden Metadata Discovery
Every section page contains hidden JSON metadata:
```html
<input id="co_document_metaInfo_{GUID}" 
       value='{"docGuid":"...","titleText":"..."}'>
```

**Implication:** GUID extraction is trivial, enables deduplication.

### ✅ Variable Hierarchy Depth
Not all sections have Division/Subchapter/Article levels.

**Implication:** Schema must allow `null` values for optional hierarchy levels.

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Site structure changes | Low | High | Validate selectors on random samples during crawl |
| Rate limiting/blocking | Medium | High | Monitor HTTP status, adjust delay if 429 errors |
| Incomplete discovery | Low | Critical | Log all skipped URLs, verify total count |
| Parser failures | Low | Medium | <1% failure rate acceptable, log for review |
| Crawler crashes | Medium | Low | Checkpoint every 100 URLs, resume on restart |

---

## Next Steps → Phase 3

**Prerequisites:**
1. Install Python dependencies
2. Create `crawler/` directory
3. Implement `crawler/discovery.py` based on `architecture.md`

**Starting Point:**
```python
# crawler/discovery.py
from collections import deque
import requests
from bs4 import BeautifulSoup

START_URL = "https://govt.westlaw.com/calregs/Index"

def main():
    queue = deque([START_URL])
    visited = set()
    discovered_sections = []
    
    # BFS implementation follows architecture.md
    # ...
```

**Testing Strategy:**
1. Test on 1 Title first (validate discovery logic)
2. Verify checkpoint save/resume works
3. Monitor logs for errors
4. Full crawl only after validation

---

## Success Metrics (Phase 2)

✅ Architecture document created  
✅ Data schema defined and validated  
✅ HTML samples collected  
✅ CSS selectors confirmed across all samples  
✅ No ambiguities remaining about implementation approach  
✅ Estimated performance characteristics documented  

**All Phase 2 objectives met.**

---

## Engineering Lesson

**Design documentation prevents implementation chaos.**

You now have:
- A clear algorithm (BFS)
- Known data locations (CSS selectors)
- Defined output format (JSON schema)
- Error handling strategy (retry + log)
- Recovery mechanism (checkpoints)

**Time to design:** ~2-3 hours  
**Time saved in debugging:** Potentially days

The next step (Phase 3) is **pure implementation** — no design decisions remain.

---

**Ready for Phase 3:** ✅ **Approved**
