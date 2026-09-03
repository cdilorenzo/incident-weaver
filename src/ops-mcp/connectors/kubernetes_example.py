"""Illustrative (non-production) Kubernetes-style connector.

Demonstrates that `ReadOperationsConnector` / `WriteOperationsConnector`
can be satisfied by a real operational platform without changing the
contracts or the MCP tool layer (CONN-001 "Hypothetical Kubernetes
implementation" mapping).

This module is intentionally NOT wired into `server.py` / `write_server.py`
and does not depend on a real Kubernetes client library or cluster. It
depends only on a small `KubernetesClient` protocol, so it can be exercised
deterministically in tests. A production implementation would adapt
`kubernetes.client` (the official Python SDK) behind that same protocol;
only this module would change — never the contracts or the MCP tool layer.
"""

from typing import Protocol

from .contracts import UnknownInstanceError, UnknownServiceError, UnsupportedCapabilityError
from .models import Deployment, KnownIncidentResult, LogResult, RestartResult, ServiceHealth, TimeRange


class PodStatus(Protocol):
    name: str
    phase: str  # e.g. "Running", "CrashLoopBackOff", "Pending"


class KubernetesClient(Protocol):
    """The minimal shape a real Kubernetes SDK wrapper would need to expose."""

    def list_pods(self, namespace: str) -> list[PodStatus]: ...

    def get_deployment_image_tag(self, namespace: str, deployment_name: str) -> str: ...

    def delete_pod(self, namespace: str, pod_name: str) -> None: ...


class KubernetesReadConnector:
    """Maps a Kubernetes namespace/deployment onto `ReadOperationsConnector`.

    `service` is treated as the namespace/deployment name; `instance` is
    treated as a pod name. Logs and known-incident history have no backing
    source in this illustrative client and are reported as unsupported
    rather than fabricated.
    """

    def __init__(self, client: KubernetesClient) -> None:
        self._client = client

    def get_service_health(self, service: str) -> ServiceHealth:
        namespace = service.strip()
        pods = self._client.list_pods(namespace)
        if not pods:
            raise UnknownServiceError(f"Unknown service: {namespace}. No pods found in namespace.")

        return {
            "service": namespace,
            "instances": [
                {
                    "instance": pod.name,
                    "status": pod.phase,
                    "healthy": pod.phase == "Running",
                    "vendor_metadata": {"kubernetes_phase": pod.phase},
                }
                for pod in pods
            ],
        }

    def get_logs(self, service: str, time_range: TimeRange) -> LogResult:
        raise UnsupportedCapabilityError(
            "This illustrative Kubernetes connector does not implement log retrieval; "
            "a production implementation would query a log backend (e.g. Loki/Grafana)."
        )

    def get_deployment(self, service: str) -> Deployment:
        namespace = service.strip()
        image_tag = self._client.get_deployment_image_tag(namespace, namespace)
        return {
            "service": namespace,
            "version": image_tag,
            "deployed_at": "unknown",
            "status": "deployed",
            "environment": "kubernetes",
            "region": namespace,
            "vendor_metadata": {"namespace": namespace},
        }

    def get_known_incidents(self, service: str) -> KnownIncidentResult:
        raise UnsupportedCapabilityError(
            "This illustrative Kubernetes connector has no incident-history source; "
            "a production implementation would query an ITSM system (e.g. ServiceNow)."
        )


class KubernetesWriteConnector:
    """Maps `restart_instance` onto deleting one explicitly identified pod.

    Kubernetes recreates a deleted pod under a Deployment/ReplicaSet, which
    is the natural mapping for "restart exactly one explicitly identified
    instance" (this issue's write scope) without granting broader authority
    such as scaling or rolling the whole deployment.
    """

    def __init__(self, client: KubernetesClient) -> None:
        self._client = client

    def restart_instance(self, action_id: str, service: str, instance: str) -> RestartResult:
        if not action_id or not action_id.strip():
            raise ValueError("ActionId is required.")

        namespace = service.strip()
        pod_name = instance.strip()
        if not pod_name or pod_name == "*":
            raise ValueError("Instance target is required and cannot be wildcarded.")

        known_pods = {pod.name for pod in self._client.list_pods(namespace)}
        if pod_name not in known_pods:
            raise UnknownInstanceError(f"Unknown instance: {pod_name}. Not found in namespace {namespace}.")

        self._client.delete_pod(namespace, pod_name)

        return {
            "action_id": action_id.strip(),
            "service": namespace,
            "instance": pod_name,
            "status": "restarted",
            "result": "completed",
        }
