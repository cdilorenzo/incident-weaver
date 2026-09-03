"""Deterministic mock connector: the reference implementation of the contracts.

Demonstrates how the existing IncidentWeaver demo data maps onto the
`ReadOperationsConnector` / `WriteOperationsConnector` protocols (CONN-001
"Existing Mock implementation" mapping). This is the connector wired into
`server.py` and `write_server.py` today.
"""

from typing import TypedDict

from .contracts import UnknownInstanceError, UnknownServiceError
from .models import Deployment, KnownIncidentResult, LogEntry, LogResult, RestartResult, ServiceHealth, TimeRange
from .time_utils import parse_iso8601, validate_time_range


class ServiceData(TypedDict):
    health: ServiceHealth
    deployment: Deployment
    logs: list[LogEntry]
    known_incidents: KnownIncidentResult


OPERATIONAL_DATA: dict[str, ServiceData] = {
    "checkout-api": {
        "health": {
            "service": "checkout-api",
            "instances": [
                {"instance": "instance-1", "status": "healthy", "healthy": True},
                {"instance": "instance-2", "status": "healthy", "healthy": True},
                {
                    "instance": "instance-3",
                    "status": "unhealthy",
                    "healthy": False,
                    "notes": "Dependency initialization failed during startup; startup did not complete successfully.",
                },
            ],
        },
        "deployment": {
            "service": "checkout-api",
            "version": "1.8.4",
            "deployed_at": "2026-08-18T10:03:00Z",
            "status": "deployed",
            "environment": "production",
            "region": "us-east-1",
        },
        "known_incidents": {
            "service": "checkout-api",
            "incidents": [
                {
                    "incident_id": "INC-142",
                    "service": "checkout-api",
                    "summary": "checkout-api deployment 1.7.9 triggered HTTP 500s after a PaymentGatewayClient dependency initialization issue on instance-3.",
                    "started_at": "2026-08-16T09:12:00Z",
                    "affected_instances": ["instance-3"],
                    "remediation": "Restart the affected instance and verify the PaymentGatewayClient dependency initializes before serving traffic.",
                }
            ],
        },
        "logs": [
            {
                "timestamp": "2026-08-18T10:03:15Z",
                "service": "checkout-api",
                "instance": "instance-3",
                "severity": "ERROR",
                "event_id": "checkout-api-1",
                "message": "PaymentGatewayClient initialization failed during dependency startup; startup did not complete successfully.",
            },
            {
                "timestamp": "2026-08-18T10:04:10Z",
                "service": "checkout-api",
                "instance": "instance-3",
                "severity": "ERROR",
                "event_id": "checkout-api-2",
                "message": "Server startup failed: dependency initialization incomplete; service is not ready to serve requests.",
            },
            {
                "timestamp": "2026-08-18T10:05:42Z",
                "service": "checkout-api",
                "instance": "instance-3",
                "severity": "ERROR",
                "event_id": "checkout-api-3",
                "message": "HTTP 500 error observed after deployment 1.8.4 for checkout-api requests routed to instance-3.",
            },
            {
                "timestamp": "2026-08-18T10:12:05Z",
                "service": "checkout-api",
                "instance": "instance-1",
                "severity": "WARN",
                "event_id": "checkout-api-4",
                "message": "Traffic remained healthy on instance-1 while instance-3 reported dependency initialization failures.",
            },
        ],
    }
}

VALID_INSTANCES = {"instance-1", "instance-2", "instance-3"}


def _require_known_service(service: str) -> str:
    normalized = service.strip()
    if normalized not in OPERATIONAL_DATA:
        raise UnknownServiceError(f"Unknown service: {normalized}. Supported service: checkout-api.")
    return normalized


class MockReadConnector:
    """Deterministic in-memory `ReadOperationsConnector` used for local/dev/test."""

    def get_service_health(self, service: str) -> ServiceHealth:
        normalized = _require_known_service(service)
        return OPERATIONAL_DATA[normalized]["health"]

    def get_logs(self, service: str, time_range: TimeRange) -> LogResult:
        normalized = _require_known_service(service)
        start, end = validate_time_range(time_range)

        entries: list[LogEntry] = []
        for entry in OPERATIONAL_DATA[normalized]["logs"]:
            timestamp = parse_iso8601(entry["timestamp"])
            if start <= timestamp < end:
                entries.append(entry)

        return {
            "service": normalized,
            "time_range": {"start": time_range["start"], "end": time_range["end"]},
            "entries": entries,
        }

    def get_deployment(self, service: str) -> Deployment:
        normalized = _require_known_service(service)
        return OPERATIONAL_DATA[normalized]["deployment"]

    def get_known_incidents(self, service: str) -> KnownIncidentResult:
        normalized = _require_known_service(service)
        return OPERATIONAL_DATA[normalized]["known_incidents"]


class MockWriteConnector:
    """Deterministic in-memory `WriteOperationsConnector` used for local/dev/test."""

    def restart_instance(self, action_id: str, service: str, instance: str) -> RestartResult:
        if not action_id or not action_id.strip():
            raise ValueError("ActionId is required.")

        normalized_service = _require_known_service(service)

        normalized_instance = instance.strip()
        if not normalized_instance or normalized_instance == "*":
            raise ValueError("Instance target is required and cannot be wildcarded.")
        if normalized_instance not in VALID_INSTANCES:
            raise UnknownInstanceError(
                f"Unknown instance: {normalized_instance}. Supported instances: instance-1, instance-2, instance-3."
            )

        return {
            "action_id": action_id.strip(),
            "service": normalized_service,
            "instance": normalized_instance,
            "status": "restarted",
            "result": "completed",
        }
