"""MCP stdio adapter for OxidizedService."""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from mcp.server.mcpserver import MCPServer

from .config import Settings
from .errors import OxidizedMCPError
from .git_reader import GitReader
from .oxidized_rest import OxidizedRestReader
from .plugins import PluginRegistry
from .service import OxidizedService

logger = logging.getLogger(__name__)


class OxidizedMCPServer:
    """Composition root and MCP tool registry."""

    def __init__(self, service: OxidizedService) -> None:
        self.service = service
        self.mcp = MCPServer(
            name="oxidized-mcp",
            title="Oxidized Configuration Search",
            description="Read-only structured search over current network-device configs stored by Oxidized in Git.",
        )
        self._register_tools()

    @staticmethod
    def _execute(call: Callable[[], dict[str, Any]]) -> dict[str, Any]:
        try:
            return call()
        except OxidizedMCPError as exc:
            return {"ok": False, "error_code": exc.code, "message": str(exc), "details": exc.details}
        except Exception:
            logger.exception("unexpected_tool_error")
            return {
                "ok": False,
                "error_code": "operation_failed",
                "message": "Operation failed; inspect server stderr logs.",
                "details": {},
            }

    def _register_tools(self) -> None:
        @self.mcp.tool(
            description=(
                "List Oxidized devices with hostname, detected vendor, group, management IP and mandatory Git config_date. "
                "Optional vendor and group filters are exact. Example: list_devices(vendor='eltex'). "
                "Use for fleet overview; do not use for searching configuration entities."
            )
        )
        def list_devices(vendor: str | None = None, group: str | None = None) -> dict[str, Any]:
            return self._execute(lambda: self.service.list_devices(vendor, group))

        @self.mcp.tool(
            description=(
                "Return a device's complete current Oxidized config plus config_date. Secrets are redacted by default. "
                "Set include_secrets=true only when the user explicitly needs exact credentials or hashes. "
                "Use dedicated entity tools for compact answers. Example: get_device_config(hostname='sw-core-01')."
            )
        )
        def get_device_config(hostname: str, include_secrets: bool = False) -> dict[str, Any]:
            return self._execute(lambda: self.service.get_device_config(hostname, include_secrets))

        @self.mcp.tool(
            description="Return only config_date, age and stale_warning for one device. Example: get_device_freshness(hostname='sw-access-15')."
        )
        def get_device_freshness(hostname: str) -> dict[str, Any]:
            return self._execute(lambda: self.service.get_device_freshness(hostname))

        entity_tools = {
            "get_device_vlans": ("vlans", "Return normalized VLAN IDs, names and tagged/untagged ports."),
            "get_device_acls": ("acls", "Return normalized ACLs, ordered permit/deny rules, direction and port bindings."),
            "get_device_ntp": ("ntp", "Return configured NTP servers and source interface/address."),
            "get_device_snmp": ("snmp", "Return normalized SNMP communities, users and manager hosts. Treat community names as sensitive."),
            "get_device_interfaces": ("interfaces", "Return interfaces with description, enabled state, VLAN mode and VLAN membership."),
            "get_device_routing": ("routing", "Return static routes and default gateway in normalized form."),
            "get_device_lldp": ("lldp", "Return LLDP global state, timers and per-port enable lists."),
            "get_device_mac_table": ("mac_table", "Return configured static MAC entries with VLAN and port."),
            "get_device_voice_vlan": ("voice_vlan", "Return Voice VLAN ID, mode, ports and priority."),
            "get_device_ssh": ("ssh", "Return SSH server status, version, users, keys and ACL restrictions."),
        }
        for tool_name, (entity, summary) in entity_tools.items():
            self._register_entity_tool(tool_name, entity, summary)

        @self.mcp.tool(
            description=(
                "Search normalized entities across all devices. entity: vlan|acl|ntp|snmp|interface|route|lldp|mac|voice_vlan|ssh. "
                "operator: equals|contains|present|absent|unrestricted. equals/contains require value; unrestricted is SSH-only. "
                "Examples: search_across_devices(entity='vlan', value='100'); search_across_devices(entity='ntp', operator='absent'); "
                "search_across_devices(entity='ssh', operator='unrestricted'). Prefer this over raw_search."
            )
        )
        def search_across_devices(
            entity: str,
            value: str | None = None,
            vendor: str | None = None,
            operator: str = "equals",
        ) -> dict[str, Any]:
            return self._execute(lambda: self.service.search_across_devices(entity, value, vendor, operator))

        @self.mcp.tool(
            description=(
                "Run bounded POSIX extended regex git grep over tracked configs. Optional vendor filter is based on plugin detection, "
                "not path text. Use only when structured tools cannot express the query. Example: raw_search(regex='storm-control|loopdetect', vendor='dlink')."
            )
        )
        def raw_search(regex: str, vendor: str | None = None, max_results: int | None = None) -> dict[str, Any]:
            return self._execute(lambda: self.service.raw_search(regex, vendor, max_results))

        @self.mcp.tool(
            description=(
                "Validate the configured Oxidized Git repository, mandatory config dates and vendor recognition. "
                "Use after deployment or when tools return incomplete inventory."
            )
        )
        def validate_repository() -> dict[str, Any]:
            return self._execute(self.service.validate_repository)

        if self.service.rest_reader is not None:
            @self.mcp.tool(
                description=(
                    "Return live Oxidized inventory and last backup result via the optional read-only GET /nodes.json API. "
                    "This is operational telemetry, not Git config freshness; it never triggers a backup and excludes inventory vars."
                )
            )
            def list_oxidized_nodes() -> dict[str, Any]:
                return self._execute(self.service.list_oxidized_nodes)

    def _register_entity_tool(self, name: str, entity: str, summary: str) -> None:
        description = f"{summary} Includes vendor, mandatory config_date, config_age_hours and stale_warning. Input: hostname."

        def tool(hostname: str) -> dict[str, Any]:
            return self._execute(lambda: self.service.get_entity(hostname, entity))

        tool.__name__ = name
        tool.__annotations__ = {"hostname": str, "return": dict[str, Any]}
        self.mcp.tool(name=name, description=description)(tool)

    def run(self) -> None:
        self.mcp.run(transport="stdio")


