"""CLI entry point: python -m harness --config config/fast.yaml"""

from __future__ import annotations

import argparse

from dotenv import load_dotenv
import yaml

from harness.runner import EvalRunner, RunConfig


def parse_config(path: str) -> RunConfig:
    with open(path) as f:
        raw = yaml.safe_load(f)

    grader = raw.get("grader", {})
    eval_ = raw.get("eval", {})
    output = raw.get("output", {})
    tasks = raw.get("tasks", {})

    return RunConfig(
        target_model=raw.get("target_model", "claude-opus-4-6"),
        grader_model=grader.get("model", "claude-opus-4-6"),
        n_trials=eval_.get("n_trials", 3),
        k_values=eval_.get("k_values", [1, 3, 5]),
        pass_threshold=grader.get("pass_threshold", 0.60),
        output_dir=output.get("results_dir", "results"),
        use_model_grader=grader.get("use_model_grader", True),
        use_code_grader=grader.get("use_code_grader", True),
        max_tokens=eval_.get("max_tokens", 4096),
        task_filter=eval_.get("task_filter"),
        save_transcripts=output.get("save_transcripts", True),
        tasks_dir=tasks.get("dir", "tasks"),
    )


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Run the Cognitive Reasoning Eval Suite")
    parser.add_argument("--config", required=True, help="Path to YAML config file")
    args = parser.parse_args()

    config = parse_config(args.config)
    runner = EvalRunner(config)
    runner.load_tasks()
    runner.run()


if __name__ == "__main__":
    main()
