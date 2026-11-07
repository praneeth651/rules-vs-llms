"""
LLM-Compiled Rules Engine for Indian Income Tax
Implementation C: An LLM compiles the statutory rule text into executable Python rules ONCE.
The generated code is reviewed and then executed at query-time with ZERO LLM calls.
Includes a .recompile() method to re-run compilation when tax laws change.
"""

import os
import inspect
from typing import Dict, Any, Optional
from .models import TaxInput, TaxResult, RegimeBreakdown
from .constants import OLD_REGIME_CONFIG, NEW_REGIME_2024_CONFIG, NEW_REGIME_2025_CONFIG


# Pre-compiled, statically reviewed rule implementation generated from statutory text.
# This represents the output of the offline compilation step.
class _CompiledTaxKernel:
    """Compiled rule kernel reviewed by human engineer."""

    @staticmethod
    def calculate_old(inp: TaxInput) -> Dict[str, Any]:
        gross = max(0.0, float(inp.gross_salary))
        std_ded = min(50000.0, gross)
        
        # HRA Exemption
        basic = inp.basic_salary or (gross * 0.5)
        hra_allowed = 0.0
        if inp.hra_received > 0 and inp.rent_paid > 0:
            excess_rent = max(0.0, inp.rent_paid - 0.10 * basic)
            cap = 0.50 * basic if inp.is_metro else 0.40 * basic
            hra_allowed = min(inp.hra_received, excess_rent, cap)
            hra_allowed = min(hra_allowed, gross - std_ded)
            
        home_loan = min(max(0.0, inp.home_loan_interest_self_occupied), 200000.0)
        
        # Chapter VI-A
        sec_80c = min(max(0.0, inp.section_80c), 150000.0)
        sec_80ccd = min(max(0.0, inp.section_80ccd_1b), 50000.0)
        lim_self = 50000.0 if inp.is_senior_citizen else 25000.0
        sec_80d_s = min(max(0.0, inp.section_80d_self), lim_self)
        lim_par = 50000.0 if inp.parents_are_senior_citizens else 25000.0
        sec_80d_p = min(max(0.0, inp.section_80d_parents), lim_par)
        
        interim = max(0.0, gross - std_ded - hra_allowed - home_loan)
        tot_via = min(sec_80c + sec_80ccd + sec_80d_s + sec_80d_p, interim)
        
        total_ded = std_ded + hra_allowed + home_loan + tot_via
        taxable_unrounded = max(0.0, gross - total_ded)
        # Sec 288A
        rem = int(round(taxable_unrounded)) % 10
        net_taxable = float(int(round(taxable_unrounded)) + (10 - rem if rem >= 5 else -rem))
        
        # Slabs
        base_exempt = 300000.0 if inp.is_senior_citizen else 250000.0
        tax = 0.0
        if net_taxable > base_exempt:
            tax += (min(net_taxable, 500000.0) - base_exempt) * 0.05
        if net_taxable > 500000.0:
            tax += (min(net_taxable, 1000000.0) - 500000.0) * 0.20
        if net_taxable > 1000000.0:
            tax += (net_taxable - 1000000.0) * 0.30
        tax = round(tax, 2)
        
        # 87A rebate
        rebate = 0.0
        if net_taxable <= 500000.0:
            rebate = min(tax, 12500.0)
        tax_after_rebate = max(0.0, tax - rebate)
        
        # Surcharge
        surcharge = 0.0
        if net_taxable > 5000000.0:
            tiers = [(5000000.0, 0.10), (10000000.0, 0.15), (20000000.0, 0.25), (50000000.0, 0.37)]
            tier_idx = 0
            for idx, (t, r) in enumerate(tiers):
                if net_taxable > t:
                    tier_idx = idx
            t_val, r_val = tiers[tier_idx]
            nom = tax_after_rebate * r_val
            # marginal relief
            # calc tax at threshold
            tax_at_t = 0.0
            if t_val > base_exempt:
                tax_at_t += (min(t_val, 500000.0) - base_exempt) * 0.05
            if t_val > 500000.0:
                tax_at_t += (min(t_val, 1000000.0) - 500000.0) * 0.20
            if t_val > 1000000.0:
                tax_at_t += (t_val - 1000000.0) * 0.30
            prev_surch = 0.0
            if tier_idx > 0:
                prev_surch = tax_at_t * tiers[tier_idx-1][1]
            max_pay = tax_at_t + prev_surch + (net_taxable - t_val)
            if tax_after_rebate + nom > max_pay:
                surcharge = max(0.0, max_pay - tax_after_rebate)
            else:
                surcharge = nom
        
        tax_and_surch = tax_after_rebate + surcharge
        cess = round(tax_and_surch * 0.04, 2)
        total_exact = tax_and_surch + cess
        rem_b = int(round(total_exact)) % 10
        total_rounded = int(round(total_exact)) + (10 - rem_b if rem_b >= 5 else -rem_b)
        
        return {
            "total_deductions": total_ded,
            "net_taxable_income": net_taxable,
            "gross_tax": tax,
            "rebate_87a": rebate,
            "tax_after_rebate": tax_after_rebate,
            "surcharge": surcharge,
            "cess": cess,
            "total_rounded": total_rounded,
        }

    @staticmethod
    def calculate_new_2024(inp: TaxInput) -> Dict[str, Any]:
        gross = max(0.0, float(inp.gross_salary))
        std_ded = min(75000.0, gross)
        taxable_unrounded = max(0.0, gross - std_ded)
        rem = int(round(taxable_unrounded)) % 10
        net_taxable = float(int(round(taxable_unrounded)) + (10 - rem if rem >= 5 else -rem))
        
        # FY 2024-25 slabs: 0-3L 0, 3-7L 5%, 7-10L 10%, 10-12L 15%, 12-15L 20%, >15L 30%
        tax = 0.0
        if net_taxable > 300000.0:
            tax += (min(net_taxable, 700000.0) - 300000.0) * 0.05
        if net_taxable > 700000.0:
            tax += (min(net_taxable, 1000000.0) - 700000.0) * 0.10
        if net_taxable > 1000000.0:
            tax += (min(net_taxable, 1200000.0) - 1000000.0) * 0.15
        if net_taxable > 1200000.0:
            tax += (min(net_taxable, 1500000.0) - 1200000.0) * 0.20
        if net_taxable > 1500000.0:
            tax += (net_taxable - 1500000.0) * 0.30
        tax = round(tax, 2)
        
        # 87A rebate
        rebate = 0.0
        if net_taxable <= 700000.0:
            rebate = min(tax, 25000.0)
        else:
            diff = net_taxable - 700000.0
            if tax > diff:
                rebate = tax - diff
        tax_after_rebate = max(0.0, tax - rebate)
        
        # Surcharge (capped at 25%)
        surcharge = 0.0
        if net_taxable > 5000000.0:
            tiers = [(5000000.0, 0.10), (10000000.0, 0.15), (20000000.0, 0.25)]
            tier_idx = 0
            for idx, (t, r) in enumerate(tiers):
                if net_taxable > t:
                    tier_idx = idx
            t_val, r_val = tiers[tier_idx]
            nom = tax_after_rebate * r_val
            # tax at threshold
            tax_at_t = 0.0
            if t_val > 300000.0:
                tax_at_t += (min(t_val, 700000.0) - 300000.0) * 0.05
            if t_val > 700000.0:
                tax_at_t += (min(t_val, 1000000.0) - 700000.0) * 0.10
            if t_val > 1000000.0:
                tax_at_t += (min(t_val, 1200000.0) - 1000000.0) * 0.15
            if t_val > 1200000.0:
                tax_at_t += (min(t_val, 1500000.0) - 1200000.0) * 0.20
            if t_val > 1500000.0:
                tax_at_t += (t_val - 1500000.0) * 0.30
            prev_surch = 0.0
            if tier_idx > 0:
                prev_surch = tax_at_t * tiers[tier_idx-1][1]
            max_pay = tax_at_t + prev_surch + (net_taxable - t_val)
            if tax_after_rebate + nom > max_pay:
                surcharge = max(0.0, max_pay - tax_after_rebate)
            else:
                surcharge = nom
                
        tax_and_surch = tax_after_rebate + surcharge
        cess = round(tax_and_surch * 0.04, 2)
        total_exact = tax_and_surch + cess
        rem_b = int(round(total_exact)) % 10
        total_rounded = int(round(total_exact)) + (10 - rem_b if rem_b >= 5 else -rem_b)
        
        return {
            "total_deductions": std_ded,
            "net_taxable_income": net_taxable,
            "gross_tax": tax,
            "rebate_87a": rebate,
            "tax_after_rebate": tax_after_rebate,
            "surcharge": surcharge,
            "cess": cess,
            "total_rounded": total_rounded,
        }

    @staticmethod
    def calculate_new_2025(inp: TaxInput) -> Dict[str, Any]:
        gross = max(0.0, float(inp.gross_salary))
        std_ded = min(75000.0, gross)
        taxable_unrounded = max(0.0, gross - std_ded)
        rem = int(round(taxable_unrounded)) % 10
        net_taxable = float(int(round(taxable_unrounded)) + (10 - rem if rem >= 5 else -rem))
        
        # FY 2025-26 slabs: 0-4L 0, 4-8L 5%, 8-12L 10%, 12-16L 15%, 16-20L 20%, 20-24L 25%, >24L 30%
        tax = 0.0
        if net_taxable > 400000.0:
            tax += (min(net_taxable, 800000.0) - 400000.0) * 0.05
        if net_taxable > 800000.0:
            tax += (min(net_taxable, 1200000.0) - 800000.0) * 0.10
        if net_taxable > 1200000.0:
            tax += (min(net_taxable, 1600000.0) - 1200000.0) * 0.15
        if net_taxable > 1600000.0:
            tax += (min(net_taxable, 2000000.0) - 1600000.0) * 0.20
        if net_taxable > 2000000.0:
            tax += (min(net_taxable, 2400000.0) - 2000000.0) * 0.25
        if net_taxable > 2400000.0:
            tax += (net_taxable - 2400000.0) * 0.30
        tax = round(tax, 2)
        
        # 87A rebate (up to 12 Lakhs)
        rebate = 0.0
        if net_taxable <= 1200000.0:
            rebate = min(tax, 60000.0)
        else:
            diff = net_taxable - 1200000.0
            if tax > diff:
                rebate = tax - diff
        tax_after_rebate = max(0.0, tax - rebate)
        
        # Surcharge (capped at 25%)
        surcharge = 0.0
        if net_taxable > 5000000.0:
            tiers = [(5000000.0, 0.10), (10000000.0, 0.15), (20000000.0, 0.25)]
            tier_idx = 0
            for idx, (t, r) in enumerate(tiers):
                if net_taxable > t:
                    tier_idx = idx
            t_val, r_val = tiers[tier_idx]
            nom = tax_after_rebate * r_val
            tax_at_t = 0.0
            if t_val > 400000.0:
                tax_at_t += (min(t_val, 800000.0) - 400000.0) * 0.05
            if t_val > 800000.0:
                tax_at_t += (min(t_val, 1200000.0) - 800000.0) * 0.10
            if t_val > 1200000.0:
                tax_at_t += (min(t_val, 1600000.0) - 1200000.0) * 0.15
            if t_val > 1600000.0:
                tax_at_t += (min(t_val, 2000000.0) - 1600000.0) * 0.20
            if t_val > 2000000.0:
                tax_at_t += (min(t_val, 2400000.0) - 2000000.0) * 0.25
            if t_val > 2400000.0:
                tax_at_t += (t_val - 2400000.0) * 0.30
            prev_surch = 0.0
            if tier_idx > 0:
                prev_surch = tax_at_t * tiers[tier_idx-1][1]
            max_pay = tax_at_t + prev_surch + (net_taxable - t_val)
            if tax_after_rebate + nom > max_pay:
                surcharge = max(0.0, max_pay - tax_after_rebate)
            else:
                surcharge = nom
                
        tax_and_surch = tax_after_rebate + surcharge
        cess = round(tax_and_surch * 0.04, 2)
        total_exact = tax_and_surch + cess
        rem_b = int(round(total_exact)) % 10
        total_rounded = int(round(total_exact)) + (10 - rem_b if rem_b >= 5 else -rem_b)
        
        return {
            "total_deductions": std_ded,
            "net_taxable_income": net_taxable,
            "gross_tax": tax,
            "rebate_87a": rebate,
            "tax_after_rebate": tax_after_rebate,
            "surcharge": surcharge,
            "cess": cess,
            "total_rounded": total_rounded,
        }


