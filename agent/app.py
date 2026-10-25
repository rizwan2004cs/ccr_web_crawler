import streamlit as st
import os
import logging
from retrieve import CCRRetriever
from groq import Groq

logger = logging.getLogger(__name__)

# Groq retires models over time, so keep them configurable and try a fallback
MODELS = [m for m in [os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"), "openai/gpt-oss-20b"] if m]

st.set_page_config(page_title="CCR Compliance Agent", page_icon="⚖️", layout="wide")

st.title("⚖️ California Regulatory Advisor")
st.markdown("Advising facility operators on **California Code of Regulations (CCR)**.")

# Config
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    logger.error("GROQ_API_KEY is not set")
    st.error("The advisor is temporarily unavailable. Please try again later.")
    st.stop()
    
# Sidebar info


# Initialize Retriever (Cached)
@st.cache_resource
def get_retriever():
    return CCRRetriever()

try:
    retriever = get_retriever()
except Exception:
    logger.exception("Failed to load retriever (did ingest.py run?)")
    st.error("The advisor is temporarily unavailable. Please try again later.")
    st.stop()

# Main Interface
query = st.text_area("Describe your facility or compliance question:", 
    placeholder="e.g., I run a movie theater in San Francisco. What are the fire safety requirements for exit doors?")

if st.button("Get Advice") and query:
    # api_key validation handled at startup
        
    client = Groq(api_key=api_key)
    
    # 1. Retrieve
    with st.spinner("Searching 75,000 regulatory sections..."):
        try:
            hits = retriever.search(query, top_k=8)
        except Exception:
            logger.exception("Retriever search failed")
            st.error("Search is temporarily unavailable. Please try again in a moment.")
            st.stop()
    
    # Display Sources
    with st.expander("📚 Referenced CCR Sections (Context)", expanded=False):
        context_text = ""
        for hit in hits:
            meta = hit['metadata']
            citation = f"{meta.get('title')} > {meta.get('citation')}"
            st.markdown(f"**{citation}**")
            st.text(hit['content'][:300] + "...")
            context_text += f"SECTION: {citation}\nCONTENT: {hit['content']}\n\n"

    # 2. Generate
    with st.spinner("Consulting AI Legal Advisor..."):
        system_prompt = """You are an expert California Regulatory Compliance Consultant. 
        Your job is to advise facility operators based STRICTLY on the provided CCR sections.
        
        Rules:
        1. Answer the user's question clearly and professionally.
        2. Cite specific sections (e.g., "According to Title 24, Section 123...") for every claim.
        3. If the provided context doesn't cover the answer, state that you cannot find specific regulations in the database, but offer general guidance based on the context.
        4. IF INFORMATION IS INSUFFICIENT: Ask specific follow-up questions to narrow down the request (e.g., "Are you asking about indoor or outdoor dining?").
        5. Be helpful, concise, and structured (use bullet points).
        
        Context Data:
        {context}
        """
        
        response = None
        for model in dict.fromkeys(MODELS):
            try:
                completion = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt.format(context=context_text)},
                        {"role": "user", "content": query}
                    ],
                    temperature=0.3,
                    max_completion_tokens=4000,
                    reasoning_effort="low"
                )
                response = completion.choices[0].message.content
                if response:
                    break
            except Exception:
                logger.exception("Groq completion failed for model %s", model)

    if response:
        st.markdown("### 🤖 Compliance Advice")
        st.markdown(response)
    else:
        st.error("The advisor is temporarily unavailable. The referenced CCR sections above are still accurate; please try again in a moment.")

st.markdown("---")
st.caption("Disclaimer: This tool provides information, not legal advice. Database: Jan 2026.")
