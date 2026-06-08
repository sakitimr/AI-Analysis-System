"""Web search with multi-engine fallback."""
import logging, re, os
from typing import List, Dict, Any
from urllib.parse import quote_plus
import requests
from bs4 import BeautifulSoup
from config.settings import SEARCH_TIMEOUT, SEARCH_PROXY

logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
PROXIES = {"http": SEARCH_PROXY, "https": SEARCH_PROXY} if SEARCH_PROXY else None

try:
    from ddgs import DDGS
    HAS_DDGS = True
except ImportError:
    HAS_DDGS = False
    logger.warning("ddgs not installed")


def _search_ddgs(query: str, max_results: int) -> List[Dict[str, Any]]:
    """Primary: ddgs package (works with proxies)."""
    results = []
    kwargs = {"timeout": SEARCH_TIMEOUT}
    if SEARCH_PROXY:
        kwargs["proxy"] = SEARCH_PROXY
    with DDGS(**kwargs) as ddgs:
        for r in ddgs.text(query, max_results=max_results):
            results.append({
                "title": r.get("title", ""),
                "url": r.get("href", ""),
                "snippet": r.get("body", "")
            })
    return results


def _search_duckduckgo_html(query: str, max_results: int) -> List[Dict[str, Any]]:
    """Fallback: direct DuckDuckGo HTML scraping via requests."""
    results = []
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    resp = requests.get(url, headers=HEADERS, proxies=PROXIES, timeout=SEARCH_TIMEOUT)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    for r in soup.select(".result")[:max_results]:
        a = r.select_one(".result__a")
        s = r.select_one(".result__snippet")
        if a:
            results.append({
                "title": a.get_text(strip=True),
                "url": a.get("href", ""),
                "snippet": s.get_text(strip=True) if s else ""
            })
    return results


def _search_bing_html(query: str, max_results: int) -> List[Dict[str, Any]]:
    """Last resort: Bing HTML scraping."""
    results = []
    url = f"https://www.bing.com/search?q={quote_plus(query)}"
    resp = requests.get(url, headers=HEADERS, proxies=PROXIES, timeout=SEARCH_TIMEOUT)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    for r in soup.select("li.b_algo")[:max_results]:
        h2 = r.select_one("h2 a")
        p = r.select_one(".b_caption p")
        if h2:
            results.append({
                "title": h2.get_text(strip=True),
                "url": h2.get("href", ""),
                "snippet": p.get_text(strip=True) if p else ""
            })
    return results


def search_web(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """Multi-engine search with automatic fallback."""
    engines = []
    if HAS_DDGS:
        engines.append(("ddgs", _search_ddgs))
    # HTML fallbacks disabled in restricted network; enable if proxy configured
    if SEARCH_PROXY:
        engines.append(("ddg_html", _search_duckduckgo_html))
        engines.append(("bing_html", _search_bing_html))

    for name, fn in engines:
        try:
            results = fn(query, max_results)
            if results:
                logger.info(f"[search] '{query}' -> {len(results)} results (via {name})")
                return results
            logger.debug(f"[search] {name}: 0 results for '{query}'")
        except Exception as e:
            logger.debug(f"[search] {name} failed: {e}")

    logger.warning(f"[search] All engines failed for '{query}'")
    return []
