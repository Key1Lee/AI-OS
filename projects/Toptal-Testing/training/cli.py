from __future__ import annotations

import sys

from .application import TrainingApplication
from .config import Settings
from .llm import LLMUnavailable


def main() -> int:
    try:
        return TrainingApplication(Settings.from_env()).run()
    except (ValueError, RuntimeError, LLMUnavailable) as exc:
        print(f"Training system could not start safely: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
