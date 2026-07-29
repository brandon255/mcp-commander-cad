"""Onshape REST API connection manager.

Communicates with Onshape's cloud REST API (https://cad.onshape.com/api/v6/)
using Basic authentication with an API key pair (access key + secret key).
All requests are made over HTTPS via ``httpx.AsyncClient``.

The API follows a RESTful resource pattern:
    GET    /api/v6/documents                     — list documents
    POST   /api/v6/documents                     — create document
    GET    /api/v6/documents/{did}/workspaces     — list workspaces
    GET    /api/v6/documents/{did}/elements       — list elements
    ...etc.

Resources are identified by:
    - document ID (did)
    - workspace ID (wid)
    - element ID (eid)
    - part ID (pid)
"""

from __future__ import annotations

import base64
import json
import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

ONSHAPE_DEFAULT_BASE_URL = "https://cad.onshape.com/api/v6"
ONSHAPE_DEFAULT_TIMEOUT = 60.0

# Environment variable names for API keys
_ONSHAPE_ACCESS_KEY = "ONSHAPE_ACCESS_KEY"
_ONSHAPE_SECRET_KEY = "ONSHAPE_SECRET_KEY"


class OnshapeConnectionError(Exception):
    """Raised when Onshape API cannot be reached or returns an error."""


class OnshapeConnection:
    """Async connection manager for the Onshape REST API.

    Manages an ``httpx.AsyncClient`` session authenticated with Basic auth
    (API key pair) and provides typed methods that map to Onshape's RESTful
    endpoints grouped by resource type.

    Typical usage::

        conn = OnshapeConnection(access_key="...", secret_key="...")
        await conn.connect()
        docs = await conn.list_documents()
        await conn.disconnect()

    The class also supports a singleton pattern via ``get_global()`` so
    tool modules can share a single connection instance.
    """

    def __init__(
        self,
        access_key: str = "",
        secret_key: str = "",
        base_url: str = ONSHAPE_DEFAULT_BASE_URL,
        timeout: float = ONSHAPE_DEFAULT_TIMEOUT,
    ) -> None:
        self._access_key = access_key or os.environ.get(_ONSHAPE_ACCESS_KEY, "")
        self._secret_key = secret_key or os.environ.get(_ONSHAPE_SECRET_KEY, "")
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None
        self._connected = False

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    def _build_auth_header(self) -> str:
        """Build Basic auth header from API key pair."""
        credentials = f"{self._access_key}:{self._secret_key}"
        encoded = base64.b64encode(credentials.encode("utf-8")).decode("ascii")
        return f"Basic {encoded}"

    async def connect(self) -> None:
        """Establish a connection to Onshape's REST API.

        Creates an ``httpx.AsyncClient`` with auth headers and verifies
        credentials by calling ``GET /api/v6/users/me``.

        Raises:
            OnshapeConnectionError: If credentials are missing or invalid,
                or the API is unreachable.
        """
        if not self._access_key or not self._secret_key:
            raise OnshapeConnectionError(
                f"Onshape API key not configured. Set {_ONSHAPE_ACCESS_KEY} "
                f"and {_ONSHAPE_SECRET_KEY} environment variables, or pass "
                "access_key and secret_key to the constructor."
            )

        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(self._timeout),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": self._build_auth_header(),
            },
        )

        try:
            response = await self._client.get("/users/me")
            response.raise_for_status()
            body = response.json()
            logger.info(
                "Connected to Onshape API as user: %s", body.get("name", "unknown")
            )
            self._connected = True
        except httpx.ConnectError as exc:
            self._connected = False
            raise OnshapeConnectionError(
                "Cannot connect to Onshape API. Check network connectivity."
            ) from exc
        except httpx.HTTPStatusError as exc:
            self._connected = False
            raise OnshapeConnectionError(
                f"Onshape API HTTP error: {exc.response.status_code} "
                f"{exc.response.text}"
            ) from exc

    async def disconnect(self) -> None:
        """Close the underlying HTTP client and mark the connection as closed."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
        self._connected = False
        logger.info("Disconnected from Onshape API")

    def is_connected(self) -> bool:
        """Return ``True`` if the connection is currently active."""
        return self._connected

    # ------------------------------------------------------------------
    # Low-level request interface
    # ------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Send a low-level HTTP request to the Onshape API.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.).
            path: API path relative to base URL (e.g. ``/documents``).
            **kwargs: Additional keyword arguments forwarded to
                ``httpx.AsyncClient.request`` (json, params, etc.).

        Returns:
            The parsed JSON response body.

        Raises:
            OnshapeConnectionError: If not connected, the request times out,
                or the API returns an error.
        """
        if not self._connected or self._client is None:
            raise OnshapeConnectionError(
                "Not connected to Onshape. Call connect() first."
            )

        try:
            response = await self._client.request(method, path, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException as exc:
            raise OnshapeConnectionError(
                f"Request {method} {path} timed out after {self._timeout}s"
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise OnshapeConnectionError(
                f"Request {method} {path} HTTP error: "
                f"{exc.response.status_code} {exc.response.text}"
            ) from exc
        except httpx.RequestError as exc:
            raise OnshapeConnectionError(
                f"Request {method} {path} failed: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Document methods
    # ------------------------------------------------------------------

    async def list_documents(self) -> list[dict[str, Any]]:
        """List all documents accessible to the authenticated user.

        Returns:
            A list of document summary dicts, each with keys like
            ``id``, ``name``, ``createdAt``, ``modifiedAt``, etc.
        """
        result = await self._request("GET", "/documents")
        return result.get("items", [])

    async def get_document(self, doc_id: str) -> dict[str, Any]:
        """Retrieve metadata for a specific document.

        Args:
            doc_id: The Onshape document ID.

        Returns:
            A dict with document details including ``id``, ``name``,
            ``description``, ``owner``, etc.
        """
        return await self._request("GET", f"/documents/{doc_id}")

    async def create_document(self, name: str) -> dict[str, Any]:
        """Create a new empty Onshape document.

        Args:
            name: Name for the new document.

        Returns:
            A dict with the created document's ``id`` and ``name``.
        """
        return await self._request(
            "POST", "/documents", json={"name": name}
        )

    async def get_document_workspaces(
        self, doc_id: str
    ) -> list[dict[str, Any]]:
        """List all workspaces within a document.

        Args:
            doc_id: The Onshape document ID.

        Returns:
            A list of workspace dicts with ``id``, ``name``, ``type``, etc.
        """
        result = await self._request("GET", f"/documents/{doc_id}/workspaces")
        return result.get("items", [])

    async def get_document_elements(
        self, doc_id: str, wid: str
    ) -> list[dict[str, Any]]:
        """List all elements (tabs) within a workspace.

        Args:
            doc_id: The Onshape document ID.
            wid: The workspace ID.

        Returns:
            A list of element dicts with ``id``, ``name``, ``type``,
            ``subType``, etc.
        """
        result = await self._request(
            "GET", f"/documents/{doc_id}/workspaces/{wid}/elements"
        )
        return result.get("items", [])

    # ------------------------------------------------------------------
    # Part methods
    # ------------------------------------------------------------------

    async def get_part(
        self, doc_id: str, wid: str, eid: str, part_id: str
    ) -> dict[str, Any]:
        """Retrieve metadata for a specific part.

        Args:
            doc_id: Document ID.
            wid: Workspace ID.
            eid: Element (Part Studio) ID.
            part_id: Part ID.

        Returns:
            A dict with part metadata including ``id``, ``name``,
            ``partNumber``, ``geometry``, etc.
        """
        return await self._request(
            "GET",
            f"/documents/{doc_id}/workspaces/{wid}"
            f"/parts/{eid}/{part_id}",
        )

    async def list_parts(
        self, doc_id: str, wid: str, eid: str
    ) -> list[dict[str, Any]]:
        """List all parts in a Part Studio element.

        Args:
            doc_id: Document ID.
            wid: Workspace ID.
            eid: Element (Part Studio) ID.

        Returns:
            A list of part summary dicts.
        """
        result = await self._request(
            "GET",
            f"/documents/{doc_id}/workspaces/{wid}"
            f"/parts/{eid}",
        )
        return result.get("parts", [])

    async def get_part_properties(
        self, doc_id: str, wid: str, eid: str, part_id: str
    ) -> dict[str, Any]:
        """Retrieve physical properties (mass, volume, etc.) for a part.

        Args:
            doc_id: Document ID.
            wid: Workspace ID.
            eid: Element (Part Studio) ID.
            part_id: Part ID.

        Returns:
            A dict with mass properties including ``mass``, ``volume``,
            ``centerOfMass``, ``momentsOfInertia``, etc.
        """
        return await self._request(
            "GET",
            f"/documents/{doc_id}/workspaces/{wid}"
            f"/parts/{eid}/{part_id}/properties",
        )

    # ------------------------------------------------------------------
    # Feature methods
    # ------------------------------------------------------------------

    async def list_features(
        self, doc_id: str, wid: str, eid: str
    ) -> list[dict[str, Any]]:
        """List all features in a Part Studio's feature tree.

        Args:
            doc_id: Document ID.
            wid: Workspace ID.
            eid: Element (Part Studio) ID.

        Returns:
            A list of feature dicts with ``id``, ``name``, ``type``,
            ``suppressed``, etc.
        """
        result = await self._request(
            "GET",
            f"/documents/{doc_id}/workspaces/{wid}"
            f"/features/{eid}",
        )
        return result.get("features", [])

    async def create_feature(
        self, doc_id: str, wid: str, eid: str, feature_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Create a new feature in a Part Studio.

        Args:
            doc_id: Document ID.
            wid: Workspace ID.
            eid: Element (Part Studio) ID.
            feature_data: Feature JSON payload following Onshape's
                FeatureScript schema.

        Returns:
            A dict with the created feature's ``id`` and status.
        """
        return await self._request(
            "POST",
            f"/documents/{doc_id}/workspaces/{wid}"
            f"/features/{eid}",
            json=feature_data,
        )

    async def delete_feature(
        self, doc_id: str, wid: str, eid: str, feature_id: str
    ) -> dict[str, Any]:
        """Delete a feature from a Part Studio's feature tree.

        Args:
            doc_id: Document ID.
            wid: Workspace ID.
            eid: Element (Part Studio) ID.
            feature_id: Feature ID to delete.

        Returns:
            A dict with the deletion status.
        """
        return await self._request(
            "DELETE",
            f"/documents/{doc_id}/workspaces/{wid}"
            f"/features/{eid}/feature/{feature_id}",
        )

    # ------------------------------------------------------------------
    # Assembly methods
    # ------------------------------------------------------------------

    async def get_assembly(
        self, doc_id: str, wid: str, eid: str
    ) -> dict[str, Any]:
        """Retrieve the assembly definition.

        Args:
            doc_id: Document ID.
            wid: Workspace ID.
            eid: Element (Assembly) ID.

        Returns:
            A dict with assembly structure including root assembly,
            instances, occurrences, and mates.
        """
        return await self._request(
            "GET",
            f"/documents/{doc_id}/workspaces/{wid}"
            f"/assemblies/{eid}",
        )

    async def list_assembly_instances(
        self, doc_id: str, wid: str, eid: str
    ) -> list[dict[str, Any]]:
        """List all instances in an assembly.

        Args:
            doc_id: Document ID.
            wid: Workspace ID.
            eid: Element (Assembly) ID.

        Returns:
            A list of instance dicts with ``id``, ``path``,
            ``transform``, etc.
        """
        result = await self._request(
            "GET",
            f"/documents/{doc_id}/workspaces/{wid}"
            f"/assemblies/{eid}/instances",
        )
        return result.get("instances", [])

    async def insert_mate(
        self, doc_id: str, wid: str, eid: str, mate_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Insert a mate (constraint) into an assembly.

        Args:
            doc_id: Document ID.
            wid: Workspace ID.
            eid: Element (Assembly) ID.
            mate_data: Mate definition JSON following Onshape's
                assembly mate schema.

        Returns:
            A dict with the created mate's ``id`` and status.
        """
        return await self._request(
            "POST",
            f"/documents/{doc_id}/workspaces/{wid}"
            f"/assemblies/{eid}/mates",
            json=mate_data,
        )

    # ------------------------------------------------------------------
    # Drawing methods
    # ------------------------------------------------------------------

    async def get_drawing(
        self, doc_id: str, wid: str, eid: str
    ) -> dict[str, Any]:
        """Retrieve a drawing's metadata and sheet data.

        Args:
            doc_id: Document ID.
            wid: Workspace ID.
            eid: Element (Drawing) ID.

        Returns:
            A dict with drawing metadata including sheets, views,
            and dimensions.
        """
        return await self._request(
            "GET",
            f"/documents/{doc_id}/workspaces/{wid}"
            f"/drawings/{eid}",
        )

    async def create_drawing(
        self, doc_id: str, wid: str, name: str, sheet_size: str = "A"
    ) -> dict[str, Any]:
        """Create a new drawing in the given document workspace.

        Args:
            doc_id: Document ID.
            wid: Workspace ID.
            name: Drawing name.
            sheet_size: Sheet size (e.g. ``"A"``, ``"B"``, ``"C"``).

        Returns:
            A dict with the created drawing element's ``id`` and ``name``.
        """
        return await self._request(
            "POST",
            f"/documents/{doc_id}/workspaces/{wid}/drawings",
            json={"name": name, "sheetSize": sheet_size},
        )

    # ------------------------------------------------------------------
    # Export methods
    # ------------------------------------------------------------------

    async def export_stl(
        self, doc_id: str, wid: str, eid: str
    ) -> dict[str, Any]:
        """Export a Part Studio as STL.

        Args:
            doc_id: Document ID.
            wid: Workspace ID.
            eid: Element (Part Studio) ID.

        Returns:
            A dict with the export result, typically including a
            download URL or base64 content.
        """
        return await self._request(
            "POST",
            f"/documents/{doc_id}/workspaces/{wid}"
            f"/stl/export",
            json={"elementId": eid},
        )

    async def export_step(
        self, doc_id: str, wid: str, eid: str
    ) -> dict[str, Any]:
        """Export a Part Studio as STEP.

        Args:
            doc_id: Document ID.
            wid: Workspace ID.
            eid: Element (Part Studio) ID.

        Returns:
            A dict with the export result, typically including a
            download URL.
        """
        return await self._request(
            "POST",
            f"/documents/{doc_id}/workspaces/{wid}"
            f"/step/export",
            json={"elementId": eid},
        )

    async def export_pdf(
        self, doc_id: str, wid: str, eid: str
    ) -> dict[str, Any]:
        """Export a Drawing as PDF.

        Args:
            doc_id: Document ID.
            wid: Workspace ID.
            eid: Element (Drawing) ID.

        Returns:
            A dict with the export result, typically including a
            download URL.
        """
        return await self._request(
            "POST",
            f"/documents/{doc_id}/workspaces/{wid}"
            f"/pdf/export",
            json={"elementId": eid},
        )

    # ------------------------------------------------------------------
    # Translation / import methods
    # ------------------------------------------------------------------

    async def import_file(
        self, doc_id: str, wid: str, element_name: str, file_path: str, file_format: str = "stl"
    ) -> dict[str, Any]:
        """Import a file into an Onshape document via multipart upload.

        Args:
            doc_id: Document ID.
            wid: Workspace ID.
            element_name: Name for the imported element.
            file_path: Local filesystem path to the file to upload.
            file_format: File format hint (``"stl"``, ``"step"``, ``"iges"``, ``"obj"``).

        Returns:
            A dict with the created element's ``id`` and ``name``.
        """
        if not self._connected or self._client is None:
            raise OnshapeConnectionError(
                "Not connected to Onshape. Call connect() first."
            )

        filename = os.path.basename(file_path)
        content_type_map: dict[str, str] = {
            "stl": "application/sla",
            "step": "application/step",
            "iges": "application/iges",
            "obj": "application/octet-stream",
        }
        content_type = content_type_map.get(file_format.lower(), "application/octet-stream")

        with open(file_path, "rb") as f:
            files = {
                "file": (filename, f, content_type),
            }
            data = {
                "elementName": element_name,
                "format": file_format.upper(),
            }
            try:
                response = await self._client.post(
                    f"/documents/{doc_id}/workspaces/{wid}/elements",
                    files=files,
                    data=data,
                )
                response.raise_for_status()
                return response.json()
            except httpx.TimeoutException as exc:
                raise OnshapeConnectionError(
                    f"Import file timed out after {self._timeout}s"
                ) from exc
            except httpx.HTTPStatusError as exc:
                raise OnshapeConnectionError(
                    f"Import file HTTP error: "
                    f"{exc.response.status_code} {exc.response.text}"
                ) from exc
            except httpx.RequestError as exc:
                raise OnshapeConnectionError(
                    f"Import file failed: {exc}"
                ) from exc
            except FileNotFoundError as exc:
                raise OnshapeConnectionError(
                    f"File not found: {file_path}"
                ) from exc

    async def export_iges(
        self, doc_id: str, wid: str, eid: str
    ) -> dict[str, Any]:
        """Export a Part Studio as IGES.

        Args:
            doc_id: Document ID.
            wid: Workspace ID.
            eid: Element (Part Studio) ID.

        Returns:
            A dict with the export result, typically including a
            download URL.
        """
        return await self._request(
            "POST",
            f"/documents/{doc_id}/workspaces/{wid}"
            f"/iges/export",
            json={"elementId": eid},
        )

    async def get_translation_status(
        self, translation_id: str
    ) -> dict[str, Any]:
        """Check the status of a translation (import/export) job.

        Args:
            translation_id: The translation job ID returned by an
                import or export call.

        Returns:
            A dict with ``requestState`` (e.g. ``"DONE"``, ``"ACTIVE"``,
            ``"FAILED"``) and result details.
        """
        return await self._request(
            "GET", f"/translations/{translation_id}"
        )

    async def create_assembly_element(
        self, doc_id: str, wid: str, name: str
    ) -> dict[str, Any]:
        """Create a new empty assembly element in a document workspace.

        Args:
            doc_id: Document ID.
            wid: Workspace ID.
            name: Assembly name.

        Returns:
            A dict with the created assembly element's ``id`` and ``name``.
        """
        return await self._request(
            "POST",
            f"/documents/{doc_id}/workspaces/{wid}/assemblies",
            json={"name": name},
        )

    # ------------------------------------------------------------------
    # Singleton convenience
    # ------------------------------------------------------------------

    _instance: OnshapeConnection | None = None

    @classmethod
    def get_global(cls) -> OnshapeConnection:
        """Return a module-level singleton connection.

        The caller is still responsible for calling ``connect()`` and
        ``disconnect()`` at the appropriate lifecycle points.
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
