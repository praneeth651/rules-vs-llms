"""
Hand-Coded Rules Engine for Indian Income Tax
Salary Income Only.
Covers FY 2024-25 (AY 2025-26) and FY 2025-26 (AY 2026-27).
Deterministic, rupee-exact, with full audit trail and statutory clause citations.
"""

from typing import List, Tuple, Dict, Any
from .models import TaxInput, DeductionItem, SlabTaxItem, RegimeBreakdown, TaxResult
from .constants import (
    CLAUSE_CITATIONS,
    OLD_REGIME_CONFIG,
    NEW_REGIME_2024_CONFIG,
    NEW_REGIME_2025_CONFIG,
    HEALTH_AND_EDUCATION_CESS_RATE,
)


def round_section_288a(amount: float) -> float:
    """
    Section 288A: Round taxable income to the nearest multiple of ten rupees.
    If the last digit is 5 or more, round up to the next multiple of 10.
    """
    amount_int = int(round(amount))
    rem = amount_int % 10
    if rem >= 5:
        return float(amount_int + (10 - rem))
    else:
        return float(amount_int - rem)


def round_section_288b(amount: float) -> int:
    """
    Section 288B: Round total tax payable to the nearest multiple of ten rupees.
    If the last digit is 5 or more, round up to the next multiple of 10.
    """
    amount_int = int(round(amount))
    rem = amount_int % 10
    if rem >= 5:
        return amount_int + (10 - rem)
    else:
        return amount_int - rem


