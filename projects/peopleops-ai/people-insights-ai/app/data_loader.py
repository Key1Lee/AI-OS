"""Validate the public IBM sample, keeping missing values distinct from bad data."""

import hashlib
import json
from pathlib import Path

import pandas as pd

from .models import DEPARTMENTS

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "EmployeeNumber",
    "Department",
    "JobSatisfaction",
    "WorkLifeBalance",
    "Attrition",
    "OverTime",
]


def validate_data(frame):
    """Reject malformed records and preserve null metric answers for correct denominators."""
    if frame.empty or not set(REQUIRED).issubset(frame.columns):
        raise ValueError("IBM data is empty or is missing required columns")
    data = frame[REQUIRED].copy()
    identifiers = pd.to_numeric(data["EmployeeNumber"], errors="coerce")
    if (
        identifiers.isna().any()
        or (identifiers % 1 != 0).any()
        or identifiers.duplicated().any()
    ):
        raise ValueError("Employee identifiers must be unique integers")
    if not data["Department"].isin(DEPARTMENTS).all():
        raise ValueError("Unsupported or missing department in IBM data")
    for column in ("JobSatisfaction", "WorkLifeBalance"):
        numeric = pd.to_numeric(data[column], errors="coerce")
        invalid = data[column].notna() & (~numeric.isin([1, 2, 3, 4]))
        if invalid.any():
            raise ValueError(f"{column} must contain 1–4 or null")
        data[column] = numeric
    for column in ("Attrition", "OverTime"):
        if (data[column].notna() & ~data[column].isin(["Yes", "No"])).any():
            raise ValueError(f"{column} must contain Yes, No or null")
    return data


def load_data(path=ROOT / "data/ibm_hr.csv", verify_source=True):
    """Load the bundled CSV and verify its fingerprint; never substitute generated records."""
    try:
        content = Path(path).read_bytes()
        if verify_source:
            metadata = json.loads((ROOT / "data/source.json").read_text())
            if hashlib.sha256(content).hexdigest() != metadata["sha256"]:
                raise ValueError(
                    "IBM CSV checksum mismatch; rerun scripts/download_data.py"
                )
        data = validate_data(pd.read_csv(path))
        if verify_source and len(data) != 1470:
            raise ValueError("The pinned IBM sample must contain 1,470 records")
        return data
    except (OSError, pd.errors.ParserError, pd.errors.EmptyDataError) as error:
        raise ValueError(
            "IBM data unavailable or malformed; run scripts/download_data.py"
        ) from error
