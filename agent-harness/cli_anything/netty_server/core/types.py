"""Shared type definitions for the Netty Server CLI harness."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CLISession:
    """Holds interactive session state for the REPL mode.

    Tracks the last queried device, last command result, history, etc.
    """

    # Device context
    current_sn: Optional[str] = None
    known_devices: List[str] = field(default_factory=list)

    # Command history
    last_command: Optional[str] = None
    last_result: Optional[Dict[str, Any]] = None
    history: List[str] = field(default_factory=list)

    # Server connection
    host: str = "localhost"
    port: int = 8235

    # Display
    json_output: bool = False
