"""Streamlit UI for AI Analysis System — simplified, no real-time monitoring."""
import sys
import os
import json
import logging
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
import time
import threading
from datetime import datetime
from src.orchestration.state import create_initial_state
from src.orchestration.graph import build_graph
from src.tools.sample_data import get_sample_data
from src.monitoring.status import get_status, reset_status

st.set_page_config(page_title="AI Analysis System", page_icon="🔭", layout="wide")

# ── Thread-safe result bridge via filesystem ──
# Module-level globals are RESET to None on every st.rerun() because Streamlit
# re-executes the entire script. This creates a race condition where the
# background thread's result is wiped before the main thread can read it.
# Fix: use a temp file on disk (survives reruns) as the signal channel.
_PIPELINE_RESULT_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "_pipeline_result.json")

# ── Theme toggle ──
if "theme" not in st.session_state:
    st.session_state.theme = "light"
theme_icon = "🌙" if st.session_state.theme == "light" else "☀️"
if st.sidebar.button(theme_icon, key="theme_toggle", help="Toggle dark/light mode"):
    st.session_state.theme = "dark" if st.session_state.theme == "light" else "light"
    st.rerun()
if st.session_state.theme == "dark":
    st.markdown("""
        <style>
        /* ── BaseWeb Input overrides (slider value box ▸ kills blue border) ── */
        div[data-baseweb="input"] {
            background: rgba(30,41,59,0.85) !important;
            border-color: rgba(56,189,248,0.12) !important;
            border-radius: 6px !important;
            box-shadow: none !important;
        }
        div[data-baseweb="input"]:focus-within {
            border-color: rgba(56,189,248,0.25) !important;
            box-shadow: none !important;
        }
        div[data-baseweb="input"] input {
            background: transparent !important;
            color: #cbd5e1 !important;
            caret-color: #38bdf8 !important;
            outline: none !important;
            box-shadow: none !important;
        }
        /* ── Root & Body ── */
        .stApp {
            background: linear-gradient(160deg, #080d16 0%, #0f172a 40%, #0a1628 100%);
            color: #cbd5e1;
        }
        [data-testid="stAppViewContainer"] {
            background: linear-gradient(160deg, #080d16 0%, #0f172a 40%, #0a1628 100%) !important;
        }
        [data-testid="stAppViewContainer"] > section > div {
            background: transparent !important;
        }
        section.main > div {
            background: transparent !important;
        }
        .main .block-container {
            padding-top: 1.5rem;
            background: transparent !important;
        }
        [data-testid="stVerticalBlock"] {
            background: transparent !important;
        }
        .stMarkdown, .stMarkdown p {
            color: #cbd5e1;
        }
        .st-emotion-cache-0 {
            background: transparent !important;
        }

        /* ── Sidebar ── */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0c1322 0%, #111b2e 100%);
            border-right: 1px solid rgba(56,189,248,0.12);
        }
        [data-testid="stSidebar"] .stMarkdown,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] .stCaption {
            color: #cbd5e1 !important;
        }
        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
            color: #e2e8f0 !important;
        }
        [data-testid="stSidebar"] hr {
            border-color: rgba(56,189,248,0.15);
        }
        [data-testid="stSidebar"] .stRadio label {
            color: #cbd5e1 !important;
        }

        /* ── Typography ── */
        h1, h2, h3, h4 {
            color: #e2e8f0 !important;
            font-weight: 600 !important;
        }
        h1 { border-bottom: 1px solid rgba(56,189,248,0.2); padding-bottom: 0.4rem; }
        p, li, span, label { color: #cbd5e1; }
        code {
            background: rgba(56,189,248,0.1);
            color: #7dd3fc;
            border: 1px solid rgba(56,189,248,0.15);
            border-radius: 4px;
            padding: 2px 6px;
        }

        /* ── Buttons ── */
        .stButton > button {
            border-radius: 8px !important;
            font-weight: 500 !important;
            transition: all 0.2s ease !important;
        }
        .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #0ea5e9, #3b82f6) !important;
            color: #fff !important;
            border: none !important;
            box-shadow: 0 2px 12px rgba(14,165,233,0.25);
        }
        .stButton > button[kind="primary"]:hover {
            box-shadow: 0 4px 20px rgba(14,165,233,0.4);
            transform: translateY(-1px);
        }
        .stButton > button[kind="secondary"] {
            background: rgba(30,41,59,0.8) !important;
            color: #cbd5e1 !important;
            border: 1px solid rgba(56,189,248,0.2) !important;
        }
        .stButton > button[kind="secondary"]:hover {
            border-color: rgba(56,189,248,0.5) !important;
            background: rgba(30,41,59,1) !important;
        }

        /* ── Text Inputs ── */
        [data-testid="stTextInput"] input, .stTextInput input {
            background: #1e293b !important;
            color: #e2e8f0 !important;
            border: 1px solid rgba(56,189,248,0.15) !important;
            border-radius: 8px !important;
        }
        [data-testid="stTextInput"] input:focus {
            border-color: rgba(56,189,248,0.5) !important;
            box-shadow: 0 0 0 2px rgba(56,189,248,0.15) !important;
        }
        [data-testid="stTextInput"] input::placeholder {
            color: #64748b !important;
        }

        /* ── Select / Multiselect ── */
        [data-baseweb="select"] > div {
            background: #1e293b !important;
            border-color: rgba(56,189,248,0.15) !important;
        }
        [data-baseweb="popover"] {
            background: #1e293b !important;
        }
        [data-baseweb="popover"] li {
            color: #cbd5e1 !important;
        }
        [data-baseweb="popover"] li:hover {
            background: rgba(56,189,248,0.1) !important;
        }

        /* ── Expander ── */
        [data-testid="stExpander"] {
            background: rgba(30,41,59,0.5) !important;
            border: 1px solid rgba(56,189,248,0.12) !important;
            border-radius: 10px !important;
        }
        [data-testid="stExpander"] summary {
            color: #94a3b8 !important;
        }

        /* ── Info / Warning / Success boxes ── */
        .stAlert {
            border-radius: 10px !important;
        }
        [data-testid="stInfo"] {
            background: rgba(14,165,233,0.08) !important;
            border: 1px solid rgba(14,165,233,0.2) !important;
            color: #bae6fd !important;
        }
        [data-testid="stWarning"] {
            background: rgba(245,158,11,0.08) !important;
            border: 1px solid rgba(245,158,11,0.2) !important;
            color: #fde68a !important;
        }
        [data-testid="stError"] {
            background: rgba(239,68,68,0.08) !important;
            border: 1px solid rgba(239,68,68,0.25) !important;
            color: #fecaca !important;
        }
        [data-testid="stSuccess"] {
            background: rgba(16,185,129,0.08) !important;
            border: 1px solid rgba(16,185,129,0.2) !important;
            color: #a7f3d0 !important;
        }

        /* ── Slider ── */
        [data-testid="stSlider"] [data-baseweb="slider"] div[role="slider"] {
            background: #0ea5e9 !important;
        }
        [data-testid="stSlider"] [data-baseweb="slider"] > div > div:first-child {
            background: #0ea5e9 !important;
        }
        /* Slider value tooltip / number display box */
        [data-testid="stSlider"] [data-baseweb="slider"] input {
            background: rgba(30,41,59,0.9) !important;
            color: #cbd5e1 !important;
            border: 1px solid rgba(56,189,248,0.1) !important;
            outline: none !important;
            box-shadow: none !important;
            border-radius: 6px !important;
            caret-color: transparent !important;
        }
        [data-testid="stSlider"] [data-baseweb="slider"] input:focus {
            border-color: rgba(56,189,248,0.2) !important;
            outline: none !important;
            box-shadow: none !important;
        }
        [data-testid="stSlider"] div[data-baseweb="input"] {
            border-color: rgba(56,189,248,0.1) !important;
            box-shadow: none !important;
        }
        [data-testid="stSlider"] div[data-baseweb="input"]:focus-within {
            border-color: rgba(56,189,248,0.2) !important;
            box-shadow: none !important;
        }
        [data-testid="stThumbValue"] {
            background: rgba(30,41,59,0.95) !important;
            color: #cbd5e1 !important;
            border: 1px solid rgba(56,189,248,0.1) !important;
            border-radius: 6px !important;
            box-shadow: none !important;
        }
        [data-testid="stThumbValue"]::after {
            border-top-color: rgba(30,41,59,0.95) !important;
        }
        /* Any input/button-like element inside slider */
        [data-testid="stSlider"] * {
            outline: none !important;
        }
        [data-testid="stSlider"] [class*="thumb"],
        [data-testid="stSlider"] [class*="Thumb"] {
            box-shadow: none !important;
        }

        /* ── Checkbox ── */
        [data-testid="stCheckbox"] label span {
            color: #cbd5e1 !important;
        }

        /* ── Caption / Help text ── */
        .stCaption, small { color: #64748b !important; }

        /* ── Divider ── */
        hr {
            border-color: rgba(56,189,248,0.12) !important;
        }

        /* ── Tables (markdown & dataframe) ── */
        .stMarkdown table {
            background: rgba(30,41,59,0.6);
            border-radius: 10px;
            overflow: hidden;
            border: 1px solid rgba(56,189,248,0.12);
        }
        .stMarkdown table th {
            background: rgba(14,165,233,0.15) !important;
            color: #7dd3fc !important;
            font-weight: 600 !important;
            border-bottom: 1px solid rgba(56,189,248,0.2) !important;
        }
        .stMarkdown table td {
            color: #cbd5e1 !important;
            border-bottom: 1px solid rgba(56,189,248,0.06) !important;
        }
        .stMarkdown table tr:hover td {
            background: rgba(56,189,248,0.04);
        }

        /* ── Download button ── */
        [data-testid="stDownloadButton"] button {
            background: rgba(16,185,129,0.15) !important;
            color: #6ee7b7 !important;
            border: 1px solid rgba(16,185,129,0.3) !important;
            border-radius: 8px !important;
        }
        [data-testid="stDownloadButton"] button:hover {
            background: rgba(16,185,129,0.25) !important;
            box-shadow: 0 2px 12px rgba(16,185,129,0.2);
        }

        /* ── Markdown links ── */
        .stMarkdown a { color: #38bdf8 !important; }
        .stMarkdown a:hover { color: #7dd3fc !important; }

        /* ── Scrollbar ── */
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: #0f172a; }
        ::-webkit-scrollbar-thumb {
            background: rgba(56,189,248,0.2);
            border-radius: 3px;
        }
        ::-webkit-scrollbar-thumb:hover { background: rgba(56,189,248,0.35); }

        /* ── Tooltip ── */
        [data-baseweb="tooltip"] {
            background: #1e293b !important;
            border: 1px solid rgba(56,189,248,0.2) !important;
            border-radius: 8px !important;
            color: #cbd5e1 !important;
        }

        /* ── Spinner ── */
        .stSpinner > div { border-top-color: #38bdf8 !important; }

        /* ── Blockquote ── */
        .stMarkdown blockquote {
            border-left: 3px solid rgba(56,189,248,0.4);
            background: rgba(56,189,248,0.05);
            padding: 8px 16px;
            border-radius: 0 8px 8px 0;
        }

        /* ── Animated grid background (subtle) ── */
        .stApp::before {
            content: "";
            position: fixed;
            top: 0; left: 0; width: 100%; height: 100%;
            background-image:
                linear-gradient(rgba(56,189,248,0.03) 1px, transparent 1px),
                linear-gradient(90deg, rgba(56,189,248,0.03) 1px, transparent 1px);
            background-size: 48px 48px;
            pointer-events: none;
            z-index: 0;
            mask-image: radial-gradient(ellipse 70% 60% at 50% 30%, black 30%, transparent 70%);
            -webkit-mask-image: radial-gradient(ellipse 70% 60% at 50% 30%, black 30%, transparent 70%);
        }
        .main .block-container { position: relative; z-index: 1; }

        /* ── Streamlit header / toolbar ── */
        [data-testid="stHeader"] {
            background: transparent !important;
        }
        header[data-testid="stHeader"] {
            background: rgba(8,13,22,0.92) !important;
            backdrop-filter: blur(8px);
            border-bottom: 1px solid rgba(56,189,248,0.08);
        }
        [data-testid="stToolbar"] {
            background: transparent !important;
        }
        [data-testid="stDecoration"] {
            background: transparent !important;
        }

        /* ── Title accent ── */
        .stApp h1 {
            background: linear-gradient(135deg, #38bdf8 0%, #818cf8 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            border-bottom: 1px solid rgba(56,189,248,0.18) !important;
        }
        </style>
    """, unsafe_allow_html=True)

