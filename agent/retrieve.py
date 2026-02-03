import os
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()

class CCRRetriever:
    def __init__(self, index_name="ccr-sections"):
        """Initialize Pinecone retriever (v6 API)"""
        pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        self.index = pc.Index(index_name)
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
    
    def search(self, query: str, top_k: int = 8):
        """
        Search for relevant CCR sections
        
        Args:
            query: User's question
            top_k: Number of results to return
            
        Returns:
            List of dicts with 'metadata' and 'content' keys
        """
        # Generate query embedding
        query_embedding = self.model.encode(query).tolist()
        
        # Search Pinecone
        results = self.index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True
        )
        
        # Format results
        hits = []
        for match in results['matches']:
            hits.append({
                'metadata': match['metadata'],
                'content': match['metadata'].get('content', ''),
                'score': match['score']
            })
        
        return hits
