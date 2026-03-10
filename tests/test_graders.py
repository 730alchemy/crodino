"""
Tests for the CodeGrader and ModelGrader.

ModelGrader tests mock the Anthropic API to avoid real API calls.
CodeGrader tests are fully deterministic.
"""

from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from graders.code_grader import (
    CheckResult,
    CodeGradeResult,
    CodeGrader,
    register_default_checks,
)
from graders.model_grader import DimensionScore, GradeResult, ModelGrader


# ------------------------------------------------------------------ #
# Fixtures                                                             #
# ------------------------------------------------------------------ #

SAMPLE_TASK = {
    "element_id": "logical_coherence",
    "element_name": "Logical Coherence",
    "prompt": "Find the contradiction in these statements.",
    "success_criteria": ["Identifies contradiction", "Suggests revision"],
    "rubric": {
        "contradiction_identification": {
            "weight": 0.40,
            "criteria": "Identifies the logical contradiction",
            "scores": {
                "excellent": "Precisely identifies contradiction",
                "good": "Identifies contradiction with minor issues",
                "partial": "Partially identifies contradiction",
                "poor": "Does not identify contradiction",
            },
        },
        "revision_quality": {
            "weight": 0.60,
            "criteria": "Quality of suggested revision",
            "scores": {
                "excellent": "Clear, precise revision",
                "good": "Good revision with minor gaps",
                "partial": "Partial revision",
                "poor": "No revision or incorrect",
            },
        },
    },
    "reference_solution": (
        "The contradiction is between statement A (rare earths needed) "
        "and statement B (always better for environment). Revise B to "
        "acknowledge conditional environmental benefits."
    ),
    "grader_type": "model",
}

GOOD_RESPONSE = (
    "The contradiction exists between Statements A and B. Statement A notes that "
    "solar panels require rare earth minerals with environmental costs, while "
    "Statement B makes an unconditional claim that renewable energy is always better "
    "for the environment. This is a direct inconsistency. "
    "I suggest revising Statement B to: 'Renewable energy typically has lower lifecycle "
    "environmental impact than fossil fuels, though manufacturing processes vary.' "
    "This revision acknowledges the nuance without making an absolute claim."
)

SHORT_RESPONSE = "It's wrong."


# ------------------------------------------------------------------ #
# CodeGrader: global built-in checks                                   #
# ------------------------------------------------------------------ #

class TestCodeGraderBuiltins:
    def setup_method(self):
        self.grader = CodeGrader(pass_threshold=0.60)

    def test_passes_good_response(self):
        result = self.grader.grade(SAMPLE_TASK, GOOD_RESPONSE)
        assert isinstance(result, CodeGradeResult)
        assert result.element_id == "logical_coherence"
        assert result.overall_score > 0.0

    def test_fails_empty_response(self):
        result = self.grader.grade(SAMPLE_TASK, "")
        names = [c.name for c in result.checks]
        assert "response_not_empty" in names
        empty_check = next(c for c in result.checks if c.name == "response_not_empty")
        assert not empty_check.passed

    def test_fails_short_response(self):
        result = self.grader.grade(SAMPLE_TASK, "Hi.")
        empty_check = next(c for c in result.checks if c.name == "response_not_empty")
        assert not empty_check.passed

    def test_global_checks_always_run(self):
        result = self.grader.grade(SAMPLE_TASK, GOOD_RESPONSE)
        names = [c.name for c in result.checks]
        assert "response_not_empty" in names
        assert "no_placeholder_text" in names

    def test_trial_index_stored(self):
        result = self.grader.grade(SAMPLE_TASK, GOOD_RESPONSE, trial_index=2)
        assert result.trial_index == 2

    def test_passed_field_reflects_threshold(self):
        result = self.grader.grade(SAMPLE_TASK, GOOD_RESPONSE)
        assert result.passed == (result.overall_score >= 0.60)


# ------------------------------------------------------------------ #
# CodeGrader: factory check functions                                  #
# ------------------------------------------------------------------ #

class TestKeywordCheck:
    def test_finds_any_keyword(self):
        check = CodeGrader.make_keyword_check("test", ["foo", "bar"])
        result = check("I found foo in here", {})
        assert result.passed
        assert result.score == 1.0

    def test_fails_no_keyword(self):
        check = CodeGrader.make_keyword_check("test", ["foo", "bar"])
        result = check("Nothing relevant", {})
        assert not result.passed
        assert result.score == 0.0

    def test_require_all(self):
        check = CodeGrader.make_keyword_check("test", ["foo", "bar"], require_all=True)
        result = check("I found foo here", {})
        assert not result.passed

        result2 = check("I found foo and bar here", {})
        assert result2.passed

    def test_case_insensitive_by_default(self):
        check = CodeGrader.make_keyword_check("test", ["Contradiction"])
        result = check("There is a contradiction here", {})
        assert result.passed

    def test_case_sensitive_option(self):
        check = CodeGrader.make_keyword_check("test", ["Foo"], case_sensitive=True)
        result = check("foo is here", {})
        assert not result.passed

        result2 = check("Foo is here", {})
        assert result2.passed


