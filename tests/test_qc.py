import pytest
from src.agents.qc import QCAgent

class TestQCAgent:
    def test_init(self):
        a = QCAgent()
        assert a.name == "qc"

    def test_check_completeness_pass(self):
        a = QCAgent()
        dims = ["功能对比", "定价模型", "用户评价"]
        content = "# Report\n## 执行摘要\nSummary\n## 竞品概览\nX\n## 功能对比\nY\n## 定价\nZ\n## 用户评价\nR\n## SWOT\nS\n## 结论\nC\n## 数据来源\nSrc"
        issues = a._check_completeness(content, dims)
        assert len(issues) == 0

    def test_check_completeness_fail(self):
        a = QCAgent()
        dims = ["功能对比", "定价模型", "用户评价", "SWOT分析"]
        issues = a._check_completeness("# Title only", dims)
        # Missing: summary + conclusion + 4 dimension sections = 6 issues
        assert len(issues) == 6

    def test_determine_retry(self):
        a = QCAgent()
        assert a.determine_retry_target([{"target_agent": "collector"}]) == "retry_collector"
        assert a.determine_retry_target([{"target_agent": "analyst"}]) == "retry_analyst"
        assert a.determine_retry_target([{"target_agent": "writer"}]) == "retry_writer"
        assert a.determine_retry_target([]) == "end"
