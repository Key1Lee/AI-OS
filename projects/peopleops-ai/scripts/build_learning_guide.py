"""Keep the repository lesson guide aligned with the in-app learning path."""
from pathlib import Path
import json

root = Path(__file__).resolve().parents[1]
lessons = json.loads((root / "peopleops/web/lessons.json").read_text())
parts = ["# Twelve-phase learning guide\n\nThe complete application is available to inspect. These exercises let you rebuild\none small idea at a time; application completion does not imply learner mastery.\nRun commands from the project root. Each phase is an entry point for further\nmicro-steps, rather than a claim that one exercise covers every part of a phase.\n"]
for index, lesson in enumerate(lessons, 1):
    parts.append(f"\n## Phase {index} — {lesson['title']}\n\n**Business problem:** {lesson['business']}\n\n"
                 f"**Visual:**\n\n| Before | After |\n| --- | --- |\n| {lesson['before']} | {lesson['after']} |\n\n"
                 f"**Our task:** {lesson['task']}\n\n**Code:**\n\n```text\n{lesson['starter']}\n```\n\n"
                 f"**Explanation:** {lesson['explanation']}\n\n**How to verify:**\n\n```sh\n{lesson['command']}\n```\n\n"
                 f"Expected: {lesson['expected']}.\n\n**Your turn:** {lesson['question']}\n\n"
                 f"Source to inspect after attempting the exercise: `{lesson['file']}`.\n")
(root / "docs/learning-guide.md").write_text("".join(parts))
