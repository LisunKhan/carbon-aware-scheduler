"""
Carbon intensity ingestion service.

Modes:
  - mock: synthetic VIC1/NSW1 profiles (no API key needed) — good for local testing
  - live: Open Electricity API (set OPENELECTRICITY_API_KEY)
"""

from __future__ import annotations

import math
import os
import time
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

from redis_store import DEFAULT_REGIONS, get_redis, write_intensity

load_dotenv()

# Open Electricity reports tCO2/MWh; convert to gCO2/kWh (×1000).
TCO2_PER_MWH_TO_G_PER_KWH = 1000.0


def mock_intensity(region: str, now: datetime | None = None) -> float:
    """
    Synthetic diurnal carbon curve for local testing.

    Midday solar trough, evening peak — rough NEM-like shape.
    VIC1 tends dirtier than NSW1 in this mock (brown coal effect).
    """
    now = now or datetime.now(timezone.utc).astimezone()
    hour = now.hour + now.minute / 60.0
    # Base sinusoid: low around 13:00, high around 19:00–20:00
    solar_dip = 180 * math.exp(-((hour - 13.0) ** 2) / 18.0)
    evening_peak = 220 * math.exp(-((hour - 19.5) ** 2) / 8.0)
    morning_bump = 80 * math.exp(-((hour - 7.5) ** 2) / 6.0)
    base = 520 if region == "VIC1" else 420
    value = base - solar_dip + evening_peak + morning_bump
    return max(80.0, value)


def fetch_live_intensities() -> dict[str, float]:
    """Fetch regional emissions intensity from Open Electricity."""
    from openelectricity import OEClient
    from openelectricity.types import DataMetric

    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=2)
    intensities: dict[str, float] = {}

    with OEClient() as client:
        response = client.get_network_data(
            network_code="NEM",
            metrics=[DataMetric.EMISSIONS_INTENSITY],
            interval="5m",
            date_start=start,
            date_end=end,
            primary_grouping="network_region",
        )

    for series in response.data:
        for result in series.results:
            region = None
            if hasattr(result, "columns") and result.columns is not None:
                region = getattr(result.columns, "network_region", None)
            if region is None and hasattr(result, "name"):
                # Fallback: sometimes region is encoded in the series name
                region = str(result.name)

            if region not in DEFAULT_REGIONS:
                continue
            if not result.data:
                continue
            latest = result.data[-1]
            if latest.value is None:
                continue
            # API unit is typically tCO2/MWh
            intensities[region] = float(latest.value) * TCO2_PER_MWH_TO_G_PER_KWH

    if not intensities:
        raise RuntimeError(
            "Live fetch returned no VIC1/NSW1 intensity values. "
            "Check API key, SDK version, and response shape."
        )
    return intensities


def poll_once(mode: str) -> None:
    client = get_redis()
    now = datetime.now(timezone.utc)

    if mode == "live":
        values = fetch_live_intensities()
        source = "openelectricity"
    else:
        values = {region: mock_intensity(region) for region in DEFAULT_REGIONS}
        source = "mock"

    for region, intensity in values.items():
        payload = write_intensity(client, region, intensity, source=source, observed_at=now)
        print(
            f"[{source}] {region}: {payload['intensity_g_per_kwh']} gCO2/kWh "
            f"@ {payload['observed_at']}",
            flush=True,
        )


def main() -> None:
    mode = os.getenv("CARBON_MODE", "mock").lower()
    api_key = os.getenv("OPENELECTRICITY_API_KEY", "").strip()
    if mode == "live" and not api_key:
        print("CARBON_MODE=live but OPENELECTRICITY_API_KEY is empty; falling back to mock.")
        mode = "mock"

    interval = int(os.getenv("POLL_INTERVAL_SECONDS", "300"))
    print(f"Starting carbon-ingest in {mode!r} mode (interval={interval}s)")

    while True:
        try:
            poll_once(mode)
        except Exception as exc:  # noqa: BLE001 — keep service alive
            print(f"Poll failed: {exc}", flush=True)
        time.sleep(interval)


if __name__ == "__main__":
    main()
