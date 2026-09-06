"""Carbon-aware decision engine combining temporal + spatial policies."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import redis
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent / "carbon-ingest"))

from algorithms import baseline, spatial, temporal  # noqa: E402
from models import Decision, JobRequest  # noqa: E402
from redis_store import DEFAULT_REGIONS, read_all_intensities  # noqa: E402

load_dotenv(ROOT.parent / ".env")


def get_redis() -> redis.Redis:
    url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    return redis.Redis.from_url(url, decode_responses=True)


def load_intensities(client: redis.Redis | None = None) -> dict[str, float]:
    client = client or get_redis()
    payloads = read_all_intensities(client, DEFAULT_REGIONS)
    if not payloads:
        raise RuntimeError(
            "No carbon data in Redis. Start the stack with: docker compose up --build"
        )
    return {
        region: float(payload["intensity_g_per_kwh"])
        for region, payload in payloads.items()
    }


def decide(
    job: JobRequest,
    policy: str = "temporal",
    intensities: dict[str, float] | None = None,
    threshold: float | None = None,
    now: datetime | None = None,
) -> Decision:
    intensities = intensities or load_intensities()
    threshold = threshold if threshold is not None else float(
        os.getenv("CARBON_THRESHOLD_G_PER_KWH", "400")
    )
    now = now or datetime.now(timezone.utc)

    if policy == "baseline":
        return baseline.decide(job, intensities)
    if policy == "spatial":
        return spatial.decide(job, intensities, threshold)
    if policy == "carbon_aware":
        # Prefer wait when dirty; if cannot wait (deadline), try spatial shift.
        temporal_decision = temporal.decide(job, intensities, threshold, now=now)
        if temporal_decision.action == "WAIT":
            return temporal_decision
        if temporal_decision.action == "RUN_NOW" and job.allow_spatial_shift:
            # Deadline forced run, or already green — still check greener region.
            spatial_decision = spatial.decide(job, intensities, threshold)
            if spatial_decision.action == "SHIFT_REGION":
                return spatial_decision
        return temporal_decision
    if policy == "temporal":
        return temporal.decide(job, intensities, threshold, now=now)

    raise ValueError(f"Unknown policy: {policy}")


def decision_to_dict(decision: Decision) -> dict:
    return {
        "action": decision.action,
        "region": decision.region,
        "reason": decision.reason,
        "current_intensity_g_per_kwh": decision.current_intensity_g_per_kwh,
        "estimated_emissions_g": round(decision.estimated_emissions_g, 2),
        "alternative_emissions_g": (
            round(decision.alternative_emissions_g, 2)
            if decision.alternative_emissions_g is not None
            else None
        ),
        "carbon_saved_pct": decision.carbon_saved_pct,
    }


def print_decision(job: JobRequest, decision: Decision, policy: str) -> None:
    print("=" * 60)
    print(f"Job:      {job.job_id}")
    print(f"Policy:   {policy}")
    print(f"Prefer:   {job.preferred_region}")
    print(f"Max wait: {job.max_delay_hours}h (deadline {job.deadline.isoformat()})")
    print("-" * 60)
    print(json.dumps(decision_to_dict(decision), indent=2))
    print("=" * 60)
