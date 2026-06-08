"""API routes."""
import logging, time
from typing import List
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from src.orchestration.state import create_initial_state
from src.orchestration.graph import build_graph
from src.storage.database import Database
from src.tools.sample_data import get_sample_data

logger = logging.getLogger(__name__)
router = APIRouter()
db = Database()
_graph = None

def _g():
    global _graph
    if _graph is None: _graph = build_graph()
    return _graph

class AnalysisRequest(BaseModel):
    competitors: List[str] = Field(default=["Cursor", "GitHub Copilot", "TRAE"])
    dimensions: List[str] = Field(default=["功能对比", "定价模型", "用户评价", "SWOT分析"])
    use_sample_data: bool = Field(default=True)
    max_iterations: int = Field(default=3, ge=1, le=5)

@router.post("/analyze")
async def start_analysis(req: AnalysisRequest, bg: BackgroundTasks):
    try:
        tid = db.create_task(req.competitors, req.dimensions)
        bg.add_task(_run_analysis, tid, req)
        return {"task_id": tid, "status": "running", "message": f"Analysis started for {len(req.competitors)} competitors"}
    except Exception as e:
        raise HTTPException(500, str(e))

def _run_analysis(tid, req):
    from datetime import datetime
    rid = db.create_run(tid)
    try:
        state = create_initial_state(req.competitors, req.dimensions, req.max_iterations)
        if req.use_sample_data:
            sample = get_sample_data()
            state["collected_data"] = {c: sample[c] for c in req.competitors if c in sample}
        result = _g().invoke(state)
        qc = result.get("qc_result", {})
        db.update_run(rid, status="completed", iterations=qc.get("iteration", 0), passed=qc.get("pass", qc.get("pass_", False)), trace=result.get("trace", []))
        logger.info(f"[api] Task {tid} completed")
    except Exception as e:
        logger.error(f"[api] Task {tid} failed: {e}")
        db.update_run(rid, status="failed", error=str(e))

@router.get("/tasks")
async def list_tasks():
    return db.list_tasks()

@router.get("/tasks/{task_id}")
async def get_task(task_id: int):
    t = db.get_task(task_id)
    if not t: raise HTTPException(404, "Task not found")
    t["runs"] = db.get_runs(task_id)
    return t

@router.post("/analyze/sync")
async def analyze_sync(req: AnalysisRequest):
    start = time.time()
    state = create_initial_state(req.competitors, req.dimensions, req.max_iterations)
    if req.use_sample_data:
        sample = get_sample_data()
        state["collected_data"] = {c: sample[c] for c in req.competitors if c in sample}
    result = _g().invoke(state)
    return {"status": result.get("status"), "report": result.get("report", ""), "qc_result": result.get("qc_result", {}), "elapsed_seconds": round(time.time() - start, 1), "iterations": result.get("qc_iteration", 0), "trace": result.get("trace", [])}
