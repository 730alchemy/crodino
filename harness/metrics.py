"""
Metrics computation for the cognitive reasoning eval suite.

Implements pass@k and pass^k metrics as described in:
"Demystifying Evals for AI Agents" (Anthropic, 2026)

pass@k  — probability that at least one trial in k attempts passes.
          Approaches 1.0 as k increases.

pass^k  — probability that ALL k trials pass.
          Approaches 0.0 as k increases (requires consistency).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class TaskMetrics:
    """Metrics for a single task across all its trials."""
    element_id: str
    n_trials: int
    n_passed: int
    per_trial_scores: list[float]
    pass_rate: float        # n_passed / n_trials
    pass_at_k: dict[int, float] = field(default_factory=dict)
    pass_hat_k: dict[int, float] = field(default_factory=dict)
    mean_score: float = 0.0
    std_score: float = 0.0


@dataclass
class SuiteMetrics:
    """Aggregated metrics across all tasks in the eval suite."""
    n_tasks: int
    n_trials_per_task: int
    task_metrics: list[TaskMetrics]
    overall_pass_rate: float        # mean pass rate across tasks
    pass_at_k: dict[int, float]     # mean pass@k across tasks
    pass_hat_k: dict[int, float]    # mean pass^k across tasks


def compute_pass_at_k(n_trials: int, n_passed: int, k: int) -> float:
    """
    Compute pass@k: probability of at least one success in k attempts.

    Uses the closed-form estimator from OpenAI's HumanEval paper:
      pass@k = 1 - C(n-c, k) / C(n, k)

    where n = total trials, c = number that passed.

    This is the unbiased estimator. When k > n, returns 1.0 if any trial
    passed, else 0.0.

    Args:
        n_trials: Total number of trials run.
        n_passed: Number of trials that passed.
        k: The k value for pass@k.

    Returns:
        Estimated pass@k probability in [0.0, 1.0].
    """
    if k > n_trials:
        # Cannot compute with fewer trials than k; fall back to binary
        return 1.0 if n_passed > 0 else 0.0

    n_failed = n_trials - n_passed

    # Probability that ALL k selected trials fail:
    # C(n_failed, k) / C(n_trials, k) using the log-space calculation
    if n_failed < k:
        # Cannot select k failures from fewer failures → guaranteed ≥1 success
        return 1.0

    # Compute using log to avoid overflow with large factorials
    log_prob_all_fail = (
        _log_comb(n_failed, k) - _log_comb(n_trials, k)
    )
    prob_all_fail = math.exp(log_prob_all_fail)
    return max(0.0, min(1.0, 1.0 - prob_all_fail))


def compute_pass_hat_k(n_trials: int, n_passed: int, k: int) -> float:
    """
    Compute pass^k: probability that ALL k trials succeed.

    Estimated as: (pass_rate)^k using the observed per-trial pass rate.

    This is conservative: if k > n_trials, we use the observed rate and
    extrapolate.

    Args:
        n_trials: Total number of trials run.
        n_passed: Number of trials that passed.
        k: The k value for pass^k.

    Returns:
        Estimated pass^k probability in [0.0, 1.0].
    """
    if n_trials == 0:
        return 0.0
    per_trial_rate = n_passed / n_trials
    return per_trial_rate ** k


def aggregate_results(
    task_results: dict[str, list[float]],
    k_values: list[int] | None = None,
) -> SuiteMetrics:
    """
    Aggregate per-task trial scores into suite-level metrics.

    Args:
        task_results: Dict mapping element_id → list of per-trial scores
                      (0.0 = fail, 1.0 = pass, or fractional).
        k_values: Which k values to compute for pass@k and pass^k.
                  Defaults to [1, 3, 5, 10].

    Returns:
        SuiteMetrics with all computed metrics.
    """
    if k_values is None:
        k_values = [1, 3, 5, 10]

    pass_threshold = 0.60  # Score ≥ threshold counts as a pass
    task_metrics_list: list[TaskMetrics] = []

    for element_id, scores in task_results.items():
        n_trials = len(scores)
        n_passed = sum(1 for s in scores if s >= pass_threshold)
        pass_rate = n_passed / n_trials if n_trials > 0 else 0.0
        mean_score = sum(scores) / n_trials if n_trials > 0 else 0.0
        variance = (
            sum((s - mean_score) ** 2 for s in scores) / n_trials
            if n_trials > 0
            else 0.0
        )
        std_score = math.sqrt(variance)

        pass_at_k = {
            k: compute_pass_at_k(n_trials, n_passed, k) for k in k_values
        }
        pass_hat_k = {
            k: compute_pass_hat_k(n_trials, n_passed, k) for k in k_values
        }

        task_metrics_list.append(TaskMetrics(
            element_id=element_id,
            n_trials=n_trials,
            n_passed=n_passed,
            per_trial_scores=scores,
            pass_rate=pass_rate,
            pass_at_k=pass_at_k,
            pass_hat_k=pass_hat_k,
            mean_score=mean_score,
            std_score=std_score,
        ))

    n_tasks = len(task_metrics_list)
    n_trials_per_task = (
        task_metrics_list[0].n_trials if task_metrics_list else 0
    )

    overall_pass_rate = (
        sum(tm.pass_rate for tm in task_metrics_list) / n_tasks
        if n_tasks > 0
        else 0.0
    )

    suite_pass_at_k: dict[int, float] = {}
    suite_pass_hat_k: dict[int, float] = {}
    for k in k_values:
        suite_pass_at_k[k] = (
            sum(tm.pass_at_k[k] for tm in task_metrics_list) / n_tasks
            if n_tasks > 0
            else 0.0
        )
        suite_pass_hat_k[k] = (
            sum(tm.pass_hat_k[k] for tm in task_metrics_list) / n_tasks
            if n_tasks > 0
            else 0.0
        )

    return SuiteMetrics(
        n_tasks=n_tasks,
        n_trials_per_task=n_trials_per_task,
        task_metrics=task_metrics_list,
        overall_pass_rate=overall_pass_rate,
        pass_at_k=suite_pass_at_k,
        pass_hat_k=suite_pass_hat_k,
    )


def _log_comb(n: int, k: int) -> float:
    """Compute log(C(n, k)) using log-gamma for numerical stability."""
    if k < 0 or k > n:
        return float("-inf")
    if k == 0 or k == n:
        return 0.0
    return (
        math.lgamma(n + 1)
        - math.lgamma(k + 1)
        - math.lgamma(n - k + 1)
    )
