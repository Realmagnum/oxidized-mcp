from __future__ import annotations

from pathlib import Path

import pytest

from oxidized_mcp.plugins import PluginRegistry


@pytest.mark.parametrize(
    ("vendor", "filename", "hostname"),
    [
        ("dlink", "des-3200.cfg", "des-3200-sw-01"),
        ("dlink", "dgs-3630.cfg", "dgs-3630-sw-02"),
        ("eltex", "mes-2348.cfg", "mes-2348-sw-01"),
        ("eltex", "mes-3528.cfg", "mes-3528-sw-02"),
        ("snr", "snr-s2950.cfg", "snr-s2950-sw-01"),
        ("snr", "snr-s3000.cfg", "snr-s3000-sw-02"),
    ],
)
def test_plugin_parses_fixture(fixture_root: Path, vendor: str, filename: str, hostname: str) -> None:
    raw = (fixture_root / vendor / filename).read_text(encoding="utf-8")
    plugin, detection = PluginRegistry().detect(f"{vendor}/{filename}", raw)
    parsed = plugin.parse_config(raw)

    assert plugin.name == vendor
    assert detection.vendor == vendor
    assert {vlan.id for vlan in parsed.vlans} >= {100, 200}
    assert parsed.ntp[0].address == "10.0.0.100"
    assert any(entry.kind == "community" and entry.name == "public" for entry in parsed.snmp)
    assert parsed.lldp.enabled
    assert parsed.ssh.enabled
    assert parsed.ssh.version == "2"
    assert "admin" in parsed.ssh.allowed_users
    assert parsed.interfaces
    assert parsed.acls


def test_dlink_extracts_ports_static_mac_and_voice_vlan(fixture_root: Path) -> None:
    raw = (fixture_root / "dlink" / "des-3200.cfg").read_text(encoding="utf-8")
    plugin = PluginRegistry().get("dlink")
    parsed = plugin.parse_config(raw)

    vlan100 = next(vlan for vlan in parsed.vlans if vlan.id == 100)
    assert {"1", "2", "3", "6"} <= set(vlan100.untagged_ports)
    assert parsed.mac_table[0].mac == "00:11:22:33:44:55"
    assert parsed.mac_table[0].vlan == 100
    assert parsed.voice_vlans[0].id == 100
    assert parsed.voice_vlans[0].mode == "auto"


def test_snr_interface_vlan_names_are_normalized(fixture_root: Path) -> None:
    raw = (fixture_root / "snr" / "snr-s3000.cfg").read_text(encoding="utf-8")
    parsed = PluginRegistry().get("snr").parse_config(raw)
    names = {vlan.id: vlan.name for vlan in parsed.vlans}
    assert names[100] == "DATA"
    assert names[200] == "VOICE"
    assert next(interface for interface in parsed.interfaces if interface.name == "gigabitethernet 0/1").tagged_vlans == [
        100,
        200,
        300,
        400,
    ]


def test_content_detection_without_vendor_path(fixture_root: Path) -> None:
    raw = (fixture_root / "dlink" / "des-3200.cfg").read_text(encoding="utf-8")
    plugin, detection = PluginRegistry().detect("core/sw-01.cfg", raw)
    assert plugin.name == "dlink"
    assert detection.confidence == "medium"
