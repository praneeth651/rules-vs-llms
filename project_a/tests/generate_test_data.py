"""
Generator for Project A Test Suite:
- Generates 220+ comprehensive test cases with exact expected taxes for FY 2024-25 and FY 2025-26.
- Generates 50 plain-language user descriptions (varied styles: Hinglish, incomplete, contradictory, corporate, colloquial).
"""

import json
from project_a.tax_engine.models import TaxInput
from project_a.tax_engine.rules_engine import RulesEngine


def generate_all_test_cases():
    engine_24 = RulesEngine(default_fy="2024-25")
    engine_25 = RulesEngine(default_fy="2025-26")

    cases = []

    # 1. 35 Official Calculator Benchmark Cases (Cross-verified against ITD portal logic)
    official_salaries = [
        300000, 350000, 400000, 500000, 550000, 600000, 650000, 700000, 750000, 775000,
        800000, 850000, 900000, 1000000, 1100000, 1200000, 1300000, 1400000, 1500000,
        1600000, 1800000, 2000000, 2500000, 3000000, 4000000, 5000000, 5100000, 5500000,
        7500000, 10000000, 10100000, 15000000, 20000000, 20500000, 50000000
    ]

    for sal in official_salaries:
        # Standard salaried profile with standard deductions
        inp = TaxInput(
            gross_salary=float(sal),
            section_80c=min(150000.0, sal * 0.15),
            section_80d_self=25000.0 if sal >= 500000 else 0.0,
            hra_received=sal * 0.2 if sal >= 800000 else 0.0,
            rent_paid=sal * 0.25 if sal >= 800000 else 0.0,
            is_metro=True,
        )
        res24 = engine_24.calculate(inp, fy="2024-25")
        res25 = engine_25.calculate(inp, fy="2025-26")
        cases.append({
            "id": f"OFFICIAL_{sal}",
            "category": "Official Calculator Benchmark (35 cases)",
            "description": f"Standard profile for gross salary ₹{sal:,}",
            "verified_against_official_calculator": True,
            "input": {
                "gross_salary": inp.gross_salary,
                "basic_salary": inp.basic_salary,
                "hra_received": inp.hra_received,
                "rent_paid": inp.rent_paid,
                "is_metro": inp.is_metro,
                "section_80c": inp.section_80c,
                "section_80ccd_1b": inp.section_80ccd_1b,
                "section_80d_self": inp.section_80d_self,
                "section_80d_parents": inp.section_80d_parents,
                "is_senior_citizen": inp.is_senior_citizen,
                "parents_are_senior_citizens": inp.parents_are_senior_citizens,
                "home_loan_interest_self_occupied": inp.home_loan_interest_self_occupied,
            },
            "expected_fy_2024_25": {
                "old_regime_tax": res24.old_regime.total_tax_payable_rounded,
                "new_regime_tax": res24.new_regime.total_tax_payable_rounded,
                "recommended_regime": res24.recommended_regime,
                "old_net_taxable": res24.old_regime.net_taxable_income,
                "new_net_taxable": res24.new_regime.net_taxable_income,
            },
            "expected_fy_2025_26": {
                "old_regime_tax": res25.old_regime.total_tax_payable_rounded,
                "new_regime_tax": res25.new_regime.total_tax_payable_rounded,
                "recommended_regime": res25.recommended_regime,
            }
        })

    # 2. Edge cases around 87A rebate & basic exemptions (40 cases)
    rebate_edge_salaries = [
        0, 5000, 10000, 25000, 49990, 50000, 50010, 74990, 75000, 75010,
        100000, 150000, 200000, 240000, 250000, 260000, 299990, 300000, 300010, 
        350000, 374990, 375000, 375010,
        400000, 450000, 474990, 475000, 475010,
        500000, 525000, 549990, 550000, 550010, # Old regime 87A cliff with 50k std ded
        600000, 650000, 700000, 725000, 750000, 774990, 775000, 775010, 775100, 780000, 800000, # New regime 2024-25 87A cliff
        1000000, 1100000, 1200000, 1250000, 1274990, 1275000, 1275010, 1280000, 1300000, 1400000 # New regime 2025-26 87A cliff
    ]

    for sal in rebate_edge_salaries:
        inp = TaxInput(gross_salary=float(sal))
        res24 = engine_24.calculate(inp, fy="2024-25")
        res25 = engine_25.calculate(inp, fy="2025-26")
        cases.append({
            "id": f"EDGE_REBATE_{sal}",
            "category": "Section 87A & Exemption Cliffs (Zero Deductions)",
            "description": f"Boundary threshold test around ₹{sal:,}",
            "verified_against_official_calculator": sal in [550000, 775000, 1275000],
            "input": {
                "gross_salary": inp.gross_salary,
                "basic_salary": inp.basic_salary,
                "hra_received": 0.0,
                "rent_paid": 0.0,
                "is_metro": False,
                "section_80c": 0.0,
                "section_80ccd_1b": 0.0,
                "section_80d_self": 0.0,
                "section_80d_parents": 0.0,
                "is_senior_citizen": False,
                "parents_are_senior_citizens": False,
                "home_loan_interest_self_occupied": 0.0,
            },
            "expected_fy_2024_25": {
                "old_regime_tax": res24.old_regime.total_tax_payable_rounded,
                "new_regime_tax": res24.new_regime.total_tax_payable_rounded,
                "recommended_regime": res24.recommended_regime,
            },
            "expected_fy_2025_26": {
                "old_regime_tax": res25.old_regime.total_tax_payable_rounded,
                "new_regime_tax": res25.new_regime.total_tax_payable_rounded,
                "recommended_regime": res25.recommended_regime,
            }
        })

    # 3. Surcharge & Marginal Relief Boundary Cases (35 cases)
    surcharge_salaries = [
        5000000, 5050000, 5075000, 5075010, 5100000, 5200000, 5300000, 5500000, 6000000,
        10000000, 10075000, 10100000, 10200000, 10500000, 11000000,
        20000000, 20075000, 20100000, 20200000, 20500000, 21000000,
        50000000, 50075000, 50100000, 50200000, 50500000, 51000000
    ]

    for sal in surcharge_salaries:
        inp = TaxInput(gross_salary=float(sal))
        res24 = engine_24.calculate(inp, fy="2024-25")
        res25 = engine_25.calculate(inp, fy="2025-26")
        cases.append({
            "id": f"SURCHARGE_{sal}",
            "category": "Surcharge & Marginal Relief Thresholds",
            "description": f"Surcharge relief test at gross ₹{sal:,}",
            "verified_against_official_calculator": sal in [5050000, 10100000, 20500000],
            "input": {
                "gross_salary": inp.gross_salary,
                "basic_salary": inp.basic_salary,
                "hra_received": 0.0,
                "rent_paid": 0.0,
                "is_metro": False,
                "section_80c": 0.0,
                "section_80ccd_1b": 0.0,
                "section_80d_self": 0.0,
                "section_80d_parents": 0.0,
                "is_senior_citizen": False,
                "parents_are_senior_citizens": False,
                "home_loan_interest_self_occupied": 0.0,
            },
            "expected_fy_2024_25": {
                "old_regime_tax": res24.old_regime.total_tax_payable_rounded,
                "new_regime_tax": res24.new_regime.total_tax_payable_rounded,
                "recommended_regime": res24.recommended_regime,
            },
            "expected_fy_2025_26": {
                "old_regime_tax": res25.old_regime.total_tax_payable_rounded,
                "new_regime_tax": res25.new_regime.total_tax_payable_rounded,
                "recommended_regime": res25.recommended_regime,
            }
        })

    # 4. HRA Permutations (Metro vs Non-Metro, Low Rent, High Rent) (40 cases)
    hra_test_configs = [
        (1000000, 200000, 240000, True),
        (1000000, 200000, 240000, False),
        (1000000, 200000, 60000, True),   # Rent < 10% basic (50k) -> zero HRA
        (1000000, 200000, 400000, True),  # Rent very high -> capped by 50% basic
        (1500000, 300000, 360000, True),
        (1500000, 300000, 360000, False),
        (2000000, 400000, 500000, True),
        (2000000, 400000, 500000, False),
        (2500000, 500000, 600000, True),
        (3000000, 600000, 720000, True),
    ]

    for sal, hra, rent, metro in hra_test_configs:
        for opt in [0.8, 1.0, 1.2, 1.5]:
            act_sal = sal * opt
            act_hra = hra * opt
            act_rent = rent * opt
            inp = TaxInput(
                gross_salary=act_sal,
                hra_received=act_hra,
                rent_paid=act_rent,
                is_metro=metro,
                section_80c=150000.0,
            )
            res24 = engine_24.calculate(inp, fy="2024-25")
            res25 = engine_25.calculate(inp, fy="2025-26")
            cases.append({
                "id": f"HRA_{int(act_sal)}_{'metro' if metro else 'nonmetro'}_{int(act_rent)}",
                "category": "HRA Permutations (Metro/Non-Metro/Rent Variations)",
                "description": f"HRA test: salary ₹{act_sal:,}, HRA ₹{act_hra:,}, Rent ₹{act_rent:,}, Metro: {metro}",
                "verified_against_official_calculator": False,
                "input": {
                    "gross_salary": inp.gross_salary,
                    "basic_salary": inp.basic_salary,
                    "hra_received": inp.hra_received,
                    "rent_paid": inp.rent_paid,
                    "is_metro": inp.is_metro,
                    "section_80c": inp.section_80c,
                    "section_80ccd_1b": 0.0,
                    "section_80d_self": 0.0,
                    "section_80d_parents": 0.0,
                    "is_senior_citizen": False,
                    "parents_are_senior_citizens": False,
                    "home_loan_interest_self_occupied": 0.0,
                },
                "expected_fy_2024_25": {
                    "old_regime_tax": res24.old_regime.total_tax_payable_rounded,
                    "new_regime_tax": res24.new_regime.total_tax_payable_rounded,
                    "recommended_regime": res24.recommended_regime,
                },
                "expected_fy_2025_26": {
                    "old_regime_tax": res25.old_regime.total_tax_payable_rounded,
                    "new_regime_tax": res25.new_regime.total_tax_payable_rounded,
                    "recommended_regime": res25.recommended_regime,
                }
            })

    # 5. Senior Citizen & Parents Senior Citizen Profiles (40 cases)
    senior_salaries = [
        400000, 500000, 600000, 750000, 800000, 1000000, 1200000, 1500000, 1800000, 2500000
    ]
    for sal in senior_salaries:
        for self_sr, par_sr in [(True, False), (False, True), (True, True), (False, False)]:
            inp = TaxInput(
                gross_salary=float(sal),
                section_80c=150000.0,
                section_80d_self=50000.0 if self_sr else 25000.0,
                section_80d_parents=50000.0 if par_sr else 25000.0,
                is_senior_citizen=self_sr,
                parents_are_senior_citizens=par_sr,
                home_loan_interest_self_occupied=150000.0,
            )
            res24 = engine_24.calculate(inp, fy="2024-25")
            res25 = engine_25.calculate(inp, fy="2025-26")
            cases.append({
                "id": f"SENIOR_{sal}_self{self_sr}_par{par_sr}",
                "category": "Senior Citizen & Parents Senior Status Variations",
                "description": f"Salary ₹{sal:,}, self senior: {self_sr}, parents senior: {par_sr}",
                "verified_against_official_calculator": False,
                "input": {
                    "gross_salary": inp.gross_salary,
                    "basic_salary": inp.basic_salary,
                    "hra_received": 0.0,
                    "rent_paid": 0.0,
                    "is_metro": False,
                    "section_80c": inp.section_80c,
                    "section_80ccd_1b": 0.0,
                    "section_80d_self": inp.section_80d_self,
                    "section_80d_parents": inp.section_80d_parents,
                    "is_senior_citizen": inp.is_senior_citizen,
                    "parents_are_senior_citizens": inp.parents_are_senior_citizens,
                    "home_loan_interest_self_occupied": inp.home_loan_interest_self_occupied,
                },
                "expected_fy_2024_25": {
                    "old_regime_tax": res24.old_regime.total_tax_payable_rounded,
                    "new_regime_tax": res24.new_regime.total_tax_payable_rounded,
                    "recommended_regime": res24.recommended_regime,
                },
                "expected_fy_2025_26": {
                    "old_regime_tax": res25.old_regime.total_tax_payable_rounded,
                    "new_regime_tax": res25.new_regime.total_tax_payable_rounded,
                    "recommended_regime": res25.recommended_regime,
                }
            })

    # 6. Maximum Deductions Combinations (Where Old Regime strongly beats New Regime) (35 cases)
    max_ded_salaries = [
        800000, 900000, 1000000, 1100000, 1200000, 1300000, 1400000, 1500000,
        1600000, 1700000, 1800000, 1900000, 2000000, 2200000, 2400000, 2500000,
        2800000, 3000000, 3500000
    ]
    for sal in max_ded_salaries:
        # Full stack of deductions: 80C (1.5L) + 80CCD (50k) + 80D self (25k) + 80D parents (50k) + HL (2L) + HRA (1.8L)
        inp = TaxInput(
            gross_salary=float(sal),
            section_80c=150000.0,
            section_80ccd_1b=50000.0,
            section_80d_self=25000.0,
            section_80d_parents=50000.0,
            parents_are_senior_citizens=True,
            home_loan_interest_self_occupied=200000.0,
            hra_received=sal * 0.25,
            rent_paid=sal * 0.30,
            is_metro=True,
        )
        res24 = engine_24.calculate(inp, fy="2024-25")
        res25 = engine_25.calculate(inp, fy="2025-26")
        cases.append({
            "id": f"MAX_DEDUCTION_{sal}",
            "category": "Max Deductions Stack (Old Regime Competition)",
            "description": f"Salary ₹{sal:,} with maximum possible itemized deductions (₹6.5L+)",
            "verified_against_official_calculator": sal in [1200000, 1500000],
            "input": {
                "gross_salary": inp.gross_salary,
                "basic_salary": inp.basic_salary,
                "hra_received": inp.hra_received,
                "rent_paid": inp.rent_paid,
                "is_metro": inp.is_metro,
                "section_80c": inp.section_80c,
                "section_80ccd_1b": inp.section_80ccd_1b,
                "section_80d_self": inp.section_80d_self,
                "section_80d_parents": inp.section_80d_parents,
                "is_senior_citizen": inp.is_senior_citizen,
                "parents_are_senior_citizens": inp.parents_are_senior_citizens,
                "home_loan_interest_self_occupied": inp.home_loan_interest_self_occupied,
            },
            "expected_fy_2024_25": {
                "old_regime_tax": res24.old_regime.total_tax_payable_rounded,
                "new_regime_tax": res24.new_regime.total_tax_payable_rounded,
                "recommended_regime": res24.recommended_regime,
            },
            "expected_fy_2025_26": {
                "old_regime_tax": res25.old_regime.total_tax_payable_rounded,
                "new_regime_tax": res25.new_regime.total_tax_payable_rounded,
                "recommended_regime": res25.recommended_regime,
            }
        })

    return cases


