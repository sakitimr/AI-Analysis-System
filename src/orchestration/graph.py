"""LangGraph state graph -- multi-agent workflow."""
import logging
from langgraph.graph import StateGraph, END
from .state import WorkflowState
from .router import qc_router
from src.agents.collector import CollectorAgent
from src.agents.analyst import AnalystAgent
from src.agents.writer import WriterAgent
from src.agents.qc import QCAgent
from src.monitoring.status import get_status

logger = logging.getLogger(__name__)
_collector, _analyst, _writer, _qc = None, None, None, None

def _get():
    global _collector, _analyst, _writer, _qc
    if _collector is None:
        _collector = CollectorAgent()
        _analyst = AnalystAgent()
        _writer = WriterAgent()
        _qc = QCAgent()
    return _collector, _analyst, _writer, _qc

def _to_dict(obj):
    if hasattr(obj, 'model_dump'): return obj.model_dump()
    if hasattr(obj, 'dict'): return obj.dict()
    return obj

def collector_node(state: WorkflowState) -> WorkflowState:
    logger.info("[graph] === Collector ===")
    status = get_status()
    status.set_overall("running", "Collector: searching data...")
    status.agent_start("Collector", "collect")
    col, _, _, _ = _get()
    try:
        if state.get("collection_hints"):
            hints = state["collection_hints"]
            for h in hints:
                tgt = h.get("target_competitor", state["competitors"][0])
                dims = [h.get("section", d) for d in state.get("analysis_dimensions", [])]
                nd = col.recollect(tgt, dims, hints)
                cd = state.get("collected_data", {})
                if isinstance(cd, dict):
                    cd[tgt] = nd
                    state["collected_data"] = cd
        elif state.get("collected_data"):
            logger.info("[graph] Using pre-loaded data, skipping collector")
        else:
            state["collected_data"] = col.collect(state.get("competitors", []), state.get("analysis_dimensions", []))
        # Phase 2.1: validate collected data
        if isinstance(state.get("collected_data"), dict):
            from src.schema.validators import validate_collected_data
            for comp, data in state["collected_data"].items():
                if isinstance(data, dict):
                    ok, errors = validate_collected_data(data)
                    if not ok:
                        state.setdefault("validation_warnings", []).extend(
                            {"competitor": comp, "error": e} for e in errors
                        )
        state.setdefault("trace", []).append(col.get_trace(
            step="collect", input_summary=f"{len(state.get('competitors',[]))} competitors",
            output_summary=f"{len(state.get('collected_data',{})) if isinstance(state.get('collected_data'), dict) else 0} result sets"
        ))
        # 检查是否没有竞品或所有数据为空
        cd = state.get("collected_data", {})
        comps = state.get("competitors", [])
        if not comps:
            logger.warning("[graph] No competitors configured, stopping early")
            state["status"] = "no_data"
            state["report"] = "\u26a0\ufe0f \u672a\u914d\u7f6e\u4efb\u4f55\u7ade\u54c1\u3002\u8bf7\u5728\u4fa7\u8fb9\u680f\u6dfb\u52a0\u81f3\u5c11\u4e00\u4e2a\u7ade\u54c1\u540e\u91cd\u8bd5\u3002"
            state["qc_result"] = {"pass_": True, "overall_score": 1.0, "issues": [], "iteration": 0}
        elif isinstance(cd, dict):
            if len(cd) == 0:
                logger.warning("[graph] Collected data is empty, stopping early")
                state["status"] = "no_data"
                state["report"] = ("\u26a0\ufe0f \u65e0\u6cd5\u641c\u7d22\u5230\u7ade\u54c1\u4fe1\u606f\u3002\n\n"
                    "\u53ef\u80fd\u539f\u56e0\uff1a\u7f51\u7edc\u8fde\u63a5\u4e0d\u7a33\u5b9a\u6216\u76ee\u6807\u7f51\u7ad9\u4e0d\u53ef\u8fbe\u3002\n\n"
                    "\u5efa\u8bae\uff1a\n"
                    "1. \u68c0\u67e5\u7f51\u7edc\u8fde\u63a5\u540e\u91cd\u8bd5\n"
                    "2. \u6216\u52fe\u9009\u201cUse sample data\u201d\u4f7f\u7528\u9884\u7f6e\u6570\u636e\u6f14\u793a")
                state["qc_result"] = {"pass_": True, "overall_score": 1.0, "issues": [], "iteration": 0}
            else:
                all_empty = all(
                    isinstance(v, dict) and v.get("status") == "insufficient_data"
                    for v in cd.values()
                )
                if all_empty:
                    logger.warning("[graph] All competitors returned insufficient_data, stopping early")
                    state["status"] = "no_data"
                    state["report"] = ("\u26a0\ufe0f \u65e0\u6cd5\u641c\u7d22\u5230\u7ade\u54c1\u4fe1\u606f\u3002\n\n"
                        "\u53ef\u80fd\u539f\u56e0\uff1a\u7f51\u7edc\u8fde\u63a5\u4e0d\u7a33\u5b9a\u6216\u76ee\u6807\u7f51\u7ad9\u4e0d\u53ef\u8fbe\u3002\n\n"
                        "\u5efa\u8bae\uff1a\n"
                        "1. \u68c0\u67e5\u7f51\u7edc\u8fde\u63a5\u540e\u91cd\u8bd5\n"
                        "2. \u6216\u52fe\u9009\u201cUse sample data\u201d\u4f7f\u7528\u9884\u7f6e\u6570\u636e\u6f14\u793a")
                    state["qc_result"] = {"pass_": True, "overall_score": 1.0, "issues": [], "iteration": 0}
        status.agent_done("Collector", f"{len(state.get('collected_data',{})) if isinstance(state.get('collected_data'), dict) else 0} result sets")
    except Exception as e:
        logger.error(f"[graph] Collector failed: {e}")
        state["status"] = "failed"
        state["error_message"] = str(e)
        state["collected_data"] = {}
        status.agent_error("Collector", str(e)[:200])
    return state

