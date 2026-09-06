#!/usr/bin/env python3
"""
Carbon-aware Job controller.

Polls Redis for queued analytics jobs, asks the decision engine what to do,
and either waits (requeues) or creates a Kubernetes Job on a region-labeled node.

Examples:
  python controller.py
  python controller.py --dry-run
  python controller.py --once
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent / "carbon-ingest"))

from dotenv import load_dotenv

from engine import decide, decision_to_dict, get_redis, load_intensities, print_decision
from job_queue import dequeue, payload_to_job, requeue, save_decision, set_status
from k8s_jobs import create_region_job, load_kube

load_dotenv(ROOT.parent / ".env")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Carbon-aware Kubernetes Job controller")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Decide and log only; do not create Kubernetes Jobs",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Process at most one queue item then exit",
    )
    parser.add_argument(
        "--wait-seconds",
        type=int,
        default=15,
        help="Sleep before requeue when action is WAIT (default: 15)",
    )
    parser.add_argument(
        "--image",
        default=os.getenv("WORKLOAD_IMAGE", "cas-workload:latest"),
        help="Container image for analytics Jobs",
    )
    return parser.parse_args()


def process_one(args: argparse.Namespace, batch=None) -> bool:
    """Returns True if a queue item was handled."""
    client = get_redis()
    payload = dequeue(client, timeout=2)
    if not payload:
        return False

    job = payload_to_job(payload)
    policy = payload.get("policy", "carbon_aware")
    run_seconds = int(payload.get("run_seconds", 20))

    intensities = load_intensities(client)
    decision = decide(job, policy=policy, intensities=intensities)
    decision_payload = decision_to_dict(decision)
    save_decision(client, job.job_id, decision_payload)
    print_decision(job, decision, policy)

    if decision.action == "WAIT":
        set_status(client, job.job_id, "waiting", decision_payload)
        print(f"[controller] WAIT — requeue in {args.wait_seconds}s")
        time.sleep(args.wait_seconds)
        requeue(client, payload)
        return True

    set_status(client, job.job_id, "scheduling", decision_payload)
    if args.dry_run:
        print(
            f"[controller] DRY-RUN would create Job on {decision.region} "
            f"image={args.image} seconds={run_seconds}"
        )
        set_status(
            client,
            job.job_id,
            "dry_run_scheduled",
            {"region": decision.region, **decision_payload},
        )
        return True

    if batch is None:
        batch = load_kube()

    k8s_name = create_region_job(
        batch,
        job.job_id,
        decision.region,
        image=args.image,
        run_seconds=run_seconds,
        decision=decision_payload,
        dry_run=False,
    )
    set_status(
        client,
        job.job_id,
        "scheduled",
        {"k8s_job": k8s_name, "region": decision.region, **decision_payload},
    )
    print(f"[controller] Created Kubernetes Job {k8s_name} on {decision.region}")
    return True


def main() -> None:
    args = parse_args()
    print(
        f"Controller starting (dry_run={args.dry_run}, once={args.once}, image={args.image})"
    )

    batch = None
    if not args.dry_run:
        batch = load_kube()
        print("Connected to Kubernetes API")

    if args.once:
        handled = process_one(args, batch=batch)
        if not handled:
            print("Queue empty — nothing to do")
        return

    print("Polling Redis queue jobs:pending ... (Ctrl+C to stop)")
    while True:
        try:
            handled = process_one(args, batch=batch)
            if not handled:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nController stopped")
            break


if __name__ == "__main__":
    main()