class TestLengthCheck:
    def test_passes_within_bounds(self):
        check = CodeGrader.make_length_check("len", min_chars=10, max_chars=100)
        result = check("A" * 50, {})
        assert result.passed

    def test_fails_too_short(self):
        check = CodeGrader.make_length_check("len", min_chars=100)
        result = check("short", {})
        assert not result.passed

    def test_fails_too_long(self):
        check = CodeGrader.make_length_check("len", max_chars=10)
        result = check("This response is definitely too long", {})
        assert not result.passed


class TestJsonValidCheck:
    def test_valid_json(self):
        check = CodeGrader.make_json_valid_check()
        result = check('Here is my answer: {"key": "value", "num": 42}', {})
        assert result.passed

    def test_invalid_json(self):
        check = CodeGrader.make_json_valid_check()
        result = check('{"key": invalid}', {})
        assert not result.passed

    def test_no_json_block(self):
        check = CodeGrader.make_json_valid_check()
        result = check("No JSON here at all.", {})
        assert not result.passed


class TestNumericAnswerCheck:
    def test_finds_exact_number(self):
        check = CodeGrader.make_numeric_answer_check("answer", expected=56.0)
        result = check("The answer is 56 units.", {})
        assert result.passed

    def test_finds_number_within_tolerance(self):
        check = CodeGrader.make_numeric_answer_check("answer", expected=3.14, tolerance=0.01)
        result = check("Approximately 3.14159 radians.", {})
        assert result.passed

    def test_fails_wrong_number(self):
        check = CodeGrader.make_numeric_answer_check("answer", expected=42.0, tolerance=0.5)
        result = check("The value is 100.", {})
        assert not result.passed


class TestSectionCheck:
    def test_all_sections_present(self):
        check = CodeGrader.make_section_check("secs", ["Part A", "Part B", "Part C"])
        result = check("Part A: ... Part B: ... Part C: ...", {})
        assert result.passed
        assert result.score == 1.0

    def test_partial_sections(self):
        check = CodeGrader.make_section_check("secs", ["Part A", "Part B", "Part C"])
        result = check("Part A: ... Part B: ...", {})
        assert not result.passed
        assert result.score > 0.0  # partial credit

    def test_no_sections(self):
        check = CodeGrader.make_section_check("secs", ["Part A", "Part B"])
        result = check("Nothing here.", {})
        assert not result.passed
        assert result.score == 0.0


# ------------------------------------------------------------------ #
# CodeGrader: element-specific checks                                  #
# ------------------------------------------------------------------ #

class TestElementSpecificChecks:
    def test_register_and_run_element_check(self):
        grader = CodeGrader()
        check = CodeGrader.make_keyword_check("custom", ["alpha"])
        grader.register_check("test_element", check, weight=1.0)

        task = {**SAMPLE_TASK, "element_id": "test_element"}
        result = grader.grade(task, "alpha is here", trial_index=0)
        custom = next((c for c in result.checks if c.name == "custom"), None)
        assert custom is not None
        assert custom.passed

    def test_element_check_not_run_for_other_elements(self):
        grader = CodeGrader()
        check = CodeGrader.make_keyword_check("custom_check", ["alpha"])
        grader.register_check("other_element", check, weight=1.0)

        result = grader.grade(SAMPLE_TASK, "alpha is here")  # element_id = logical_coherence
        names = [c.name for c in result.checks]
        assert "custom_check" not in names

    def test_register_default_checks(self):
        grader = CodeGrader()
        register_default_checks(grader)

        task = {**SAMPLE_TASK, "element_id": "logical_coherence"}
        result = grader.grade(task, GOOD_RESPONSE)
        names = [c.name for c in result.checks]
        assert "mentions_contradiction" in names

    def test_verification_check_finds_error(self):
        grader = CodeGrader()
        register_default_checks(grader)

        task = {**SAMPLE_TASK, "element_id": "verification"}
        response = (
            "The error is in Step 5: dividing both sides by (a-b). "
            "Since a = b, a - b = 0, so this division by zero is invalid."
        )
        result = grader.grade(task, response)
        error_check = next(
            (c for c in result.checks if c.name == "identifies_division_by_zero"), None
        )
        assert error_check is not None
        assert error_check.passed


# ------------------------------------------------------------------ #
# ModelGrader: initialization                                          #
# ------------------------------------------------------------------ #

class TestModelGraderInit:
    def test_default_model(self):
        grader = ModelGrader(api_key="fake-key")
        assert grader.model == "claude-opus-4-6"

    def test_default_threshold(self):
        grader = ModelGrader(api_key="fake-key")
        assert grader.pass_threshold == 0.60

    def test_custom_threshold(self):
        grader = ModelGrader(pass_threshold=0.80, api_key="fake-key")
        assert grader.pass_threshold == 0.80


