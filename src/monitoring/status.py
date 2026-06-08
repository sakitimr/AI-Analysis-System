"""Thread-safe shared status store for real-time agent pipeline monitoring."""
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional, Any


class AgentStatus:
    """Per-agent status tracking with LLM call log."""

    def __init__(self, name: str):
        self.name = name
        self.status = "idle"  # idle | running | done | error | skipped
        self.current_step = ""
        self.started_at: Optional[str] = None
        self.ended_at: Optional[str] = None
        self.summary = ""
        self.error = ""
        self.calls: List[dict] = []
        self.total_tokens_input = 0
        self.total_tokens_output = 0
        self.total_duration_ms = 0

    def add_call(self, info: dict):
        self.calls.append(info)
        self.total_tokens_input += info.get("token_input", 0)
        self.total_tokens_output += info.get("token_output", 0)
        self.total_duration_ms += info.get("duration_ms", 0)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "status": self.status,
            "current_step": self.current_step,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "summary": self.summary,
            "error": self.error,
            "call_count": len(self.calls),
            "calls": self.calls[-20:],  # last 20 calls to avoid bloat
            "total_tokens_input": self.total_tokens_input,
            "total_tokens_output": self.total_tokens_output,
            "total_duration_ms": self.total_duration_ms,
        }


class PipelineStatus:
    """Thread-safe pipeline status store.

    Singleton per-run: reset before each pipeline invocation.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self.agents: Dict[str, AgentStatus] = {}
        self.overall_status = "idle"  # idle | running | done | error
        self.current_step = ""
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.result = None
        self.errors: List[str] = []

    # ── overall pipeline ──

    def set_overall(self, status: str, step: str = ""):
        with self._lock:
            self.overall_status = status
            if step:
                self.current_step = step
            if status == "running" and self.start_time is None:
                self.start_time = time.time()
            if status in ("done", "error"):
                self.end_time = time.time()

    # ── per-agent status ──

    def _ensure_agent(self, name: str) -> AgentStatus:
        if name not in self.agents:
            self.agents[name] = AgentStatus(name)
        return self.agents[name]

    def agent_start(self, name: str, step: str = ""):
        with self._lock:
            a = self._ensure_agent(name)
            a.status = "running"
            a.current_step = step
            a.started_at = datetime.now().isoformat()
            a.error = ""

    def agent_done(self, name: str, summary: str = ""):
        with self._lock:
            a = self._ensure_agent(name)
            a.status = "done"
            a.summary = summary
            a.ended_at = datetime.now().isoformat()
            a.current_step = ""

    def agent_error(self, name: str, error: str = ""):
        with self._lock:
            a = self._ensure_agent(name)
            a.status = "error"
            a.error = error
            a.ended_at = datetime.now().isoformat()
        self.errors.append(f"[{name}] {error}")

    def agent_skip(self, name: str, reason: str = ""):
        with self._lock:
            a = self._ensure_agent(name)
            a.status = "skipped"
            a.summary = reason

    def add_llm_call(self, agent_name: str, call_info: dict):
        with self._lock:
            a = self._ensure_agent(agent_name)
            a.add_call(call_info)

    # ── snapshot ──

    def snapshot(self) -> dict:
        with self._lock:
            elapsed = time.time() - self.start_time if self.start_time else 0
            return {
                "overall_status": self.overall_status,
                "current_step": self.current_step,
                "elapsed_sec": round(elapsed, 2),
                "agents": [a.to_dict() for a in self.agents.values()],
                "errors": self.errors[-10:],
            }


# ── module-level singleton ──

_pipeline_status: Optional[PipelineStatus] = None


def get_status() -> PipelineStatus:
    global _pipeline_status
    if _pipeline_status is None:
        _pipeline_status = PipelineStatus()
    return _pipeline_status


def reset_status():
    global _pipeline_status
    _pipeline_status = PipelineStatus()
