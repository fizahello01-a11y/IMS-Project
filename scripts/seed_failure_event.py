#!/usr/bin/env python3
"""
scripts/seed_failure_event.py
──────────────────────────────
Simulates a cascading failure:
  1. RDBMS (PostgreSQL replica) goes down → 100 signals in 10 seconds → 1 Work Item
  2. MCP Host detects DB outage → starts failing → new Work Item
  3. Cache cluster starts evicting → new Work Item

Usage:
  python scripts/seed_failure_event.py
  python scripts/seed_failure_event.py --url http://localhost:8000
"""
import asyncio
import argparse
import httpx
import random
import time

BASE_URL = "http://localhost:8000"

FAILURE_SCENARIOS = [
    {
        "name": "RDBMS Primary Outage (P0)",
        "signals": [
            {
                "component_id":   "POSTGRES_PRIMARY",
                "component_type": "RDBMS",
                "error_code":     "CONNECTION_TIMEOUT",
                "message":        "Primary DB replica unreachable – TCP timeout after 30s",
                "severity":       "P0",
            }
        ],
        "count": 110,    # > 100 to trigger debounce
        "interval": 0.08,
    },
    {
        "name": "MCP Host Cascade (P1)",
        "signals": [
            {
                "component_id":   "MCP_HOST_01",
                "component_type": "MCP_HOST",
                "error_code":     "DEPENDENCY_FAILURE",
                "message":        "MCP host cannot reach database layer – request queue backing up",
                "severity":       "P1",
            }
        ],
        "count": 50,
        "interval": 0.15,
    },
    {
        "name": "Cache Cluster Evictions (P2)",
        "signals": [
            {
                "component_id":   "CACHE_CLUSTER_01",
                "component_type": "CACHE",
                "error_code":     "EVICTION_SPIKE",
                "message":        "Cache hit rate dropped below 40% – mass evictions in progress",
                "severity":       "P2",
            }
        ],
        "count": 30,
        "interval": 0.2,
    },
]


async def send_signal(client: httpx.AsyncClient, signal: dict, url: str) -> bool:
    try:
        r = await client.post(f"{url}/signals", json=signal, timeout=5.0)
        return r.status_code == 202
    except Exception as e:
        print(f"  ⚠ Send failed: {e}")
        return False


async def run_scenario(client: httpx.AsyncClient, scenario: dict, url: str):
    name     = scenario["name"]
    count    = scenario["count"]
    interval = scenario["interval"]
    base_sig = scenario["signals"][0]

    print(f"\n{'─'*55}")
    print(f"🚨 Simulating: {name}")
    print(f"   Sending {count} signals over ~{count*interval:.1f}s")
    print(f"{'─'*55}")

    success = 0
    for i in range(count):
        sig = {
            **base_sig,
            "metadata": {
                "sequence": i + 1,
                "host": f"node-{random.randint(1,4)}",
                "latency_ms": random.randint(5000, 30000) if i < count // 2 else random.randint(200, 2000),
            }
        }
        ok = await send_signal(client, sig, url)
        if ok:
            success += 1
            if (i + 1) % 10 == 0:
                print(f"   [{i+1:3d}/{count}] ✓ Sent")
        await asyncio.sleep(interval)

    print(f"   ✅ Sent {success}/{count} signals")


async def main(url: str):
    print(f"\n{'═'*55}")
    print("  IMS Failure Simulation")
    print(f"  Target: {url}")
    print(f"{'═'*55}")

    # Verify backend is up
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{url}/health", timeout=5)
            health = r.json()
            print(f"\n✓ Backend healthy: {health.get('status')}")
    except Exception as e:
        print(f"\n✗ Cannot reach backend at {url}: {e}")
        print("  Make sure `docker compose up` is running first.")
        return

    async with httpx.AsyncClient() as client:
        for scenario in FAILURE_SCENARIOS:
            await run_scenario(client, scenario, url)
            await asyncio.sleep(2)   # brief pause between scenarios

    print(f"\n{'═'*55}")
    print("  Simulation complete! Check the dashboard at http://localhost:5173")
    print(f"{'═'*55}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=BASE_URL)
    args = parser.parse_args()
    asyncio.run(main(args.url))
