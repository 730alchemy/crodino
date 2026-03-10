"""
Model-based grader for subjective reasoning quality.

Uses Claude as a judge to score responses against rubrics from task YAML files.
Implements structured output for reliable grading scores.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

import anthropic


@dataclass
class DimensionScore:
    """Score for a single rubric dimension."""
    dimension: str
    score: float        # 0.0 – 1.0
    weight: float       # relative weight in overall score
    label: str          # e.g. "excellent" | "good" | "partial" | "poor"
    reasoning: str      # grader's justification


@dataclass
class GradeResult:
    """Complete grading result for one trial."""
    element_id: str
    trial_index: int
    overall_score: float                        # weighted average 0.0 – 1.0
    passed: bool                                # overall_score >= pass_threshold
    dimension_scores: list[DimensionScore] = field(default_factory=list)
    grader_reasoning: str = ""
    raw_response: str = ""
    error: str | None = None


_GRADER_SYSTEM = """\
You are an expert evaluator assessing the quality of AI-generated responses
to cognitive reasoning tasks. Your job is to score each response dimension
according to the provided rubric.

For each rubric dimension, assign one of four score labels:
- "excellent": Full credit — response completely satisfies the criterion
- "good": Mostly satisfies — minor gaps or imprecision
- "partial": Partially satisfies — significant gaps
- "poor": Fails to satisfy — does not meet the criterion

Map labels to numeric scores:
  excellent → 1.0
  good      → 0.75
  partial   → 0.40
  poor      → 0.0

Return a JSON object with this exact schema:
{
  "dimension_scores": [
    {
      "dimension": "<dimension_id>",
      "label": "<excellent|good|partial|poor>",
      "score": <0.0-1.0>,
      "reasoning": "<1-3 sentence justification>"
    }
  ],
  "overall_reasoning": "<2-3 sentence overall assessment>"
}

Be rigorous but fair. Grade on the quality of the response given, not
on whether it matches the reference solution exactly — the reference
solution is one valid answer, not the only valid answer.
"""


_LABEL_TO_SCORE: dict[str, float] = {
    "excellent": 1.0,
    "good": 0.75,
    "partial": 0.40,
    "poor": 0.0,
}


class ModelGrader:
    """
    Uses Claude as a judge to score responses against task rubrics.

    The grader sends a structured prompt to the grader model containing:
    - The original task prompt
    - The response being graded
    - The rubric criteria
    - The reference solution (for calibration)

    It returns a GradeResult with per-dimension scores and an overall score.
    """

    def __init__(
        self,
        model: str = "claude-opus-4-6",
        pass_threshold: float = 0.60,
        api_key: str | None = None,
    ) -> None:
        self.model = model
        self.pass_threshold = pass_threshold
        self._client = anthropic.Anthropic(
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        )

    def grade(
        self,
        task: dict[str, Any],
        response: str,
        trial_index: int = 0,
    ) -> GradeResult:
        """
        Grade a response against a task's rubric.

        Args:
            task: Parsed task YAML dict (must contain element_id, prompt, rubric,
                  reference_solution, success_criteria).
            response: The model's response text to grade.
            trial_index: Which trial this is (for bookkeeping).

        Returns:
            GradeResult with overall score, pass/fail, and per-dimension scores.
        """
        element_id = task.get("element_id", "unknown")
        rubric = task.get("rubric", {})
        if not rubric:
            return GradeResult(
                element_id=element_id,
                trial_index=trial_index,
                overall_score=0.0,
                passed=False,
                error="No rubric found in task definition",
            )

        grader_prompt = self._build_grader_prompt(task, response)

        try:
            api_response = self._client.messages.create(
                model=self.model,
                max_tokens=2048,
                thinking={"type": "adaptive"},
                system=_GRADER_SYSTEM,
                messages=[{"role": "user", "content": grader_prompt}],
            )
            raw_text = next(
                (b.text for b in api_response.content if b.type == "text"), ""
            )
        except anthropic.APIError as exc:
            return GradeResult(
                element_id=element_id,
                trial_index=trial_index,
                overall_score=0.0,
                passed=False,
                error=str(exc),
            )

        return self._parse_grader_response(
            raw_text, element_id, trial_index, rubric, response
        )

    # ------------------------------------------------------------------ #
    # Private helpers                                                       #
    # ------------------------------------------------------------------ #

    def _build_grader_prompt(self, task: dict[str, Any], response: str) -> str:
        rubric = task.get("rubric", {})
        rubric_text = self._format_rubric(rubric)
        criteria_text = "\n".join(
            f"- {c}" for c in task.get("success_criteria", [])
        )
        return (
            f"# Task: {task.get('element_name', task.get('element_id', ''))}\n\n"
            f"## Original prompt given to the model:\n{task.get('prompt', '')}\n\n"
            f"## Success criteria:\n{criteria_text}\n\n"
            f"## Reference solution (one valid answer):\n{task.get('reference_solution', 'N/A')}\n\n"
            f"## Rubric dimensions:\n{rubric_text}\n\n"
            f"## Response to grade:\n{response}\n\n"
            "Now grade this response according to each rubric dimension and return "
            "the JSON object as specified."
        )

    def _format_rubric(self, rubric: dict[str, Any]) -> str:
        lines = []
        for dim_id, dim in rubric.items():
            lines.append(
                f"### {dim_id} (weight: {dim.get('weight', 0.0):.2f})\n"
                f"Criteria: {dim.get('criteria', '')}\n"
                f"Score labels:\n"
                + "\n".join(
                    f"  {label}: {desc}"
                    for label, desc in dim.get("scores", {}).items()
                )
            )
        return "\n\n".join(lines)

    def _parse_grader_response(
        self,
        raw_text: str,
        element_id: str,
        trial_index: int,
        rubric: dict[str, Any],
        response: str,
    ) -> GradeResult:
        # Extract JSON from the response (may be surrounded by markdown fences)
        json_str = self._extract_json(raw_text)
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            return GradeResult(
                element_id=element_id,
                trial_index=trial_index,
                overall_score=0.0,
                passed=False,
                raw_response=response,
                error=f"Grader returned unparseable JSON: {raw_text[:200]}",
            )

        dimension_scores = []
        total_weighted_score = 0.0
        total_weight = 0.0

        for dim_data in data.get("dimension_scores", []):
            dim_id = dim_data.get("dimension", "")
            label = dim_data.get("label", "poor")
            score = _LABEL_TO_SCORE.get(label, dim_data.get("score", 0.0))
            weight = rubric.get(dim_id, {}).get("weight", 1.0)
            dimension_scores.append(
                DimensionScore(
                    dimension=dim_id,
                    score=score,
                    weight=weight,
                    label=label,
                    reasoning=dim_data.get("reasoning", ""),
                )
            )
            total_weighted_score += score * weight
            total_weight += weight

        overall_score = (
            total_weighted_score / total_weight if total_weight > 0 else 0.0
        )

        return GradeResult(
            element_id=element_id,
            trial_index=trial_index,
            overall_score=round(overall_score, 4),
            passed=overall_score >= self.pass_threshold,
            dimension_scores=dimension_scores,
            grader_reasoning=data.get("overall_reasoning", ""),
            raw_response=response,
        )

    @staticmethod
    def _extract_json(text: str) -> str:
        """Extract JSON from text, handling markdown code fences."""
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            # Drop opening fence line and closing fence
            inner = lines[1:]
            if inner and inner[-1].strip() == "```":
                inner = inner[:-1]
            text = "\n".join(inner)
        # Find the first { and last }
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            return text[start : end + 1]
        return text
