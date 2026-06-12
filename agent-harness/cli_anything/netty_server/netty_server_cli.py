"""
Netty Server CLI — IoT device communication server management tool.

Usage
-----
One-shot mode::

    cli-anything-netty-server devices list
    cli-anything-netty-server command send <sn> <cmd>
    cli-anything-netty-server logs show <sn>

REPL mode (default when no subcommand is given)::

    cli-anything-netty-server
    > devices list
    > command send ZCG0422412160066 detail
    > logs show ZCG0422412160066
    > exit

All commands support ``--json`` for machine-readable output.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import click

from cli_anything.netty_server.core.session import SessionManager
from cli_anything.netty_server.utils.http_client import (
    NettyHttpClient,
    NettyServerError,
    DeviceOfflineWarning,
)
from cli_anything.netty_server.utils.log_reader import LogReader, LogEntry

# ---------------------------------------------------------------------------
# Global state
# ---------------------------------------------------------------------------

_session_mgr = SessionManager()


def _get_client() -> NettyHttpClient:
    s = _session_mgr.session
    return NettyHttpClient(host=s.host, port=s.port)


def _get_log_reader() -> LogReader:
    # Try to find the log dir relative to the project
    # Walk upward looking for a "log" directory
    candidate = Path("log").resolve()
    if candidate.is_dir():
        return LogReader(log_dir=candidate)

    # Fall back to the server's default
    return LogReader()


def _json_echo(data: Any, **kwargs: Any) -> None:
    """Print data as JSON and exit."""
    click.echo(json.dumps(data, ensure_ascii=False, default=str, **kwargs))


# ---------------------------------------------------------------------------
# Shared CLI options
# ---------------------------------------------------------------------------

def _server_options(f):
    """Add --host and --port options to a command."""
    f = click.option(
        "--host",
        default=lambda: _session_mgr.session.host,
        show_default=True,
        help="Netty server hostname.",
    )(f)
    f = click.option(
        "--port",
        type=int,
        default=lambda: _session_mgr.session.port,
        show_default=True,
        help="Netty HTTP command API port.",
    )(f)
    return f


def _json_option(f):
    """Add --json / -j flag."""
    f = click.option(
        "-j", "--json/--no-json",
        "json_output",
        default=False,
        help="Output raw JSON instead of formatted text.",
    )(f)
    return f


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_timestamp(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _print_devices_table(devices: List[str], status_map: Dict[str, bool]) -> None:
    """Print a table of devices with their online status."""
    if not devices and not status_map:
        click.echo("No devices found.")
        return

    all_sns = list(dict.fromkeys(list(devices) + list(status_map.keys())))
    if not all_sns:
        click.echo("No devices found.")
        return

    click.echo(f"{'SN':<30} {'Status':<10}")
    click.echo("-" * 42)
    for sn in sorted(all_sns):
        status = "🟢 Online" if status_map.get(sn, False) else "🔴 Offline"
        click.echo(f"{sn:<30} {status:<10}")


def _print_command_result(result: Any, json_output: bool) -> None:
    """Print a command result nicely."""
    if json_output:
        _json_echo({
            "success": result.success,
            "sn": result.sn,
            "response": result.response,
            "warning": result.warning,
            "error": result.error,
        })
        return

    if result.error:
        click.secho(f"✗ Error: {result.error}", fg="red")
        return

    click.secho(f"✓ Command sent to {result.sn}", fg="green", bold=True)
    if result.warning:
        click.secho(f"  ⚠ {result.warning}", fg="yellow")

    if result.response:
        click.echo("\nResponse:")
        click.echo(json.dumps(result.response, ensure_ascii=False, indent=2))


def _print_log_entries(entries: List[LogEntry], json_output: bool) -> None:
    """Print a list of log entries."""
    if json_output:
        _json_echo([
            {
                "timestamp": _format_timestamp(e.timestamp),
                "client_id": e.client_id,
                "client_ip": e.client_ip,
                "event_type": e.event_type,
                "receive_data": e.receive_data,
                "send_data": e.send_data,
            }
            for e in entries
        ])
        return

    if not entries:
        click.echo("No log entries found.")
        return

    for i, e in enumerate(entries):
        if i > 0:
            click.echo("─" * 60)
        click.echo(f"[{_format_timestamp(e.timestamp)}] ", nl=False)
        click.secho(f"{e.event_type.upper()}", bold=True)
        if e.client_id:
            click.echo(f"  Client: {e.client_id} (IP: {e.client_ip})")
        if e.receive_data:
            click.echo(f"  ← Receive: {e.receive_data[:200]}{'…' if len(e.receive_data) > 200 else ''}")
        if e.send_data:
            click.echo(f"  → Send: {e.send_data[:200]}{'…' if len(e.send_data) > 200 else ''}")


# ---------------------------------------------------------------------------
# Click CLI
# ---------------------------------------------------------------------------

@click.group(invoke_without_command=True)
@click.option("--host", default="localhost", help="Netty server hostname.")
@click.option("--port", type=int, default=8235, help="Netty HTTP command API port.")
@click.pass_context
def cli(ctx: click.Context, host: str, port: int) -> None:
    """Netty Server CLI — manage IoT devices via the HTTP command API.

    When invoked without a subcommand, enters an interactive REPL.
    """
    _session_mgr.set_server(host, port)

    if ctx.invoked_subcommand is None:
        # Enter REPL mode
        _repl()
        sys.exit(0)


# ===========================================================================
# DEVICES
# ===========================================================================

@cli.group()
def devices() -> None:
    """Query and manage device connections."""


@devices.command("list")
@_server_options
@_json_option
def devices_list(host: str, port: int, json_output: bool) -> None:
    """List all online devices currently connected to the server."""
    client = NettyHttpClient(host=host, port=port)
    try:
        online = client.list_online_devices()
        status = client.get_device_status()
    except NettyServerError as e:
        click.secho(f"Error: {e}", fg="red", err=True)
        sys.exit(1)

    _session_mgr.sync_known_devices(online)

    if json_output:
        _json_echo({"onlineDevices": online, "deviceStatus": status})
        return

    click.secho(f"Online devices ({len(online)} total):", bold=True)
    _print_devices_table(online, status)


@devices.command("status")
@click.argument("sn", required=False)
@_server_options
@_json_option
def devices_status(sn: Optional[str], host: str, port: int, json_output: bool) -> None:
    """Show online status for one or all devices.

    If SN is omitted, shows status for all known devices.
    """
    client = NettyHttpClient(host=host, port=port)
    try:
        status = client.get_device_status()
    except NettyServerError as e:
        click.secho(f"Error: {e}", fg="red", err=True)
        sys.exit(1)

    if sn:
        online = status.get(sn, False)
        if json_output:
            _json_echo({"sn": sn, "online": online})
            return
        icon = "🟢" if online else "🔴"
        click.echo(f"{icon} Device {sn} is {'online' if online else 'offline'}")
        return

    _session_mgr.sync_known_devices(list(status.keys()))

    if json_output:
        _json_echo({"deviceStatus": status})
        return

    click.secho(f"Device status ({len(status)} known):", bold=True)
    _print_devices_table([], status)


@devices.command("info")
@click.argument("sn")
@_server_options
@_json_option
def devices_info(sn: str, host: str, port: int, json_output: bool) -> None:
    """Show detailed metadata for a device (from logs)."""
    log_reader = _get_log_reader()
    summary = log_reader.summarize_device(sn)

    if json_output:
        _json_echo({
            "sn": sn,
            "total_events": summary.total_events,
            "first_seen": _format_timestamp(summary.first_seen) if summary.first_seen else None,
            "last_seen": _format_timestamp(summary.last_seen) if summary.last_seen else None,
            "event_counts": summary.event_counts,
        })
        return

    click.secho(f"Device: {sn}", bold=True)
    click.echo(f"  Total events logged: {summary.total_events}")
    if summary.first_seen:
        click.echo(f"  First seen: {_format_timestamp(summary.first_seen)}")
    if summary.last_seen:
        click.echo(f"  Last seen: {_format_timestamp(summary.last_seen)}")
    if summary.event_counts:
        click.echo("  Event breakdown:")
        for evt, count in sorted(summary.event_counts.items()):
            click.echo(f"    {evt}: {count}")


# ===========================================================================
# COMMAND
# ===========================================================================

@cli.group()
def command() -> None:
    """Send commands to devices."""


@command.command("send")
@click.argument("sn")
@click.argument("cmd")
@click.option("--data", "-d", default=None, help="JSON data payload (e.g. '{\"n\": 1}').")
@click.option("--aims", type=int, default=None, help="AIMs group override.")
@_server_options
@_json_option
def command_send(
    sn: str,
    cmd: str,
    data: Optional[str],
    aims: Optional[int],
    host: str,
    port: int,
    json_output: bool,
) -> None:
    """Send a structured command to a device.

    Common commands: login, heartbeat, detail, detailup, force, rent, return.

    SN is the device serial number (e.g. ZCG0422412160066).
    """
    client = NettyHttpClient(host=host, port=port)

    parsed_data = None
    if data:
        try:
            parsed_data = json.loads(data)
        except json.JSONDecodeError as e:
            click.secho(f"Invalid JSON in --data: {e}", fg="red", err=True)
            sys.exit(1)

    try:
        result = client.send_command(sn, cmd, data=parsed_data, aims=aims)
    except NettyServerError as e:
        click.secho(f"Error: {e}", fg="red", err=True)
        sys.exit(1)

    _session_mgr.set_current_device(sn)
    _session_mgr.record_result(f"command send {sn} {cmd}", {
        "success": result.success,
        "response": result.response,
        "warning": result.warning,
    })

    _print_command_result(result, json_output)


@command.command("detail")
@click.argument("sn")
@_server_options
@_json_option
def command_detail(sn: str, host: str, port: int, json_output: bool) -> None:
    """Query device detail (polling endpoint data).

    This requests the 'detail' command and waits for a response,
    including multi-part aggregation when the device has multiple AIMs groups.
    """
    client = NettyHttpClient(host=host, port=port)
    try:
        result = client.get_detail(sn)
    except NettyServerError as e:
        click.secho(f"Error: {e}", fg="red", err=True)
        sys.exit(1)

    _session_mgr.set_current_device(sn)
    _session_mgr.record_result(f"command detail {sn}", {
        "success": result.success,
        "response": result.response,
    })

    _print_command_result(result, json_output)


@command.command("force")
@click.argument("sn")
@click.argument("n", type=int)
@_server_options
@_json_option
def command_force(sn: str, n: int, host: str, port: int, json_output: bool) -> None:
    """Send a force-release command for port index N."""
    client = NettyHttpClient(host=host, port=port)
    try:
        result = client.force_release(sn, n)
    except NettyServerError as e:
        click.secho(f"Error: {e}", fg="red", err=True)
        sys.exit(1)

    _session_mgr.set_current_device(sn)
    _print_command_result(result, json_output)


@command.command("rent")
@click.argument("sn")
@click.argument("n", type=int)
@_server_options
@_json_option
def command_rent(sn: str, n: int, host: str, port: int, json_output: bool) -> None:
    """Send a rent (lock) command for port index N."""
    client = NettyHttpClient(host=host, port=port)
    try:
        result = client.rent_lock(sn, n)
    except NettyServerError as e:
        click.secho(f"Error: {e}", fg="red", err=True)
        sys.exit(1)

    _session_mgr.set_current_device(sn)
    _print_command_result(result, json_output)


@command.command("return")
@click.argument("sn")
@click.argument("n", type=int)
@_server_options
@_json_option
def command_return(sn: str, n: int, host: str, port: int, json_output: bool) -> None:
    """Send a return (unlock) command for port index N."""
    client = NettyHttpClient(host=host, port=port)
    try:
        result = client.return_unlock(sn, n)
    except NettyServerError as e:
        click.secho(f"Error: {e}", fg="red", err=True)
        sys.exit(1)

    _session_mgr.set_current_device(sn)
    _print_command_result(result, json_output)


@command.command("custom")
@click.argument("sn")
@click.argument("json_data")
@_server_options
@_json_option
def command_custom(
    sn: str,
    json_data: str,
    host: str,
    port: int,
    json_output: bool,
) -> None:
    """Send a raw JSON payload directly to a device.

    JSON_DATA should be a JSON string (e.g. '{"cmd":"force","data":{"n":1}}').
    """
    client = NettyHttpClient(host=host, port=port)
    try:
        result = client.send_custom_command(sn, json_data)
    except NettyServerError as e:
        click.secho(f"Error: {e}", fg="red", err=True)
        sys.exit(1)

    _session_mgr.set_current_device(sn)
    _print_command_result(result, json_output)


# ===========================================================================
# LOGS
# ===========================================================================

@cli.group()
def logs() -> None:
    """Inspect device log files."""


@logs.command("show")
@click.argument("sn")
@click.option("--date", "-d", "log_date", default=None,
              help="Specific date (YYYY-MM-DD). Default: most recent day.")
@click.option("--event", "-e", "event_type", default=None,
              help="Filter by event type (login, heart, detailup, detail, send, etc.).")
@click.option("--limit", "-n", type=int, default=20,
              help="Number of entries to show (newest first). Default: 20.")
@_server_options
@_json_option
def logs_show(
    sn: str,
    log_date: Optional[str],
    event_type: Optional[str],
    limit: int,
    host: str,
    port: int,
    json_output: bool,
) -> None:
    """Show recent log entries for a device.

    SN is the device serial number.

    The log file stores events in this format:
      timestamp + client info + event type + receive/send data
    """
    log_reader = _get_log_reader()

    try:
        if log_date:
            dt = datetime.strptime(log_date, "%Y-%m-%d").date()
            entries = log_reader.get_device_logs(sn, log_date=dt)
            entries.sort(key=lambda e: e.timestamp, reverse=True)
            if event_type:
                entries = [e for e in entries if e.event_type == event_type]
            entries = entries[:limit]
        else:
            entries = log_reader.recent_events(sn, event_type=event_type, limit=limit)
    except Exception as e:
        click.secho(f"Error reading logs: {e}", fg="red", err=True)
        sys.exit(1)

    _session_mgr.set_current_device(sn)
    _print_log_entries(entries, json_output)


@logs.command("list-devices")
@_server_options
@_json_option
def logs_list_devices(host: str, port: int, json_output: bool) -> None:
    """List all device SNs that have log files."""
    log_reader = _get_log_reader()
    try:
        sns = log_reader.available_device_sns()
    except Exception as e:
        click.secho(f"Error scanning logs: {e}", fg="red", err=True)
        sys.exit(1)

    if json_output:
        _json_echo({"device_sns": sns})
        return

    if not sns:
        click.echo("No device log files found.")
        return

    click.secho(f"Devices with log files ({len(sns)}):", bold=True)
    for sn in sorted(sns):
        summary = log_reader.summarize_device(sn)
        click.echo(f"  {sn:<30} ({summary.total_events} events)")
        if summary.last_seen:
            click.echo(f"  {'':<30}  Last: {_format_timestamp(summary.last_seen)}")


@logs.command("dates")
@_server_options
@_json_option
def logs_dates(host: str, port: int, json_output: bool) -> None:
    """List dates for which log files exist."""
    log_reader = _get_log_reader()
    dates = log_reader.available_dates()

    if json_output:
        _json_echo({"dates": dates})
        return

    if not dates:
        click.echo("No log date directories found.")
        return

    click.echo("Available log dates:")
    for d in sorted(dates, reverse=True):
        click.echo(f"  {d}")


@logs.command("search")
@click.argument("event_type")
@click.option("--data-contains", "-c", default=None,
              help="Filter by substring in receive/send data.")
@_server_options
@_json_option
def logs_search(
    event_type: str,
    data_contains: Optional[str],
    host: str,
    port: int,
    json_output: bool,
) -> None:
    """Find devices that have a specific event type in their logs."""
    log_reader = _get_log_reader()
    try:
        sns = log_reader.find_device_by_event(event_type, data_substring=data_contains)
    except Exception as e:
        click.secho(f"Error searching logs: {e}", fg="red", err=True)
        sys.exit(1)

    if json_output:
        _json_echo({"event_type": event_type, "matching_devices": sns})
        return

    if not sns:
        click.echo(f"No devices found with event '{event_type}'.")
        return

    click.echo(f"Devices with event '{event_type}': {len(sns)}")
    for sn in sorted(sns):
        click.echo(f"  {sn}")


# ===========================================================================
# SERVER
# ===========================================================================

@cli.group()
def server() -> None:
    """Server-level operations and diagnostics."""


@server.command("ping")
@_server_options
@_json_option
def server_ping(host: str, port: int, json_output: bool) -> None:
    """Check if the Netty HTTP command API is reachable."""
    client = NettyHttpClient(host=host, port=port)
    try:
        # The debug endpoint is the cheapest GET call
        online = client.list_online_devices()
        click.secho(f"✓ Server at {host}:{port} is reachable", fg="green")
        if json_output:
            _json_echo({"host": host, "port": port, "reachable": True, "online_count": len(online)})
    except NettyServerError as e:
        click.secho(f"✗ Server at {host}:{port} is NOT reachable: {e}", fg="red")
        if json_output:
            _json_echo({"host": host, "port": port, "reachable": False, "error": str(e)})
        sys.exit(1)


@server.command("config")
@_server_options
@_json_option
def server_config(host: str, port: int, json_output: bool) -> None:
    """Show current server connection configuration."""
    cfg = {
        "host": host,
        "port": port,
        "api_base": f"http://{host}:{port}",
    }

    if json_output:
        _json_echo(cfg)
        return

    click.secho("Server Configuration:", bold=True)
    click.echo(f"  Host: {cfg['host']}")
    click.echo(f"  Port: {cfg['port']}")
    click.echo(f"  API:  {cfg['api_base']}")


@server.command("connect")
@click.argument("hostname")
@click.argument("port", type=int)
def server_connect(hostname: str, port: int) -> None:
    """Set the target Netty server host and port for this session."""
    _session_mgr.set_server(hostname, port)
    click.secho(f"✓ Connected to {hostname}:{port}", fg="green")


# ===========================================================================
# SESSION
# ===========================================================================

@cli.group()
def session() -> None:
    """Manage interactive session state."""


@session.command("show")
@_json_option
def session_show(json_output: bool) -> None:
    """Display current session state."""
    s = _session_mgr.session
    state = {
        "host": s.host,
        "port": s.port,
        "current_sn": s.current_sn,
        "known_devices": s.known_devices,
        "history_count": len(s.history),
        "json_output": s.json_output,
        "can_undo": _session_mgr.can_undo,
        "can_redo": _session_mgr.can_redo,
    }

    if json_output:
        _json_echo(state)
        return

    click.secho("Session State:", bold=True)
    click.echo(f"  Server:        {state['host']}:{state['port']}")
    click.echo(f"  Current SN:    {state['current_sn'] or '(none)'}")
    click.echo(f"  Known devices: {len(state['known_devices'])}")
    click.echo(f"  History:       {state['history_count']} commands")
    click.echo(f"  JSON output:   {'yes' if state['json_output'] else 'no'}")
    click.echo(f"  Undo stack:    {'available' if state['can_undo'] else 'empty'}")
    click.echo(f"  Redo stack:    {'available' if state['can_redo'] else 'empty'}")


@session.command("undo")
def session_undo() -> None:
    """Undo the last session state change."""
    if _session_mgr.undo():
        click.secho("✓ Undo successful", fg="green")
    else:
        click.secho("Nothing to undo.", fg="yellow")


@session.command("redo")
def session_redo() -> None:
    """Redo a previously undone session state change."""
    if _session_mgr.redo():
        click.secho("✓ Redo successful", fg="green")
    else:
        click.secho("Nothing to redo.", fg="yellow")


@session.command("clear")
def session_clear() -> None:
    """Clear session history."""
    _session_mgr.clear_history()
    click.secho("✓ Session history cleared", fg="green")


@session.command("json")
@click.argument("mode", type=click.Choice(["on", "off"]))
def session_json(mode: str) -> None:
    """Enable or disable JSON output mode globally."""
    _session_mgr.set_json_output(mode == "on")
    click.secho(f"✓ JSON output {'enabled' if mode == 'on' else 'disabled'}", fg="green")


# ===========================================================================
# REPL
# ===========================================================================

def _repl() -> None:
    """Interactive REPL loop.

    Commands are the same as the CLI subcommands, typed without the
    ``cli-anything-netty-server`` prefix.  The REPL keeps session state
    (current device, server connection, command history) across calls.
    """
    click.secho("Netty Server CLI — Interactive Mode", bold=True, fg="cyan")
    click.echo(f"  Server: {_session_mgr.session.host}:{_session_mgr.session.port}")
    click.echo("  Type 'help' for commands, 'exit' to quit.")
    click.echo()

    # Build a Click command mapping for REPL dispatch
    command_map: Dict[str, click.Command] = {}
    for group_name, group_cmd in cli.commands.items():
        if isinstance(group_cmd, click.Group):
            for sub_name, sub_cmd in group_cmd.commands.items():
                full_name = f"{group_name} {sub_name}"
                command_map[full_name] = sub_cmd
                command_map[f"{group_name}_{sub_name}"] = sub_cmd

    # Also add first-level groups as standalone commands
    for group_name, group_cmd in cli.commands.items():
        command_map[group_name] = group_cmd

    while True:
        try:
            line = click.prompt("netty", prompt_suffix="> ").strip()
        except (EOFError, KeyboardInterrupt):
            click.echo()
            break

        if not line:
            continue

        if line.lower() in ("exit", "quit", "q"):
            break

        if line.lower() in ("help", "?"):
            _repl_help()
            continue

        parts = line.split()
        # Try to match two-word commands first (e.g. "devices list")
        if len(parts) >= 2:
            two_word = f"{parts[0]} {parts[1]}"
            if two_word in command_map:
                _repl_execute(command_map[two_word], parts[2:])
                continue

        # Single-word commands (e.g. "devices" shows its group help)
        if parts[0] in command_map:
            _repl_execute(command_map[parts[0]], parts[1:])
        else:
            click.secho(f"Unknown command: {line}", fg="red")
            click.echo("Type 'help' for available commands.")


def _repl_help() -> None:
    """Print REPL help."""
    click.secho("\nAvailable Commands:", bold=True)

    groups: Dict[str, List[str]] = {}
    for group_name, group_cmd in cli.commands.items():
        if isinstance(group_cmd, click.Group):
            sub_names = list(group_cmd.commands.keys())
            groups[group_name] = sub_names

    click.echo("\n  Device Management:")
    click.echo("    devices list          List online devices")
    click.echo("    devices status [sn]   Show device(s) online status")
    click.echo("    devices info <sn>     Show device log summary")

    click.echo("\n  Commands:")
    click.echo("    command send <sn> <cmd> [--data JSON]")
    click.echo("    command detail <sn>")
    click.echo("    command force <sn> <n>")
    click.echo("    command rent <sn> <n>")
    click.echo("    command return <sn> <n>")
    click.echo("    command custom <sn> <json_data>")

    click.echo("\n  Logs:")
    click.echo("    logs show <sn> [--date YYYY-MM-DD] [--event TYPE] [--limit N]")
    click.echo("    logs list-devices")
    click.echo("    logs dates")
    click.echo("    logs search <event_type> [--data-contains TEXT]")

    click.echo("\n  Server:")
    click.echo("    server ping")
    click.echo("    server config")
    click.echo("    server connect <host> <port>")

    click.echo("\n  Session:")
    click.echo("    session show")
    click.echo("    session undo / redo")
    click.echo("    session clear")
    click.echo("    session json on|off")

    click.echo("\n  General:")
    click.echo("    exit / quit           Exit REPL")
    click.echo("    help / ?              Show this help")
    click.echo()


def _repl_execute(cmd: click.Command, args: List[str]) -> None:
    """Execute a Click command in REPL context.

    Injects global options from session state where applicable.
    """
    # Build argv that the Click command expects
    argv = list(args)

    # Inject --host / --port if the command accepts them
    accepts_server = any(
        p.name in ("host", "port") for p in cmd.params
    )
    if accepts_server:
        s = _session_mgr.session
        argv.extend(["--host", s.host, "--port", str(s.port)])

    # Inject --json if session has it enabled
    if _session_mgr.session.json_output:
        argv.append("--json")

    try:
        with click.Context(cmd) as ctx:
            cmd.main(args=argv, standalone_mode=False, parent=ctx)
    except SystemExit:
        pass
    except click.ClickException as e:
        click.secho(f"Error: {e.format_message()}", fg="red", err=True)
    except Exception as e:
        click.secho(f"Unexpected error: {e}", fg="red", err=True)
