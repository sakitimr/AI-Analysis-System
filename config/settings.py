"""Global configuration."""
import os
from dotenv import load_dotenv
load_dotenv()
DOUBAO_API_KEY = os.getenv("DOUBAO_API_KEY", "")
DOUBAO_BASE_URL = os.getenv("DOUBAO_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
DOUBAO_MODEL = os.getenv("DOUBAO_MODEL", "doubao-seed-2.0-lite-251015")
LLM_TEMPERATURE = 0.3
LLM_MAX_TOKENS = 4096
LLM_TIMEOUT = 120
MAX_QC_ITERATIONS = 3
MAX_SEARCH_RESULTS = 6
MAX_PAGE_CONTENT_CHARS = 8000
SEARCH_TIMEOUT = 8
SEARCH_PROXY = os.getenv("SEARCH_PROXY", "")
SCRAPE_DELAY = 1.0
SCRAPE_TIMEOUT = 8
MAX_SCRAPE_PAGES = 2
MAX_SCRAPE_FAILURES = 5
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "tasks.db")
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "cache")
REPORT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "reports")
SCHEMA_DIR = os.path.join(os.path.dirname(__file__), "schema")
PROMPT_DIR = os.path.join(os.path.dirname(__file__), "prompts")
DEFAULT_COMPETITORS = ["Cursor", "GitHub Copilot", "TRAE"]
DEFAULT_DIMENSIONS = ["功能对比", "定价模型", "用户评价", "SWOT分析"]
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
