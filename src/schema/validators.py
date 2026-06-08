"""Schema validators for competitive analysis data."""
import json, re
from typing import List, Tuple

def validate_collected_data(data: dict) -> Tuple[bool, List[str]]:
    errors = []
    if "competitor" not in data:
        errors.append("Missing: competitor")
    if "dimensions" not in data:
        errors.append("Missing: dimensions")
        return False, errors
    dims = data.get("dimensions", {})
    if not isinstance(dims, dict):
        errors.append(f"dimensions must be a dict, got {type(dims).__name__}")
        return False, errors
    total = 0
    for dim, points in dims.items():
        if not isinstance(points, list):
            errors.append(f"Dimension '{dim}' must be a list")
            continue
        for pt in points:
            if "source_url" not in pt:
                errors.append(f"Missing source_url in '{dim}'")
            if "value" not in pt:
                errors.append(f"Missing value in '{dim}'")
            total += 1
    if total == 0:
        errors.append("No data points collected")
    return len(errors) == 0, errors

def validate_analysis_result(data: dict) -> Tuple[bool, List[str]]:
    errors = []
    if "feature_matrix" not in data:
        errors.append("Missing feature_matrix")
    elif "matrix" not in data.get("feature_matrix", {}) or not data["feature_matrix"].get("matrix"):
        errors.append("Feature matrix is empty")
    if "swot" not in data:
        errors.append("Missing SWOT")
    else:
        for e in data["swot"]:
            for f in ["strengths", "weaknesses", "opportunities", "threats"]:
                if f not in e or len(e.get(f, [])) < 2:
                    errors.append(f"SWOT '{f}' insufficient")
    return len(errors) == 0, errors

def validate_report_content(content: str) -> Tuple[bool, List[str]]:
    errors = []
    sections = ["执行摘要", "竞品概览", "功能对比", "定价", "用户评价", "SWOT", "结论", "数据来源"]
    for s in sections:
        if s not in content:
            errors.append(f"Missing section: {s}")
    cites = re.findall(r'\[(\d+)\]\s*\((https?://[^\)]+)\)', content)
    if not cites:
        errors.append("No source citations found")
    return len(errors) == 0, errors

def safe_json_parse(raw: str) -> dict:
    cleaned = re.sub(r'^```(?:json)?\s*\n', '', raw.strip())
    cleaned = re.sub(r'\n```\s*$', '', cleaned)
    cleaned = re.sub(r',\s*}', '}', cleaned)
    cleaned = re.sub(r',\s*]', ']', cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    m = re.search(r'\{[\s\S]*\}', cleaned)
    if m:
        try:
            return json.loads(m.group())
        except json.JSONDecodeError:
            pass
    raise ValueError("Cannot parse JSON from LLM output")
