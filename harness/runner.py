"""
Eval harness runner for the cognitive reasoning eval suite.

Orchestrates:
- Loading task definitions from YAML files
- Running the target model on each task (multiple trials)
- Collecting full transcripts
- Applying graders (model-based and/or code-based)
- Computing pass@k and pass^k metrics
- Saving results to the results/ directory
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import anthropic
import yaml

from graders.code_grader import CodeGrader, register_default_checks
from graders.model_grader import GradeResult, ModelGrader
from harness.metrics import SuiteMetrics, aggregate_results


@dataclass
class Transcript:
    """Full record of one trial."""
    element_id: str
    trial_index: int
    prompt: str
    response: str
    usage: dict[str, int]
    model_grade: GradeResult | None = None
    code_grade: Any | None = None
    timestamp: str = ""


@dataclass
class RunConfig:
    """Configuration for an eval run."""
    target_model: str = "claude-opus-4-6"
    grader_model: str = "claude-opus-4-6"
    n_trials: int = 3
    k_values: list[int] = field(default_factory=lambda: [1, 3, 5])
    pass_threshold: float = 0.60
    output_dir: str = "results"
    use_model_grader: bool = True
    use_code_grader: bool = True
    max_tokens: int = 4096
    task_filter: list[str] | None = None   # If set, only run these element_ids
    save_transcripts: bool = True
    tasks_dir: str = "tasks"


class EvalRunner:
    """
    Main evaluation harness.

    Loads tasks, runs the target model, grades responses, and
    aggregates metrics.

    Usage:
        config = RunConfig(target_model="claude-opus-4-6", n_trials=3)
        runner = EvalRunner(config)
        suite_metrics = runner.run()
    """

    def __init__(self, config: RunConfig) -> None:
        self.config = config
        self._client = anthropic.Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY", "")
        )
        self._model_grader = (
            ModelGrader(
                model=config.grader_model,
                pass_threshold=config.pass_threshold,
            )
            if config.use_model_grader
            else None
        )
        self._code_grader: CodeGrader | None = None
        if config.use_code_grader:
            self._code_grader = CodeGrader(pass_threshold=config.pass_threshold)
            register_default_checks(self._code_grader)

        self._tasks: list[dict[str, Any]] = []
        self._transcripts: list[Transcript] = []

    def load_tasks(self) -> list[dict[str, Any]]:
        """Load all task YAML files from the tasks directory."""
        tasks_path = Path(self.config.tasks_dir)
        tasks = []
        for yaml_file in sorted(tasks_path.rglob("*.yaml")):
            with yaml_file.open() as f:
                task = yaml.safe_load(f)
            if task and "element_id" in task:
                # Apply filter if configured
                if self.config.task_filter is None or task["element_id"] in self.config.task_filter:
                    tasks.append(task)
        self._tasks = tasks
        return tasks

    def run(self) -> SuiteMetrics:
        """
        Run the full eval suite.

        Returns:
            SuiteMetrics with pass@k and pass^k for all tasks.
        """
        if not self._tasks:
            self.load_tasks()

        print(f"Running eval suite: {len(self._tasks)} tasks × {self.config.n_trials} trials")
        print(f"Target model: {self.config.target_model}")
        print("-" * 60)

        task_results: dict[str, list[float]] = {}

        for task in self._tasks:
            element_id = task["element_id"]
            scores: list[float] = []
            print(f"\n[{element_id}] Running {self.config.n_trials} trials...")

            for trial_idx in range(self.config.n_trials):
                transcript = self._run_trial(task, trial_idx)
                self._transcripts.append(transcript)

                # Determine score for this trial
                score = self._compute_trial_score(transcript)
                scores.append(score)

                status = "✓ pass" if score >= self.config.pass_threshold else "✗ fail"
                print(f"  Trial {trial_idx + 1}: score={score:.3f} {status}")

            task_results[element_id] = scores

        suite_metrics = aggregate_results(task_results, k_values=self.config.k_values)

        self._save_results(suite_metrics, task_results)
        self._print_summary(suite_metrics)

        return suite_metrics

    def run_task(
        self,
        task: dict[str, Any],
        n_trials: int | None = None,
    ) -> dict[str, list[float]]:
        """Run a single task and return its scores."""
        n = n_trials or self.config.n_trials
        element_id = task["element_id"]
        scores = []
        for trial_idx in range(n):
            transcript = self._run_trial(task, trial_idx)
            self._transcripts.append(transcript)
            scores.append(self._compute_trial_score(transcript))
        return {element_id: scores}

    # ------------------------------------------------------------------ #
    # Private methods                                                       #
    # ------------------------------------------------------------------ #

    def _run_trial(self, task: dict[str, Any], trial_idx: int) -> Transcript:
        """Execute one trial: call the target model and collect response."""
        prompt = task.get("prompt", "")
        element_id = task.get("element_id", "unknown")

        try:
            response = self._client.messages.create(
                model=self.config.target_model,
                max_tokens=self.config.max_tokens,
                thinking={"type": "adaptive"},
                messages=[{"role": "user", "content": prompt}],
            )
            response_text = next(
                (b.text for b in response.content if b.type == "text"), ""
            )
            usage = {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            }
        except anthropic.APIError as exc:
            response_text = f"[API ERROR: {exc}]"
            usage = {}

        transcript = Transcript(
            element_id=element_id,
            trial_index=trial_idx,
            prompt=prompt,
            response=response_text,
            usage=usage,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )

        # Grade the response
        if self._model_grader and not response_text.startswith("[API ERROR"):
            transcript.model_grade = self._model_grader.grade(task, response_text, trial_idx)

        if self._code_grader:
            transcript.code_grade = self._code_grader.grade(task, response_text, trial_idx)

        return transcript

    def _compute_trial_score(self, transcript: Transcript) -> float:
        """
        Combine model and code grader scores into a single trial score.

        When both graders are active, the model grader is weighted 80% and
        the code grader 20% (since model graders capture reasoning quality
        while code graders only check structural properties).
        """
        scores = []
        weights = []

        if transcript.model_grade and transcript.model_grade.error is None:
            scores.append(transcript.model_grade.overall_score)
            weights.append(0.8)

        if transcript.code_grade and transcript.code_grade.error is None:
            scores.append(transcript.code_grade.overall_score)
            weights.append(0.2)

        if not scores:
            return 0.0

        total_weight = sum(weights)
        return sum(s * w for s, w in zip(scores, weights)) / total_weight

    def _save_results(
        self,
        suite_metrics: SuiteMetrics,
        task_results: dict[str, list[float]],
    ) -> None:
        """Save transcripts and metrics to the results directory."""
        if not self.config.save_transcripts:
            return

        output_dir = Path(self.config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        run_id = time.strftime("%Y%m%d_%H%M%S")

        # Save summary metrics
        summary = {
            "run_id": run_id,
            "target_model": self.config.target_model,
            "n_trials": self.config.n_trials,
            "n_tasks": suite_metrics.n_tasks,
            "overall_pass_rate": suite_metrics.overall_pass_rate,
            "pass_at_k": suite_metrics.pass_at_k,
            "pass_hat_k": suite_metrics.pass_hat_k,
            "task_results": {
                tm.element_id: {
                    "pass_rate": tm.pass_rate,
                    "mean_score": tm.mean_score,
                    "std_score": tm.std_score,
                    "pass_at_k": tm.pass_at_k,
                    "pass_hat_k": tm.pass_hat_k,
                    "scores": tm.per_trial_scores,
                }
                for tm in suite_metrics.task_metrics
            },
        }

        summary_path = output_dir / f"summary_{run_id}.json"
        with summary_path.open("w") as f:
            json.dump(summary, f, indent=2)

        # Save transcripts
        transcripts_data = []
        for t in self._transcripts:
            record: dict[str, Any] = {
                "element_id": t.element_id,
                "trial_index": t.trial_index,
                "timestamp": t.timestamp,
                "prompt": t.prompt,
                "response": t.response,
                "usage": t.usage,
            }
            if t.model_grade:
                record["model_grade"] = {
                    "overall_score": t.model_grade.overall_score,
                    "passed": t.model_grade.passed,
                    "grader_reasoning": t.model_grade.grader_reasoning,
                    "dimension_scores": [
                        {
                            "dimension": ds.dimension,
                            "score": ds.score,
                            "label": ds.label,
                            "reasoning": ds.reasoning,
                        }
                        for ds in t.model_grade.dimension_scores
                    ],
                    "error": t.model_grade.error,
                }
            if t.code_grade:
                record["code_grade"] = {
                    "overall_score": t.code_grade.overall_score,
                    "passed": t.code_grade.passed,
                    "checks": [
                        {
                            "name": c.name,
                            "passed": c.passed,
                            "score": c.score,
                            "message": c.message,
                        }
                        for c in t.code_grade.checks
                    ],
                }
            transcripts_data.append(record)

        transcripts_path = output_dir / f"transcripts_{run_id}.json"
        with transcripts_path.open("w") as f:
            json.dump(transcripts_data, f, indent=2)

        print(f"\nResults saved:")
        print(f"  Summary:     {summary_path}")
        print(f"  Transcripts: {transcripts_path}")

    def _print_summary(self, suite_metrics: SuiteMetrics) -> None:
        """Print a human-readable summary of results."""
        print("\n" + "=" * 60)
        print("EVAL SUITE RESULTS")
        print("=" * 60)
        print(f"Tasks: {suite_metrics.n_tasks}")
        print(f"Trials per task: {suite_metrics.n_trials_per_task}")
        print(f"Overall pass rate: {suite_metrics.overall_pass_rate:.1%}")
        print()
        print("pass@k  (probability of ≥1 success in k attempts):")
        for k, v in sorted(suite_metrics.pass_at_k.items()):
            print(f"  pass@{k:2d}: {v:.3f}")
        print()
        print("pass^k  (probability that all k attempts succeed):")
        for k, v in sorted(suite_metrics.pass_hat_k.items()):
            print(f"  pass^{k:2d}: {v:.3f}")
        print()

        # Per-task breakdown
        print("Per-task pass rates:")
        for tm in sorted(suite_metrics.task_metrics, key=lambda x: x.pass_rate, reverse=True):
            bar = "█" * round(tm.pass_rate * 20)
            print(f"  {tm.element_id:<35} {tm.pass_rate:.0%} {bar}")
