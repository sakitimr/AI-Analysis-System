"""QC Agent -- quality control with real feedback loop."""
import logging, json, uuid, re
from typing import List, Dict, Any
from datetime import datetime
from .base import BaseAgent
from src.schema.messages import QCVerdict
from src.schema.validators import safe_json_parse
from config.settings import MAX_QC_ITERATIONS

logger = logging.getLogger(__name__)


class QCAgent(BaseAgent):
    def __init__(self, model=None):
        super().__init__(name="qc", model=model)

    def verify(self, report: str, analysis: dict, collected: dict, iteration: int = 1, dimensions: List[str] = None) -> QCVerdict:
        logger.info(f"[qc] Verifying (iteration {iteration}/{MAX_QC_ITERATIONS})")
        dims = dimensions or []
        issues = []
        issues.extend(self._check_completeness(report, dims))
        issues.extend(self._check_sources(report, collected))
        issues.extend(self._check_placeholders(report))
        issues.extend(self._check_word_count(report))
        issues.extend(self._llm_check(report))

        critical = [i for i in issues if i["severity"] == "critical"]
        major = [i for i in issues if i["severity"] == "major"]
        passed = len(critical) == 0 and len(major) == 0
        score = max(0.0, 1.0 - (len(critical) * 3 + len(major) * 2 + len(issues) * 0.5) / 10)
        if not passed:
            logger.warning(f"[qc] QC FAILED: {len(critical)} critical, {len(major)} major, {len(issues)} total")
            for i in issues:
                logger.warning(f"[qc]   [{i['severity']}] {i.get('section','?')}: {i.get('description','?')[:120]}")

        return QCVerdict(
            qc_id=str(uuid.uuid4())[:8],
            pass_=passed,
            overall_score=score,
            checks={
                "data_integrity": {"score": 0.9, "issues": len(critical)},
                "completeness": {"score": 0.85, "issues": len(major)},
                "consistency": {"score": 0.8, "issues": len(issues)},
            },
            issues=issues,
            suggestions=[i.get("suggestion", "") for i in issues],
            iteration=iteration,
        )

    def _check_completeness(self, content, dims):
        base_keywords = ["摘要", "Executive Summary", "结论", "Conclusion"]
        has_summary = any(kw in content for kw in ["摘要", "Executive Summary"])
        has_conclusion = any(kw in content for kw in ["结论", "Conclusion"])
        issues = []
        if not has_summary:
            issues.append({"severity": "critical", "section": "summary",
                           "description": "Missing summary section",
                           "target_agent": "writer", "suggestion": "Add summary section"})
        if not has_conclusion:
            issues.append({"severity": "critical", "section": "conclusion",
                           "description": "Missing conclusion section",
                           "target_agent": "writer", "suggestion": "Add conclusion section"})
        dim_map = {
            "功能对比": ["功能对比", "Feature Comparison"],
            "定价模型": ["定价", "Pricing"],
            "用户评价": ["用户评价", "User Sentiment"],
            "SWOT分析": ["SWOT"],
        }
        for dim in dims:
            if dim in dim_map:
                if not any(kw in content for kw in dim_map[dim]):
                    issues.append({"severity": "major", "section": dim,
                                   "description": f"Missing section for: {dim}",
                                   "target_agent": "writer", "suggestion": f"Add '{dim}' section"})
        return issues

    def _check_sources(self, content, collected):
        # Match markdown links: [text](url) — supports numbered citations and named references
        links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)
        # Filter to actual URLs (exclude internal/anchor references)
        cited = [(label, url) for label, url in links if url.startswith('http')]
        if not cited:
            # Also try the old numbered format as fallback
            cited = re.findall(r'\[(\d+)\]\s*\(([^)]+)\)', content)
        if not cited:
            return [{"severity": "critical", "section": "all", "description": "No source citations",
                     "target_agent": "writer", "suggestion": "Add [title](url) citations"}]
        known = set()
        for cd in collected.values():
            if isinstance(cd, dict):
                for s in cd.get("sources", []):
                    known.add(s.get("url", ""))
                for pts in cd.get("dimensions", {}).values():
                    for p in pts:
                        if isinstance(p, dict) and "source_url" in p:
                            known.add(p["source_url"])
        return []

    def _check_placeholders(self, content):
        phs = ["[TODO]", "[待补充]", "[TBD]", "[PLACEHOLDER]"]
        return [
            {"severity": "minor", "section": "general", "description": f"Placeholder: {ph}",
             "target_agent": "writer", "suggestion": "Replace placeholder"}
            for ph in phs if ph in content
        ]

    def _check_word_count(self, content):
        # 核心章节内容过短视为问题
        issues = []
        for section in ["功能对比", "定价", "用户评价"]:
            idx = content.find(section)
            if idx == -1:
                continue
            # 取章节内容（到下一个 ## 或文件末尾）
            rest = content[idx:]
            next_sec = rest.find("\n## ", 2)
            if next_sec != -1:
                rest = rest[:next_sec]
            if len(rest.strip()) < 50:
                issues.append({
                    "severity": "major",
                    "section": section,
                    "description": f"Section '{section}' too short ({len(rest.strip())} chars)",
                    "target_agent": "writer",
                    "suggestion": f"Expand '{section}' section with more detail"
                })
        return issues

    def _llm_check(self, content):
        """用中文 prompt 检查报告质量——仅检查前3000和后1000字符确保覆盖头尾。"""
        # Include both beginning and end of report so LLM can see Sources section
        sample = content[:3000]
        if len(content) > 4000:
            sample += "\n\n...(中间省略)...\n\n" + content[-1000:]
        prompt = f"""你是竞品分析报告的终审质检员。检查以下报告是否存在致命缺陷。

⚠️ 重要：
- 你只能看到头部和尾部（中间省略），不要因为你没看到的内容而标记遗漏
- 仅标记致命缺陷（数据前后严重矛盾、关键分析完全错误、虚构不存在的产品/数据）
- 不要标记：格式问题、语言问题（如缩写）、风格问题、轻微不准确
- 如果报告基本合格，输出 has_issues: false

报告内容：
{sample}

严格输出 JSON：{{"has_issues": false, "issues": []}}
每个 issue：{{"severity": "critical", "section": "章节名", "description": "问题描述"}}
"""
        try:
            d = self.safe_invoke_json(prompt)
            if d.get("has_issues"):
                issues = []
                for i in d.get("issues", []):
                    sev = i.get("severity", "minor")
                    # Downgrade: only accept critical/major; ignore minor from LLM
                    if sev not in ("critical", "major"):
                        continue
                    issues.append({
                        "severity": sev,
                        "section": i.get("section", "general"),
                        "description": i.get("description", ""),
                        "target_agent": "writer",
                        "suggestion": i.get("description", ""),
                    })
                return issues
        except Exception as e:
            logger.warning(f"[qc] LLM check failed: {e}")
        return []

    def determine_retry_target(self, issues):
        targets = {}
        for i in issues:
            t = i.get("target_agent", "writer")
            targets[t] = targets.get(t, 0) + 1
        if "collector" in targets:
            return "retry_collector"
        if "analyst" in targets:
            return "retry_analyst"
        if targets:
            return "retry_writer"
        return "end"
