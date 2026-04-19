"""Internal Dashboard API for knowledge base management.

Provides endpoints to upload, view, and delete knowledge base files.
Also manages RAG indexing of documents.
"""

import logging
from typing import List

from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import FileResponse

from .knowledge_base import get_knowledge_base, SUPPORTED_EXTENSIONS
from .rag_retriever import get_rag_retriever

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal", tags=["internal"])


@router.get("/files")
async def list_knowledge_base_files() -> dict:
    """List all files in the knowledge base.
    
    Returns:
        Dictionary with list of files and their metadata.
    """
    try:
        kb = get_knowledge_base()
        files = kb.list_files()
        
        return {
            "files": [f.to_dict() for f in files],
            "count": len(files),
            "supported_extensions": list(SUPPORTED_EXTENSIONS),
        }
    except Exception as e:
        logger.error(f"Error listing files: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)) -> dict:
    """Upload a file to the knowledge base and index it for RAG.
    
    Args:
        file: The file to upload.
        
    Returns:
        Dictionary with upload status and file metadata.
    """
    try:
        # Validate file extension
        import os
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {ext}. Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
            )
        
        # Read file content
        content = await file.read()
        
        # Check file size (10MB limit)
        max_size = 10 * 1024 * 1024  # 10MB
        if len(content) > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size is 10MB."
            )
        
        # Save file
        kb = get_knowledge_base()
        saved_file = kb.save_file(file.filename, content)
        
        # Index for RAG
        retriever = get_rag_retriever()
        indexed = retriever.index_document(file.filename)
        
        logger.info(f"Uploaded and indexed file: {file.filename}")
        
        return {
            "status": "success",
            "message": f"File '{file.filename}' uploaded and indexed successfully",
            "file": saved_file.to_dict(),
            "indexed": indexed,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")


@router.get("/download/{filename}")
async def download_file(filename: str):
    """Download a file from the knowledge base.
    
    Args:
        filename: Name of the file to download.
        
    Returns:
        FileResponse with the file content.
    """
    try:
        kb = get_knowledge_base()
        file = kb.get_file(filename)
        
        if not file:
            raise HTTPException(status_code=404, detail=f"File '{filename}' not found")
        
        return FileResponse(
            path=file.path,
            filename=file.name,
            media_type="application/octet-stream",
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to download file: {str(e)}")


@router.delete("/files/{filename}")
async def delete_file(filename: str) -> dict:
    """Delete a file from the knowledge base and remove from RAG index.
    
    Args:
        filename: Name of the file to delete.
        
    Returns:
        Dictionary with deletion status.
    """
    try:
        kb = get_knowledge_base()
        deleted = kb.delete_file(filename)
        
        if not deleted:
            raise HTTPException(status_code=404, detail=f"File '{filename}' not found")
        
        # Remove from RAG index
        retriever = get_rag_retriever()
        retriever.vector_store.delete_document(filename)
        
        logger.info(f"Deleted file and removed from index: {filename}")
        
        return {
            "status": "success",
            "message": f"File '{filename}' deleted successfully",
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")


@router.post("/index")
async def index_all_documents() -> dict:
    """Index all knowledge base documents for RAG.
    
    Returns:
        Dictionary with indexing results.
    """
    try:
        retriever = get_rag_retriever()
        results = retriever.index_all_documents()
        
        return {
            "status": "success",
            "message": f"Indexed {results['indexed']} of {results['total']} documents",
            "results": results,
        }
        
    except Exception as e:
        logger.error(f"Error indexing documents: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to index documents: {str(e)}")


@router.get("/rag/status")
async def rag_status() -> dict:
    """Get RAG vector store status.
    
    Returns:
        Dictionary with vector store statistics.
    """
    try:
        retriever = get_rag_retriever()
        stats = retriever.vector_store.get_stats()
        
        return {
            "status": "ok",
            "vector_store": stats,
        }
        
    except Exception as e:
        logger.error(f"Error getting RAG status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get RAG status: {str(e)}")


@router.get("/health")
async def internal_health():
    """Health check endpoint for internal dashboard."""
    return {
        "status": "ok",
        "service": "internal-dashboard",
        "features": ["upload", "download", "delete", "list", "index", "rag_status"],
    }
