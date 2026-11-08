"""
app/engine

Islamic Analysis Engine and Anti-Hallucination RAG Service.
"""

from app.engine.rag_service import (
    IslamicRAGService,
    get_rag_service,
    verify_citation,
)

__all__ = [
    "IslamicRAGService",
    "get_rag_service",
    "verify_citation",
]
