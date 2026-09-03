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

from collections.abc import Callable
from typing import Protocol, TypeVar

from .contracts import (
    ConnectorError,
    InvalidRequestError,
    TransientProviderError,
    UnknownInstanceError,
    UnknownServiceError,
    UnsupportedCapabilityError,
)
from .models import Deployment, KnownIncidentResult, LogResult, RestartResult, ServiceHealth, TimeRange

ResultT = TypeVar("ResultT")


class PodStatus(Protocol):
    name: str
    uid: str
    phase: str


class KubernetesClient(Protocol):
    """The minimal shape a real Kubernetes SDK wrapper would need to expose."""

    def list_pods(self, namespace: str) -> list[PodStatus]: ...

    def get_deployment_image_tag(self, namespace: str, deployment_name: str) -> str: ...

    def delete_pod(self, namespace: str, pod_name: str, pod_uid: str) -> None: ...


def _provider_call(
    operation: Callable[[], ResultT], service: str, not_found_error: ConnectorError | None = None
) -> ResultT:
    try:
        return operation()
    except KeyError as exc:
        raise not_found_error or UnknownServiceError(f"Unknown service: {service}.") from exc
    except (ConnectionError, TimeoutError) as exc:
        raise TransientProviderError("Kubernetes provider unavailable.") from exc
    except Exception as exc:
        raise TransientProviderError("Kubernetes provider unavailable.") from exc


def _instance_identifier(pod: PodStatus) -> str:
    return f"{pod.name}:{pod.uid}"


class KubernetesReadConnector:
    """Maps a Kubernetes namespace/deployment onto `ReadOperationsConnector`.

    `service` is treated as the namespace/deployment name; `instance` is
    treated as a pod name. Logs and known-incident history have no backing
    source in this illustrative client and are reported as unsupported
    rather than fabricated.
    """

    def __init__(self, client: KubernetesClient) -> None:
        self._client = client

    def _pods_for_service(self, service: str) -> tuple[str, list[PodStatus]]:
        namespace = service.strip()
        if not namespace:
            raise InvalidRequestError("Service is required.")
        pods = _provider_call(lambda: self._client.list_pods(namespace), namespace)
        if not pods:
            raise UnknownServiceError(f"Unknown service: {namespace}. No pods found in namespace.")
        return namespace, pods

    def get_service_health(self, service: str) -> ServiceHealth:
        namespace, pods = self._pods_for_service(service)

        return {
            "service": namespace,
            "instances": [
                {
                    "instance": _instance_identifier(pod),
                    "status": pod.phase,
                    "healthy": pod.phase == "Running",
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
        namespace, _ = self._pods_for_service(service)
        image_tag = _provider_call(
            lambda: self._client.get_deployment_image_tag(namespace, namespace), namespace
        )
        return {
            "service": namespace,
            "version": image_tag,
            "deployed_at": "unknown",
            "status": "deployed",
            "environment": "kubernetes",
            "region": namespace,
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

    def _pod_for_instance(self, service: str, instance: str) -> tuple[str, PodStatus]:
        namespace = service.strip()
        if not namespace:
            raise InvalidRequestError("Service is required.")

        pod_name, separator, pod_uid = instance.strip().partition(":")
        if not pod_name or separator != ":" or not pod_uid:
            raise InvalidRequestError("Instance target must include a Kubernetes pod UID.")

        pods = _provider_call(lambda: self._client.list_pods(namespace), namespace)
        if not pods:
            raise UnknownServiceError(f"Unknown service: {namespace}. No pods found in namespace.")
        for pod in pods:
            if pod.name == pod_name and pod.uid == pod_uid:
                return namespace, pod
        raise UnknownInstanceError(f"Unknown instance: {instance}. Not found in namespace {namespace}.")

    def restart_instance(self, action_id: str, service: str, instance: str) -> RestartResult:
        if not action_id or not action_id.strip():
            raise InvalidRequestError("ActionId is required.")

        namespace, pod = self._pod_for_instance(service, instance)
        _provider_call(
            lambda: self._client.delete_pod(namespace, pod.name, pod.uid),
            namespace,
            UnknownInstanceError(f"Unknown instance: {instance}. Not found in namespace {namespace}."),
        )

        return {
            "action_id": action_id.strip(),
            "service": namespace,
            "instance": _instance_identifier(pod),
            "status": "restarted",
            "result": "completed",
        }
