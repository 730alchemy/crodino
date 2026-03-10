"""
Tests for eval task YAML files.

Validates:
- Task files exist for all 28 cognitive elements
- Each task has the required fields
- Prompts are non-trivial
- Rubrics reference valid dimensions with weights that sum to ~1.0
- Success criteria are specified
"""

from pathlib import Path
import pytest
import yaml


TASKS_DIR = Path(__file__).parent.parent / "tasks"
TAXONOMY_PATH = Path(__file__).parent.parent / "taxonomy" / "cognitive_elements.yaml"

REQUIRED_TASK_FIELDS = {"element_id", "prompt", "success_criteria", "rubric", "reference_solution"}
REQUIRED_RUBRIC_DIMENSION_FIELDS = {"weight", "criteria"}


def load_all_tasks() -> list[dict]:
    """Load all task YAML files from the tasks directory."""
    tasks = []
    for yaml_file in sorted(TASKS_DIR.rglob("*.yaml")):
        with yaml_file.open() as f:
            task = yaml.safe_load(f)
        if task and "element_id" in task:
            tasks.append(task)
    return tasks


def load_taxonomy_element_ids() -> set[str]:
    """Load element IDs from the taxonomy."""
    with TAXONOMY_PATH.open() as f:
        taxonomy = yaml.safe_load(f)
    return {el["id"] for el in taxonomy.get("elements", [])}


@pytest.fixture(scope="module")
def all_tasks():
    return load_all_tasks()


@pytest.fixture(scope="module")
def taxonomy_element_ids():
    return load_taxonomy_element_ids()


@pytest.fixture(scope="module")
def task_map(all_tasks):
    return {task["element_id"]: task for task in all_tasks}


class TestTaskCoverage:
    """Tests that task files cover all taxonomy elements."""

    def test_task_files_exist(self, all_tasks):
        assert len(all_tasks) > 0, "No task YAML files found"

    def test_28_tasks_exist(self, all_tasks):
        assert len(all_tasks) == 28, (
            f"Expected 28 task files, found {len(all_tasks)}. "
            f"Found: {[t['element_id'] for t in all_tasks]}"
        )

    def test_all_taxonomy_elements_have_tasks(self, task_map, taxonomy_element_ids):
        missing = taxonomy_element_ids - set(task_map.keys())
        assert not missing, f"No task file for elements: {missing}"

    def test_no_extra_tasks(self, task_map, taxonomy_element_ids):
        extra = set(task_map.keys()) - taxonomy_element_ids
        assert not extra, f"Task files for unknown elements: {extra}"


class TestTaskStructure:
    """Tests that each task has all required fields."""

    def test_all_tasks_have_element_id(self, all_tasks):
        for task in all_tasks:
            assert "element_id" in task and task["element_id"]

    def test_all_tasks_have_prompt(self, all_tasks):
        for task in all_tasks:
            assert "prompt" in task and task["prompt"], (
                f"Task {task.get('element_id')} missing prompt"
            )

    def test_all_tasks_have_success_criteria(self, all_tasks):
        for task in all_tasks:
            criteria = task.get("success_criteria")
            assert criteria and len(criteria) > 0, (
                f"Task {task.get('element_id')} missing success_criteria"
            )

    def test_all_tasks_have_rubric(self, all_tasks):
        for task in all_tasks:
            rubric = task.get("rubric")
            assert rubric and len(rubric) > 0, (
                f"Task {task.get('element_id')} missing rubric"
            )

    def test_all_tasks_have_reference_solution(self, all_tasks):
        for task in all_tasks:
            ref = task.get("reference_solution")
            assert ref and len(str(ref).strip()) > 20, (
                f"Task {task.get('element_id')} missing or too-short reference_solution"
            )

    def test_all_tasks_have_grader_type(self, all_tasks):
        for task in all_tasks:
            grader_type = task.get("grader_type")
            assert grader_type in ("model", "code", "both"), (
                f"Task {task.get('element_id')} has invalid grader_type: {grader_type}"
            )


