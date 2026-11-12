import json
from datetime import datetime, timedelta, timezone

from vacancy_scout.storage import RETENTION, SeenStore

NOW = datetime(2026, 11, 12, 9, 0, tzinfo=timezone.utc)


def test_new_url_is_new_until_marked(tmp_path):
    store = SeenStore(tmp_path / "seen.json", now=NOW)

    assert store.is_new("https://jobs.example/1")
    store.mark_seen("https://jobs.example/1")
    assert not store.is_new("https://jobs.example/1")


def test_state_survives_restart(tmp_path):
    path = tmp_path / "state" / "seen.json"
    first = SeenStore(path, now=NOW)
    first.mark_seen("https://jobs.example/1")
    first.save()

    second = SeenStore(path, now=NOW)

    assert not second.is_new("https://jobs.example/1")


def test_old_entries_are_pruned_on_save(tmp_path):
    path = tmp_path / "seen.json"
    old = (NOW - RETENTION - timedelta(days=1)).isoformat()
    recent = (NOW - timedelta(days=1)).isoformat()
    path.write_text(json.dumps({"https://old": old, "https://recent": recent}), encoding="utf-8")

    SeenStore(path, now=NOW).save()

    assert set(json.loads(path.read_text(encoding="utf-8"))) == {"https://recent"}


def test_corrupted_state_file_does_not_crash(tmp_path):
    path = tmp_path / "seen.json"
    path.write_text("{broken", encoding="utf-8")

    store = SeenStore(path, now=NOW)

    assert store.is_new("https://jobs.example/1")
