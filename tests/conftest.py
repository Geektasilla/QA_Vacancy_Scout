import json
from types import SimpleNamespace

import pytest

from vacancy_scout.models import Vacancy


class FakeOpenAI:
    """Mimics client.chat.completions.create() and records the request."""

    def __init__(self, content: str) -> None:
        self.content = content
        self.calls: list[dict] = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        message = SimpleNamespace(content=self.content)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


@pytest.fixture
def make_llm():
    def factory(vacancies: list[dict]) -> FakeOpenAI:
        return FakeOpenAI(json.dumps({"vacancies": vacancies}))

    return factory


@pytest.fixture
def vacancy() -> Vacancy:
    return Vacancy(
        title="QA Automation Engineer (m/w/d)",
        url="https://www.stepstone.de/stellenangebote--qa-1.html",
        company="ACME GmbH",
        location="Berlin",
        posted="2 hours ago",
    )
