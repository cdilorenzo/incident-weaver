from typing import TypedDict

from fastapi.responses import JSONResponse
from mcp.server.fastmcp import FastMCP

class RestartResult(TypedDict):
    action_id: str
    service: str
    instance: str
    status: str
    result: str

VALID_SERVICE = "checkout-api"
VALID_INSTANCES = {"instance-1", "instance-2", "instance-3"}


def _validate_service(service: str) -> str:
    normalized = service.strip()
    if normalized != VALID_SERVICE:
        raise ValueError(f"Unknown service: {normalized}. Supported service: checkout-api.")
    return normalized


def _validate_instance(instance: str) -> str:
    normalized = instance.strip()
    if not normalized or normalized in {"*", ""}:
        raise ValueError("Instance target is required and cannot be wildcarded.")
    if normalized not in VALID_INSTANCES:
        raise ValueError(f"Unknown instance: {normalized}. Supported instances: instance-1, instance-2, instance-3.")
    return normalized


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
    if not action_id or not action_id.strip():
        raise ValueError("ActionId is required.")

    normalized_service = _validate_service(service)
    normalized_instance = _validate_instance(instance)

    return {
        "action_id": action_id.strip(),
        "service": normalized_service,
        "instance": normalized_instance,
        "status": "restarted",
        "result": "completed",
    }


app = server.streamable_http_app(
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002)
