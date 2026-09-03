from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from oxidized_mcp.errors import RepositoryError
from oxidized_mcp.git_reader import GitReader


def test_list_configs_and_mandatory_stale_date(oxidized_repo: Path) -> None:
    reader = GitReader(oxidized_repo)
    configs = reader.list_configs()
    assert len(configs) == 6
    freshness = reader.freshness(configs[0].relative_path, stale_threshold_hours=24)
    assert freshness.config_date is not None
    assert freshness.age_hours >= 47
    assert freshness.stale


def test_list_configs_preserves_ipv4_style_hostname(oxidized_repo: Path) -> None:
    source = oxidized_repo / "dlink" / "dgs-3630.cfg"
    target = oxidized_repo / "sw-10.90.90.13"
    source.rename(target)
    subprocess.run(["git", "add", "-A"], cwd=oxidized_repo, check=True)
    subprocess.run(["git", "commit", "-qm", "rename fixture"], cwd=oxidized_repo, check=True)

    reader = GitReader(oxidized_repo)
    configs = reader.list_configs()
    assert "sw-10.90.90.13" in [item.hostname for item in configs]


def test_raw_grep_is_bounded(oxidized_repo: Path) -> None:
    reader = GitReader(oxidized_repo)
    hits = reader.grep("vlan", max_results=3)
    assert len(hits) == 3
    assert all(hit.line_number > 0 for hit in hits)


def test_read_config_rejects_path_traversal(oxidized_repo: Path) -> None:
    reader = GitReader(oxidized_repo)
    with pytest.raises(RepositoryError, match="escapes"):
        reader.read_config("../../etc/passwd")
