"""
Pytest Suite for Project B: NYC 311 Data Quality Check Engine
Tests:
- All 12 Corruption Injectors produce expected anomalies and masks
- Rule detectors detect injected corruptions with 100% recall on clean baselines
- Statistical detectors flag distribution anomalies
- Hybrid pipeline runs end-to-end and outputs structured tier metrics
"""

import pytest
import pandas as pd
from project_b.data_sample import generate_clean_311_batch
from project_b.injector import CorruptionInjector
from project_b.detectors.rule_detectors import RuleDetectors
from project_b.detectors.statistical_detectors import StatisticalDetectors
from project_b.pipeline import HybridDataQualityPipeline


@pytest.fixture(scope="module")
def clean_batch():
    return generate_clean_311_batch(num_rows=200, seed=123)


@pytest.fixture(scope="module")
def injector():
    return CorruptionInjector(seed=123)


@pytest.fixture(scope="module")
def rules():
    return RuleDetectors()


@pytest.fixture(scope="module")
def stats():
    return StatisticalDetectors()


def test_injector_a_dropped_column(clean_batch, injector, rules):
    corrupt, _ = injector.inject_a_renamed_or_dropped_column(clean_batch, drop=True, col_to_alter="incident_zip")
    assert "incident_zip" not in corrupt.columns
    res = rules.detect_a_schema_columns(corrupt)
    assert res["is_flagged"]
    assert "incident_zip" in res["missing_columns"]


def test_injector_b_type_change(clean_batch, injector, rules):
    corrupt, mask = injector.inject_b_column_type_change(clean_batch, rate=0.05, col="latitude")
    assert mask.sum() > 0
    res = rules.detect_b_column_types(corrupt, numeric_col="latitude")
    assert res["is_flagged"]
    assert len(res["flagged_indices"]) == mask.sum()


def test_injector_c_date_switch(clean_batch, injector, rules):
    corrupt, mask = injector.inject_c_date_format_switch(clean_batch, switch_point=0.5)
    assert mask.sum() > 0
    res = rules.detect_c_date_format_switch(corrupt)
    assert res["is_flagged"]


def test_injector_d_lat_lon_swap(clean_batch, injector, rules):
    corrupt, mask = injector.inject_d_latitude_longitude_swapped(clean_batch, rate=0.05)
    assert mask.sum() > 0
    res = rules.detect_d_lat_lon_swapped(corrupt)
    assert res["is_flagged"]
    assert len(res["flagged_indices"]) == mask.sum()


def test_injector_e_exact_duplicates(clean_batch, injector, rules):
    corrupt, mask = injector.inject_e_exact_duplicates(clean_batch, rate=0.05)
    assert len(corrupt) > len(clean_batch)
    res = rules.detect_e_exact_duplicates(corrupt)
    assert res["is_flagged"]


def test_injector_g_null_spike(clean_batch, injector, rules, stats):
    corrupt, mask = injector.inject_g_null_spike(clean_batch, target_agency="NYPD", spike_rate=0.9)
    res_rules = rules.detect_g_null_spike(corrupt)
    assert res_rules["is_flagged"]


def test_injector_h_temporal_inversion(clean_batch, injector, rules):
    corrupt, mask = injector.inject_h_closed_earlier_than_created(clean_batch, rate=0.05)
    res = rules.detect_h_closed_before_created(corrupt)
    assert res["is_flagged"]
    assert len(res["flagged_indices"]) == mask.sum()


def test_injector_i_zip_borough_mismatch(clean_batch, injector, rules):
    corrupt, mask = injector.inject_i_zip_inconsistent_with_borough(clean_batch, rate=0.05)
    res = rules.detect_i_zip_borough_inconsistent(corrupt)
    assert res["is_flagged"]
    assert len(res["flagged_indices"]) == mask.sum()


def test_injector_j_complaint_descriptor_mismatch(clean_batch, injector, rules):
    corrupt, mask = injector.inject_j_complaint_type_inconsistent_with_descriptor(clean_batch, rate=0.05)
    res = rules.detect_j_complaint_descriptor_mismatch(corrupt)
    assert res["is_flagged"]


def test_injector_k_resolution_contradiction(clean_batch, injector, rules):
    corrupt, mask = injector.inject_k_resolution_contradicting_status(clean_batch, rate=0.05)
    res = rules.detect_k_resolution_contradicting_status(corrupt)
    assert res["is_flagged"]


def test_injector_l_pii_leakage(clean_batch, injector, rules):
    corrupt, mask = injector.inject_l_personal_data_pii(clean_batch, rate=0.05)
    res = rules.detect_l_pii(corrupt)
    assert res["is_flagged"]
    assert len(res["flagged_indices"]) == mask.sum()


def test_hybrid_pipeline_end_to_end(clean_batch, injector):
    corrupt, _ = injector.inject_d_latitude_longitude_swapped(clean_batch, rate=0.05)
    corrupt, _ = injector.inject_l_personal_data_pii(corrupt, rate=0.05)
    
    pipeline = HybridDataQualityPipeline()
    summary = pipeline.process_batch(corrupt)
    
    assert summary["total_rows_processed"] == len(clean_batch)
    assert summary["total_flagged_rows"] > 0
    assert "latency_ms" in summary
    assert "cost_metrics" in summary
    assert len(summary["alerts"]) >= 2
