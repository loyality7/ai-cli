import urllib.request
import urllib.parse
import re
import html
from typing import Optional

def search_web(query: str) -> str:
    """Search the web using DuckDuckGo HTML search (zero dependencies)."""
    url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            body = response.read().decode('utf-8', errors='ignore')
            
            snippets = re.findall(r'<a class="result__snippet"[^>]*>(.*?)</a>', body, re.DOTALL)
            results = []
            
            for i, snip in enumerate(snippets[:5]):
                clean_snip = re.sub(r'<[^>]+>', '', snip)
                clean_snip = html.unescape(clean_snip).strip()
                results.append(f"{i+1}. {clean_snip}")
                
            if not results:
                return "No search results found."
            return "\n".join(results)
    except Exception as e:
        return f"Search error: {e}"

def fetch_url(url: str) -> str:
    """Fetch content of a URL or resolve GitHub repository readme files."""
    # GitHub repository URL detection
    github_match = re.match(r"https?://(?:www\.)?github\.com/([^/]+)/([^/]+)/?$", url)
    if github_match:
        owner, repo = github_match.group(1), github_match.group(2)
        # Try common README names
        readme_names = ("README.md", "README.rst", "README.txt", "readme.md", "README")
        for branch in ("main", "master"):
            for name in readme_names:
                raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{name}"
                req = urllib.request.Request(raw_url, headers={"User-Agent": "Mozilla/5.0"})
                try:
                    with urllib.request.urlopen(req, timeout=3) as response:
                        return response.read().decode('utf-8', errors='ignore')
                except Exception:
                    continue

    # General page fetch
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            content = response.read().decode('utf-8', errors='ignore')
            # Strip script and style blocks
            content = re.sub(r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>', '', content, flags=re.IGNORECASE)
            content = re.sub(r'<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>', '', content, flags=re.IGNORECASE)
            # Remove tags
            text = re.sub(r'<[^>]+>', ' ', content)
            # Normalize whitespace
            text = re.sub(r'\s+', ' ', text)
            return text[:3000].strip()
    except Exception as e:
        return f"Error fetching URL: {e}"
