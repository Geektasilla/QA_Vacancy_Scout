from datetime import datetime, timezone
from unittest.mock import Mock

import pytest
import requests

from vacancy_scout.config import ConfigError, Settings
from vacancy_scout.fetcher import FetchError, fetch_page_text
from vacancy_scout.main import scout_board
from vacancy_scout.models import Vacancy
from vacancy_scout.notifier import NotifyError
from vacancy_scout.storage import SeenStore

NOW = datetime(2026, 11, 12, tzinfo=timezone.utc)
A = Vacancy(title="QA A", url="https://jobs.example/a")
B = Vacancy(title="QA B", url="https://jobs.example/b")


@pytest.fixture
def store(tmp_path):
    return SeenStore(tmp_path / "seen.json", now=NOW)


def test_only_unseen_vacancies_are_sent(store):
    store.mark_seen(A.url)
    sent: list[str] = []

    count = scout_board(
        "Board", "https://board", store, fetch=lambda url: "page", extract=lambda page: [A, B], notify=sent.append
    )

    assert count == 1
    assert "QA B" in sent[0] and "QA A" not in sent[0]


def test_second_run_sends_nothing(store):
    sent: list[str] = []
    kwargs = dict(fetch=lambda url: "page", extract=lambda page: [A, B], notify=sent.append)

    scout_board("Board", "https://board", store, **kwargs)
    scout_board("Board", "https://board", store, **kwargs)

    assert len(sent) == 1


def test_failed_delivery_is_retried_next_run(store):
    def broken_notify(message):
        raise NotifyError("Telegram down")

    with pytest.raises(NotifyError):
        scout_board("Board", "https://board", store, fetch=lambda url: "page", extract=lambda page: [A], notify=broken_notify)

    assert store.is_new(A.url)


def test_no_message_when_nothing_found(store):
    notify = Mock()

    scout_board("Board", "https://board", store, fetch=lambda url: "page", extract=lambda page: [], notify=notify)

    notify.assert_not_called()


def test_fetch_goes_through_reader_proxy():
    session = Mock()
    session.get.return_value = Mock(text="content", raise_for_status=Mock())

    assert fetch_page_text("https://board", session=session) == "content"
    assert session.get.call_args.args[0] == "https://r.jina.ai/https://board"


def test_fetch_wraps_http_errors():
    session = Mock()
    session.get.side_effect = requests.Timeout("slow")

    with pytest.raises(FetchError):
        fetch_page_text("https://board", session=session)


def test_settings_require_secrets(monkeypatch):
    monkeypatch.setattr("vacancy_scout.config.load_dotenv", lambda: None)
    for name in ("OPENAI_API_KEY", "TELEGRAM_TOKEN", "TELEGRAM_CHAT_ID", "DRY_RUN"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    with pytest.raises(ConfigError, match="TELEGRAM_TOKEN, TELEGRAM_CHAT_ID"):
        Settings.from_env()

    monkeypatch.setenv("DRY_RUN", "true")
    assert Settings.from_env().dry_run is True


def test_settings_repr_hides_secrets():
    settings = Settings(openai_api_key="sk-secret", telegram_token="tg-secret", telegram_chat_id="123")

    assert "secret" not in repr(settings)