st.title("🔬 AI Analysis System")

# ── Sidebar ──
with st.sidebar:
    st.header("⚙️ Configuration")

    st.subheader("🌐 Language")
    language = st.radio("Report language", ["中文", "English"], index=0, horizontal=True, key="lang_radio",
                        help="Output report language")
    lang_code = "zh" if language == "中文" else "en"

    st.divider()

    st.subheader("🎯 Competitors")
    if "custom_competitors" not in st.session_state:
        st.session_state.custom_competitors = []
    col_c1, col_c2 = st.columns([3, 1])
    with col_c1:
        new_comp = st.text_input("Add competitor", placeholder="e.g. Cursor, 文心快码",
                                 key="new_comp_input", label_visibility="collapsed",
                                 disabled=st.session_state.get("_running", False))
    with col_c2:
        if st.button("➕", key="add_comp", help="Add competitor", use_container_width=True,
                     disabled=st.session_state.get("_running", False)):
            val = new_comp.strip()
            if val and val not in st.session_state.custom_competitors:
                st.session_state.custom_competitors.append(val)
            st.rerun()
    for i, c in enumerate(st.session_state.custom_competitors):
        col_n, col_x = st.columns([5, 1])
        with col_n:
            st.caption(f"🔹 {c}")
        with col_x:
            if st.button("✕", key=f"rm_comp_{i}", help=f"Remove {c}",
                         disabled=st.session_state.get("_running", False)):
                st.session_state.custom_competitors.pop(i)
                st.rerun()
    competitors = list(st.session_state.custom_competitors)
    if not competitors:
        st.warning("Add at least one competitor")

    st.divider()

    st.subheader("📐 Dimensions")
    PRESET_DIMENSIONS = ["功能对比", "定价模型", "用户评价", "SWOT分析", "市场定位", "技术架构"]
    if "custom_dimensions" not in st.session_state:
        st.session_state.custom_dimensions = []
    selected_dims = st.multiselect(
        "Preset", PRESET_DIMENSIONS,
        default=["功能对比", "定价模型", "用户评价", "SWOT分析"],
        key="preset_dimensions",
        disabled=st.session_state.get("_running", False),
    )
    col_d1, col_d2 = st.columns([3, 1])
    with col_d1:
        new_dim = st.text_input("Custom dimension", placeholder="e.g. 安全合规",
                                key="new_dim_input", label_visibility="collapsed",
                                disabled=st.session_state.get("_running", False))
    with col_d2:
        if st.button("➕", key="add_dim", help="Add custom dimension", use_container_width=True,
                     disabled=st.session_state.get("_running", False)):
            val = new_dim.strip()
            if val and val not in PRESET_DIMENSIONS and val not in st.session_state.custom_dimensions:
                st.session_state.custom_dimensions.append(val)
            st.rerun()
    for i, d in enumerate(st.session_state.custom_dimensions):
        col_n, col_x = st.columns([5, 1])
        with col_n:
            st.caption(f"🔹 {d}")
        with col_x:
            if st.button("✕", key=f"rm_dim_{i}", help=f"Remove {d}",
                         disabled=st.session_state.get("_running", False)):
                st.session_state.custom_dimensions.pop(i)
                st.rerun()
    dimensions = selected_dims + st.session_state.custom_dimensions
    if not dimensions:
        st.warning("Select or add at least one dimension")

    st.divider()

    use_sample = st.checkbox("Use sample data", value=False, help="Pre-collected data, no web search needed",
                             disabled=st.session_state.get("_running", False))
    max_iterations = st.slider("Max QC iterations", 1, 5, 3, disabled=st.session_state.get("_running", False),
                               help="Maximum retry loops when QC finds issues")
    st.divider()

    if st.session_state.get("_running", False):
        if st.button("⏹️ Stop", type="secondary", use_container_width=True):
            st.session_state._stop_requested = True
            st.rerun()
    else:
        start_disabled = (not competitors or not dimensions)
        if st.button("▶️ Start Analysis", type="primary", use_container_width=True, disabled=start_disabled):
            st.session_state.trigger_run = True


