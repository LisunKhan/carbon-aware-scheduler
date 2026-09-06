"""Estimate job CO2e from intensity × energy."""

from __future__ import annotations

from models import JobRequest


def estimate_emissions_g(job: JobRequest, intensity_g_per_kwh: float) -> float:
    """
    Emissions (gCO2e) ≈ intensity (gCO2/kWh) × energy (kWh)
    energy ≈ power_kw × runtime_hours
    """
    energy_kwh = job.estimated_power_kw * job.estimated_runtime_hours
    return intensity_g_per_kwh * energy_kwh
