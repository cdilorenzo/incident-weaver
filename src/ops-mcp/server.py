from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi.responses import JSONResponse
from mcp.server.mcpserver.server import MCPServer

FastMCP = MCPServer


def parse_iso8601(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    try:
        timestamp = datetime.fromisoformat(normalized)
    except ValueError as exc:  # pragma: no cover - defensive validation for bad input
        raise ValueError(f"Invalid timestamp: {value}") from exc
    if timestamp.tzinfo is None:
        raise ValueError(f"Timestamp must include timezone information: {value}")
    return timestamp.astimezone(timezone.utc)


def validate_time_range(start: str, end: str) -> tuple[datetime, datetime]:
    start_dt = parse_iso8601(start)
    end_dt = parse_iso8601(end)
    if start_dt >= end_dt:
        raise ValueError("Invalid time range: start must be earlier than end.")
    return start_dt, end_dt


OPERATIONAL_DATA: dict[str, dict[str, Any]] = {
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


server = FastMCP(
    name="incidentweaver-ops-read",
    instructions="Read-only operational evidence tools for IncidentWeaver.",
)


@server.custom_route("/health", methods=["GET"])
async def health_route(request: Any) -> JSONResponse:
    return JSONResponse({"status": "healthy", "service": "operations-mcp", "read_only": True})


@server.tool(description="Return deterministic instance-level health for the requested service.")
def get_service_health(service: str) -> dict[str, Any]:
    normalized = service.strip()
    if normalized not in OPERATIONAL_DATA:
        raise ValueError(f"Unknown service: {normalized}. Supported service: checkout-api.")

    return OPERATIONAL_DATA[normalized]["health"]


@server.tool(description="Return deterministic log entries for a service within the provided time range.")
def get_logs(service: str, time_range: dict[str, str]) -> dict[str, Any]:
    normalized = service.strip()
    if normalized not in OPERATIONAL_DATA:
        raise ValueError(f"Unknown service: {normalized}. Supported service: checkout-api.")

    if "start" not in time_range or "end" not in time_range:
        raise ValueError("Invalid time range: time_range must contain 'start' and 'end'.")

    start, end = validate_time_range(str(time_range["start"]), str(time_range["end"]))

    entries: list[dict[str, Any]] = []
    for entry in OPERATIONAL_DATA[normalized]["logs"]:
        timestamp = parse_iso8601(entry["timestamp"])
        if start <= timestamp < end:
            entries.append(entry)

    return {
        "service": normalized,
        "time_range": {"start": time_range["start"], "end": time_range["end"]},
        "entries": entries,
    }


@server.tool(description="Return deterministic deployment metadata for the requested service.")
def get_deployment(service: str) -> dict[str, Any]:
    normalized = service.strip()
    if normalized not in OPERATIONAL_DATA:
        raise ValueError(f"Unknown service: {normalized}. Supported service: checkout-api.")

    return OPERATIONAL_DATA[normalized]["deployment"]


@server.tool(description="Return structured historical incidents for the requested service.")
def get_known_incidents(service: str) -> dict[str, Any]:
    normalized = service.strip()
    if normalized not in OPERATIONAL_DATA:
        raise ValueError(f"Unknown service: {normalized}. Supported service: checkout-api.")

    return OPERATIONAL_DATA[normalized]["known_incidents"]


app = server.streamable_http_app(
    streamable_http_path="/mcp",
    json_response=True,
    host="0.0.0.0",
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
