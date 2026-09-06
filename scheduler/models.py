"""Shared job request model for scheduling decisions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone


@dataclass
class JobRequest:
    job_id: str
    max_delay_hours: float = 4.0
    preferred_region: str = "VIC1"
    allow_spatial_shift: bool = True
    estimated_runtime_hours: float = 1.0
    estimated_power_kw: float = 0.5  # rough single-node CPU job
    submitted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def deadline(self) -> datetime:
        return self.submitted_at + timedelta(hours=self.max_delay_hours)


@dataclass
class Decision:
    action: str  # RUN_NOW | WAIT | SHIFT_REGION
    region: str
    reason: str
    current_intensity_g_per_kwh: float
    estimated_emissions_g: float
    alternative_emissions_g: float | None = None
    carbon_saved_pct: float | None = None
