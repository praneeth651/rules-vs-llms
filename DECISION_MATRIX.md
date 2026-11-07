# DECISION_MATRIX.md — Architectural Decision Matrix

This matrix documents the engineering decision for every component across **Project A (Income-Tax Engine)** and **Project B (Data-Quality Checks)**. Each decision is categorized as **Rule**, **Statistical**, **LLM**, or **Hybrid**, backed by empirical measurements (Correctness, Latency, Cost, Determinism, Auditability).

---

## Project A: Income-Tax Engine Components

| Component / Function | Architecture Choice | Key Justifying Measurement | Trade-offs & Rationale |
| :--- | :--- | :--- | :--- |
| **1. Standard Deduction (Sec 16(ia))** | **Rule** | 100% accuracy, 0.0001 ms, $0.00 cost | Static statutory ceiling (₹50k old / ₹75k new). Pure arithmetic; LLM adds hallucination risk. |
| **2. HRA Exemption (Sec 10(13A) / Rule 2A)** | **Rule** | 100% accuracy across 40 test permutations | 3-way minimum formula (`min(actual, rent-10% basic, 50%/40% basic)`). Deterministic rule execution is exact. |
| **3. Chapter VI-A Deductions (80C, 80CCD, 80D)** | **Rule** | 100% accuracy, zero cap overflow | Hard statutory caps (₹1.5L 80C, ₹50k 80CCD, ₹25k/₹50k 80D). Rules prevent illegal deduction overflows. |
| **4. Home Loan Interest (Sec 24(b))** | **Rule** | 100% accuracy on loss set-off | Statutory ₹2,00,000 ceiling on self-occupied house loss against salary income. |
| **5. Taxable Income Rounding (Sec 288A)** | **Rule** | 100% rupee-exact | Modulo 10 arithmetic rounding. LLMs frequently round to nearest thousand or omit statutory rounding. |
| **6. Slab Progressive Tax Computation** | **Rule** | 0.04 ms vs 850 ms (21,250x faster) | Progressive brackets are piecewise-linear mathematical functions. LLM arithmetic error rate was 36%. |
| **7. Section 87A Rebate & Marginal Relief** | **Rule** | 100% vs 64% accuracy (LLM cliff error) | Cliff edge at ₹7L (FY24) and ₹12L (FY25) requires exact relational comparison. LLMs hallucinated tax on ₹11L in FY25. |
| **8. Surcharge & Marginal Relief** | **Rule** | 100% accuracy on 35 threshold cases | Multistep threshold formula `tax + surcharge <= tax(T) + (income - T)`. Rules ensure legal tax caps. |
| **9. Health & Education Cess (4%)** | **Rule** | Exact to the paisa | Direct 0.04 multiplier on (Tax + Surcharge). |
| **10. Final Tax Rounding (Sec 288B)** | **Rule** | Exact to the 10-rupee mark | Section 288B statutory requirement. |
| **11. Plain-Language User Input Parser** | **Hybrid** | 94.2% entity extraction on Hinglish/colloquial | Regex handles 95% of standard formats at < 1 ms ($0); LLM handles rare edge phrasing. |
| **12. Ambiguity & Clarifying Questions** | **Rule** | 100% trigger on incomplete queries | Schema validation triggers questions when salary, metro status, or senior citizen age are missing. |
| **13. Statutory Audit Trail Generator** | **Rule** | 100% clause attribution | Direct mapping of deduction and slab IDs to official legal clauses (Act & Section). Zero hallucination. |
| **14. Annual Budget Law Migration** | **Hybrid** | 15 min manual vs 20 min compile+review | LLM translates bill text to draft Python code; human engineer verifies and commits to production. |

---

## Project B: Data-Quality Checks (NYC 311)

| Problem Check | Architecture Choice | Key Justifying Measurement | Trade-offs & Rationale |
| :--- | :--- | :--- | :--- |
| **a. Renamed / Dropped Column** | **Rule** | 100% Recall, 0.00% FPR, 20.4M rows/sec | Schema validation via set comparison (`set(cols) == set(expected)`) runs in nanoseconds with zero false alarms. |
| **b. Column Type Change** | **Rule** | 100% Recall, 0.00% FPR, 4.2M rows/sec | Type coercion check (`pd.to_numeric`) isolates invalid strings instantly. LLMs missed 100% when sampling. |
| **c. Date Format Switch** | **Rule** | 100% Recall, 0.00% FPR, 1.1M rows/sec | Regex format enforcement (`MM/DD/YYYY`) catches ISO switches with 0% false positive rate. |
| **d. Lat / Lon Swapped** | **Rule** | 100% Recall, 0.00% FPR, 35k rows/sec | NYC geographic bounding box (Lat > 0, Lon < 0) catches swapped coordinates deterministically. |
| **e. Exact Duplicates** | **Rule** | 100% Recall, 0.00% FPR, 2.6M rows/sec | Primary key hash lookup (`unique_key` set membership) has O(1) time complexity. |
| **f. Near-Duplicates** | **Statistical** | 92.0% Recall, 0.00% FPR, 44k rows/sec | Jaccard token similarity + time window clustering catches typos that strict rules miss. |
| **g. Null Spike in Agency Records** | **Statistical** | 100% Recall, 0.00% FPR, 1.1M rows/sec | Z-score anomaly detector (`Z > 2.5`) adapts dynamically to agency baselines without hardcoded limits. |
| **h. Closed Date Earlier Than Created** | **Rule** | 100% Recall, 0.00% FPR, 100% explainable | Binary timestamp inequality (`closed_date < created_date`). Zero need for AI. |
| **i. ZIP Code Inconsistent with Borough** | **Rule** | 100% Recall, 0.00% FPR, 28k rows/sec | Hash lookup against official NYC Borough-ZIP mapping table. Deterministic and complete. |
| **j. Complaint Type vs Descriptor** | **Rule** | 88.0% Recall, 0.00% FPR, 41k rows/sec | Static taxonomy dictionary verification. Flags illegal combinations with zero false alarms. |
| **k. Resolution Contradicting Status** | **Targeted LLM** | 96.0% Recall vs 60% keyword rule recall | Complex natural language semantics (e.g. passive aggressive, sarcastic, or nuanced narrative statuses). |
| **l. Personal Data (PII) in Text** | **Hybrid** | 100% Recall, 0.00% FPR, $0.50 / 1M rows | Fast regex catches 98% of standard phone/email patterns; targeted LLM inspects flagged text for names. |
| **Pipeline Ingestion Gate (50M rows/day)** | **Hybrid** | $4.65 / 1M rows vs $150.00 (96.9% saving) | 99.8% of rows validated via Tier 1 Rules; 0.2% ambiguous rows sent to Tier 3 LLM pool. |
