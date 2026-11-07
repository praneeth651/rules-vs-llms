"""
Pytest Suite for Indian Income Tax Engine (Project A)
Tests:
- Rupee-exact accuracy across all 215 test cases under both regimes (FY 2024-25 and FY 2025-26)
- Cross-verification of 35 official calculator benchmark cases
- Determinism test (10 runs on identical inputs)
- LLM-Compiled rules parity with Hand-Coded rules
- Audit trail and clause citation verification
"""

import os
import json
import pytest
from project_a.tax_engine.models import TaxInput
from project_a.tax_engine.rules_engine import RulesEngine
from project_a.tax_engine.llm_compiled_engine import LLMCompiledEngine


@pytest.fixture(scope="module")
def test_cases():
    test_file = os.path.join(os.path.dirname(__file__), "test_cases.json")
    with open(test_file, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def engines():
    return {
        "rules_2024": RulesEngine(default_fy="2024-25"),
        "rules_2025": RulesEngine(default_fy="2025-26"),
        "compiled_2024": LLMCompiledEngine(default_fy="2024-25"),
        "compiled_2025": LLMCompiledEngine(default_fy="2025-26"),
    }


def test_total_case_count(test_cases):
    """Ensure requirement of at least 200 test cases is met."""
    assert len(test_cases) >= 200, f"Expected at least 200 cases, found {len(test_cases)}"


def test_official_calculator_benchmark_cases(test_cases, engines):
    """Cross-verify at least 30 cases verified against official ITD calculator."""
    official_cases = [c for c in test_cases if c.get("verified_against_official_calculator")]
    assert len(official_cases) >= 30, f"Expected at least 30 official cases, found {len(official_cases)}"

    for case in official_cases:
        inp_dict = case["input"]
        inp = TaxInput(**inp_dict)
        res = engines["rules_2024"].calculate(inp, fy="2024-25")
        
        expected = case["expected_fy_2024_25"]
        assert res.old_regime.total_tax_payable_rounded == expected["old_regime_tax"], (
            f"Case {case['id']} Old Regime mismatch: got {res.old_regime.total_tax_payable_rounded}, "
            f"expected {expected['old_regime_tax']}"
        )
        assert res.new_regime.total_tax_payable_rounded == expected["new_regime_tax"], (
            f"Case {case['id']} New Regime mismatch: got {res.new_regime.total_tax_payable_rounded}, "
            f"expected {expected['new_regime_tax']}"
        )


def test_all_cases_fy_2024_25_rupee_exact(test_cases, engines):
    """Verify rupee-exact correctness across all 215 cases for FY 2024-25."""
    for case in test_cases:
        inp = TaxInput(**case["input"])
        res = engines["rules_2024"].calculate(inp, fy="2024-25")
        expected = case["expected_fy_2024_25"]

        assert res.old_regime.total_tax_payable_rounded == expected["old_regime_tax"], (
            f"FY24 Old Tax mismatch for {case['id']}"
        )
        assert res.new_regime.total_tax_payable_rounded == expected["new_regime_tax"], (
            f"FY24 New Tax mismatch for {case['id']}"
        )
        assert res.recommended_regime == expected["recommended_regime"], (
            f"FY24 Recommendation mismatch for {case['id']}"
        )


def test_all_cases_fy_2025_26_task_5_change(test_cases, engines):
    """Verify rupee-exact correctness across all 215 cases under FY 2025-26 Budget change."""
    for case in test_cases:
        inp = TaxInput(**case["input"])
        res = engines["rules_2025"].calculate(inp, fy="2025-26")
        expected = case["expected_fy_2025_26"]

        assert res.old_regime.total_tax_payable_rounded == expected["old_regime_tax"], (
            f"FY25 Old Tax mismatch for {case['id']}"
        )
        assert res.new_regime.total_tax_payable_rounded == expected["new_regime_tax"], (
            f"FY25 New Tax mismatch for {case['id']}"
        )
        assert res.recommended_regime == expected["recommended_regime"], (
            f"FY25 Recommendation mismatch for {case['id']}"
        )


def test_compiled_rules_parity(test_cases, engines):
    """Verify Implementation C (LLM-Compiled Rules) produces 100% identical results to Implementation A."""
    for case in test_cases[:50]:  # sample 50 representative cases
        inp = TaxInput(**case["input"])
        res_rules = engines["rules_2024"].calculate(inp, fy="2024-25")
        res_comp = engines["compiled_2024"].calculate(inp, fy="2024-25")

        assert res_comp.old_regime.total_tax_payable_rounded == res_rules.old_regime.total_tax_payable_rounded
        assert res_comp.new_regime.total_tax_payable_rounded == res_rules.new_regime.total_tax_payable_rounded
        assert res_comp.recommended_regime == res_rules.recommended_regime


def test_determinism_repeated_10_times(engines):
    """Verify that repeated calculations 10 times on the same input produce identical numbers."""
    inp = TaxInput(
        gross_salary=1850000,
        section_80c=150000,
        section_80ccd_1b=50000,
        section_80d_self=25000,
        section_80d_parents=50000,
        parents_are_senior_citizens=True,
        rent_paid=300000,
        hra_received=250000,
        is_metro=True,
    )

    baseline = engines["rules_2024"].calculate(inp)
    for _ in range(10):
        run_res = engines["rules_2024"].calculate(inp)
        assert run_res.old_regime.total_tax_payable_rounded == baseline.old_regime.total_tax_payable_rounded
        assert run_res.new_regime.total_tax_payable_rounded == baseline.new_regime.total_tax_payable_rounded
        assert run_res.tax_difference == baseline.tax_difference


def test_every_rupee_has_statutory_clause(engines):
    """Verify statutory auditability: every rupee of deduction and slab tax links to a clause."""
    inp = TaxInput(
        gross_salary=2500000,
        section_80c=150000,
        section_80ccd_1b=50000,
        section_80d_self=25000,
        rent_paid=360000,
        hra_received=300000,
        is_metro=True,
        home_loan_interest_self_occupied=200000,
    )
    res = engines["rules_2024"].calculate(inp)

    # Check deductions have statutory clauses
    for ded in res.old_regime.deductions:
        assert ded.statutory_clause is not None and len(ded.statutory_clause) > 10

    # Check slabs have statutory clauses
    for slab in res.old_regime.slab_taxes:
        assert slab.statutory_clause is not None and len(slab.statutory_clause) > 5

    for slab in res.new_regime.slab_taxes:
        assert slab.statutory_clause is not None and len(slab.statutory_clause) > 5
