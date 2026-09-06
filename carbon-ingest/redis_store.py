"""Redis helpers for carbon intensity time-series."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

import redis

DEFAULT_REGIONS = ("VIC1", "NSW1")


def get_redis() -> redis.Redis:
    url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    return redis.Redis.from_url(url, decode_responses=True)


def intensity_key(region: str) -> str:
    return f"carbon:intensity:{region}"


def history_key(region: str) -> str:
    return f"carbon:history:{region}"


def write_intensity(
    client: redis.Redis,
    region: str,
    intensity_g_per_kwh: float,
    source: str,
    observed_at: datetime | None = None,
) -> dict[str, Any]:
    observed_at = observed_at or datetime.now(timezone.utc)
    payload = {
        "region": region,
        "intensity_g_per_kwh": round(float(intensity_g_per_kwh), 2),
        "source": source,
        "observed_at": observed_at.isoformat(),
        "unit": "gCO2/kWh",
    }
    client.set(intensity_key(region), json.dumps(payload))
    client.lpush(history_key(region), json.dumps(payload))
    client.ltrim(history_key(region), 0, 287)  # ~24h at 5-min intervals
    return payload


def read_intensity(client: redis.Redis, region: str) -> dict[str, Any] | None:
    raw = client.get(intensity_key(region))
    if not raw:
        return None
    return json.loads(raw)


def read_all_intensities(
    client: redis.Redis, regions: tuple[str, ...] = DEFAULT_REGIONS
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for region in regions:
        value = read_intensity(client, region)
        if value:
            result[region] = value
    return result
