# Cognitive Reasoning Eval Suite

An evaluation suite for measuring cognitive reasoning capabilities in large language models, based on the taxonomy from Kargupta et al. (2024), "Cognitive Foundations for Reasoning and Their Manifestation in LLMs" (arXiv:2511.16660).

## Overview

This suite evaluates 28 cognitive elements across four categories:

| Category | Count | Description |
|---|---|---|
| Reasoning Invariants | 4 | Structural properties that must hold in any valid reasoning |
| Metacognitive Controls | 5 | Self-monitoring, evaluation, and strategy-selection capabilities |
| Reasoning Representations | 7 | Mental structures used to organize and represent knowledge |
| Reasoning Operations | 12 | Transformations applied to representations during reasoning |

Each cognitive element has a task (eval prompt + rubric + reference solution), a model-based grader, and a code-based grader.

## Taxonomy

**Reasoning Invariants**: `logical_coherence`, `compositionality`, `invariance`, `systematicity`

**Metacognitive Controls**: `self_awareness`, `evaluation`, `strategy_selection`, `goal_management`, `resource_allocation`

**Reasoning Representations**: `propositional_representation`, `sequential_organization`, `causal_organization`, `taxonomic_organization`, `analogical_representation`, `spatial_representation`, `temporal_organization`

**Reasoning Operations**: `pattern_recognition`, `abstraction`, `decomposition_and_integration`, `representational_restructuring`, `forward_chaining`, `backward_chaining`, `verification`, `backtracking`, `knowledge_alignment`, `selective_attention`, `adaptive_detail_management`, `ordinal_organization`

The full taxonomy with definitions is in `taxonomy/cognitive_elements.yaml`.

## Running Evals

### Prerequisites

```bash
pip install anthropic pyyaml
export ANTHROPIC_API_KEY="your-key-here"
```

### Run tests

```bash
python -m pytest tests/ -v
```

### Quick smoke test (fast, no model grader)

```bash
python -m harness.runner --config config/fast.yaml
```

### Full eval suite

```bash
python -m harness.runner --config config/default.yaml
```

## Interpreting Results

Results are saved to `results/` as JSON. Each run produces:
- `summary_{run_id}.json` — metrics for all tasks
- `transcripts_{run_id}.json` — full model responses and grades

**pass@k** — probability that at least one trial in k attempts passes. Measures peak capability.

**pass^k** — probability that all k trials pass. Measures reliability and consistency.

Formula (unbiased estimator from Chen et al. 2021): `pass@k = 1 - C(n-c, k) / C(n, k)`

**Score interpretation:**
- `pass@1 > 0.8` — reliable in a single attempt
- `pass@1 in [0.5, 0.8)` — capable but inconsistent
- `pass@1 < 0.5` — struggles with this element

## Configuration

| File | Use case |
|---|---|
| `config/default.yaml` | Full eval, both graders, 3 trials, Opus |
| `config/fast.yaml` | Development: 1 trial, code grader only, Haiku |

Key settings:

```yaml
target_model: "claude-opus-4-6"
grader:
  model: "claude-opus-4-6"
  pass_threshold: 0.60
  use_model_grader: true
  use_code_grader: true
eval:
  n_trials: 3
  k_values: [1, 3, 5, 10]
  task_filter: null            # List of element_ids, or null for all
```

## Graders

**Model Grader** (`graders/model_grader.py`): Uses Claude-as-judge with the task rubric. Scores each rubric dimension as `excellent` (1.0), `good` (0.75), `partial` (0.40), or `poor` (0.0). Overall score is the weighted average.

**Code Grader** (`graders/code_grader.py`): Deterministic structural checks — keyword presence, numeric answer correctness, section headers, response length. Each task has element-specific checks in `register_default_checks()`.

## Adding New Tasks

1. Create `tasks/<category>/<element_id>.yaml` with required fields: `element_id`, `element_name`, `category`, `prompt` (>=100 chars), `success_criteria`, `rubric` (>=2 dimensions, weights summing to 1.0, each with excellent/good/partial/poor scores), `reference_solution`, `grader_type`.

2. Add the element to `taxonomy/cognitive_elements.yaml`.

3. Optionally add structural checks in `graders/code_grader.py::register_default_checks()`.

4. Verify: `python -m pytest tests/ -v`

## Project Structure

```
taxonomy/cognitive_elements.yaml   All 28 elements with definitions
tasks/
  reasoning_invariants/            4 tasks
  metacognitive_controls/          5 tasks
  reasoning_representations/       7 tasks
  reasoning_operations/            12 tasks
graders/
  model_grader.py                  LLM-as-judge grader
  code_grader.py                   Deterministic structural checks
harness/
  runner.py                        Eval orchestrator
  metrics.py                       pass@k / pass^k computation
config/
  default.yaml                     Full eval configuration
  fast.yaml                        Development configuration
tests/                             Pytest test suite (106 tests)
results/                           Output directory
```

## References

- Kargupta et al. (2024). Cognitive Foundations for Reasoning and Their Manifestation in LLMs. arXiv:2511.16660.
- Chen et al. (2021). Evaluating Large Language Models Trained on Code. arXiv:2107.03374. (Source of the pass@k estimator.)
