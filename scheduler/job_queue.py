"""Redis-backed pending job queue for the carbon-aware controller."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import redis

from models import JobRequest

QUEUE_KEY = "jobs:pending"
STATUS_PREFIX = "jobs:status:"
DECISION_PREFIX = "jobs:decision:"


def enqueue(
    client: redis.Redis,
    job: JobRequest,
    *,
    policy: str = "carbon_aware",
    run_seconds: int = 20,
) -> None:
    payload = {
        "job_id": job.job_id,
        "max_delay_hours": job.max_delay_hours,
        "preferred_region": job.preferred_region,
        "allow_spatial_shift": job.allow_spatial_shift,
        "estimated_runtime_hours": job.estimated_runtime_hours,
        "estimated_power_kw": job.estimated_power_kw,
        "submitted_at": job.submitted_at.isoformat(),
        "policy": policy,
        "run_seconds": max(5, min(int(run_seconds), 300)),
    }
    client.rpush(QUEUE_KEY, json.dumps(payload))
    set_status(client, job.job_id, "queued", {"policy": policy})


def dequeue(client: redis.Redis, timeout: int = 2) -> dict[str, Any] | None:
    item = client.blpop(QUEUE_KEY, timeout=timeout)
    if not item:
        return None
    _, raw = item
    return json.loads(raw)


def requeue(client: redis.Redis, payload: dict[str, Any]) -> None:
    client.rpush(QUEUE_KEY, json.dumps(payload))


def set_status(
    client: redis.Redis,
    job_id: str,
    status: str,
    extra: dict[str, Any] | None = None,
) -> None:
    data = {"status": status, "updated_at": datetime.now(timezone.utc).isoformat()}
    if extra:
        data.update(extra)
    client.set(f"{STATUS_PREFIX}{job_id}", json.dumps(data))


def get_status(client: redis.Redis, job_id: str) -> dict[str, Any] | None:
    raw = client.get(f"{STATUS_PREFIX}{job_id}")
    return json.loads(raw) if raw else None


def save_decision(client: redis.Redis, job_id: str, decision: dict[str, Any]) -> None:
    client.set(f"{DECISION_PREFIX}{job_id}", json.dumps(decision))


def payload_to_job(payload: dict[str, Any]) -> JobRequest:
    submitted = datetime.fromisoformat(payload["submitted_at"])
    return JobRequest(
        job_id=payload["job_id"],
        max_delay_hours=float(payload.get("max_delay_hours", 4)),
        preferred_region=payload.get("preferred_region", "VIC1"),
        allow_spatial_shift=bool(payload.get("allow_spatial_shift", True)),
        estimated_runtime_hours=float(payload.get("estimated_runtime_hours", 1.0)),
        estimated_power_kw=float(payload.get("estimated_power_kw", 0.5)),
        submitted_at=submitted,
    )
