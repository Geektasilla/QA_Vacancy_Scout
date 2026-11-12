"""Formats the digest and delivers it to Telegram."""

import html
import logging

import requests

from .models import Vacancy

log = logging.getLogger(__name__)

TELEGRAM_LIMIT = 4096  # max characters per Telegram message


class NotifyError(RuntimeError):
    pass


def format_digest(board: str, vacancies: list[Vacancy]) -> list[str]:
    """Build HTML messages; split into several if the Telegram size limit is exceeded."""
    header = f"🚀 <b>New QA jobs · {html.escape(board)}</b>\n\n"
    lines = [_format_line(i, v) for i, v in enumerate(vacancies, start=1)]

    messages, current = [], header
    for line in lines:
        if len(current) + len(line) + 1 > TELEGRAM_LIMIT:
            messages.append(current.rstrip())
            current = header
        current += line + "\n"
    messages.append(current.rstrip())
    return messages


def _format_line(index: int, v: Vacancy) -> str:
    title = f'<a href="{html.escape(v.url, quote=True)}">{html.escape(v.title)}</a>'
    parts = (v.company, v.location and f"📍 {v.location}", v.posted and f"📅 {v.posted}")
    details = [html.escape(part) for part in parts if part]
    return f"{index}. {title}" + (" | " + " | ".join(details) if details else "")


def send_telegram(text: str, token: str, chat_id: str, session: requests.Session | None = None) -> None:
    http = session or requests.Session()
    try:
        response = http.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True},
            timeout=20,
        )
    except requests.RequestException as exc:
        # The exception text contains the request URL (and therefore the token) - do not log it.
        raise NotifyError(f"Telegram request failed: {type(exc).__name__}") from None

    if response.status_code != 200:
        raise NotifyError(f"Telegram API returned {response.status_code}: {response.text[:200]}")
