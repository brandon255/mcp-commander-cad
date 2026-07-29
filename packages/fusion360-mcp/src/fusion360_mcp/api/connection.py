"""Fusion 360 REST API connection manager.

Communicates with Fusion 360's local HTTP server for external automation.
Fusion 360 exposes a REST API on localhost (default port 8080) that accepts
JSON command payloads and returns structured results.

The API follows a simple RPC-style pattern:
    POST /api/command  {"command": "...", "params": {...}}
    -> {"status": "ok|error", "result": ..., "message": "..."}
"""

from __future__ import annotations

import json
import logging
from enum import Enum
from typing import Any

import httpx

logger = logging.getLogger(__name__)

FUSION_DEFAULT_HOST = "localhost"
FUSION_DEFAULT_PORT = 8080
FUSION_DEFAULT_TIMEOUT = 30.0
FUSION_API_BASE = "/api"


class DocumentType(str, Enum):
    """Supported Fusion 360 document types for creation."""

    PART = "part"
    ASSEMBLY = "assembly"
    DRAWING = "drawing"
    SHEET_METAL = "sheet_metal"


class FusionConnectionError(Exception):
    """Raised when Fusion 360 cannot be reached or returns an error."""


class FusionConnection:
    """Async connection manager for the Fusion 360 REST API.

    Manages an ``httpx.AsyncClient`` session and provides typed methods
    that translate high-level operations into the JSON payloads the
    Fusion 360 local API expects.

    Typical usage::

        conn = FusionConnection()
        await conn.connect()
        doc = await conn.get_active_document()
        await conn.disconnect()
    """

    def __init__(
        self,
        host: str = FUSION_DEFAULT_HOST,
        port: int = FUSION_DEFAULT_PORT,
        timeout: float = FUSION_DEFAULT_TIMEOUT,
        api_key: str | None = None,
    ) -> None:
        self._host = host
        self._port = port
        self._timeout = timeout
        self._api_key = api_key
        self._base_url = f"http://{host}:{port}{FUSION_API_BASE}"
        self._client: httpx.AsyncClient | None = None
        self._connected = False

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Establish a connection to Fusion 360's REST API endpoint.

        Sends a lightweight ping to verify the API is reachable.

        Raises:
            FusionConnectionError: If Fusion 360 is not running or rejects
                the connection.
        """
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(self._timeout),
            headers=headers,
        )

        try:
            response = await self._client.get("/ping")
            response.raise_for_status()
            body = response.json()
            if body.get("status") != "ok":
                raise FusionConnectionError(
                    f"Fusion 360 API returned unexpected ping response: {body}"
                )
            self._connected = True
            logger.info("Connected to Fusion 360 API at %s", self._base_url)
        except httpx.ConnectError as exc:
            self._connected = False
            raise FusionConnectionError(
                "Cannot connect to Fusion 360. Ensure Fusion 360 is running and "
                "the REST API server is enabled in the Scripts and Add-Ins panel."
            ) from exc
        except httpx.HTTPStatusError as exc:
            self._connected = False
            raise FusionConnectionError(
                f"Fusion 360 API HTTP error: {exc.response.status_code} "
                f"{exc.response.text}"
            ) from exc

    async def disconnect(self) -> None:
        """Close the underlying HTTP client and mark the connection as closed."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
        self._connected = False
        logger.info("Disconnected from Fusion 360 API")

    def is_connected(self) -> bool:
        """Return ``True`` if the connection is currently active."""
        return self._connected

    # ------------------------------------------------------------------
    # Low-level command interface
    # ------------------------------------------------------------------

    async def send_command(self, command: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Send an arbitrary API command to Fusion 360.

        Args:
            command: The command name accepted by the Fusion 360 REST API
                (e.g. ``"sketch_create"``, ``"extrude_profile"``).
            params: Optional dictionary of parameters forwarded to the command.

        Returns:
            The parsed JSON ``result`` field from the API response.

        Raises:
            FusionConnectionError: If the connection is closed, the request
                times out, or Fusion 360 returns an error status.
        """
        if not self._connected or self._client is None:
            raise FusionConnectionError("Not connected to Fusion 360. Call connect() first.")

        payload: dict[str, Any] = {"command": command, "params": params or {}}

        try:
            response = await self._client.post("/command", json=payload)
            response.raise_for_status()
            body = response.json()
        except httpx.TimeoutException as exc:
            raise FusionConnectionError(
                f"Command '{command}' timed out after {self._timeout}s"
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise FusionConnectionError(
                f"Command '{command}' HTTP error: {exc.response.status_code} "
                f"{exc.response.text}"
            ) from exc
        except httpx.RequestError as exc:
            raise FusionConnectionError(
                f"Command '{command}' request failed: {exc}"
            ) from exc

        if body.get("status") == "error":
            raise FusionConnectionError(
                body.get("message", f"Unknown error from command '{command}'")
            )

        return body.get("result", {})

    # ------------------------------------------------------------------
    # Document management
    # ------------------------------------------------------------------

    async def get_active_document(self) -> dict[str, Any]:
        """Retrieve metadata for the currently active Fusion 360 document.

        Returns:
            A dict with keys such as ``name``, ``path``, ``document_type``,
            ``is_dirty``, and ``units``.
        """
        return await self.send_command("document_get_active")

    async def list_documents(self) -> list[dict[str, Any]]:
        """List all documents currently open in Fusion 360.

        Returns:
            A list of dicts, each representing an open document.
        """
        result = await self.send_command("document_list")
        return result.get("documents", [])

    async def open_document(self, filepath: str) -> dict[str, Any]:
        """Open a Fusion 360 document (.f3d, .step, .iges, etc.).

        Args:
            filepath: Absolute path to the file on the local filesystem.

        Returns:
            A dict with ``name``, ``document_type``, and other metadata.
        """
        return await self.send_command("document_open", {"filepath": filepath})

    async def save_document(self, filepath: str | None = None) -> dict[str, Any]:
        """Save the active document.

        Args:
            filepath: If provided, perform a Save-As to this path. Otherwise,
                save in-place.

        Returns:
            A dict with ``saved_path`` and ``success``.
        """
        params: dict[str, Any] = {}
        if filepath is not None:
            params["filepath"] = filepath
        return await self.send_command("document_save", params)

    async def create_document(self, doc_type: str | DocumentType = DocumentType.PART) -> dict[str, Any]:
        """Create a new Fusion 360 document.

        Args:
            doc_type: One of ``"part"``, ``"assembly"``, ``"drawing"``,
                or ``"sheet_metal"``.

        Returns:
            A dict with the new document's ``name`` and ``document_type``.
        """
        if isinstance(doc_type, DocumentType):
            doc_type = doc_type.value
        return await self.send_command("document_create", {"doc_type": doc_type})

    # ------------------------------------------------------------------
    # Singleton convenience
    # ------------------------------------------------------------------

    _instance: FusionConnection | None = None

    @classmethod
    def get_global(cls) -> FusionConnection:
        """Return a module-level singleton connection.

        The caller is still responsible for calling ``connect()`` and
        ``disconnect()`` at the appropriate lifecycle points.
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
