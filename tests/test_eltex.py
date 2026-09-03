"""Tests for ELTEX plugin."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.plugins.eltex import EltexPlugin
from src.models import VLAN, ACL, NTPEntry, SNMPEntry, Interface, MACEntry, VoiceVLAN, SSHConfig, LLDPConfig


FIXTURES_DIR = Path(__file__).parent / "fixtures" / "eltex"


def _read_fixture(filename: str) -> str:
    path = FIXTURES_DIR / filename
    if not path.exists():
        pytest.skip(f"Fixture not found: {path}")
    return path.read_text(encoding="utf-8", errors="replace")


def test_eltex_plugin_metadata():
    plugin = EltexPlugin()
    assert plugin.name == "eltex"
    assert isinstance(plugin.match_patterns, list)
    assert len(plugin.match_patterns) > 0


def test_eltex_plugin_extract_vlans():
    raw = _read_fixture("mes-2348.cfg")
    plugin = EltexPlugin()
    try:
        vlans = plugin.extract_vlans(raw)
        assert isinstance(vlans, list)
        for v in vlans:
            assert isinstance(v, VLAN)
    except NotImplementedError:
        pytest.skip("ELTEX parser not yet implemented")


def test_eltex_plugin_extract_acls():
    raw = _read_fixture("mes-2348.cfg")
    plugin = EltexPlugin()
    try:
        acls = plugin.extract_acls(raw)
        assert isinstance(acls, list)
        for a in acls:
            assert isinstance(a, ACL)
    except NotImplementedError:
        pytest.skip("ELTEX parser not yet implemented")


def test_eltex_plugin_extract_ntp():
    raw = _read_fixture("mes-2348.cfg")
    plugin = EltexPlugin()
    try:
        ntps = plugin.extract_ntp(raw)
        assert isinstance(ntps, list)
        for n in ntps:
            assert isinstance(n, NTPEntry)
    except NotImplementedError:
        pytest.skip("ELTEX parser not yet implemented")


def test_eltex_plugin_extract_snmp():
    raw = _read_fixture("mes-2348.cfg")
    plugin = EltexPlugin()
    try:
        snmps = plugin.extract_snmp(raw)
        assert isinstance(snmps, list)
        for s in snmps:
            assert isinstance(s, SNMPEntry)
    except NotImplementedError:
        pytest.skip("ELTEX parser not yet implemented")


def test_eltex_plugin_extract_interfaces():
    raw = _read_fixture("mes-2348.cfg")
    plugin = EltexPlugin()
    try:
        interfaces = plugin.extract_interfaces(raw)
        assert isinstance(interfaces, list)
        for i in interfaces:
            assert isinstance(i, Interface)
    except NotImplementedError:
        pytest.skip("ELTEX parser not yet implemented")


def test_eltex_plugin_extract_mac_table():
    raw = _read_fixture("mes-2348.cfg")
    plugin = EltexPlugin()
    try:
        macs = plugin.extract_mac_table(raw)
        assert isinstance(macs, list)
        for m in macs:
            assert isinstance(m, MACEntry)
    except NotImplementedError:
        pytest.skip("ELTEX parser not yet implemented")


def test_eltex_plugin_extract_voice_vlan():
    raw = _read_fixture("mes-2348.cfg")
    plugin = EltexPlugin()
    try:
        voice = plugin.extract_voice_vlan(raw)
        assert isinstance(voice, list)
        for v in voice:
            assert isinstance(v, VoiceVLAN)
    except NotImplementedError:
        pytest.skip("ELTEX parser not yet implemented")


def test_eltex_plugin_extract_ssh():
    raw = _read_fixture("mes-2348.cfg")
    plugin = EltexPlugin()
    try:
        ssh = plugin.extract_ssh(raw)
        assert isinstance(ssh, SSHConfig)
    except NotImplementedError:
        pytest.skip("ELTEX parser not yet implemented")


def test_eltex_plugin_extract_lldp():
    raw = _read_fixture("mes-2348.cfg")
    plugin = EltexPlugin()
    try:
        lldp = plugin.extract_lldp(raw)
        assert isinstance(lldp, LLDPConfig)
    except NotImplementedError:
        pytest.skip("ELTEX parser not yet implemented")