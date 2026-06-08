"""Web page scraping with content extraction."""
import logging, time
from typing import Optional
import requests
from bs4 import BeautifulSoup
from config.settings import SCRAPE_DELAY, SCRAPE_TIMEOUT, MAX_PAGE_CONTENT_CHARS, SEARCH_PROXY
logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"}
PROXIES = {"http": SEARCH_PROXY, "https": SEARCH_PROXY} if SEARCH_PROXY else None

def scrape_page(url: str, max_chars: int = MAX_PAGE_CONTENT_CHARS) -> Optional[str]:
    try:
        time.sleep(SCRAPE_DELAY)
        r = requests.get(url, headers=HEADERS, proxies=PROXIES, timeout=SCRAPE_TIMEOUT)
        r.raise_for_status()
        r.encoding = r.apparent_encoding or 'utf-8'
        soup = BeautifulSoup(r.text, 'html.parser')
        for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
            tag.decompose()
        text = soup.get_text(separator='\n', strip=True)
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        text = '\n'.join(lines)
        if len(text) > max_chars:
            text = text[:max_chars] + "..."
        logger.info(f"[scraper] {url} -> {len(text)} chars")
        return text
    except Exception as e:
        logger.warning(f"[scraper] Failed: {url}: {e}")
    return None
