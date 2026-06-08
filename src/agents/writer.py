"""Writer Agent -- report generation with source citations."""
import logging, uuid, re
from typing import List, Dict, Any
from datetime import datetime
from .base import BaseAgent
from src.schema.competitive import FinalReport, AnalysisResult

logger = logging.getLogger(__name__)

# ── Bilingual label maps ──
T = {
    "zh": {
        "report_title": "Analysis Report",
        "timestamp": "生成时间",
        "competitors": "分析竞品",
        "model": "分析模型",
        "summary": "摘要",
        "overview": "竞品概览",
        "feature_matrix": "核心功能对比矩阵",
        "pricing": "定价模型对比",
        "sentiment": "用户评价分析",
        "swot": "SWOT 分析",
        "conclusion": "结论与建议",
        "sources": "数据来源",
        "score_desc": "评分 (0=缺失 1=基础 2=良好 3=领先)",
        "feature": "功能",
        "notes": "说明",
        "competitor_col": "竞品",
        "developer": "开发商",
        "positioning": "定位",
        "target_user": "目标用户",
        "tier": "层级",
        "price": "价格",
        "strengths": "优势",
        "weaknesses": "劣势",
        "opportunities": "机会",
        "threats": "威胁",
        "positive": "正面",
        "negative": "负面",
        "no_data": "暂无数据",
        "msg_summary_fallback": "本报告对所选的竞品进行了多维度分析。",
        "msg_conclusion_fallback": "分析完成，详见各维度对比。",
        "msg_insight_prefix": "核心发现",
    },
    "en": {
        "report_title": "Analysis Report",
        "timestamp": "Generated",
        "competitors": "Competitors",
        "model": "Model",
        "summary": "Executive Summary",
        "overview": "Competitor Overview",
        "feature_matrix": "Feature Comparison Matrix",
        "pricing": "Pricing Comparison",
        "sentiment": "User Sentiment Analysis",
        "swot": "SWOT Analysis",
        "conclusion": "Conclusion & Recommendations",
        "sources": "Sources",
        "score_desc": "Score (0=Missing 1=Basic 2=Good 3=Leading)",
        "feature": "Feature",
        "notes": "Notes",
        "competitor_col": "Competitor",
        "developer": "Developer",
        "positioning": "Positioning",
        "target_user": "Target User",
        "tier": "Tier",
        "price": "Price",
        "strengths": "Strengths",
        "weaknesses": "Weaknesses",
        "opportunities": "Opportunities",
        "threats": "Threats",
        "positive": "Positive",
        "negative": "Negative",
        "no_data": "No data available",
        "msg_summary_fallback": "This report provides a multi-dimensional competitive analysis of the selected products.",
        "msg_conclusion_fallback": "Analysis complete. See details in each section.",
        "msg_insight_prefix": "Key Findings",
    },
}