def analyst_node(state: WorkflowState) -> WorkflowState:
    logger.info("[graph] === Analyst ===")
    status = get_status()
    _, ana, _, _ = _get()
    try:
        if state.get("status") in ("no_data", "failed"):
            logger.info(f"[graph] Analyst skipped (status={state.get('status')})")
            status.agent_skip("Analyst", f"upstream status={state.get('status')}")
            return state
        status.set_overall("running", "Analyst: analyzing competitors...")
        status.agent_start("Analyst", "analyze")
        raw_cd = state.get("collected_data", {})
        if not isinstance(raw_cd, dict):
            state["status"] = "failed"
            state["error_message"] = state.get("error_message", "Collector failed upstream")
            return state
        cd = {c: _to_dict(d) for c, d in raw_cd.items() if isinstance(d, dict)}
        result = ana.analyze(cd, dimensions=state.get("analysis_dimensions", []))
        state["analysis_result"] = _to_dict(result)
        # Phase 2.1: validate analysis result
        from src.schema.validators import validate_analysis_result
        ok, errors = validate_analysis_result(state["analysis_result"])
        if not ok:
            state.setdefault("validation_warnings", []).extend(
                {"source": "analyst", "error": e} for e in errors
            )
        state.setdefault("trace", []).append(ana.get_trace(
            step="analyze", input_summary=f"{len(cd)} competitors",
            output_summary=f"FM: {len(result.feature_matrix.matrix)} features, SWOT: {len(result.swot)} entries"
        ))
        status.agent_done("Analyst", f"{len(cd)} competitors analyzed")
    except Exception as e:
        logger.error(f"[graph] Analyst failed: {e}")
        state["status"] = "failed"
        state["error_message"] = str(e)
        status.agent_error("Analyst", str(e)[:200])
    return state

