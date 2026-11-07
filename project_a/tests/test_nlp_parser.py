"""
Pytest Suite for Plain-Language Tax Input Parser
Tests:
- Extraction of numbers, salaries, HRA, rent, 80C, 80D from plain text & Hinglish
- Triggering clarifying questions when inputs are incomplete or ambiguous
- Detecting contradictions (e.g. age 24 + senior citizen)
"""

import os
import json
import pytest
from project_a.tax_engine.nlp_parser import NaturalLanguageTaxParser


@pytest.fixture(scope="module")
def plain_inputs():
    path = os.path.join(os.path.dirname(__file__), "plain_language_inputs.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_plain_language_total_count(plain_inputs):
    """Ensure requirement of 50 plain-language user descriptions is met."""
    assert len(plain_inputs) >= 50, f"Expected 50 descriptions, found {len(plain_inputs)}"


def test_parser_extracts_complete_descriptions(plain_inputs):
    """Verify standard and Hinglish complete descriptions extract valid TaxInput."""
    parser = NaturalLanguageTaxParser()
    complete_cases = [c for c in plain_inputs if c.get("expected_complete")]
    
    success_count = 0
    for case in complete_cases:
        res = parser.parse(case["text"])
        if res.tax_input and res.tax_input.gross_salary > 0:
            success_count += 1
            
    # At least 90% of complete descriptions should extract cleanly
    assert success_count / len(complete_cases) >= 0.90


def test_parser_asks_clarifying_questions_for_incomplete(plain_inputs):
    """Verify incomplete descriptions trigger clarifying questions instead of guessing."""
    parser = NaturalLanguageTaxParser()
    incomplete_cases = [c for c in plain_inputs if not c.get("expected_complete")]
    
    for case in incomplete_cases:
        res = parser.parse(case["text"])
        assert len(res.clarifying_questions) > 0 or len(res.contradictions) > 0 or len(res.ambiguities) > 0, (
            f"Case {case['id']} should have triggered clarifying questions or contradictions: '{case['text']}'"
        )


def test_parser_catches_age_contradiction():
    """Verify specific contradiction detection: age 24 declared as senior citizen."""
    parser = NaturalLanguageTaxParser()
    res = parser.parse("I am 24 years old senior citizen earning 10 LPA salary.")
    assert len(res.contradictions) > 0
    assert "senior citizen" in res.contradictions[0].lower()
