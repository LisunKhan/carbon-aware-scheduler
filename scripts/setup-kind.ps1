#Requires -Version 5.1
<#
.SYNOPSIS
  Install Kind (if missing), create the carbon-aware cluster, load the workload image.
#>
$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Tools = Join-Path $Root "tools"
$KindExe = Join-Path $Tools "kind.exe"

Write-Host "==> Repo: $Root"

function Get-KindCommand {
    $existing = Get-Command kind -ErrorAction SilentlyContinue
    if ($existing) { return $existing.Source }

    New-Item -ItemType Directory -Force -Path $Tools | Out-Null
    if (-not (Test-Path $KindExe)) {
        Write-Host "Downloading kind.exe to $KindExe ..."
        $url = "https://kind.sigs.k8s.io/dl/v0.27.0/kind-windows-amd64"
        Invoke-WebRequest -Uri $url -OutFile $KindExe -UseBasicParsing
    }
    return $KindExe
}

$Kind = Get-KindCommand
Write-Host "Using kind: $Kind"
& $Kind version

$clusterName = "carbon-aware"
$clusters = cmd /c "`"$Kind`" get clusters 2>nul"
$hasCluster = $false
if ($clusters) {
    foreach ($line in ($clusters -split "`r?`n")) {
        if ($line.Trim() -eq $clusterName) { $hasCluster = $true }
    }
}
if ($hasCluster) {
    Write-Host "Kind cluster '$clusterName' already exists"
} else {
    Write-Host "Creating Kind cluster '$clusterName' ..."
    & $Kind create cluster --config (Join-Path $Root "k8s\kind-config.yaml")
    if ($LASTEXITCODE -ne 0) { throw "kind create cluster failed" }
}

Write-Host "Applying namespace manifests ..."
kubectl apply -f (Join-Path $Root "k8s\namespace.yaml")

Write-Host "Building workload image ..."
docker build -t cas-workload:latest (Join-Path $Root "workloads")

Write-Host "Loading image into Kind ..."
& $Kind load docker-image cas-workload:latest --name $clusterName

Write-Host "Label check (region workers):"
kubectl get nodes -L cas.nem/region

Write-Host ""
Write-Host "Milestone 2 cluster is ready."
Write-Host "Next:"
Write-Host "  docker compose up -d"
Write-Host "  .\.venv\Scripts\python.exe -m pip install -r scheduler\requirements.txt"
Write-Host "  .\.venv\Scripts\python.exe scheduler\submit_job.py --job demo-1 --delay 4 --seconds 15"
Write-Host "  .\.venv\Scripts\python.exe scheduler\controller.py --once"
