import chromadb
from sentence_transformers import SentenceTransformer
import os

class ContextRetriever:
    def __init__(self, persist_dir: str, model_name: str = "all-MiniLM-L6-v2"):
        if not os.path.exists(persist_dir):
            raise ValueError(f"ChromaDB directory not found: {persist_dir}. Please run indexer first.")
            
        self.persist_dir = persist_dir
        self.chroma_client = chromadb.PersistentClient(path=persist_dir)
        try:
            self.collection = self.chroma_client.get_collection(name="project_context")
        except ValueError:
            raise ValueError(f"Collection 'project_context' not found in ChromaDB. Please run indexer first.")
        
        print(f"[RAG] Loading model {model_name}...")
        self.model = SentenceTransformer(model_name)
        print(f"[RAG] Model loaded.")

    def search(self, query: str, top_k: int = 5, max_distance: float = 1.4) -> str:
        # Nhúng câu hỏi thành vector
        query_embedding = self.model.encode(query).tolist()
        
        # Query DB lấy top K chunks kèm distance
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "distances"]
        )
        
        # Kiểm tra kết quả
        if not results or "documents" not in results or not results["documents"]:
            return "(Không tìm thấy context liên quan)"
            
        documents = results["documents"][0]
        distances = results["distances"][0] if "distances" in results and results["distances"] else []
        
        context_parts = []
        for i, doc in enumerate(documents):
            # Lọc theo max_distance để tránh gửi lố context (câu hỏi không liên quan code)
            if i < len(distances) and distances[i] <= max_distance:
                context_parts.append(doc)
            
        if not context_parts:
            return "(Không tìm thấy context có độ tương đồng đủ cao với câu hỏi)"
            
        return "\n".join(context_parts)
