from __future__ import annotations


class ScriptedIO:
    def __init__(self, inputs: list[str]):
        self.inputs = iter(inputs)
        self.output: list[str] = []

    def write(self, text: str = "") -> None:
        self.output.append(text)

    def read(self, prompt: str = "") -> str:
        self.output.append(prompt)
        try:
            return next(self.inputs)
        except StopIteration as exc:
            raise AssertionError(f"Application requested unexpected input: {prompt}") from exc

    @property
    def transcript(self) -> str:
        return "\n".join(self.output)
