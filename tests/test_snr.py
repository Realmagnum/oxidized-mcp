"""Tests for SNR plugin."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.plugins.snr import SNRPlugin
from src.models import VLAN, ACL, NTPEntry, SNMPEntry, Interface, MACEntry, VoiceVLAN, SSHConfig, LLDPConfig


FIXTURES_DIR = Path(__file__).parent / "fixtures" / "snr"


def _read_fixture(filename: str) -> str:
    path = FIXTURES_DIR / filename
    if not path.exists():
        pytest.skip(f"Fixture not found: {path}")
    return path.read_text(encoding="utf-8", errors="replace")


def test_snr_plugin_metadata():
    plugin = SNRPlugin()
    assert plugin.name == "snr"
    assert isinstance(plugin.match_patterns, list)
    assert len(plugin.match_patterns) > 0


def test_snr_plugin_extract_vlans():
    raw = _read_fixture("snr-s2950.cfg")
    plugin = SNRPlugin()
    try:
        vlans = plugin.extract_vlans(raw)
        assert isinstance(vlans, list)
        for v in vlans:
            assert isinstance(v, VLAN)
    except NotImplementedError:
        pytest.skip("SNR parser not yet implemented")


def test_snr_plugin_extract_acls():
    raw = _read_fixture("snr-s2950.cfg")
    plugin = SNRPlugin()
    try:
        acls = plugin.extract_acls(raw)
        assert isinstance(acls, list)
        for a in acls:
            assert isinstance(a, ACL)
    except NotImplementedError:
        pytest.skip("SNR parser not yet implemented")


def test_snr_plugin_extract_ntp():
    raw = _read_fixture("snr-s2950.cfg")
    plugin = SNRPlugin()
    try:
        ntps = plugin.extract_ntp(raw)
        assert isinstance(ntps, list)
        for n in ntps:
            assert isinstance(n, NTPEntry)
    except NotImplementedError:
        pytest.skip("SNR parser not yet implemented")


def test_snr_plugin_extract_snmp():
    raw = _read_fixture("snr-s2950.cfg")
    plugin = SNRPlugin()
    try:
        snmps = plugin.extract_snmp(raw)
        assert isinstance(snmps, list)
        for s in snmps:
            assert isinstance(s, SNMPEntry)
    except NotImplementedError:
        pytest.skip("SNR parser not yet implemented")


def test_snr_plugin_extract_interfaces():
    raw = _read_fixture("snr-s2950.cfg")
    plugin = SNRPlugin()
    try:
        interfaces = plugin.extract_interfaces(raw)
        assert isinstance(interfaces, list)
        for i in interfaces:
            assert isinstance(i, Interface)
    except NotImplementedError:
        pytest.skip("SNR parser not yet implemented")


def test_snr_plugin_extract_mac_table():
    raw = _read_fixture("snr-s2950.cfg")
    plugin = SNRPlugin()
    try:
        macs = plugin.extract_mac_table(raw)
        assert isinstance(macs, list)
        for m in macs:
            assert isinstance(m, MACEntry)
    except NotImplementedError:
        pytest.skip("SNR parser not yet implemented")


def test_snr_plugin_extract_voice_vlan():
    raw = _read_fixture("snr-s2950.cfg")
    plugin = SNRPlugin()
    try:
        voice = plugin.extract_voice_vlan(raw)
        assert isinstance(voice, list)
        for v in voice:
            assert isinstance(v, VoiceVLAN)
    except NotImplementedError:
        pytest.skip("SNR parser not yet implemented")


def test_snr_plugin_extract_ssh():
    raw = _read_fixture("snr-s2950.cfg")
    plugin = SNRPlugin()
    try:
        ssh = plugin.extract_ssh(raw)
        assert isinstance(ssh, SSHConfig)
    except NotImplementedError:
        pytest.skip("SNR parser not yet implemented")


def test_snr_plugin_extract_lldp():
    raw = _read_fixture("snr-s2950.cfg")
    plugin = SNRPlugin()
    try:
        lldp = plugin.extract_lldp(raw)
        assert isinstance(lldp, LLDPConfig)
    except NotImplementedError:
        pytest.skip("SNR parser not yet implemented")