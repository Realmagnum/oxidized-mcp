"""Integration tests for MCP tools and GitReader."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.git_reader import GitReader
from src.cache import ConfigCache


# ---------------------------------------------------------------------------
# GitReader tests (uses tests/fixtures as a fake repo)
# ---------------------------------------------------------------------------

def _make_fake_repo(tmp_path: Path) -> Path:
    """Create a minimal git repo with fake Oxidized configs."""
    import subprocess

    repo = tmp_path / "fake-oxidized"
    repo.mkdir()
    # create group dir + config files
    (repo / "dlink").mkdir()
    (repo / "dlink" / "sw-core-01.cfg").write_text("hostname sw-core-01\nvlan 100\n")
    (repo / "dlink" / "sw-core-02.cfg").write_text("hostname sw-core-02\nvlan 200\n")
    (repo / "eltex").mkdir()
    (repo / "eltex" / "sw-access-01.cfg").write_text("hostname sw-access-01\nvlan 100\n")

    # init git
    subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=repo, capture_output=True, check=True)
    subprocess.run(["git", "add", "."], cwd=repo, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=repo, capture_output=True, check=True)
    return repo


def test_git_reader_list_devices(tmp_path):
    repo = _make_fake_repo(tmp_path)
    reader = GitReader(repo_path=str(repo))
    devices = reader.list_devices()
    assert len(devices) == 3
    names = {d["hostname"] for d in devices}
    assert names == {"sw-core-01", "sw-core-02", "sw-access-01"}


def test_git_reader_read_config(tmp_path):
    repo = _make_fake_repo(tmp_path)
    reader = GitReader(repo_path=str(repo))
    content = reader.read_config("dlink/sw-core-01.cfg")
    assert "hostname sw-core-01" in content


def test_git_reader_get_config_date(tmp_path):
    repo = _make_fake_repo(tmp_path)
    reader = GitReader(repo_path=str(repo))
    dt = reader.get_config_date("dlink/sw-core-01.cfg")
    assert dt is not None


def test_git_reader_config_age_hours(tmp_path):
    repo = _make_fake_repo(tmp_path)
    reader = GitReader(repo_path=str(repo))
    age = reader.config_age_hours("dlink/sw-core-01.cfg")
    assert age is not None
    assert age < 1  # just committed, should be < 1 hour


def test_git_reader_is_stale(tmp_path):
    repo = _make_fake_repo(tmp_path)
    reader = GitReader(repo_path=str(repo))
    assert not reader.is_stale("dlink/sw-core-01.cfg", threshold_hours=1.0)


def test_git_reader_raw_grep(tmp_path):
    repo = _make_fake_repo(tmp_path)
    reader = GitReader(repo_path=str(repo))
    matches = reader.raw_grep("vlan")
    assert len(matches) >= 3


def test_git_reader_find_devices_by_group(tmp_path):
    repo = _make_fake_repo(tmp_path)
    reader = GitReader(repo_path=str(repo))
    dlink_devices = reader.find_devices_by_group("dlink")
    assert len(dlink_devices) == 2
    eltex_devices = reader.find_devices_by_group("eltex")
    assert len(eltex_devices) == 1


# ---------------------------------------------------------------------------
# Cache tests
# ---------------------------------------------------------------------------

def test_cache_get_set():
    cache = ConfigCache(ttl_seconds=60)
    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"
    assert cache.size() == 1


def test_cache_invalidate():
    cache = ConfigCache(ttl_seconds=60)
    cache.set("key1", "value1")
    cache.invalidate("key1")
    assert cache.get("key1") is None
    assert cache.size() == 0


def test_cache_clear():
    cache = ConfigCache(ttl_seconds=60)
    cache.set("key1", "value1")
    cache.set("key2", "value2")
    cache.clear()
    assert cache.size() == 0


def test_cache_ttl_expiry():
    cache = ConfigCache(ttl_seconds=0)
    cache.set("key1", "value1")
    # TTL=0 → immediately stale
    assert cache.get("key1") is None


# ---------------------------------------------------------------------------
# Plugin registry tests
# ---------------------------------------------------------------------------

def test_plugin_registry_loads():
    from src.plugins import list_plugins, get_plugin_by_name
    plugins = list_plugins()
    assert "dlink" in plugins
    assert "eltex" in plugins
    assert "snr" in plugins


def test_plugin_registry_get_by_name():
    from src.plugins import get_plugin_by_name
    plugin = get_plugin_by_name("dlink")
    assert plugin is not None
    assert plugin.name == "dlink"


def test_plugin_registry_get_for_path():
    from src.plugins import get_plugin_for_path
    plugin = get_plugin_for_path("dlink/sw-core-01.cfg")
    assert plugin is not None
    assert plugin.name == "dlink"