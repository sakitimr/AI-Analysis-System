"""Quick pipeline diagnostic."""
import sys, os, time, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

print('[1] Importing modules...')
from src.orchestration.state import create_initial_state
from src.orchestration.graph import build_graph
from src.tools.sample_data import get_sample_data
from src.monitoring.status import reset_status, get_status

print('[2] Loading sample data...')
sample = get_sample_data()
competitors = list(sample.keys())
dims = ['功能对比', '定价模型', '用户评价', 'SWOT分析']
print(f'   Competitors: {competitors}')
print(f'   Dimensions: {dims}')

print('[3] Creating initial state...')
state = create_initial_state(competitors, dims, 3, language='zh')
state['collected_data'] = {c: sample[c] for c in competitors if c in sample}
print(f'   State keys: {list(state.keys())}')

print('[4] Building graph...')
graph = build_graph()

print('[5] Invoking pipeline (timeout=120s)...')
reset_status()
start = time.time()
try:
    result = graph.invoke(state, {'recursion_limit': 20})
    elapsed = time.time() - start
    print(f'   Done in {elapsed:.1f}s')
    report = result.get('report', '')
    if report:
        print(f'   Report length: {len(report)} chars')
        print(f'   First 200 chars: {report[:200]}...')
    else:
        status = result.get('status', 'unknown')
        error = result.get('error_message', 'none')
        print(f'   NO REPORT. Status: {status}, Error: {error}')
        print(f'   QC result: {result.get("qc_result", {})}')
        print(f'   Analysis result keys: {list(result.get("analysis_result", {}).keys()) if isinstance(result.get("analysis_result"), dict) else type(result.get("analysis_result"))}')
except Exception as e:
    elapsed = time.time() - start
    print(f'   FAILED after {elapsed:.1f}s: {e}')
    traceback.print_exc()
