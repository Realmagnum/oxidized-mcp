"""MCP server entry point.

Registers all tools from ТЗ §5. Each tool has a rich description for the AI agent
to understand when to call it. Plugin implementations are loaded lazily.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Allow `python -m src.server` from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.server import Server
from mcp.types import Tool, TextContent

from .git_reader import GitReader
from .cache import ConfigCache
from .plugins import get_plugin_for_path, get_plugin_by_name, list_plugins


REPO_PATH = os.environ.get("OXIDIZED_CONFIG_PATH", "/srv/oxidized/configs")
CACHE_TTL = int(os.environ.get("MCP_CACHE_TTL", "300"))
STALE_THRESHOLD_HOURS = float(os.environ.get("MCP_STALE_HOURS", "24"))


server = Server("oxidized-mcp")
git_reader = GitReader(repo_path=REPO_PATH)
config_cache = ConfigCache(ttl_seconds=CACHE_TTL)


def _enrich_device_info(
    rel_path: str,
    vendor: str,
    hostname: str,
) -> Dict[str, Any]:
    """Add config_date / stale_warning to a device response."""
    config_date = git_reader.get_config_date(rel_path)
    age = git_reader.config_age_hours(rel_path)
    return {
        "hostname": hostname,
        "vendor": vendor,
        "relative_path": rel_path,
        "config_date": config_date.isoformat() if config_date else None,
        "config_age_hours": round(age, 1) if age is not None else None,
        "stale_warning": (age or 0) > STALE_THRESHOLD_HOURS,
    }


def _find_device(hostname: str) -> Optional[Dict[str, str]]:
    """Find a device by hostname (case-insensitive). Returns device dict or None."""
    for dev in git_reader.list_devices():
        if dev["hostname"].lower() == hostname.lower():
            return dev
    return None


def _find_similar(hostname: str, limit: int = 5) -> List[str]:
    """Suggest similar hostnames when an exact match is not found."""
    needle = hostname.lower()
    candidates = [d["hostname"] for d in git_reader.list_devices()]
    # simple substring / prefix match
    scored = []
    for c in candidates:
        c_lower = c.lower()
        score = 0
        if c_lower.startswith(needle[:3]):
            score += 2
        if needle in c_lower or c_lower in needle:
            score += 1
        if score:
            scored.append((score, c))
    scored.sort(reverse=True)
    return [c for _, c in scored[:limit]]


def _resolve_vendor(rel_path: str) -> str:
    """Determine vendor from path. Falls back to 'unknown'."""
    plugin = get_plugin_for_path(rel_path)
    return plugin.name if plugin else "unknown"


# ---------------------------------------------------------------------------
# Tool definitions (rich descriptions per ТЗ §6)
# ---------------------------------------------------------------------------

TOOL_LIST_DEVICES = Tool(
    name="list_devices",
    description=(
        "List all devices in the Oxidized repo with metadata.\n\n"
        "Inputs:\n"
        "  - vendor (optional): filter by vendor (dlink, eltex, snr)\n"
        "  - group (optional): filter by Oxidized group (directory name)\n\n"
        "Returns: list of {hostname, vendor, group, relative_path, "
        "config_date, config_age_hours, stale_warning}.\n\n"
        "Use when: you need an overview of the fleet before drilling into "
        "a specific device. NOT for searching by config content."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "vendor": {"type": "string"},
            "group": {"type": "string"},
        },
    },
)

TOOL_GET_DEVICE_CONFIG = Tool(
    name="get_device_config",
    description=(
        "Get the full raw config text of a device.\n\n"
        "Input: hostname (required).\n"
        "Returns: {hostname, vendor, raw_config, config_date, stale_warning}.\n\n"
        "Use when: the user wants to see the whole config or a section that "
        "has no dedicated tool. AVOID for VLAN/ACL/etc. — use the dedicated "
        "tools which return normalized structured data."
    ),
    inputSchema={
        "type": "object",
        "properties": {"hostname": {"type": "string"}},
        "required": ["hostname"],
    },
)

TOOL_GET_DEVICE_VLANS = Tool(
    name="get_device_vlans",
    description=(
        "Get parsed VLANs for a device (normalized across vendors).\n\n"
        "Returns list of {id, name, tagged_ports, untagged_ports}.\n\n"
        "Use when: user asks 'show VLANs on sw-core-01' or 'what VLANs exist'."
    ),
    inputSchema={
        "type": "object",
        "properties": {"hostname": {"type": "string"}},
        "required": ["hostname"],
    },
)

TOOL_GET_DEVICE_ACLS = Tool(
    name="get_device_acls",
    description=(
        "Get parsed ACLs for a device.\n\n"
        "Returns list of {name, direction, bound_ports, rules[]} where each rule "
        "is {action, protocol, source, destination, source_port, dest_port}.\n\n"
        "Use when: user asks about access-lists, traffic filtering, or 'which "
        "ports have ACL X applied'."
    ),
    inputSchema={
        "type": "object",
        "properties": {"hostname": {"type": "string"}},
        "required": ["hostname"],
    },
)

TOOL_GET_DEVICE_NTP = Tool(
    name="get_device_ntp",
    description=(
        "Get NTP server configuration for a device.\n\n"
        "Returns list of {address, source, version}.\n\n"
        "Use when: user asks 'is NTP configured', 'show time servers', or "
        "needs to verify time synchronization sources."
    ),
    inputSchema={
        "type": "object",
        "properties": {"hostname": {"type": "string"}},
        "required": ["hostname"],
    },
)

TOOL_GET_DEVICE_SNMP = Tool(
    name="get_device_snmp",
    description=(
        "Get SNMP configuration for a device.\n\n"
        "Returns list of {community, version, access_hosts, trap_receivers}.\n\n"
        "Use when: user asks about monitoring setup, 'SNMP communities', "
        "or 'who can poll this device'."
    ),
    inputSchema={
        "type": "object",
        "properties": {"hostname": {"type": "string"}},
        "required": ["hostname"],
    },
)

TOOL_GET_DEVICE_INTERFACES = Tool(
    name="get_device_interfaces",
    description=(
        "Get parsed interfaces for a device.\n\n"
        "Returns list of {name, description, status, vlan_mode, access_vlan, "
        "tagged_vlans, port_security, speed}.\n\n"
        "Use when: user asks 'show interfaces', 'which ports are trunk', "
        "or 'port status on sw-X'."
    ),
    inputSchema={
        "type": "object",
        "properties": {"hostname": {"type": "string"}},
        "required": ["hostname"],
    },
)

TOOL_GET_DEVICE_LLDP = Tool(
    name="get_device_lldp",
    description=(
        "Get LLDP global and per-port configuration for a device.\n\n"
        "Returns {enabled, timer, hold_multiplier, ports{port: bool}}.\n\n"
        "Use when: user asks 'is LLDP enabled', 'which ports have LLDP', "
        "or 'show discovery protocol'."
    ),
    inputSchema={
        "type": "object",
        "properties": {"hostname": {"type": "string"}},
        "required": ["hostname"],
    },
)

TOOL_GET_DEVICE_MAC_TABLE = Tool(
    name="get_device_mac_table",
    description=(
        "Get static MAC address entries for a device.\n\n"
        "Returns list of {vlan, mac, port, type}.\n\n"
        "Use when: user asks about MAC bindings, port security, or "
        "'which MACs are pinned to a port'."
    ),
    inputSchema={
        "type": "object",
        "properties": {"hostname": {"type": "string"}},
        "required": ["hostname"],
    },
)

TOOL_GET_DEVICE_VOICE_VLAN = Tool(
    name="get_device_voice_vlan",
    description=(
        "Get Voice VLAN configuration for a device.\n\n"
        "Returns list of {id, mode, ports, priority, lldp_enabled}.\n\n"
        "Use when: user asks about IP phone setup or 'voice VLAN'."
    ),
    inputSchema={
        "type": "object",
        "properties": {"hostname": {"type": "string"}},
        "required": ["hostname"],
    },
)

TOOL_GET_DEVICE_SSH = Tool(
    name="get_device_ssh",
    description=(
        "Get SSH server configuration for a device.\n\n"
        "Returns {enabled, port, version, permit_root_login, allowed_users, "
        "allowed_acls, pubkey_auth}.\n\n"
        "Use when: user asks about remote access, 'is SSH on', 'which users "
        "can SSH', or 'is SSH ACL-protected'."
    ),
    inputSchema={
        "type": "object",
        "properties": {"hostname": {"type": "string"}},
        "required": ["hostname"],
    },
)

TOOL_SEARCH_ACROSS_DEVICES = Tool(
    name="search_across_devices",
    description=(
        "Global search across all devices for a specific entity=value pair.\n\n"
        "Inputs:\n"
        "  - entity (required): vlan, acl, ntp_server, snmp_community, mac, "
        "voice_vlan, ssh_user, route, interface\n"
        "  - value (required): the value to search for (e.g. '100' for VLAN 100)\n"
        "  - vendor (optional): restrict to dlink/eltex/snr\n\n"
        "Returns: list of {hostname, vendor, config_date, entity, value, "
        "location, raw_snippet}.\n\n"
        "Use when: user asks 'where is VLAN 100 configured', 'which devices "
        "have NTP server 10.0.0.1', 'list all MACs in VLAN 200'."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "entity": {"type": "string"},
            "value": {"type": "string"},
            "vendor": {"type": "string"},
        },
        "required": ["entity", "value"],
    },
)

TOOL_RAW_SEARCH = Tool(
    name="raw_search",
    description=(
        "Run a raw regex search across all configs (git grep under the hood).\n\n"
        "Inputs:\n"
        "  - regex (required): POSIX extended regex\n"
        "  - vendor (optional): restrict to a vendor\n"
        "  - max_results (optional, default 100)\n\n"
        "Returns: list of {relative_path, line_number, content}.\n\n"
        "Use when: the structured tools don't cover what you need. Prefer "
        "search_across_devices when possible — it returns normalized results."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "regex": {"type": "string"},
            "vendor": {"type": "string"},
            "max_results": {"type": "integer", "default": 100},
        },
        "required": ["regex"],
    },
)

ALL_TOOLS: List[Tool] = [
    TOOL_LIST_DEVICES,
    TOOL_GET_DEVICE_CONFIG,
    TOOL_GET_DEVICE_VLANS,
    TOOL_GET_DEVICE_ACLS,
    TOOL_GET_DEVICE_NTP,
    TOOL_GET_DEVICE_SNMP,
    TOOL_GET_DEVICE_INTERFACES,
    TOOL_GET_DEVICE_LLDP,
    TOOL_GET_DEVICE_MAC_TABLE,
    TOOL_GET_DEVICE_VOICE_VLAN,
    TOOL_GET_DEVICE_SSH,
    TOOL_SEARCH_ACROSS_DEVICES,
    TOOL_RAW_SEARCH,
]


# ---------------------------------------------------------------------------
# Tool dispatch
# ---------------------------------------------------------------------------

@server.list_tools()
async def list_tools() -> List[Tool]:
    return ALL_TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    try:
        if name == "list_devices":
            return await _list_devices(**arguments)
        elif name == "get_device_config":
            return await _get_device_config(**arguments)
        elif name == "get_device_vlans":
            return await _get_device_vlans(**arguments)
        elif name == "get_device_acls":
            return await _get_device_acls(**arguments)
        elif name == "get_device_ntp":
            return await _get_device_ntp(**arguments)
        elif name == "get_device_snmp":
            return await _get_device_snmp(**arguments)
        elif name == "get_device_interfaces":
            return await _get_device_interfaces(**arguments)
        elif name == "get_device_lldp":
            return await _get_device_lldp(**arguments)
        elif name == "get_device_mac_table":
            return await _get_device_mac_table(**arguments)
        elif name == "get_device_voice_vlan":
            return await _get_device_voice_vlan(**arguments)
        elif name == "get_device_ssh":
            return await _get_device_ssh(**arguments)
        elif name == "search_across_devices":
            return await _search_across_devices(**arguments)
        elif name == "raw_search":
            return await _raw_search(**arguments)
        else:
            return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]
    except Exception as e:
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

async def _list_devices(vendor: Optional[str] = None, group: Optional[str] = None) -> List[TextContent]:
    devices = git_reader.list_devices()
    if group:
        devices = [d for d in devices if d.get("group") == group]
    result = []
    for d in devices:
        v = vendor or _resolve_vendor(d["relative_path"])
        if vendor and v != vendor:
            continue
        info = _enrich_device_info(d["relative_path"], v, d["hostname"])
        info["group"] = d.get("group", "default")
        result.append(info)
    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]


async def _get_device_config(hostname: str) -> List[TextContent]:
    dev = _find_device(hostname)
    if not dev:
        similar = _find_similar(hostname)
        msg = {"error": f"Device '{hostname}' not found"}
        if similar:
            msg["similar"] = similar
        return [TextContent(type="text", text=json.dumps(msg))]
    raw = git_reader.read_config(dev["relative_path"])
    info = _enrich_device_info(dev["relative_path"], _resolve_vendor(dev["relative_path"]), dev["hostname"])
    info["raw_config"] = raw
    return [TextContent(type="text", text=json.dumps(info, ensure_ascii=False, indent=2))]


async def _get_device_vlans(hostname: str) -> List[TextContent]:
    return await _call_extractor(hostname, "extract_vlans")


async def _get_device_acls(hostname: str) -> List[TextContent]:
    return await _call_extractor(hostname, "extract_acls")


async def _get_device_ntp(hostname: str) -> List[TextContent]:
    return await _call_extractor(hostname, "extract_ntp")


async def _get_device_snmp(hostname: str) -> List[TextContent]:
    return await _call_extractor(hostname, "extract_snmp")


async def _get_device_interfaces(hostname: str) -> List[TextContent]:
    return await _call_extractor(hostname, "extract_interfaces")


async def _get_device_lldp(hostname: str) -> List[TextContent]:
    return await _call_extractor(hostname, "extract_lldp")


async def _get_device_mac_table(hostname: str) -> List[TextContent]:
    return await _call_extractor(hostname, "extract_mac_table")


async def _get_device_voice_vlan(hostname: str) -> List[TextContent]:
    return await _call_extractor(hostname, "extract_voice_vlan")


async def _get_device_ssh(hostname: str) -> List[TextContent]:
    return await _call_extractor(hostname, "extract_ssh")


async def _call_extractor(hostname: str, method: str) -> List[TextContent]:
    dev = _find_device(hostname)
    if not dev:
        similar = _find_similar(hostname)
        msg = {"error": f"Device '{hostname}' not found"}
        if similar:
            msg["similar"] = similar
        return [TextContent(type="text", text=json.dumps(msg))]

    plugin = get_plugin_for_path(dev["relative_path"])
    if plugin is None:
        return [TextContent(type="text", text=json.dumps({
            "error": "Could not detect vendor plugin for this file",
            "relative_path": dev["relative_path"],
            "available_vendors": list_plugins(),
        }))]

    raw = git_reader.read_config(dev["relative_path"])
    extractor = getattr(plugin, method)
    data = extractor(raw)
    if not isinstance(data, list):
        data = [data]

    info = _enrich_device_info(dev["relative_path"], plugin.name, dev["hostname"])
    payload = {
        "device": info,
        "extractor": method,
        "data": [d.model_dump(mode="json") if hasattr(d, "model_dump") else d for d in data],
    }
    return [TextContent(type="text", text=json.dumps(payload, ensure_ascii=False, indent=2))]


async def _search_across_devices(
    entity: str,
    value: str,
    vendor: Optional[str] = None,
) -> List[TextContent]:
    """Run entity=value across all devices using the matching plugin."""
    results = []
    for dev in git_reader.list_devices():
        plugin = get_plugin_for_path(dev["relative_path"])
        if plugin is None:
            continue
        if vendor and plugin.name != vendor:
            continue
        try:
            raw = git_reader.read_config(dev["relative_path"])
            hits = plugin.search(raw, entity, value)
            for h in hits:
                info = _enrich_device_info(dev["relative_path"], plugin.name, dev["hostname"])
                # merge hit with device info
                hit_dict = h.model_dump(mode="json") if hasattr(h, "model_dump") else h
                hit_dict["config_date"] = info["config_date"]
                hit_dict["stale_warning"] = info["stale_warning"]
                results.append(hit_dict)
        except Exception:
            # skip broken device, don't fail the whole query
            continue
    return [TextContent(type="text", text=json.dumps(results, ensure_ascii=False, indent=2))]


async def _raw_search(
    regex: str,
    vendor: Optional[str] = None,
    max_results: int = 100,
) -> List[TextContent]:
    matches = git_reader.raw_grep(regex, vendor_filter=vendor, max_results=max_results)
    return [TextContent(type="text", text=json.dumps(matches, ensure_ascii=False, indent=2))]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Run the MCP server over stdio."""
    import asyncio
    from mcp.server.stdio import stdio_server

    async def run() -> None:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options(),
            )

    asyncio.run(run())


if __name__ == "__main__":
    main()
