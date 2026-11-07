"""
Task 2: Corruption Injector for NYC 311 Service Requests
Injects 12 specific problem types into clean batches at controlled rates,
returning the corrupted dataset along with row-level ground-truth masks.
"""

import random
import copy
from typing import Tuple, Dict, Any, List, Optional
import pandas as pd
import numpy as np


class CorruptionInjector:
    """
    Engine to inject 12 distinct data quality corruptions into clean NYC 311 batches.
    Each method returns (corrupted_df, ground_truth_mask_series).
    """

    def __init__(self, seed: int = 42):
        self.seed = seed
        random.seed(seed)
        np.random.seed(seed)

    def inject_a_renamed_or_dropped_column(
        self, df: pd.DataFrame, drop: bool = False, col_to_alter: str = "incident_zip"
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """Problem (a): Renamed or dropped column (schema corruption)."""
        corrupted = df.copy()
        mask = pd.Series([True] * len(df), index=df.index)  # entire batch affected by schema breakage
        if drop:
            corrupted = corrupted.drop(columns=[col_to_alter])
        else:
            corrupted = corrupted.rename(columns={col_to_alter: f"{col_to_alter}_renamed_err"})
        return corrupted, mask

    def inject_b_column_type_change(
        self, df: pd.DataFrame, rate: float = 0.05, col: str = "latitude"
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """Problem (b): Column type change (e.g., numeric float arriving as formatted string or corrupted text)."""
        corrupted = df.copy()
        mask = pd.Series([False] * len(df), index=df.index)
        n_corrupt = max(1, int(len(df) * rate))
        indices = np.random.choice(df.index, size=n_corrupt, replace=False)

        # Cast column to object and inject corrupt string representations
        corrupted[col] = corrupted[col].astype(object)
        for idx in indices:
            val = corrupted.loc[idx, col]
            corrupted.loc[idx, col] = f"STR_{val}_INVALID" if pd.notnull(val) else "N/A_NOT_NUMERIC"
            mask.loc[idx] = True

        return corrupted, mask

    def inject_c_date_format_switch(
        self, df: pd.DataFrame, switch_point: float = 0.5
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """Problem (c): Date format switch partway through a batch (e.g. MM/DD/YYYY to YYYY-MM-DD or DD/MM/YYYY)."""
        corrupted = df.copy()
        mask = pd.Series([False] * len(df), index=df.index)
        split_idx = int(len(df) * switch_point)

        for i in range(split_idx, len(df)):
            idx = df.index[i]
            val = corrupted.loc[idx, "created_date"]
            if pd.notnull(val):
                try:
                    dt = pd.to_datetime(val)
                    # Switch format from standard US MM/DD/YYYY to ISO YYYY-MM-DDTHH:MM:SS
                    corrupted.loc[idx, "created_date"] = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
                    mask.loc[idx] = True
                except Exception:
                    pass

        return corrupted, mask

    def inject_d_latitude_longitude_swapped(
        self, df: pd.DataFrame, rate: float = 0.05
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """Problem (d): Latitude and longitude coordinates swapped."""
        corrupted = df.copy()
        mask = pd.Series([False] * len(df), index=df.index)
        n_corrupt = max(1, int(len(df) * rate))
        indices = np.random.choice(df.index, size=n_corrupt, replace=False)

        for idx in indices:
            lat = corrupted.loc[idx, "latitude"]
            lon = corrupted.loc[idx, "longitude"]
            corrupted.loc[idx, "latitude"] = lon
            corrupted.loc[idx, "longitude"] = lat
            mask.loc[idx] = True

        return corrupted, mask

    def inject_e_exact_duplicates(
        self, df: pd.DataFrame, rate: float = 0.05
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """Problem (e): Exact duplicate rows duplicated within the batch."""
        corrupted = df.copy()
        n_dups = max(1, int(len(df) * rate))
        dup_indices = np.random.choice(df.index, size=n_dups, replace=False)

        duplicate_rows = df.loc[dup_indices].copy()
        corrupted = pd.concat([corrupted, duplicate_rows], ignore_index=True)
        
        mask = pd.Series([False] * len(corrupted), index=corrupted.index)
        # The newly appended rows are duplicates
        mask.iloc[len(df):] = True
        return corrupted, mask

    def inject_f_near_duplicates(
        self, df: pd.DataFrame, rate: float = 0.05
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """Problem (f): Near-duplicates (same request, slightly altered timestamp or text typo)."""
        corrupted = df.copy()
        n_dups = max(1, int(len(df) * rate))
        indices = np.random.choice(df.index, size=n_dups, replace=False)

        near_dups = []
        for idx in indices:
            row = df.loc[idx].copy()
            # Slightly alter unique key & timestamp by 2 minutes, or minor typo in descriptor
            row["unique_key"] = int(row["unique_key"]) + 999999
            if pd.notnull(row["descriptor"]):
                row["descriptor"] = str(row["descriptor"]) + " ."
            near_dups.append(row)

        corrupted = pd.concat([corrupted, pd.DataFrame(near_dups)], ignore_index=True)
        mask = pd.Series([False] * len(corrupted), index=corrupted.index)
        mask.iloc[len(df):] = True
        return corrupted, mask

    def inject_g_null_spike(
        self, df: pd.DataFrame, target_agency: str = "NYPD", spike_rate: float = 0.85
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """Problem (g): Null spike in one agency's records (e.g. NYPD complaint_type or incident_zip becomes null)."""
        corrupted = df.copy()
        mask = pd.Series([False] * len(df), index=df.index)
        
        agency_mask = corrupted["agency"] == target_agency
        agency_indices = corrupted[agency_mask].index

        for idx in agency_indices:
            if random.random() < spike_rate:
                corrupted.loc[idx, "descriptor"] = None
                corrupted.loc[idx, "incident_zip"] = None
                mask.loc[idx] = True

        return corrupted, mask

    def inject_h_closed_earlier_than_created(
        self, df: pd.DataFrame, rate: float = 0.05
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """Problem (h): Closed date earlier than created date (temporal paradox)."""
        corrupted = df.copy()
        mask = pd.Series([False] * len(df), index=df.index)
        
        # Only inject on rows that have valid closed dates
        closed_indices = corrupted[corrupted["closed_date"].notnull()].index
        n_corrupt = max(1, int(len(closed_indices) * rate))
        sample_indices = np.random.choice(closed_indices, size=n_corrupt, replace=False)

        for idx in sample_indices:
            try:
                created_dt = pd.to_datetime(corrupted.loc[idx, "created_date"])
                # Set closed date to 3 days BEFORE created date
                earlier_dt = created_dt - pd.Timedelta(days=random.randint(1, 10))
                corrupted.loc[idx, "closed_date"] = earlier_dt.strftime("%m/%d/%Y %I:%M:%S %p")
                mask.loc[idx] = True
            except Exception:
                pass

        return corrupted, mask

    def inject_i_zip_inconsistent_with_borough(
        self, df: pd.DataFrame, rate: float = 0.05
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """Problem (i): ZIP code inconsistent with borough (e.g., Bronx borough with Staten Island 10301 ZIP)."""
        corrupted = df.copy()
        mask = pd.Series([False] * len(df), index=df.index)
        n_corrupt = max(1, int(len(df) * rate))
        indices = np.random.choice(df.index, size=n_corrupt, replace=False)

        for idx in indices:
            current_borough = str(corrupted.loc[idx, "borough"]).upper()
            # Swap with completely wrong borough's ZIP
            if "MANHATTAN" in current_borough:
                corrupted.loc[idx, "incident_zip"] = "10314"  # Staten Island ZIP in Manhattan
            else:
                corrupted.loc[idx, "incident_zip"] = "10001"  # Manhattan ZIP in outer borough
            mask.loc[idx] = True

        return corrupted, mask

    def inject_j_complaint_type_inconsistent_with_descriptor(
        self, df: pd.DataFrame, rate: float = 0.05
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """Problem (j): Complaint Type inconsistent with Descriptor (e.g. Noise complaint with Pothole descriptor)."""
        corrupted = df.copy()
        mask = pd.Series([False] * len(df), index=df.index)
        n_corrupt = max(1, int(len(df) * rate))
        indices = np.random.choice(df.index, size=n_corrupt, replace=False)

        mismatched_descriptors = [
            ("Noise - Residential", "Pothole"),
            ("Illegal Parking", "Catch Basin Clogged"),
            ("Water System", "Loud Music/Party"),
            ("Dirty Conditions", "Light Timing"),
        ]

        for idx in indices:
            _, mismatch = random.choice(mismatched_descriptors)
            corrupted.loc[idx, "descriptor"] = mismatch
            mask.loc[idx] = True

        return corrupted, mask

    def inject_k_resolution_contradicting_status(
        self, df: pd.DataFrame, rate: float = 0.05
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """Problem (k): Resolution Description contradicting Status (e.g., Status='Closed' but text='Pending investigation')."""
        corrupted = df.copy()
        mask = pd.Series([False] * len(df), index=df.index)
        n_corrupt = max(1, int(len(df) * rate))
        indices = np.random.choice(df.index, size=n_corrupt, replace=False)

        for idx in indices:
            status = corrupted.loc[idx, "status"]
            if status == "Closed":
                corrupted.loc[idx, "resolution_description"] = (
                    "The complaint is still open and currently pending field inspection. No action has been taken yet."
                )
            else:
                corrupted.loc[idx, "resolution_description"] = (
                    "Case fully resolved and closed on site. Final resolution completed."
                )
            mask.loc[idx] = True

        return corrupted, mask

    def inject_l_personal_data_pii(
        self, df: pd.DataFrame, rate: float = 0.05
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """Problem (l): Personal data (phone numbers, emails, personal names) leaked inside free-text fields."""
        corrupted = df.copy()
        mask = pd.Series([False] * len(df), index=df.index)
        n_corrupt = max(1, int(len(df) * rate))
        indices = np.random.choice(df.index, size=n_corrupt, replace=False)

        pii_samples = [
            " Please call complainant John Doe at 917-555-0199 for building access.",
            " Contact tenant Jane Smith at jane.smith@gmail.com regarding the leak.",
            " Contact officer Robert Davis cell: (212) 555-4321 immediately.",
            " Landlord email is contact_owner@yahoo.com or tel 718-555-8822.",
        ]

        for idx in indices:
            orig = str(corrupted.loc[idx, "descriptor"] or "")
            corrupted.loc[idx, "descriptor"] = orig + random.choice(pii_samples)
            mask.loc[idx] = True

        return corrupted, mask
