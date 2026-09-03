from fastapi.responses import JSONResponse
from mcp.server.fastmcp import FastMCP

from connectors.boundary import invoke_connector
from connectors.config import select_write_connector
from connectors.contracts import WriteOperationsConnector
from connectors.models import RestartResult

connector: WriteOperationsConnector = select_write_connector()

server = FastMCP(
    name="incidentweaver-ops-write",
    instructions="Write-only operational capability for privileged restart of a known instance.",
    host="0.0.0.0",
    port=8002,
    streamable_http_path="/mcp",
    json_response=True,
)


@server.custom_route("/health", methods=["GET"])
async def health_route(request: object) -> JSONResponse:
    return JSONResponse({"status": "healthy", "service": "operations-mcp-write", "write_only": True})


@server.tool(description="Restart a single known instance of the checkout-api service.")
def restart_instance(action_id: str, service: str, instance: str) -> RestartResult:
    return invoke_connector(lambda: connector.restart_instance(action_id, service, instance))


app = server.streamable_http_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002)
