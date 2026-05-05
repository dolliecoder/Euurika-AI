"""
Knowledge Base Module - ChromaDB Search for Eurika AI
Handles document storage and semantic search
"""

import os
import chromadb
from typing import Optional


class KnowledgeBase:
    """ChromaDB-backed knowledge base for semantic search"""
    
    def __init__(self, persist_path: str = "./chroma_doc_db"):
        """Initialize ChromaDB client"""
        self.client = chromadb.PersistentClient(path=persist_path)
    
    def get_collection(self, session_id: str):
        """Get or create a collection for a session"""
        return self.client.get_or_create_collection(name=session_id)
    
    def add_documents(
        self,
        session_id: str,
        documents: list[str],
        ids: list[str],
        metadata: Optional[list[dict]] = None
    ) -> None:
        """
        Add documents to a session's collection
        
        Args:
            session_id: Session identifier
            documents: List of text chunks
            ids: List of chunk IDs
            metadata: Optional metadata for each chunk
        """
        collection = self.get_collection(session_id)
        collection.add(
            documents=documents,
            ids=ids,
            metadatas=metadata
        )
    
    def search(
        self,
        session_id: str,
        query: str,
        top_k: int = 3,
        include_scores: bool = False
    ) -> list[str] | list[dict]:
        """
        Search for relevant documents
        
        Args:
            session_id: Session identifier
            query: Search query
            top_k: Number of results to return
            include_scores: Whether to include relevance scores
            
        Returns:
            List of document chunks, or dicts with doc + score if include_scores
        """
        collection = self.get_collection(session_id)
        
        try:
            results = collection.query(
                query_texts=[query],
                n_results=top_k
            )
            
            if not results.get("documents"):
                return []
            
            documents = results["documents"][0]
            
            if include_scores and results.get("distances"):
                scores = results["distances"][0]
                return [
                    {"text": doc, "score": 1 - dist}
                    for doc, dist in zip(documents, scores)
                ]
            
            return documents
            
        except Exception as e:
            print(f"Search error: {e}")
            return []
    
    def get_document_count(self, session_id: str) -> int:
        """Get number of documents in a session"""
        try:
            collection = self.client.get_collection(name=session_id)
            return collection.count()
        except Exception:
            return 0
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session and all its documents"""
        try:
            self.client.delete_collection(name=session_id)
            return True
        except Exception as e:
            print(f"Delete error: {e}")
            return False
    
    def list_sessions(self) -> list[str]:
        """List all session IDs"""
        return [c.name for c in self.client.list_collections()]


# Global instance
_kb_instance: Optional[KnowledgeBase] = None


def get_knowledge_base(persist_path: Optional[str] = None) -> KnowledgeBase:
    """Get or create global KnowledgeBase instance"""
    global _kb_instance
    if _kb_instance is None:
        path = persist_path or os.getenv("CHROMA_PERSIST_PATH", "./chroma_doc_db")
        _kb_instance = KnowledgeBase(persist_path=path)
    return _kb_instance
