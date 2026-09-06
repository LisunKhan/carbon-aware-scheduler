#!/usr/bin/env python3
"""
Submit a fake analytics job and print the carbon-aware scheduling decision.

Examples:
  python demo_submit.py --job etl-1 --delay 4 --policy temporal
  python demo_submit.py --job ml-1 --delay 0 --policy spatial
  python demo_submit.py --job batch-2 --delay 6 --policy carbon_aware
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from engine import decide, load_intensities, print_decision  # noqa: E402
from models import JobRequest  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Demo carbon-aware job submission")
    parser.add_argument("--job", default="demo-etl-1", help="Job ID")
    parser.add_argument("--delay", type=float, default=4.0, help="Max allowed delay (hours)")
    parser.add_argument(
        "--region",
        default="VIC1",
        choices=["VIC1", "NSW1"],
        help="Preferred NEM region",
    )
    parser.add_argument(
        "--policy",
        default="carbon_aware",
        choices=["baseline", "temporal", "spatial", "carbon_aware"],
        help="Scheduling policy",
    )
    parser.add_argument("--runtime", type=float, default=1.0, help="Estimated runtime hours")
    parser.add_argument("--power", type=float, default=0.5, help="Estimated power draw (kW)")
    parser.add_argument(
        "--no-spatial",
        action="store_true",
        help="Disable region shifting",
    )
    parser.add_argument(
        "--show-intensities",
        action="store_true",
        help="Print current Redis carbon intensities",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    intensities = load_intensities()

    if args.show_intensities:
        print("Current intensities (gCO2/kWh):")
        for region, value in intensities.items():
            print(f"  {region}: {value:.1f}")

    job = JobRequest(
        job_id=args.job,
        max_delay_hours=args.delay,
        preferred_region=args.region,
        allow_spatial_shift=not args.no_spatial,
        estimated_runtime_hours=args.runtime,
        estimated_power_kw=args.power,
    )
    decision = decide(job, policy=args.policy, intensities=intensities)
    print_decision(job, decision, args.policy)


if __name__ == "__main__":
    main()
