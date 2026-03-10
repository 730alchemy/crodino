"""
Tests for the cognitive elements taxonomy YAML.

Validates:
- File exists and is valid YAML
- Exactly 28 cognitive elements are present
- Each element has all required fields
- Elements are distributed across the 4 required categories
- Category IDs match declared categories
"""

from pathlib import Path
import pytest
import yaml


TAXONOMY_PATH = Path(__file__).parent.parent / "taxonomy" / "cognitive_elements.yaml"

REQUIRED_ELEMENT_FIELDS = {"id", "name", "category", "definition", "why_it_matters"}
REQUIRED_CATEGORIES = {
    "reasoning_invariants",
    "metacognitive_controls",
    "reasoning_representations",
    "reasoning_operations",
}

# Expected element counts per category (from the paper's taxonomy)
EXPECTED_CATEGORY_COUNTS = {
    "reasoning_invariants": 4,
    "metacognitive_controls": 5,
    "reasoning_representations": 7,
    "reasoning_operations": 12,
}

EXPECTED_TOTAL_ELEMENTS = 28


@pytest.fixture(scope="module")
def taxonomy():
    """Load the taxonomy YAML once for all tests."""
    assert TAXONOMY_PATH.exists(), f"Taxonomy file not found: {TAXONOMY_PATH}"
    with TAXONOMY_PATH.open() as f:
        data = yaml.safe_load(f)
    assert data is not None, "Taxonomy YAML is empty"
    return data


class TestTaxonomyStructure:
    """Tests for top-level taxonomy structure."""

    def test_has_elements_key(self, taxonomy):
        assert "elements" in taxonomy, "Taxonomy must have an 'elements' key"

    def test_has_categories_key(self, taxonomy):
        assert "categories" in taxonomy, "Taxonomy must have a 'categories' key"

    def test_total_element_count(self, taxonomy):
        elements = taxonomy["elements"]
        assert len(elements) == EXPECTED_TOTAL_ELEMENTS, (
            f"Expected {EXPECTED_TOTAL_ELEMENTS} elements, found {len(elements)}"
        )

    def test_categories_declared(self, taxonomy):
        declared = {cat["id"] for cat in taxonomy["categories"]}
        assert declared == REQUIRED_CATEGORIES, (
            f"Categories mismatch. Expected: {REQUIRED_CATEGORIES}, Got: {declared}"
        )


class TestElementFields:
    """Tests that each element has all required fields with non-empty values."""

    @pytest.fixture(autouse=True)
    def elements(self, taxonomy):
        self._elements = taxonomy["elements"]

    def test_all_elements_have_id(self):
        for el in self._elements:
            assert "id" in el and el["id"], f"Element missing 'id': {el}"

    def test_all_elements_have_name(self):
        for el in self._elements:
            assert "name" in el and el["name"], f"Element {el.get('id')} missing 'name'"

    def test_all_elements_have_category(self):
        for el in self._elements:
            assert "category" in el and el["category"], (
                f"Element {el.get('id')} missing 'category'"
            )

    def test_all_elements_have_definition(self):
        for el in self._elements:
            assert "definition" in el and el["definition"], (
                f"Element {el.get('id')} missing 'definition'"
            )

    def test_all_elements_have_why_it_matters(self):
        for el in self._elements:
            assert "why_it_matters" in el and el["why_it_matters"], (
                f"Element {el.get('id')} missing 'why_it_matters'"
            )

    def test_all_ids_unique(self):
        ids = [el["id"] for el in self._elements]
        assert len(ids) == len(set(ids)), f"Duplicate element IDs found: {ids}"

    def test_all_categories_valid(self):
        for el in self._elements:
            assert el.get("category") in REQUIRED_CATEGORIES, (
                f"Element {el.get('id')} has invalid category: {el.get('category')}"
            )

    def test_definitions_are_substantial(self):
        """Each definition should be at least 20 words."""
        for el in self._elements:
            definition = str(el.get("definition", ""))
            word_count = len(definition.split())
            assert word_count >= 20, (
                f"Definition for {el.get('id')} is too short ({word_count} words)"
            )


class TestCategoryCounts:
    """Tests that elements are distributed correctly across categories."""

    @pytest.fixture(autouse=True)
    def elements(self, taxonomy):
        self._elements = taxonomy["elements"]

    def test_reasoning_invariants_count(self):
        count = sum(
            1 for el in self._elements
            if el.get("category") == "reasoning_invariants"
        )
        assert count == EXPECTED_CATEGORY_COUNTS["reasoning_invariants"], (
            f"Expected 4 reasoning invariants, found {count}"
        )

    def test_metacognitive_controls_count(self):
        count = sum(
            1 for el in self._elements
            if el.get("category") == "metacognitive_controls"
        )
        assert count == EXPECTED_CATEGORY_COUNTS["metacognitive_controls"], (
            f"Expected 5 metacognitive controls, found {count}"
        )

    def test_reasoning_representations_count(self):
        count = sum(
            1 for el in self._elements
            if el.get("category") == "reasoning_representations"
        )
        assert count == EXPECTED_CATEGORY_COUNTS["reasoning_representations"], (
            f"Expected 7 reasoning representations, found {count}"
        )

    def test_reasoning_operations_count(self):
        count = sum(
            1 for el in self._elements
            if el.get("category") == "reasoning_operations"
        )
        assert count == EXPECTED_CATEGORY_COUNTS["reasoning_operations"], (
            f"Expected 12 reasoning operations, found {count}"
        )


class TestSpecificElements:
    """Tests that specific important elements are present and correct."""

    @pytest.fixture(autouse=True)
    def element_map(self, taxonomy):
        self._elements = {el["id"]: el for el in taxonomy["elements"]}

    def test_logical_coherence_present(self):
        assert "logical_coherence" in self._elements

    def test_self_awareness_is_metacognitive(self):
        el = self._elements.get("self_awareness", {})
        assert el.get("category") == "metacognitive_controls"

    def test_backtracking_is_operation(self):
        el = self._elements.get("backtracking", {})
        assert el.get("category") == "reasoning_operations"

    def test_causal_organization_is_representation(self):
        el = self._elements.get("causal_organization", {})
        assert el.get("category") == "reasoning_representations"

    def test_all_28_known_elements_present(self):
        known_ids = {
            "logical_coherence", "compositionality", "productivity", "conceptual_processing",
            "self_awareness", "context_awareness", "strategy_selection", "goal_management",
            "evaluation",
            "sequential_organization", "hierarchical_organization", "network_organization",
            "ordinal_organization", "causal_organization", "temporal_organization",
            "spatial_organization",
            "context_alignment", "knowledge_alignment", "verification", "selective_attention",
            "adaptive_detail_management", "decomposition_and_integration",
            "representational_restructuring", "pattern_recognition", "abstraction",
            "forward_chaining", "backward_chaining", "backtracking",
        }
        missing = known_ids - set(self._elements.keys())
        assert not missing, f"Missing expected elements: {missing}"
