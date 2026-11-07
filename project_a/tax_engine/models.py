"""
Tax Engine Models for Indian Income Tax Engine (Salary Income Only)
Covers FY 2024-25 (AY 2025-26) and FY 2025-26 (AY 2026-27).
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any


@dataclass
class TaxInput:
    """Input parameters for salaried individual income tax calculation."""
    gross_salary: float
    basic_salary: Optional[float] = None  # Needed for HRA calculation; default to 50% of gross if not provided
    hra_received: float = 0.0
    rent_paid: float = 0.0
    is_metro: bool = False  # Delhi, Mumbai, Kolkata, Chennai -> 50%, non-metro -> 40%
    section_80c: float = 0.0  # Max 1,50,000 (PF, PPF, ELSS, Life Insurance, etc.)
    section_80ccd_1b: float = 0.0  # Additional NPS self-contribution max 50,000
    section_80d_self: float = 0.0  # Health insurance self/family (max 25k, 50k if senior)
    section_80d_parents: float = 0.0  # Health insurance parents (max 25k, 50k if senior)
    is_senior_citizen: bool = False  # Age 60 or above
    parents_are_senior_citizens: bool = False  # Parents age 60 or above
    home_loan_interest_self_occupied: float = 0.0  # Max 2,00,000 under Section 24(b)
    age: Optional[int] = None
    
    def __post_init__(self):
        if self.basic_salary is None:
            # Standard HR practice in India: Basic is typically 40-50% of Gross
            self.basic_salary = round(self.gross_salary * 0.5, 2)
        if self.age is not None and self.age >= 60:
            self.is_senior_citizen = True


@dataclass
class DeductionItem:
    """Individual deduction line item with statutory clause citation."""
    section: str
    description: str
    claimed_amount: float
    allowed_amount: float
    max_limit: Optional[float]
    statutory_clause: str


@dataclass
class SlabTaxItem:
    """Slab-wise tax calculation item with statutory clause citation."""
    slab_range: str
    taxable_in_slab: float
    rate_percent: float
    tax_amount: float
    statutory_clause: str


@dataclass
class RegimeBreakdown:
    """Detailed audit trail breakdown for a specific tax regime."""
    regime_name: str  # 'Old Regime' or 'New Regime'
    financial_year: str  # e.g., '2024-25' or '2025-26'
    gross_salary: float
    deductions: List[DeductionItem] = field(default_factory=list)
    total_deductions: float = 0.0
    net_taxable_income: float = 0.0
    slab_taxes: List[SlabTaxItem] = field(default_factory=list)
    gross_tax_before_rebate: float = 0.0
    rebate_87a: float = 0.0
    tax_after_rebate: float = 0.0
    surcharge_rate_percent: float = 0.0
    surcharge_before_marginal_relief: float = 0.0
    marginal_relief_surcharge: float = 0.0
    final_surcharge: float = 0.0
    tax_and_surcharge: float = 0.0
    health_education_cess_4pct: float = 0.0
    total_tax_payable_exact: float = 0.0
    total_tax_payable_rounded: int = 0  # Section 288B rounding to nearest 10
    audit_trail: List[str] = field(default_factory=list)


@dataclass
class TaxResult:
    """Final tax calculation result comparing both regimes and making recommendation."""
    financial_year: str
    old_regime: RegimeBreakdown
    new_regime: RegimeBreakdown
    recommended_regime: str  # 'New Regime', 'Old Regime', or 'Either'
    tax_difference: float  # Absolute savings
    recommendation_reason: str
    is_deterministic: bool = True
