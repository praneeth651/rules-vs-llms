"""
Rules vs LLMs Take-Home Assignment — Master Reproducibility Runner
Single command to reproduce every benchmark, number, and test result reported across
RESULTS_A.md, RESULTS_B.md, DECISION_MATRIX.md, and AI_USAGE.md.

Usage:
    python run_all.py
"""

import sys
import subprocess
import time


def main():
    print("\n" + "#"*90)
    print(" FIRE AI — RULES VS LLMS TAKE-HOME ASSIGNMENT: MASTER REPRODUCIBILITY RUNNER ")
    print("#"*90 + "\n")

    python_bin = sys.executable

    # 1. Run Automated Test Suite
    print(">>> STEP 1: RUNNING COMPREHENSIVE AUTOMATED TEST SUITE (pytest)...")
    t0 = time.time()
    res = subprocess.run([python_bin, "-m", "pytest", "project_a/tests", "project_b/tests", "-v"], check=False)
    print(f"Test suite finished in {time.time() - t0:.2f} seconds with exit code {res.returncode}.\n")

    # 2. Run Project A Benchmarks & Task 5 Evaluation
    print(">>> STEP 2: RUNNING PROJECT A BENCHMARKS & TASK 5 MIGRATION EVALUATION...")
    from project_a.benchmark import run_benchmark
    run_benchmark()

    # 3. Run Project B Task 1 Raw Data Profiler
    print(">>> STEP 3: RUNNING PROJECT B RAW DATA PROFILER (NYC 311 2023)...")
    from project_b.profiler import profile_raw_311_data
    report = profile_raw_311_data()
    print(f"Profiled {report['total_rows_profiled']:,} records. Found {len(report['discovered_quality_issues'])} distinct quality defect categories.\n")

    # 4. Run Project B Comprehensive Benchmark (12 Problems x 3 Detector Families)
    print(">>> STEP 4: RUNNING PROJECT B 12-PROBLEM DETECTOR BENCHMARKS...")
    from project_b.benchmark import run_comprehensive_benchmark
    run_comprehensive_benchmark()

    # 5. Run Project B Hybrid Pipeline End-to-End
    print(">>> STEP 5: RUNNING PROJECT B HYBRID PIPELINE END-TO-END DEMO...")
    from project_b.data_sample import generate_clean_311_batch
    from project_b.injector import CorruptionInjector
    from project_b.pipeline import HybridDataQualityPipeline

    df = generate_clean_311_batch(1000)
    injector = CorruptionInjector(seed=42)
    corrupted, _ = injector.inject_d_latitude_longitude_swapped(df, rate=0.04)
    corrupted, _ = injector.inject_h_closed_earlier_than_created(corrupted, rate=0.03)
    corrupted, _ = injector.inject_l_personal_data_pii(corrupted, rate=0.02)

    pipeline = HybridDataQualityPipeline()
    summary = pipeline.process_batch(corrupted)
    print(f"Processed {summary['total_rows_processed']:,} rows in {summary['latency_ms']['total']:.1f} ms.")
    print(f"Flagged {summary['total_flagged_rows']} corrupted rows ({summary['flagged_percentage']}%).")
    print(f"Effective Cost per Million Rows: ${summary['cost_metrics']['cost_per_million_rows_usd']:.4f}\n")

    print("#"*90)
    print(" ALL BENCHMARKS COMPLETED SUCCESSFULLY! ")
    print(" Deliverable Reports Generated on Disk:")
    print("  • RESULTS_A.md        : Project A benchmarks, Task 5 migration log, final design")
    print("  • RESULTS_B.md        : Project B 12-problem benchmarks, real data issues, 50M scale design")
    print("  • DECISION_MATRIX.md  : Architectural decisions with empirical measurement justifications")
    print("  • AI_USAGE.md         : AI tools disclosure and detailed failure analysis")
    print("#"*90 + "\n")


if __name__ == "__main__":
    main()
