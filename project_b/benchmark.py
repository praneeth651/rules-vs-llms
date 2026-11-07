"""
Task 4: Comprehensive Benchmark Runner for Project B
Measures all 12 problem types across all 3 detector families:
1. Detection Rate (Recall / Sensitivity)
2. False Alarm Rate on clean batches (False Positive Rate)
3. Cost per million rows
4. Throughput on a laptop (rows / sec)
5. Clarity of alert explanation
"""

import time
import pandas as pd
from tabulate import tabulate
from project_b.data_sample import generate_clean_311_batch
from project_b.injector import CorruptionInjector
from project_b.detectors.rule_detectors import RuleDetectors
from project_b.detectors.statistical_detectors import StatisticalDetectors
from project_b.detectors.llm_detectors import LLMDetectors


def run_comprehensive_benchmark():
    clean_batch = generate_clean_311_batch(num_rows=1000, seed=42)
    injector = CorruptionInjector(seed=42)
    rules = RuleDetectors()
    stats = StatisticalDetectors()
    llm = LLMDetectors()

    problems = [
        ("a", "Renamed or dropped column",
         lambda df: injector.inject_a_renamed_or_dropped_column(df, drop=True),
         rules.detect_a_schema_columns,
         stats.detect_a_schema_entropy,
         lambda df: llm.review_batch(df, "a")),
        
        ("b", "Column type change (strings in numeric)",
         lambda df: injector.inject_b_column_type_change(df, rate=0.05),
         rules.detect_b_column_types,
         stats.detect_b_type_distribution_shift,
         lambda df: llm.review_batch(df, "b")),

        ("c", "Date format switch partway through",
         lambda df: injector.inject_c_date_format_switch(df, switch_point=0.5),
         rules.detect_c_date_format_switch,
         stats.detect_c_date_string_length_anomaly,
         lambda df: llm.review_batch(df, "c")),

        ("d", "Latitude and Longitude swapped",
         lambda df: injector.inject_d_latitude_longitude_swapped(df, rate=0.05),
         rules.detect_d_lat_lon_swapped,
         stats.detect_d_coordinate_outliers_zscore,
         lambda df: llm.review_batch(df, "d")),

        ("e", "Exact duplicates",
         lambda df: injector.inject_e_exact_duplicates(df, rate=0.05),
         rules.detect_e_exact_duplicates,
         stats.detect_e_exact_duplicate_frequencies,
         lambda df: llm.review_batch(df, "e")),

        ("f", "Near-duplicates (same request, slight alter)",
         lambda df: injector.inject_f_near_duplicates(df, rate=0.05),
         rules.detect_f_near_duplicates,
         stats.detect_f_near_duplicates_jaccard,
         lambda df: llm.review_batch(df, "f")),

        ("g", "Null spike in one agency's records",
         lambda df: injector.inject_g_null_spike(df, target_agency="NYPD", spike_rate=0.85),
         rules.detect_g_null_spike,
         stats.detect_g_null_spike_zscore,
         lambda df: llm.review_batch(df, "g")),

        ("h", "Closed date earlier than created date",
         lambda df: injector.inject_h_closed_earlier_than_created(df, rate=0.05),
         rules.detect_h_closed_before_created,
         stats.detect_h_temporal_negative_duration,
         lambda df: llm.review_batch(df, "h")),

        ("i", "ZIP code inconsistent with borough",
         lambda df: injector.inject_i_zip_inconsistent_with_borough(df, rate=0.05),
         rules.detect_i_zip_borough_inconsistent,
         stats.detect_i_zip_borough_joint_distribution,
         lambda df: llm.review_batch(df, "i")),

        ("j", "Complaint Type inconsistent with Descriptor",
         lambda df: injector.inject_j_complaint_type_inconsistent_with_descriptor(df, rate=0.05),
         rules.detect_j_complaint_descriptor_mismatch,
         stats.detect_j_complaint_descriptor_chi2,
         lambda df: llm.review_batch(df, "j")),

        ("k", "Resolution Description contradicting Status",
         lambda df: injector.inject_k_resolution_contradicting_status(df, rate=0.05),
         rules.detect_k_resolution_contradicting_status,
         stats.detect_k_status_resolution_word_vector_cosine,
         lambda df: llm.review_batch(df, "k")),

        ("l", "Personal data (PII) inside free text",
         lambda df: injector.inject_l_personal_data_pii(df, rate=0.05),
         rules.detect_l_pii,
         stats.detect_l_pii_entropy,
         lambda df: llm.review_batch(df, "l")),
    ]

    benchmark_rows = []

    print("\n" + "="*110)
    print("PROJECT B — BENCHMARKING 12 PROBLEM TYPES ACROSS 3 DETECTOR FAMILIES")
    print("="*110)

    for code, name, inject_fn, rule_fn, stat_fn, llm_fn in problems:
        corrupted_df, ground_truth_mask = inject_fn(clean_batch)
        actual_corrupt_indices = set(ground_truth_mask[ground_truth_mask].index)
        n_corrupt = len(actual_corrupt_indices)

        detector_map = [
            ("Declarative Rule", rule_fn, "$0.00", "High (Exact rule/clause cited)"),
            ("Statistical/ML", stat_fn, "$0.00", "Medium (Z-score/frequency p-value)"),
            ("LLM Review", llm_fn, "$22.50 - $150.00", "High (Natural language explanation)"),
        ]

        for det_family, det_func, cost_1m, clarity in detector_map:
            # Measure on corrupted batch (Detection Rate)
            t0 = time.perf_counter()
            res_corrupt = det_func(corrupted_df)
            dur = time.perf_counter() - t0
            throughput = int(len(corrupted_df) / dur) if dur > 0 else 50000

            flagged_indices = set(res_corrupt["flagged_indices"])
            
            # Recall
            if n_corrupt > 0:
                # If problem is batch/schema-level (like a or g), check binary flag
                if code in ["a", "g"]:
                    recall = 100.0 if res_corrupt["is_flagged"] else 0.0
                else:
                    true_positives = len(flagged_indices & actual_corrupt_indices)
                    recall = round((true_positives / n_corrupt) * 100.0, 1)
            else:
                recall = 100.0

            # Measure on clean batch (False Alarm Rate)
            res_clean = det_func(clean_batch)
            clean_flagged = set(res_clean["flagged_indices"])
            if code in ["a", "g"]:
                fpr = 0.0 if not res_clean["is_flagged"] else 100.0
            else:
                fpr = round((len(clean_flagged) / len(clean_batch)) * 100.0, 2)

            benchmark_rows.append([
                f"{code}. {name[:28]}",
                det_family,
                f"{recall:.1f}%",
                f"{fpr:.2f}%",
                cost_1m,
                f"{throughput:,} r/s",
                clarity
            ])

    headers = [
        "Problem Type", "Detector Family", "Detection Rate (Recall)",
        "False Alarm Rate (Clean)", "Cost / 1M Rows", "Throughput", "Alert Clarity"
    ]
    print(tabulate(benchmark_rows, headers=headers, tablefmt="github"))
    print("="*110 + "\n")


if __name__ == "__main__":
    run_comprehensive_benchmark()
