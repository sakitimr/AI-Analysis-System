"""Conditional routing based on QC verdict -- REAL feedback loop."""
import logging
from .state import WorkflowState
from config.settings import MAX_QC_ITERATIONS
logger = logging.getLogger(__name__)

def qc_router(state: WorkflowState) -> str:
    # Short-circuit: if upstream failed, don't retry
    if state.get("status") in ("no_data", "failed"):
        logger.info(f"[router] Upstream status={state.get('status')} -> END")
        return "end"
    qc = state.get("qc_result") or {}
    iteration = state.get("qc_iteration", 0)
    max_iter = state.get("max_iterations", MAX_QC_ITERATIONS)
    passed = qc.get("pass_", qc.get("pass", False))

    if passed:
        state["status"] = "completed"
        logger.info("[router] QC passed -> END")
        return "end"

    if iteration >= max_iter:
        state["status"] = "completed_degraded"
        logger.warning(f"[router] Max iterations ({max_iter}) -> END (degraded)")
        return "end"

    issues = qc.get("issues", [])
    if not issues:
        state["status"] = "completed"
        return "end"

    targets = {}
    for i in issues:
        t = i.get("target_agent", "writer")
        targets[t] = targets.get(t, 0) + 1

    hints = [i for i in issues if i.get("target_agent") == "collector"]
    if hints:
        state["collection_hints"] = hints
        logger.info(f"[router] {len(hints)} collector issues -> retry_collector")
        return "retry_collector"
    if "analyst" in targets:
        return "retry_analyst"
    return "retry_writer"
