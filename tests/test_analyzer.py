import json

import pytest

from vacancy_scout.analyzer import MAX_INPUT_CHARS, extract_vacancies, parse_vacancies


def test_extracts_valid_vacancies(make_llm):
    llm = make_llm(
        [{"title": "QA Engineer", "url": "https://jobs.example/1", "company": "ACME", "location": "Berlin", "posted": "Today"}]
    )

    result = extract_vacancies("page", llm, model="gpt-4o-mini")

    assert len(result) == 1
    assert result[0].title == "QA Engineer"
    assert result[0].location == "Berlin"


def test_request_is_deterministic_and_json(make_llm):
    llm = make_llm([])

    extract_vacancies("x" * (MAX_INPUT_CHARS + 500), llm, model="gpt-4o-mini")

    request = llm.calls[0]
    assert request["temperature"] == 0
    assert request["response_format"] == {"type": "json_object"}
    assert len(request["messages"][1]["content"]) == MAX_INPUT_CHARS


@pytest.mark.parametrize(
    "raw",
    ["not json", "", None, json.dumps([1, 2]), json.dumps({"vacancies": "oops"}), json.dumps({"other": []})],
    ids=["text", "empty", "none", "list", "wrong-type", "missing-key"],
)
def test_malformed_output_returns_empty_list(raw):
    assert parse_vacancies(raw) == []


@pytest.mark.parametrize(
    "item",
    [
        {"title": "", "url": "https://jobs.example/1"},
        {"title": "QA", "url": ""},
        {"title": "QA", "url": "jobs.example/relative"},
        "just a string",
    ],
    ids=["no-title", "no-url", "relative-url", "not-an-object"],
)
def test_invalid_items_are_skipped(item):
    raw = json.dumps({"vacancies": [item, {"title": "Valid", "url": "https://jobs.example/ok"}]})

    result = parse_vacancies(raw)

    assert [v.title for v in result] == ["Valid"]


def test_duplicate_urls_within_one_page_are_collapsed():
    raw = json.dumps({"vacancies": [{"title": "A", "url": "https://jobs.example/1"}, {"title": "A again", "url": "https://jobs.example/1"}]})

    assert len(parse_vacancies(raw)) == 1
