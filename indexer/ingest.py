import os
import json
import gzip
from pinecone import Pinecone, ServerlessSpec
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()

# Configuration
DATA_FILE = "data/sections_CCR_COMPLETE.jsonl.gz"
INDEX_NAME = "ccr-sections"
BATCH_SIZE = 100

def ingest_data():
    print("Initializing Pinecone...")
    
    # Initialize Pinecone (v6 API - correct syntax from error message)
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    
    # Create index if it doesn't exist
    if INDEX_NAME not in pc.list_indexes().names():
        print(f"Creating index '{INDEX_NAME}'...")
        pc.create_index(
            name=INDEX_NAME,
            dimension=384,  # all-MiniLM-L6-v2 embedding dimension
            metric='cosine',
            spec=ServerlessSpec(
                cloud='aws',
                region='us-east-1'
            )
        )
    
    index = pc.Index(INDEX_NAME)
    
    # Load embedding model
    print("Loading embedding model...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    print(f"Reading {DATA_FILE}...")
    vectors = []
    count = 0
    errors = 0
    
    with gzip.open(DATA_FILE, 'rt', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            
            try:
                data = json.loads(line)
                
                # Extract fields
                section_title = data.get('section_title') or ''
                citation = data.get('citation_short') or ''
                hierarchy = data.get('hierarchy') or {}
                content = data.get('text_plain') or ''
                
                # Build hierarchy string
                hierarchy_parts = []
                if isinstance(hierarchy, dict):
                    for key in ['title', 'division', 'chapter', 'article']:
                        val = hierarchy.get(key)
                        if val:
                            hierarchy_parts.append(str(val))
                hierarchy_str = " > ".join(hierarchy_parts)
                
                # Combine for embedding
                text_content = f"{section_title}\n{citation}\n{hierarchy_str}\n{content[:2000]}"
                
                # Generate embedding
                embedding = model.encode(text_content).tolist()
                
                # Prepare vector
                doc_id = data.get('url', f"doc_{count}")
                vectors.append({
                    "id": doc_id,
                    "values": embedding,
                    "metadata": {
                        "title": section_title[:500] if section_title else "Unknown",
                        "section": data.get("section_number", "")[:100] if data.get("section_number") else "",
                        "citation": citation[:200] if citation else "",
                        "content": content[:1000]  # Store first 1000 chars for display
                    }
                })
                
                count += 1
                
                # Upsert batch
                if len(vectors) >= BATCH_SIZE:
                    index.upsert(vectors=vectors)
                    print(f"Indexed: {count}...", end='\r')
                    vectors = []
                    
            except Exception as e:
                errors += 1
                if errors < 10:
                    print(f"\nError processing record {count}: {e}")
                continue
    
    # Final batch
    if vectors:
        index.upsert(vectors=vectors)
    
    print(f"\nSuccessfully indexed {count} records into Pinecone index '{INDEX_NAME}'")
    if errors > 0:
        print(f"Skipped {errors} records due to errors")
    
    # Print index stats
    stats = index.describe_index_stats()
    print(f"Index stats: {stats}")

if __name__ == "__main__":
    ingest_data()
