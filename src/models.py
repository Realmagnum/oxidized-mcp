"""Pydantic models for normalized network device configuration entities."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class VLAN(BaseModel):
    """Normalized VLAN representation across all vendors."""

    id: int = Field(..., description="VLAN ID (1-4094)")
    name: Optional[str] = Field(None, description="VLAN description/name")
    tagged_ports: list[str] = Field(default_factory=list, description="Trunk/tagged ports")
    untagged_ports: list[str] = Field(default_factory=list, description="Access/untagged ports")


class ACLRule(BaseModel):
    """Single ACL rule."""

    action: str = Field(..., description="permit or deny")
    protocol: Optional[str] = Field(None, description="ip, tcp, udp, icmp, any")
    source: Optional[str] = Field(None, description="Source network or any")
    destination: Optional[str] = Field(None, description="Destination network or any")
    source_port: Optional[str] = Field(None, description="Source port (for tcp/udp)")
    dest_port: Optional[str] = Field(None, description="Destination port (for tcp/udp)")
    remark: Optional[str] = Field(None, description="Comment/description line")
    line_number: Optional[int] = Field(None, description="Position in ACL config")


class ACL(BaseModel):
    """Normalized ACL / access-list."""

    name: str = Field(..., description="ACL name or number")
    direction: Optional[str] = Field(None, description="inbound, outbound, or None if global")
    bound_ports: list[str] = Field(default_factory=list, description="Interfaces where ACL is applied")
    rules: list[ACLRule] = Field(default_factory=list, description="Ordered list of ACL rules")


class NTPEntry(BaseModel):
    """NTP server configuration."""

    address: str = Field(..., description="NTP server IP or hostname")
    source: Optional[str] = Field(None, description="Source interface or preferred")
    version: Optional[int] = Field(None, description="NTP version (1-4)")


class SNMPEntry(BaseModel):
    """SNMP community / user configuration."""

    community: Optional[str] = Field(None, description="Community string (v1/v2c)")
    version: str = Field(..., description="v1, v2c, v3")
    access_hosts: list[str] = Field(default_factory=list, description="Allowed SNMP managers")
    trap_receivers: list[str] = Field(default_factory=list, description="SNMP trap destinations")


class Interface(BaseModel):
    """Normalized network interface."""

    name: str = Field(..., description="Interface identifier (e.g. port1, GigabitEthernet0/1)")
    description: Optional[str] = Field(None, description="Interface description")
    status: str = Field(..., description="up, down, or disabled")
    vlan_mode: Optional[str] = Field(None, description="access, trunk, or hybrid")
    access_vlan: Optional[int] = Field(None, description="PVID / access VLAN")
    tagged_vlans: list[int] = Field(default_factory=list, description="Allowed/trunk VLANs")
    port_security: Optional[dict] = Field(None, description="Port-security settings if any")
    speed: Optional[str] = Field(None, description="Speed negotiated (e.g. 1000M, auto)")


class Route(BaseModel):
    """Routing entry."""

    destination: str = Field(..., description="Destination network or default")
    gateway: Optional[str] = Field(None, description="Next-hop IP")
    metric: Optional[int] = Field(None, description="Administrative distance / metric")
    vrf: Optional[str] = Field(None, description="VRF name if not default")


class LLDPNeighbor(BaseModel):
    """LLDP neighbor on a port."""

    port: str = Field(..., description="Local port name")
    chassis_id: Optional[str] = Field(None, description="Neighbor chassis ID")
    port_id: Optional[str] = Field(None, description="Neighbor port identifier")
    system_name: Optional[str] = Field(None, description="Neighbor hostname")
    system_description: Optional[str] = Field(None, description="Neighbor device description")
    capabilities: Optional[list[str]] = Field(None, description="LLDP capabilities (B, R, S, T...)")


class LLDPConfig(BaseModel):
    """LLDP global and per-port configuration."""

    enabled: bool = Field(..., description="Global LLDP enable/disable")
    timer: Optional[int] = Field(None, description="Transmit interval in seconds")
    hold_multiplier: Optional[int] = Field(None, description="Message hold multiplier")
    ports: dict[str, bool] = Field(default_factory=dict, description="Per-port enable state")
    neighbors: list[LLDPNeighbor] = Field(default_factory=list, description="LLDP neighbors")


class MACEntry(BaseModel):
    """Static MAC address entry."""

    vlan: int = Field(..., description="VLAN ID where MAC is learned")
    mac: str = Field(..., description="MAC address (canonical format)")
    port: str = Field(..., description="Port where MAC is bound")
    type: str = Field(default="static", description="static, permanent, or dynamic")


class VoiceVLAN(BaseModel):
    """Voice VLAN configuration."""

    id: int = Field(..., description="Voice VLAN ID")
    mode: str = Field(..., description="auto, manual, or none")
    ports: list[str] = Field(default_factory=list, description="Ports in Voice VLAN")
    priority: Optional[str] = Field(None, description="802.1p priority (0-7)")
    lldp_enabled: bool = Field(default=False, description="Voice VLAN via LLDP-MED")


class SSHConfig(BaseModel):
    """SSH server configuration."""

    enabled: bool = Field(..., description="SSH server status")
    port: int = Field(default=22, description="SSH listen port")
    version: Optional[str] = Field(None, description="SSH protocol version (1, 2, or both)")
    permit_root_login: Optional[str] = Field(None, description="yes, without-password, no")
    allowed_users: list[str] = Field(default_factory=list, description="Explicitly allowed users")
    allowed_acls: list[str] = Field(default_factory=list, description="ACL names applied to SSH")
    pubkey_auth: Optional[bool] = Field(None, description="Public key authentication enabled")


class DeviceInfo(BaseModel):
    """Device metadata."""

    hostname: str
    vendor: str
    group: Optional[str] = None
    ip: Optional[str] = None
    config_date: Optional[datetime] = None
    config_age_hours: Optional[float] = None
    stale_warning: bool = False


class DeviceConfig(DeviceInfo):
    """Complete normalized device configuration."""

    raw_config: Optional[str] = None
    vlans: list[VLAN] = Field(default_factory=list)
    acls: list[ACL] = Field(default_factory=list)
    ntp: list[NTPEntry] = Field(default_factory=list)
    snmp: list[SNMPEntry] = Field(default_factory=list)
    interfaces: list[Interface] = Field(default_factory=list)
    routes: list[Route] = Field(default_factory=list)
    lldp: Optional[LLDPConfig] = None
    mac_table: list[MACEntry] = Field(default_factory=list)
    voice_vlans: list[VoiceVLAN] = Field(default_factory=list)
    ssh: Optional[SSHConfig] = None


class SearchHit(BaseModel):
    """Single search result entry."""

    hostname: str
    vendor: str
    config_date: Optional[datetime] = None
    entity: str = Field(..., description="Type of entity matched")
    value: str = Field(..., description="Matched value")
    location: Optional[str] = Field(None, description="Where matched (port, interface, etc.)")
    raw_snippet: Optional[str] = Field(None, description="Raw config line(s) for context")
