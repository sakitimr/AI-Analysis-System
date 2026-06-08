import pytest
from src.agents.analyst import AnalystAgent

class TestAnalystAgent:
    def test_init(self):
        a = AnalystAgent()
        assert a.name == "analyst"

    def test_extract_features(self, sample_data):
        a = AnalystAgent()
        feats = a._extract_features(["Cursor", "GitHub Copilot", "TRAE"], sample_data)
        assert len(feats) > 0