# ── Background pipeline runner ──
def _generate_fallback_report(competitors, dimensions, analysis_result, collected_data, language):
    """Generate a basic fallback report when the Writer agent fails.
    Handles both dict (from LangGraph state) and object (AnalysisResult) types.
    """
    lang = language or "zh"
    labels = {
        "zh": {"title": "竞品分析报告", "generated": "生成时间", "competitors": "分析竞品",
               "dimensions": "分析维度", "summary": "摘要", "note": "⚠️ 注意：此报告为兜底生成，Writer Agent 未能正常完成。",
               "analysis_result": "分析结果数据", "sources": "数据来源"},
        "en": {"title": "Competitive Analysis Report", "generated": "Generated",
               "competitors": "Competitors", "dimensions": "Analysis Dimensions",
               "summary": "Summary", "note": "⚠️ Note: This is a fallback report; the Writer Agent did not complete normally.",
               "analysis_result": "Analysis Results", "sources": "Sources"},
    }
    L = labels.get(lang, labels["zh"])
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = [
        f"# {L['title']}",
        "",
        f"**{L['generated']}:** {ts}  ",
        f"**{L['competitors']}:** {', '.join(competitors)}  ",
        f"**{L['dimensions']}:** {', '.join(dimensions)}  ",
        "",
        L["note"],
        "",
        "---",
        f"## {L['summary']}",
        "",
    ]

    # Helper: safely get attr or key
    def _get(obj, key):
        if isinstance(obj, dict):
            return obj.get(key)
        return getattr(obj, key, None)

    # Feature matrix if available
    if analysis_result:
        fm = _get(analysis_result, 'feature_matrix')
        if fm:
            matrix_rows = _get(fm, 'matrix') if not isinstance(fm, dict) else fm.get('matrix', [])
            features_list = _get(fm, 'features') if not isinstance(fm, dict) else fm.get('features', [])
            if matrix_rows:
                lines.append(f"### {L['analysis_result']}")
                lines.append("")
                lines.append("| Feature | " + " | ".join(competitors) + " | Notes |")
                lines.append("|" + "|".join(["------"] * (len(competitors) + 2)) + "|")
                for row in matrix_rows:
                    if isinstance(row, dict):
                        feat = row.get('feature', '?')
                        vals_dict = row.get('values', {})
                        notes = row.get('notes', '')
                    else:
                        feat = getattr(row, 'feature', '?')
                        vals_dict = getattr(row, 'values', {})
                        notes = getattr(row, 'notes', '')
                    vals = " | ".join(str(vals_dict.get(c, "N/A")) for c in competitors)
                    lines.append(f"| {feat} | {vals} | {notes} |")
                lines.append("")

        insights = _get(analysis_result, 'key_insights')
        if insights:
            lines.append("### Key Insights")
            for insight in insights:
                lines.append(f"- {insight}")
            lines.append("")

    # Sources from collected data
    if collected_data:
        sources_seen = set()
        lines.append(f"## {L['sources']}")
        lines.append("")
        idx = 1
        for cd in collected_data.values():
            if isinstance(cd, dict):
                for s in cd.get("sources", []):
                    u = s.get("url", "")
                    if u and u not in sources_seen:
                        sources_seen.add(u)
                        lines.append(f"{idx}. [{s.get('title', 'Untitled')}]({u})")
                        idx += 1
        if not sources_seen:
            lines.append("_No source data available_")

    return "\n".join(lines)


