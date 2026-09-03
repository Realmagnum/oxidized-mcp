from __future__ import annotations

import os
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from oxidized_mcp.git_reader import GitReader
from oxidized_mcp.plugins import PluginRegistry
from oxidized_mcp.service import OxidizedService


@pytest.fixture
def fixture_root() -> Path:
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def oxidized_repo(tmp_path: Path, fixture_root: Path) -> Path:
    repo = tmp_path / "oxidized"
    repo.mkdir()
    for vendor in ("dlink", "eltex", "snr"):
        target = repo / vendor
        target.mkdir()
        for source in (fixture_root / vendor).glob("*.cfg"):
            (target / source.name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "oxidized-test"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    old_date = (datetime.now(UTC) - timedelta(hours=48)).isoformat()
    env = {**os.environ, "GIT_AUTHOR_DATE": old_date, "GIT_COMMITTER_DATE": old_date}
    subprocess.run(["git", "commit", "-q", "-m", "fixture configs"], cwd=repo, check=True, env=env)
    return repo


@pytest.fixture
def service(oxidized_repo: Path) -> OxidizedService:
    return OxidizedService(
        GitReader(oxidized_repo),
        PluginRegistry(),
        stale_threshold_hours=24,
        cache_ttl_seconds=300,
        max_search_results=100,
    )
