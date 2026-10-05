from .bridge import invoke

class NativeModelingAdapter:
    def build(self, orders: list[dict], source: list[dict], run_id: str) -> dict:
        return invoke("modeling", {"orders": orders, "source": source, "run_id": run_id})
