"""Normalized domain models shared by every vendor plugin."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class VendorDetection(Model):
    vendor: str
    confidence: Literal["high", "medium", "low"]
    reason: str


class VLAN(Model):
    id: int = Field(ge=1, le=4094)
    name: str | None = None
    tagged_ports: list[str] = Field(default_factory=list)
    untagged_ports: list[str] = Field(default_factory=list)


class ACLRule(Model):
    action: Literal["permit", "deny"]
    protocol: str | None = None
    source: str | None = None
    destination: str | None = None
    source_port: str | None = None
    destination_port: str | None = None
    remark: str | None = None
    sequence: int | None = None


class ACL(Model):
    name: str
    rules: list[ACLRule] = Field(default_factory=list)
    direction: Literal["in", "out"] | None = None
    bound_ports: list[str] = Field(default_factory=list)


class NTPEntry(Model):
    address: str
    source: str | None = None
    preferred: bool = False


class SNMPEntry(Model):
    kind: Literal["community", "user", "host"] = "community"
    name: str
    version: Literal["v1", "v2c", "v3", "unknown"] = "unknown"
    access: str | None = None
    allowed_hosts: list[str] = Field(default_factory=list)


class Interface(Model):
    name: str
    description: str | None = None
    enabled: bool = True
    vlan_mode: Literal["access", "trunk", "hybrid", "unknown"] = "unknown"
    access_vlan: int | None = None
    tagged_vlans: list[int] = Field(default_factory=list)
    untagged_vlans: list[int] = Field(default_factory=list)
    port_security: bool | None = None


class Route(Model):
    destination: str
    gateway: str | None = None
    metric: int | None = None


class LLDPConfig(Model):
    enabled: bool = False
    timer: int | None = None
    hold_multiplier: int | None = None
    enabled_ports: list[str] = Field(default_factory=list)
    disabled_ports: list[str] = Field(default_factory=list)


class MACEntry(Model):
    mac: str
    vlan: int
    port: str


class VoiceVLAN(Model):
    id: int = Field(ge=1, le=4094)
    mode: Literal["auto", "manual", "unknown"] = "unknown"
    ports: list[str] = Field(default_factory=list)
    priority: int | None = Field(default=None, ge=0, le=7)


class SSHConfig(Model):
    enabled: bool = False
    version: str | None = None
    port: int = Field(default=22, ge=1, le=65535)
    allowed_users: list[str] = Field(default_factory=list)
    keys_configured: bool = False
    acl_names: list[str] = Field(default_factory=list)

    @property
    def unrestricted(self) -> bool:
        return self.enabled and not self.acl_names


class DeviceConfig(Model):
    vlans: list[VLAN] = Field(default_factory=list)
    acls: list[ACL] = Field(default_factory=list)
    ntp: list[NTPEntry] = Field(default_factory=list)
    snmp: list[SNMPEntry] = Field(default_factory=list)
    interfaces: list[Interface] = Field(default_factory=list)
    routes: list[Route] = Field(default_factory=list)
    lldp: LLDPConfig = Field(default_factory=LLDPConfig)
    mac_table: list[MACEntry] = Field(default_factory=list)
    voice_vlans: list[VoiceVLAN] = Field(default_factory=list)
    ssh: SSHConfig = Field(default_factory=SSHConfig)


class DeviceRecord(Model):
    hostname: str
    vendor: str
    group: str | None = None
    ip: str | None = None
    relative_path: str
    config_date: datetime
    config_age_hours: float
    stale_warning: bool
    detection: VendorDetection


class SearchOperator(StrEnum):
    EQUALS = "equals"
    CONTAINS = "contains"
    PRESENT = "present"
    ABSENT = "absent"
    UNRESTRICTED = "unrestricted"


class SearchHit(Model):
    hostname: str
    vendor: str
    config_date: datetime
    config_age_hours: float
    stale_warning: bool
    entity: str
    value: str | int | bool | None = None
    location: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class RawSearchHit(Model):
    hostname: str
    vendor: str
    relative_path: str
    line_number: int
    content: str
    config_date: datetime
    config_age_hours: float
    stale_warning: bool


class ToolError(Model):
    ok: Literal[False] = False
    error_code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