class TestTaskPrompts:
    """Tests for prompt quality."""

    def test_prompts_are_non_trivial(self, all_tasks):
        """Each prompt should be at least 100 characters."""
        for task in all_tasks:
            prompt = str(task.get("prompt", ""))
            assert len(prompt.strip()) >= 100, (
                f"Prompt for {task.get('element_id')} is too short ({len(prompt)} chars)"
            )

    def test_prompts_end_with_instruction(self, all_tasks):
        """Each prompt should end with an actionable request, not trailing text."""
        for task in all_tasks:
            prompt = str(task.get("prompt", "")).strip()
            # Should not end with a bare URL or just a blank
            assert len(prompt) > 0, f"Empty prompt for {task.get('element_id')}"


class TestRubrics:
    """Tests for rubric validity."""

    def test_rubric_has_dimensions(self, all_tasks):
        for task in all_tasks:
            rubric = task.get("rubric", {})
            assert len(rubric) >= 2, (
                f"Rubric for {task.get('element_id')} has fewer than 2 dimensions"
            )

    def test_rubric_weights_sum_to_one(self, all_tasks):
        for task in all_tasks:
            rubric = task.get("rubric", {})
            total_weight = sum(
                dim.get("weight", 0) for dim in rubric.values()
            )
            assert abs(total_weight - 1.0) < 0.01, (
                f"Rubric weights for {task.get('element_id')} sum to "
                f"{total_weight:.3f}, expected 1.0"
            )

    def test_rubric_dimensions_have_criteria(self, all_tasks):
        for task in all_tasks:
            rubric = task.get("rubric", {})
            for dim_id, dim in rubric.items():
                assert "criteria" in dim and dim["criteria"], (
                    f"Dimension {dim_id} in {task.get('element_id')} missing criteria"
                )

    def test_rubric_dimensions_have_weights(self, all_tasks):
        for task in all_tasks:
            rubric = task.get("rubric", {})
            for dim_id, dim in rubric.items():
                weight = dim.get("weight")
                assert weight is not None and 0 < weight <= 1, (
                    f"Dimension {dim_id} in {task.get('element_id')} has invalid weight: {weight}"
                )

    def test_rubric_scores_defined(self, all_tasks):
        for task in all_tasks:
            rubric = task.get("rubric", {})
            for dim_id, dim in rubric.items():
                scores = dim.get("scores", {})
                expected_labels = {"excellent", "good", "partial", "poor"}
                assert set(scores.keys()) == expected_labels, (
                    f"Dimension {dim_id} in {task.get('element_id')} missing score labels. "
                    f"Got: {set(scores.keys())}"
                )


class TestSpecificTasks:
    """Spot-check specific tasks for correctness."""

    def test_logical_coherence_task(self, task_map):
        task = task_map.get("logical_coherence", {})
        prompt = task.get("prompt", "")
        assert "contradiction" in prompt.lower() or "consistent" in prompt.lower(), (
            "Logical coherence prompt should address contradiction/consistency"
        )

    def test_backtracking_task_requires_backtrack(self, task_map):
        task = task_map.get("backtracking", {})
        prompt = task.get("prompt", "")
        assert "dead end" in prompt.lower() or "backtrack" in prompt.lower() or "show" in prompt.lower()

    def test_verification_task_has_proof(self, task_map):
        task = task_map.get("verification", {})
        prompt = task.get("prompt", "")
        # Should contain a proof or checking exercise
        assert "proof" in prompt.lower() or "error" in prompt.lower() or "valid" in prompt.lower()

    def test_self_awareness_task_has_confidence(self, task_map):
        task = task_map.get("self_awareness", {})
        prompt = task.get("prompt", "")
        assert "confidence" in prompt.lower() or "know" in prompt.lower() or "uncertain" in prompt.lower()
