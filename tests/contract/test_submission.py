"""Coldline.

===================

File:              tests/contract/test_submission.py
Component:         Contract tests — Test Submission
Purpose:           Tests for the public answer and path checks for this Task's submission.
Interacts With:    Published interfaces and repository boundaries
Sprint/Task:       Sprint 2 — Project 2
Concepts:          Compatibility, ownership, export safety
Tools:             Python 3.12, pytest
"""

from pathlib import Path

import pytest
import yaml

from tests.contract.submission_validation import (
    SubmissionError,
    _load_one_document,
    main,
    validate_changed_paths,
    validate_submission,
)
from tests.golden import load_queries

ROOT = Path(__file__).parents[2]
SCHEMA = ROOT / "docs/contracts/submission.schema.json"


def valid_answers() -> dict[str, object]:
    """Return a complete answer sheet using two real published query identifiers.

    These are shape fixtures. Whether either query truly meets the success or
    the miss criterion is decided by ``test_baseline_answers.py`` against the
    running system, so nothing here encodes an expected outcome.
    """
    queries = load_queries()
    return {
        "answers": {
            "success_query_id": queries[0].query_id,
            "miss_query_id": queries[1].query_id,
        }
    }


def _task_root(tmp_path: Path, submission_text: str) -> Path:
    """Stage a minimal Task root the public verifier can validate."""
    (tmp_path / "docs/contracts").mkdir(parents=True)
    (tmp_path / "infra/corpus").mkdir(parents=True)
    (tmp_path / "submission.yaml").write_text(submission_text, encoding="utf-8")
    (tmp_path / "submission-sample.yaml").write_text(
        (ROOT / "submission-sample.yaml").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (tmp_path / "docs/contracts/submission.schema.json").write_text(
        SCHEMA.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (tmp_path / "infra/corpus/queries.jsonl").write_text(
        (ROOT / "infra/corpus/queries.jsonl").read_text(encoding="utf-8"), encoding="utf-8"
    )
    return tmp_path


def test_complete_answer_shape_passes_public_validation(tmp_path: Path) -> None:
    """A complete direct-answer mapping must pass syntax and schema validation."""
    root = _task_root(tmp_path, yaml.safe_dump(valid_answers()))

    validate_submission(root / "submission.yaml", SCHEMA)


def test_blank_template_fails_with_field_address(tmp_path: Path) -> None:
    """An untouched answer sheet must identify an incomplete field."""
    root = _task_root(
        tmp_path, (ROOT / "tests/fixtures/submission-template.yaml").read_text(encoding="utf-8")
    )

    with pytest.raises(SubmissionError, match="answers.success_query_id"):
        validate_submission(root / "submission.yaml", SCHEMA)


def test_unpublished_query_identifier_is_rejected(tmp_path: Path) -> None:
    """A well-formed but invented identifier must not pass structural validation."""
    answers = valid_answers()
    mapping = answers["answers"]
    assert isinstance(mapping, dict)
    mapping["miss_query_id"] = "q-not-a-published-query"
    root = _task_root(tmp_path, yaml.safe_dump(answers))

    with pytest.raises(SubmissionError, match="not a published query identifier"):
        validate_submission(root / "submission.yaml", SCHEMA)


def test_same_identifier_twice_is_rejected(tmp_path: Path) -> None:
    """One query cannot be both the recorded success and the recorded miss."""
    answers = valid_answers()
    mapping = answers["answers"]
    assert isinstance(mapping, dict)
    mapping["miss_query_id"] = mapping["success_query_id"]
    root = _task_root(tmp_path, yaml.safe_dump(answers))

    with pytest.raises(SubmissionError, match="must name different queries"):
        validate_submission(root / "submission.yaml", SCHEMA)


def test_malformed_yaml_is_rejected(tmp_path: Path) -> None:
    """A syntactically invalid answer sheet must fail safely."""
    root = _task_root(tmp_path, "answers: [unterminated")

    with pytest.raises(SubmissionError, match="restricted YAML"):
        validate_submission(root / "submission.yaml", SCHEMA)


def test_unexpected_answer_field_is_rejected(tmp_path: Path) -> None:
    """Fields outside the published direct-answer schema must fail validation."""
    answers = valid_answers()
    mapping = answers["answers"]
    assert isinstance(mapping, dict)
    mapping["attributed_stage"] = "not part of this Task's schema"
    root = _task_root(tmp_path, yaml.safe_dump(answers))

    with pytest.raises(SubmissionError, match="Additional properties"):
        validate_submission(root / "submission.yaml", SCHEMA)


def test_exact_sample_copy_is_rejected(tmp_path: Path) -> None:
    """The fictional sample must not be accepted as a student submission."""
    root = _task_root(tmp_path, (ROOT / "submission-sample.yaml").read_text(encoding="utf-8"))

    with pytest.raises(SubmissionError, match="fictional sample"):
        validate_submission(
            root / "submission.yaml",
            SCHEMA,
            sample_path=root / "submission-sample.yaml",
        )


def test_sample_identifiers_are_not_published_queries() -> None:
    """The published sample must not leak a usable answer.

    A sample that happened to name real queries would hand a student two
    identifiers that pass the published-set check without running anything.
    """
    sample = _load_one_document(ROOT / "submission-sample.yaml")
    answers = sample["answers"]
    assert isinstance(answers, dict)
    published = {query.query_id for query in load_queries()}
    assert not published & {answers["success_query_id"], answers["miss_query_id"]}


def test_only_student_editable_paths_are_permitted() -> None:
    """The advisory path gate must accept this Task's editable path and reject others."""
    validate_changed_paths(["submission.yaml"])

    with pytest.raises(SubmissionError, match="src/api"):
        validate_changed_paths(["src/api/routes.py"])

    with pytest.raises(SubmissionError, match="infra/corpus"):
        validate_changed_paths(["infra/corpus/queries.jsonl"])

    with pytest.raises(SubmissionError, match="tests/contract"):
        validate_changed_paths(["tests/contract/test_baseline_answers.py"])


def test_public_entrypoint_reports_an_incomplete_answer_sheet(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Catch a verifier entrypoint that skips the real submission contract."""
    root = _task_root(
        tmp_path, (ROOT / "tests/fixtures/submission-template.yaml").read_text(encoding="utf-8")
    )

    assert main(root, changed_paths=[]) == 1
    assert "answers.success_query_id is incomplete" in capsys.readouterr().err


@pytest.mark.parametrize(
    "unsafe_text",
    [
        "answers: {value: first, value: second}\n",
        "answers: &answer {value: fictional}\n",
        "answers: *missing\n",
        "answers: {<<: {value: fictional}}\n",
        "answers: {value: 2026-09-04}\n",
        "answers: {value: 2026-09-04T12:30:00Z}\n",
        "answers: {value: !custom fictional}\n",
        "answers: {value: !!set {fictional: null}}\n",
        "answers: {1: fictional}\n",
    ],
    ids=[
        "duplicate-key",
        "anchor",
        "alias",
        "merge-key",
        "date",
        "timestamp",
        "custom-tag",
        "set",
        "non-string-key",
    ],
)
def test_non_json_yaml_constructs_are_rejected(tmp_path: Path, unsafe_text: str) -> None:
    """Reject restricted syntax before schema validation can mask a parser defect."""
    submission = tmp_path / "submission.yaml"
    submission.write_text(unsafe_text, encoding="utf-8")

    with pytest.raises(SubmissionError, match="restricted YAML"):
        _load_one_document(submission)


def test_multiple_yaml_documents_are_rejected(tmp_path: Path) -> None:
    """A second document cannot supply or replace the answer mapping."""
    submission = tmp_path / "submission.yaml"
    submission.write_text("answers: {}\n---\nanswers: {}\n", encoding="utf-8")

    with pytest.raises(SubmissionError, match="exactly one YAML mapping"):
        _load_one_document(submission)