class WriterAgent(BaseAgent):
    def __init__(self, model=None):
        super().__init__(name="writer", model=model)

    def write_report(self, analysis: AnalysisResult, collected: Dict[str, Any],
                     dimensions: List[str] = None, language: str = "zh") -> FinalReport:
        dims = dimensions or []
        lang = language if language in T else "zh"
        L = T[lang]
        logger.info(f"[writer] Generating report | comps={analysis.competitors} | dims={dims} | lang={lang}")

        all_sources = self._collect_sources(collected)
        comps_str = " vs ".join(analysis.competitors)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")

        sections = []

        # ── Header ──
        sections.append(f"# {L['report_title']}\n")
        sections.append(f"**{L['timestamp']}:** {ts}  ")
        sections.append(f"**{L['competitors']}:** {comps_str}  ")
        sections.append(f"**{L['model']}:** Doubao-Seed-2.0-lite\n")
        sections.append("---")

        # ── Summary (no sub-heading, inline key findings) ──
        sections.append(f"## {L['summary']}\n")
        sections.append(self._exec_summary(analysis, lang))
        if analysis.key_insights:
            sections.append(f"\n**{L['msg_insight_prefix']}:**")
            for i in analysis.key_insights:
                sections.append(f"- {i}")
        sections.append("\n---")

        # ── Overview ──
        sections.append(f"## {L['overview']}\n")
        sections.append(self._overview(analysis, collected, lang))
        sections.append("\n---")

        # ── Dynamic dimension sections ──
        DIM_TITLES = {
            "功能对比": L["feature_matrix"],
            "定价模型": L["pricing"],
            "用户评价": L["sentiment"],
            "SWOT分析": L["swot"],
        }
        for dim in dims:
            title = DIM_TITLES.get(dim, dim)  # custom dimension uses its own name
            content = self._render_dimension(analysis, collected, dim, lang)
            if content and content != L["no_data"]:
                sections.append(f"## {title}\n")
                sections.append(content)
                sections.append("\n---")

        # ── Conclusion ──
        sections.append(f"## {L['conclusion']}\n")
        sections.append(self._conclusion(analysis, lang))
        sections.append("\n---")

        # ── Sources ──
        sections.append(f"## {L['sources']}\n")
        sections.append(self._sources(all_sources))

        content = "\n".join(sections)
        return FinalReport(
            report_id=str(uuid.uuid4())[:8],
            title=L["report_title"],
            content=content,
            word_count=len(content),
            source_count=len(all_sources),
        )

    def _render_dimension(self, analysis, collected, dim, lang):
        if dim == "功能对比":
            return self._feature_table(analysis, lang)
        elif dim == "定价模型":
            return self._pricing(analysis, lang)
        elif dim == "用户评价":
            return self._sentiment(analysis, lang)
        elif dim == "SWOT分析":
            return self._swot(analysis, lang)
        else:
            return self._generic_dim(analysis, collected, dim, lang)

    def _generic_dim(self, analysis, collected, dim, lang):
        """Render a custom or unrecognised dimension from raw collected data."""
        L = T.get(lang, T["zh"])
        lines = []
        found = False
        for comp in analysis.competitors:
            cd = collected.get(comp, {})
            if not isinstance(cd, dict):
                continue
            dims_data = cd.get("dimensions", {})
            if not isinstance(dims_data, dict):
                continue
            items = dims_data.get(dim, [])
            if items:
                found = True
                lines.append(f"### {comp}")
                for item in items:
                    if isinstance(item, dict):
                        field = item.get("field", "")
                        value = item.get("value", "")
                        lines.append(f"- **{field}**: {value}")
                lines.append("")
        return "\n".join(lines) if found else L["no_data"]

    def _exec_summary(self, a, lang):
        L = T.get(lang, T["zh"])
        lang_name = "Chinese" if lang == "zh" else "English"
        # Guard: if there's no real analysis data, don't hallucinate
        has_data = bool(a.feature_matrix.matrix) or bool(a.swot) or bool(a.pricing_analysis)
        if not has_data:
            return L.get("msg_summary_fallback", "Insufficient data for summary.")
        # Build context from analysis results
        ctx_parts = []
        if a.feature_matrix.matrix:
            ctx_parts.append(f"**Feature Matrix** ({len(a.feature_matrix.matrix)} features):")
            for row in a.feature_matrix.matrix[:8]:
                vals = ", ".join(f"{c}={v}" for c, v in row.values.items())
                ctx_parts.append(f"- {row.feature}: {vals}")
        if a.swot:
            ctx_parts.append(f"\n**SWOT** ({len(a.swot)} competitors):")
            for e in a.swot[:3]:
                ctx_parts.append(f"- {e.competitor}: S={len(e.strengths)} W={len(e.weaknesses)} O={len(e.opportunities)} T={len(e.threats)}")
        if a.pricing_analysis:
            ctx_parts.append("\n**Pricing:** " + "; ".join(f"{p.competitor}:{p.price}" for p in a.pricing_analysis[:6]))
        data_ctx = "\n".join(ctx_parts)
        try:
            return self.invoke(
                f"Write a concise 2-paragraph {lang_name} executive summary for competitive analysis "
                f"of {a.competitors}. Base it ONLY on the data below, do not invent or speculate. "
                f"Do NOT include a section title or heading.\n\n"
                f"ANALYSIS DATA:\n{data_ctx[:2500]}"
            )
        except Exception:
            return ", ".join(f"Analysis of {c}" for c in a.competitors) + "."

    # Hardcoded developer lookup for well-known competitors
    _KNOWN_DEVS = {
        "cursor": ("Anysphere", "AI-first IDE with deep codebase context", "Solo/team developers"),
        "github copilot": ("GitHub / Microsoft", "Universal AI coding assistant", "All developers across IDEs"),
        "trae": ("ByteDance / 字节跳动", "AI-native full-stack IDE for Chinese developers", "Chinese-speaking developers"),
        "windsurf": ("Codeium", "Agentic AI IDE with Cascade", "Independent developers"),
        "通义灵码": ("Alibaba / 阿里云", "AI coding assistant for Alibaba Cloud ecosystem", "Chinese developers"),
        "文心快码": ("Baidu / 百度", "AI coding assistant based on ERNIE", "Chinese developers"),
        "codegeex": ("Zhipu AI / 智谱", "Open source AI coding assistant", "Chinese developers"),
        "iflycode": ("iFlytek / 科大讯飞", "AI coding assistant for domestic market", "Chinese developers"),
        "tabnine": ("Tabnine", "AI code completion with privacy focus", "Enterprise developers"),
        "cody": ("Sourcegraph", "AI coding assistant with code search", "Enterprise team developers"),
        "cline": ("Cline (open source)", "VS Code AI agent extension", "Developer power users"),
    }

    def _overview(self, analysis, collected, lang):
        """Generate overview table with hardcoded dev lookup + LLM fallback."""
        L = T.get(lang, T["zh"])
        # Build info dict: try hardcoded lookup first, then LLM fallback
        info = {}
        unknown_comps = []
        for c in analysis.competitors:
            key = c.lower().strip()
            if key in self._KNOWN_DEVS:
                dev, pos, tgt = self._KNOWN_DEVS[key]
                info[c] = {"developer": dev, "positioning": pos, "target_user": tgt}
            else:
                unknown_comps.append(c)

        # LLM fallback for unknown competitors
        if unknown_comps:
            ctx_parts = []
            for c in unknown_comps:
                cd = collected.get(c, {})
                if isinstance(cd, dict):
                    dims = cd.get("dimensions", {})
                    snippets = []
                    for dname, items in (dims if isinstance(dims, dict) else {}).items():
                        for item in (items if isinstance(items, list) else [])[:3]:
                            if isinstance(item, dict):
                                snippets.append(f"{item.get('field','')}: {item.get('value','')[:100]}")
                    ctx_parts.append(f"## {c}\n" + "\n".join(snippets[:5]) if snippets else f"{c}: no data")
            data_ctx = "\n\n".join(ctx_parts[:3]) if ctx_parts else "No data"
            prompt = f"""Based on the collected data below, fill in the developer, positioning, and target user for each competitor.
If you cannot determine a field from the data, use "Unknown".

DATA:
{data_ctx[:2000]}

Output STRICT JSON only:
{{"competitors": {{"CompetitorName": {{"developer": "...", "positioning": "...", "target_user": "..."}}}}}}"""
            try:
                d = self.safe_invoke_json(prompt)
                info.update(d.get("competitors", {}))
            except Exception:
                pass

        h = [L["competitor_col"], L["developer"], L["positioning"], L["target_user"]]
        rows = ["| " + " | ".join(h) + " |", "|" + "|".join(["------"] * 4) + "|"]
        for c in analysis.competitors:
            entry = info.get(c, {})
            dev = entry.get("developer", "Unknown")
            pos = entry.get("positioning", "Unknown")
            tgt = entry.get("target_user", "Unknown")
            rows.append(f"| {c} | {dev} | {pos} | {tgt} |")
        return "\n".join(rows)

    def _feature_table(self, a, lang):
        L = T.get(lang, T["zh"])
        if not a.feature_matrix.matrix:
            return L["no_data"]
        comps = a.competitors
        score_header = L["score_desc"]
        hdr_comps = " | ".join(f"{c}<br>({score_header})" for c in comps)
        rows = [
            f"| {L['feature']} | {hdr_comps} | {L['notes']} |",
            "|" + "|".join(["------"] * (len(comps) + 2)) + "|",
        ]
        for r in a.feature_matrix.matrix:
            vals = " | ".join(str(r.values.get(c, "N/A")) for c in comps)
            rows.append(f"| {r.feature} | {vals} | {r.notes} |")
        return "\n".join(rows)

    def _pricing(self, a, lang):
        L = T.get(lang, T["zh"])
        if not a.pricing_analysis:
            return L["no_data"]
        rows = [
            f"| {L['competitor_col']} | {L['tier']} | {L['price']} |",
            "|------|------|------|",
        ]
        for p in a.pricing_analysis:
            rows.append(f"| {p.competitor} | {p.tier} | {p.price} |")
        return "\n".join(rows)

    def _sentiment(self, a, lang):
        L = T.get(lang, T["zh"])
        if not a.user_sentiment:
            return L["no_data"]
        parts = []
        for sp in a.user_sentiment:
            parts.append(f"### {sp.competitor}\n**{lang_title('Score', lang)}:** {sp.sentiment_score:.2f}")
            if sp.positive_themes:
                parts.append(f"**{L['positive']}:** " + "; ".join(sp.positive_themes))
            if sp.negative_themes:
                parts.append(f"**{L['negative']}:** " + "; ".join(sp.negative_themes))
            parts.append("")
        return "\n".join(parts)

    def _swot(self, a, lang):
        L = T.get(lang, T["zh"])
        parts = []
        for e in a.swot:
            parts.append(
                f"### {e.competitor}\n"
                f"| {L['strengths']} | {L['weaknesses']} |\n|------|------|"
            )
            mx = max(len(e.strengths), len(e.weaknesses))
            for i in range(mx):
                s = e.strengths[i] if i < len(e.strengths) else ""
                w = e.weaknesses[i] if i < len(e.weaknesses) else ""
                parts.append(f"| {s} | {w} |")
            parts.append(f"| {L['opportunities']} | {L['threats']} |")
            for i in range(max(len(e.opportunities), len(e.threats))):
                o = e.opportunities[i] if i < len(e.opportunities) else ""
                t = e.threats[i] if i < len(e.threats) else ""
                parts.append(f"| {o} | {t} |")
            parts.append("")
        return "\n".join(parts)

    def _conclusion(self, a, lang):
        L = T.get(lang, T["zh"])
        lang_name = "Chinese" if lang == "zh" else "English"
        # Guard: if there's no real analysis data, don't hallucinate
        has_data = bool(a.feature_matrix.matrix) or bool(a.swot) or bool(a.pricing_analysis)
        if not has_data:
            return L.get("msg_conclusion_fallback", "Analysis complete. See details in each section.")
        # Build context from analysis results
        ctx_parts = []
        if a.feature_matrix.matrix:
            ctx_parts.append(f"**Feature Matrix Scores:**")
            for row in a.feature_matrix.matrix[:8]:
                vals = ", ".join(f"{c}={v}" for c, v in row.values.items())
                ctx_parts.append(f"- {row.feature}: {vals}")
        if a.swot:
            for e in a.swot[:3]:
                ctx_parts.append(f"\n**{e.competitor} SWOT:** S: {'; '.join(e.strengths[:2])} | W: {'; '.join(e.weaknesses[:2])}")
        if a.pricing_analysis:
            ctx_parts.append("\n**Pricing:** " + "; ".join(f"{p.competitor}:{p.tier}/{p.price}" for p in a.pricing_analysis[:6]))
        data_ctx = "\n".join(ctx_parts)
        try:
            return self.invoke(
                f"Write a 2-paragraph {lang_name} conclusion with actionable recommendations "
                f"for competitive analysis of {a.competitors}."
                f"Base it ONLY on the data below, do not invent or speculate:\n\n{data_ctx[:3000]}"
            )
        except Exception:
            return L["msg_conclusion_fallback"]

    def _sources(self, sources):
        if not sources:
            return "_暂无来源_"
        return "\n".join(
            f"{i}. [{s.get('title', 'Untitled')}]({s.get('url', '')}) -- *{s.get('type', 'other')}*"
            for i, s in enumerate(sources, 1)
        )

    def _collect_sources(self, collected):
        seen, sources = set(), []
        for cd in collected.values():
            if isinstance(cd, dict):
                for s in cd.get("sources", []):
                    u = s.get("url", "")
                    if u and u not in seen:
                        seen.add(u)
                        sources.append(s)
        return sources


def lang_title(text, lang):
    """Quick bilingual helper for inline labels."""
    return text  # Keep it simple, use the label maps
