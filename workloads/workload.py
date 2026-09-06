"""
Sample analytics workload: CPU-bound matrix work to simulate an ETL/ML job.

Usage:
  python workload.py --seconds 30
"""

from __future__ import annotations

import argparse
import time


def burn_cpu(seconds: float) -> None:
    end = time.time() + seconds
    x = 0.0
    while time.time() < end:
        # Tight loop to burn CPU
        x = (x + 1.000001) ** 1.000001
        if x > 1e12:
            x = 0.0
    print(f"Completed {seconds:.1f}s CPU burn (dummy result={x:.4f})")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=30.0)
    args = parser.parse_args()
    print(f"Starting simulated analytics job for {args.seconds:.1f}s...")
    burn_cpu(args.seconds)


if __name__ == "__main__":
    main()
