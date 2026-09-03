from fastapi.responses import JSONResponse
from mcp.server.fastmcp import FastMCP

from connectors.config import select_read_connector
from connectors.contracts import ReadOperationsConnector
from connectors.models import Deployment, KnownIncidentResult, LogResult, ServiceHealth, TimeRange

connector: ReadOperationsConnector = select_read_connector()

server = FastMCP(
    name="incidentweaver-ops-read",
    instructions="Read-only operational evidence tools for IncidentWeaver.",
    host="0.0.0.0",
    port=8001,
    streamable_http_path="/mcp",
    json_response=True,
)


@server.custom_route("/health", methods=["GET"])
async def health_route(request: object) -> JSONResponse:
    return JSONResponse({"status": "healthy", "service": "operations-mcp", "read_only": True})


@server.tool(description="Return deterministic instance-level health for the requested service.")
def get_service_health(service: str) -> ServiceHealth:
    return connector.get_service_health(service)


@server.tool(description="Return deterministic log entries for a service within the provided time range.")
def get_logs(service: str, time_range: TimeRange) -> LogResult:
    return connector.get_logs(service, time_range)


@server.tool(description="Return deterministic deployment metadata for the requested service.")
def get_deployment(service: str) -> Deployment:
    return connector.get_deployment(service)


@server.tool(description="Return structured historical incidents for the requested service.")
def get_known_incidents(service: str) -> KnownIncidentResult:
    return connector.get_known_incidents(service)


app = server.streamable_http_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