# ------------------------------------------------------------------ #
# GradeResult: scoring logic                                           #
# ------------------------------------------------------------------ #

class TestGradeResult:
    def test_weighted_score_stored(self):
        dims = [
            DimensionScore(
                dimension="dim_a",
                label="excellent",
                score=1.0,
                weight=0.60,
                reasoning="Perfect",
            ),
            DimensionScore(
                dimension="dim_b",
                label="good",
                score=0.75,
                weight=0.40,
                reasoning="Good",
            ),
        ]
        expected = 1.0 * 0.60 + 0.75 * 0.40
        result = GradeResult(
            element_id="test",
            trial_index=0,
            overall_score=expected,
            passed=True,
            dimension_scores=dims,
        )
        assert abs(result.overall_score - expected) < 0.001

    def test_pass_fail_stored(self):
        result_pass = GradeResult(
            element_id="test", trial_index=0, overall_score=0.75, passed=True,
        )
        result_fail = GradeResult(
            element_id="test", trial_index=0, overall_score=0.40, passed=False,
        )
        assert result_pass.passed
        assert not result_fail.passed

    def test_error_field(self):
        result = GradeResult(
            element_id="test", trial_index=0, overall_score=0.0, passed=False,
            error="Something went wrong",
        )
        assert result.error == "Something went wrong"


# ------------------------------------------------------------------ #
# ModelGrader: API interaction (mocked)                                #
# ------------------------------------------------------------------ #

def _make_api_response(json_content: dict) -> MagicMock:
    """Create a mock Anthropic API response with a JSON text block."""
    mock_response = MagicMock()
    mock_text_block = MagicMock()
    mock_text_block.type = "text"
    mock_text_block.text = json.dumps(json_content)
    mock_response.content = [mock_text_block]
    return mock_response


class TestModelGraderApi:
    def _grade_with_mock(self, fake_json: dict) -> GradeResult:
        with patch("graders.model_grader.anthropic.Anthropic") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client
            mock_client.messages.create.return_value = _make_api_response(fake_json)

            grader = ModelGrader(api_key="fake-key")
            return grader.grade(SAMPLE_TASK, GOOD_RESPONSE, trial_index=0)

    def test_grade_returns_grade_result(self):
        fake_json = {
            "overall_reasoning": "Good response",
            "dimension_scores": [
                {
                    "dimension": "contradiction_identification",
                    "label": "good",
                    "score": 0.75,
                    "reasoning": "Identified the main contradiction",
                },
                {
                    "dimension": "revision_quality",
                    "label": "excellent",
                    "score": 1.0,
                    "reasoning": "Excellent revision proposed",
                },
            ],
        }
        result = self._grade_with_mock(fake_json)
        assert isinstance(result, GradeResult)
        assert result.element_id == "logical_coherence"
        assert result.trial_index == 0
        assert 0.0 <= result.overall_score <= 1.0
        assert len(result.dimension_scores) == 2

    def test_grade_computes_weighted_score(self):
        # excellent=1.0 × weight=0.40, partial=0.40 × weight=0.60
        fake_json = {
            "overall_reasoning": "OK",
            "dimension_scores": [
                {
                    "dimension": "contradiction_identification",
                    "label": "excellent",
                    "score": 1.0,
                    "reasoning": "Perfect",
                },
                {
                    "dimension": "revision_quality",
                    "label": "partial",
                    "score": 0.40,
                    "reasoning": "Weak revision",
                },
            ],
        }
        result = self._grade_with_mock(fake_json)
        expected = 1.0 * 0.40 + 0.40 * 0.60  # = 0.40 + 0.24 = 0.64
        assert abs(result.overall_score - expected) < 0.01

    def test_grade_handles_api_error(self):
        with patch("graders.model_grader.anthropic.Anthropic") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client
            mock_client.messages.create.side_effect = anthropic_api_error()

            grader = ModelGrader(api_key="fake-key")
            result = grader.grade(SAMPLE_TASK, GOOD_RESPONSE)

        assert result.error is not None
        assert result.overall_score == 0.0
        assert not result.passed

    def test_grade_handles_malformed_json(self):
        with patch("graders.model_grader.anthropic.Anthropic") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client
            mock_text = MagicMock()
            mock_text.type = "text"
            mock_text.text = "This is not JSON at all!"
            mock_response = MagicMock()
            mock_response.content = [mock_text]
            mock_client.messages.create.return_value = mock_response

            grader = ModelGrader(api_key="fake-key")
            result = grader.grade(SAMPLE_TASK, GOOD_RESPONSE)

        assert result.error is not None
        assert result.overall_score == 0.0


def anthropic_api_error():
    """Create a mock APIError for testing error handling."""
    import anthropic as anthropic_module
    # Create an APIError instance that will be caught by the grader
    return anthropic_module.APIStatusError(
        message="API error",
        response=MagicMock(status_code=500, headers={}),
        body={"error": "server error"},
    )
