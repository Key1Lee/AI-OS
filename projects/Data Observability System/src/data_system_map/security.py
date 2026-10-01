import re


def redact(value: str | None) -> str | None:
    if value is None:
        return None
    value = re.sub(r"(?i)\b(password|passwd|api[_-]?key|access[_-]?token|secret|authorization)\s*[:=]\s*(['\"]?)[^\s,;]+", r"\1=[REDACTED]", value)
    value = re.sub(r"\bsk-[A-Za-z0-9_-]{8,}", "[REDACTED]", value)
    value = re.sub(r"(?i)([a-z][a-z0-9+.-]*://)[^\s/@]+:[^\s/@]+@", r"\1[REDACTED]@", value)
    return value
