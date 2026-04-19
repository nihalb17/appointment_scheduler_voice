"""RAG Retriever for knowledge base queries.

Retrieves relevant context from the vector store for eligibility checks.
"""

import logging
from typing import List, Optional

from .vector_store import get_vector_store
from .document_parser import parse_document
from .text_chunker import create_chunks
from .knowledge_base import get_knowledge_base

logger = logging.getLogger(__name__)


class RAGRetriever:
    """Retrieves relevant knowledge base context for queries."""
    
    def __init__(self):
        self.vector_store = get_vector_store()
        self.kb = get_knowledge_base()
    
    def index_document(self, filename: str) -> bool:
        """Index a knowledge base document into the vector store.
        
        Args:
            filename: Name of the file to index.
            
        Returns:
            True if indexed successfully.
        """
        try:
            from pathlib import Path
            
            file_path = Path(self.kb.base_path) / filename
            if not file_path.exists():
                logger.error(f"File not found: {filename}")
                return False
            
            # Parse document
            text = parse_document(file_path)
            if not text or text.startswith("["):
                logger.warning(f"Could not parse document: {filename}")
                return False
            
            # Delete existing chunks for this document
            self.vector_store.delete_document(filename)
            
            # Chunk and add to vector store
            chunks = create_chunks(text, filename)
            self.vector_store.add_chunks(chunks, filename)
            
            logger.info(f"Indexed document: {filename} ({len(chunks)} chunks)")
            return True
            
        except Exception as e:
            logger.error(f"Error indexing document {filename}: {e}")
            return False
    
    def index_all_documents(self) -> dict:
        """Index all documents in the knowledge base.
        
        Returns:
            Dictionary with indexing results.
        """
        files = self.kb.list_files()
        results = {
            "total": len(files),
            "indexed": 0,
            "failed": 0,
            "files": [],
        }
        
        for file in files:
            success = self.index_document(file.name)
            if success:
                results["indexed"] += 1
                results["files"].append({"name": file.name, "status": "indexed"})
            else:
                results["failed"] += 1
                results["files"].append({"name": file.name, "status": "failed"})
        
        return results
    
    def retrieve(
        self,
        query: str,
        n_results: int = 5,
        context_type: Optional[str] = None,
    ) -> str:
        """Retrieve relevant context for a query.
        
        Args:
            query: Search query.
            n_results: Number of results to retrieve.
            context_type: Optional filter for context type.
            
        Returns:
            Formatted context string.
        """
        try:
            # Search vector store
            filter_meta = {"type": context_type} if context_type else None
            results = self.vector_store.search(query, n_results, filter_meta)
            
            if not results:
                # Fallback: try to index documents if vector store is empty
                stats = self.vector_store.get_stats()
                if stats["total_documents"] == 0:
                    logger.info("Vector store empty, indexing documents...")
                    self.index_all_documents()
                    results = self.vector_store.search(query, n_results, filter_meta)
            
            if not results:
                return "No relevant context found in knowledge base."
            
            # Format context
            context_parts = []
            for i, result in enumerate(results, 1):
                source = result["metadata"].get("source", "Unknown")
                text = result["text"]
                context_parts.append(f"[{i}] Source: {source}\n{text}\n")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"Error retrieving context: {e}")
            return "Error retrieving knowledge base context."
    
    def retrieve_for_booking(
        self,
        topic: str,
        time_slot: str,
    ) -> str:
        """Retrieve context relevant to a booking request.
        
        Args:
            topic: Appointment topic.
            time_slot: Requested time slot.
            
        Returns:
            Relevant context string.
        """
        query = f"Booking rules for {topic} at {time_slot}. Slot availability, limits, business hours."
        return self.retrieve(query, n_results=3)
    
    def retrieve_for_cancellation(
        self,
        booking_code: str,
    ) -> str:
        """Retrieve context relevant to a cancellation request.
        
        Args:
            booking_code: Booking code to cancel.
            
        Returns:
            Relevant context string.
        """
        query = f"Cancellation policy for booking {booking_code}. Notice period requirements."
        return self.retrieve(query, n_results=3)


# Singleton instance
_retriever: Optional[RAGRetriever] = None


def get_rag_retriever() -> RAGRetriever:
    """Get or create the RAG Retriever singleton."""
    global _retriever
    if _retriever is None:
        _retriever = RAGRetriever()
    return _retriever


def retrieve_context(query: str, n_results: int = 5) -> str:
    """Convenience function to retrieve context for a query."""
    retriever = get_rag_retriever()
    return retriever.retrieve(query, n_results)
