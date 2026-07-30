"""
Rhino bridge connection manager.

Talks to the RhinoMCPBridge plugin running inside Rhino over a local HTTP
listener - never attaches to Rhino "from outside" the way the original
SolidWorks connector did via COM (see packages/rhino-mcp/README.md for why).
"""
from __future__ import annotations

from typing import Any

import httpx

RHINO_DEFAULT_HOST = "127.0.0.1"
RHINO_DEFAULT_PORT = 8765
RHINO_DEFAULT_TIMEOUT = 30.0


class RhinoConnectionError(Exception):
    """Raised when the Rhino bridge plugin cannot be reached or returns an error."""


class RhinoConnection:
    """Sync HTTP client for the RhinoMCPBridge plugin's local listener."""

    def __init__(
        self,
        host: str = RHINO_DEFAULT_HOST,
        port: int = RHINO_DEFAULT_PORT,
        timeout: float = RHINO_DEFAULT_TIMEOUT,
    ) -> None:
        self._base_url = f"http://{host}:{port}"
        self._timeout = timeout

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            resp = httpx.post(f"{self._base_url}{path}", json=payload, timeout=self._timeout)
        except httpx.ConnectError as exc:
            raise RhinoConnectionError(
                "Cannot connect to the Rhino bridge plugin on "
                f"{self._base_url}. Ensure Rhino is running and RhinoMCPBridge.py "
                "has been loaded (see packages/rhino-mcp/README.md)."
            ) from exc
        except httpx.TimeoutException as exc:
            raise RhinoConnectionError(
                f"Request to {path} timed out after {self._timeout}s"
            ) from exc

        try:
            body = resp.json()
        except ValueError as exc:
            raise RhinoConnectionError(
                f"Non-JSON response from Rhino bridge ({resp.status_code}): {resp.text[:200]}"
            ) from exc

        if resp.status_code != 200 or body.get("status") == "error":
            raise RhinoConnectionError(body.get("message", f"Bridge returned {resp.status_code}"))

        return body.get("result", {})

    def diagnostics(self) -> dict[str, Any]:
        return self._post("/diagnostics", {})

    def read(self, query: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._post("/read", {"query": query, "params": params or {}})

    def execute(self, code: str) -> dict[str, Any]:
        return self._post("/execute", {"code": code})

    def update(self, operation: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._post("/update", {"operation": operation, "params": params or {}})


_connection: RhinoConnection | None = None


def get_connection() -> RhinoConnection:
    global _connection
    if _connection is None:
        _connection = RhinoConnection()
    return _connection
