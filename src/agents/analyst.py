"""Analyst Agent -- comparative analysis, SWOT, feature matrix."""
import logging, json, uuid
from typing import List, Dict, Any
from datetime import datetime
from .base import BaseAgent
from src.schema.validators import safe_json_parse
from src.schema.competitive import AnalysisResult, FeatureMatrix, FeatureRow, SWOTEntry, SentimentProfile, PricingPlan

logger = logging.getLogger(__name__)
ANALYST_PROMPT = """You are a Competitive Intelligence Analyst. Analyze structured data objectively. Rate features 0-3. Output valid JSON."""

class AnalystAgent(BaseAgent):
    def __init__(self, model=None):
        super().__init__(name="analyst", model=model)

    def analyze(self, collected_data: Dict[str, Any], dimensions: List[str] = None) -> AnalysisResult:
        competitors = list(collected_data.keys())
        dims = dimensions or []
        logger.info(f"[analyst] Analyzing {len(competitors)} competitors | dims={dims}")
        fm = self._build_feature_matrix(competitors, collected_data)
        swot = self._gen_swot(competitors, collected_data) if "SWOT分析" in dims else []
        sentiment = self._analyze_sentiment(competitors, collected_data) if "用户评价" in dims else []
        pricing = self._analyze_pricing(competitors, collected_data) if "定价模型" in dims else []
        insights = self._gen_insights(competitors, collected_data)
        return AnalysisResult(analysis_id=str(uuid.uuid4())[:8], competitors=competitors, feature_matrix=fm, swot=swot, pricing_analysis=pricing, user_sentiment=sentiment, key_insights=insights)

    def _build_feature_matrix(self, comps, collected):
        feats = self._extract_features(comps, collected)
        if not feats:
            return FeatureMatrix(features=[])

        # Build lookup: competitor -> field_name -> value_text
        lookup = {}
        for c in comps:
            lookup[c] = {}
            cd = collected.get(c, {})
            if not isinstance(cd, dict):
                continue
            dims = cd.get("dimensions", {})
            if not isinstance(dims, dict):
                continue
            for item in dims.get("功能对比", []):
                if isinstance(item, dict) and "field" in item:
                    lookup[c][item["field"]] = item.get("value", "")

        # Try LLM scoring first, fall back to heuristic
        try:
            scores = self._score_features_llm(comps, feats, lookup)
        except Exception as e:
            logger.warning(f"[analyst] LLM scoring failed, using heuristic: {e}")
            scores = self._score_features_heuristic(comps, feats, lookup)

        # Build FeatureRows from scores and data
        rows = []
        for feat in feats:
            values = {}
            for c in comps:
                values[c] = scores.get(feat, {}).get(c, 0)
            # Compile notes from each competitor's actual data
            notes_parts = []
            for c in comps:
                v = lookup.get(c, {}).get(feat, "")
                if v:
                    notes_parts.append(f"[{c}] {v[:120]}")
            rows.append(FeatureRow(
                feature=feat, values=values,
                notes=" | ".join(notes_parts) if notes_parts else ""
            ))

        logger.info(f"[analyst] Built matrix: {len(feats)} features x {len(comps)} competitors")
        return FeatureMatrix(features=feats, matrix=rows)

    def _score_features_llm(self, comps, feats, lookup):
        """Use LLM to score features 0-3 based on collected data."""
        # Build context with actual data for each feature
        ctx_parts = []
        for feat in feats:
            ctx_parts.append(f"## Feature: {feat}")
            for c in comps:
                v = lookup.get(c, {}).get(feat, "MISSING")
                ctx_parts.append(f"- {c}: {v[:300]}")
            ctx_parts.append("")
        data_context = "\n".join(ctx_parts)

        prompt = f"""You are scoring AI coding tools on specific features. Rate each feature 0-3:
0 = Not available / no evidence
1 = Basic / limited support
2 = Good / competitive support
3 = Best-in-class / leading edge

COMPETITORS: {comps}

{data_context}

Output STRICT JSON only (no markdown, no explanation):
{{"scores": {{"feature_name": {{"CompetitorA": 2, "CompetitorB": 3}}, ...}}}}"""
        d = self.safe_invoke_json(prompt)
        scores = d.get("scores", {})
        if not scores:
            raise ValueError("LLM returned empty scores")
        return scores

    def _score_features_heuristic(self, comps, feats, lookup):
        """Heuristic fallback: score based on data presence and detail depth."""
        scores = {}
        for feat in feats:
            scores[feat] = {}
            for c in comps:
                val = lookup.get(c, {}).get(feat, "")
                if not val:
                    scores[feat][c] = 0
                elif len(val) > 150:
                    scores[feat][c] = 3  # Rich detail
                elif len(val) > 70:
                    scores[feat][c] = 2  # Good detail
                else:
                    scores[feat][c] = 1  # Basic data available
        return scores

    def _extract_features(self, comps, collected):
        feats = set()
        for c in comps:
            cd = collected.get(c, {})
            if not isinstance(cd, dict):
                continue
            dims = cd.get("dimensions", {})
            if not isinstance(dims, dict):
                continue
            for item in dims.get("功能对比", []):
                if isinstance(item, dict) and "field" in item:
                    feats.add(item["field"])
        return sorted(feats) if feats else ["代码补全", "Chat对话", "多文件编辑", "Agent模式", "模型选择", "插件生态", "价格", "文档"]

    def _gen_swot(self, comps, collected):
        entries = []
        for c in comps:
            data_ctx = self._build_competitor_context(c, collected)
            prompt = f"""You are a Competitive Intelligence Analyst generating a SWOT analysis.

Analyze this competitor based ONLY on the provided data. For each of the 4 SWOT categories, provide at least 3 detailed, evidence-based items.

COMPETITOR: {c}

DATA:
{data_ctx}

Output STRICT JSON only (no markdown, no explanation):
{{"strengths": ["item1", "item2", "item3"], "weaknesses": ["item1", "item2", "item3"], "opportunities": ["item1", "item2", "item3"], "threats": ["item1", "item2", "item3"]}}"""
            try:
                d = self.safe_invoke_json(prompt)
                entries.append(SWOTEntry(
                    competitor=c,
                    strengths=d.get("strengths", ["No data available"]),
                    weaknesses=d.get("weaknesses", ["No data available"]),
                    opportunities=d.get("opportunities", ["No data available"]),
                    threats=d.get("threats", ["No data available"])
                ))
            except Exception as e:
                logger.error(f"[analyst] SWOT {c} failed, using heuristic: {e}")
                entries.append(self._swot_heuristic(c, collected))
        return entries

    def _build_competitor_context(self, comp, collected, dim_filter=None):
        """Compile collected data for one competitor into a text context.
        If dim_filter is set, only include that dimension (e.g. '用户评价').
        """
        cd = collected.get(comp, {})
        if not isinstance(cd, dict):
            return f"No valid data for {comp}"
        parts = []
        dims = cd.get("dimensions", {})
        if not isinstance(dims, dict):
            return f"No valid data for {comp}"
        target_dims = [dim_filter] if dim_filter and dim_filter in dims else list(dims.keys())
        for dim in target_dims:
            items = dims.get(dim, [])
            parts.append(f"## {dim}")
            if isinstance(items, list):
                for item in items[:8]:  # Limit to avoid token overflow
                    if isinstance(item, dict):
                        label = item.get("field", "")
                        val = item.get("value", "")[:200]
                        conf = item.get("confidence", "")
                        parts.append(f"- {label}: {val} (confidence: {conf})")
            parts.append("")
        # Also include sources summary
        sources = cd.get("sources", [])
        if sources:
            parts.append("## 数据来源")
            for s in sources[:5]:
                parts.append(f"- {s.get('title', '')} ({s.get('type', '')})")
        return "\n".join(parts) if parts else f"No data available for {comp}"

    def _swot_heuristic(self, comp, collected):
        """Heuristic SWOT fallback when LLM fails."""
        cd = collected.get(comp, {})
        if not isinstance(cd, dict):
            return [], [], [], []
        strengths = []
        weaknesses = []
        for dim, items in cd.get("dimensions", {}).items():
            for item in (items if isinstance(items, list) else []):
                if isinstance(item, dict):
                    label = item.get("field", "")
                    val = item.get("value", "")
                    conf = item.get("confidence", "")
                    if "positive" in str(label).lower() or conf == "high":
                        strengths.append(val[:120])
                    elif "negative" in str(label).lower() or conf == "low":
                        weaknesses.append(val[:120])
        return SWOTEntry(
            competitor=comp,
            strengths=strengths[:3] if strengths else [f"{comp} provides AI coding capabilities"],
            weaknesses=weaknesses[:3] if weaknesses else ["No specific weakness data collected"],
            opportunities=["Expanding AI IDE market", "Growing demand for developer productivity tools"],
            threats=["Intense competition in AI coding space", "Rapid technology evolution"]
        )

    def _analyze_sentiment(self, comps, collected):
        profiles = []
        for c in comps:
            # Build data context from collected "用户评价" dimension
            data_ctx = self._build_competitor_context(c, collected, dim_filter="用户评价")
            if not data_ctx or data_ctx == f"No valid data for {c}":
                # Fallback: try all dimensions
                data_ctx = self._build_competitor_context(c, collected)
            prompt = f"""{ANALYST_PROMPT}

Analyze user sentiment for {c} BASED ONLY on the provided data below. Do NOT invent or assume data not present.

DATA:
{data_ctx[:2500]}

Output STRICT JSON only (no markdown, no explanation):
{{"positive_themes": ["theme1", "theme2"], "negative_themes": ["theme1", "theme2"], "sentiment_score": 0.5}}

sentiment_score must be between -1 (very negative) and 1 (very positive)."""
            try:
                d = self.safe_invoke_json(prompt)
                profiles.append(SentimentProfile(competitor=c, positive_themes=d.get("positive_themes",[]), negative_themes=d.get("negative_themes",[]), sentiment_score=d.get("sentiment_score",0)))
            except Exception:
                profiles.append(SentimentProfile(competitor=c))
        return profiles

    def _analyze_pricing(self, comps, collected):
        plans = []
        for c in comps:
            cd = collected.get(c, {})
            if not isinstance(cd, dict):
                continue
            dims = cd.get("dimensions", {})
            if not isinstance(dims, dict):
                continue
            for item in dims.get("定价模型", []):
                if isinstance(item, dict):
                    v = item.get("value", "")
                    field = item.get("field", "").lower()
                    vl = v.lower()
                    # Classify tier: field name takes priority over value content
                    if "free" in field or "免费" in field:
                        tier = "free"
                    elif "enterprise" in field or "企业" in field:
                        tier = "enterprise"
                    elif "business" in field or "team" in field:
                        tier = "business"
                    elif "individual" in field:
                        tier = "individual"
                    elif "pro" in field:
                        tier = "pro"
                    elif "免费" in vl or "free" in vl:
                        tier = "free"
                    elif "enterprise" in vl or "企业" in vl:
                        tier = "enterprise"
                    elif "business" in vl or "team" in vl:
                        tier = "business"
                    else:
                        tier = "pro"
                    plans.append(PricingPlan(competitor=c, tier=tier, price=v[:50], source_url=item.get("source_url","")))
        return plans

    def _gen_insights(self, comps, collected):
        # Build summary context from collected data for all competitors
        ctx_parts = []
        for c in comps:
            data_ctx = self._build_competitor_context(c, collected)
            ctx_parts.append(data_ctx[:800])
        data_summary = "\n\n---\n\n".join(ctx_parts)
        try:
            d = self.safe_invoke_json(
                f"You are a Competitive Intelligence Analyst. Based ONLY on the collected data below, "
                f"derive 3-5 concrete key insights (specific, evidence-based, no speculation).\n\n"
                f"COMPETITORS: {comps}\n\n"
                f"COLLECTED DATA:\n{data_summary[:3000]}\n\n"
                f"Output STRICT JSON only: {{\"insights\": [\"insight1\", \"insight2\", ...]}}"
            )
            return d.get("insights", [f"Analysis of {len(comps)} competitors complete"])
        except Exception:
            return [f"Analysis of {len(comps)} competitors complete"]

