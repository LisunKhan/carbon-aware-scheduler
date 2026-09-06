# Dynamic Carbon-Aware Resource Scheduler

Local-first prototype for a Master's thesis on **carbon-aware scheduling of cloud analytics jobs** (NEM regions VIC1 / NSW1).

**Milestone 1** — carbon ingest + decision engine  
**Milestone 2** — Kind cluster + Redis job queue + Job controller (current)

## Architecture

```text
submit_job.py ──► Redis queue (jobs:pending)
                        │
              carbon-ingest (mock / Open Electricity)
                        │
                        ▼
              controller.py (decision engine)
                 ├── WAIT  → requeue
                 └── RUN_NOW / SHIFT_REGION
                        │
                        ▼
              Kubernetes Job (Kind)
                 nodeSelector: cas.nem/region=VIC1|NSW1
```

## Prerequisites

- Docker Desktop (running)
- Python 3.11+ (`py -3` on Windows)
- `kubectl` (you already have this)
- Kind (installed automatically by `scripts/setup-kind.ps1`)

## Milestone 1 — decision engine

```powershell
cd C:\Users\islam\Documents\carbon-aware-scheduler
Copy-Item .env.example .env -ErrorAction SilentlyContinue
docker compose up --build -d

py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r scheduler\requirements.txt

.\.venv\Scripts\python.exe scheduler\test_algorithms.py
.\.venv\Scripts\python.exe scheduler\demo_submit.py --job etl-1 --delay 4 --policy carbon_aware --show-intensities
```

## Milestone 2 — Kind + Job controller

### 1. Create cluster and load workload image

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup-kind.ps1
```

### 2. Ensure Redis + ingest are running

```powershell
docker compose up -d
```

### 3. Submit a job and run the controller once

```powershell
.\.venv\Scripts\python.exe -m pip install -r scheduler\requirements.txt

# Force an immediate schedule (delay=0) so you see a Pod quickly
.\.venv\Scripts\python.exe scheduler\submit_job.py --job demo-1 --delay 0 --region VIC1 --seconds 15

# Dry-run first (no Pods)
.\.venv\Scripts\python.exe scheduler\controller.py --once --dry-run

# Real schedule into Kind
.\.venv\Scripts\python.exe scheduler\submit_job.py --job demo-2 --delay 0 --region VIC1 --seconds 15
.\.venv\Scripts\python.exe scheduler\controller.py --once
```

### 4. Verify the Pod ran on a region node

```powershell
kubectl get jobs,pods -n carbon-aware -o wide
kubectl get nodes -L cas.nem/region
kubectl logs -n carbon-aware -l app=carbon-aware-workload --tail=50
```

### Continuous controller

```powershell
.\.venv\Scripts\python.exe scheduler\controller.py
```

Leave it running, then submit jobs from another terminal.

### Demo WAIT behaviour

Lower the threshold so current mock intensity looks “dirty”:

```powershell
# In .env set: CARBON_THRESHOLD_G_PER_KWH=200
# Restart is not required for the controller (it reads .env on start)
.\.venv\Scripts\python.exe scheduler\submit_job.py --job wait-1 --delay 4 --seconds 15
.\.venv\Scripts\python.exe scheduler\controller.py --once --dry-run --wait-seconds 5
```

You should see `action: WAIT` and a requeue message.

## Policies

| Policy | Behaviour |
|---|---|
| `baseline` | Always run now in preferred region |
| `temporal` | Wait if intensity > threshold until deadline |
| `spatial` | Pick greener region (VIC1 vs NSW1) |
| `carbon_aware` | Wait when dirty; otherwise consider spatial shift |

## Project layout

```text
carbon-aware-scheduler/
├── carbon-ingest/       # Poll mock or live carbon data → Redis
├── scheduler/           # Decision engine, queue, controller
├── workloads/           # Fake CPU analytics Job image
├── k8s/                 # Kind config + namespace
├── scripts/             # setup-kind.ps1
├── sim/                 # (next) trace replay experiments
├── monitoring/          # (next) Prometheus/Grafana
└── docker-compose.yml
```

## Next milestones

1. Simulation harness over historical carbon traces (thesis results)
2. ILP vs rule-based comparison
3. Cost model (compute vs wait storage)
4. Optional: Spark-on-K8s / real GKE-EKS