def _run_pipeline(comps, dims, iters, lang, use_s):
    """Run the LangGraph pipeline in background thread.
    Writes results to a temp JSON file on disk (survives st.rerun() resets).
    
    Args are passed explicitly to avoid st.session_state thread-safety issues
    with Streamlit's daemon-thread context.
    """
    comps = list(comps)
    dims = list(dims)
    iters = int(iters)
    lang = str(lang)
    use_s = bool(use_s)
    status = get_status()
    try:
        # ── DEBUG: Log input config ──
        logger = logging.getLogger("pipeline")
        logger.info(f"[pipeline] START | comps={comps} | dims={dims} | use_sample={use_s} | lang={lang}")
        state = create_initial_state(comps, dims, iters, language=lang)
        if use_s:
            sample = get_sample_data()
            state["collected_data"] = {c: sample[c] for c in comps if c in sample}
            logger.info(f"[pipeline] Sample data loaded: {len(state['collected_data'])}/{len(comps)} competitors matched")
        else:
            logger.info("[pipeline] Running with live web search (sample data disabled)")

        result = build_graph().invoke(state)
        report = result.get("report", "")

        # ── Fallback: if report is empty but we have analysis_result, generate a basic report ──
        if not report:
            ar = result.get("analysis_result")
            cd = result.get("collected_data")
            if ar and cd:
                try:
                    report = _generate_fallback_report(comps, dims, ar, cd, lang)
                    status.set_overall("done", "Analysis complete (fallback report)")
                except Exception as e:
                    report = f"*Report generation failed after analysis: {e}*"
                    status.set_overall("error", str(e)[:200])
            else:
                err = result.get("error_message", "No report generated and no analysis results available.")
                report = f"*Analysis failed. {err}*"
                status.set_overall("error", err)

        # Build trace records
        trace = result.get("trace", [])
        trace_data = [
            {
                "agent": t.get("agent", "?"),
                "step": t.get("step", ""),
                "input": t.get("input_summary", ""),
                "output": t.get("output_summary", ""),
                "status": t.get("status", "?"),
                "calls": t.get("calls", 0),
                "tokens_in": t.get("total_tokens_input", 0),
                "tokens_out": t.get("total_tokens_output", 0),
                "duration_ms": t.get("total_duration_ms", 0),
            }
            for t in trace
        ]

        if report and not report.startswith("*Analysis failed"):
            status.set_overall("done", "Analysis complete")

        # Write result to disk file (survives st.rerun() script re-execution)
        result_dict = {
            "report": report,
            "trace": trace_data,
            "status": result.get("status", "unknown"),
            "success": True,
        }
        with open(_PIPELINE_RESULT_FILE, "w", encoding="utf-8") as f:
            json.dump(result_dict, f, ensure_ascii=False)
    except Exception as e:
        result_dict = {
            "report": f"*Pipeline error: {e}*",
            "trace": [],
            "status": "error",
            "success": False,
        }
        try:
            with open(_PIPELINE_RESULT_FILE, "w", encoding="utf-8") as f:
                json.dump(result_dict, f, ensure_ascii=False)
        except Exception:
            pass
        status.set_overall("error", str(e)[:200])
    # NOTE: File-based result bridge is used instead of module-level globals
    # because st.rerun() re-executes the entire script, wiping module globals.
    # The main thread polling loop picks up the _PIPELINE_RESULT_FILE on disk.


