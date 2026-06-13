"""
LLM module — multi-provider AI backend.

Providers:
  - Anthropic (Claude)
  - OpenAI (GPT)
  - Google (Gemini)
  - OpenRouter (multi-model gateway)
  - Custom (any OpenAI-compatible endpoint)
"""

from ai_cli.llm.base import BaseProvider
from ai_cli.llm.factory import get_provider

__all__ = ["BaseProvider", "get_provider"]
