"""
Statutory Constants and Tax Provisions for Indian Income Tax
Salary Income Only.
Covers:
- FY 2024-25 (AY 2025-26) [Finance Act 2024]
- FY 2025-26 (AY 2026-27) [Finance Act 2025 / Task 5 Change]
"""

from typing import List, Dict, Any, Tuple

# Section citations for auditability
CLAUSE_CITATIONS = {
    "SEC_16_IA_OLD": "Section 16(ia) of the Income-tax Act, 1961 — Standard Deduction for salaried individuals (₹50,000)",
    "SEC_16_IA_NEW_2024": "Section 16(ia) as amended by Finance Act 2024 — Standard Deduction under New Regime (₹75,000)",
    "SEC_16_IA_NEW_2025": "Section 16(ia) as per Finance Act 2025 — Standard Deduction under New Regime (₹75,000)",
    "SEC_10_13A": "Section 10(13A) read with Rule 2A of Income-tax Rules, 1962 — House Rent Allowance (HRA) Exemption",
    "SEC_80C": "Section 80C read with Section 80CCE of the Income-tax Act, 1961 — Aggregate cap ₹1,50,000",
    "SEC_80CCD_1B": "Section 80CCD(1B) of the Income-tax Act, 1961 — Additional NPS voluntary contribution cap ₹50,000",
    "SEC_80D_SELF": "Section 80D(2)(a) — Medical insurance premium for self/family (₹25,000 non-senior, ₹50,000 senior citizen)",
    "SEC_80D_PARENTS": "Section 80D(2)(b) — Medical insurance premium for parents (₹25,000 non-senior, ₹50,000 senior citizen parents)",
    "SEC_24_B": "Section 24(b) second proviso read with Section 71(3A) — Interest on borrowed capital for self-occupied property capped at loss of ₹2,00,000",
    "SEC_87A_OLD": "Section 87A of the Income-tax Act, 1961 — Tax rebate up to ₹12,500 if Total Income ≤ ₹5,00,000",
    "SEC_87A_NEW_2024": "Section 87A first and second provisos under Section 115BAC — Rebate up to ₹25,000 if Total Income ≤ ₹7,00,000 (with marginal relief above 7L)",
    "SEC_87A_NEW_2025": "Section 87A as amended by Finance Act 2025 — Rebate up to ₹60,000 if Total Income ≤ ₹12,00,000 (with marginal relief above 12L)",
    "SEC_115BAC_2024": "Section 115BAC(1A) as amended by Finance Act 2024 — Default New Tax Regime slabs",
    "SEC_115BAC_2025": "Section 115BAC(1A) as amended by Finance Act 2025 — Revised New Tax Regime slabs",
    "SEC_SURCHARGE_OLD": "Chapter II / First Schedule Part I of Finance Act — Surcharge on Old Regime with Marginal Relief under first proviso",
    "SEC_SURCHARGE_NEW": "Section 115BAC read with Finance Act — Surcharge on New Regime capped at 25% with Marginal Relief",
    "SEC_CESS": "Health and Education Cess at 4% under Section 4 of relevant Finance Act on (Income-tax + Surcharge)",
    "SEC_288A": "Section 288A — Rounding off of taxable income to nearest ₹10",
    "SEC_288B": "Section 288B — Rounding off of tax payable to nearest ₹10",
}

# --- OLD REGIME PROVISIONS (Identical for FY 2024-25 and FY 2025-26) ---
OLD_REGIME_CONFIG = {
    "standard_deduction": 50000.0,
    "max_80c": 150000.0,
    "max_80ccd_1b": 50000.0,
    "max_80d_self_nonsenior": 25000.0,
    "max_80d_self_senior": 50000.0,
    "max_80d_parents_nonsenior": 25000.0,
    "max_80d_parents_senior": 50000.0,
    "max_home_loan_interest": 200000.0,
    "rebate_87a_max_income": 500000.0,
    "rebate_87a_max_amount": 12500.0,
    # Slabs for non-senior citizen (< 60 years)
    "slabs_general": [
        (0.0, 250000.0, 0.0, "₹0 to ₹2,50,000: Nil rate under First Schedule"),
        (250000.0, 500000.0, 0.05, "₹2,50,001 to ₹5,00,000: 5% under First Schedule"),
        (500000.0, 1000000.0, 0.20, "₹5,00,001 to ₹10,00,000: 20% under First Schedule"),
        (1000000.0, float("inf"), 0.30, "Above ₹10,00,000: 30% under First Schedule"),
    ],
    # Slabs for senior citizen (60 to 79 years)
    "slabs_senior": [
        (0.0, 300000.0, 0.0, "₹0 to ₹3,00,000: Nil rate for Senior Citizen"),
        (300000.0, 500000.0, 0.05, "₹3,00,001 to ₹5,00,000: 5% for Senior Citizen"),
        (500000.0, 1000000.0, 0.20, "₹5,00,001 to ₹10,00,000: 20% for Senior Citizen"),
        (1000000.0, float("inf"), 0.30, "Above ₹10,00,000: 30% for Senior Citizen"),
    ],
    # Surcharge tiers (income_threshold, rate)
    "surcharge_tiers": [
        (5000000.0, 0.10),    # > 50L to 1 Cr: 10%
        (10000000.0, 0.15),   # > 1 Cr to 2 Cr: 15%
        (20000000.0, 0.25),   # > 2 Cr to 5 Cr: 25%
        (50000000.0, 0.37),   # > 5 Cr: 37%
    ],
}