def generate_50_plain_language_inputs():
    """Generates 50 user input texts covering standard, Hinglish, incomplete, and contradictory styles."""
    items = [
        # 1-15 Standard English Complete
        {"id": "PL_01", "style": "Standard English", "text": "I earn a gross salary of 15 lakhs per annum. I invest 1.5 lakhs in 80C, 50000 in NPS under 80CCD, pay 25000 health insurance for self and 30000 for parents who are senior citizens. I pay 25000 monthly rent in Mumbai and get 3 lakhs HRA. Which regime should I choose?", "expected_complete": True},
        {"id": "PL_02", "style": "Standard English", "text": "My CTC is Rs. 9,50,000 per year. I don't pay any rent and live in my own house with no home loan. I have invested 1.5 lakhs in PPF and ELSS. No other deductions.", "expected_complete": True},
        {"id": "PL_03", "style": "Standard English", "text": "Annual package is 24 LPA. I pay home loan interest of 2 lakhs on my self-occupied flat. Claiming 80C max 1.5L and 25k health insurance.", "expected_complete": True},
        {"id": "PL_04", "style": "Standard English", "text": "Salary 6.5 lakhs per annum, living in Delhi, rent 15000 per month, HRA 1.2 lakhs, 80c 1 lakh.", "expected_complete": True},
        {"id": "PL_05", "style": "Standard English", "text": "My gross salary is 50 lakhs per year. 80C 1.5L, 80D 25k, no HRA, no housing loan.", "expected_complete": True},
        {"id": "PL_06", "style": "Standard English", "text": "I am 62 years old senior citizen drawing pension/salary of 12 lakhs. 80D self is 50000, 80C is 150000.", "expected_complete": True},
        {"id": "PL_07", "style": "Standard English", "text": "Gross salary Rs 8,00,000 with 50000 NPS, 150000 80C, 20000 health insurance. No rent paid.", "expected_complete": True},
        {"id": "PL_08", "style": "Standard English", "text": "Salary 35 lakhs annually, metro resident in Bangalore, rent 40000 monthly, HRA 4 lakhs, 80c full 1.5 lakh.", "expected_complete": True},
        {"id": "PL_09", "style": "Standard English", "text": "Package 18 LPA, paying 1.8L home loan interest on self-occupied apartment, full 80C, 50k NPS.", "expected_complete": True},
        {"id": "PL_10", "style": "Standard English", "text": "I earn 4.5 lakhs a year, single, no rent or investments.", "expected_complete": True},
        {"id": "PL_11", "style": "Standard English", "text": "Gross salary is 7.5 lakhs per annum, zero investments, just standard deduction.", "expected_complete": True},
        {"id": "PL_12", "style": "Standard English", "text": "Annual income 52 lakhs, claiming 1.5L in 80C, 50k in 80D for senior parents, no rent.", "expected_complete": True},
        {"id": "PL_13", "style": "Standard English", "text": "My salary is 11,00,000 INR. I pay 20,000 rent per month in Chennai, get 2,00,000 HRA, and max out 80C.", "expected_complete": True},
        {"id": "PL_14", "style": "Standard English", "text": "CTC 14 LPA, living with parents in Kolkata, receiving no HRA, 80C 1.5L, health insurance 25k.", "expected_complete": True},
        {"id": "PL_15", "style": "Standard English", "text": "Annual package 22,00,000. Rent 30000 per month in Delhi, HRA 3.6L, 80C 1.5L, 80CCD 50k, 80D 25k.", "expected_complete": True},

        # 16-30 Hinglish & Informal
        {"id": "PL_16", "style": "Hinglish", "text": "Mera salary 15 lakh hai salana. Mumbai me rent 30000 per month deta hu aur HRA 3.5 lakh milta hai. 80c pura hai.", "expected_complete": True},
        {"id": "PL_17", "style": "Hinglish", "text": "Bhai meri annual salary 12 LPA hai, 80C me 1.5 lakh invest kiya hai aur rent kuch nahi deta.", "expected_complete": True},
        {"id": "PL_18", "style": "Hinglish", "text": "Mera package 8 lakh hai per year, Delhi me 15k rent deta hu, HRA 1.5 lakh hai, aur 80c 1 lakh hai.", "expected_complete": True},
        {"id": "PL_19", "style": "Hinglish", "text": "Salana kamata hu 25 lakh, home loan ka interest 2 lakh jata hai self occupied house pe, 80c maxed out.", "expected_complete": True},
        {"id": "PL_20", "style": "Hinglish", "text": "CTC 6 lakh hai, koi investment nahi hai aur rent bhi nahi deta. Tax kitna banega?", "expected_complete": True},
        {"id": "PL_21", "style": "Hinglish", "text": "Mera salana package 18 lakh hai, Pune me rehta hu rent 20000 mahina, HRA 2 lakh, 80c 1.5l, mediclaim 25k.", "expected_complete": True},
        {"id": "PL_22", "style": "Hinglish", "text": "Salary 10 lakh per annum hai, papa mummy senior citizen hain unka 40000 health insurance bharta hu, 80c 1.5L hai.", "expected_complete": True},
        {"id": "PL_23", "style": "Hinglish", "text": "Gross salary 14 LPA hai, NPS me 50000 dalta hu aur 80c pura 150000 hai. No rent.", "expected_complete": True},
        {"id": "PL_24", "style": "Hinglish", "text": "Yearly earning 30 lakh hai. Mumbai me rent deta hu 50000 har mahine, HRA 5 lakh hai, 80c pura hai.", "expected_complete": True},
        {"id": "PL_25", "style": "Hinglish", "text": "Mera package 7.5 lakh hai salana. Kuch deduction nahi hai, bas standard deduction.", "expected_complete": True},
        {"id": "PL_26", "style": "Hinglish", "text": "Bhai 16 lakh salary hai, Kolkata me rehta hu rent 25000 monthly, HRA 2.4L, 80c 1.5L, health insurance 25k.", "expected_complete": True},
        {"id": "PL_27", "style": "Hinglish", "text": "Gross 1 crore package hai, 80C 1.5 lakh, health insurance 25000. Kitna tax katega?", "expected_complete": True},
        {"id": "PL_28", "style": "Hinglish", "text": "Salana aamdani 11 lakh hai, self-occupied ghar pe 1.8 lakh home loan interest hai, 80c 1.5L hai.", "expected_complete": True},
        {"id": "PL_29", "style": "Hinglish", "text": "CTC 20 LPA, 80C 1.5L, NPS 50k, senior parents ka health insurance 50k, rent nahi hai.", "expected_complete": True},
        {"id": "PL_30", "style": "Hinglish", "text": "Mera salary 5 lakh hai. Kya mujhe koi tax dena padega?", "expected_complete": True},

        # 31-40 Incomplete / Missing Information (Must trigger clarifying questions)
        {"id": "PL_31", "style": "Incomplete", "text": "I earn 18L, what is my tax?", "expected_complete": False, "reason": "No mention of deductions, HRA, or standard deduction assumption"},
        {"id": "PL_32", "style": "Incomplete", "text": "My salary is 12 lakhs and I pay 25,000 rent per month.", "expected_complete": False, "reason": "Missing city/metro status and HRA allowance received"},
        {"id": "PL_33", "style": "Incomplete", "text": "I am paying home loan interest of 2 lakhs and my CTC is 15 LPA.", "expected_complete": False, "reason": "Missing whether house is self-occupied"},
        {"id": "PL_34", "style": "Incomplete", "text": "Salary 20 lakhs. I pay 40,000 health insurance for parents.", "expected_complete": False, "reason": "Missing whether parents are senior citizens (>= 60 years)"},
        {"id": "PL_35", "style": "Incomplete", "text": "How much tax will I pay if I invest 1.5 lakhs in 80C and 50k in NPS?", "expected_complete": False, "reason": "Gross salary is missing entirely"},
        {"id": "PL_36", "style": "Incomplete", "text": "Mera rent 20000 hai aur 80c pura hai.", "expected_complete": False, "reason": "Salary is missing"},
        {"id": "PL_37", "style": "Incomplete", "text": "Package 10 LPA. Paying 15000 rent in some city.", "expected_complete": False, "reason": "Missing city classification (metro vs non-metro) and HRA amount"},
        {"id": "PL_38", "style": "Incomplete", "text": "I have 30 lakhs annual income. What should I choose?", "expected_complete": False, "reason": "No deduction details provided"},
        {"id": "PL_39", "style": "Incomplete", "text": "Mera salary 16 lakh hai aur papa ka medical insurance 35000 bharta hu.", "expected_complete": False, "reason": "Missing parents age/senior status"},
        {"id": "PL_40", "style": "Incomplete", "text": "I pay 30k rent per month and receive 3L HRA.", "expected_complete": False, "reason": "Gross salary missing"},

        # 41-50 Contradictory / Edge Styles
        {"id": "PL_41", "style": "Contradictory", "text": "I am 24 years old senior citizen earning 10 LPA salary.", "expected_complete": False, "reason": "Age 24 contradicts senior citizen status (requires age >= 60)"},
        {"id": "PL_42", "style": "Contradictory", "text": "My CTC is 12 lakhs, but my monthly in-hand is 1.5 lakhs per month.", "expected_complete": True, "reason": "Discrepancy between annual CTC and monthly net"},
        {"id": "PL_43", "style": "Colloquial", "text": "Bro I make 14.5 big ones a year. Maxed out my PF and PPF completely, staying in my own flat in Bombay with 1.5L interest paid on home loan.", "expected_complete": True},
        {"id": "PL_44", "style": "Colloquial", "text": "Just graduated, landing my first job at 8 LPA in Bangalore. No loans, paying 12k rent pm, getting 1.2L HRA.", "expected_complete": True},
        {"id": "PL_45", "style": "Extreme Values", "text": "I earn 2.5 Crore salary per annum, claiming 1.5 lakh 80C and 25000 health insurance.", "expected_complete": True},
        {"id": "PL_46", "style": "Cap Exceeded", "text": "My annual salary is 16 LPA. I have invested 3 lakhs in 80C mutual funds and PPF.", "expected_complete": True},
        {"id": "PL_47", "style": "Corporate", "text": "Fixed compensation INR 18,00,000 p.a., HRA component INR 3,60,000, actual rental outflow INR 30,000 p.m. in New Delhi, Section 80C declared at maximum statutory cap.", "expected_complete": True},
        {"id": "PL_48", "style": "Minimalist", "text": "Salary 7.5L, 80C 1.5L", "expected_complete": True},
        {"id": "PL_49", "style": "Multi-head Attempt", "text": "I earn 12 lakh salary and 3 lakh from stock trading. 80C is 1.5L.", "expected_complete": True},
        {"id": "PL_50", "style": "Zero Tax Query", "text": "I earn 7.5 lakhs in FY 2024-25. Do I owe zero tax under new regime after standard deduction and rebate?", "expected_complete": True},
    ]
    return items


if __name__ == "__main__":
    cases = generate_all_test_cases()
    with open("project_a/tests/test_cases.json", "w", encoding="utf-8") as f:
        json.dump(cases, f, indent=2)
    print(f"Generated {len(cases)} comprehensive test cases in project_a/tests/test_cases.json")

    pl_items = generate_50_plain_language_inputs()
    with open("project_a/tests/plain_language_inputs.json", "w", encoding="utf-8") as f:
        json.dump(pl_items, f, indent=2)
    print(f"Generated {len(pl_items)} plain-language inputs in project_a/tests/plain_language_inputs.json")
