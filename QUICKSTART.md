# Quick Reference — CCR Crawler Commands

**Project:** CCR Web Crawler (Internship Assignment)  
**Current Phase:** 3 Complete → 4 Next

---

## 🚀 Quick Start Commands

### Activate Environment
```bash
.\venv\Scripts\activate
```

### Test Crawler (1-2 min, 50 URLs)
```bash
python test_crawler.py
```

### Full URL Discovery Crawl (5-8 hours)
```bash
python crawler/discovery.py
```

### Monitor Progress
```bash
# Watch logs in real-time
tail -f logs/discovery.log

# Check URLs discovered
wc -l checkpoints/discovered_urls.txt

# View latest checkpoint
cat checkpoints/queue_state.json
```

---

## 📁 Important Files

| File | Purpose |
|------|---------|
| `crawler/discovery.py` | Main crawler (Crawl4AI) |
| `test_crawler.py` | Test script (50 URLs) |
| `checkpoints/discovered_urls.txt` | **Output** (section URLs) |
| `checkpoints/queue_state.json` | Resume state |
| `logs/discovery.log` | Detailed logs |
| `architecture.md` | Design specification |
| `schema.json` | Data structure |
| `PROJECT_STATUS.md` | **Current status** |

---

## ✅ Phase 3 Status

**Implementation:** Complete  
**Testing:** Validated (50 URLs, 0 errors)  
**Assignment Compliance:** Crawl4AI ✅  
**Ready for:** Full crawl (5-8 hours)

---

## 🎯 Next Steps

### Option 1: Start Full Crawl
```bash
.\venv\Scripts\activate
python crawler/discovery.py
```

### Option 2: Design Phase 4
Focus on content extraction architecture

### Option 3: Both (Recommended)
```bash
# Start crawl
python crawler/discovery.py &

# Work on Phase 4 while it runs
```

---

## 📊 Expected Outputs

**After Phase 3 (URL Discovery):**
- `checkpoints/discovered_urls.txt` — 40,000-60,000 section URLs
- Time: 5-8 hours

**After Phase 4 (Content Extraction):**
- `data/sections.jsonl` — All section content
- Time: 20-30 hours

---

## ⚠️ Troubleshooting

### Crawler won't start
```bash
# Check browser installed
.\venv\Scripts\playwright install chromium

# Verify imports
python -c "from crawler import discovery; print('OK')"
```

### Resume after interruption
```bash
# Just run again - auto-resumes
python crawler/discovery.py
```

### Clear checkpoints (start fresh)
```bash
rm -rf checkpoints/*
```

---

**See `PROJECT_STATUS.md` for full details**
