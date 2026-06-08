"""SQLite database for task and run persistence."""
import sqlite3, json, os, logging
from datetime import datetime
from config.settings import DB_PATH

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    competitors TEXT NOT NULL,
    dimensions TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    report_path TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'running',
    started_at TEXT NOT NULL,
    completed_at TEXT DEFAULT '',
    duration_seconds REAL DEFAULT 0.0,
    total_tokens INTEGER DEFAULT 0,
    qc_iterations INTEGER DEFAULT 0,
    qc_passed INTEGER DEFAULT 0,
    trace TEXT DEFAULT '[]',
    error_message TEXT DEFAULT '',
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);
CREATE INDEX IF NOT EXISTS idx_runs_task ON runs(task_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
"""

class Database:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init()

    def _init(self):
        with self._conn() as c:
            c.executescript(SCHEMA)
        logger.info(f"[db] Initialized: {self.db_path}")

    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def create_task(self, competitors, dimensions):
        now = datetime.now().isoformat()
        with self._conn() as c:
            cur = c.execute(
                "INSERT INTO tasks (competitors, dimensions, status, created_at, updated_at) VALUES (?,?,?,?,?)",
                (json.dumps(competitors), json.dumps(dimensions), "pending", now, now))
            return cur.lastrowid

    def create_run(self, task_id):
        now = datetime.now().isoformat()
        with self._conn() as c:
            cur = c.execute("INSERT INTO runs (task_id, status, started_at) VALUES (?,?,?)",
                          (task_id, "running", now))
            return cur.lastrowid

    def update_run(self, run_id, **kwargs):
        fields, vals = [], []
        for k, v in kwargs.items():
            if k == "status": fields.append("status=?"); vals.append(v)
            elif k == "iterations": fields.append("qc_iterations=?"); vals.append(v)
            elif k == "passed": fields.append("qc_passed=?"); vals.append(1 if v else 0)
            elif k == "trace": fields.append("trace=?"); vals.append(json.dumps(v))
            elif k == "error": fields.append("error_message=?"); vals.append(v)
            elif k == "duration": fields.append("duration_seconds=?"); vals.append(v)
        if "status" in kwargs and kwargs["status"] in ("completed", "failed"):
            fields.append("completed_at=?"); vals.append(datetime.now().isoformat())
        if fields:
            vals.append(run_id)
            with self._conn() as c:
                c.execute(f"UPDATE runs SET {','.join(fields)} WHERE id=?", vals)

    def get_task(self, task_id):
        with self._conn() as c:
            row = c.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
            if row:
                d = dict(row)
                d["competitors"] = json.loads(d["competitors"])
                d["dimensions"] = json.loads(d["dimensions"])
                return d

    def get_runs(self, task_id):
        with self._conn() as c:
            return [dict(r) for r in c.execute(
                "SELECT * FROM runs WHERE task_id=? ORDER BY started_at DESC", (task_id,)).fetchall()]

    def list_tasks(self, limit=20):
        with self._conn() as c:
            rows = c.execute("SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
            return [dict(r) for r in rows]
