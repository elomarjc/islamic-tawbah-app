"""
app/engine/analyzer.py

Analyzer Coordinator Engine (Requirement R2 & Feature #14).
Coordinates the analysis pipeline:
Confession Text -> Incident Splitter -> Fiqh Classifier -> Rule Engine / LLM ->
RAG Sanitizer -> 17-field Pydantic AnalysisResultSchema validation.
"""

from __future__ import annotations

import logging
from typing import Dict, Any, Optional

from app.schemas import AnalysisResultSchema
from app.engine.rule_engine import get_rule_engine
from app.engine.llm_client import get_llm_client
from app.engine.rag_service import get_rag_service

logger = logging.getLogger("tawbah.analyzer")


class IslamicAnalyzer:
    """
    Coordinator and orchestrator for Islamic Tawbah Analysis.
    Enforces strict Pydantic v2 contract across all 17 required keys.
    """

    def __init__(self):
        self.rule_engine = get_rule_engine()
        self.llm_client = get_llm_client()
        self.rag_service = get_rag_service()

    def analyze_confession(
        self,
        confession_text: str,
        is_development_mode: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Coordinates full analysis of a text confession.
        Returns a validated dictionary matching AnalysisResultSchema.
        """
        if not confession_text or not isinstance(confession_text, str) or not confession_text.strip():
            raise ValueError("Confession text must not be empty or whitespace.")

        clean_text = confession_text.strip()

        # Execute analysis via LLM Client (which delegates to Rule Engine in offline/dev mode)
        analysis_data = self.llm_client.analyze(clean_text)

        # Enforce RAG sanitization and anti-hallucination verification
        sanitized = self.rag_service.validate_and_sanitize_analysis(analysis_data)

        # Strictly validate and serialize using Pydantic v2
        validated_model = AnalysisResultSchema.model_validate(sanitized)
        return validated_model.model_dump()


# Global Singleton
_ANALYZER_INSTANCE: Optional[IslamicAnalyzer] = None


def get_analyzer() -> IslamicAnalyzer:
    """Returns the singleton instance of IslamicAnalyzer."""
    global _ANALYZER_INSTANCE
    if _ANALYZER_INSTANCE is None:
        _ANALYZER_INSTANCE = IslamicAnalyzer()
    return _ANALYZER_INSTANCE


def analyze_confession(text: str) -> Dict[str, Any]:
    """Convenience function for analyzing a confession."""
    return get_analyzer().analyze_confession(text)
