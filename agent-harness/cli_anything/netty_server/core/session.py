"""
Session state manager for the Netty Server CLI REPL.

Provides an undo/redo stack and persistent context (current device, etc.)
so that interactive commands can be run without repeating arguments.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from cli_anything.netty_server.core.types import CLISession


class SessionManager:
    """Manages a CLISession with undo/redo support.

    Every state mutation is recorded on an undo stack.  Call ``undo()``
    to revert and ``redo()`` to re-apply.
    """

    def __init__(self) -> None:
        self._session = CLISession()
        self._undo_stack: List[CLISession] = []
        self._redo_stack: List[CLISession] = []

    @property
    def session(self) -> CLISession:
        return self._session

    # -- Snapshot helpers ---------------------------------------------------

    def _snapshot(self) -> CLISession:
        """Return a shallow copy of the current session."""
        s = CLISession(
            current_sn=self._session.current_sn,
            known_devices=list(self._session.known_devices),
            last_command=self._session.last_command,
            last_result=self._session.last_result,
            history=list(self._session.history),
            host=self._session.host,
            port=self._session.port,
            json_output=self._session.json_output,
        )
        return s

    def _restore(self, s: CLISession) -> None:
        self._session.current_sn = s.current_sn
        self._session.known_devices = list(s.known_devices)
        self._session.last_command = s.last_command
        self._session.last_result = s.last_result
        self._session.history = list(s.history)
        self._session.host = s.host
        self._session.port = s.port
        self._session.json_output = s.json_output

    # -- Mutations with undo ------------------------------------------------

    def set_current_device(self, sn: Optional[str]) -> None:
        self._undo_stack.append(self._snapshot())
        self._redo_stack.clear()
        self._session.current_sn = sn
        if sn and sn not in self._session.known_devices:
            self._session.known_devices.append(sn)

    def set_server(self, host: str, port: int) -> None:
        self._undo_stack.append(self._snapshot())
        self._redo_stack.clear()
        self._session.host = host
        self._session.port = port

    def set_json_output(self, enabled: bool) -> None:
        self._undo_stack.append(self._snapshot())
        self._redo_stack.clear()
        self._session.json_output = enabled

    def record_result(self, command: str, result: Dict[str, Any]) -> None:
        self._undo_stack.append(self._snapshot())
        self._redo_stack.clear()
        self._session.last_command = command
        self._session.last_result = result
        self._session.history.append(command)

    def sync_known_devices(self, devices: List[str]) -> None:
        """Update the known device list from a server query."""
        self._undo_stack.append(self._snapshot())
        self._redo_stack.clear()
        for sn in devices:
            if sn not in self._session.known_devices:
                self._session.known_devices.append(sn)

    # -- Undo / Redo --------------------------------------------------------

    @property
    def can_undo(self) -> bool:
        return bool(self._undo_stack)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo_stack)

    def undo(self) -> bool:
        if not self._undo_stack:
            return False
        self._redo_stack.append(self._snapshot())
        self._restore(self._undo_stack.pop())
        return True

    def redo(self) -> bool:
        if not self._redo_stack:
            return False
        self._undo_stack.append(self._snapshot())
        self._restore(self._redo_stack.pop())
        return True

    def clear_history(self) -> None:
        self._undo_stack.append(self._snapshot())
        self._redo_stack.clear()
        self._session.history.clear()
        self._session.last_command = None
        self._session.last_result = None
