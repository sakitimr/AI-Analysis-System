import pytest
from src.agents.writer import WriterAgent
from src.agents.analyst import AnalystAgent

class TestWriterAgent:
    def test_init(self):
        a = WriterAgent()
        assert a.name == "writer"
