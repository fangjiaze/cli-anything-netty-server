"""
Log reader for the Netty Server's per-device log system.

Logs are stored in two locations:
  - ``log/<YYYY-MM-DD>/<SN>.log`` — date-partitioned logs (rich format)
  - ``log/<SN>.log`` — flat (legacy) format

Each log entry contains:
  - Timestamp
  - Client ID / IP
  - Event type (login, heart, detailup, detail, disconnect, send, etc.)
  - Received data (JSON)
  - Sent data (JSON)
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Optional, Iterator


@dataclass
class LogEntry:
    """A single log entry for a device event."""
    timestamp: datetime
    client_id: str = ""
    client_ip: str = ""
    event_type: str = ""
    receive_data: str = ""
    send_data: str = ""
    raw_lines: List[str] = field(default_factory=list)


@dataclass
class DeviceLogSummary:
    """Summary statistics for a device's log."""
    sn: str
    total_events: int = 0
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    event_counts: Dict[str, int] = field(default_factory=dict)


class LogReader:
    """Reads and parses Netty Server device logs.

    Parameters
    ----------
    log_dir : str or Path
        Root log directory (defaults to the server's *log/* directory).
        Override by passing a custom path.
    """

    TIMESTAMP_RE = re.compile(
        r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}$"
    )
    CLIENT_RE = re.compile(
        r"^client_id:(?P<client_id>[^,]+),\s*IP:(?P<ip>[^,]+),\s*type:(?P<type>\w+)$"
    )
    EVENT_RE = re.compile(r"^event:(?P<event>.+)$")
    RECEIVE_RE = re.compile(r"^receive:(?P<data>.*)$")
    SEND_RE = re.compile(r"^send:(?P<data>.*)$")

    def __init__(self, log_dir: Optional[os.PathLike] = None):
        if log_dir is not None:
            self._base = Path(log_dir).resolve()
        else:
            # Try to find the log directory relative to the harness location
            # Default: look for a "log" directory next to the project
            self._base = Path("log").resolve()

    # ------------------------------------------------------------------
    # Path resolution helpers
    # ------------------------------------------------------------------

    def _resolve_log_file(self, sn: str, log_date: Optional[date] = None) -> Path:
        """Return the path to a device's log file for a given date."""
        if log_date is not None:
            date_str = log_date.strftime("%Y-%m-%d")
            return self._base / date_str / f"{sn}.log"
        # Flat (legacy) log
        return self._base / f"{sn}.log"

    def available_dates(self) -> List[str]:
        """List all date directories under the log root."""
        if not self._base.exists():
            return []
        return sorted(
            d.name
            for d in self._base.iterdir()
            if d.is_dir() and self.TIMESTAMP_RE.match(d.name + " 00:00:00")
        )

    def available_device_sns(self) -> List[str]:
        """Scan log files across all date dirs and return unique device SNs."""
        sns: set[str] = set()
        if not self._base.exists():
            return []
        # Check date-partitioned
        for d in self._base.iterdir():
            if d.is_dir():
                for f in d.iterdir():
                    if f.suffix == ".log":
                        sns.add(f.stem)
        # Check flat logs
        for f in self._base.iterdir():
            if f.is_file() and f.suffix == ".log":
                sns.add(f.stem)
        return sorted(sns)

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def parse_log_file(self, path: Path) -> List[LogEntry]:
        """Parse a single log file into a list of LogEntry objects."""
        if not path.exists():
            return []

        entries: List[LogEntry] = []
        current: Optional[LogEntry] = None
        buffer: List[str] = []

        def _flush():
            nonlocal current, buffer
            if current is not None:
                current.raw_lines = list(buffer)
                entries.append(current)
                current = None
                buffer = []

        try:
            text = path.read_text("utf-8", errors="replace")
        except OSError:
            return []

        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                _flush()
                continue

            ts_match = self.TIMESTAMP_RE.match(stripped)
            if ts_match:
                _flush()
                try:
                    ts = datetime.strptime(stripped, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    ts = datetime.min
                current = LogEntry(timestamp=ts)
                buffer.append(stripped)
                continue

            if current is None:
                continue

            buffer.append(stripped)

            client_match = self.CLIENT_RE.match(stripped)
            if client_match:
                current.client_id = client_match.group("client_id")
                current.client_ip = client_match.group("ip")
                continue

            event_match = self.EVENT_RE.match(stripped)
            if event_match:
                current.event_type = event_match.group("event")
                continue

            recv_match = self.RECEIVE_RE.match(stripped)
            if recv_match:
                current.receive_data = recv_match.group("data")
                continue

            send_match = self.SEND_RE.match(stripped)
            if send_match:
                current.send_data = send_match.group("data")
                continue

        _flush()
        return entries

    def get_device_logs(
        self,
        sn: str,
        log_date: Optional[date] = None,
    ) -> List[LogEntry]:
        """Return parsed log entries for a device.

        Parameters
        ----------
        sn : str
            Device serial number.
        log_date : date or None
            Specific date; if None, checks the flat legacy log.
        """
        path = self._resolve_log_file(sn, log_date)
        return self.parse_log_file(path)

    def get_device_logs_all_dates(self, sn: str) -> Dict[str, List[LogEntry]]:
        """Return log entries for a device, grouped by date string."""
        result: Dict[str, List[LogEntry]] = {}
        # Flat legacy
        flat_path = self._resolve_log_file(sn, None)
        if flat_path.exists():
            result["legacy"] = self.parse_log_file(flat_path)
        # Date-partitioned
        for d in sorted(self.available_dates()):
            try:
                dt = datetime.strptime(d, "%Y-%m-%d").date()
            except ValueError:
                continue
            path = self._resolve_log_file(sn, dt)
            if path.exists():
                entries = self.parse_log_file(path)
                if entries:
                    result[d] = entries
        return result

    def summarize_device(self, sn: str) -> DeviceLogSummary:
        """Build a summary for the given device across all logs."""
        summary = DeviceLogSummary(sn=sn)
        for date_str, entries in self.get_device_logs_all_dates(sn).items():
            for e in entries:
                summary.total_events += 1
                summary.event_counts[e.event_type] = (
                    summary.event_counts.get(e.event_type, 0) + 1
                )
                if summary.first_seen is None or e.timestamp < summary.first_seen:
                    summary.first_seen = e.timestamp
                if summary.last_seen is None or e.timestamp > summary.last_seen:
                    summary.last_seen = e.timestamp
        return summary

    # ------------------------------------------------------------------
    # High-level queries
    # ------------------------------------------------------------------

    def recent_events(
        self,
        sn: str,
        event_type: Optional[str] = None,
        limit: int = 20,
    ) -> List[LogEntry]:
        """Return the most recent log entries for a device.

        Parameters
        ----------
        sn : str
            Device serial number.
        event_type : str or None
            If set, filter to a specific event type (login, heart, detailup, etc.).
        limit : int
            Maximum number of entries to return (newest first).
        """
        all_entries: List[LogEntry] = []
        for entries in self.get_device_logs_all_dates(sn).values():
            all_entries.extend(entries)

        all_entries.sort(key=lambda e: e.timestamp, reverse=True)

        if event_type:
            all_entries = [e for e in all_entries if e.event_type == event_type]

        return all_entries[:limit]

    def find_device_by_event(
        self,
        event_type: str,
        data_substring: Optional[str] = None,
    ) -> List[str]:
        """Find device SNs that have a particular event type.

        Optionally filter by a substring in receive or send data.
        """
        matches: set[str] = set()
        for sn in self.available_device_sns():
            summary = self.summarize_device(sn)
            if event_type not in summary.event_counts:
                continue
            if data_substring:
                for entries in self.get_device_logs_all_dates(sn).values():
                    for e in entries:
                        if e.event_type != event_type:
                            continue
                        if (data_substring in e.receive_data
                                or data_substring in e.send_data):
                            matches.add(sn)
                            break
                    if sn in matches:
                        break
            else:
                matches.add(sn)
        return sorted(matches)
