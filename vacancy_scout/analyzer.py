"""Extracts structured vacancies from raw page text with an LLM."""

import json
import logging
from typing import Any

from .models import Vacancy

log = logging.getLogger(__name__)

# Page text is truncated to keep the request small and the cost predictable.
MAX_INPUT_CHARS = 60_000

SYSTEM_PROMPT = """\
You are a recruitment scout. You receive the text of a job board search results page.
Extract QA / software testing vacancies posted within the last 24 hours
(e.g. "Today", "1 hour ago", "Neu", "vor 5 Stunden"). Ignore everything older and ignore ads.

Return JSON only, in exactly this shape:
{"vacancies": [{"title": str, "url": str, "company": str, "location": str, "posted": str}]}

Rules:
- "url" must be the absolute link to the vacancy exactly as it appears in the text. Never invent links.
- Use an empty string for unknown fields.
- If there are no matching vacancies, return {"vacancies": []}.
"""


def extract_vacancies(page_text: str, client: Any, model: str) -> list[Vacancy]:
    """Ask the model for vacancies as JSON and validate the result."""
    response = client.chat.completions.create(
        model=model,
        temperature=0,  # deterministic output: same page -> same answer
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": page_text[:MAX_INPUT_CHARS]},
        ],
    )
    return parse_vacancies(response.choices[0].message.content)


def parse_vacancies(raw: str | None) -> list[Vacancy]:
    """Validate the model output; malformed items are skipped instead of failing the run."""
    try:
        payload = json.loads(raw or "")
    except json.JSONDecodeError:
        log.warning("Model returned invalid JSON, skipping this page")
        return []

    items = payload.get("vacancies") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        return []

    vacancies: list[Vacancy] = []
    seen_urls: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip()
        url = str(item.get("url", "")).strip()
        if not title or not url.startswith(("http://", "https://")) or url in seen_urls:
            continue
        seen_urls.add(url)
        vacancies.append(
            Vacancy(
                title=title,
                url=url,
                company=str(item.get("company", "")).strip(),
                location=str(item.get("location", "")).strip(),
                posted=str(item.get("posted", "")).strip(),
            )
        )
    return vacancies
