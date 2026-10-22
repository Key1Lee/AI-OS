"""Send bounded, real HTTP load to our localhost mock, never to Qualtrics."""

import argparse
import asyncio
import json
import math
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import httpx

from .fixture import export_fixture
from .mock_account import DEMO_API_TOKEN
from .pipeline import digest

BASE = "http://127.0.0.1:8812"


def percentile(values, fraction):
    """Calculate a latency percentile by linearly interpolating sorted samples."""
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    low, high = math.floor(position), math.ceil(position)
    return round(ordered[low] + (ordered[high] - ordered[low]) * (position - low), 3)


async def run_load(requests=500, concurrency=20):
    """Validate authentication, then download and check every synthetic export under load."""
    if not 1 <= requests <= 10000 or not 1 <= concurrency <= 50:
        raise ValueError("Use 1..10000 requests and 1..50 concurrent requests")
    expected = export_fixture()
    expected_hash = digest(expected)
    headers = {"X-API-TOKEN": DEMO_API_TOKEN}
    limits = httpx.Limits(
        max_connections=concurrency, max_keepalive_connections=concurrency
    )
    async with httpx.AsyncClient(
        base_url=BASE,
        timeout=10,
        limits=limits,
        follow_redirects=False,
        trust_env=False,
    ) as client:
        no_token = await client.get("/mock-qualtrics/account")
        wrong_token = await client.get(
            "/mock-qualtrics/account", headers={"X-API-TOKEN": "FAKE-WRONG-TOKEN"}
        )
        account = await client.get("/mock-qualtrics/account", headers=headers)
        assert no_token.status_code == wrong_token.status_code == 401
        assert (
            account.status_code == 200
            and account.json()["real_qualtrics_connected"] is False
        )
        started = await client.post("/mock-qualtrics/exports", headers=headers)
        started.raise_for_status()
        export_id = started.json()["export_id"]
        status = await client.get(
            f"/mock-qualtrics/exports/{export_id}", headers=headers
        )
        assert status.status_code == 200 and status.json()["status"] == "complete"
        route = f"/mock-qualtrics/exports/{export_id}/file"
        gate = asyncio.Semaphore(concurrency)

        async def download(index):
            async with gate:
                start = time.perf_counter()
                try:
                    response = await client.get(route, headers=headers)
                    latency = (time.perf_counter() - start) * 1000
                    valid = (
                        response.status_code == 200
                        and digest(response.json()) == expected_hash
                    )
                    return {
                        "request": index,
                        "status": response.status_code,
                        "latency_ms": latency,
                        "valid": valid,
                        "error": None
                        if valid
                        else "unexpected status or synthetic payload",
                    }
                except (httpx.HTTPError, ValueError) as error:
                    return {
                        "request": index,
                        "status": "transport_or_decode_error",
                        "latency_ms": (time.perf_counter() - start) * 1000,
                        "valid": False,
                        "error": type(error).__name__,
                    }

        started_at_utc = datetime.now(UTC).isoformat()
        start = time.perf_counter()
        results = await asyncio.gather(*(download(i + 1) for i in range(requests)))
        elapsed = time.perf_counter() - start
    valid = sum(r["valid"] for r in results)
    latencies = [r["latency_ms"] for r in results]
    return {
        "status": "passed" if valid == requests else "failed",
        "synthetic_only": True,
        "started_at_utc": started_at_utc,
        "target": BASE + route,
        "account_id": account.json()["account_id"],
        "requests": requests,
        "concurrency": concurrency,
        "successful_http_200": sum(r["status"] == 200 for r in results),
        "payloads_validated": valid,
        "failures": requests - valid,
        "http_status_counts": dict(Counter(str(r["status"]) for r in results)),
        "elapsed_seconds": round(elapsed, 4),
        "requests_per_second": round(requests / elapsed, 2),
        "latency_ms": {
            "p50": percentile(latencies, 0.5),
            "p95": percentile(latencies, 0.95),
            "p99": percentile(latencies, 0.99),
            "max": round(max(latencies), 3),
        },
        "auth_controls": {
            "missing_token": no_token.status_code,
            "wrong_token": wrong_token.status_code,
            "fake_token": account.status_code,
        },
        "setup_control_requests_excluded_from_load_count": 5,
        "mock_data": {
            "source_sha256": expected_hash,
            "rows_per_response": len(expected["responses"]),
            "response_rows_validated": valid * len(expected["responses"]),
            "unique_response_ids_per_export": len(
                {r["responseId"] for r in expected["responses"]}
            ),
            "note": "Repeated fixed fixture downloads; not new respondents or Gold writes",
        },
        "errors": [r for r in results if not r["valid"]][:10],
        "measurement": "Real localhost HTTP, keep-alive, no retries, HTTP latency excludes semaphore wait; percentiles use linear interpolation",
    }


def main():
    """Save a reproducible load report and exit unsuccessfully if any payload fails."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requests", type=int, default=500)
    parser.add_argument("--concurrency", type=int, default=20)
    args = parser.parse_args()
    report = asyncio.run(run_load(args.requests, args.concurrency))
    target = Path(__file__).parent / "reports/load-test.json"
    target.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if report["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
