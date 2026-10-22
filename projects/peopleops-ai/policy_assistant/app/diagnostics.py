"""Record actual elapsed component work without retaining request/source content."""
from contextlib import contextmanager
from time import perf_counter

from app.models import ExecutionStage

STAGES = ("authentication", "intent", "authorization", "data_source", "retrieval", "validation", "response")


class ExecutionTrace:
    def __init__(self):
        self.stages = []

    @contextmanager
    def step(self, stage, rule_ids=()):
        start = perf_counter()
        result = ExecutionStage(stage=stage, status="passed", duration_ms=0, rule_ids=list(rule_ids))
        try:
            yield result
        except Exception:
            result.status = "failed"
            raise
        finally:
            result.duration_ms = round((perf_counter()-start)*1000, 4)
            self.stages.append(result)

    def complete(self):
        """Mark unexecuted mandatory stages as skipped rather than inventing timings."""
        done = {row.stage for row in self.stages}
        return self.stages + [ExecutionStage(stage=stage, status="skipped", duration_ms=0) for stage in STAGES if stage not in done]
