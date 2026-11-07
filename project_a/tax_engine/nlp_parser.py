"""
Plain-Language Input Parser for Indian Income Tax Engine
Converts natural language, Hinglish, informal, and messy user text into structured TaxInput.
Identifies missing or ambiguous information and generates targeted clarifying questions instead of guessing.
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from .models import TaxInput


@dataclass
class ParsedQuery:
    """Result of parsing a natural language query."""
    raw_query: str
    tax_input: Optional[TaxInput]
    is_complete: bool
    clarifying_questions: List[str] = field(default_factory=list)
    detected_entities: Dict[str, Any] = field(default_factory=dict)
    contradictions: List[str] = field(default_factory=list)
    ambiguities: List[str] = field(default_factory=list)


METRO_CITIES = {
    "mumbai", "bombay", "delhi", "new delhi", "ncr", "kolkata", "calcutta", "chennai", "madras"
}


def parse_indian_number(text: str) -> Optional[float]:
    """Parse numbers expressed in Indian numbering formats (Lakhs, Crores, LPA, K, etc.)."""
    cleaned = text.lower().replace(",", "").strip()
    
    # Matches patterns like: 12.5 lakh, 15l, 1.2 cr, 50k, 50000, 1.5 lakhs, 18 lpa
    m_cr = re.search(r"(\d+(?:\.\d+)?)\s*(?:cr|crore|crores)", cleaned)
    if m_cr:
        return float(m_cr.group(1)) * 10000000.0

    m_lpa = re.search(r"(\d+(?:\.\d+)?)\s*lpa\b", cleaned)
    if m_lpa:
        return float(m_lpa.group(1)) * 100000.0

    m_lakh = re.search(r"(\d+(?:\.\d+)?)\s*(?:lakh|lakhs|lac|lacs|l|big ones)\b", cleaned)
    if m_lakh:
        return float(m_lakh.group(1)) * 100000.0

    m_k = re.search(r"(\d+(?:\.\d+)?)\s*(?:k|thousand|hazar)\b", cleaned)
    if m_k:
        return float(m_k.group(1)) * 1000.0

    # Bare number (e.g. 50000, 1800000)
    m_num = re.search(r"\b(\d{4,9})\b", cleaned)
    if m_num:
        return float(m_num.group(1))

    return None


def extract_monthly_or_annual(text: str, default_to_annual: bool = True) -> bool:
    """Returns True if the frequency is annual, False if monthly."""
    lowered = text.lower()
    if any(k in lowered for k in ["per month", "/month", "pm", "p.m.", "monthly", "har mahine", "mahina"]):
        return False
    if any(k in lowered for k in ["per annum", "/annum", "pa", "p.a.", "lpa", "annual", "annually", "salana", "ctc"]):
        return True
    return default_to_annual


class NaturalLanguageTaxParser:
    """
    Parser that turns free-text descriptions into structured TaxInput.
    Asks clarifying questions whenever information is missing, ambiguous, or contradictory.
    """

    def parse(self, text: str) -> ParsedQuery:
        entities: Dict[str, Any] = {}
        questions: List[str] = []
        contradictions: List[str] = []
        ambiguities: List[str] = []

        lowered = text.lower()

        # 1. Age & Senior Citizen Detection
        age = None
        age_match = re.search(r"\b(\d{1,3})\s*(?:years? old|yr|yrs|age)\b", lowered)
        if age_match:
            age = int(age_match.group(1))
            entities["age"] = age

        is_senior = False
        if "senior citizen" in lowered or "senior" in lowered or "retired" in lowered or "pensioner" in lowered:
            is_senior = True
            entities["is_senior_citizen"] = True

        if age is not None:
            if age >= 60:
                is_senior = True
            elif is_senior and age < 60:
                contradictions.append(
                    f"You mentioned being age {age}, but also referred to yourself as a senior citizen. "
                    "Under Section 80D/First Schedule, senior citizen status requires age 60 or above."
                )

        # 2. Parents Senior Citizen Status
        parents_senior = False
        has_parents_insurance = False
        if any(w in lowered for w in ["parents", "mother", "father", "mummy", "papa"]):
            if "senior" in lowered:
                parents_senior = True
                entities["parents_are_senior_citizens"] = True

        # 3. Gross Salary Extraction
        gross_salary = None
        salary_patterns = [
            r"(?:salary|ctc|package|earning|income|kamata|kamaata|aamdani|compensation)\s*(?:is|of|=|:)?\s*(?:rs\.?|inr|₹)?\s*([0-9.,]+\s*(?:lakhs?|lacs?|lac|l|cr|crore|k|thousand|lpa)?(?:\s*(?:per\s*(?:annum|month|year)|pa|pm|p\.a\.|p\.m\.))?)",
            r"(?:rs\.?|inr|₹)\s*([0-9.,]+\s*(?:lakhs?|lacs?|lac|l|cr|crore|k|thousand|lpa)?)\s*(?:salary|ctc|package|per\s*(?:annum|month)|pa|pm|p\.a\.|p\.m\.)?",
            r"([0-9.,]+\s*(?:lakhs?|lacs?|lac|l|cr|crore|lpa))\s*(?:salary|ctc|package|big ones)",
            r"\b([0-9.]+\s*lpa)\b",
        ]
        
        for pat in salary_patterns:
            m = re.search(pat, lowered)
            if m:
                val_str = m.group(1)
                num = parse_indian_number(val_str)
                if num:
                    is_ann = extract_monthly_or_annual(m.group(0), default_to_annual=True)
                    gross_salary = num * 12.0 if not is_ann else num
                    entities["gross_salary"] = gross_salary
                    break

        # Fallback for plain "I earn X" or "X salary"
        if gross_salary is None:
            m_earn = re.search(r"(?:earn|make|get|draw)\s*(?:around|about)?\s*(?:rs\.?|inr|₹)?\s*([0-9.,]+\s*(?:lakhs?|lacs?|lac|l|cr|crore)?)", lowered)
            if m_earn:
                num = parse_indian_number(m_earn.group(1))
                if num:
                    is_ann = extract_monthly_or_annual(m_earn.group(0), default_to_annual=True)
                    gross_salary = num * 12.0 if not is_ann else num
                    entities["gross_salary"] = gross_salary

        if gross_salary is None:
            questions.append("What is your gross annual salary or CTC?")

        # 4. HRA and Rent Paid Extraction
        rent_paid = 0.0
        hra_received = 0.0
        is_metro = False

        # City / Metro detection
        for city in METRO_CITIES:
            if re.search(r"\b" + re.escape(city) + r"\b", lowered):
                is_metro = True
                entities["city"] = city
                entities["is_metro"] = True
                break

        # Rent paid pattern
        rent_match = re.search(r"(?:rent|kiraya)\s*(?:paid|is|of|=|:)?\s*(?:rs\.?|inr|₹)?\s*([0-9.,]+\s*(?:lakhs?|lacs?|lac|l|k|thousand)?)", lowered)
        if not rent_match:
            rent_match = re.search(r"(?:pay|paying)\s*(?:rs\.?|inr|₹)?\s*([0-9.,]+\s*(?:lakhs?|lacs?|lac|l|k|thousand)?)\s*(?:as|for)?\s*rent", lowered)

        if rent_match:
            num = parse_indian_number(rent_match.group(1))
            if num:
                is_ann = extract_monthly_or_annual(rent_match.group(0), default_to_annual=False)
                # Most people state rent monthly
                rent_paid = num if is_ann else num * 12.0
                entities["rent_paid"] = rent_paid

        # HRA component in salary
        hra_match = re.search(r"(?:hra|house rent allowance)\s*(?:is|of|=|:)?\s*(?:rs\.?|inr|₹)?\s*([0-9.,]+\s*(?:lakhs?|lacs?|lac|l|k|thousand)?)", lowered)
        if hra_match:
            num = parse_indian_number(hra_match.group(1))
            if num:
                is_ann = extract_monthly_or_annual(hra_match.group(0), default_to_annual=True)
                hra_received = num if is_ann else num * 12.0
                entities["hra_received"] = hra_received

        # Ambiguity check for HRA exemption
        if rent_paid > 0 and hra_received == 0:
            ambiguities.append("You mentioned paying rent, but did not specify the HRA component in your salary.")
            questions.append("How much HRA (House Rent Allowance) do you receive annually from your employer?")

        if rent_paid > 0 and not is_metro:
            ambiguities.append("Metro status determines whether 50% or 40% salary limit applies to HRA exemption.")
            questions.append("In which city do you live/rent (metro: Delhi, Mumbai, Kolkata, Chennai or non-metro)?")

        # 5. Section 80C Extraction
        sec_80c = 0.0
        # "80c is full", "pura 80c", "max 80c"
        if any(k in lowered for k in ["full 80c", "80c full", "max 80c", "80c max", "pura 80c", "80c pura"]):
            sec_80c = 150000.0
            entities["section_80c"] = 150000.0
        else:
            m_80c = re.search(r"(?:80c|80-c|pf|ppf|elss|lic)\s*(?:is|of|=|:)?\s*(?:rs\.?|inr|₹)?\s*([0-9.,]+\s*(?:lakhs?|lacs?|lac|l|k|thousand)?)", lowered)
            if m_80c:
                num = parse_indian_number(m_80c.group(1))
                if num:
                    sec_80c = min(num, 150000.0)
                    entities["section_80c"] = sec_80c
                    if num > 150000.0:
                        ambiguities.append(
                            f"Section 80C investment of ₹{num:,.0f} exceeds statutory cap of ₹1,50,000 (Section 80CCE)."
                        )

        # 6. Section 80CCD(1B) NPS Extraction
        sec_80ccd = 0.0
        m_nps = re.search(r"(?:nps|80ccd|80ccd\(1b\))\s*(?:is|of|=|:)?\s*(?:rs\.?|inr|₹)?\s*([0-9.,]+\s*(?:lakhs?|lacs?|lac|l|k|thousand)?)", lowered)
        if m_nps:
            num = parse_indian_number(m_nps.group(1))
            if num:
                sec_80ccd = min(num, 50000.0)
                entities["section_80ccd_1b"] = sec_80ccd

        # 7. Section 80D Medical Insurance
        sec_80d_self = 0.0
        sec_80d_parents = 0.0

        # Check parents insurance first
        m_parents_health = re.search(r"(?:parents?|mother|father|mummy|papa)\s*(?:ka|ki|ke)?\s*(?:health|medical)?\s*(?:insurance|mediclaim)?\s*(?:is|of|=|:)?\s*(?:rs\.?|inr|₹)?\s*([0-9.,]+\s*(?:lakhs?|lacs?|lac|l|k|thousand)?)", lowered)
        if m_parents_health:
            num = parse_indian_number(m_parents_health.group(1))
            if num:
                sec_80d_parents = num
                entities["section_80d_parents"] = sec_80d_parents
                has_parents_insurance = True

        m_health = re.search(r"(?:health insurance|medical insurance|mediclaim|80d)\s*(?:for self|self)?\s*(?:is|of|=|:)?\s*(?:rs\.?|inr|₹)?\s*([0-9.,]+\s*(?:lakhs?|lacs?|lac|l|k|thousand)?)", lowered)
        if m_health and not has_parents_insurance:
            num = parse_indian_number(m_health.group(1))
            if num:
                sec_80d_self = num
                entities["section_80d_self"] = sec_80d_self

        if has_parents_insurance and not parents_senior:
            questions.append("Are your parents senior citizens (aged 60 or above)? (This increases Section 80D limit from ₹25,00,0 to ₹50,000)")

        # 8. Home Loan Interest
        home_loan_interest = 0.0
        m_hl = re.search(r"(?:home loan|housing loan)\s*(?:interest)?\s*(?:is|of|=|:)?\s*(?:rs\.?|inr|₹)?\s*([0-9.,]+\s*(?:lakhs?|lacs?|lac|l|k|thousand)?)", lowered)
        if m_hl:
            num = parse_indian_number(m_hl.group(1))
            if num:
                home_loan_interest = min(num, 200000.0)
                entities["home_loan_interest"] = home_loan_interest
                if not any(k in lowered for k in ["self occupied", "self-occupied", "own house", "staying"]):
                    questions.append("Is this home loan for a self-occupied property? (Loss capped at ₹2,00,000 under Section 24(b))")

        # Incomplete / Unspecified deductions question
        if gross_salary is not None and len(entities) == 1:
            # Only gross salary was found
            ambiguities.append("No deductions (80C, 80D, HRA, Home Loan) were mentioned.")
            questions.append(
                "Do you have any tax deductions to claim (such as Section 80C investments, HRA, Health Insurance under 80D, or Home Loan Interest), "
                "or should we calculate assuming standard deduction only?"
            )

        is_complete = (gross_salary is not None) and (len(questions) == 0) and (len(contradictions) == 0)

        tax_input = None
        if gross_salary is not None:
            tax_input = TaxInput(
                gross_salary=gross_salary,
                hra_received=hra_received,
                rent_paid=rent_paid,
                is_metro=is_metro,
                section_80c=sec_80c,
                section_80ccd_1b=sec_80ccd,
                section_80d_self=sec_80d_self,
                section_80d_parents=sec_80d_parents,
                is_senior_citizen=is_senior,
                parents_are_senior_citizens=parents_senior,
                home_loan_interest_self_occupied=home_loan_interest,
                age=age,
            )

        return ParsedQuery(
            raw_query=text,
            tax_input=tax_input,
            is_complete=is_complete,
            clarifying_questions=questions,
            detected_entities=entities,
            contradictions=contradictions,
            ambiguities=ambiguities,
        )


def parse_user_description(text: str) -> ParsedQuery:
    """Convenience functional wrapper for natural language tax parser."""
    parser = NaturalLanguageTaxParser()
    return parser.parse(text)
