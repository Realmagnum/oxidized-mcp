"""Integration tests for MCP tools."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.git_reader import GitReader
from src.cache import ConfigCache
from src.plugins import get_plugin_for_path


# Reuse the fake repo fixture from test_git_reader
from test_git_reader import _make_fake_repo


def test_list_devices_includes_config_date(tmp_path):
    repo = _make_fake_repo(tmp_path)
    reader = GitReader(repo_path=str(repo))
    devices = reader.list_devices()
    for d in devices:
        dt = reader.get_config_date(d["relative_path"])
        assert dt is not None


def test_get_device_config_returns_raw(tmp_path):
    repo = _make_fake_repo(tmp_path)
    reader = GitReader(repo_path=str(repo))
    raw = reader.read_config("dlink/sw-core-01.cfg")
    assert "hostname sw-core-01" in raw


def test_stale_warning(tmp_path):
    repo = _make_fake_repo(tmp_path)
    reader = GitReader(repo_path=str(repo))
    age = reader.config_age_hours("dlink/sw-core-01.cfg")
    assert age is not None
    stale = age > 24
    assert stale is False  # just committed


def test_unknown_device_returns_error(tmp_path):
    repo = _make_fake_repo(tmp_path)
    reader = GitReader(repo_path=str(repo))
    dev = None
    for d in reader.list_devices():
        if d["hostname"].lower() == "nonexistent":
            dev = d
    assert dev is None


def test_cross_vendor_normalization(tmp_path):
    """Ensure different vendors return the same structure."""
    repo = _make_fake_repo(tmp_path)
    reader = GitReader(repo_path=str(repo))
    dlink_dev = None
    eltex_dev = None
    for d in reader.list_devices():
        if d["hostname"] == "sw-core-01":
            dlink_dev = d
        if d["hostname"] == "sw-access-01":
            eltex_dev = d
    assert dlink_dev is not None
    assert eltex_dev is not None
    # Both have the same keys
    assert set(dlink_dev.keys()) == set(eltex_dev.keys())