class RulesEngine:
    """
    Implementation A: Hand-coded rules engine.
    Calculates tax under both Old and New regimes with zero LLM dependence.
    """

    def __init__(self, default_fy: str = "2024-25"):
        self.default_fy = default_fy

    def calculate(self, user_input: TaxInput, fy: str = None) -> TaxResult:
        """Calculate income tax under both regimes for the given financial year."""
        active_fy = fy or self.default_fy
        if active_fy not in ("2024-25", "2025-26"):
            raise ValueError(f"Unsupported FY: {active_fy}. Supported: '2024-25', '2025-26'.")

        old_breakdown = self.calculate_old_regime(user_input, active_fy)
        new_breakdown = self.calculate_new_regime(user_input, active_fy)

        # Recommendation logic
        old_tax = old_breakdown.total_tax_payable_rounded
        new_tax = new_breakdown.total_tax_payable_rounded

        if new_tax < old_tax:
            recommended = "New Regime"
            diff = old_tax - new_tax
            reason = (
                f"New Regime saves ₹{diff:,} compared to Old Regime "
                f"(₹{new_tax:,} vs ₹{old_tax:,}). "
                f"Under the New Regime default provision (Sec 115BAC), "
                f"lower slab rates and higher basic rebate yield a lower tax liability."
            )
        elif old_tax < new_tax:
            recommended = "Old Regime"
            diff = new_tax - old_tax
            reason = (
                f"Old Regime saves ₹{diff:,} compared to New Regime "
                f"(₹{old_tax:,} vs ₹{new_tax:,}). "
                f"Your itemized deductions under Sec 80C, 80D, 24(b), and HRA (total ₹{old_breakdown.total_deductions:,.0f}) "
                f"reduce your taxable income significantly enough to beat the lower slab rates of the New Regime."
            )
        else:
            recommended = "Either"
            diff = 0.0
            reason = (
                f"Both regimes yield identical tax liability of ₹{new_tax:,}. "
                f"New Regime is recommended by default under Section 115BAC(1A) for simplified filing."
            )

        return TaxResult(
            financial_year=active_fy,
            old_regime=old_breakdown,
            new_regime=new_breakdown,
            recommended_regime=recommended,
            tax_difference=float(diff),
            recommendation_reason=reason,
            is_deterministic=True,
        )

    def calculate_old_regime(self, user_input: TaxInput, fy: str) -> RegimeBreakdown:
        """Calculate Old Tax Regime step-by-step with citations."""
        config = OLD_REGIME_CONFIG
        audit: List[str] = []
        deductions: List[DeductionItem] = []

        gross = max(0.0, float(user_input.gross_salary))
        audit.append(f"Gross Salary: ₹{gross:,.2f}")

        # 1. Standard Deduction (Sec 16(ia))
        std_ded_allowed = min(config["standard_deduction"], gross)
        deductions.append(
            DeductionItem(
                section="Section 16(ia)",
                description="Standard Deduction for Salaried Employees",
                claimed_amount=config["standard_deduction"],
                allowed_amount=std_ded_allowed,
                max_limit=config["standard_deduction"],
                statutory_clause=CLAUSE_CITATIONS["SEC_16_IA_OLD"],
            )
        )
        audit.append(f"Standard Deduction allowed: ₹{std_ded_allowed:,.2f} [Sec 16(ia)]")

        # 2. HRA Exemption (Sec 10(13A) read with Rule 2A)
        basic = user_input.basic_salary or (gross * 0.5)
        hra_received = max(0.0, user_input.hra_received)
        rent_paid = max(0.0, user_input.rent_paid)
        hra_allowed = 0.0

        if hra_received > 0 and rent_paid > 0:
            ten_pct_basic = 0.10 * basic
            rent_excess = max(0.0, rent_paid - ten_pct_basic)
            salary_pct_limit = 0.50 * basic if user_input.is_metro else 0.40 * basic
            hra_allowed = min(hra_received, rent_excess, salary_pct_limit)
            hra_allowed = min(hra_allowed, gross - std_ded_allowed)

        deductions.append(
            DeductionItem(
                section="Section 10(13A)",
                description="House Rent Allowance (HRA) Exemption",
                claimed_amount=hra_received,
                allowed_amount=hra_allowed,
                max_limit=None,
                statutory_clause=CLAUSE_CITATIONS["SEC_10_13A"],
            )
        )
        audit.append(
            f"HRA Exemption allowed: ₹{hra_allowed:,.2f} [Sec 10(13A) read with Rule 2A; metro={user_input.is_metro}]"
        )

        # 3. Home Loan Interest on Self-Occupied House (Section 24(b))
        home_loan_claimed = max(0.0, user_input.home_loan_interest_self_occupied)
        home_loan_allowed = min(home_loan_claimed, config["max_home_loan_interest"])
        deductions.append(
            DeductionItem(
                section="Section 24(b)",
                description="Deduction for Interest on Housing Loan (Self-Occupied)",
                claimed_amount=home_loan_claimed,
                allowed_amount=home_loan_allowed,
                max_limit=config["max_home_loan_interest"],
                statutory_clause=CLAUSE_CITATIONS["SEC_24_B"],
            )
        )
        audit.append(f"Home loan interest allowed: ₹{home_loan_allowed:,.2f} [Sec 24(b)]")

        # Income after Head Salary deductions & House Property Loss
        interim_income = max(0.0, gross - std_ded_allowed - hra_allowed - home_loan_allowed)

        # 4. Chapter VI-A Deductions
        # Sec 80C
        claimed_80c = max(0.0, user_input.section_80c)
        allowed_80c = min(claimed_80c, config["max_80c"])
        deductions.append(
            DeductionItem(
                section="Section 80C",
                description="Deduction for Life Insurance, PF, PPF, ELSS, etc.",
                claimed_amount=claimed_80c,
                allowed_amount=allowed_80c,
                max_limit=config["max_80c"],
                statutory_clause=CLAUSE_CITATIONS["SEC_80C"],
            )
        )

        # Sec 80CCD(1B)
        claimed_80ccd = max(0.0, user_input.section_80ccd_1b)
        allowed_80ccd = min(claimed_80ccd, config["max_80ccd_1b"])
        deductions.append(
            DeductionItem(
                section="Section 80CCD(1B)",
                description="Deduction for voluntary contribution to National Pension System (NPS)",
                claimed_amount=claimed_80ccd,
                allowed_amount=allowed_80ccd,
                max_limit=config["max_80ccd_1b"],
                statutory_clause=CLAUSE_CITATIONS["SEC_80CCD_1B"],
            )
        )

        # Sec 80D Self
        claimed_80d_self = max(0.0, user_input.section_80d_self)
        limit_80d_self = config["max_80d_self_senior"] if user_input.is_senior_citizen else config["max_80d_self_nonsenior"]
        allowed_80d_self = min(claimed_80d_self, limit_80d_self)
        deductions.append(
            DeductionItem(
                section="Section 80D (Self)",
                description="Medical insurance premium for self and dependent family",
                claimed_amount=claimed_80d_self,
                allowed_amount=allowed_80d_self,
                max_limit=limit_80d_self,
                statutory_clause=CLAUSE_CITATIONS["SEC_80D_SELF"],
            )
        )

        # Sec 80D Parents
        claimed_80d_parents = max(0.0, user_input.section_80d_parents)
        limit_80d_parents = config["max_80d_parents_senior"] if user_input.parents_are_senior_citizens else config["max_80d_parents_nonsenior"]
        allowed_80d_parents = min(claimed_80d_parents, limit_80d_parents)
        deductions.append(
            DeductionItem(
                section="Section 80D (Parents)",
                description="Medical insurance premium for parents",
                claimed_amount=claimed_80d_parents,
                allowed_amount=allowed_80d_parents,
                max_limit=limit_80d_parents,
                statutory_clause=CLAUSE_CITATIONS["SEC_80D_PARENTS"],
            )
        )

        # Cap Chapter VI-A deductions so taxable income does not become negative
        total_ch_via = allowed_80c + allowed_80ccd + allowed_80d_self + allowed_80d_parents
        allowed_ch_via = min(total_ch_via, interim_income)

        total_deductions = std_ded_allowed + hra_allowed + home_loan_allowed + allowed_ch_via
        taxable_income_unrounded = max(0.0, gross - total_deductions)
        net_taxable_income = round_section_288a(taxable_income_unrounded)

        audit.append(f"Total deductions allowed: ₹{total_deductions:,.2f}")
        audit.append(f"Net Taxable Income (Sec 288A rounded): ₹{net_taxable_income:,.2f}")

        # Slab computation
        slabs = config["slabs_senior"] if user_input.is_senior_citizen else config["slabs_general"]
        slab_taxes, gross_tax = self._calculate_slabs(net_taxable_income, slabs)

        audit.append(f"Gross Tax before Rebate: ₹{gross_tax:,.2f}")

        # Section 87A Rebate
        rebate_87a = 0.0
        if net_taxable_income <= config["rebate_87a_max_income"]:
            rebate_87a = min(gross_tax, config["rebate_87a_max_amount"])
            audit.append(f"Section 87A rebate applied: ₹{rebate_87a:,.2f} [Sec 87A]")

        tax_after_rebate = max(0.0, gross_tax - rebate_87a)
        audit.append(f"Tax after Rebate: ₹{tax_after_rebate:,.2f}")

        # Surcharge & Marginal Relief
        surcharge_rate, surcharge_nom, marginal_relief, final_surcharge = self._calculate_surcharge(
            net_taxable_income, tax_after_rebate, config["surcharge_tiers"], slabs, is_old_regime=True
        )

        if final_surcharge > 0:
            audit.append(
                f"Surcharge: ₹{final_surcharge:,.2f} (Rate: {surcharge_rate*100:.0f}%, Relief: ₹{marginal_relief:,.2f})"
            )

        tax_and_surcharge = tax_after_rebate + final_surcharge

        # Health & Education Cess (4%)
        cess = round(tax_and_surcharge * HEALTH_AND_EDUCATION_CESS_RATE, 2)
        audit.append(f"Health & Education Cess (4%): ₹{cess:,.2f} [Sec 4]")

        total_tax_exact = tax_and_surcharge + cess
        total_tax_rounded = round_section_288b(total_tax_exact)
        audit.append(f"Total Tax Payable (Sec 288B rounded): ₹{total_tax_rounded:,}")

        return RegimeBreakdown(
            regime_name="Old Regime",
            financial_year=fy,
            gross_salary=gross,
            deductions=deductions,
            total_deductions=total_deductions,
            net_taxable_income=net_taxable_income,
            slab_taxes=slab_taxes,
            gross_tax_before_rebate=gross_tax,
            rebate_87a=rebate_87a,
            tax_after_rebate=tax_after_rebate,
            surcharge_rate_percent=surcharge_rate * 100.0,
            surcharge_before_marginal_relief=surcharge_nom,
            marginal_relief_surcharge=marginal_relief,
            final_surcharge=final_surcharge,
            tax_and_surcharge=tax_and_surcharge,
            health_education_cess_4pct=cess,
            total_tax_payable_exact=total_tax_exact,
            total_tax_payable_rounded=total_tax_rounded,
            audit_trail=audit,
        )

    def calculate_new_regime(self, user_input: TaxInput, fy: str) -> RegimeBreakdown:
        """Calculate New Tax Regime (Section 115BAC) step-by-step with citations."""
        config = NEW_REGIME_2024_CONFIG if fy == "2024-25" else NEW_REGIME_2025_CONFIG
        audit: List[str] = []
        deductions: List[DeductionItem] = []

        gross = max(0.0, float(user_input.gross_salary))
        audit.append(f"Gross Salary: ₹{gross:,.2f}")

        # Standard Deduction under New Regime (Sec 16(ia))
        std_limit = config["standard_deduction"]
        std_ded_allowed = min(std_limit, gross)
        citation = CLAUSE_CITATIONS["SEC_16_IA_NEW_2024"] if fy == "2024-25" else CLAUSE_CITATIONS["SEC_16_IA_NEW_2025"]
        deductions.append(
            DeductionItem(
                section="Section 16(ia)",
                description="Standard Deduction under New Regime (Sec 115BAC)",
                claimed_amount=std_limit,
                allowed_amount=std_ded_allowed,
                max_limit=std_limit,
                statutory_clause=citation,
            )
        )
        audit.append(f"Standard Deduction allowed: ₹{std_ded_allowed:,.2f} [{citation}]")
        audit.append("Note: Chapter VI-A (80C, 80D), HRA (10(13A)), and Home loan interest (24(b)) are NOT allowed under New Regime (Sec 115BAC(2)).")

        total_deductions = std_ded_allowed
        taxable_unrounded = max(0.0, gross - total_deductions)
        net_taxable_income = round_section_288a(taxable_unrounded)
        audit.append(f"Net Taxable Income (Sec 288A rounded): ₹{net_taxable_income:,.2f}")

        # Slabs calculation
        slab_taxes, gross_tax = self._calculate_slabs(net_taxable_income, config["slabs"])
        audit.append(f"Gross Tax before Rebate: ₹{gross_tax:,.2f}")

        # Section 87A Rebate & Marginal Rebate
        rebate_87a = 0.0
        max_rebate_income = config["rebate_87a_max_income"]
        max_rebate_amount = config["rebate_87a_max_amount"]

        if net_taxable_income <= max_rebate_income:
            rebate_87a = min(gross_tax, max_rebate_amount)
            audit.append(f"Section 87A full rebate: ₹{rebate_87a:,.2f} (Tax becomes ₹0)")
        else:
            # Marginal rebate under Section 87A proviso for New Regime:
            # Tax payable cannot exceed (Net Taxable Income - Threshold)
            excess_income = net_taxable_income - max_rebate_income
            if gross_tax > excess_income:
                rebate_87a = gross_tax - excess_income
                audit.append(
                    f"Section 87A marginal rebate: ₹{rebate_87a:,.2f} "
                    f"(Tax capped at excess income ₹{excess_income:,.2f} over threshold ₹{max_rebate_income:,.2f})"
                )

        tax_after_rebate = max(0.0, gross_tax - rebate_87a)
        audit.append(f"Tax after Rebate: ₹{tax_after_rebate:,.2f}")

        # Surcharge & Marginal Relief
        surcharge_rate, surcharge_nom, marginal_relief, final_surcharge = self._calculate_surcharge(
            net_taxable_income, tax_after_rebate, config["surcharge_tiers"], config["slabs"], is_old_regime=False
        )

        if final_surcharge > 0:
            audit.append(
                f"Surcharge: ₹{final_surcharge:,.2f} (Rate: {surcharge_rate*100:.0f}%, Relief: ₹{marginal_relief:,.2f})"
            )

        tax_and_surcharge = tax_after_rebate + final_surcharge
        cess = round(tax_and_surcharge * HEALTH_AND_EDUCATION_CESS_RATE, 2)
        audit.append(f"Health & Education Cess (4%): ₹{cess:,.2f}")

        total_tax_exact = tax_and_surcharge + cess
        total_tax_rounded = round_section_288b(total_tax_exact)
        audit.append(f"Total Tax Payable (Sec 288B rounded): ₹{total_tax_rounded:,}")

        return RegimeBreakdown(
            regime_name="New Regime",
            financial_year=fy,
            gross_salary=gross,
            deductions=deductions,
            total_deductions=total_deductions,
            net_taxable_income=net_taxable_income,
            slab_taxes=slab_taxes,
            gross_tax_before_rebate=gross_tax,
            rebate_87a=rebate_87a,
            tax_after_rebate=tax_after_rebate,
            surcharge_rate_percent=surcharge_rate * 100.0,
            surcharge_before_marginal_relief=surcharge_nom,
            marginal_relief_surcharge=marginal_relief,
            final_surcharge=final_surcharge,
            tax_and_surcharge=tax_and_surcharge,
            health_education_cess_4pct=cess,
            total_tax_payable_exact=total_tax_exact,
            total_tax_payable_rounded=total_tax_rounded,
            audit_trail=audit,
        )

    def _calculate_slabs(
        self, taxable_income: float, slabs: List[Tuple[float, float, float, str]]
    ) -> Tuple[List[SlabTaxItem], float]:
        """Compute slab-by-slab progressive tax."""
        slab_items: List[SlabTaxItem] = []
        total_tax = 0.0

        for lower, upper, rate, description in slabs:
            if taxable_income > lower:
                taxable_in_slab = min(taxable_income, upper) - lower
                tax_in_slab = round(taxable_in_slab * rate, 2)
                total_tax += tax_in_slab
                slab_items.append(
                    SlabTaxItem(
                        slab_range=f"₹{lower:,.0f} to {'₹' + f'{upper:,.0f}' if upper != float('inf') else 'Above'}",
                        taxable_in_slab=taxable_in_slab,
                        rate_percent=rate * 100.0,
                        tax_amount=tax_in_slab,
                        statutory_clause=description,
                    )
                )

        return slab_items, round(total_tax, 2)

    def _calculate_surcharge(
        self,
        income: float,
        tax: float,
        surcharge_tiers: List[Tuple[float, float]],
        slabs: List[Tuple[float, float, float, str]],
        is_old_regime: bool,
    ) -> Tuple[float, float, float, float]:
        """
        Calculate surcharge with exact marginal relief according to statutory provisos.
        Returns: (surcharge_rate, nominal_surcharge, marginal_relief, final_surcharge)
        """
        # Surcharge only applies if taxable income > 50,00,000
        applicable_tier_idx = -1
        for i, (threshold, rate) in enumerate(surcharge_tiers):
            if income > threshold:
                applicable_tier_idx = i

        if applicable_tier_idx == -1:
            return 0.0, 0.0, 0.0, 0.0

        threshold, rate = surcharge_tiers[applicable_tier_idx]
        nominal_surcharge = round(tax * rate, 2)
        current_total = tax + nominal_surcharge

        # Marginal relief check:
        # Total tax + surcharge cannot exceed:
        # [Tax + Surcharge payable at threshold] + (Income - threshold)
        # Compute tax at threshold:
        _, tax_at_threshold = self._calculate_slabs(threshold, slabs)
        
        # If threshold itself had surcharge (e.g. 1 Cr threshold where 50L had 10% surcharge)
        surcharge_at_threshold = 0.0
        if applicable_tier_idx > 0:
            prev_threshold, prev_rate = surcharge_tiers[applicable_tier_idx - 1]
            surcharge_at_threshold = round(tax_at_threshold * prev_rate, 2)

        max_payable = tax_at_threshold + surcharge_at_threshold + (income - threshold)

        marginal_relief = 0.0
        if current_total > max_payable:
            marginal_relief = round(current_total - max_payable, 2)
            final_surcharge = max(0.0, round(nominal_surcharge - marginal_relief, 2))
        else:
            final_surcharge = nominal_surcharge

        return rate, nominal_surcharge, marginal_relief, final_surcharge
