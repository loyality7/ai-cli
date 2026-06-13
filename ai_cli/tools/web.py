"""
Web search tool — uses Tavily API for grounded answers.

Falls back to a simple httpx-based search if Tavily is not installed.
"""

from typing import Optional

from ai_cli.core.config import get_api_key


def search(query: str, max_results: int = 3) -> Optional[str]:
    """
    Search the web for a query. Returns formatted results or None.

    Requires TAVILY_API_KEY in env or keys.toml.
    """
    api_key = get_api_key("tavily")
    if not api_key:
        return None

    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=api_key)
        response = client.search(query, max_results=max_results)

        results = []
        for r in response.get("results", []):
            title = r.get("title", "")
            url = r.get("url", "")
            content = r.get("content", "")[:200]
            results.append(f"- {title}\n  {url}\n  {content}")

        return "\n\n".join(results) if results else None

    except ImportError:
        return _fallback_search(query)
    except Exception:
        return None


def _fallback_search(query: str) -> Optional[str]:
    """Basic fallback if Tavily is not installed."""
    try:
        import httpx
        # Use a simple DuckDuckGo instant answer API
        resp = httpx.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": 1},
            timeout=10,
        )
        data = resp.json()
        abstract = data.get("AbstractText", "")
        if abstract:
            return f"- {abstract}\n  Source: {data.get('AbstractSource', '')}"
        return None
    except Exception:
        return None
