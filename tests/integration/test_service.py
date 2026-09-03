from __future__ import annotations

from oxidized_mcp.service import OxidizedService


def test_list_devices_filters_vendor_and_includes_freshness(service: OxidizedService) -> None:
    result = service.list_devices(vendor="eltex")
    assert result["ok"]
    assert len(result["devices"]) == 2
    assert {device["vendor"] for device in result["devices"]} == {"eltex"}
    assert all(device["config_date"] for device in result["devices"])
    assert all(device["stale_warning"] for device in result["devices"])


def test_get_device_config_redacts_secrets_by_default(service: OxidizedService) -> None:
    result = service.get_device_config("des-3200")
    assert result["ok"]
    assert result["secrets_redacted"]
    assert "snmp-server community ***REDACTED***" in result["config"]
    assert "snmp-server community public" not in result["config"]


def test_unknown_device_returns_similar_names(service: OxidizedService) -> None:
    from oxidized_mcp.errors import DeviceNotFoundError

    try:
        service.get_device_config("des-3201")
    except DeviceNotFoundError as exc:
        assert "des-3200" in exc.details["similar"]
    else:
        raise AssertionError("DeviceNotFoundError was not raised")


def test_search_vlan_100_across_vendors(service: OxidizedService) -> None:
    result = service.search_across_devices("vlan", "100")
    assert result["ok"]
    assert len(result["hits"]) == 6
    assert {hit["vendor"] for hit in result["hits"]} == {"dlink", "eltex", "snr"}
    assert all(hit["config_date"] for hit in result["hits"])


def test_search_absent_ntp(service: OxidizedService) -> None:
    result = service.search_across_devices("ntp", operator="absent")
    assert result == {"ok": True, "hits": [], "truncated": False}


def test_search_unrestricted_ssh(service: OxidizedService) -> None:
    result = service.search_across_devices("ssh", operator="unrestricted")
    assert len(result["hits"]) == 6
    assert all(hit["details"]["acl_names"] == [] for hit in result["hits"])


def test_get_entity_uses_domain_name_not_internal_method(service: OxidizedService) -> None:
    result = service.get_entity("mes-2348", "vlans")
    assert result["ok"]
    assert "vlans" in result
    assert "extractor" not in result
    assert result["vendor"] == "eltex"


def test_validate_repository(service: OxidizedService) -> None:
    result = service.validate_repository()
    assert result["ok"]
    assert result["device_count"] == 6
    assert result["recognized"] == 6
    assert result["problems"] == []
