import pytest
from src.orchestration.state import create_initial_state
from src.orchestration.router import qc_router
from src.orchestration.graph import build_graph

class TestState:
    def test_create(self):
        s = create_initial_state(["Cursor"], ["功能对比"])
        assert s["competitors"] == ["Cursor"]
        assert s["status"] == "running"
        assert s["qc_iteration"] == 0

class TestRouter:
    def test_pass(self):
        s = create_initial_state(["Cursor"], ["功能对比"])
        s["qc_result"] = {"pass": True}
        assert qc_router(s) == "end"

    def test_reject_collector(self):
        s = create_initial_state(["Cursor"], ["功能对比"])
        s["qc_result"] = {"pass": False, "issues": [{"target_agent": "collector"}]}
        assert qc_router(s) == "retry_collector"

    def test_max_iterations(self):
        s = create_initial_state(["Cursor"], ["功能对比"], max_iterations=3)
        s["qc_iteration"] = 3
        s["qc_result"] = {"pass": False, "issues": [{"target_agent": "collector"}]}
        assert qc_router(s) == "end"

class TestGraph:
    def test_build(self):
        g = build_graph()
        assert g is not None
