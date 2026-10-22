import json


def extract_documents(directory):
    """Read independent JSONL source records with bounded file and record sizes."""
    for path in sorted(directory.glob("*.jsonl")):
        if path.stat().st_size > 2_000_000:
            raise ValueError("Source file too large")
        for number, line in enumerate(path.read_text().splitlines(), 1):
            if not line.strip():
                continue
            try:
                if len(line) > 120_000:
                    raise ValueError("Record too large")
                yield path.name, number, json.loads(line), None
            except (ValueError, json.JSONDecodeError):
                yield path.name, number, None, "malformed_json"
