"""
HTTP client for the Netty Server's Device Command API (port 8235).

All communication with the running Netty server happens through this module.
The server exposes:
  - GET  /api/debug/connections      → list online device SNs
  - GET  /api/device/status          → per-device online status
  - POST /api/device/command         → send a structured command
  - POST /api/device/custom-command  → send raw JSON data

References
----------
Host server source: DeviceCommandServer.java in the netty-server project.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from urllib.error import URLError
from urllib.request import Request, urlopen


class NettyServerError(Exception):
    """Raised when the Netty HTTP API returns an error or is unreachable."""


class DeviceOfflineWarning(Warning):
    """Raised when a command is sent to an offline device."""


@dataclass
class DeviceInfo:
    """Represents a connected device and its known metadata."""
    sn: str
    online: bool = True
    message_format: str = "#$"
    bn: Optional[int] = None
    num: Optional[int] = None
    device_type: Optional[str] = None
    fw: Optional[str] = None


@dataclass
class CommandResult:
    """Result of sending a command to a device."""
    success: bool
    sn: str
    response: Optional[Dict[str, Any]] = None
    warning: Optional[str] = None
    error: Optional[str] = None


class NettyHttpClient:
    """Wraps the Netty Device Command HTTP API.

    Parameters
    ----------
    host : str
        Hostname or IP of the Netty server (default localhost).
    port : int
        HTTP command API port (default 8235, matches config.properties).
    timeout : int
        Request timeout in seconds (default 10).
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8235,
        timeout: int = 10,
    ):
        self.base_url = f"http://{host}:{port}"
        self.timeout = timeout

    # ------------------------------------------------------------------
    # Low-level request helpers
    # ------------------------------------------------------------------

    def _get(self, path: str) -> Dict[str, Any]:
        """Perform a GET request and return parsed JSON."""
        url = f"{self.base_url}{path}"
        try:
            req = Request(url, method="GET")
            with urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body)
        except URLError as exc:
            raise NettyServerError(
                f"Cannot reach Netty HTTP API at {url}: {exc.reason}"
            ) from exc
        except (json.JSONDecodeError, OSError) as exc:
            raise NettyServerError(f"Invalid response from {url}: {exc}") from exc

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Perform a POST request with JSON body and return parsed JSON."""
        url = f"{self.base_url}{path}"
        data = json.dumps(payload).encode("utf-8")
        try:
            req = Request(url, data=data, method="POST")
            req.add_header("Content-Type", "application/json")
            with urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body)
        except URLError as exc:
            raise NettyServerError(
                f"Cannot reach Netty HTTP API at {url}: {exc.reason}"
            ) from exc
        except (json.JSONDecodeError, OSError) as exc:
            raise NettyServerError(f"Invalid response from {url}: {exc}") from exc

    # ------------------------------------------------------------------
    # Device discovery
    # ------------------------------------------------------------------

    def list_online_devices(self) -> List[str]:
        """Return a list of SNs for all currently connected devices.

        Calls ``GET /api/debug/connections``.
        """
        result = self._get("/api/debug/connections")
        return result.get("onlineDevices", [])

    def get_device_status(self) -> Dict[str, bool]:
        """Return a dict mapping each known device SN to its online status.

        Calls ``GET /api/device/status``.
        """
        result = self._get("/api/device/status")
        return result.get("deviceStatus", {})

    def get_all_devices(self) -> List[DeviceInfo]:
        """Return a list of DeviceInfo for every known device.

        Combines information from the status endpoint.  For richer metadata
        (bn, type, fw) you would need to inspect device log files or wait for
        a detailup; currently the HTTP API does not expose those directly.
        """
        status_map = self.get_device_status()
        return [
            DeviceInfo(sn=sn, online=online)
            for sn, online in status_map.items()
        ]

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    def send_command(
        self,
        sn: str,
        cmd: str,
        data: Optional[Dict[str, Any]] = None,
        aims: Optional[int] = None,
    ) -> CommandResult:
        """Send a structured command to a device.

        Parameters
        ----------
        sn : str
            Device serial number.
        cmd : str
            Command name (login, heartbeat, detail, detailup, force,
            rent, return, or any custom command the device understands).
        data : dict or None
            Optional payload data (e.g. ``{"n": 1}`` for force commands).
        aims : int or None
            Target AIMs group; auto-calculated if omitted.

        Returns
        -------
        CommandResult
            Contains success flag, the device response (if received), and
            any warnings.
        """
        payload: Dict[str, Any] = {"sn": sn, "cmd": cmd}
        if data is not None:
            payload["data"] = data
        if aims is not None:
            payload["aims"] = aims

        result = self._post("/api/device/command", payload)
        return CommandResult(
            success=result.get("success", False),
            sn=result.get("sn", sn),
            response=result.get("response"),
            warning=result.get("warning"),
            error=result.get("error"),
        )

    def send_custom_command(
        self,
        sn: str,
        json_data: str,
    ) -> CommandResult:
        """Send a raw JSON string directly to a device.

        This is useful for prototyping or sending commands that the
        structured API doesn't yet support.

        Parameters
        ----------
        sn : str
            Device serial number.
        json_data : str
            Raw JSON string to send (e.g. ``'{"cmd":"force","data":{"n":1}}'``).
        """
        payload = {"sn": sn, "jsonData": json_data}
        result = self._post("/api/device/custom-command", payload)
        return CommandResult(
            success=result.get("success", False),
            sn=result.get("sn", sn),
            warning=result.get("warning"),
            error=result.get("error"),
        )

    # ------------------------------------------------------------------
    # Convenience: known device commands
    # ------------------------------------------------------------------

    def get_detail(self, sn: str) -> CommandResult:
        """Request device detail data (polling endpoint data)."""
        return self.send_command(sn, "detail", data={"n": 0})

    def get_heartbeat(self, sn: str) -> CommandResult:
        """Send a heartbeat ping to a device."""
        return self.send_command(sn, "heartbeat")

    def force_release(self, sn: str, n: int) -> CommandResult:
        """Send a force-release command for a specific port index *n*."""
        return self.send_command(sn, "force", data={"n": n})

    def rent_lock(self, sn: str, n: int) -> CommandResult:
        """Send a rent (lock) command for a specific port index *n*."""
        return self.send_command(sn, "rent", data={"n": n})

    def return_unlock(self, sn: str, n: int) -> CommandResult:
        """Send a return (unlock) command for a specific port index *n*."""
        return self.send_command(sn, "return", data={"n": n})
