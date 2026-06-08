"""Agent-to-agent structured message protocol."""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class MessageType(str, Enum):
    PASS = "pass"
    REJECT = "reject"
    CORRECTION = "correction"
    QUERY = "query"

class AgentMessage(BaseModel):
    """Structured message between agents."""
    message_id: str = ""
    agent_from: str = ""
    agent_to: str = ""
    message_type: MessageType = MessageType.PASS
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    payload: Any = None
    trace_id: str = ""
    iteration: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)

class QCVerdict(BaseModel):
    """Quality control verdict."""
    qc_id: str = ""
    verified_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    pass_: bool = Field(default=False, alias="pass")
    overall_score: float = Field(default=0.0, ge=0.0, le=1.0)
    checks: Dict[str, Any] = Field(default_factory=dict)
    issues: List[Dict[str, Any]] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    iteration: int = 1
    class Config:
        populate_by_name = True

class TraceEntry(BaseModel):
    """Single entry in execution trace."""
    agent_name: str = ""
    step: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    input_summary: str = ""
    output_summary: str = ""
    token_usage: Dict[str, int] = Field(default_factory=dict)
    duration_ms: int = 0
    status: str = "success"
    error_message: str = ""