# ── Trigger pipeline ──
if st.session_state.get("trigger_run", False):
    st.session_state.trigger_run = False
    st.session_state._running = True
    st.session_state.pipeline_done = False
    st.session_state.pipeline_report = None
    st.session_state.pipeline_trace = None
    st.session_state.pipeline_status = None
    st.session_state.pipeline_competitors = competitors
    st.session_state.pipeline_dimensions = dimensions
    st.session_state.pipeline_max_iterations = max_iterations
    st.session_state.pipeline_lang = lang_code
    st.session_state.pipeline_use_sample = use_sample
    st.session_state._run_start_time = time.time()
    # Remove any stale result file from previous run
    if os.path.exists(_PIPELINE_RESULT_FILE):
        os.remove(_PIPELINE_RESULT_FILE)
    reset_status()
    get_status().set_overall("running", "Starting analysis...")
    thread = threading.Thread(target=_run_pipeline, args=(competitors, dimensions, max_iterations, lang_code, use_sample), daemon=True)
    thread.start()
    st.session_state._pipeline_thread = thread
    st.rerun()


# ── Running state: poll result file on disk for completion ──
if st.session_state.get("_running", False):
    # Check if the background thread has finished (via result file on disk)
    if os.path.exists(_PIPELINE_RESULT_FILE):
        try:
            with open(_PIPELINE_RESULT_FILE, "r", encoding="utf-8") as f:
                result = json.load(f)
            os.remove(_PIPELINE_RESULT_FILE)  # Clean up signal file
            st.session_state.pipeline_report = result["report"]
            st.session_state.pipeline_trace = result["trace"]
            st.session_state.pipeline_status = result["status"]
            st.session_state._running = False
            st.session_state.pipeline_done = True
            st.rerun()
        except (json.JSONDecodeError, KeyError) as e:
            st.warning(f"Result file corrupted, retrying... ({e})")
            if os.path.exists(_PIPELINE_RESULT_FILE):
                os.remove(_PIPELINE_RESULT_FILE)

    # Still running: show status
    status = get_status()
    snap = status.snapshot()
    elapsed = snap.get("elapsed_sec", 0)
    elapsed_str = f"{int(elapsed // 60)}m {int(elapsed % 60)}s"
    step_text = snap.get("current_step", "Running...")

    with st.expander("📋 Running Configuration", expanded=False):
        st.markdown(f"""
| Setting | Value |
|---------|-------|
| **Competitors** | {', '.join(st.session_state.get('pipeline_competitors', []))} |
| **Dimensions** | {', '.join(st.session_state.get('pipeline_dimensions', []))} |
| **Max QC Iterations** | {st.session_state.get('pipeline_max_iterations', 3)} |
| **Language** | {'中文' if st.session_state.get('pipeline_lang', 'zh') == 'zh' else 'English'} |
| **Data Source** | {'Sample data' if st.session_state.get('pipeline_use_sample', True) else 'Live search'} |
        """)

    agent_order = ["Collector", "Analyst", "Writer", "QC"]
    agent_snaps = {}
    for a in snap.get("agents", []):
        agent_snaps[a["name"]] = a

    status_colors = {
        "idle":    ("#475569", "○"),
        "running": ("#38bdf8", "◉"),
        "done":    ("#10b981", "●"),
        "error":   ("#ef4444", "◈"),
        "skipped": ("#6b7280", "◇"),
    }
    cols = st.columns(len(agent_order))
    for i, name in enumerate(agent_order):
        a = agent_snaps.get(name, {"status": "idle"})
        s = a.get("status", "idle")
        color, dot = status_colors.get(s, status_colors["idle"])
        with cols[i]:
            st.markdown(
                f"""<div style="text-align:center; padding:8px 4px;
                background:rgba(30,41,59,0.4); border-radius:8px;
                border:1px solid rgba(56,189,248,0.08);">
                <span style="font-size:1.1em; color:{color};">{dot}</span>
                <span style="font-size:0.85em; color:#94a3b8; margin-left:4px;">{name}</span>
                </div>""",
                unsafe_allow_html=True,
            )

    st.info(f"⏳ {step_text}")
    st.caption(f"⏱ Elapsed: {elapsed_str}")

    if st.button("⏹️ Stop Analysis", type="secondary"):
        st.session_state._stop_requested = True
        st.session_state._running = False
        st.session_state.pipeline_report = "*⚠️ Analysis was stopped by user.*"
        st.session_state.pipeline_done = True
        # Clean up result file
        if os.path.exists(_PIPELINE_RESULT_FILE):
            os.remove(_PIPELINE_RESULT_FILE)
        st.rerun()

    time.sleep(1)
    st.rerun()


