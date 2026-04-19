"""Knowledge Base loader and reader utility.

Handles loading and reading files from the knowledge base folder.
Supports: PDF, CSV, XLSX, DOCX, TXT files.
"""

import logging
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
import mimetypes

from .config import KNOWLEDGE_BASE_PATH

logger = logging.getLogger(__name__)

# Supported file extensions
SUPPORTED_EXTENSIONS = {".pdf", ".csv", ".xlsx", ".docx", ".txt"}


class KnowledgeBaseFile:
    """Represents a knowledge base file."""
    
    def __init__(self, path: Path):
        self.path = path
        self.name = path.name
        self.extension = path.suffix.lower()
        self.size = path.stat().st_size
        self.modified = path.stat().st_mtime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "name": self.name,
            "extension": self.extension,
            "size_bytes": self.size,
            "size_human": self._format_size(self.size),
            "modified": self.modified,
        }
    
    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Format byte size to human readable string."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"
    
    def read_text(self) -> str:
        """Read file content as text."""
        try:
            if self.extension == ".txt":
                return self.path.read_text(encoding="utf-8")
            elif self.extension == ".csv":
                return self.path.read_text(encoding="utf-8")
            else:
                # For other formats, return a placeholder
                # In production, you'd use specific libraries (PyPDF2, python-docx, etc.)
                return f"[{self.extension.upper()} file: {self.name}]"
        except Exception as e:
            logger.error(f"Failed to read file {self.name}: {e}")
            return f"[Error reading file: {self.name}]"


class KnowledgeBase:
    """Knowledge Base manager for loading and accessing files."""
    
    def __init__(self, base_path: Optional[str] = None):
        self.base_path = Path(base_path or KNOWLEDGE_BASE_PATH)
        self._ensure_directory()
    
    def _ensure_directory(self) -> None:
        """Ensure the knowledge base directory exists."""
        if not self.base_path.exists():
            logger.info(f"Creating knowledge base directory: {self.base_path}")
            self.base_path.mkdir(parents=True, exist_ok=True)
    
    def list_files(self) -> List[KnowledgeBaseFile]:
        """List all supported files in the knowledge base."""
        files = []
        if not self.base_path.exists():
            return files
        
        for file_path in self.base_path.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
                files.append(KnowledgeBaseFile(file_path))
        
        # Sort by modification time (newest first)
        files.sort(key=lambda f: f.modified, reverse=True)
        return files
    
    def get_file(self, filename: str) -> Optional[KnowledgeBaseFile]:
        """Get a specific file by name."""
        file_path = self.base_path / filename
        if file_path.exists() and file_path.is_file():
            if file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
                return KnowledgeBaseFile(file_path)
        return None
    
    def save_file(self, filename: str, content: bytes) -> KnowledgeBaseFile:
        """Save a file to the knowledge base.
        
        Args:
            filename: Name of the file.
            content: File content as bytes.
            
        Returns:
            KnowledgeBaseFile object.
        """
        # Validate extension
        ext = Path(filename).suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file type: {ext}. Supported: {SUPPORTED_EXTENSIONS}")
        
        file_path = self.base_path / filename
        
        # Write file
        file_path.write_bytes(content)
        logger.info(f"Saved knowledge base file: {filename}")
        
        return KnowledgeBaseFile(file_path)
    
    def delete_file(self, filename: str) -> bool:
        """Delete a file from the knowledge base.
        
        Args:
            filename: Name of the file to delete.
            
        Returns:
            True if deleted, False if not found.
        """
        file_path = self.base_path / filename
        if file_path.exists() and file_path.is_file():
            file_path.unlink()
            logger.info(f"Deleted knowledge base file: {filename}")
            return True
        return False
    
    def load_context(self) -> str:
        """Load and combine context from all knowledge base files.
        
        Returns:
            Combined text content from all files.
        """
        files = self.list_files()
        contexts = []
        
        for file in files:
            content = file.read_text()
            if content:
                contexts.append(f"--- {file.name} ---\n{content}\n")
        
        return "\n".join(contexts) if contexts else "No knowledge base files available."


# Singleton instance
_knowledge_base: Optional[KnowledgeBase] = None


def get_knowledge_base() -> KnowledgeBase:
    """Get or create the Knowledge Base singleton."""
    global _knowledge_base
    if _knowledge_base is None:
        _knowledge_base = KnowledgeBase()
    return _knowledge_base