def build_server(settings: Settings) -> OxidizedMCPServer:
    reader = GitReader(
        settings.repository_path,
        timeout_seconds=settings.git_timeout_seconds,
        max_regex_length=settings.max_regex_length,
    )
    service = OxidizedService(
        reader,
        PluginRegistry(),
        cache_ttl_seconds=settings.cache_ttl_seconds,
        stale_threshold_hours=settings.stale_threshold_hours,
        max_search_results=settings.max_search_results,
        redact_secrets_by_default=settings.redact_secrets_by_default,
        rest_reader=(
            OxidizedRestReader(
                settings.oxidized_rest_base_url,
                timeout_seconds=settings.oxidized_rest_timeout_seconds,
                cache_ttl_seconds=settings.oxidized_rest_cache_ttl_seconds,
            )
            if settings.oxidized_rest_enabled
            else None
        ),
    )
    return OxidizedMCPServer(service)


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only Oxidized configuration MCP server")
    parser.add_argument("--repository", type=Path, help="Override OXIDIZED_CONFIG_PATH")
    parser.add_argument("--check", action="store_true", help="Validate repository and exit")
    args = parser.parse_args()
    settings = Settings.from_env()
    if args.repository:
        settings = settings.model_copy(update={"repository_path": args.repository})
    try:
        server = build_server(settings)
        if args.check:
            result = server.service.validate_repository()
            print(result)
            raise SystemExit(0 if result["ok"] else 1)
        server.run()
    except OxidizedMCPError as exc:
        print(f"oxidized-mcp startup failed [{exc.code}]: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
