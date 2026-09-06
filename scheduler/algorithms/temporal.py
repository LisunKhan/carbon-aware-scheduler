"""Temporal shifting: delay until intensity is below threshold or deadline hit."""

from __future__ import annotations

from datetime import datetime, timezone

from emissions import estimate_emissions_g
from models import Decision, JobRequest


def decide(
    job: JobRequest,
    intensities: dict[str, float],
    threshold_g_per_kwh: float,
    now: datetime | None = None,
) -> Decision:
    now = now or datetime.now(timezone.utc)
    region = job.preferred_region
    intensity = intensities.get(region)
    if intensity is None:
        raise ValueError(f"No carbon intensity for preferred region {region}")

    emissions_now = estimate_emissions_g(job, intensity)
    past_deadline = now >= job.deadline

    if intensity <= threshold_g_per_kwh or past_deadline:
        reason = (
            f"Intensity {intensity:.1f} <= threshold {threshold_g_per_kwh:.1f}."
            if intensity <= threshold_g_per_kwh
            else f"Deadline reached ({job.deadline.isoformat()}); must run."
        )
        return Decision(
            action="RUN_NOW",
            region=region,
            reason=reason,
            current_intensity_g_per_kwh=intensity,
            estimated_emissions_g=emissions_now,
        )

    return Decision(
        action="WAIT",
        region=region,
        reason=(
            f"Intensity {intensity:.1f} > threshold {threshold_g_per_kwh:.1f}; "
            f"delay until greener window or deadline {job.deadline.isoformat()}."
        ),
        current_intensity_g_per_kwh=intensity,
        estimated_emissions_g=emissions_now,
        alternative_emissions_g=estimate_emissions_g(job, threshold_g_per_kwh),
        carbon_saved_pct=_saved_pct(emissions_now, estimate_emissions_g(job, threshold_g_per_kwh)),
    )


def _saved_pct(baseline: float, greener: float) -> float:
    if baseline <= 0:
        return 0.0
    return round((baseline - greener) / baseline * 100.0, 2)
