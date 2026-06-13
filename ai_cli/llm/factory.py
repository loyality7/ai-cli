"""
Provider factory — creates the right provider based on config.

This is the only place that knows about specific provider classes.
The rest of the app just calls `get_provider()`.
"""

from typing import Optional

from ai_cli.core.config import cfg, get_api_key
from ai_cli.llm.base import BaseProvider

# ──────────────────────────────────────────────
# Provider registry
# ──────────────────────────────────────────────
PROVIDER_MAP = {
    "anthropic": "ai_cli.llm.anthropic_provider.AnthropicProvider",
    "openai": "ai_cli.llm.openai_provider.OpenAIProvider",
    "google": "ai_cli.llm.google_provider.GoogleProvider",
    "openrouter": "ai_cli.llm.openai_provider.OpenAIProvider",     # OpenRouter is OpenAI-compatible
    "custom": "ai_cli.llm.openai_provider.OpenAIProvider",         # Custom endpoints too
}

# Known models per provider (for onboarding suggestions)

PROVIDER_MODELS = {
    "anthropic": [
      "claude-opus-4.8",
      "claude-opus-4.7",
      "claude-sonnet-4.6",
      "claude-sonnet-4"
    ],

    "openai": [
      "gpt-5.5",
      "gpt-5.5-pro",
      "gpt-5.4",
      "gpt-5.4-mini",
      "gpt-5.4-nano"
    ],

    "google": [
      "gemini-3.5-pro",
      "gemini-3.5-flash",
      "gemini-2.5-pro",
      "gemini-2.5-flash"
    ],

    "openrouter": [
      "anthropic/claude-opus-4.8",
      "openai/gpt-5.5",
      "google/gemini-3.5-flash",
      "meta-llama/llama-4-maverick"
    ],

    "custom": []
}


# Base URLs for known providers
PROVIDER_BASE_URLS = {
    "openrouter": "https://openrouter.ai/api/v1",
}


def _import_class(dotted_path: str) -> type:
    """Import a class from a dotted module path."""
    module_path, class_name = dotted_path.rsplit(".", 1)
    import importlib
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def get_provider(
    provider_name: Optional[str] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> BaseProvider:
    """
    Create a provider instance from config (or overrides).

    Usage:
        provider = get_provider()                    # from config
        provider = get_provider("openai", "gpt-4o")  # explicit
    """
    provider_name = provider_name or cfg.get("provider")
    model = model or cfg.get("model")
    api_key = api_key or get_api_key(provider_name)
    timeout = int(cfg.get("request_timeout", 60))

    if not provider_name:
        raise ValueError("No provider configured. Run `ai` to set up.")
    if not api_key:
        raise ValueError(f"No API key found for '{provider_name}'. Run `ai --setup` to configure.")

    # Resolve base URL
    if not base_url:
        base_url = cfg.get("api_base_url") or PROVIDER_BASE_URLS.get(provider_name)

    # Get provider class
    class_path = PROVIDER_MAP.get(provider_name)
    if not class_path:
        raise ValueError(
            f"Unknown provider '{provider_name}'. "
            f"Supported: {', '.join(PROVIDER_MAP.keys())}"
        )

    provider_class = _import_class(class_path)

    return provider_class(
        api_key=api_key,
        model=model,
        base_url=base_url if base_url else None,
        timeout=timeout,
    )
