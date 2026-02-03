# CCR Compliance Agent — Web Crawler

**Status:** ✅ **Phase 4 Complete** (100% Data Extracted)  
**Final Output:** `data/sections_CCR_COMPLETE.jsonl` (~75,000 Records)  
**Date:** 2026-02-02

---

## 🚀 Quick Start

### 1. Verification
You can verify the final dataset is present and valid:
```bash
ls -lh data/sections_CCR_COMPLETE.jsonl
head -n 1 data/sections_CCR_COMPLETE.jsonl
```

### 2. Project Structure
```
ccr_web_crawler/
├── crawler/
│   ├── discovery.py    # Phase 3: URL Discovery (BFS)
│   └── extraction.py   # Phase 4: Content Extraction
├── data/
│   └── sections_CCR_COMPLETE.jsonl  # The Final Dataset
├── logs/               # Execution logs
├── scripts/            # Helper scripts (merge, cleanup)
├── requirements.txt    # Dependencies
└── README.md           # This file
```

---

## 🎯 Project Goals

The goal of this project is to build a crawler that discovers and extracts every **California Code of Regulations (CCR)** Section (§) in a structured format for AI/RAG applications.

**Achievement:**
*   **Total URLs Discovered:** 74,997
*   **Total Sections Extracted:** ~75,000 (99%+ Success Rate)
*   **Completeness:** Includes all extractable Titles (1-28, excluding Title 24 external redirect).

---

## 🏗️ Architecture

### Core Technology
*   **Engine:** `Crawl4AI` (`AsyncWebCrawler`) - **Assignment Requirement §6 Satisfied**
*   **Language:** Python 3.10+
*   **Parsing:** `BeautifulSoup` + `lxml`
*   **Concurrency:** `asyncio` with Semaphore control (10-25x)

### Discovery (Phase 3)
*   **Algorithm:** Breadth-First Search (BFS)
*   **Target:** `/Browse/` navigation pages
*   **Output:** `checkpoints/discovered_urls.txt`

### Extraction (Phase 4)
*   **Target:** `/Document/` section pages
*   **Fields:** URL, Section Number, Title, Hierarchy (Title/Division/Chapter), Text (Markdown), Citation
*   **Resilience:**
    *   **Retry Logic:** Built-in Crawl4AI backoff + Custom Recovery Lists
    *   **Checkpointing:** JSON state saving
    *   **Recovery:** 3-stage recovery process for failed URLs

---

## ✅ Assignment Compliance

| Requirement | Implementation | Status |
|-------------|----------------|--------|
| **Use Crawl4AI** | `AsyncWebCrawler` used for all network requests | ✅ SATISFIED |
| **Controlled Concurrency** | `asyncio.Semaphore` used to limit load | ✅ SATISFIED |
| **Retry Logic** | Crawl4AI built-in + Custom Recovery Script | ✅ SATISFIED |
| **URL Normalization** | Canonical URL handling implemented | ✅ SATISFIED |
| **Persistent Checkpoints** | State saved every 100 iterations | ✅ SATISFIED |
| **Completeness** | Multi-pass extraction (Initial -> Recovery -> Final) | ✅ SATISFIED |

---

### Phase 5: RAG Agent
*   **Database:** `Pinecone` (Cloud-hosted, Serverless)
*   **Justification:** 
    - **Scalability**: Cloud-hosted vector database eliminates local storage constraints
    - **Deployment**: No need to distribute large database files (~300MB) - users only need API credentials
    - **Production-Ready**: Serverless architecture with automatic scaling
    - **Assignment Compliance**: Meets all requirements (semantic search, metadata filtering, idempotent upserts)
    - **Free Tier**: Generous free tier (1 index, 100K vectors) sufficient for this prototype
*   **LLM:** Groq (Llama 3.1) - Fast inference

**Setup:**
```bash
# Install dependencies
pip install -r requirements.txt

# Configure API Keys in .env
GROQ_API_KEY=your_groq_key
PINECONE_API_KEY=your_pinecone_key
```

**Run Data Ingestion (One-time, by project maintainer):**
```bash
python indexer/ingest.py
# This creates a Pinecone index 'ccr-sections' with 75k vectors (~5-10 mins)
```

**Launch the AI Agent:**
```bash
# Recommended (ensures correct dependencies):
venv/Scripts/python -m streamlit run agent/app.py

# Standard (if venv is active):
streamlit run agent/app.py
```

**Test Queries:**
*   **Restaurants:** "What are the fire extinguisher requirements for a commercial kitchen?"
*   **Theaters:** "What is the maximum occupancy load for a movie theater waiting area?"
*   **Hospitals:** "How often must emergency backup generators be tested?"
*   **General:** "What are the specific signage requirements for gender-neutral restrooms?"
*   **Safety:** "Are employees required to wear protective gear when handling hazardous chemicals?"

The agent will:
- Retrieve relevant CCR sections via semantic search (Pinecone)
- Provide specific citations (Title, Section numbers)
- Explain why each section applies
- Ask follow-up questions if information is insufficient

**Note for Users:** The Pinecone index is already populated. You only need API keys to query it - no local database setup required!

---

## 🛠️ Usage References

### To Re-Run Discovery
```bash
python crawler/discovery.py
```

### To Re-Run Extraction
```bash
python crawler/extraction.py
```

### To Merge Data (if re-run)
```bash
python scripts/final_finish.py
```
