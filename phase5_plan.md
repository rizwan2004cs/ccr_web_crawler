# Phase 5: RAG Agent Implementation Plan

## Goal
Build an AI system that advises facility operators (restaurants, farms, etc.) on relevant CCR sections with citations.

## Architecture (RAG Pipeline)

### 1. Vector Database
*   **Choice:** **ChromaDB**
*   **Why:** Embedded, local, open-source, no sign-up required (Satisfies "free tier" requirement).
*   **Storage:** Local `./chroma_db` folder.

### 2. Embeddings
*   **Choice:** **Sentence-Transformers** (`all-MiniLM-L6-v2`)
*   **Why:** Runs locally on CPU, fast, good performance for semantic search.

### 3. LLM (Reasoning Engine)
*   **Options:**
    *   **External API:** OpenAI (GPT-4), Google (Gemini), Anthropic (Claude). *Best quality, costs money/needs key.*
    *   **Local LLM:** Ollama (Llama3). *Free, but heavy on CPU/RAM.*
    *   **Free API:** Groq (Llama3 on cloud). *Fast, free limited tier.*
*   **Decision:** (Need User Input)

### 4. User Interface
*   **Choice:** **Streamlit** (Web App)
*   **Why:** Fast to build, interactive, displays citations nicely.

## Step-by-Step Implementation

1.  **Environment Setup**
    *   Install `chromadb`, `sentence-transformers`, `streamlit`, `openai` (or other client).

2.  **Indexing Script (`indexer/ingest.py`)**
    *   Read `data/sections_CCR_COMPLETE.jsonl.gz`.
    *   Generate embeddings for Section Title + Text.
    *   Store in ChromaDB with metadata (Title, Chapter, Citation).

3.  **Retrieval Logic (`agent/retrieve.py`)**
    *   Input: "What are the fire safety rules for movie theaters?"
    *   Search: Find top 10 relevant sections.
    *   Output: List of sections with text.

4.  **Agent Interaction (`agent/app.py`)**
    *   System Prompt: "You are a California Regulatory Advisor..."
    *   Context: Inject retrieved sections.
    *   Generation: Answer specific questions with citations.

## Questions for You
1.  **LLM:** Do you have an API Key (OpenAI/Gemini)? Or should we use Groq (Fast & Free)?
2.  **UI:** Is a simple Streamlit web app okay?
