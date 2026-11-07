"""
Task 1: Raw Data Profiler for NYC 311 (Calendar Year 2023)
Finds and documents real-world quality problems that exist in raw data,
providing exact counts, percentages, and representative examples.
"""

import json
import re
from typing import Dict, Any, List
import pandas as pd
from .data_sample import download_or_load_raw_2023_data, BOROUGH_ZIP_MAP, TAXONOMY


PII_PHONE_REGEX = re.compile(r"\b(?:\+?1[-.]?)?\(?[2-9]\d{2}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
PII_EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")


def profile_raw_311_data(df: pd.DataFrame = None) -> Dict[str, Any]:
    """Run comprehensive profiling suite over 2023 NYC 311 records."""
    if df is None:
        df = download_or_load_raw_2023_data(limit=5000)

    total_rows = len(df)
    report = {
        "dataset_name": "NYC 311 Service Requests (2023)",
        "total_rows_profiled": total_rows,
        "total_columns": len(df.columns),
        "column_profiles": {},
        "discovered_quality_issues": []
    }

    # 1. Null / Missingness Profile
    null_counts = df.isnull().sum().to_dict()
    for col, count in null_counts.items():
        pct = round((count / total_rows) * 100.0, 2)
        report["column_profiles"][col] = {
            "null_count": int(count),
            "null_percentage": pct,
            "dtype": str(df[col].dtype),
        }
        if count > 0:
            sample_examples = df[df[col].isnull()]["unique_key"].head(3).tolist()
            report["discovered_quality_issues"].append({
                "issue_type": "Missing / Null Values",
                "column": col,
                "count": int(count),
                "percentage": pct,
                "impact": f"Dashboard aggregations on {col} will produce incomplete sums or omit records.",
                "sample_keys": sample_examples,
            })

    # 2. Temporal Inversions (Closed Date < Created Date)
    temporal_inversions = []
    # Check rows where both created and closed dates exist
    valid_dates_df = df[df["created_date"].notnull() & df["closed_date"].notnull()].copy()
    try:
        created_series = pd.to_datetime(valid_dates_df["created_date"], errors="coerce")
        closed_series = pd.to_datetime(valid_dates_df["closed_date"], errors="coerce")
        inverted_mask = closed_series < created_series
        inverted_df = valid_dates_df[inverted_mask]
        if len(inverted_df) > 0:
            examples = []
            for _, r in inverted_df.head(3).iterrows():
                examples.append({
                    "unique_key": int(r["unique_key"]),
                    "created_date": str(r["created_date"]),
                    "closed_date": str(r["closed_date"])
                })
            report["discovered_quality_issues"].append({
                "issue_type": "Temporal Inversion (Closed Date earlier than Created Date)",
                "count": len(inverted_df),
                "percentage": round((len(inverted_df) / total_rows) * 100.0, 3),
                "impact": "Produces negative resolution SLA durations on executive dashboards.",
                "examples": examples
            })
    except Exception:
        pass

    # 3. Spatial Bounds Violations (NYC Bounds: Lat 40.49 to 40.92, Lon -74.26 to -73.70)
    if "latitude" in df.columns and "longitude" in df.columns:
        coords_df = df[df["latitude"].notnull() & df["longitude"].notnull()].copy()
        lat_mask = (coords_df["latitude"] < 40.49) | (coords_df["latitude"] > 40.92)
        lon_mask = (coords_df["longitude"] < -74.26) | (coords_df["longitude"] > -73.70)
        out_of_bounds = coords_df[lat_mask | lon_mask]
        if len(out_of_bounds) > 0:
            report["discovered_quality_issues"].append({
                "issue_type": "Spatial Coordinate Out of Bounds",
                "count": len(out_of_bounds),
                "percentage": round((len(out_of_bounds) / total_rows) * 100.0, 3),
                "impact": "Pins render off the NYC map (e.g. in the Atlantic Ocean or outside NYC).",
                "sample_keys": out_of_bounds["unique_key"].head(3).tolist()
            })

    # 4. ZIP Code vs Borough Inconsistency
    if "incident_zip" in df.columns and "borough" in df.columns:
        inconsistent_geo = []
        for idx, row in df.iterrows():
            borough = str(row["borough"]).upper().strip()
            zip_code = str(row["incident_zip"]).strip() if pd.notnull(row["incident_zip"]) else None
            if zip_code and borough in BOROUGH_ZIP_MAP:
                # If zip is not in borough's known prefix list
                expected_zips = BOROUGH_ZIP_MAP[borough]
                # In NYC: Manhattan is 100xx/101xx/102xx, Bronx is 104xx, Brooklyn is 112xx, Queens is 111xx/113xx/114xx/116xx, SI is 103xx
                prefix = zip_code[:3]
                valid_prefixes = {z[:3] for z in expected_zips}
                if prefix not in valid_prefixes and zip_code not in expected_zips:
                    inconsistent_geo.append({
                        "unique_key": int(row["unique_key"]),
                        "borough": borough,
                        "incident_zip": zip_code
                    })
        if len(inconsistent_geo) > 0:
            report["discovered_quality_issues"].append({
                "issue_type": "Borough and ZIP Code Inconsistency",
                "count": len(inconsistent_geo),
                "percentage": round((len(inconsistent_geo) / total_rows) * 100.0, 3),
                "impact": "Mismatches break district-level and borough-level financial reporting.",
                "examples": inconsistent_geo[:3]
            })

    # 5. PII Detection in Free-Text Fields
    text_cols = [c for c in ["descriptor", "resolution_description"] if c in df.columns]
    pii_found = []
    for col in text_cols:
        for idx, text in df[col].dropna().items():
            text_str = str(text)
            if PII_PHONE_REGEX.search(text_str) or PII_EMAIL_REGEX.search(text_str):
                pii_found.append({
                    "unique_key": int(df.loc[idx, "unique_key"]),
                    "column": col,
                    "sample_text": text_str[:80] + "..."
                })
    if len(pii_found) > 0:
        report["discovered_quality_issues"].append({
            "issue_type": "Personal Data (PII) Leakage in Free-Text",
            "count": len(pii_found),
            "percentage": round((len(pii_found) / total_rows) * 100.0, 3),
            "impact": "GDPR / CCPA / privacy regulation violation when dashboards surface PII to unauthorized users.",
            "examples": pii_found[:3]
        })

    return report


if __name__ == "__main__":
    report = profile_raw_311_data()
    print("\n" + "="*80)
    print("TASK 1: NYC 311 2023 DATA QUALITY PROFILING REPORT")
    print("="*80)
    print(f"Total rows analyzed: {report['total_rows_profiled']:,}")
    print(f"Total quality issue categories discovered: {len(report['discovered_quality_issues'])}\n")
    for issue in report["discovered_quality_issues"]:
        print(f"• [{issue['issue_type']}]")
        print(f"  Count: {issue['count']} ({issue['percentage']}%)")
        print(f"  Impact: {issue['impact']}")
        if "examples" in issue:
            print(f"  Examples: {issue['examples']}")
        print()
    print("="*80 + "\n")
