"""Safe translation of connector failures at the MCP trust boundary."""

from collections.abc import Callable
from typing import TypeVar

from .contracts import (
    ConnectorError,
    InvalidRequestError,
    InvalidTimeRangeError,
    TransientProviderError,
    UnknownInstanceError,
    UnknownServiceError,
    UnsupportedCapabilityError,
)

ResultT = TypeVar("ResultT")


def invoke_connector(operation: Callable[[], ResultT]) -> ResultT:
    """Run an operation without exposing connector/provider details over MCP."""
    try:
        return operation()
    except UnknownServiceError as exc:
        raise ValueError("Unknown service.") from exc
    except UnknownInstanceError as exc:
        raise ValueError("Unknown instance.") from exc
    except InvalidTimeRangeError as exc:
        raise ValueError("Invalid time range.") from exc
    except InvalidRequestError as exc:
        raise ValueError("Invalid operation request.") from exc
    except UnsupportedCapabilityError as exc:
        raise ValueError("Requested operational capability is unsupported.") from exc
    except (TransientProviderError, ConnectorError, Exception) as exc:
        raise ValueError("Operational provider unavailable.") from exc