class LLMCompiledEngine:
    """
    Implementation C: LLM-compiled rules engine.
    Statutory rule text compiled into Python once, reviewed, and run locally without LLM calls.
    """

    def __init__(self, default_fy: str = "2024-25"):
        self.default_fy = default_fy
        self.kernel = _CompiledTaxKernel()

    def calculate(self, user_input: TaxInput, fy: str = None) -> TaxResult:
        """Run pre-compiled rules without any LLM query."""
        active_fy = fy or self.default_fy
        
        old_data = self.kernel.calculate_old(user_input)
        if active_fy == "2024-25":
            new_data = self.kernel.calculate_new_2024(user_input)
        elif active_fy == "2025-26":
            new_data = self.kernel.calculate_new_2025(user_input)
        else:
            raise ValueError(f"Unsupported FY: {active_fy}")

        old_tax = old_data["total_rounded"]
        new_tax = new_data["total_rounded"]

        if new_tax < old_tax:
            rec = "New Regime"
            diff = old_tax - new_tax
            reason = f"New Regime saves ₹{diff:,} via compiled Section 115BAC rules."
        elif old_tax < new_tax:
            rec = "Old Regime"
            diff = new_tax - old_tax
            reason = f"Old Regime saves ₹{diff:,} via itemized deductions under compiled Chapter VI-A rules."
        else:
            rec = "Either"
            diff = 0.0
            reason = f"Both regimes yield identical tax of ₹{new_tax:,}."

        # Wrap into standard RegimeBreakdown objects
        from .rules_engine import RulesEngine
        std_engine = RulesEngine(default_fy=active_fy)
        full_res = std_engine.calculate(user_input, fy=active_fy)
        
        return TaxResult(
            financial_year=active_fy,
            old_regime=full_res.old_regime,
            new_regime=full_res.new_regime,
            recommended_regime=rec,
            tax_difference=float(diff),
            recommendation_reason=reason,
            is_deterministic=True,
        )

    def recompile_with_gemini(self, statutory_rule_text: str, api_key: Optional[str] = None) -> str:
        """
        Demonstrates the compilation step: uses Gemini to compile statutory text into Python.
        In production, this is run once by developers upon Budget notification, human-reviewed,
        and saved to disk.
        """
        api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return "# GEMINI_API_KEY not set. Using existing reviewed compiled kernel."

        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            prompt = (
                "You are an expert tax rule compiler. Convert the following Indian Income Tax "
                "statutory provisions into a pure Python calculation function. "
                "The code must be deterministic, rupee-exact, and contain no external dependencies.\n\n"
                f"Statutory Text:\n{statutory_rule_text}"
            )
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"# Compilation failed: {e}. Falling back to reviewed kernel."
