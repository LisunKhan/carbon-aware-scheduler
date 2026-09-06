"""Create Kubernetes Jobs pinned to a simulated NEM region node."""

from __future__ import annotations

import re
from typing import Any

from kubernetes import client, config
from kubernetes.client.exceptions import ApiException


REGION_LABEL = "cas.nem/region"
NAMESPACE = "carbon-aware"
DEFAULT_IMAGE = "cas-workload:latest"


def load_kube() -> client.BatchV1Api:
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()
    return client.BatchV1Api()


def _safe_name(job_id: str) -> str:
    name = re.sub(r"[^a-z0-9-]", "-", job_id.lower()).strip("-")
    if not name:
        name = "job"
    return name[:50]


def build_job_manifest(
    job_id: str,
    region: str,
    *,
    image: str = DEFAULT_IMAGE,
    run_seconds: int = 20,
    decision: dict[str, Any] | None = None,
) -> client.V1Job:
    decision = decision or {}
    labels = {
        "app": "carbon-aware-workload",
        "cas.job-id": _safe_name(job_id),
        REGION_LABEL: region,
    }
    env = [
        client.V1EnvVar(name="JOB_ID", value=job_id),
        client.V1EnvVar(name="CAS_REGION", value=region),
        client.V1EnvVar(name="RUN_SECONDS", value=str(run_seconds)),
    ]
    container = client.V1Container(
        name="workload",
        image=image,
        image_pull_policy="IfNotPresent",
        env=env,
        resources=client.V1ResourceRequirements(
            requests={"cpu": "100m", "memory": "64Mi"},
            limits={"cpu": "500m", "memory": "256Mi"},
        ),
    )
    pod_spec = client.V1PodSpec(
        restart_policy="Never",
        containers=[container],
        node_selector={REGION_LABEL: region},
    )
    template = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(labels=labels),
        spec=pod_spec,
    )
    annotations = {
        "cas.decision/action": str(decision.get("action", "")),
        "cas.decision/reason": str(decision.get("reason", ""))[:200],
        "cas.decision/intensity": str(decision.get("current_intensity_g_per_kwh", "")),
    }
    return client.V1Job(
        api_version="batch/v1",
        kind="Job",
        metadata=client.V1ObjectMeta(
            name=f"cas-{_safe_name(job_id)}",
            namespace=NAMESPACE,
            labels=labels,
            annotations=annotations,
        ),
        spec=client.V1JobSpec(
            backoff_limit=1,
            ttl_seconds_after_finished=600,
            template=template,
        ),
    )


def create_region_job(
    batch: client.BatchV1Api,
    job_id: str,
    region: str,
    *,
    image: str = DEFAULT_IMAGE,
    run_seconds: int = 20,
    decision: dict[str, Any] | None = None,
    dry_run: bool = False,
) -> str:
    manifest = build_job_manifest(
        job_id,
        region,
        image=image,
        run_seconds=run_seconds,
        decision=decision,
    )
    if dry_run:
        return manifest.metadata.name

    try:
        created = batch.create_namespaced_job(namespace=NAMESPACE, body=manifest)
    except ApiException as exc:
        if exc.status == 409:
            # Already created — treat as success for idempotency
            return manifest.metadata.name
        raise
    return created.metadata.name
