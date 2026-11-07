"""
Task 3a: Declarative Rule and Schema Checks Detector Family
Covers all 12 problem types (a through l) with deterministic, low-cost row-level checks.
"""

import re
from typing import Dict, Any, List, Set, Tuple
import pandas as pd
from ..data_sample import BOROUGH_ZIP_MAP, TAXONOMY


EXPECTED_COLUMNS = [
    "unique_key", "created_date", "closed_date", "agency", "complaint_type",
    "descriptor", "location_type", "incident_zip", "borough", "status",
    "resolution_description", "latitude", "longitude"
]

PHONE_PATTERN = re.compile(r"\b(?:\+?1[-.]?)?\(?[2-9]\d{2}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
DATE_STANDARD_PATTERN = re.compile(r"^\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2}\s+(?:AM|PM)$")


class RuleDetectors:
    """Declarative rules, schema enforcements, and lookup validators."""

    @staticmethod
    def detect_a_schema_columns(df: pd.DataFrame, expected_cols: List[str] = EXPECTED_COLUMNS) -> Dict[str, Any]:
        """Detect missing or renamed columns against the statutory 311 schema."""
        current_cols = set(df.columns)
        missing = [c for c in expected_cols if c not in current_cols]
        unexpected = [c for c in current_cols if c not in expected_cols]

        is_corrupt = len(missing) > 0 or len(unexpected) > 0
        explanation = "Schema Valid"
        if is_corrupt:
            explanation = f"Schema violation: Missing required columns: {missing}; Unexpected columns: {unexpected}"

        return {
            "problem": "a_renamed_or_dropped_column",
            "detector": "rule",
            "is_flagged": is_corrupt,
            "flagged_indices": list(df.index) if is_corrupt else [],
            "explanation": explanation,
            "missing_columns": missing,
            "unexpected_columns": unexpected,
        }

    @staticmethod
    def detect_b_column_types(df: pd.DataFrame, numeric_col: str = "latitude") -> Dict[str, Any]:
        """Detect numeric columns arriving as invalid strings."""
        flagged = []
        if numeric_col in df.columns:
            # Check non-null values that fail float conversion
            series = df[numeric_col].dropna()
            for idx, val in series.items():
                if isinstance(val, str):
                    try:
                        float(val)
                    except ValueError:
                        flagged.append(idx)

        return {
            "problem": "b_column_type_change",
            "detector": "rule",
            "is_flagged": len(flagged) > 0,
            "flagged_indices": flagged,
            "explanation": f"Found {len(flagged)} non-numeric string values in numeric column '{numeric_col}'.",
        }

    @staticmethod
    def detect_c_date_format_switch(df: pd.DataFrame, date_col: str = "created_date") -> Dict[str, Any]:
        """Detect date format switches that violate standard MM/DD/YYYY format."""
        flagged = []
        if date_col in df.columns:
            for idx, val in df[date_col].dropna().items():
                val_str = str(val).strip()
                if not DATE_STANDARD_PATTERN.match(val_str):
                    flagged.append(idx)

        return {
            "problem": "c_date_format_switch",
            "detector": "rule",
            "is_flagged": len(flagged) > 0,
            "flagged_indices": flagged,
            "explanation": f"Found {len(flagged)} dates failing standard format 'MM/DD/YYYY HH:MM:SS AM/PM'.",
        }

    @staticmethod
    def detect_d_lat_lon_swapped(df: pd.DataFrame) -> Dict[str, Any]:
        """Detect latitude and longitude swapped using NYC coordinate bounding box."""
        # NYC Latitude is always ~ +40.5 to +40.9; Longitude is always ~ -74.3 to -73.7
        flagged = []
        if "latitude" in df.columns and "longitude" in df.columns:
            coords = df[df["latitude"].notnull() & df["longitude"].notnull()]
            for idx, r in coords.iterrows():
                try:
                    lat = float(r["latitude"])
                    lon = float(r["longitude"])
                    # If lat is negative or lon is positive / around 40, they are swapped
                    if lat < 0 and lon > 0:
                        flagged.append(idx)
                    elif (35.0 <= lon <= 45.0) and (-75.0 <= lat <= -70.0):
                        flagged.append(idx)
                except (ValueError, TypeError):
                    pass

        return {
            "problem": "d_latitude_longitude_swapped",
            "detector": "rule",
            "is_flagged": len(flagged) > 0,
            "flagged_indices": flagged,
            "explanation": f"Identified {len(flagged)} rows with inverted Latitude/Longitude outside NYC bounding box.",
        }

    @staticmethod
    def detect_e_exact_duplicates(df: pd.DataFrame, key_col: str = "unique_key") -> Dict[str, Any]:
        """Detect exact duplicate records via primary key or row hashing."""
        dup_mask = df.duplicated(subset=[key_col], keep="first")
        flagged = list(df[dup_mask].index)

        return {
            "problem": "e_exact_duplicates",
            "detector": "rule",
            "is_flagged": len(flagged) > 0,
            "flagged_indices": flagged,
            "explanation": f"Found {len(flagged)} exact duplicate rows with duplicate '{key_col}'.",
        }

    @staticmethod
    def detect_f_near_duplicates(df: pd.DataFrame) -> Dict[str, Any]:
        """Detect near-duplicates using deterministic composite matching rule."""
        # Rule: Same created_date + same agency + same complaint_type + same incident_zip
        subset_cols = [c for c in ["created_date", "agency", "complaint_type", "incident_zip"] if c in df.columns]
        flagged = []
        if len(subset_cols) >= 3:
            dups = df.duplicated(subset=subset_cols, keep="first")
            flagged = list(df[dups].index)

        return {
            "problem": "f_near_duplicates",
            "detector": "rule",
            "is_flagged": len(flagged) > 0,
            "flagged_indices": flagged,
            "explanation": f"Found {len(flagged)} candidate near-duplicates matching identical timestamp, agency, and complaint type.",
        }

    @staticmethod
    def detect_g_null_spike(df: pd.DataFrame, threshold_rate: float = 0.50) -> Dict[str, Any]:
        """Detect null spikes in agency records using threshold rules."""
        flagged_agencies = []
        flagged_indices = []

        if "agency" in df.columns:
            for agency, grp in df.groupby("agency"):
                null_rate = grp["descriptor"].isnull().mean() if "descriptor" in grp.columns else 0.0
                if null_rate >= threshold_rate:
                    flagged_agencies.append((agency, round(null_rate, 2)))
                    flagged_indices.extend(list(grp[grp["descriptor"].isnull()].index))

        return {
            "problem": "g_null_spike",
            "detector": "rule",
            "is_flagged": len(flagged_agencies) > 0,
            "flagged_indices": flagged_indices,
            "explanation": f"Detected null spike in agencies exceeding {threshold_rate*100:.0f}%: {flagged_agencies}",
        }

    @staticmethod
    def detect_h_closed_before_created(df: pd.DataFrame) -> Dict[str, Any]:
        """Detect temporal ordering violations (Closed Date < Created Date)."""
        flagged = []
        if "created_date" in df.columns and "closed_date" in df.columns:
            valid = df[df["created_date"].notnull() & df["closed_date"].notnull()]
            for idx, r in valid.iterrows():
                try:
                    c_dt = pd.to_datetime(r["created_date"])
                    cl_dt = pd.to_datetime(r["closed_date"])
                    if cl_dt < c_dt:
                        flagged.append(idx)
                except Exception:
                    pass

        return {
            "problem": "h_closed_date_earlier_than_created_date",
            "detector": "rule",
            "is_flagged": len(flagged) > 0,
            "flagged_indices": flagged,
            "explanation": f"Found {len(flagged)} temporal inversions where closed_date precedes created_date.",
        }

    @staticmethod
    def detect_i_zip_borough_inconsistent(df: pd.DataFrame) -> Dict[str, Any]:
        """Detect geographic ZIP code vs Borough mismatches via lookup dictionary."""
        flagged = []
        if "incident_zip" in df.columns and "borough" in df.columns:
            for idx, r in df.iterrows():
                b = str(r["borough"]).upper().strip() if pd.notnull(r["borough"]) else None
                z = str(r["incident_zip"]).strip() if pd.notnull(r["incident_zip"]) else None
                if b and z and b in BOROUGH_ZIP_MAP:
                    valid_zips = BOROUGH_ZIP_MAP[b]
                    prefix = z[:3]
                    valid_prefixes = {vz[:3] for vz in valid_zips}
                    if prefix not in valid_prefixes and z not in valid_zips:
                        flagged.append(idx)

        return {
            "problem": "i_zip_code_inconsistent_with_borough",
            "detector": "rule",
            "is_flagged": len(flagged) > 0,
            "flagged_indices": flagged,
            "explanation": f"Found {len(flagged)} records where ZIP prefix does not belong to the stated NYC borough.",
        }

    @staticmethod
    def detect_j_complaint_descriptor_mismatch(df: pd.DataFrame) -> Dict[str, Any]:
        """Detect categorical taxonomy mismatches between Complaint Type and Descriptor."""
        flagged = []
        if "complaint_type" in df.columns and "descriptor" in df.columns:
            # Build valid complaint -> descriptors map
            valid_pairs: Dict[str, Set[str]] = {}
            for agency_dict in TAXONOMY.values():
                for c_type, desc_list in agency_dict.items():
                    if c_type not in valid_pairs:
                        valid_pairs[c_type] = set()
                    valid_pairs[c_type].update(desc_list)

            for idx, r in df.iterrows():
                c_type = r["complaint_type"]
                desc = r["descriptor"]
                if pd.notnull(c_type) and pd.notnull(desc) and c_type in valid_pairs:
                    if desc not in valid_pairs[c_type]:
                        flagged.append(idx)

        return {
            "problem": "j_complaint_type_inconsistent_with_descriptor",
            "detector": "rule",
            "is_flagged": len(flagged) > 0,
            "flagged_indices": flagged,
            "explanation": f"Found {len(flagged)} records with invalid Complaint Type to Descriptor combinations.",
        }

    @staticmethod
    def detect_k_resolution_contradicting_status(df: pd.DataFrame) -> Dict[str, Any]:
        """Detect semantic contradictions between Resolution Description and Status via keyword rules."""
        flagged = []
        if "status" in df.columns and "resolution_description" in df.columns:
            for idx, r in df.iterrows():
                status = str(r["status"]).lower().strip()
                desc = str(r["resolution_description"]).lower().strip()
                if pd.notnull(r["status"]) and pd.notnull(r["resolution_description"]):
                    if status == "closed":
                        # If closed but text explicitly states open/pending/no action taken yet
                        if any(k in desc for k in ["still open", "pending field inspection", "no action has been taken yet", "currently investigating"]):
                            flagged.append(idx)
                    elif status in ["pending", "in progress", "open"]:
                        if any(k in desc for k in ["fully resolved and closed", "final resolution completed", "condition was inspected and resolved"]):
                            flagged.append(idx)

        return {
            "problem": "k_resolution_contradicting_status",
            "detector": "rule",
            "is_flagged": len(flagged) > 0,
            "flagged_indices": flagged,
            "explanation": f"Found {len(flagged)} status-resolution text contradictions via keyword heuristic rules.",
        }

    @staticmethod
    def detect_l_pii(df: pd.DataFrame) -> Dict[str, Any]:
        """Detect phone numbers and email addresses leaked in free-text columns using regex."""
        flagged = []
        text_cols = [c for c in ["descriptor", "resolution_description"] if c in df.columns]
        for col in text_cols:
            for idx, text in df[col].dropna().items():
                s = str(text)
                if PHONE_PATTERN.search(s) or EMAIL_PATTERN.search(s):
                    flagged.append(idx)

        flagged = list(set(flagged))
        return {
            "problem": "l_personal_data_pii_in_text",
            "detector": "rule",
            "is_flagged": len(flagged) > 0,
            "flagged_indices": flagged,
            "explanation": f"Detected PII (phone number / email pattern) in {len(flagged)} free-text records.",
        }
