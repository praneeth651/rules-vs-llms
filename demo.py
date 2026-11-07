"""
Interactive CLI Demo for Fire AI Evaluation & Interview Presentation
Allows interactive testing of:
1. Natural language plain-text queries (English, Hinglish, incomplete) with live tax calculation
2. Project B live corruption injection and hybrid pipeline detection in real-time
"""

import sys
from project_a.tax_engine.nlp_parser import NaturalLanguageTaxParser
from project_a.tax_engine.rules_engine import RulesEngine
from project_b.data_sample import generate_clean_311_batch
from project_b.injector import CorruptionInjector
from project_b.pipeline import HybridDataQualityPipeline


def demo_project_a():
    parser = NaturalLanguageTaxParser()
    engine = RulesEngine(default_fy="2024-25")

    print("\n" + "="*80)
    print(" PROJECT A: PLAIN LANGUAGE TAX ENGINE DEMO ")
    print("="*80)
    print("Enter plain language tax descriptions (or type 'sample' or 'back'):")
    
    sample_queries = [
        "Mera salary 15 lakh hai, Mumbai me rent 30000 per month deta hu, HRA 3 lakh hai, 80c pura hai",
        "I earn 18L, what is my tax?",
        "My CTC is 25 LPA in Delhi, paying 2L home loan interest on self-occupied flat, maxed 80C, 50k NPS",
        "I am 24 years old senior citizen earning 10 LPA"
    ]

    while True:
        try:
            user_input = input("\nQuery > ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input or user_input.lower() in ["back", "exit", "q"]:
            break

        if user_input.lower() == "sample":
            print("\nAvailable Samples:")
            for i, q in enumerate(sample_queries, 1):
                print(f" {i}. {q}")
            continue

        if user_input.isdigit() and 1 <= int(user_input) <= len(sample_queries):
            user_input = sample_queries[int(user_input) - 1]
            print(f"Selected: '{user_input}'")

        parsed = parser.parse(user_input)
        print("\n--- PARSING ANALYSIS ---")
        print(f"Complete: {parsed.is_complete}")
        print(f"Detected Entities: {parsed.detected_entities}")

        if parsed.contradictions:
            print(f"⚠️ CONTRADICTION DETECTED: {parsed.contradictions}")

        if parsed.clarifying_questions:
            print("❓ SYSTEM ASKS CLARIFYING QUESTIONS INSTEAD OF GUESSING:")
            for q in parsed.clarifying_questions:
                print(f"  • {q}")

        if parsed.tax_input:
            print("\n--- RUPEE-EXACT CALCULATION ---")
            res_24 = engine.calculate(parsed.tax_input, fy="2024-25")
            res_25 = engine.calculate(parsed.tax_input, fy="2025-26")

            print(f"Gross Salary       : ₹{parsed.tax_input.gross_salary:,.0f}")
            print(f"Old Regime Tax     : ₹{res_24.old_regime.total_tax_payable_rounded:,}")
            print(f"New Regime (FY24)  : ₹{res_24.new_regime.total_tax_payable_rounded:,}")
            print(f"New Regime (FY25)  : ₹{res_25.new_regime.total_tax_payable_rounded:,} (Under Budget 2025 slabs)")
            print(f"Recommended Regime : {res_24.recommended_regime} (Saves ₹{res_24.tax_difference:,.0f})")
            print(f"Reason             : {res_24.recommendation_reason}")


def demo_project_b():
    print("\n" + "="*80)
    print(" PROJECT B: NYC 311 HYBRID PIPELINE LIVE DEMO ")
    print("="*80)
    print("Generating clean batch of 1,000 NYC 311 service requests...")
    df = generate_clean_311_batch(num_rows=1000, seed=42)

    injector = CorruptionInjector(seed=42)
    print("Injecting corruptions:")
    print(" - 3% Swapped Lat/Lon coordinates")
    print(" - 3% Closed Date earlier than Created Date")
    print(" - 2% PII (phone numbers/emails) in text")
    
    corrupted, _ = injector.inject_d_latitude_longitude_swapped(df, rate=0.03)
    corrupted, _ = injector.inject_h_closed_earlier_than_created(corrupted, rate=0.03)
    corrupted, _ = injector.inject_l_personal_data_pii(corrupted, rate=0.02)

    print("\nExecuting 3-Tier Hybrid Pipeline...")
    pipeline = HybridDataQualityPipeline()
    summary = pipeline.process_batch(corrupted)

    print("\n--- RESULTS ---")
    print(f"Total Rows Processed : {summary['total_rows_processed']:,}")
    print(f"Total Flagged Rows   : {summary['total_flagged_rows']} ({summary['flagged_percentage']}%)")
    print(f"End-to-End Latency   : {summary['latency_ms']['total']} ms")
    print(f"Throughput           : {summary['throughput_rows_per_sec']:,} rows/sec")
    print(f"Cost per 1M rows     : ${summary['cost_metrics']['cost_per_million_rows_usd']:.4f}")
    
    print("\nAlert Breakdown by Tier:")
    for a in summary["alerts"]:
        print(f" [{a['tier']}] {a['check']} -> {a['flagged_count']} rows flagged")
        print(f"   Explanation: {a['explanation']}")


def main():
    while True:
        print("\n" + "#"*70)
        print(" FIRE AI TAKE-HOME ASSIGNMENT: INTERACTIVE DEMO ")
        print("#"*70)
        print("Select demo module:")
        print(" 1. Project A — Income-Tax Engine (Plain-Language & Calculation)")
        print(" 2. Project B — NYC 311 Hybrid Data-Quality Pipeline")
        print(" 3. Exit")
        
        try:
            choice = input("\nSelect (1-3) > ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if choice == "1":
            demo_project_a()
        elif choice == "2":
            demo_project_b()
        elif choice in ["3", "exit", "q"]:
            break


if __name__ == "__main__":
    main()
