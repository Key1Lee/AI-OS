from lab.telemetry import Telemetry


def test_nearest_rank_percentile_and_bounded_window():
    telemetry = Telemetry()
    for latency in [10, 20]:
        telemetry.record(kind="http", route="/test", status=200, latency_ms=latency)
    assert telemetry.summary()["p95_latency_ms"] == 20
    for _ in range(1100):
        telemetry.record(kind="http", route="/test", status=200, latency_ms=1)
    assert telemetry.summary()["requests"] == 1000
