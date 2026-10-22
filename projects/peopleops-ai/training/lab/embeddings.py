"""Deterministic hash embeddings for plumbing, not a semantic model."""
import hashlib
import math
import re


def embed(text: str) -> list[float]:
    values = [0.0] * 64
    for word in re.findall(r"[a-z0-9]+", text.lower()):
        digest = hashlib.sha256(word.encode()).digest()
        values[int.from_bytes(digest[:4], "big") % 64] += 1.0
    norm = math.sqrt(sum(v * v for v in values))
    return [v / norm for v in values] if norm else values