# --- NEW REGIME FY 2024-25 (Finance Act 2024 / AY 2025-26) ---
NEW_REGIME_2024_CONFIG = {
    "standard_deduction": 75000.0,
    "rebate_87a_max_income": 700000.0,
    "rebate_87a_max_amount": 25000.0,
    # Slabs under Sec 115BAC(1A) Finance Act 2024
    "slabs": [
        (0.0, 300000.0, 0.0, "₹0 to ₹3,00,000: Nil rate under Sec 115BAC(1A)"),
        (300000.0, 700000.0, 0.05, "₹3,00,001 to ₹7,00,000: 5% under Sec 115BAC(1A)"),
        (700000.0, 1000000.0, 0.10, "₹7,00,001 to ₹10,00,000: 10% under Sec 115BAC(1A)"),
        (1000000.0, 1200000.0, 0.15, "₹10,00,001 to ₹12,00,000: 15% under Sec 115BAC(1A)"),
        (1200000.0, 1500000.0, 0.20, "₹12,00,001 to ₹15,00,000: 20% under Sec 115BAC(1A)"),
        (1500000.0, float("inf"), 0.30, "Above ₹15,00,000: 30% under Sec 115BAC(1A)"),
    ],
    # Surcharge tiers under New Regime (capped at 25%)
    "surcharge_tiers": [
        (5000000.0, 0.10),    # > 50L to 1 Cr: 10%
        (10000000.0, 0.15),   # > 1 Cr to 2 Cr: 15%
        (20000000.0, 0.25),   # > 2 Cr: 25% (max rate under 115BAC)
    ],
}

# --- NEW REGIME FY 2025-26 (Finance Act 2025 / AY 2026-27 / Task 5 Change) ---
NEW_REGIME_2025_CONFIG = {
    "standard_deduction": 75000.0,
    "rebate_87a_max_income": 1200000.0,
    "rebate_87a_max_amount": 60000.0,
    # Slabs under Sec 115BAC(1A) Finance Act 2025
    "slabs": [
        (0.0, 400000.0, 0.0, "₹0 to ₹4,00,000: Nil rate under amended Sec 115BAC"),
        (400000.0, 800000.0, 0.05, "₹4,00,001 to ₹8,00,000: 5% under amended Sec 115BAC"),
        (800000.0, 1200000.0, 0.10, "₹8,00,001 to ₹12,00,000: 10% under amended Sec 115BAC"),
        (1200000.0, 1600000.0, 0.15, "₹12,00,001 to ₹16,00,000: 15% under amended Sec 115BAC"),
        (1600000.0, 2000000.0, 0.20, "₹16,00,001 to ₹20,00,000: 20% under amended Sec 115BAC"),
        (2000000.0, 2400000.0, 0.25, "₹20,00,001 to ₹24,00,000: 25% under amended Sec 115BAC"),
        (2400000.0, float("inf"), 0.30, "Above ₹24,00,000: 30% under amended Sec 115BAC"),
    ],
    # Surcharge tiers under New Regime
    "surcharge_tiers": [
        (5000000.0, 0.10),    # > 50L to 1 Cr: 10%
        (10000000.0, 0.15),   # > 1 Cr to 2 Cr: 15%
        (20000000.0, 0.25),   # > 2 Cr: 25%
    ],
}

HEALTH_AND_EDUCATION_CESS_RATE = 0.04
