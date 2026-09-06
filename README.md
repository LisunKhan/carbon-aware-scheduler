# Dynamic Carbon-Aware Resource Scheduler

Local-first prototype for a Master's thesis on **carbon-aware scheduling of cloud analytics jobs** (NEM regions VIC1 / NSW1).

This scaffold is **Milestone 1**: ingest carbon intensity → store in Redis → make RUN / WAIT / SHIFT decisions.

Kubernetes, Spark, ILP, and cloud deploy come later — after you can test the decision engine yourself.

## Architecture (current)

```text
Open Electricity API  ──┐
   (or mock curve)      │
                        ▼
              carbon-ingest (Python)
                        │
                        ▼
                     Redis
                        │
                        ▼
              scheduler (demo_submit)
                 ├── baseline
                 ├── temporal (delay)
                 ├── spatial (region shift)
                 └── carbon_aware (combo)
```

## Prerequisites

- Docker Desktop
- Python 3.11+
- (Optional) Open Electricity API key from https://platform.openelectricity.org.au/

## Quick start (mock mode — no API key)

```powershell
cd C:\Users\islam\Documents\carbon-aware-scheduler
Copy-Item .env.example .env

# Start Redis + carbon ingest
docker compose up --build -d

# Install scheduler deps locally (Windows: use the py launcher)
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r scheduler\requirements.txt

# See current intensities and a scheduling decision
python scheduler\demo_submit.py --job etl-1 --delay 4 --policy carbon_aware --show-intensities
```

Expected output includes something like:

- current `VIC1` / `NSW1` intensities in **gCO₂/kWh**
- action: `RUN_NOW`, `WAIT`, or `SHIFT_REGION`
- reason + estimated emissions

## Run unit tests (no Docker needed)

```powershell
.\.venv\Scripts\Activate.ps1
python scheduler\test_algorithms.py
```

## Switch to live Open Electricity data

1. Put your key in `.env`:
   ```env
   OPENELECTRICITY_API_KEY=your-key-here
   CARBON_MODE=live
   ```
2. Restart ingest:
   ```powershell
   docker compose up --build -d
   ```

If the live API response shape changes, ingest falls back gracefully in mock mode when the key is missing.

## Demo policies

| Policy | Behaviour |
|---|---|
| `baseline` | Always run now in preferred region |
| `temporal` | Wait if intensity > threshold until deadline |
| `spatial` | Pick greener region (VIC1 vs NSW1) |
| `carbon_aware` | Wait when dirty; otherwise consider spatial shift |

Threshold default: `CARBON_THRESHOLD_G_PER_KWH=400` in `.env`.

## Sample workload container

```powershell
docker build -t cas-workload .\workloads
docker run --rm cas-workload
```

## Project layout

```text
carbon-aware-scheduler/
├── carbon-ingest/       # Poll mock or live carbon data → Redis
├── scheduler/           # Decision engine + demo CLI
├── workloads/           # Fake CPU analytics job
├── sim/                 # (next) trace replay experiments
├── k8s/                 # (next) Kind manifests
├── monitoring/          # (next) Prometheus/Grafana
└── docker-compose.yml
```

## Next milestones (after you verify Milestone 1)

1. Kind cluster + Job controller that creates Pods only on `RUN_NOW` / `SHIFT_REGION`
2. Simulation harness over historical carbon traces (thesis results)
3. ILP vs rule-based comparison
4. Cost model (compute vs wait storage)
5. Optional: Spark-on-K8s / real GKE-EKS

## Thesis research hooks already supported

- Trade-off: delay (`WAIT`) vs estimated carbon saved %
- Spatial vs temporal policies as separable algorithms
- Baseline comparator for fair evaluation
