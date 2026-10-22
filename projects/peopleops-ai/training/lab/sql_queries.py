"""Read explicitly named exercise queries; no SQL solution lives here."""
from pathlib import Path
import re


def query(name):
    sql = (Path(__file__).parent.parent / "exercises" / "e03_analytics.sql").read_text()
    sections = re.split(r"^-- name: (\w+)\s*$", sql, flags=re.MULTILINE)
    queries = dict(zip(sections[1::2], sections[2::2]))
    if name not in queries:
        raise ValueError("Unknown metric")
    return queries[name]
