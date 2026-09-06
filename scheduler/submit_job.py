#!/usr/bin/env python3
"""
Enqueue an analytics job for the carbon-aware controller.

Examples:
  python submit_job.py --job etl-night --delay 4 --region VIC1
  python submit_job.py --job urgent-1 --delay 0 --policy baseline --seconds 15
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from engine import get_redis  # noqa: E402
from job_queue import enqueue, get_status  # noqa: E402
from models import JobRequest  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Submit job to carbon-aware queue")
    parser.add_argument("--job", required=True, help="Unique job ID")
    parser.add_argument("--delay", type=float, default=4.0, help="Max delay hours")
    parser.add_argument("--region", default="VIC1", choices=["VIC1", "NSW1"])
    parser.add_argument(
        "--policy",
        default="carbon_aware",
        choices=["baseline", "temporal", "spatial", "carbon_aware"],
    )
    parser.add_argument("--seconds", type=int, default=20, help="Workload runtime seconds")
    parser.add_argument("--no-spatial", action="store_true")
    parser.add_argument("--runtime-hours", type=float, default=1.0, help="For emissions estimate")
    parser.add_argument("--power", type=float, default=0.5, help="Estimated kW for emissions")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    client = get_redis()
    job = JobRequest(
        job_id=args.job,
        max_delay_hours=args.delay,
        preferred_region=args.region,
        allow_spatial_shift=not args.no_spatial,
        estimated_runtime_hours=args.runtime_hours,
        estimated_power_kw=args.power,
    )
    enqueue(client, job, policy=args.policy, run_seconds=args.seconds)
    status = get_status(client, args.job)
    print(f"Queued job {args.job} policy={args.policy} status={status}")


if __name__ == "__main__":
    main()
