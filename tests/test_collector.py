import pytest
from unittest.mock import MagicMock, patch
from src.agents.collector import CollectorAgent

class TestCollectorAgent:
    def test_init(self):
        a = CollectorAgent()
        assert a.name == "collector"

    def test_gen_queries(self):
        a = CollectorAgent()
        qs = a._gen_queries("Cursor", "功能对比")
        assert len(qs) == 2
        assert "Cursor" in qs[0]

    def test_empty(self):
        a = CollectorAgent()
        r = a._empty("Test", ["功能对比"])
        assert r["competitor"] == "Test"
        assert r["status"] == "insufficient_data"
