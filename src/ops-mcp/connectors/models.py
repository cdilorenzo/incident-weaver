"""Wire-level structured types shared by connector contracts and implementations.

These are the stable shapes that cross the MCP boundary. They are
intentionally plain ``TypedDict``s (matching the existing MCP tool schema
style) rather than vendor-specific objects.
"""

from typing import NotRequired, TypedDict


class InstanceHealth(TypedDict):
    instance: str
    status: str
    healthy: bool
    notes: NotRequired[str]


class ServiceHealth(TypedDict):
    service: str
    instances: list[InstanceHealth]


class Deployment(TypedDict):
    service: str
    version: str
    deployed_at: str
    status: str
    environment: str
    region: str


class LogEntry(TypedDict):
    timestamp: str
    service: str
    instance: str
    severity: str
    event_id: str
    message: str


class TimeRange(TypedDict):
    start: str
    end: str


class LogResult(TypedDict):
    service: str
    time_range: TimeRange
    entries: list[LogEntry]


class KnownIncident(TypedDict):
    incident_id: str
    service: str
    summary: str
    started_at: str
    affected_instances: list[str]
    remediation: str


class KnownIncidentResult(TypedDict):
    service: str
    incidents: list[KnownIncident]


class RestartResult(TypedDict):
    action_id: str
    service: str
    instance: str
    status: str
    result: str
