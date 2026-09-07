"""Coldline.

===================

File:              tests/contract/test_baseline_answers.py
Component:         Contract tests — Baseline answer recomputation
Purpose:           Check the recorded success and miss claims against the running system.
Interacts With:    The running retrieval API, the golden set, and submission.yaml
Sprint/Task:       Sprint 2 — Project 2
Concepts:          Recomputed evidence, published criteria, deterministic assessment
Tools:             Python 3.12, pytest, httpx
"""

from pathlib import Path

import httpx
import pytest
import yaml

from tests.golden import GoldenQuery, api_base_url, is_miss, is_success, load_queries, search

TASK_ROOT = Path(__file__).resolve().parents[2]
# Assessed: a fresh starter has a blank answer sheet and is supposed to fail
# these. Runtime: they rerun the recorded queries against the started stack.
pytestmark = [pytest.mark.runtime, pytest.mark.assessed]


def _answers() -> dict[str, str]:
    """Return the recorded answer mapping from the student's sheet."""
    document = yaml.safe_load((TASK_ROOT / "submission.yaml").read_text(encoding="utf-8"))
    answers = document.get("answers") if isinstance(document, dict) else None
    if not isinstance(answers, dict):
        pytest.fail("submission.yaml must define an answers mapping")
    return {key: str(value) for key, value in answers.items()}


def _query(query_id: str) -> GoldenQuery:
    """Return the published query with one identifier."""
    for query in load_queries():
        if query.query_id == query_id:
            return query
    pytest.fail(
        f"{query_id!r} is not a published query identifier; run `poe baseline` and copy one of "
        "the identifiers it prints"
    )


def _run(query: GoldenQuery) -> dict[str, object]:
    """Run one query against the running API or fail with actionable guidance."""
    with httpx.Client(timeout=20.0) as client:
        try:
            return search(client, query)
        except httpx.HTTPError as exc:
            pytest.fail(
                f"could not reach the retrieval API at {api_base_url()}: {exc}. "
                "Run `poe start` and `poe ingest` first."
            )


def test_recorded_success_query_meets_the_published_success_criterion() -> None:
    """A recorded success claim is checked by rerunning that exact query.

    Nothing about the expected answer is stored in this repository. The check
    recomputes the outcome from the running system, so it cannot be satisfied
    by a lucky guess and it leaks no answer key.
    """
    answers = _answers()
    query_id = answers.get("success_query_id", "")
    if not query_id:
        pytest.fail("answers.success_query_id is empty; complete submission.yaml")
    query = _query(query_id)
    payload = _run(query)
    if not payload["results"]:
        pytest.fail(
            f"{query_id} returned no candidates at all. Ingest the corpus with `poe ingest` "
            "before recording answers."
        )
    assert is_success(query, payload), (
        f"{query_id} does not meet the published success criterion: its target document "
        f"{query.target_document_id!r} is absent from the returned results"
    )


def test_recorded_miss_query_meets_the_published_miss_criterion() -> None:
    """A recorded miss claim is checked by rerunning that exact query."""
    answers = _answers()
    query_id = answers.get("miss_query_id", "")
    if not query_id:
        pytest.fail("answers.miss_query_id is empty; complete submission.yaml")
    query = _query(query_id)
    payload = _run(query)
    if not payload["results"]:
        pytest.fail(
            f"{query_id} returned no candidates at all, which means the corpus is not ingested. "
            "An empty index is not the published miss criterion; run `poe ingest`."
        )
    assert is_miss(query, payload), (
        f"{query_id} does not meet the published miss criterion: its target document "
        f"{query.target_document_id!r} is present in the returned results"
    )


def test_recorded_queries_are_two_different_published_queries() -> None:
    """The two answers must name two different published queries."""
    answers = _answers()
    success = answers.get("success_query_id", "")
    miss = answers.get("miss_query_id", "")
    if not success or not miss:
        pytest.fail("both answers.success_query_id and answers.miss_query_id must be recorded")
    assert success != miss, "the success and miss answers must name different queries"
