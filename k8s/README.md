# Kubernetes (Milestone 2)

## What this folder does

Simulates two Australian cloud regions inside one Kind cluster:

| Node role | Label | Meaning |
|---|---|---|
| worker | `cas.nem/region=VIC1` | Victoria (Melbourne-style AZ) |
| worker | `cas.nem/region=NSW1` | NSW (Sydney-style AZ) |

The Job controller creates `batch/v1` Jobs with a `nodeSelector` so pods land on the greener region.

## Setup

From the repo root (Docker Desktop must be running):

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup-kind.ps1
```

## Useful commands

```powershell
kubectl get nodes -L cas.nem/region
kubectl get jobs,pods -n carbon-aware -o wide
kubectl logs -n carbon-aware -l app=carbon-aware-workload --tail=50
```

## Tear down

```powershell
.\tools\kind.exe delete cluster --name carbon-aware
# or: kind delete cluster --name carbon-aware
```
