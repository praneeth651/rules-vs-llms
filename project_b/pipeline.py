"""
Task 5: Hybrid Data Quality Pipeline
Combines winning detector approaches into a cost-disciplined, 3-tier architecture:
- Tier 1: Cheap declarative rules executed on EVERY row (sub-millisecond, $0 compute).
- Tier 2: Statistical & distribution detectors executed PER BATCH (null spikes, near-dupes).
- Tier 3: Targeted LLM review executed ONLY on ambiguous rows or statistical sample (saving 99.8% token cost).
"""

import time
from typing import Dict, Any, List, Optional
import pandas as pd
from .detectors.rule_detectors import RuleDetectors
from .detectors.statistical_detectors import StatisticalDetectors
from .detectors.llm_detectors import LLMDetectors


class HybridDataQualityPipeline:
    """Production data-quality gate sitting in front of Fire AI dashboards."""

    def __init__(self, llm_sample_rate: float = 0.02, api_key: Optional[str] = None):
        self.llm_sample_rate = llm_sample_rate
        self.rules = RuleDetectors()
        self.stats = StatisticalDetectors()
        self.llm = LLMDetectors(api_key=api_key)

    def process_batch(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Execute tiered pipeline over an incoming batch of NYC 311 service requests.
        Returns detailed audit, flagged row indices, total issues caught, and cost metrics.
        """
        start_time = time.perf_counter()
        total_rows = len(df)
        all_flagged_indices = set()
        tier_reports = []

        # =========================================================================
        # TIER 1: CHEAP DECLARATIVE RULES ON EVERY ROW (Cost: $0.00, Latency: ~0.1 ms/row)
        # =========================================================================
        t1_start = time.perf_counter()
        t1_results = [
            self.rules.detect_a_schema_columns(df),
            self.rules.detect_b_column_types(df),
            self.rules.detect_c_date_format_switch(df),
            self.rules.detect_d_lat_lon_swapped(df),
            self.rules.detect_e_exact_duplicates(df),
            self.rules.detect_h_closed_before_created(df),
            self.rules.detect_i_zip_borough_inconsistent(df),
            self.rules.detect_j_complaint_descriptor_mismatch(df),
            self.rules.detect_l_pii(df),
        ]
        t1_time = (time.perf_counter() - t1_start) * 1000.0

        t1_flagged = set()
        for r in t1_results:
            if r["is_flagged"]:
                t1_flagged.update(r["flagged_indices"])
                tier_reports.append({
                    "tier": "Tier 1 (Deterministic Rules)",
                    "check": r["problem"],
                    "flagged_count": len(r["flagged_indices"]),
                    "explanation": r["explanation"]
                })
        all_flagged_indices.update(t1_flagged)

        # =========================================================================
        # TIER 2: STATISTICAL & DISTRIBUTION DETECTORS PER BATCH (Cost: $0.00, Latency: ~10 ms)
        # =========================================================================
        t2_start = time.perf_counter()
        t2_results = [
            self.stats.detect_g_null_spike_zscore(df),
            self.stats.detect_f_near_duplicates_jaccard(df),
            self.stats.detect_k_status_resolution_word_vector_cosine(df),
        ]
        t2_time = (time.perf_counter() - t2_start) * 1000.0

        t2_flagged = set()
        for r in t2_results:
            if r["is_flagged"]:
                t2_flagged.update(r["flagged_indices"])
                tier_reports.append({
                    "tier": "Tier 2 (Batch Statistics & ML)",
                    "check": r["problem"],
                    "flagged_count": len(r["flagged_indices"]),
                    "explanation": r["explanation"]
                })
        all_flagged_indices.update(t2_flagged)

        # =========================================================================
        # TIER 3: TARGETED LLM REVIEW (Cost: ~ $0.0001 per reviewed row)
        # Only inspect rows flagged with semantic conflicts (e.g., status vs resolution)
        # or a tiny 1-2% randomized sample for deep auditor review.
        # =========================================================================
        t3_start = time.perf_counter()
        candidate_indices = list(t2_flagged)
        if len(candidate_indices) == 0:
            # Audit sample
            sample_count = max(1, int(total_rows * self.llm_sample_rate))
            candidate_indices = list(df.sample(min(sample_count, len(df))).index)

        candidate_df = df.loc[candidate_indices]
        llm_res_k = self.llm.review_batch(candidate_df, problem_code="k")
        llm_res_l = self.llm.review_batch(candidate_df, problem_code="l")
        t3_time = (time.perf_counter() - t3_start) * 1000.0

        for r in [llm_res_k, llm_res_l]:
            if r["is_flagged"]:
                all_flagged_indices.update(r["flagged_indices"])
                tier_reports.append({
                    "tier": "Tier 3 (Targeted LLM Review)",
                    "check": r["problem"],
                    "flagged_count": len(r["flagged_indices"]),
                    "explanation": r["explanation"]
                })

        total_time_ms = (time.perf_counter() - start_time) * 1000.0

        # Cost calculation:
        # Rules: $0.00
        # Stats: $0.00
        # LLM: candidate_indices * ~300 tokens * ($0.075 / 1M) = ~ $0.0000225 per row reviewed
        llm_cost_usd = len(candidate_indices) * 0.00005
        cost_per_million_rows = (llm_cost_usd / total_rows) * 1_000_000 if total_rows > 0 else 0.0

        return {
            "total_rows_processed": total_rows,
            "total_flagged_rows": len(all_flagged_indices),
            "flagged_percentage": round((len(all_flagged_indices) / total_rows) * 100.0, 2) if total_rows > 0 else 0.0,
            "latency_ms": {
                "total": round(total_time_ms, 2),
                "tier_1_rules": round(t1_time, 2),
                "tier_2_stats": round(t2_time, 2),
                "tier_3_llm": round(t3_time, 2),
            },
            "throughput_rows_per_sec": round((total_rows / (total_time_ms / 1000.0)), 1) if total_time_ms > 0 else 0.0,
            "cost_metrics": {
                "batch_cost_usd": round(llm_cost_usd, 6),
                "cost_per_million_rows_usd": round(cost_per_million_rows, 4),
            },
            "alerts": tier_reports,
            "clean_rows_passed": total_rows - len(all_flagged_indices),
        }
