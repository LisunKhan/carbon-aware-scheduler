"""Spatial shifting: pick the greener eligible region when delay is not allowed/wanted."""

from __future__ import annotations

from emissions import estimate_emissions_g
from models import Decision, JobRequest


def decide(
    job: JobRequest,
    intensities: dict[str, float],
    threshold_g_per_kwh: float,
) -> Decision:
    if not intensities:
        raise ValueError("No regional intensities available")

    preferred = job.preferred_region
    preferred_intensity = intensities.get(preferred)
    if preferred_intensity is None:
        raise ValueError(f"No carbon intensity for preferred region {preferred}")

    baseline_emissions = estimate_emissions_g(job, preferred_intensity)

    if not job.allow_spatial_shift:
        return Decision(
            action="RUN_NOW",
            region=preferred,
            reason="Spatial shifting disabled for this job.",
            current_intensity_g_per_kwh=preferred_intensity,
            estimated_emissions_g=baseline_emissions,
        )

    # Choose lowest intensity region among available
    best_region, best_intensity = min(intensities.items(), key=lambda item: item[1])
    best_emissions = estimate_emissions_g(job, best_intensity)

    if best_region == preferred or best_intensity >= preferred_intensity:
        action = "RUN_NOW"
        reason = (
            f"Preferred region {preferred} is already best "
            f"({preferred_intensity:.1f} gCO2/kWh)."
        )
        return Decision(
            action=action,
            region=preferred,
            reason=reason,
            current_intensity_g_per_kwh=preferred_intensity,
            estimated_emissions_g=baseline_emissions,
        )

    saved = (baseline_emissions - best_emissions) / baseline_emissions * 100.0
    note = ""
    if best_intensity > threshold_g_per_kwh:
        note = f" Still above threshold {threshold_g_per_kwh:.1f}, but greener than preferred."

    return Decision(
        action="SHIFT_REGION",
        region=best_region,
        reason=(
            f"Shift {preferred} ({preferred_intensity:.1f}) → "
            f"{best_region} ({best_intensity:.1f} gCO2/kWh).{note}"
        ),
        current_intensity_g_per_kwh=preferred_intensity,
        estimated_emissions_g=best_emissions,
        alternative_emissions_g=baseline_emissions,
        carbon_saved_pct=round(saved, 2),
    )
