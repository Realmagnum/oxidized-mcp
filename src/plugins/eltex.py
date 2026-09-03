"""ELTEX vendor plugin for Oxidized MCP server.

NOTE: This is a stub. The real parser is implemented during development
phase by OpenCode/Codex. The contract is defined in src/plugins/base.py.

To implement: see docs/adding_new_vendor.md
"""

from __future__ import annotations

from typing import List

from .base import VendorPlugin

from ..models import (
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


class EltexPlugin(VendorPlugin):
    """ELTEX specific configuration parser.

    TODO: implement parsing based on real ELTEX config samples
    (MES-2348, MES-3528, etc.) — see tests/fixtures/eltex/.
    """

    name = "eltex"
    match_patterns = [
        "eltex/",
        "mes-",
    ]

    def parse_config(self, raw: str) -> dict:
        raise NotImplementedError("TODO: implement ELTEX parser")

    def extract_vlans(self, raw: str) -> List[VLAN]:
        raise NotImplementedError

    def extract_acls(self, raw: str) -> List[ACL]:
        raise NotImplementedError

    def extract_ntp(self, raw: str) -> List[NTPEntry]:
        raise NotImplementedError

    def extract_snmp(self, raw: str) -> List[SNMPEntry]:
        raise NotImplementedError

    def extract_interfaces(self, raw: str) -> List[Interface]:
        raise NotImplementedError

    def extract_routing(self, raw: str) -> List[Route]:
        raise NotImplementedError

    def extract_lldp(self, raw: str) -> LLDPConfig:
        raise NotImplementedError

    def extract_mac_table(self, raw: str) -> List[MACEntry]:
        raise NotImplementedError

    def extract_voice_vlan(self, raw: str) -> List[VoiceVLAN]:
        raise NotImplementedError

    def extract_ssh(self, raw: str) -> SSHConfig:
        raise NotImplementedError

    def search(self, raw: str, entity: str, value: str) -> List[SearchHit]:
        raise NotImplementedError
