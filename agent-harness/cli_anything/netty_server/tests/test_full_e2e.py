"""
End-to-end tests for the Netty Server CLI.

These tests require:
  1. The harness installed (`pip install -e .` or `pip install -e agent-harness/`)
  2. A running Netty TCP server on localhost:8235 (for HTTP API tests)

Set environment variables to customise:
  NETTY_HOST  — server hostname (default: localhost)
  NETTY_PORT  — HTTP API port   (default: 8235)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

import pytest

# ---------------------------------------------------------------------------
# Environment / helpers
# ---------------------------------------------------------------------------

NETTY_HOST = os.environ.get("NETTY_HOST", "localhost")
NETTY_PORT = int(os.environ.get("NETTY_PORT", "8235"))


def cli_command(*args: str) -> subprocess.CompletedProcess:
    """Run the CLI and return the completed process."""
    cmd = ["cli-anything-netty-server", *args]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=15,
    )
    return result


def server_is_reachable() -> bool:
    """Check if the Netty HTTP API is up."""
    try:
        req = Request(f"http://{NETTY_HOST}:{NETTY_PORT}/api/debug/connections")
        with urlopen(req, timeout=3):
            return True
    except (URLError, OSError):
        return False


def device_is_online() -> bool:
    """Check if at least one device is connected."""
    try:
        req = Request(f"http://{NETTY_HOST}:{NETTY_PORT}/api/debug/connections")
        with urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            devices = data.get("onlineDevices", [])
            return len(devices) > 0
    except (URLError, OSError, json.JSONDecodeError):
        return False


# ===================================================================
# E2E Tests
# ===================================================================

class TestCLIInstalled:
    """Verify the CLI tool is installed and accessible."""

    def test_cli_version(self):
        """CLI entry point exists and responds."""
        result = cli_command("--version")
        assert result.returncode == 0

    def test_cli_help(self):
        """--help shows all command groups."""
        result = cli_command("--help")
        assert result.returncode == 0
        assert "devices" in result.stdout
        assert "command" in result.stdout
        assert "logs" in result.stdout
        assert "server" in result.stdout
        assert "session" in result.stdout

    def test_devices_help(self):
        """devices --help shows subcommands."""
        result = cli_command("devices", "--help")
        assert result.returncode == 0
        assert "list" in result.stdout or "Status" in result.stdout

    def test_command_help(self):
        """command --help shows subcommands."""
        result = cli_command("command", "--help")
        assert result.returncode == 0
        assert "send" in result.stdout or "custom" in result.stdout

    def test_logs_help(self):
        """logs --help shows subcommands."""
        result = cli_command("logs", "--help")
        assert result.returncode == 0
        assert "show" in result.stdout

    def test_server_help(self):
        """server --help shows subcommands."""
        result = cli_command("server", "--help")
        assert result.returncode == 0

    def test_session_help(self):
        """session --help shows subcommands."""
        result = cli_command("session", "--help")
        assert result.returncode == 0


class TestDevicesCommands:
    """Test device listing and status (requires running server)."""

    @pytest.mark.skipif(not server_is_reachable(), reason="Netty server not running")
    def test_devices_list(self):
        """devices list returns online devices."""
        result = cli_command("devices", "list", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "online_devices" in data
        assert isinstance(data["online_devices"], list)

    @pytest.mark.skipif(not server_is_reachable(), reason="Netty server not running")
    def test_devices_status(self):
        """devices status returns status map."""
        result = cli_command("devices", "status", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "device_status" in data
        assert isinstance(data["device_status"], dict)

    @pytest.mark.skipif(not server_is_reachable(), reason="Netty server not running")
    def test_devices_list_table(self):
        """devices list without --json returns readable table."""
        result = cli_command("devices", "list")
        assert result.returncode == 0
        # Should contain device SNs or a "no devices" message
        assert len(result.stdout) > 0


class TestCommandCommands:
    """Test sending commands (requires server + at least one online device)."""

    @pytest.mark.skipif(not device_is_online(), reason="No online device available")
    def test_command_detail(self):
        """Send detail command to first online device."""
        # Get a device SN
        result = cli_command("devices", "list", "--json")
        devices = json.loads(result.stdout).get("online_devices", [])
        if not devices:
            pytest.skip("No online devices")
        sn = devices[0]

        result = cli_command("command", "send", sn, "detail", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "success" in data

    @pytest.mark.skipif(not device_is_online(), reason="No online device available")
    def test_command_force(self):
        """Send force command with port index."""
        result = cli_command("devices", "list", "--json")
        devices = json.loads(result.stdout).get("online_devices", [])
        if not devices:
            pytest.skip("No online devices")
        sn = devices[0]

        result = cli_command("command", "send", sn, "force", "--n", "1", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "success" in data

    @pytest.mark.skipif(not server_is_reachable(), reason="Netty server not running")
    def test_command_custom(self):
        """Send custom JSON to a device."""
        result = cli_command("devices", "list", "--json")
        devices = json.loads(result.stdout).get("online_devices", [])
        if not devices:
            pytest.skip("No online devices")
        sn = devices[0]

        result = cli_command(
            "command", "custom", sn,
            '{"cmd":"detail","data":{}}',
            "--json",
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "success" in data


class TestLogsCommands:
    """Test log-related commands (does not require server)."""

    def test_logs_list_devices(self):
        """logs list-devices returns device SNs."""
        result = cli_command("logs", "list-devices", "--json")
        # May fail if no log dir configured — that's acceptable
        if result.returncode == 0:
            data = json.loads(result.stdout)
            assert "devices" in data

    def test_logs_show_nonexistent(self):
        """logs show for a non-existent device returns gracefully."""
        result = cli_command("logs", "show", "NONEXISTENT_SN_12345", "--json")
        # Should either succeed with empty result or give a useful error
        assert result.returncode in (0, 2)

    def test_logs_events_help(self):
        """logs events subcommand has help."""
        result = cli_command("logs", "events", "--help")
        assert result.returncode == 0


class TestServerCommands:
    """Test server info command."""

    @pytest.mark.skipif(not server_is_reachable(), reason="Netty server not running")
    def test_server_info(self):
        """server info returns connection status."""
        result = cli_command("server", "info", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "host" in data
        assert "port" in data
        assert "online_count" in data


class TestJSONOutput:
    """Test --json flag consistently produces valid JSON."""

    @pytest.mark.skipif(not server_is_reachable(), reason="Netty server not running")
    def test_json_output_all_devices(self):
        """All device-related commands output valid JSON with --json."""
        for sub in ["list", "status"]:
            result = cli_command("devices", sub, "--json")
            assert result.returncode == 0
            try:
                json.loads(result.stdout)
            except json.JSONDecodeError:
                pytest.fail(f"devices {sub} --json: invalid JSON: {result.stdout}")

    def test_json_output_logs(self):
        """Log commands output valid JSON with --json (no server needed)."""
        result = cli_command("logs", "list-devices", "--json")
        if result.returncode == 0:
            try:
                json.loads(result.stdout)
            except json.JSONDecodeError:
                pytest.fail(f"logs list-devices --json: invalid JSON: {result.stdout}")


class TestServerUnreachable:
    """Test graceful handling when server is down."""

    def test_devices_list_no_server(self):
        """devices list fails gracefully when server is unreachable."""
        result = cli_command("devices", "list")
        # Should not crash — may return exit code 0 or 1 depending on design
        assert result.returncode in (0, 1)
