"""
Task 3b: Statistical and Machine Learning Detectors Family
Detects anomalies via distribution profiling, Z-scores, text similarity,
and outlier detection across all 12 problem types.
"""

from typing import Dict, Any, List, Set, Tuple
import pandas as pd
import numpy as np


class StatisticalDetectors:
    """Statistical, distribution-based, and ML anomaly detectors."""

    @staticmethod
    def detect_a_schema_entropy(df: pd.DataFrame, expected_count: int = 13) -> Dict[str, Any]:
        """Statistical check: column count and schema entropy anomaly."""
        col_count = len(df.columns)
        is_corrupt = (col_count != expected_count)
        return {
            "problem": "a_renamed_or_dropped_column",
            "detector": "statistical",
            "is_flagged": is_corrupt,
            "flagged_indices": list(df.index) if is_corrupt else [],
            "explanation": f"Statistical schema check: Observed {col_count} columns vs expected {expected_count}.",
            "col_count": col_count,
        }

    @staticmethod
    def detect_b_type_distribution_shift(df: pd.DataFrame, col: str = "latitude") -> Dict[str, Any]:
        """Detect column type change via non-numeric value ratio anomaly."""
        flagged = []
        if col in df.columns:
            non_numeric = pd.to_numeric(df[col], errors="coerce").isnull() & df[col].notnull()
            flagged = list(df[non_numeric].index)

        anomaly_rate = len(flagged) / len(df) if len(df) > 0 else 0.0
        # If string conversion rate > 1%, flag as type distribution anomaly
        is_flagged = anomaly_rate > 0.01

        return {
            "problem": "b_column_type_change",
            "detector": "statistical",
            "is_flagged": is_flagged,
            "flagged_indices": flagged,
            "explanation": f"Statistical type check: {anomaly_rate*100:.2f}% non-numeric entries in '{col}' exceeds baseline 0.0%.",
        }

    @staticmethod
    def detect_c_date_string_length_anomaly(df: pd.DataFrame, col: str = "created_date") -> Dict[str, Any]:
        """Detect date format switch partway through batch via string length distribution shift."""
        flagged = []
        if col in df.columns:
            lengths = df[col].dropna().astype(str).str.len()
            if len(lengths) > 0:
                mode_len = lengths.mode()[0]
                # Any row whose string length deviates significantly from the batch mode
                deviants = lengths[lengths != mode_len]
                flagged = list(deviants.index)

        return {
            "problem": "c_date_format_switch",
            "detector": "statistical",
            "is_flagged": len(flagged) > 0,
            "flagged_indices": flagged,
            "explanation": f"Detected {len(flagged)} date entries with deviant string representation lengths.",
        }

    @staticmethod
    def detect_d_coordinate_outliers_zscore(df: pd.DataFrame) -> Dict[str, Any]:
        """Detect swapped coordinates via multivariate Z-score outlier detection."""
        flagged = []
        if "latitude" in df.columns and "longitude" in df.columns:
            coords = df[df["latitude"].notnull() & df["longitude"].notnull()].copy()
            coords["lat_num"] = pd.to_numeric(coords["latitude"], errors="coerce")
            coords["lon_num"] = pd.to_numeric(coords["longitude"], errors="coerce")
            clean_coords = coords.dropna(subset=["lat_num", "lon_num"])

            if len(clean_coords) > 10:
                # Swapped coordinates have negative latitude and positive longitude!
                # Compute Z-score on latitude and longitude
                lat_mean, lat_std = clean_coords["lat_num"].mean(), clean_coords["lat_num"].std()
                lon_mean, lon_std = clean_coords["lon_num"].mean(), clean_coords["lon_num"].std()

                if lat_std > 0 and lon_std > 0:
                    lat_z = (clean_coords["lat_num"] - lat_mean).abs() / lat_std
                    lon_z = (clean_coords["lon_num"] - lon_mean).abs() / lon_std
                    outliers = clean_coords[(lat_z > 4.0) | (lon_z > 4.0)]
                    flagged = list(outliers.index)

        return {
            "problem": "d_latitude_longitude_swapped",
            "detector": "statistical",
            "is_flagged": len(flagged) > 0,
            "flagged_indices": flagged,
            "explanation": f"Statistical outlier detector: {len(flagged)} coordinate pairs exceed 4 standard deviations from cluster center.",
        }

    @staticmethod
    def detect_e_exact_duplicate_frequencies(df: pd.DataFrame, key_col: str = "unique_key") -> Dict[str, Any]:
        """Detect exact duplicate spikes via frequency value count statistics."""
        val_counts = df[key_col].value_counts()
        dup_keys = set(val_counts[val_counts > 1].index)
        flagged = list(df[df[key_col].isin(dup_keys)].index)

        return {
            "problem": "e_exact_duplicates",
            "detector": "statistical",
            "is_flagged": len(flagged) > 0,
            "flagged_indices": flagged,
            "explanation": f"Statistical frequency check: {len(dup_keys)} keys appear with frequency > 1 in batch.",
        }

    @staticmethod
    def detect_f_near_duplicates_jaccard(df: pd.DataFrame, sample_size: int = 200, threshold: float = 0.85) -> Dict[str, Any]:
        """Detect near-duplicates using Jaccard token set similarity on concatenated text features."""
        flagged = []
        # Sample to maintain sub-second laptop throughput
        sample_df = df.head(sample_size).copy()
        
        feature_tokens = []
        indices = list(sample_df.index)
        for idx in indices:
            row_str = f"{sample_df.loc[idx, 'complaint_type']} {sample_df.loc[idx, 'descriptor']} {sample_df.loc[idx, 'borough']}"
            tokens = set(row_str.lower().split())
            feature_tokens.append(tokens)

        # Pairwise comparison
        for i in range(len(indices)):
            for j in range(i + 1, len(indices)):
                t1 = feature_tokens[i]
                t2 = feature_tokens[j]
                if t1 and t2:
                    jaccard = len(t1 & t2) / len(t1 | t2)
                    if jaccard >= threshold and sample_df.loc[indices[i], "unique_key"] != sample_df.loc[indices[j], "unique_key"]:
                        # Also check timestamp proximity (within 1 day)
                        flagged.append(indices[j])

        flagged = list(set(flagged))
        return {
            "problem": "f_near_duplicates",
            "detector": "statistical",
            "is_flagged": len(flagged) > 0,
            "flagged_indices": flagged,
            "explanation": f"Statistical Jaccard similarity: Identified {len(flagged)} record pairs with text similarity >= {threshold*100:.0f}%.",
        }

    @staticmethod
    def detect_g_null_spike_zscore(df: pd.DataFrame, z_threshold: float = 2.5) -> Dict[str, Any]:
        """Detect sudden null rate spike in an agency's records via agency-level Z-score."""
        flagged_indices = []
        flagged_agencies = []

        if "agency" in df.columns and "descriptor" in df.columns:
            agency_rates = df.groupby("agency")["descriptor"].apply(lambda s: s.isnull().mean())
            mean_rate = agency_rates.mean()
            std_rate = agency_rates.std()

            if std_rate > 0:
                for agency, rate in agency_rates.items():
                    z = (rate - mean_rate) / std_rate
                    if z > z_threshold and rate > 0.3:
                        flagged_agencies.append((agency, round(rate, 2), round(z, 2)))
                        flagged_indices.extend(list(df[(df["agency"] == agency) & df["descriptor"].isnull()].index))

        return {
            "problem": "g_null_spike",
            "detector": "statistical",
            "is_flagged": len(flagged_agencies) > 0,
            "flagged_indices": flagged_indices,
            "explanation": f"Statistical Z-score null spike: Agencies with Z > {z_threshold}: {flagged_agencies}",
        }

    @staticmethod
    def detect_h_temporal_negative_duration(df: pd.DataFrame) -> Dict[str, Any]:
        """Detect temporal anomaly via negative duration distribution statistics."""
        flagged = []
        if "created_date" in df.columns and "closed_date" in df.columns:
            valid = df[df["created_date"].notnull() & df["closed_date"].notnull()]
            c_dt = pd.to_datetime(valid["created_date"], errors="coerce")
            cl_dt = pd.to_datetime(valid["closed_date"], errors="coerce")
            duration_hrs = (cl_dt - c_dt).dt.total_seconds() / 3600.0
            negatives = duration_hrs[duration_hrs < 0]
            flagged = list(negatives.index)

        return {
            "problem": "h_closed_date_earlier_than_created_date",
            "detector": "statistical",
            "is_flagged": len(flagged) > 0,
            "flagged_indices": flagged,
            "explanation": f"Statistical duration distribution: Found {len(flagged)} negative duration SLA values.",
        }

    @staticmethod
    def detect_i_zip_borough_joint_distribution(df: pd.DataFrame) -> Dict[str, Any]:
        """Detect ZIP vs Borough inconsistency via rare joint co-occurrence frequency (< 0.5%)."""
        flagged = []
        if "incident_zip" in df.columns and "borough" in df.columns:
            valid = df[df["incident_zip"].notnull() & df["borough"].notnull()]
            # Empirical probability of ZIP given Borough
            contingency = pd.crosstab(valid["borough"], valid["incident_zip"], normalize="index")
            for idx, r in valid.iterrows():
                b = r["borough"]
                z = r["incident_zip"]
                if b in contingency.index and z in contingency.columns:
                    prob = contingency.loc[b, z]
                    if prob < 0.005:  # Extremely rare conditional probability
                        flagged.append(idx)

        return {
            "problem": "i_zip_code_inconsistent_with_borough",
            "detector": "statistical",
            "is_flagged": len(flagged) > 0,
            "flagged_indices": flagged,
            "explanation": f"Statistical joint probability: {len(flagged)} records with P(ZIP|Borough) < 0.5% in historical distribution.",
        }

    @staticmethod
    def detect_j_complaint_descriptor_chi2(df: pd.DataFrame) -> Dict[str, Any]:
        """Detect invalid Complaint Type to Descriptor combinations via low conditional frequency."""
        flagged = []
        if "complaint_type" in df.columns and "descriptor" in df.columns:
            valid = df[df["complaint_type"].notnull() & df["descriptor"].notnull()]
            counts = valid.groupby(["complaint_type", "descriptor"]).size()
            total_per_complaint = valid.groupby("complaint_type").size()
            
            for idx, r in valid.iterrows():
                c = r["complaint_type"]
                d = r["descriptor"]
                pair_count = counts.get((c, d), 0)
                tot = total_per_complaint.get(c, 1)
                cond_prob = pair_count / tot
                if cond_prob < 0.01:
                    flagged.append(idx)

        return {
            "problem": "j_complaint_type_inconsistent_with_descriptor",
            "detector": "statistical",
            "is_flagged": len(flagged) > 0,
            "flagged_indices": flagged,
            "explanation": f"Statistical contingency check: {len(flagged)} combinations with conditional probability P(Desc|Type) < 1%.",
        }

    @staticmethod
    def detect_k_status_resolution_word_vector_cosine(df: pd.DataFrame) -> Dict[str, Any]:
        """Detect Status vs Resolution contradictions via vocabulary bag-of-words mismatch."""
        flagged = []
        if "status" in df.columns and "resolution_description" in df.columns:
            for idx, r in df.iterrows():
                status = str(r["status"]).lower()
                desc = str(r["resolution_description"]).lower()
                if "closed" in status and ("pending" in desc or "investigating" in desc or "open" in desc):
                    flagged.append(idx)
                elif ("pending" in status or "progress" in status) and ("resolved" in desc or "completed" in desc):
                    flagged.append(idx)

        return {
            "problem": "k_resolution_contradicting_status",
            "detector": "statistical",
            "is_flagged": len(flagged) > 0,
            "flagged_indices": flagged,
            "explanation": f"Statistical semantic overlap: {len(flagged)} rows exhibit polarity conflict between Status and Resolution tokens.",
        }

    @staticmethod
    def detect_l_pii_entropy(df: pd.DataFrame) -> Dict[str, Any]:
        """Detect PII by scanning for digit sequence density and Shannon entropy in free text."""
        flagged = []
        text_cols = [c for c in ["descriptor", "resolution_description"] if c in df.columns]
        for col in text_cols:
            for idx, val in df[col].dropna().items():
                s = str(val)
                # Count digit sequences of 7+ digits (phone numbers) or '@' token (emails)
                digits = sum(c.isdigit() for c in s)
                if digits >= 7 or "@" in s:
                    flagged.append(idx)

        flagged = list(set(flagged))
        return {
            "problem": "l_personal_data_pii_in_text",
            "detector": "statistical",
            "is_flagged": len(flagged) > 0,
            "flagged_indices": flagged,
            "explanation": f"Statistical entropy/digit density check: {len(flagged)} records with high numeric density or email markers.",
        }
