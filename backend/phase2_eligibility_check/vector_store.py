"""Vector store for RAG using ChromaDB.

Stores and retrieves document embeddings for knowledge base queries.
"""

import logging
import hashlib
from pathlib import Path
from typing import List, Optional, Dict, Any

import chromadb
from chromadb.config import Settings

from .config import KNOWLEDGE_BASE_PATH, get_gemini_eligibility_credentials

logger = logging.getLogger(__name__)


class VectorStore:
    """ChromaDB vector store for document embeddings."""
    
    def __init__(self, collection_name: str = "knowledge_base"):
        """Initialize vector store.
        
        Args:
            collection_name: Name of the ChromaDB collection.
        """
        self.collection_name = collection_name
        self.client = None
        self.collection = None
        self._initialize()
    
    def _initialize(self) -> None:
        """Initialize ChromaDB client and collection."""
        # Use persistent storage in knowledge_base folder
        persist_dir = Path(KNOWLEDGE_BASE_PATH) / ".chroma"
        persist_dir.mkdir(parents=True, exist_ok=True)
        
        self.client = chromadb.Client(
            Settings(
                persist_directory=str(persist_dir),
                anonymized_telemetry=False,
            )
        )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        
        logger.info(f"Vector store initialized with collection: {self.collection_name}")
    
    def _get_embedding(self, text: str) -> List[float]:
        """Get embedding for text using Gemini.
        
        Args:
            text: Text to embed.
            
        Returns:
            Embedding vector.
        """
        try:
            import google.generativeai as genai
            creds = get_gemini_eligibility_credentials()
            genai.configure(api_key=creds["api_key"])
            
            # Use Gemini's embedding model
            result = genai.embed_content(
                model="models/embedding-001",
                content=text,
                task_type="retrieval_document",
            )
            return result["embedding"]
        except Exception as e:
            logger.error(f"Error getting embedding: {e}")
            # Return zero vector as fallback
            return [0.0] * 768  # Gemini embedding-001 dimension
    
    def add_document(
        self,
        doc_id: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add a document to the vector store.
        
        Args:
            doc_id: Unique document ID.
            text: Document text content.
            metadata: Optional metadata dictionary.
        """
        try:
            embedding = self._get_embedding(text)
            
            self.collection.add(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[text],
                metadatas=[metadata or {}],
            )
            
            logger.info(f"Added document to vector store: {doc_id}")
        except Exception as e:
            logger.error(f"Error adding document {doc_id}: {e}")
            raise
    
    def add_chunks(self, chunks: List[dict], source: str) -> None:
        """Add multiple chunks from a document.
        
        Args:
            chunks: List of chunk dictionaries with 'text' and 'metadata'.
            source: Source document name.
        """
        ids = []
        embeddings = []
        documents = []
        metadatas = []
        
        for i, chunk in enumerate(chunks):
            # Generate unique ID based on content hash
            content_hash = hashlib.md5(chunk["text"].encode()).hexdigest()[:12]
            doc_id = f"{source}_{content_hash}_{i}"
            
            ids.append(doc_id)
            embeddings.append(self._get_embedding(chunk["text"]))
            documents.append(chunk["text"])
            
            # Merge chunk metadata with source
            meta = chunk.get("metadata", {})
            meta["source"] = source
            meta["chunk_index"] = i
            metadatas.append(meta)
        
        if ids:
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
            )
            logger.info(f"Added {len(ids)} chunks from {source} to vector store")
    
    def search(
        self,
        query: str,
        n_results: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[dict]:
        """Search for similar documents.
        
        Args:
            query: Search query.
            n_results: Number of results to return.
            filter_metadata: Optional metadata filter.
            
        Returns:
            List of result dictionaries with text, metadata, and distance.
        """
        try:
            query_embedding = self._get_embedding(query)
            
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=filter_metadata,
                include=["documents", "metadatas", "distances"],
            )
            
            # Format results
            formatted_results = []
            for i in range(len(results["ids"][0])):
                formatted_results.append({
                    "id": results["ids"][0][i],
                    "text": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i],
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error searching vector store: {e}")
            return []
    
    def delete_document(self, source: str) -> None:
        """Delete all chunks from a document.
        
        Args:
            source: Source document name.
        """
        try:
            self.collection.delete(where={"source": source})
            logger.info(f"Deleted all chunks from {source}")
        except Exception as e:
            logger.error(f"Error deleting document {source}: {e}")
    
    def get_stats(self) -> dict:
        """Get vector store statistics."""
        try:
            count = self.collection.count()
            return {
                "total_documents": count,
                "collection_name": self.collection_name,
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {"total_documents": 0, "collection_name": self.collection_name}


# Singleton instance
_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """Get or create the Vector Store singleton."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
