"""Tests for the illustrative (non-production) Kubernetes-style connector.

Proves that `ReadOperationsConnector` / `WriteOperationsConnector` can be
satisfied by a real operational platform's shape (CONN-001 "Hypothetical
Kubernetes implementation" mapping) using a fake client — no real cluster
or Kubernetes SDK dependency required.
"""

from dataclasses import dataclass, field

import pytest

from connectors.contracts import (
    InvalidRequestError,
    ReadOperationsConnector,
    TransientProviderError,
    UnknownInstanceError,
    UnknownServiceError,
    UnsupportedCapabilityError,
    WriteOperationsConnector,
)
from connectors.kubernetes_example import KubernetesReadConnector, KubernetesWriteConnector, PodStatus


@dataclass
class FakePod:
    name: str
    uid: str
    phase: str


@dataclass
class FakeKubernetesClient:
    pods_by_namespace: dict[str, list[FakePod]] = field(default_factory=dict[str, list[FakePod]])
    image_tags: dict[str, str] = field(default_factory=dict[str, str])
    deleted_pods: list[tuple[str, str, str]] = field(default_factory=list[tuple[str, str, str]])

    def list_pods(self, namespace: str) -> list[PodStatus]:
        return list(self.pods_by_namespace.get(namespace, []))

    def get_deployment_image_tag(self, namespace: str, deployment_name: str) -> str:
        return self.image_tags[namespace]

    def delete_pod(self, namespace: str, pod_name: str, pod_uid: str) -> None:
        self.deleted_pods.append((namespace, pod_name, pod_uid))


def _client_with_checkout_api() -> FakeKubernetesClient:
    return FakeKubernetesClient(
        pods_by_namespace={
            "checkout-api": [
                FakePod(name="checkout-api-abc12", uid="uid-abc12", phase="Running"),
                FakePod(name="checkout-api-def34", uid="uid-def34", phase="CrashLoopBackOff"),
            ]
        },
        image_tags={"checkout-api": "1.8.4"},
    )


def test_kubernetes_read_connector_satisfies_read_protocol() -> None:
    connector: ReadOperationsConnector = KubernetesReadConnector(_client_with_checkout_api())
    health = connector.get_service_health("checkout-api")

    assert health["service"] == "checkout-api"
    statuses = {instance["instance"]: instance["healthy"] for instance in health["instances"]}
    assert statuses == {"checkout-api-abc12:uid-abc12": True, "checkout-api-def34:uid-def34": False}


def test_kubernetes_read_connector_maps_deployment_image_tag_to_version() -> None:
    connector = KubernetesReadConnector(_client_with_checkout_api())
    deployment = connector.get_deployment("checkout-api")

    assert deployment["version"] == "1.8.4"
    assert deployment["environment"] == "kubernetes"


def test_kubernetes_read_connector_reports_unknown_service_explicitly() -> None:
    connector = KubernetesReadConnector(FakeKubernetesClient())
    with pytest.raises(UnknownServiceError):
        connector.get_service_health("payments-api")


def test_kubernetes_deployment_for_unknown_service_raises_typed_error() -> None:
    connector = KubernetesReadConnector(FakeKubernetesClient())
    with pytest.raises(UnknownServiceError):
        connector.get_deployment("payments-api")


def test_kubernetes_read_connector_reports_unsupported_capabilities_explicitly() -> None:
    connector = KubernetesReadConnector(_client_with_checkout_api())
    with pytest.raises(UnsupportedCapabilityError):
        connector.get_logs("checkout-api", {"start": "2026-08-18T10:00:00Z", "end": "2026-08-18T10:20:00Z"})
    with pytest.raises(UnsupportedCapabilityError):
        connector.get_known_incidents("checkout-api")


def test_kubernetes_write_connector_satisfies_write_protocol_and_deletes_one_pod() -> None:
    client = _client_with_checkout_api()
    connector: WriteOperationsConnector = KubernetesWriteConnector(client)

    result = connector.restart_instance("action-001", "checkout-api", "checkout-api-def34:uid-def34")

    assert result["status"] == "restarted"
    assert result["instance"] == "checkout-api-def34:uid-def34"
    assert client.deleted_pods == [("checkout-api", "checkout-api-def34", "uid-def34")]


def test_kubernetes_write_connector_rejects_unknown_pod() -> None:
    connector = KubernetesWriteConnector(_client_with_checkout_api())
    with pytest.raises(UnknownInstanceError):
        connector.restart_instance("action-001", "checkout-api", "checkout-api-nope99:uid-nope99")


def test_kubernetes_write_connector_rejects_wildcard_instance() -> None:
    connector = KubernetesWriteConnector(_client_with_checkout_api())
    with pytest.raises(InvalidRequestError, match="UID"):
        connector.restart_instance("action-001", "checkout-api", "*")


def test_kubernetes_write_connector_refuses_a_replaced_pod_with_the_same_name() -> None:
    client = _client_with_checkout_api()
    client.pods_by_namespace["checkout-api"] = [
        FakePod(name="checkout-api-def34", uid="replacement-uid", phase="Running")
    ]
    connector = KubernetesWriteConnector(client)

    with pytest.raises(UnknownInstanceError):
        connector.restart_instance("action-001", "checkout-api", "checkout-api-def34:uid-def34")

    assert client.deleted_pods == []


def test_kubernetes_write_connector_normalizes_delete_time_pod_not_found() -> None:
    class MissingPodClient(FakeKubernetesClient):
        def delete_pod(self, namespace: str, pod_name: str, pod_uid: str) -> None:
            raise KeyError("provider pod not found")

    connector = KubernetesWriteConnector(MissingPodClient(**_client_with_checkout_api().__dict__))
    with pytest.raises(UnknownInstanceError):
        connector.restart_instance("action-001", "checkout-api", "checkout-api-def34:uid-def34")


def test_kubernetes_provider_timeout_is_normalized_to_a_typed_transient_error() -> None:
    class TimeoutClient(FakeKubernetesClient):
        def list_pods(self, namespace: str) -> list[PodStatus]:
            raise TimeoutError("bearer provider-secret")

    connector = KubernetesReadConnector(TimeoutClient())
    with pytest.raises(TransientProviderError):
        connector.get_service_health("checkout-api")
