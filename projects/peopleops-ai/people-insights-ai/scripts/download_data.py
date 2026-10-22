"""Fetch only the pinned public IBM CSV and verify it before replacing local data."""

import hashlib
import json
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import io

import pandas as pd

from app.data_loader import validate_data


def main():
    metadata = json.loads((ROOT / "data/source.json").read_text())
    try:
        response = httpx.get(metadata["source_url"], timeout=30, follow_redirects=True)
        response.raise_for_status()
        content = response.content
        if hashlib.sha256(content).hexdigest() != metadata["sha256"]:
            raise ValueError("Downloaded CSV does not match the pinned source checksum")
        frame = validate_data(pd.read_csv(io.BytesIO(content)))
        if len(frame) != 1470:
            raise ValueError("Expected 1,470 IBM sample records")
        target = ROOT / "data/ibm_hr.csv"
        pending = target.with_suffix(".csv.tmp")
        pending.write_bytes(content)
        pending.replace(target)
        print(
            f"Verified {len(frame):,} synthetic IBM records. SHA-256: {metadata['sha256']}"
        )
    except (httpx.HTTPError, ValueError) as error:
        raise SystemExit(
            f"IBM download failed: {error}. No replacement dataset was generated."
        ) from error


if __name__ == "__main__":
    main()
