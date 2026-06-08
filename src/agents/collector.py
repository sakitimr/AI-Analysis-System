"""Collector Agent -- multi-source search and structured data collection."""
import logging, json, time
from typing import List, Dict, Any
from datetime import datetime
from .base import BaseAgent
from src.tools.search import search_web
from src.tools.web_scraper import scrape_page
from src.tools.citation import CitationManager
from src.schema.validators import safe_json_parse
from config.settings import MAX_SEARCH_RESULTS, SCRAPE_DELAY, MAX_PAGE_CONTENT_CHARS, MAX_SCRAPE_PAGES, MAX_SCRAPE_FAILURES

logger = logging.getLogger(__name__)

COLLECTOR_PROMPT = """You are a Competitive Intelligence Collector. Your task is to EXTRACT information from the provided search results — NOT to generate or guess.

CRITICAL RULES:
1. ONLY use information explicitly present in the provided search results. If a piece of information is not in the search results, mark it as "NOT_FOUND" instead of inventing it.
2. Every data point MUST cite the specific source URL it came from.
3. For confidence: "high" = directly stated in official page/data sheet; "medium" = from review/community/indirect source; "low" = inferred from context.
4. Do NOT fabricate feature names, pricing tiers, or user opinions. If the search results don't contain price information, say so explicitly.
5. Do NOT create comparative statements that are not in the source data.

Output JSON with:
- "dimensions": object mapping dimension names to arrays of {{field, value, source_url, source_type, confidence}} objects
- "sources": array of {{url, title, type}} objects"""

class CollectorAgent(BaseAgent):
    def __init__(self, model=None):
        super().__init__(name="collector", model=model)
        self.citation_mgr = CitationManager()

    def collect(self, competitors: List[str], dimensions: List[str]) -> Dict[str, Any]:
        results = {}
        for comp in competitors:
            logger.info(f"[collector] Collecting: {comp}")
            results[comp] = self._collect_single(comp, dimensions)
            time.sleep(SCRAPE_DELAY)
        return results

    def _collect_single(self, competitor: str, dimensions: List[str]) -> dict:
        all_results = []
        for dim in dimensions:
            queries = self._gen_queries(competitor, dim)
            scrape_failures = 0
            for q in queries[:2]:
                try:
                    r = search_web(q, MAX_SEARCH_RESULTS)
                    # 对前 MAX_SCRAPE_PAGES 条结果抓取页面正文
                    for item in r[:MAX_SCRAPE_PAGES]:
                        if "page_content" not in item:
                            content = scrape_page(item["url"])
                            if content:
                                item["page_content"] = content[:MAX_PAGE_CONTENT_CHARS]
                                scrape_failures = 0
                            else:
                                scrape_failures += 1
                                if scrape_failures >= MAX_SCRAPE_FAILURES:
                                    logger.warning(f"[collector] {MAX_SCRAPE_FAILURES} consecutive scrape failures, stopping")
                                    break
                    all_results.extend(r)
                    logger.info(f"[collector] Search '{q}' -> {len(r)} results")
                    if scrape_failures >= MAX_SCRAPE_FAILURES:
                        break
                except Exception as e:
                    logger.warning(f"[collector] Search failed: {e}")
            if scrape_failures >= MAX_SCRAPE_FAILURES:
                break

        if all_results:
            return self._extract_with_llm(competitor, dimensions, all_results)
        logger.warning(f"[collector] No results for {competitor}")
        return self._empty(competitor, dimensions)

    def _gen_queries(self, comp: str, dim: str) -> List[str]:
        # Phase 1: hardcoded templates for common dimensions
        tmpl = {
            "功能对比": [f"{comp} features review 2025", f"{comp} AI coding features comparison"],
            "定价模型": [f"{comp} pricing plans 2025", f"{comp} subscription cost tiers"],
            "用户评价": [f"{comp} vs AI coding tool review", f"{comp} user experience developer review"],
            "SWOT分析": [f"{comp} pros and cons AI IDE", f"{comp} market position analysis 2025"],
        }
        if dim in tmpl:
            return tmpl[dim]
        # Phase 2 (forward-thinking): adaptive LLM query generation for unknown dimensions
        try:
            prompt = f"""Generate 2 specific English search queries to research "{dim}" for "{comp}".
Queries should be concrete search-engine-friendly phrases. Output ONLY a JSON array of 2 strings, no explanation.
Format: ["query1", "query2"]"""
            queries = self.safe_invoke_json(prompt)
            if isinstance(queries, list) and len(queries) >= 2:
                return queries[:2]
        except Exception:
            pass
        return [f"{comp} {dim}"]

    def _extract_with_llm(self, competitor: str, dimensions: List[str], results: List[dict]) -> dict:
        # 优先使用 page_content（完整正文），降级使用 snippet
        parts = []
        for i, r in enumerate(results[:8]):
            parts.append(f"[{i}] {r.get('title','')}\nURL: {r.get('url','')}")
            if r.get("page_content"):
                parts.append(f"PAGE CONTENT:\n{r['page_content'][:3000]}")
            else:
                parts.append(f"SNIPPET: {r.get('snippet','')}")
            parts.append("---")
        ctx = "\n".join(parts)
        prompt = f"""{COLLECTOR_PROMPT}

COMPETITOR: {competitor}
DIMENSIONS: {', '.join(dimensions)}

SEARCH RESULTS (some with full page content):
{ctx}

Output JSON with dimensions and sources."""
        try:
            return self.safe_invoke_json(prompt)
        except Exception as e:
            logger.error(f"[collector] Parse failed: {e}")
        return self._empty(competitor, dimensions)

    def _empty(self, comp: str, dims: List[str]) -> dict:
        return {"competitor": comp, "status": "insufficient_data", "dimensions": {d: [] for d in dims}, "sources": []}

    def recollect(self, competitor: str, dimensions: List[str], hints: List[dict]) -> dict:
        logger.info(f"[collector] Re-collecting {competitor} with {len(hints)} hints")
        failed_dims = list(set(h.get("section", d) for h in hints for d in dimensions))
        return self._collect_single(competitor, failed_dims or dimensions)
