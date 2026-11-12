"""Remembers which vacancies were already sent, so each one is delivered only once."""

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

log = logging.getLogger(__name__)

# Entries older than this are forgotten to keep the state file small.
RETENTION = timedelta(days=30)


class SeenStore:
    def __init__(self, path: str | Path, now: datetime | None = None) -> None:
        self.path = Path(path)
        self.now = now or datetime.now(timezone.utc)
        self._seen: dict[str, str] = self._load()

    def _load(self) -> dict[str, str]:
        if not self.path.exists():
            return {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            log.warning("State file %s is unreadable, starting fresh", self.path)
            return {}
        return data if isinstance(data, dict) else {}

    def is_new(self, url: str) -> bool:
        return url not in self._seen

    def mark_seen(self, url: str) -> None:
        self._seen[url] = self.now.isoformat()

    def save(self) -> None:
        cutoff = self.now - RETENTION
        fresh = {url: ts for url, ts in self._seen.items() if _parse(ts) >= cutoff}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(fresh, indent=2, sort_keys=True), encoding="utf-8")


def _parse(timestamp: str) -> datetime:
    try:
        return datetime.fromisoformat(timestamp)
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)
