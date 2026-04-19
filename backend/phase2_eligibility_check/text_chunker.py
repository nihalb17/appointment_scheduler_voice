"""Text chunking utility for RAG.

Splits documents into overlapping chunks for vector embedding.
"""

import logging
from typing import List

logger = logging.getLogger(__name__)


class TextChunker:
    """Chunks text into overlapping segments for RAG."""
    
    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 100,
        separator: str = "\n",
    ):
        """Initialize chunker.
        
        Args:
            chunk_size: Target size of each chunk in characters.
            chunk_overlap: Number of characters to overlap between chunks.
            separator: Preferred separator for splitting.
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separator = separator
    
    def chunk_text(self, text: str, metadata: dict = None) -> List[dict]:
        """Split text into overlapping chunks.
        
        Args:
            text: Text to chunk.
            metadata: Metadata to attach to each chunk.
            
        Returns:
            List of chunk dictionaries with text and metadata.
        """
        if not text:
            return []
        
        chunks = []
        start = 0
        
        while start < len(text):
            # Find the end of this chunk
            end = start + self.chunk_size
            
            if end >= len(text):
                # Last chunk
                chunk_text = text[start:]
            else:
                # Try to find a good break point
                chunk_text = text[start:end]
                
                # Look for separator to break at
                last_sep = chunk_text.rfind(self.separator)
                if last_sep > self.chunk_size * 0.5:  # Only break if we have substantial content
                    end = start + last_sep + len(self.separator)
                    chunk_text = text[start:end]
            
            # Create chunk with metadata
            chunk = {
                "text": chunk_text.strip(),
                "start_char": start,
                "end_char": min(end, len(text)),
                "metadata": metadata or {},
            }
            chunks.append(chunk)
            
            # Move to next chunk with overlap
            start = end - self.chunk_overlap
            
            # Prevent infinite loop
            if start >= end:
                start = end
        
        logger.info(f"Chunked text into {len(chunks)} chunks")
        return chunks
    
    def chunk_document(self, text: str, source: str, doc_type: str = "document") -> List[dict]:
        """Chunk a document with source metadata.
        
        Args:
            text: Document text.
            source: Document source name (e.g., filename).
            doc_type: Type of document.
            
        Returns:
            List of chunk dictionaries.
        """
        metadata = {
            "source": source,
            "type": doc_type,
        }
        return self.chunk_text(text, metadata)


def create_chunks(text: str, source: str, chunk_size: int = 500, chunk_overlap: int = 100) -> List[dict]:
    """Convenience function to create chunks from text.
    
    Args:
        text: Text to chunk.
        source: Source document name.
        chunk_size: Size of each chunk.
        chunk_overlap: Overlap between chunks.
        
    Returns:
        List of chunk dictionaries.
    """
    chunker = TextChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return chunker.chunk_document(text, source)
