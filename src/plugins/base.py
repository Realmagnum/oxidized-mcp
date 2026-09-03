"""Abstract base class for vendor-specific plugins."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from .models import (
    VLAN,
    ACL,
    NTPEntry,
    SNMPEntry,
    Interface,
    Route,
    LLDPConfig,
    MACEntry,
    VoiceVLAN,
    SSHConfig,
    SearchHit,
)


class VendorPlugin(ABC):
    """Interface all vendor plugins must implement."""

    name: str
    """Short vendor identifier, e.g. "dlink", "eltex", "snr"."""

    match_patterns: List[str]
    """List of glob patterns or regexes to match device config files by path/name."""

    @abstractmethod
    def parse_config(self, raw: str) -> dict:
        """Parse raw config into a dict matching DeviceConfig model (without metadata)."""

    @abstractmethod
    def extract_vlans(self, raw: str) -> List[VLAN]:
        """Extract VLANs from raw config."""

    @abstractmethod
    def extract_acls(self, raw: str) -> List[ACL]:
        """Extract ACLs from raw config."""

    @abstractmethod
    def extract_ntp(self, raw: str) -> List[NTPEntry]:
        """Extract NTP servers from raw config."""

    @abstractmethod
    def extract_snmp(self, raw: str) -> List[SNMPEntry]:
        """Extract SNMP settings from raw config."""

    @abstractmethod
    def extract_interfaces(self, raw: str) -> List[Interface]:
        """Extract interfaces from raw config."""

    @abstractmethod
    def extract_routing(self, raw: str) -> List[Route]:
        """Extract static routes from raw config."""

    @abstractmethod
    def extract_lldp(self, raw: str) -> LLDPConfig:
        """Extract LLDP config from raw config."""

    @abstractmethod
    def extract_mac_table(self, raw: str) -> List[MACEntry]:
        """Extract static MAC table from raw config."""

    @abstractmethod
    def extract_voice_vlan(self, raw: str) -> List[VoiceVLAN]:
        """Extract Voice VLAN from raw config."""

    @abstractmethod
    def extract_ssh(self, raw: str) -> SSHConfig:
        """Extract SSH config from raw config."""

    @abstractmethod
    def search(self, raw: str, entity: str, value: str) -> List[SearchHit]:
        """Search raw config for entity=value, return list of hits."""