# ── Done: show results ──
elif st.session_state.get("pipeline_done"):
    report = st.session_state.get("pipeline_report", "")
    pstatus = st.session_state.get("pipeline_status", "unknown")
    trace = st.session_state.get("pipeline_trace", [])

    # ── Agent Work Records ──
    st.subheader("📊 Agent Work Records")
    if trace:
        cols = st.columns(min(len(trace), 4))
        for i, t in enumerate(trace):
            is_ok = t.get("status") == "success"
            border = "#10b981" if is_ok else "#f59e0b"
            accent = "#34d399" if is_ok else "#fbbf24"
            badge = "✅" if is_ok else "⚠️"
            dur_s = t.get("duration_ms", 0) / 1000
            with cols[i % len(cols)]:
                st.markdown(f"""
<div style="
    border: 1.5px solid {border}55;
    border-top: 3px solid {accent};
    border-radius: 12px;
    padding: 14px;
    margin-bottom: 12px;
    background: linear-gradient(160deg, rgba(30,41,59,0.7) 0%, rgba(15,23,42,0.9) 100%);
    color: #cbd5e1;
    min-height: 148px;
    font-family: 'Inter', -apple-system, sans-serif;
    box-shadow: 0 2px 16px rgba(0,0,0,0.25), inset 0 1px 0 rgba(255,255,255,0.03);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
">
    <div style="font-size:1.05em; font-weight:600; letter-spacing:0.3px;">
        <span style="font-size:1.2em; margin-right:6px;">{badge}</span>{t.get('agent', '?')}
    </div>
    <div style="font-size:0.8em; color:#64748b; margin-top:2px;">{t.get('step', '')}</div>
    <div style="margin-top:10px; font-size:0.78em; line-height:1.7; color:#94a3b8;">
        <span>⚡ Calls: <b style="color:#e2e8f0;">{t.get('calls', 0)}</b></span><br>
        <span>🔤 Tokens: <b style="color:#e2e8f0;">{t.get('tokens_in', 0):,}</b> → <b style="color:#e2e8f0;">{t.get('tokens_out', 0):,}</b></span><br>
        <span>⏱ Duration: <b style="color:#e2e8f0;">{dur_s:.1f}s</b></span>
    </div>
    <div style="margin-top:8px; padding-top:8px; border-top:1px solid rgba(56,189,248,0.08); font-size:0.76em; line-height:1.5;">
        <span style="color:#64748b;">📥</span> <span style="color:#94a3b8;">{t.get('input', '')}</span><br>
        <span style="color:#64748b;">📤</span> <span style="color:#94a3b8;">{t.get('output', '')}</span>
    </div>
</div>
""", unsafe_allow_html=True)
    else:
        st.info("No agent work records available.")

    total_tokens = sum(t.get("tokens_in", 0) + t.get("tokens_out", 0) for t in trace) if trace else 0
    total_calls = sum(t.get("calls", 0) for t in trace) if trace else 0
    if total_tokens or total_calls:
        st.caption(f"📈 Total: {total_calls} LLM calls, {total_tokens:,} tokens")

    st.divider()

    # ── Report ──
    st.subheader("📄 Analysis Report")
    if report and not report.startswith("*Analysis failed") and not report.startswith("*Pipeline error"):
        st.markdown(report)
        col_dl, col_reset = st.columns([1, 1])
        with col_dl:
            st.download_button(
                "📥 Download Report (MD)",
                report,
                file_name=f"analysis_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
                mime="text/markdown",
                use_container_width=True,
            )
        with col_reset:
            if st.button("🔄 New Analysis", type="secondary", use_container_width=True):
                for key in list(st.session_state.keys()):
                    if key.startswith("pipeline_"):
                        del st.session_state[key]
                for key in ("_running", "_paused", "_stop_requested", "_run_start_time", "trigger_run", "_pipeline_thread"):
                    if key in st.session_state:
                        del st.session_state[key]
                reset_status()
                st.rerun()
    else:
        st.error(report or "No report generated.")
        if st.button("🔄 New Analysis", type="secondary"):
            for key in list(st.session_state.keys()):
                if key.startswith("pipeline_"):
                    del st.session_state[key]
            for key in ("_running", "_paused", "_stop_requested", "_run_start_time", "trigger_run", "_pipeline_thread"):
                if key in st.session_state:
                    del st.session_state[key]
            reset_status()
            st.rerun()

else:
    # ── Idle state ──
    st.subheader("📄 Analysis Report")
    st.info("Configure competitors, dimensions, and language in the sidebar. Then click **Start Analysis**.")
    st.markdown("""
### System Capabilities
| Agent | Role |
|-------|------|
| 🔍 **Collector** | Multi-source search, web scraping, structured data extraction |
| 📊 **Analyst** | Feature matrix scoring (0-3), SWOT analysis, pricing comparison |
| ✍️ **Writer** | Professional Markdown report with citations |
| ✅ **QC** | Completeness check, source validation, consistency verification |

> After analysis completes, each agent's work record (LLM calls, tokens, duration) will be displayed.
""")
