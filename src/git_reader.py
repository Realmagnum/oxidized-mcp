"""Git repository reader for oxidized-mcp.

Reads device configs from a local Git working tree (read-only). Uses:
- `git log -1 --format=%cI -- <path>` for config_date
- `git grep` for fast global regex search across all configs
- direct file reads for individual config inspection

Designed to work with the default Oxidized Git output model
(/srv/oxidized/configs/<group>/<device>) but stays generic.
"""

from __future__ import annotations

import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Tuple


class GitReader:
    """Read-only access to the Oxidized Git config repository."""

    def __init__(self, repo_path: str = "/srv/oxidized/configs"):
        self.repo_path = Path(repo_path).resolve()
        if not self.repo_path.exists():
            raise FileNotFoundError(f"Oxidized repo path not found: {repo_path}")

    def _run_git(self, *args: str, cwd: Optional[Path] = None) -> str:
        """Run a git command and return stdout."""
        cmd = ["git", *args]
        proc = subprocess.run(
            cmd,
            cwd=str(cwd or self.repo_path),
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0 and proc.returncode != 1:
            # git grep returns 1 for no matches; that's expected
            raise RuntimeError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
        return proc.stdout

    def list_devices(self) -> List[Dict[str, str]]:
        """Enumerate all device config files.

        Returns list of {hostname, vendor, group, relative_path}.
        """
        devices = []
        for root, dirs, files in os.walk(self.repo_path):
            for fname in files:
                # skip .git internals
                if ".git" in Path(root).parts:
                    continue
                full_path = Path(root) / fname
                rel_path = full_path.relative_to(self.repo_path)
                # group = parent dir name; hostname = filename without extension
                parts = rel_path.parts
                if len(parts) >= 2:
                    group = parts[-2]
                    hostname = Path(fname).stem
                else:
                    group = "default"
                    hostname = Path(fname).stem
                devices.append({
                    "hostname": hostname,
                    "vendor": "unknown",
                    "group": group,
                    "relative_path": str(rel_path),
                    "full_path": str(full_path),
                })
        return devices

    def read_config(self, relative_path: str) -> str:
        """Read the raw config file."""
        full = self.repo_path / relative_path
        if not full.exists():
            raise FileNotFoundError(f"Config not found: {relative_path}")
        return full.read_text(encoding="utf-8", errors="replace")

    def get_config_date(self, relative_path: str) -> Optional[datetime]:
        """Get the commit date of the last change to this file."""
        try:
            out = self._run_git(
                "log", "-1", "--format=%cI", "--", relative_path
            )
            date_str = out.strip()
            if not date_str:
                return None
            return datetime.fromisoformat(date_str)
        except (RuntimeError, ValueError):
            return None

    def config_age_hours(self, relative_path: str) -> Optional[float]:
        """Age of the config in hours since the last commit."""
        dt = self.get_config_date(relative_path)
        if dt is None:
            return None
        # Force to UTC for comparison
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        delta = now - dt
        return delta.total_seconds() / 3600.0

    def is_stale(self, relative_path: str, threshold_hours: float = 24.0) -> bool:
        """Return True if config is older than threshold."""
        age = self.config_age_hours(relative_path)
        if age is None:
            return False
        return age > threshold_hours

    def raw_grep(
        self,
        pattern: str,
        vendor_filter: Optional[str] = None,
        max_results: int = 100,
    ) -> List[Dict[str, str]]:
        """Run git grep across all configs.

        Returns list of {relative_path, line_number, content}.
        """
        try:
            out = self._run_git(
                "grep", "-n", "-I", "--extended-regexp", pattern
            )
        except RuntimeError:
            return []

        results = []
        for line in out.splitlines():
            if not line:
                continue
            # git grep format: <path>:<lineno>:<content>
            parts = line.split(":", 2)
            if len(parts) < 3:
                continue
            rel_path, lineno, content = parts
            if vendor_filter:
                # naive filter by path containing vendor name
                if vendor_filter.lower() not in rel_path.lower():
                    continue
            results.append({
                "relative_path": rel_path,
                "line_number": lineno,
                "content": content,
            })
            if len(results) >= max_results:
                break
        return results

    def find_devices_by_group(self, group: str) -> List[Dict[str, str]]:
        """Return devices belonging to a specific group."""
        return [d for d in self.list_devices() if d.get("group") == group]
