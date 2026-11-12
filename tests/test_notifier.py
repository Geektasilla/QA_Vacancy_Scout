from unittest.mock import Mock

import pytest
import requests

from vacancy_scout.models import Vacancy
from vacancy_scout.notifier import TELEGRAM_LIMIT, NotifyError, format_digest, send_telegram


def test_digest_contains_clickable_title_and_details(vacancy):
    [message] = format_digest("Stepstone", [vacancy])

    assert f'<a href="{vacancy.url}">QA Automation Engineer (m/w/d)</a>' in message
    assert "ACME GmbH | 📍 Berlin | 📅 2 hours ago" in message


def test_html_special_characters_are_escaped():
    v = Vacancy(title="QA <Lead> & Tester", url="https://jobs.example/?a=1&b=2", company="R&D")

    [message] = format_digest("Board", [v])

    assert "QA &lt;Lead&gt; &amp; Tester" in message
    assert 'href="https://jobs.example/?a=1&amp;b=2"' in message
    assert "R&amp;D" in message


def test_long_digest_is_split_under_telegram_limit():
    many = [Vacancy(title="QA Engineer " + "x" * 150, url=f"https://jobs.example/{i}") for i in range(60)]

    messages = format_digest("Board", many)

    assert len(messages) > 1
    assert all(len(m) <= TELEGRAM_LIMIT for m in messages)
    assert sum(m.count("<a href") for m in messages) == 60


def test_send_uses_html_parse_mode():
    session = Mock()
    session.post.return_value = Mock(status_code=200)

    send_telegram("hello", token="TOKEN", chat_id="42", session=session)

    payload = session.post.call_args.kwargs["json"]
    assert payload == {"chat_id": "42", "text": "hello", "parse_mode": "HTML", "disable_web_page_preview": True}


def test_api_error_raises():
    session = Mock()
    session.post.return_value = Mock(status_code=400, text="Bad Request: can't parse entities")

    with pytest.raises(NotifyError, match="400"):
        send_telegram("hello", token="TOKEN", chat_id="42", session=session)


def test_network_error_does_not_leak_token():
    session = Mock()
    session.post.side_effect = requests.ConnectionError("https://api.telegram.org/botSECRET-TOKEN/sendMessage")

    with pytest.raises(NotifyError) as exc_info:
        send_telegram("hello", token="SECRET-TOKEN", chat_id="42", session=session)

    assert "SECRET-TOKEN" not in str(exc_info.value)
    assert exc_info.value.__cause__ is None
