"""Full pipeline CLI runner."""
import argparse, logging, sys, time, os
from datetime import datetime
from pathlib import Path
from src.orchestration.state import create_initial_state
from src.orchestration.graph import build_graph
from src.tools.sample_data import get_sample_data
from src.storage.database import Database

# Resolve project root regardless of CWD
PROJECT_ROOT = Path(__file__).resolve().parent

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("pipeline")

def main():
    p = argparse.ArgumentParser(description="Competitive Analysis Pipeline")
    p.add_argument("--competitors", default="Cursor,GitHub Copilot,TRAE")
    p.add_argument("--dimensions", default="功能对比,定价模型,用户评价,SWOT分析")
    p.add_argument("--online", action="store_true")
    p.add_argument("--max-iterations", type=int, default=3)
    p.add_argument("--output", default="")
    p.add_argument("--api", action="store_true")
    args = p.parse_args()

    comps = [c.strip() for c in args.competitors.split(",")]
    dims = [d.strip() for d in args.dimensions.split(",")]

    if args.api:
        import uvicorn
        logger.info("Starting API server on :8000")
        uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
        return

    print("=" * 60)
    print("  AI-Driven Competitive Analysis Agent System")
    print("=" * 60)
    print(f"  Competitors: {', '.join(comps)}")
    print(f"  Dimensions: {', '.join(dims)}")
    print(f"  Mode: {'Online' if args.online else 'Offline (sample data)'}")
    print("=" * 60)

    db = Database()
    tid = db.create_task(comps, dims)
    rid = db.create_run(tid)

    state = create_initial_state(comps, dims, args.max_iterations)
    if not args.online:
        sample = get_sample_data()
        state["collected_data"] = {c: sample[c] for c in comps if c in sample}
        print(f"Loaded sample data: {len(state['collected_data'])} competitors")

    print("\nStarting analysis...\n")
    start = time.time()

    try:
        graph = build_graph()
        result = graph.invoke(state)
        elapsed = time.time() - start
        status = result.get("status", "unknown")

        print(f"\n{'='*60}")
        print(f"  Complete! Status: {status} | Time: {elapsed:.1f}s")
        qc = result.get("qc_result", {})
        if qc:
            print(f"  QC Score: {qc.get('overall_score', 0):.0%} | Iterations: {qc.get('iteration', 0)}")
        trace = result.get("trace", [])
        print(f"  Chain: {' -> '.join(t.get('agent','?') for t in trace)}")
        total_tokens = sum(t.get("total_tokens_input", 0) + t.get("total_tokens_output", 0) for t in trace)
        print(f"  Total tokens: {total_tokens} | LLM calls: {sum(t.get('calls',0) for t in trace)}")
        for t in trace:
            calls = t.get("calls", 0)
            dur = t.get("total_duration_ms", 0) / 1000
            tin = t.get("total_tokens_input", 0)
            tout = t.get("total_tokens_output", 0)
            out = t.get("output_summary", "")
            print(f"  [{t.get('agent','?')}] {calls} calls | {dur:.1f}s | {tin}+{tout} tokens | {out}")
        print(f"{'='*60}\n")

        report = result.get("report", "")
        if report:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            out_dir = PROJECT_ROOT / "data" / "reports"
            out_dir.mkdir(parents=True, exist_ok=True)
            path = args.output or str(out_dir / f"analysis_{ts}.md")
            with open(path, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"Report saved: {path} ({len(report)} chars)")
            db.update_run(rid, status="completed", iterations=qc.get("iteration", 0), passed=qc.get("pass_", qc.get("pass", False)), trace=trace, duration=elapsed)
            print("\n" + "-" * 40)
            print(report[:500])
            print("...")
        else:
            error = result.get("error_message", "Unknown")
            status = result.get("status", "unknown")
            print(f"\n⚠️  REPORT GENERATION FAILED")
            print(f"   Status: {status}")
            print(f"   Error: {error}")
            analysis = result.get("analysis_result")
            if analysis:
                if isinstance(analysis, dict):
                    print(f"   Analysis keys: {list(analysis.keys())}")
                    print(f"   Competitors: {analysis.get('competitors', [])}")
                else:
                    print(f"   Analysis type: {type(analysis).__name__}")
            else:
                print(f"   Analysis result: MISSING")
            collected = result.get("collected_data")
            print(f"   Collected data: {'present' if collected else 'MISSING'} ({len(collected) if isinstance(collected, dict) else 0} entries)")
            db.update_run(rid, status="failed", error=error, iterations=qc.get("iteration", 0), trace=trace, duration=elapsed)
        return result
    except Exception as e:
        elapsed = time.time() - start
        logger.error(f"Pipeline failed: {e}")
        db.update_run(rid, status="failed", error=str(e), duration=elapsed)
        print(f"\nFAILED ({elapsed:.1f}s): {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
