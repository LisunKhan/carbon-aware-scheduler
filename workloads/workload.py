"""
Sample analytics workload: CPU-bound work to simulate an ETL/ML job.

Env vars (set by the Job controller):
  JOB_ID, CAS_REGION, RUN_SECONDS
"""

from __future__ import annotations

import argparse
import os
import time


def burn_cpu(seconds: float) -> None:
    end = time.time() + seconds
    x = 0.0
    while time.time() < end:
        x = (x + 1.000001) ** 1.000001
        if x > 1e12:
            x = 0.0
    print(f"Completed {seconds:.1f}s CPU burn (dummy result={x:.4f})")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--seconds",
        type=float,
        default=float(os.getenv("RUN_SECONDS", "20")),
    )
    args = parser.parse_args()

    job_id = os.getenv("JOB_ID", "unknown")
    region = os.getenv("CAS_REGION", "unknown")
    print(f"Starting simulated analytics job id={job_id} region={region} seconds={args.seconds:.1f}")
    burn_cpu(args.seconds)
    print(f"Finished job id={job_id} on region={region}")


if __name__ == "__main__":
    main()
