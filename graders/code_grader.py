"""
Code-based (deterministic) grader for structural and format checks.

Provides fast, reproducible grading for aspects of responses that can be
checked programmatically: JSON validity, required fields, numeric constraints,
presence of required keywords, response length, etc.

These graders are intentionally narrow — they check structure and format,
not reasoning quality (which is the model grader's domain).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class CheckResult:
    """Result of a single code-based check."""
    name: str
    passed: bool
    score: float        # 0.0 or 1.0 (binary checks)
    weight: float
    message: str


@dataclass
class CodeGradeResult:
    """Aggregate result from the code grader."""
    element_id: str
    trial_index: int
    overall_score: float
    passed: bool
    checks: list[CheckResult] = field(default_factory=list)
    error: str | None = None


# Type alias for check functions
CheckFn = Callable[[str, dict[str, Any]], CheckResult]


class CodeGrader:
    """
    Runs deterministic structural/format checks on a model response.

    Each check is a function that takes (response_text, task_dict) and
    returns a CheckResult. Checks are registered per-element or globally.

    Built-in checks (always available):
    - response_not_empty: Ensures the response has non-trivial content
    - no_placeholder_text: Ensures the response doesn't contain common
      placeholder text indicating the model didn't actually answer

    Element-specific checks can be added via register_check().
    """

    _PLACEHOLDER_PATTERNS = [
        r"\[your answer here\]",
        r"\[insert",
        r"\.\.\.\s*$",
        r"TODO",
        r"N/A",
    ]

    def __init__(self, pass_threshold: float = 0.60) -> None:
        self.pass_threshold = pass_threshold
        # element_id -> list of (check_fn, weight)
        self._element_checks: dict[str, list[tuple[CheckFn, float]]] = {}
        # Global checks applied to all elements
        self._global_checks: list[tuple[CheckFn, float]] = [
            (self._check_not_empty, 0.1),
            (self._check_no_placeholders, 0.1),
        ]

    def register_check(
        self,
        element_id: str,
        check_fn: CheckFn,
        weight: float = 1.0,
    ) -> None:
        """Register an element-specific check function."""
        if element_id not in self._element_checks:
            self._element_checks[element_id] = []
        self._element_checks[element_id].append((check_fn, weight))

    def grade(
        self,
        task: dict[str, Any],
        response: str,
        trial_index: int = 0,
    ) -> CodeGradeResult:
        """
        Run all applicable checks on a response.

        Args:
            task: Parsed task YAML dict.
            response: The model response text to check.
            trial_index: Trial index for bookkeeping.

        Returns:
            CodeGradeResult with individual check results and overall score.
        """
        element_id = task.get("element_id", "unknown")
        checks: list[CheckResult] = []

        # Run global checks
        for fn, weight in self._global_checks:
            try:
                result = fn(response, task)
                result.weight = weight
                checks.append(result)
            except Exception as exc:
                checks.append(CheckResult(
                    name=fn.__name__,
                    passed=False,
                    score=0.0,
                    weight=weight,
                    message=f"Check raised exception: {exc}",
                ))

        # Run element-specific checks
        for fn, weight in self._element_checks.get(element_id, []):
            try:
                result = fn(response, task)
                result.weight = weight
                checks.append(result)
            except Exception as exc:
                checks.append(CheckResult(
                    name=fn.__name__,
                    passed=False,
                    score=0.0,
                    weight=weight,
                    message=f"Check raised exception: {exc}",
                ))

        total_weight = sum(c.weight for c in checks)
        weighted_score = sum(c.score * c.weight for c in checks)
        overall_score = weighted_score / total_weight if total_weight > 0 else 0.0

        return CodeGradeResult(
            element_id=element_id,
            trial_index=trial_index,
            overall_score=round(overall_score, 4),
            passed=overall_score >= self.pass_threshold,
            checks=checks,
        )

    # ------------------------------------------------------------------ #
    # Built-in global checks                                               #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _check_not_empty(response: str, task: dict[str, Any]) -> CheckResult:
        passed = len(response.strip()) >= 50
        return CheckResult(
            name="response_not_empty",
            passed=passed,
            score=1.0 if passed else 0.0,
            weight=0.1,
            message="OK" if passed else f"Response too short ({len(response.strip())} chars)",
        )

    @staticmethod
    def _check_no_placeholders(response: str, task: dict[str, Any]) -> CheckResult:
        patterns = CodeGrader._PLACEHOLDER_PATTERNS
        found = [p for p in patterns if re.search(p, response, re.IGNORECASE)]
        passed = len(found) == 0
        return CheckResult(
            name="no_placeholder_text",
            passed=passed,
            score=1.0 if passed else 0.0,
            weight=0.1,
            message="OK" if passed else f"Found placeholder patterns: {found}",
        )

    # ------------------------------------------------------------------ #
    # Reusable check factory functions                                     #
    # ------------------------------------------------------------------ #

    @staticmethod
    def make_keyword_check(
        name: str,
        keywords: list[str],
        require_all: bool = False,
        case_sensitive: bool = False,
    ) -> CheckFn:
        """
        Create a check that verifies required keywords appear in the response.

        Args:
            name: Human-readable check name.
            keywords: List of required keywords or phrases.
            require_all: If True, ALL keywords must be present. If False, ANY one.
            case_sensitive: Whether to use case-sensitive matching.
        """
        def check(response: str, task: dict[str, Any]) -> CheckResult:
            text = response if case_sensitive else response.lower()
            kws = keywords if case_sensitive else [k.lower() for k in keywords]
            found = [k for k in kws if k in text]
            if require_all:
                passed = len(found) == len(kws)
                msg = (
                    f"All required keywords found: {kws}"
                    if passed
                    else f"Missing: {[k for k in kws if k not in found]}"
                )
            else:
                passed = len(found) > 0
                msg = (
                    f"Found keyword(s): {found}"
                    if passed
                    else f"None of {kws} found in response"
                )
            return CheckResult(
                name=name,
                passed=passed,
                score=1.0 if passed else 0.0,
                weight=1.0,
                message=msg,
            )
        return check

    @staticmethod
    def make_length_check(
        name: str,
        min_chars: int = 0,
        max_chars: int = 1_000_000,
    ) -> CheckFn:
        """Create a check that verifies response length is within bounds."""
        def check(response: str, task: dict[str, Any]) -> CheckResult:
            length = len(response.strip())
            passed = min_chars <= length <= max_chars
            return CheckResult(
                name=name,
                passed=passed,
                score=1.0 if passed else 0.0,
                weight=1.0,
                message=(
                    f"Length {length} within [{min_chars}, {max_chars}]"
                    if passed
                    else f"Length {length} outside [{min_chars}, {max_chars}]"
                ),
            )
        return check

    @staticmethod
    def make_json_valid_check(name: str = "valid_json") -> CheckFn:
        """Create a check that verifies the response contains valid JSON."""
        def check(response: str, task: dict[str, Any]) -> CheckResult:
            # Try to find a JSON block
            start = response.find("{")
            end = response.rfind("}")
            if start == -1 or end == -1:
                return CheckResult(
                    name=name, passed=False, score=0.0, weight=1.0,
                    message="No JSON object found in response",
                )
            try:
                json.loads(response[start:end + 1])
                return CheckResult(
                    name=name, passed=True, score=1.0, weight=1.0,
                    message="Valid JSON found",
                )
            except json.JSONDecodeError as e:
                return CheckResult(
                    name=name, passed=False, score=0.0, weight=1.0,
                    message=f"Invalid JSON: {e}",
                )
        return check

    @staticmethod
    def make_numeric_answer_check(
        name: str,
        expected: float,
        tolerance: float = 0.01,
    ) -> CheckFn:
        """
        Create a check that verifies a specific numeric answer appears
        in the response within a tolerance.
        """
        def check(response: str, task: dict[str, Any]) -> CheckResult:
            # Extract all numbers from the response
            numbers = re.findall(r"-?\d+(?:\.\d+)?", response)
            for num_str in numbers:
                try:
                    if abs(float(num_str) - expected) <= tolerance:
                        return CheckResult(
                            name=name, passed=True, score=1.0, weight=1.0,
                            message=f"Found expected value ~{expected} (found {num_str})",
                        )
                except ValueError:
                    continue
            return CheckResult(
                name=name, passed=False, score=0.0, weight=1.0,
                message=f"Expected ~{expected} not found in response numbers: {numbers[:10]}",
            )
        return check

    @staticmethod
    def make_section_check(
        name: str,
        required_sections: list[str],
        case_sensitive: bool = False,
    ) -> CheckFn:
        """
        Create a check that verifies required section headers or labels
        appear in the response (e.g., 'Q1:', 'Part A', 'Step 1').
        """
        def check(response: str, task: dict[str, Any]) -> CheckResult:
            text = response if case_sensitive else response.lower()
            sections = required_sections if case_sensitive else [
                s.lower() for s in required_sections
            ]
            missing = [s for s in sections if s not in text]
            passed = len(missing) == 0
            return CheckResult(
                name=name,
                passed=passed,
                score=1.0 if passed else max(0.0, (len(sections) - len(missing)) / len(sections)),
                weight=1.0,
                message=(
                    "All required sections present"
                    if passed
                    else f"Missing sections: {missing}"
                ),
            )
        return check


# ------------------------------------------------------------------ #
# Pre-built element-specific code graders                             #
# ------------------------------------------------------------------ #

def register_default_checks(grader: CodeGrader) -> None:
    """Register element-specific structural checks for all 28 elements."""

    # Logical coherence: must mention contradiction
    grader.register_check(
        "logical_coherence",
        CodeGrader.make_keyword_check(
            "mentions_contradiction",
            ["contradiction", "contradict", "inconsistent", "inconsistency"],
        ),
        weight=0.5,
    )

    # Compositionality: must show Q1, Q2, Q3
    grader.register_check(
        "compositionality",
        CodeGrader.make_section_check(
            "question_sections",
            ["question 1", "question 2", "question 3"],
        ),
        weight=0.3,
    )

    # Self-awareness: must show confidence levels
    grader.register_check(
        "self_awareness",
        CodeGrader.make_keyword_check(
            "confidence_expressed",
            ["confidence", "high", "low", "uncertain", "unsure", "don't know"],
        ),
        weight=0.4,
    )

    # Verification: must find the error in step 5
    grader.register_check(
        "verification",
        CodeGrader.make_keyword_check(
            "identifies_division_by_zero",
            ["division by zero", "divide by zero", "a-b = 0", "a - b = 0",
             "a=b", "zero denominator"],
            require_all=False,
        ),
        weight=0.5,
    )

    # Backtracking: must contain backtrack/dead end language
    grader.register_check(
        "backtracking",
        CodeGrader.make_keyword_check(
            "shows_backtrack",
            ["backtrack", "back", "fails", "dead end", "try again",
             "cannot", "go back", "undo"],
            require_all=False,
        ),
        weight=0.4,
    )

    # Forward chaining: must show rule firings
    grader.register_check(
        "forward_chaining",
        CodeGrader.make_keyword_check(
            "shows_rule_firings",
            ["rule", "fires", "step", "derived", "new fact", "chain"],
            require_all=False,
        ),
        weight=0.3,
    )

    # Backward chaining: must show backward reasoning
    grader.register_check(
        "backward_chaining",
        CodeGrader.make_keyword_check(
            "shows_backward_reasoning",
            ["goal", "backward", "sub-goal", "prerequisite", "which rule", "prove"],
            require_all=False,
        ),
        weight=0.3,
    )

    # Sequential organization: must identify at least some stages
    grader.register_check(
        "sequential_organization",
        CodeGrader.make_keyword_check(
            "mentions_stages",
            ["stage", "step", "parallel", "sequence", "depends"],
        ),
        weight=0.3,
    )

    # Pattern recognition: must give correct answer for Set 1 (56)
    grader.register_check(
        "pattern_recognition",
        CodeGrader.make_numeric_answer_check(
            "set1_correct_answer", expected=56.0, tolerance=0.0
        ),
        weight=0.3,
    )

    # Representational restructuring: must show all three problems
    grader.register_check(
        "representational_restructuring",
        CodeGrader.make_section_check(
            "all_problems_addressed",
            ["problem a", "problem b", "problem c"],
        ),
        weight=0.3,
    )

    # Decomposition: must show sub-problem structure
    grader.register_check(
        "decomposition_and_integration",
        CodeGrader.make_keyword_check(
            "shows_decomposition",
            ["sub-problem", "sub problem", "sector", "decompose", "decomposition"],
        ),
        weight=0.3,
    )

    # Abstraction: must address all 5 levels
    grader.register_check(
        "abstraction",
        CodeGrader.make_section_check(
            "addresses_all_levels",
            ["level 1", "level 2", "level 3"],
        ),
        weight=0.3,
    )
