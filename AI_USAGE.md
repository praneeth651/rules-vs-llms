# AI_USAGE.md — AI Tools Disclosure & Failure Analysis

## 1. AI Tools Used and Their Purpose

| Tool / Model | Scope of Usage | Specific Deliverables Supported |
| :--- | :--- | :--- |
| **Antigravity Coding Assistant** | System architecture, test-driven development, code synthesis, refactoring, and benchmark automation. | Built complete `project_a/` and `project_b/` modules, test suites, and documentation. |
| **Google Gemini (gemini-1.5-flash)** | LLM at query-time evaluation (`project_a/tax_engine/llm_engine.py`), static rule compilation (`llm_compiled_engine.py`), and semantic data quality auditing (`project_b/detectors/llm_detectors.py`). | Tested real LLM latency, cost, and failure modes on Indian tax calculations and NYC 311 review. |
| **Python 3.11 Runtime & Tooling** | Execution engine, deterministic rule validation, automated test runner (`pytest`), data profiling (`pandas`). | Ran 23 automated tests across 215 tax cases and 12 data corruption types. |

---

## 2. Where the AI Was Wrong and How It Was Caught

### The Defect: Silent Omission of the Section 87A Marginal Rebate Proviso
During the implementation of **Implementation C (LLM-Compiled Rules)** and the query-time tax engine, the AI was prompted to convert the statutory text of the Finance Act into an executable Python tax calculator for the New Regime (Section 115BAC).

The AI generated the following Python snippet for Section 87A rebate:
```python
# --- CODE INITIALLY PRODUCED BY AI ---
if net_taxable_income <= 700000.0:
    rebate_87a = min(gross_tax, 25000.0)
else:
    rebate_87a = 0.0  # <--- CRITICAL STATUTORY BUG!
```

### Why This Was Catastrophically Wrong
In Indian Income Tax law, the New Tax Regime contains a **marginal relief proviso under Section 87A** (introduced by the Finance Act, 2023):
> *"Provided that where the total income of the person chargeable to tax under sub-section (1A) exceeds seven hundred thousand rupees, the amount of income-tax payable on such total income shall be restricted to the amount by which the total income exceeds seven hundred thousand rupees."*

Under the AI's buggy code:
- An individual with a taxable income of **₹7,00,000** owed **₹0** tax.
- An individual with a taxable income of **₹7,00,050** (just ₹50 more) had the rebate abruptly zeroed out, resulting in a tax liability of **₹25,010** (plus 4% cess = **₹26,010**).
- This represented an absurd, illegal effective marginal tax rate of **52,000%** on that ₹50!

The identical failure occurred when migrating to FY 2025-26 (Task 5), where the threshold increased to ₹12,00,000: the AI repeatedly omitted the marginal relief formula for incomes between ₹12,00,000 and ₹12,75,000.

### How It Was Caught
Because the project followed a strict **Test-Driven Development (TDD)** methodology:
1. We authored `project_a/tests/test_cases.json` containing explicit threshold boundary test cases around every statutory cliff (`EDGE_REBATE_700010`, `EDGE_REBATE_705000`, `EDGE_REBATE_1200010`).
2. These boundary test cases were cross-verified against the official Income Tax Department online calculator.
3. When running `pytest project_a/tests/test_tax_engine.py`, the test failed immediately:
   ```
   AssertionError: FY24 New Tax mismatch for EDGE_REBATE_700010
   Expected: 10
   Got: 25010
   ```

### The Fix Applied
We corrected the compiled kernel and rules engine to implement the exact statutory proviso:
```python
# --- CORRECTED STATUTORY FORMULA ---
if net_taxable_income <= max_rebate_income:
    rebate_87a = min(gross_tax, max_rebate_amount)
else:
    # Marginal rebate proviso: tax cannot exceed excess income over threshold
    excess_income = net_taxable_income - max_rebate_income
    if gross_tax > excess_income:
        rebate_87a = gross_tax - excess_income
    else:
        rebate_87a = 0.0
```

### Key Takeaway for the Defense Interview
This incident provides direct empirical proof for why **financial calculations must never be delegated to unsupervised LLMs in production**:
1. An LLM optimizes for typical textual patterns and frequently overlooks statutory edge provisos.
2. The error was completely **silent** (it returned a clean float with no exception).
3. Only deterministic code backed by comprehensive boundary unit tests can guarantee rupee-exact correctness.
