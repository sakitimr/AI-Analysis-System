"""Citation management for traceability."""
import json
from typing import List, Dict, Optional
from datetime import datetime

class CitationManager:
    def __init__(self):
        self._sources: Dict[str, dict] = {}
        self._counter: int = 0

    def register(self, source: dict) -> int:
        url = source.get("url", "")
        if url in self._sources:
            return self._sources[url]["id"]
        self._counter += 1
        self._sources[url] = {
            "id": self._counter, "url": url,
            "title": source.get("title", "Untitled"),
            "type": source.get("type", "other"),
            "accessed_at": datetime.now().isoformat()}
        return self._counter

    def get(self, cid: int) -> Optional[dict]:
        for s in self._sources.values():
            if s["id"] == cid: return s
        return None

    def list_all(self) -> List[dict]:
        return sorted(self._sources.values(), key=lambda x: x["id"])

    def format_markdown(self) -> str:
        lines = []
        for s in self.list_all():
            lines.append(f"{s['id']}. [{s['title']}]({s['url']}) -- *{s['type']}*")
        return "\n".join(lines) if lines else "No sources"

    @property
    def count(self) -> int:
        return len(self._sources)