def writer_node(state: WorkflowState) -> WorkflowState:
    logger.info("[graph] === Writer ===")
    status = get_status()
    _, _, wri, _ = _get()
    try:
        if state.get("status") == "no_data" or not state.get("analysis_result"):
            if state.get("status") != "no_data":
                state["status"] = "failed"
            state["error_message"] = state.get("error_message", "Analyst failed upstream")
            status.agent_skip("Writer", f"upstream failed")
            return state
        # Reset status on retry so Writer has a chance to run
        if state.get("status") == "failed":
            logger.info("[graph] Resetting failed status for Writer retry")
            state["status"] = "running"
        status.set_overall("running", "Writer: generating report...")
        status.agent_start("Writer", "write")
        from src.schema.competitive import AnalysisResult
        ar = state.get("analysis_result", {})
        if not isinstance(ar, dict):
            state["status"] = "failed"
            state["error_message"] = f"analysis_result is not a dict: {type(ar).__name__}"
            return state
        analysis = AnalysisResult(**ar)
        cd = {c: _to_dict(d) for c, d in state.get("collected_data", {}).items()}
        report = wri.write_report(analysis, cd, dimensions=state.get("analysis_dimensions", []), language=state.get("language", "zh"))
        state["report"] = report.content
        state.setdefault("trace", []).append(wri.get_trace(
            step="write_report", input_summary=f"{len(analysis.competitors)} competitors",
            output_summary=f"{report.word_count} words, {report.source_count} sources"
        ))
        status.agent_done("Writer", f"{report.word_count} words, {report.source_count} sources")
    except Exception as e:
        logger.error(f"[graph] Writer failed: {e}")
        state["status"] = "failed"
        state["error_message"] = str(e)
        status.agent_error("Writer", str(e)[:200])
        state.setdefault("trace", []).append(wri.get_trace(
            step="write_report", input_summary="generating report",
            output_summary=f"FAILED: {str(e)[:80]}"
        ))
    return state

def qc_node(state: WorkflowState) -> WorkflowState:
    logger.info("[graph] === QC ===")
    status = get_status()
    _, _, _, qc = _get()
    try:
        if state.get("status") in ("no_data", "failed"):
            logger.info(f"[graph] QC skipped (status={state.get('status')})")
            status.agent_skip("QC", state.get('status', '?'))
            return state
        status.set_overall("running", "QC: verifying report quality...")
        status.agent_start("QC", "verify")
        iteration = state.get("qc_iteration", 0) + 1
        state["qc_iteration"] = iteration
        raw_cd = state.get("collected_data", {})
        cd = {c: _to_dict(d) for c, d in raw_cd.items() if isinstance(d, dict)} if isinstance(raw_cd, dict) else {}
        verdict = qc.verify(state.get("report", ""), state.get("analysis_result", {}), cd, iteration, dimensions=state.get("analysis_dimensions", []))
        state["qc_result"] = _to_dict(verdict)
        passed = verdict.pass_ if hasattr(verdict, 'pass_') else verdict.pass_
        state.setdefault("trace", []).append(qc.get_trace(
            step=f"verify_iter{iteration}", input_summary=f"{len(state.get('report',''))} chars report",
            output_summary=f"{'PASS' if passed else 'FAIL'} score={verdict.overall_score:.0%}"
        ))
        status.agent_done("QC", f"{'PASS' if passed else 'FAIL'} score={verdict.overall_score:.0%}")
    except Exception as e:
        logger.error(f"[graph] QC failed: {e}")
        state["status"] = "failed"
        state["error_message"] = str(e)
        # Set pass_=True on QC crash to prevent retry loop
        state["qc_result"] = {"pass_": True, "overall_score": 0, "issues": [], "iteration": iteration}
        status.agent_error("QC", str(e)[:200])
    return state

def build_graph():
    wf = StateGraph(WorkflowState)
    wf.add_node("collector", collector_node)
    wf.add_node("analyst", analyst_node)
    wf.add_node("writer", writer_node)
    wf.add_node("qc", qc_node)
    wf.set_entry_point("collector")
    wf.add_edge("collector", "analyst")
    wf.add_edge("analyst", "writer")
    wf.add_edge("writer", "qc")
    wf.add_conditional_edges("qc", qc_router, {"end": END, "retry_collector": "collector", "retry_analyst": "analyst", "retry_writer": "writer"})
    return wf.compile()
