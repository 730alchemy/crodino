"""
Tests for the eval harness: metrics computation and runner loading logic.

Runner tests mock the Anthropic API and file system where needed.
Metrics tests are purely computational.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from harness.metrics import (
    SuiteMetrics,
    TaskMetrics,
    aggregate_results,
    compute_pass_at_k,
    compute_pass_hat_k,
)


# ------------------------------------------------------------------ #
# pass@k metric                                                        #
# ------------------------------------------------------------------ #

class TestPassAtK:
    def test_zero_passed_gives_zero(self):
        assert compute_pass_at_k(n_trials=5, n_passed=0, k=1) == 0.0

    def test_all_passed_gives_one(self):
        assert compute_pass_at_k(n_trials=5, n_passed=5, k=1) == 1.0

    def test_all_passed_higher_k(self):
        assert compute_pass_at_k(n_trials=5, n_passed=5, k=5) == 1.0

    def test_k_equals_one_equals_pass_rate(self):
        # pass@1 = observed pass rate
        result = compute_pass_at_k(n_trials=10, n_passed=6, k=1)
        assert abs(result - 0.6) < 0.001

    def test_k_greater_than_n_returns_binary(self):
        # k > n_trials: fall back to 1 if any passed, 0 otherwise
        assert compute_pass_at_k(n_trials=3, n_passed=1, k=10) == 1.0
        assert compute_pass_at_k(n_trials=3, n_passed=0, k=10) == 0.0

    def test_increases_monotonically_with_k(self):
        # More attempts should not decrease pass@k
        scores = [
            compute_pass_at_k(n_trials=10, n_passed=5, k=k)
            for k in [1, 2, 3, 5, 7, 10]
        ]
        for i in range(len(scores) - 1):
            assert scores[i] <= scores[i + 1] + 1e-9

    def test_n_failed_equals_zero(self):
        # If n_failed < k → guaranteed success → 1.0
        result = compute_pass_at_k(n_trials=5, n_passed=4, k=2)
        # n_failed=1 < k=2 → return 1.0
        assert result == 1.0

    def test_result_in_unit_interval(self):
        for n in range(1, 11):
            for c in range(0, n + 1):
                for k in range(1, n + 1):
                    val = compute_pass_at_k(n, c, k)
                    assert 0.0 <= val <= 1.0, f"Out of range: n={n}, c={c}, k={k} → {val}"

    def test_known_value(self):
        # n=3, c=2, k=2: P(at least 1 success in 2 draws from {pass, pass, fail})
        # P(all fail) = C(1,2)/C(3,2) but C(1,2)=0 → P=1.0
        result = compute_pass_at_k(n_trials=3, n_passed=2, k=2)
        assert result == 1.0

    def test_known_value_2(self):
        # n=4, c=1, k=2: C(3,2)/C(4,2) = 3/6 = 0.5 → pass@2 = 0.5
        result = compute_pass_at_k(n_trials=4, n_passed=1, k=2)
        assert abs(result - 0.5) < 0.001


# ------------------------------------------------------------------ #
# pass^k metric                                                        #
# ------------------------------------------------------------------ #

class TestPassHatK:
    def test_zero_passed_gives_zero(self):
        assert compute_pass_hat_k(n_trials=5, n_passed=0, k=1) == 0.0

    def test_all_passed_gives_one(self):
        assert compute_pass_hat_k(n_trials=5, n_passed=5, k=1) == 1.0

    def test_decreases_monotonically_with_k(self):
        # Higher k requires more consistent success → lower probability
        scores = [
            compute_pass_hat_k(n_trials=10, n_passed=7, k=k)
            for k in [1, 2, 3, 5, 10]
        ]
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1] - 1e-9

    def test_equals_pass_rate_at_k1(self):
        result = compute_pass_hat_k(n_trials=10, n_passed=7, k=1)
        assert abs(result - 0.7) < 0.001

    def test_equals_pass_rate_squared_at_k2(self):
        result = compute_pass_hat_k(n_trials=10, n_passed=8, k=2)
        assert abs(result - 0.64) < 0.001

    def test_zero_trials_returns_zero(self):
        result = compute_pass_hat_k(n_trials=0, n_passed=0, k=1)
        assert result == 0.0


# ------------------------------------------------------------------ #
# aggregate_results                                                    #
# ------------------------------------------------------------------ #

class TestAggregateResults:
    def test_basic_aggregation(self):
        task_results = {
            "task_a": [1.0, 1.0, 0.0],
            "task_b": [0.0, 0.0, 0.0],
        }
        metrics = aggregate_results(task_results, k_values=[1, 3])
        assert metrics.n_tasks == 2
        assert len(metrics.task_metrics) == 2

    def test_overall_pass_rate(self):
        task_results = {
            "task_a": [1.0, 1.0],      # 100% pass rate
            "task_b": [0.0, 0.0],      # 0% pass rate
        }
        metrics = aggregate_results(task_results, k_values=[1])
        assert abs(metrics.overall_pass_rate - 0.5) < 0.001

    def test_task_metrics_fields(self):
        task_results = {"my_task": [1.0, 0.8, 0.5]}
        metrics = aggregate_results(task_results, k_values=[1, 3])
        tm = metrics.task_metrics[0]

        assert tm.element_id == "my_task"
        assert tm.n_trials == 3
        assert isinstance(tm.pass_rate, float)
        assert isinstance(tm.mean_score, float)
        assert isinstance(tm.std_score, float)
        assert 1 in tm.pass_at_k
        assert 3 in tm.pass_at_k
        assert 1 in tm.pass_hat_k

    def test_pass_at_k_in_suite_metrics(self):
        task_results = {
            "task_a": [1.0, 1.0, 1.0],
        }
        metrics = aggregate_results(task_results, k_values=[1, 3])
        assert metrics.pass_at_k[1] == 1.0
        assert metrics.pass_at_k[3] == 1.0

    def test_pass_threshold_applied(self):
        # Scores at exactly threshold (0.60) count as pass
        task_results = {"task_a": [0.60, 0.59, 0.61]}
        metrics = aggregate_results(task_results, k_values=[1])
        tm = metrics.task_metrics[0]
        assert tm.n_passed == 2  # 0.60 and 0.61 pass; 0.59 does not

    def test_empty_tasks(self):
        metrics = aggregate_results({}, k_values=[1, 3])
        assert metrics.n_tasks == 0
        assert metrics.overall_pass_rate == 0.0

    def test_default_k_values_used_when_none(self):
        task_results = {"task_a": [1.0, 0.5, 0.8]}
        metrics = aggregate_results(task_results)  # No k_values argument
        # Default k_values = [1, 3, 5, 10]
        assert 1 in metrics.pass_at_k
        assert 3 in metrics.pass_at_k
        assert 5 in metrics.pass_at_k
        assert 10 in metrics.pass_at_k

    def test_mean_and_std_computed_correctly(self):
        scores = [0.8, 0.6, 1.0]
        task_results = {"t": scores}
        metrics = aggregate_results(task_results, k_values=[1])
        tm = metrics.task_metrics[0]
        expected_mean = sum(scores) / len(scores)
        expected_std = math.sqrt(
            sum((s - expected_mean) ** 2 for s in scores) / len(scores)
        )
        assert abs(tm.mean_score - expected_mean) < 0.001
        assert abs(tm.std_score - expected_std) < 0.001


# ------------------------------------------------------------------ #
# EvalRunner: task loading (no API required)                           #
# ------------------------------------------------------------------ #

class TestEvalRunnerTaskLoading:
    """Tests for task loading logic — no real API calls needed."""

    def _make_runner(self, **kwargs):
        from unittest.mock import patch
        from harness.runner import EvalRunner, RunConfig

        config = RunConfig(**kwargs)
        # Patch anthropic in both the runner and model_grader modules
        with patch("harness.runner.anthropic.Anthropic"), \
             patch("graders.model_grader.anthropic.Anthropic"):
            runner = EvalRunner(config)
        return runner

    def test_loads_tasks_from_tasks_dir(self):
        """Verify the tasks directory contains YAML files for all 28 elements."""
        runner = self._make_runner(
            target_model="claude-opus-4-6", n_trials=1, tasks_dir="tasks"
        )
        tasks = runner.load_tasks()

        assert len(tasks) > 0, "No tasks loaded from tasks/ directory"
        assert len(tasks) == 28, (
            f"Expected 28 tasks, got {len(tasks)}: "
            f"{[t['element_id'] for t in tasks]}"
        )

    def test_loaded_tasks_have_required_fields(self):
        runner = self._make_runner(n_trials=1, tasks_dir="tasks")
        tasks = runner.load_tasks()

        required = {"element_id", "prompt", "rubric", "reference_solution"}
        for task in tasks:
            missing = required - set(task.keys())
            assert not missing, (
                f"Task {task.get('element_id')} missing fields: {missing}"
            )

    def test_task_filter_restricts_loaded_tasks(self):
        runner = self._make_runner(
            n_trials=1,
            tasks_dir="tasks",
            task_filter=["logical_coherence", "backtracking"],
        )
        tasks = runner.load_tasks()

        ids = [t["element_id"] for t in tasks]
        assert set(ids) == {"logical_coherence", "backtracking"}
