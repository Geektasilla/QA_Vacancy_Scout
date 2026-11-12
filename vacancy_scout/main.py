"""Pipeline: fetch page -> extract vacancies with LLM -> drop already seen -> notify."""

import logging
import sys
from collections.abc import Callable
from typing import Any

from .analyzer import extract_vacancies
from .config import JOB_TARGETS, ConfigError, Settings
from .fetcher import FetchError, fetch_page_text
from .models import Vacancy
from .notifier import NotifyError, format_digest, send_telegram
from .storage import SeenStore

log = logging.getLogger("vacancy_scout")


def scout_board(
    board: str,
    url: str,
    store: SeenStore,
    *,
    fetch: Callable[[str], str],
    extract: Callable[[str], list[Vacancy]],
    notify: Callable[[str], None],
) -> int:
    """Process one job board. Returns the number of new vacancies delivered."""
    page = fetch(url)
    new = [v for v in extract(page) if store.is_new(v.url)]
    if not new:
        log.info("%s: no new vacancies", board)
        return 0

    for message in format_digest(board, new):
        notify(message)
    # Mark as seen only after successful delivery, so a failed send is retried next run.
    for vacancy in new:
        store.mark_seen(vacancy.url)
    log.info("%s: delivered %d new vacancies", board, len(new))
    return len(new)


def run(settings: Settings, client: Any, targets: dict[str, str] = JOB_TARGETS) -> int:
    store = SeenStore(settings.state_file)

    def notify(message: str) -> None:
        if settings.dry_run:
            print(message, end="\n\n")
        else:
            send_telegram(message, settings.telegram_token, settings.telegram_chat_id)

    failures = 0
    for board, url in targets.items():
        try:
            scout_board(
                board,
                url,
                store,
                fetch=fetch_page_text,
                extract=lambda page: extract_vacancies(page, client, settings.model),
                notify=notify,
            )
        except (FetchError, NotifyError) as exc:
            # One broken board must not stop the others.
            failures += 1
            log.error("%s: %s", board, exc)

    if not settings.dry_run:
        store.save()
    return 1 if failures == len(targets) else 0


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        settings = Settings.from_env()
    except ConfigError as exc:
        log.error(exc)
        return 2

    from openai import OpenAI

    return run(settings, OpenAI(api_key=settings.openai_api_key))


if __name__ == "__main__":
    sys.exit(main())
