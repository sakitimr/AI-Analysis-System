"""Base Agent class with LLM interaction utilities."""
import logging, time, json
from datetime import datetime
from typing import Any, Dict, Optional
from langchain_openai import ChatOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential
from config.settings import DOUBAO_API_KEY, DOUBAO_BASE_URL, DOUBAO_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS, LLM_TIMEOUT
from src.schema.messages import TraceEntry

logger = logging.getLogger(__name__)


class BaseAgent:
    def __init__(self, name: str, model: Optional[ChatOpenAI] = None):
        self.name = name
        self.model = model or ChatOpenAI(model=DOUBAO_MODEL, api_key=DOUBAO_API_KEY, base_url=DOUBAO_BASE_URL, temperature=LLM_TEMPERATURE, max_tokens=LLM_MAX_TOKENS, timeout=LLM_TIMEOUT)
        self.last_trace = {}  # Per-call trace metadata
        self.call_log = []    # Accumulated call traces for aggregation
        self._total_tokens = {"input": 0, "output": 0}
        self._total_duration_ms = 0

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=30), reraise=True)
    def _invoke_with_retry(self, prompt: str, **kwargs):
        """Internal LLM call with exponential-backoff retry (transient errors only)."""
        return self.model.invoke(prompt, **kwargs)

    def invoke(self, prompt: str, **kwargs) -> str:
        start = time.time()
        entry = {"agent": self.name, "prompt_chars": len(prompt)}
        try:
            response = self._invoke_with_retry(prompt, **kwargs)
            elapsed_ms = int((time.time() - start) * 1000)
            token_usage = {}
            if hasattr(response, 'response_metadata'):
                meta = response.response_metadata
                token_usage = {"input": meta.get("token_usage", {}).get("prompt_tokens", 0), "output": meta.get("token_usage", {}).get("completion_tokens", 0)}
            content = response.content if hasattr(response, 'content') else str(response)
            entry.update({
                "duration_ms": elapsed_ms,
                "token_input": token_usage.get("input", 0),
                "token_output": token_usage.get("output", 0),
                "output_chars": len(content),
                "status": "success"
            })
            self._total_tokens["input"] += token_usage.get("input", 0)
            self._total_tokens["output"] += token_usage.get("output", 0)
            self._total_duration_ms += elapsed_ms
            self.last_trace = entry
            self.call_log.append(entry)
            self._push_monitor(entry)
            logger.info(f"[{self.name}] Invoke | {elapsed_ms}ms | tokens: {token_usage}")
            return content
        except Exception as e:
            elapsed_ms = int((time.time() - start) * 1000)
            entry.update({"duration_ms": elapsed_ms, "status": "error", "error": str(e)[:200]})
            self._total_duration_ms += elapsed_ms
            self.last_trace = entry
            self.call_log.append(entry)
            self._push_monitor(entry)
            logger.error(f"[{self.name}] Invoke failed after retries: {e}")
            raise

    def safe_invoke_json(self, prompt: str, max_retries: int = 2, **kwargs) -> dict:
        """Invoke LLM, parse JSON, retry with fix prompt on failure.

        Three-layer defense:
        1. Direct JSON parse via safe_json_parse
        2. If parse fails, ask LLM to fix its own JSON
        3. If still fails, raise ValueError for caller to handle
        """
        from src.schema.validators import safe_json_parse

        for attempt in range(max_retries + 1):
            try:
                resp = self.invoke(prompt, **kwargs)
                return safe_json_parse(resp)
            except (ValueError, json.JSONDecodeError) as e:
                if attempt < max_retries:
                    logger.warning(f"[{self.name}] JSON parse failed (attempt {attempt+1}), asking LLM to fix: {e}")
                    prompt = f"""Your previous output failed JSON validation. Error: {str(e)[:200]}

Please fix the JSON and output ONLY valid JSON (no markdown, no explanation).

Previous prompt context: {prompt[:500]}..."""
                else:
                    raise ValueError(f"JSON parse failed after {max_retries} retries: {e}") from e

    def get_trace(self, step: str = "", input_summary: str = "", output_summary: str = "") -> dict:
        """Return aggregated trace for graph nodes to record."""
        return {
            "agent": self.name,
            "step": step,
            "input_summary": input_summary,
            "output_summary": output_summary,
            "status": "success" if all(c.get("status") == "success" for c in self.call_log) else "partial",
            "calls": len(self.call_log),
            "total_tokens_input": self._total_tokens["input"],
            "total_tokens_output": self._total_tokens["output"],
            "total_duration_ms": self._total_duration_ms,
        }

    def make_trace(self, step: str, **kwargs) -> TraceEntry:
        return TraceEntry(agent_name=self.name, step=step, **kwargs)

    def _push_monitor(self, entry: dict):
        """Push LLM call details to the shared pipeline status store."""
        try:
            from src.monitoring.status import get_status
            get_status().add_llm_call(self.name, {
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "prompt_chars": entry.get("prompt_chars", 0),
                "output_chars": entry.get("output_chars", 0),
                "token_input": entry.get("token_input", 0),
                "token_output": entry.get("token_output", 0),
                "duration_ms": entry.get("duration_ms", 0),
                "status": entry.get("status", "?"),
            })
        except Exception:
            pass  # monitoring is best-effort, never crash the pipeline
