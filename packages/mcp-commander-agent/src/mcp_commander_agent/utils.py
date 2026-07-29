"""Shared utility functions for MCP Commander Agent."""

from __future__ import annotations

import datetime as _dt
import json
import logging
import shutil
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def format_result(result: Any) -> str:
    """Format an MCP tool result for human-readable display."""
    if result is None:
        return "(no result)"
    if isinstance(result, str):
        return result.strip()
    if isinstance(result, (dict, list)):
        try:
            return json.dumps(result, indent=2, default=str)
        except (TypeError, ValueError):
            return str(result)
    return str(result)


def confirm_action(description: str) -> bool:
    """Prompt the user for a yes/no confirmation.

    Returns True if the user confirms, False otherwise.
    Defaults to True when stdin is not a TTY (non-interactive mode).
    """
    if not sys.stdin.isatty():
        logger.info("Non-interactive mode -- auto-confirming: %s", description)
        return True
    try:
        response = input(f"Confirm: {description} [Y/n] ").strip().lower()
        return response in ("", "y", "yes")
    except (EOFError, KeyboardInterrupt):
        return False


def create_backup(filepath: str | Path) -> Path | None:
    """Create a timestamped backup of *filepath*.

    Returns the backup path, or None if the file does not exist.
    """
    src = Path(filepath).resolve()
    if not src.is_file():
        logger.warning("Cannot back up -- file does not exist: %s", src)
        return None
    ts = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = src.with_name(f"{src.stem}_{ts}_backup{src.suffix}")
    shutil.copy2(src, backup)
    logger.info("Backup created: %s -> %s", src, backup)
    return backup


def log_execution(plan: Any, results: list[Any], log_path: str | Path = "mcp_commander_exec.log") -> None:
    """Append an execution record to a JSON-lines log file."""
    entry = {
        "timestamp": _dt.datetime.now().isoformat(),
        "plan": _serialize(plan),
        "results": [_serialize(r) for r in results],
    }
    path = Path(log_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, default=str) + "\n")
    logger.debug("Execution logged to %s", path)


def _serialize(obj: Any) -> Any:
    """Best-effort JSON-serializable representation of an object."""
    if hasattr(obj, "__dataclass_fields__"):
        from dataclasses import asdict
        return asdict(obj)
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    if isinstance(obj, (list, tuple)):
        return [_serialize(item) for item in obj]
    if isinstance(obj, dict):
        return {str(k): _serialize(v) for k, v in obj.items()}
    return str(obj)
