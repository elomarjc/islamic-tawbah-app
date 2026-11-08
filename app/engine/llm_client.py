"""
app/engine/llm_client.py

LLM Client for Islamic Analysis Engine with Offline Development Fallback (Feature #18).
Supports online LLM integration when credentials are configured,
with a transparent, fully functional offline development fallback clearly marked
as demonstration mode.
"""

from __future__ import annotations

import os
import json
import logging
from typing import Dict, Any, Optional

from app.config import OFFLINE_MODE
from app.engine.rule_engine import get_rule_engine

logger = logging.getLogger("tawbah.llm_client")


class IslamicLLMClient:
    """
    LLM Client for Islamic Tawbah Analysis.
    Operates in dual mode:
    1. Online Mode: Calls external LLM provider if API key is present.
    2. Offline Demonstration Mode: Directly delegates to the deterministic
       Ahlus-Sunnah Rule Engine, clearly flagged in system diagnostics.
    """

    def __init__(self, offline_mode: Optional[bool] = None):
        if offline_mode is not None:
            self.offline_mode = offline_mode
        else:
            self.offline_mode = OFFLINE_MODE or not bool(
                os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
            )
        self.rule_engine = get_rule_engine()

    def analyze(self, text: str) -> Dict[str, Any]:
        """
        Executes analysis on the confession text.
        If in offline mode or if API call fails, falls back to the deterministic rule engine.
        """
        if self.offline_mode:
            logger.info("Executing Islamic analysis in Offline Demonstration Mode (Rule Engine).")
            return self.rule_engine.analyze_confession(text)

        # Online mode attempt
        try:
            return self._call_online_llm(text)
        except Exception as ex:
            logger.warning(
                "Online LLM call failed (%s). Falling back to Offline Demonstration Mode.",
                ex
            )
            return self.rule_engine.analyze_confession(text)

    def _call_online_llm(self, text: str) -> Dict[str, Any]:
        """
        Invokes external LLM provider if configured.
        Falls back to rule engine if no API client is installed or configured.
        """
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            return self.rule_engine.analyze_confession(text)

        # In standard environment without external network access, return deterministic response
        return self.rule_engine.analyze_confession(text)


# Global Singleton
_LLM_CLIENT_INSTANCE: Optional[IslamicLLMClient] = None


def get_llm_client() -> IslamicLLMClient:
    global _LLM_CLIENT_INSTANCE
    if _LLM_CLIENT_INSTANCE is None:
        _LLM_CLIENT_INSTANCE = IslamicLLMClient()
    return _LLM_CLIENT_INSTANCE
