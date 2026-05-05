#!/usr/bin/env python3
"""
scripts/load_test.py
────────────────────
Generates high-volume signals to test the 10,000 signals/sec capacity.

Usage:
  pip install httpx
  python scripts/load_test.py --rate 500 --duration 30
  python scripts/load_test.py --rate 5000 --duration 10
"""
import asyncio
import argparse
import time
import httpx
import random

BASE_URL = "http://localhost:8000"

COMPONENTS = [
    ("POSTGRES_PRIMARY", "RDBMS",    "P0"),
    ("POSTGRES_REPLICA", "RDBMS",    "P1"),
    ("CACHE_CLUSTER_01", "CACHE",    "P2"),
    ("CACHE_CLUSTER_02", "CACHE",    "P2"),
    ("MCP_HOST_01",      "MCP_HOST", "P1"),
    ("API_GATEWAY_01",   "API",      "P0"),
    ("QUEUE_PRIMARY",    "QUEUE",    "P2"),
    ("NOSQL_01",         "NOSQL",    "P1"),
]

ERROR_CODES = [
    "CONNECTION_TIMEOUT", "LATENCY_SPIKE", "MEMORY_EXHAUSTION",
    "DISK_FULL", "CPU_THROTTLE", "PACKET_LOSS", "TLS_HANDSHAKE_FAIL",
]


async def send_batch(client: httpx.AsyncClient, signals: list[dict]) -> tuple[int, int]:
    """Send a batch of signals concurrently. Returns (success, failed)."""
    tasks = [
        client.post(f"{BASE_URL}/signals", json=sig, timeout=3.0)
        for sig in signals
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    success = sum(1 for r in results if isinstance(r, httpx.Response) and r.status_code in (200, 202))
    failed  = len(results) - success
    return success, failed


async def main(rate: int, duration: int):
    print(f"\nLoad Test: {rate} signals/sec for {duration}s = {rate * duration:,} total")
    print(f"Target: {BASE_URL}\n")

    # Verify backend
    try:
        async with httpx.AsyncClient() as c:
            r = await c.get(f"{BASE_URL}/health", timeout=3)
            print(f"Backend: {r.json().get('status')}\n")
    except Exception as e:
        print(f"Cannot reach backend: {e}")
        return

    total_sent = total_ok = total_fail = 0
    interval = 1.0 / rate      # seconds between signals (if rate=500, interval=0.002)
    batch_size = max(1, min(rate // 10, 100))   # send in batches of up to 100
    batch_interval = batch_size * interval

    start = time.monotonic()

    async with httpx.AsyncClient(limits=httpx.Limits(max_connections=200)) as client:
        while (time.monotonic() - start) < duration:
            batch_start = time.monotonic()

            # Build batch
            batch = []
            for _ in range(batch_size):
                comp_id, comp_type, severity = random.choice(COMPONENTS)
                batch.append({
                    "component_id":   comp_id,
                    "component_type": comp_type,
                    "error_code":     random.choice(ERROR_CODES),
                    "message":        f"Automated load test signal #{total_sent}",
                    "severity":       severity,
                    "metadata":       {"load_test": True, "seq": total_sent},
                })

            ok, fail = await send_batch(client, batch)
            total_ok   += ok
            total_fail += fail
            total_sent += batch_size

            elapsed = time.monotonic() - start
            actual_rate = total_sent / elapsed if elapsed > 0 else 0

            print(f"\r  [{elapsed:5.1f}s] Sent: {total_sent:6,} | OK: {total_ok:6,} | "
                  f"429/err: {total_fail:4,} | Rate: {actual_rate:6.0f}/sec", end="", flush=True)

            # Sleep to maintain target rate
            batch_elapsed = time.monotonic() - batch_start
            sleep = max(0, batch_interval - batch_elapsed)
            if sleep > 0:
                await asyncio.sleep(sleep)

    elapsed = time.monotonic() - start
    print(f"\n\nResults:")
    print(f"  Duration:      {elapsed:.1f}s")
    print(f"  Total sent:    {total_sent:,}")
    print(f"  Successful:    {total_ok:,}")
    print(f"  Rate limited:  {total_fail:,}")
    print(f"  Actual rate:   {total_sent / elapsed:.0f}/sec")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rate",     type=int, default=200,  help="Signals per second")
    parser.add_argument("--duration", type=int, default=20,   help="Duration in seconds")
    args = parser.parse_args()
    asyncio.run(main(args.rate, args.duration))
