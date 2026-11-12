"""Downloads a job board page as plain text."""

import logging

import requests

from .config import READER_PROXY

log = logging.getLogger(__name__)


class FetchError(RuntimeError):
    pass


def fetch_page_text(url: str, session: requests.Session | None = None, timeout: int = 30) -> str:
    """Fetch the page through the Jina Reader proxy, which strips markup and scripts."""
    http = session or requests.Session()
    log.info("Fetching %s", url)
    try:
        response = http.get(READER_PROXY + url, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise FetchError(f"Could not fetch {url}: {exc}") from exc

    if not response.text.strip():
        raise FetchError(f"Empty page returned for {url}")
    return response.text
