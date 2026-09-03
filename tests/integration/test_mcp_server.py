from __future__ import annotations

from oxidized_mcp.server import OxidizedMCPServer
from oxidized_mcp.service import OxidizedService


def test_server_registers_phase_one_and_improvement_tools(service: OxidizedService) -> None:
    server = OxidizedMCPServer(service)
    names = {tool.name for tool in server.mcp._tool_manager.list_tools()}
    assert {
        "list_devices",
        "get_device_config",
        "get_device_vlans",
        "get_device_acls",
        "get_device_ntp",
        "get_device_snmp",
        "get_device_interfaces",
        "get_device_lldp",
        "get_device_mac_table",
        "get_device_voice_vlan",
        "get_device_ssh",
        "search_across_devices",
        "raw_search",
        "get_device_routing",
        "get_device_freshness",
        "validate_repository",
    } == names


def test_server_converts_domain_error_to_stable_envelope(service: OxidizedService) -> None:
    server = OxidizedMCPServer(service)
    result = server._execute(lambda: service.get_device_config("unknown-switch"))
    assert result["ok"] is False
    assert result["error_code"] == "device_not_found"
    assert "similar" in result["details"]
