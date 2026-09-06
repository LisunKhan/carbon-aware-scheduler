"""Baseline: always run immediately in preferred region."""

from __future__ import annotations

from emissions import estimate_emissions_g
from models import Decision, JobRequest


def decide(job: JobRequest, intensities: dict[str, float]) -> Decision:
    region = job.preferred_region
    intensity = intensities.get(region)
    if intensity is None:
        raise ValueError(f"No carbon intensity for preferred region {region}")

    emissions = estimate_emissions_g(job, intensity)
    return Decision(
        action="RUN_NOW",
        region=region,
        reason="Baseline scheduler ignores carbon intensity.",
        current_intensity_g_per_kwh=intensity,
        estimated_emissions_g=emissions,
    )
