"""One stable deterministic definition; later families are intentionally absent."""
from dataclasses import dataclass
from .contracts import SCENARIO_ID

@dataclass(frozen=True)
class Scenario:
    id: str
    concept: str
    priority: str
    initial_state: str
    input_data: str
    healthy_behavior: str
    fault: str
    symptoms: tuple[str, ...]
    diagnosis: str
    remediation: str
    verification: tuple[str, ...]

IDEMPOTENCY = Scenario(
    id=SCENARIO_ID, concept="idempotency", priority="MUST KNOW",
    initial_state="Empty isolated warehouse; append loader; one stable source key per order",
    input_data="Seed 42: 1,000 completed USD orders; seven fixture tables",
    healthy_behavior="1,000 rows, unique order_id, USD 53,945.00 gross completed-order revenue",
    fault="Commit 700 rows, inject transient worker crash, native retry appends all 1,000 rows",
    symptoms=("Successful retry", "1,700 loaded/fact rows", "700 extra duplicate IDs", "USD 91,448.50 untrusted revenue", "Publication blocked; dashboard impact"),
    diagnosis="Loader lacks idempotent writes; retry eligibility alone does not provide data correctness",
    remediation="Repair historical duplicates; enforce order_id uniqueness; upsert by stable order_id",
    verification=("root_cause_resolved", "data_corrected", "quality_checks_pass", "models_correct",
                  "downstream_recovered", "rerun_safe", "partial_write_retry_safe", "historic_failure_preserved"),
)
SCENARIOS = {IDEMPOTENCY.id: IDEMPOTENCY}
