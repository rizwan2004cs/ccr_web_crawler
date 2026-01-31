# Phase 3 — URL Discovery Crawler

**Status:** Implementation Complete  
**Date:** 2026-01-31

---

## Implementation Summary

Phase 3 implements a Breadth-First Search (BFS) crawler that discovers all CCR section URLs by traversing navigation pages.

### Files Created

1. **`crawler/discovery.py`** — Main crawler implementation
   - BFS algorithm with `collections.deque`
   - URL classification (`/Browse/` vs `/Document/`)
   - Checkpoint/resume functionality
   - Rate limiting (1.5s delay)
   - Error handling and logging

2. **`test_crawler.py`** — Limited test script
   - Validates crawler logic on small subset
   - Max 50 URLs, 10 sections
   - Fast testing before 24-hour full crawl

3. **`requirements.txt`** — Python dependencies
   - requests
   - beautifulsoup4
   - lxml

### Environment Setup

✅ Python virtual environment: `venv/`  
✅ Dependencies installed  
✅ Directory structure created:
```
ccr_web_crawler/
├── crawler/
│   └── discovery.py
├── checkpoints/      (auto-created on first run)
├── logs/             (auto-created on first run)
├── data/             (auto-created on first run)
├── venv/
├── test_crawler.py
└── requirements.txt
```

---

## How to Use

### 1. Activate Virtual Environment

**Windows:**
```bash
.\venv\Scripts\activate
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

### 2. Test Crawler (Recommended First)

Run limited crawl to validate logic:
```bash
python test_crawler.py
```

**Expected output:**
- Visits ~50 URLs
- Discovers ~10 section URLs
- Prints summary of discovered sections
- Takes ~1-2 minutes

**Success criteria:**
- No errors
- At least a few section URLs discovered
- Links are properly classified

### 3. Run Full Crawler

Once test passes, run full discovery:
```bash
python crawler/discovery.py
```

**Expected behavior:**
- Starts at https://govt.westlaw.com/calregs/Index
- Traverses all navigation pages (BFS)
- Discovers all section URLs
- Checkpoints every 100 URLs
- **Estimated time: ~3-5 hours** (navigation pages only)

**Output:**
- `checkpoints/queue_state.json` — Crawler state
- `checkpoints/visited_urls.txt` — All visited URLs
- `checkpoints/discovered_urls.txt` — All section URLs found
- `logs/discovery.log` — Detailed log

### 4. Resume After Interruption

If crawler stops (Ctrl+C, crash, etc.):
```bash
python crawler/discovery.py
```

Automatically resumes from last checkpoint.

---

## Implementation Details

### BFS Algorithm

```python
queue = [START_URL]
visited = set()
discovered_sections = []

while queue:
    url = queue.pop(0)  # FIFO
    
    if url in visited:
        continue
    
    visited.add(url)
    html = fetch(url)
    links = extract_links(html)
    
    for link in links:
        if is_navigation_url(link):
            queue.append(link)  # Traverse
        
        elif is_section_url(link):
            discovered_sections.append(link)  # Record
```

### URL Classification

**Navigation URLs (traversed):**
```
/calregs/Browse/Home/California/CaliforniaCodeofRegulations?guid=...
```

**Section URLs (recorded):**
```
/calregs/Document/{GUID}?viewType=FullText
```

### Checkpoint/Resume

**Saves every 100 URLs:**
- Queue state (what's left to crawl)
- Visited URLs (avoid duplicates)
- Discovered sections (output)

**Resume logic:**
- If checkpoint exists, load it
- Otherwise, start fresh

### Rate Limiting

- **1.5 second delay** between requests
- Respectful to server
- No parallelization (single-threaded)

### Error Handling

- **Network errors:** Logged, crawler continues
- **Parse errors:** Logged, crawler continues
- **Unexpected errors:** Checkpoint saved, then raise

---

## Validation Checklist

Before running full crawl:

- [ ] Test crawler runs without errors
- [ ] At least 5+ section URLs discovered in test
- [ ] Links properly classified (Browse vs Document)
- [ ] Checkpoint files created after test
- [ ] Log file shows INFO messages

---

## Expected Output (Full Crawl)

**After Phase 3 completes:**
```
checkpoints/discovered_urls.txt should contain:
- Estimated 40,000-60,000 section URLs
- All unique (no duplicates)
- All from extractable titles (1-23, 25-28)
- Title 24 navigation traversed, but sections marked for external redirect
```

**Next Phase:**
Phase 4 will read `discovered_urls.txt` and extract content from each section.

---

## Troubleshooting

**Issue:** `ModuleNotFoundError: No module named 'requests'`  
**Solution:** Activate virtual environment first

**Issue:** Crawler seems stuck  
**Solution:** Check logs (`logs/discovery.log`) for errors or slow responses

**Issue:** Rate limiting / 429 errors  
**Solution:** Increase `DELAY_SECONDS` in `discovery.py` (currently 1.5)

**Issue:** Need to stop crawl  
**Solution:** Ctrl+C (graceful stop with checkpoint)

---

## Performance Estimates

Based on architecture design:

- **Navigation pages:** ~3,000-5,000 pages
- **Rate:** 1.5s per page
- **Time:** 3-5 hours for URL discovery

**Note:** This is Phase 3 only (discovery). Content extraction (Phase 4) will take longer (~20 hours).

---

## Next Steps After Phase 3

1. ✅ Verify `discovered_urls.txt` exists and has content
2. ✅ Spot-check URLs (should be `/Document/` format)
3. ✅ Check logs for error rate (<1% acceptable)
4. → Proceed to Phase 4 (Content Extraction)

---

**Status:** ✅ **Ready for Testing**

Run `python test_crawler.py` to begin validation.
