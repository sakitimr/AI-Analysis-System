"""Data models for SQLite storage."""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime

@dataclass
class TaskRecord:
    id: Optional[int] = None
    competitors: List[str] = field(default_factory=list)
    dimensions: List[str] = field(default_factory=list)
    status: str = "pending"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    report_path: str = ""

@dataclass
class RunRecord:
    id: Optional[int] = None
    task_id: int = 0
    status: str = "running"
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: str = ""
    duration_seconds: float = 0.0
    total_tokens: int = 0
    qc_iterations: int = 0
    qc_passed: bool = False
    trace: List[Dict[str, Any]] = field(default_factory=list)
    error_message: str = ""
