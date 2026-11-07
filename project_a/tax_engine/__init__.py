"""
Indian Income Tax Engine package (Salary Income).
Contains Rules Engine (A), LLM Query Engine (B), LLM-Compiled Engine (C), and NLP Parser.
"""

from .models import TaxInput, TaxResult, RegimeBreakdown, DeductionItem, SlabTaxItem
from .constants import OLD_REGIME_CONFIG, NEW_REGIME_2024_CONFIG, NEW_REGIME_2025_CONFIG, CLAUSE_CITATIONS
from .rules_engine import RulesEngine
from .llm_engine import LLMEngine
from .llm_compiled_engine import LLMCompiledEngine
from .nlp_parser import NaturalLanguageTaxParser, parse_user_description, ParsedQuery

__all__ = [
    "TaxInput",
    "TaxResult",
    "RegimeBreakdown",
    "DeductionItem",
    "SlabTaxItem",
    "RulesEngine",
    "LLMEngine",
    "LLMCompiledEngine",
    "NaturalLanguageTaxParser",
    "parse_user_description",
    "ParsedQuery",
    "OLD_REGIME_CONFIG",
    "NEW_REGIME_2024_CONFIG",
    "NEW_REGIME_2025_CONFIG",
    "CLAUSE_CITATIONS",
]
