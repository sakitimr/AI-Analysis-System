"""LangGraph workflow state definition."""
from typing import TypedDict, List, Optional, Dict, Any

class WorkflowState(TypedDict, total=False):
    competitors: List[str]
    analysis_dimensions: List[str]
    language: str
    collected_data: Optional[Dict[str, Any]]
    analysis_result: Optional[Dict[str, Any]]
    report: Optional[str]
    qc_result: Optional[Dict[str, Any]]
    qc_iteration: int
    max_iterations: int
    collection_hints: Optional[List[dict]]
    trace: List[dict]
    validation_warnings: List[dict]
    status: str
    error_message: str

def create_initial_state(competitors: List[str], dimensions: List[str], max_iterations: int = 3, language: str = "zh") -> WorkflowState:
    return WorkflowState(competitors=competitors, analysis_dimensions=dimensions, language=language, collected_data=None, analysis_result=None, report=None, qc_result=None, qc_iteration=0, max_iterations=max_iterations, collection_hints=None, trace=[], validation_warnings=[], status="running", error_message="")
