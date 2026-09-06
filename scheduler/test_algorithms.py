"""Lightweight unit tests for scheduling algorithms (no Redis required)."""

from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scheduler"))

from algorithms import baseline, spatial, temporal  # noqa: E402
from models import JobRequest  # noqa: E402


class TemporalTests(unittest.TestCase):
    def test_waits_when_dirty(self) -> None:
        job = JobRequest(job_id="j1", max_delay_hours=4, preferred_region="VIC1")
        decision = temporal.decide(job, {"VIC1": 650.0}, threshold_g_per_kwh=400.0)
        self.assertEqual(decision.action, "WAIT")

    def test_runs_when_green(self) -> None:
        job = JobRequest(job_id="j2", max_delay_hours=4, preferred_region="VIC1")
        decision = temporal.decide(job, {"VIC1": 250.0}, threshold_g_per_kwh=400.0)
        self.assertEqual(decision.action, "RUN_NOW")

    def test_runs_at_deadline(self) -> None:
        now = datetime.now(timezone.utc)
        job = JobRequest(
            job_id="j3",
            max_delay_hours=1,
            preferred_region="VIC1",
            submitted_at=now - timedelta(hours=2),
        )
        decision = temporal.decide(
            job, {"VIC1": 700.0}, threshold_g_per_kwh=400.0, now=now
        )
        self.assertEqual(decision.action, "RUN_NOW")


class SpatialTests(unittest.TestCase):
    def test_shifts_to_greener_region(self) -> None:
        job = JobRequest(job_id="j4", preferred_region="VIC1", allow_spatial_shift=True)
        decision = spatial.decide(
            job,
            {"VIC1": 700.0, "NSW1": 350.0},
            threshold_g_per_kwh=400.0,
        )
        self.assertEqual(decision.action, "SHIFT_REGION")
        self.assertEqual(decision.region, "NSW1")


class BaselineTests(unittest.TestCase):
    def test_always_runs(self) -> None:
        job = JobRequest(job_id="j5", preferred_region="VIC1")
        decision = baseline.decide(job, {"VIC1": 900.0})
        self.assertEqual(decision.action, "RUN_NOW")


if __name__ == "__main__":
    unittest.main()
