"""Read-only adapter for an Oxidized Git working tree."""

from __future__ import annotations

import shutil
import subprocess  # nosec B404
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from .errors import ConfigDateError, QueryValidationError, RepositoryError


@dataclass(frozen=True, slots=True)
class ConfigFile:
    hostname: str
    group: str | None
    relative_path: str
    full_path: Path
    mtime_ns: int
    size: int


@dataclass(frozen=True, slots=True)
class Freshness:
    config_date: datetime
    age_hours: float
    stale: bool


@dataclass(frozen=True, slots=True)
class GrepMatch:
    relative_path: str
    line_number: int
    content: str


class GitReader:
    """All filesystem and Git access is contained in this class."""

    def __init__(
        self,
        repository_path: str | Path,
        *,
        timeout_seconds: float = 5.0,
        max_regex_length: int = 512,
    ) -> None:
        self.repository_path = Path(repository_path).expanduser().resolve()
        self.timeout_seconds = timeout_seconds
        self.max_regex_length = max_regex_length
        git_executable = shutil.which("git")
        if git_executable is None:
            raise RepositoryError("git executable was not found in PATH")
        self.git_executable: str = git_executable
        self._validate_repository()

    def _validate_repository(self) -> None:
        if not self.repository_path.is_dir():
            raise RepositoryError(
                "Oxidized repository directory does not exist",
                details={"repository_path": str(self.repository_path)},
            )
        result = self._run_git("rev-parse", "--is-inside-work-tree", allow_no_match=False)
        if result.strip() != "true":
            raise RepositoryError("Configured path is not a Git working tree")

    def _run_git(self, *args: str, allow_no_match: bool = False) -> str:
        try:
            # Fixed executable, argv list, shell=False; user regex follows Git's `--`.
            process = subprocess.run(  # nosec B603
                [self.git_executable, "-c", f"safe.directory={self.repository_path}", *args],
                cwd=self.repository_path,
                capture_output=True,
                text=True,
                check=False,
                timeout=self.timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            raise RepositoryError(
                "Git command timed out",
                details={"operation": args[0] if args else "unknown"},
            ) from exc
        if process.returncode == 1 and allow_no_match:
            return ""
        if process.returncode != 0:
            raise RepositoryError(
                "Git operation failed",
                details={
                    "operation": args[0] if args else "unknown",
                    "stderr": process.stderr.strip()[:500],
                },
            )
        return process.stdout

    def _contained_path(self, relative_path: str) -> Path:
        candidate = (self.repository_path / relative_path).resolve()
        try:
            candidate.relative_to(self.repository_path)
        except ValueError as exc:
            raise RepositoryError(
                "Config path escapes the repository",
                details={"relative_path": relative_path},
            ) from exc
        return candidate

    def list_configs(self) -> list[ConfigFile]:
        """Return tracked config files only; Git metadata and untracked files are excluded."""
        paths = self._run_git("ls-files", "-z").split("\0")
        configs: list[ConfigFile] = []
        for relative_path in paths:
            if not relative_path:
                continue
            full_path = self._contained_path(relative_path)
            if not full_path.is_file():
                continue
            stat = full_path.stat()
            posix = PurePosixPath(relative_path)
            configs.append(
                ConfigFile(
                    hostname=posix.stem,
                    group=posix.parent.name if posix.parent != PurePosixPath(".") else None,
                    relative_path=relative_path,
                    full_path=full_path,
                    mtime_ns=stat.st_mtime_ns,
                    size=stat.st_size,
                )
            )
        return sorted(configs, key=lambda item: item.hostname.casefold())

    def read_config(self, config: ConfigFile | str) -> str:
        relative_path = config.relative_path if isinstance(config, ConfigFile) else config
        path = self._contained_path(relative_path)
        if not path.is_file():
            raise RepositoryError("Config file does not exist", details={"relative_path": relative_path})
        return path.read_text(encoding="utf-8", errors="replace")

    def freshness(self, relative_path: str, *, stale_threshold_hours: float) -> Freshness:
        output = self._run_git("log", "-1", "--format=%cI", "--", relative_path).strip()
        if not output:
            raise ConfigDateError(
                "Tracked config has no commit date",
                details={"relative_path": relative_path},
            )
        try:
            config_date = datetime.fromisoformat(output)
        except ValueError as exc:
            raise ConfigDateError(
                "Git returned an invalid config date",
                details={"relative_path": relative_path, "value": output},
            ) from exc
        if config_date.tzinfo is None:
            config_date = config_date.replace(tzinfo=UTC)
        age_hours = max(0.0, (datetime.now(UTC) - config_date.astimezone(UTC)).total_seconds() / 3600)
        return Freshness(config_date=config_date, age_hours=age_hours, stale=age_hours > stale_threshold_hours)

    def grep(self, pattern: str, *, max_results: int) -> list[GrepMatch]:
        if not pattern or len(pattern) > self.max_regex_length:
            raise QueryValidationError(
                "Regex length is outside the allowed range",
                details={"max_regex_length": self.max_regex_length},
            )
        try:
            output = self._run_git(
                "grep",
                "-n",
                "-I",
                "--extended-regexp",
                "--",
                pattern,
                allow_no_match=True,
            )
        except RepositoryError as exc:
            if "Invalid" in str(exc.details.get("stderr", "")):
                raise QueryValidationError("Invalid regular expression") from exc
            raise
        matches: list[GrepMatch] = []
        for line in output.splitlines():
            parts = line.split(":", 2)
            if len(parts) != 3:
                continue
            relative_path, line_number, content = parts
            matches.append(GrepMatch(relative_path, int(line_number), content))
            if len(matches) >= max_results:
                break
        return matches

    def status(self) -> dict[str, object]:
        return {
            "repository_path": str(self.repository_path),
            "inside_work_tree": True,
            "head": self._run_git("rev-parse", "HEAD").strip(),
            "device_count": len(self.list_configs()),
        }
