# Rules vs LLMs: Fire AI Take-Home Assignment

Complete implementation and evaluation of **Project A (Income-Tax Engine)** and **Project B (NYC 311 Data-Quality Checks)**.

---

## ⚡ Single Command Reproducibility
As required by the assignment guidelines, a single command executes the automated test suite, runs all benchmarks, and reproduces every reported figure:

```bash
python run_all.py
```
*(Or via the virtualenv: `.\.venv\python.exe run_all.py`)*

---

## 📁 Repository Structure & Deliverables

### Project A: Indian Income-Tax Engine (`project_a/`)
- `project_a/tax_engine/models.py`: Data models (`TaxInput`, `RegimeBreakdown`, `TaxResult`).
- `project_a/tax_engine/constants.py`: Statutory tax provisions & clauses for FY 2024-25 and FY 2025-26.
- `project_a/tax_engine/rules_engine.py`: **Implementation A** — Hand-coded deterministic rules (rupee-exact).
- `project_a/tax_engine/llm_engine.py`: **Implementation B** — LLM at query time with statutory context.
- `project_a/tax_engine/llm_compiled_engine.py`: **Implementation C** — LLM-compiled executable rules.
- `project_a/tax_engine/nlp_parser.py`: **Task 3** — Plain-language parser with clarifying questions for ambiguous inputs.
- `project_a/tests/test_cases.json`: **215 test cases** (35 verified against official ITD calculator).
- `project_a/tests/plain_language_inputs.json`: **50 plain-language inputs** (Hinglish, incomplete, contradictory).
- `project_a/tests/`: Pytest suites verifying rupee-exact accuracy, 10-run determinism, and statutory audit trails.
- `project_a/benchmark.py`: Empirical measurement runner for Project A.
- 📄 **[RESULTS_A.md](RESULTS_A.md)**: Deliverable report with comparison table, Task 5 change log, and final design for 100k users.

### Project B: Data-Quality Checks (`project_b/`)
- `project_b/data_sample.py`: NYC 311 2023 dataset generator & Socrata API integration.
- `project_b/profiler.py`: **Task 1** — Raw 2023 data profiler finding real quality defects with counts and examples.
- `project_b/injector.py`: **Task 2** — Controlled corruption injector for all 12 problem types (a through l).
- `project_b/detectors/rule_detectors.py`: **Task 3a** — Declarative rules & schema checks.
- `project_b/detectors/statistical_detectors.py`: **Task 3b** — Statistical & ML anomaly detectors (Z-score, Jaccard).
- `project_b/detectors/llm_detectors.py`: **Task 3c** — LLM review on batch samples and semantic contradictions.
- `project_b/pipeline.py`: **Task 5** — 3-tier hybrid pipeline combining winning detectors.
- `project_b/benchmark.py`: **Task 4** — Benchmarks for all 12 problems across 3 detector families.
- 📄 **[RESULTS_B.md](RESULTS_B.md)**: Deliverable report with per-problem metrics, real data issues, and 50M rows/day scale design.

### Core Deliverable Documents
- 📄 **[DECISION_MATRIX.md](DECISION_MATRIX.md)**: 27-row matrix justifying every component as Rule, Statistical, LLM, or Hybrid with measurements.
- 📄 **[AI_USAGE.md](AI_USAGE.md)**: AI tools disclosure and detailed post-mortem on where AI was wrong (Section 87A marginal rebate omission) and how test suites caught it.

---

## 🧪 Running Pytest
```bash
.\.venv\python.exe -m pytest -v
```
*All 23 unit & integration tests pass in ~1.0 second.*
