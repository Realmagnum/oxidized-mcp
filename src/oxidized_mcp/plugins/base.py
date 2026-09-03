"""Vendor plugin contract and reusable CLI parsing helpers."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod

from ..models import (
    ACL,
    VLAN,
    ACLRule,
    DeviceConfig,
    Interface,
    LLDPConfig,
    MACEntry,
    NTPEntry,
    Route,
    SNMPEntry,
    SSHConfig,
    VendorDetection,
    VoiceVLAN,
)


class VendorPlugin(ABC):
    name: str
    path_patterns: tuple[str, ...] = ()
    content_patterns: tuple[str, ...] = ()

    def detect_path(self, relative_path: str) -> VendorDetection | None:
        value = relative_path.casefold()
        for pattern in self.path_patterns:
            if pattern.casefold() in value:
                return VendorDetection(vendor=self.name, confidence="high", reason=f"path contains {pattern!r}")
        return None

    def detect_content(self, raw: str) -> VendorDetection | None:
        for pattern in self.content_patterns:
            if re.search(pattern, raw, re.IGNORECASE | re.MULTILINE):
                return VendorDetection(vendor=self.name, confidence="medium", reason=f"content matches {pattern!r}")
        return None

    @abstractmethod
    def parse_config(self, raw: str) -> DeviceConfig:
        raise NotImplementedError


class ClassicCLIPlugin(VendorPlugin):
    """Parser for flat and interface-block switch CLI configurations.

    Vendor subclasses provide detection. The parser intentionally preserves
    unknown values instead of guessing operational state from a backup config.
    """

    def parse_config(self, raw: str) -> DeviceConfig:
        return DeviceConfig(
            vlans=self.extract_vlans(raw),
            acls=self.extract_acls(raw),
            ntp=self.extract_ntp(raw),
            snmp=self.extract_snmp(raw),
            interfaces=self.extract_interfaces(raw),
            routes=self.extract_routing(raw),
            lldp=self.extract_lldp(raw),
            mac_table=self.extract_mac_table(raw),
            voice_vlans=self.extract_voice_vlan(raw),
            ssh=self.extract_ssh(raw),
        )

    @staticmethod
    def _lines(raw: str) -> list[str]:
        return [line.strip() for line in raw.splitlines() if line.strip() and not line.lstrip().startswith(("#", "!"))]

    @staticmethod
    def _csv_numbers(value: str) -> list[int]:
        result: list[int] = []
        for token in re.split(r"[ ,]+", value.strip()):
            if not token:
                continue
            if "-" in token:
                start, end = token.split("-", 1)
                result.extend(range(int(start), int(end) + 1))
            elif token.isdigit():
                result.append(int(token))
        return sorted(set(result))

    @staticmethod
    def _csv_ports(value: str) -> list[str]:
        return [token.strip() for token in value.split(",") if token.strip()]

    def extract_vlans(self, raw: str) -> list[VLAN]:
        vlans: dict[int, VLAN] = {}
        current_vlan: int | None = None
        for line in self._lines(raw):
            match = re.match(r'create\s+vlan\s+(\d+)(?:\s+name\s+"?([^"\s]+)"?)?(?:\s+on\s+port\s+(.+))?$', line, re.I)
            if match:
                vlan_id = int(match.group(1))
                vlan = vlans.setdefault(vlan_id, VLAN(id=vlan_id))
                vlan.name = match.group(2) or vlan.name
                if match.group(3):
                    vlan.untagged_ports = sorted(set(vlan.untagged_ports + self._csv_ports(match.group(3))))
                current_vlan = None
                continue
            match = re.match(r"vlan\s+(\d+)(?:\s+name\s+\"?(.+?)\"?)?$", line, re.I)
            if match:
                vlan_id = int(match.group(1))
                vlan = vlans.setdefault(vlan_id, VLAN(id=vlan_id))
                vlan.name = match.group(2) or vlan.name
                current_vlan = None
                continue
            match = re.match(r"interface\s+vlan\s+(\d+)$", line, re.I)
            if match:
                current_vlan = int(match.group(1))
                vlans.setdefault(current_vlan, VLAN(id=current_vlan))
                continue
            if current_vlan is not None:
                match = re.match(r"name\s+\"?(.+?)\"?$", line, re.I)
                if match:
                    vlans[current_vlan].name = match.group(1)
                if line.casefold() == "exit":
                    current_vlan = None
        interfaces = self.extract_interfaces(raw, include_vlan_discovery=False)
        for interface in interfaces:
            if interface.access_vlan:
                vlan = vlans.setdefault(interface.access_vlan, VLAN(id=interface.access_vlan))
                vlan.untagged_ports = sorted(set(vlan.untagged_ports + [interface.name]))
            for vlan_id in interface.tagged_vlans:
                vlan = vlans.setdefault(vlan_id, VLAN(id=vlan_id))
                vlan.tagged_ports = sorted(set(vlan.tagged_ports + [interface.name]))
        return sorted(vlans.values(), key=lambda item: item.id)

    def extract_acls(self, raw: str) -> list[ACL]:
        acls: dict[str, ACL] = {}
        current: ACL | None = None
        sequence = 0
        for line in self._lines(raw):
            match = re.match(r"(?:ip\s+)?access-list(?:\s+(?:standard|extended|advanced))?\s+(\S+)(?:\s+(inbound|outbound))?$", line, re.I)
            if match:
                direction = {"inbound": "in", "outbound": "out"}.get((match.group(2) or "").lower())
                current = acls.setdefault(match.group(1), ACL(name=match.group(1), direction=direction))
                sequence = 0
                continue
            match = re.match(r"(permit|deny)\s+(.*)$", line, re.I)
            if current and match:
                sequence += 1
                tokens = match.group(2).split()
                protocol = tokens[0] if tokens and tokens[0].lower() in {"ip", "tcp", "udp", "icmp", "any"} else None
                body = tokens[1:] if protocol else tokens
                source = (
                    " ".join(body[:2]) if len(body) >= 2 and re.fullmatch(r"\d+\.\d+\.\d+\.\d+", body[1]) else (body[0] if body else None)
                )
                destination_start = 2 if source and " " in source else 1
                destination = " ".join(body[destination_start:]) or None
                current.rules.append(
                    ACLRule(action=match.group(1).lower(), protocol=protocol, source=source, destination=destination, sequence=sequence)
                )
                continue
            match = re.match(r"(?:ip\s+)?access-group\s+(\S+)\s+(in|out)", line, re.I)
            if match:
                acl = acls.setdefault(match.group(1), ACL(name=match.group(1)))
                acl.direction = match.group(2).lower()
        return list(acls.values())

    def extract_ntp(self, raw: str) -> list[NTPEntry]:
        source: str | None = None
        entries: list[NTPEntry] = []
        for line in self._lines(raw):
            match = re.match(r"ntp\s+source(?:\s+interface)?\s+(.+)$", line, re.I)
            if match:
                source = match.group(1)
            match = re.match(r"ntp\s+server\s+(\S+)(.*)$", line, re.I)
            if match:
                entries.append(NTPEntry(address=match.group(1), preferred="prefer" in match.group(2).lower()))
        return [entry.model_copy(update={"source": source}) for entry in entries]

    def extract_snmp(self, raw: str) -> list[SNMPEntry]:
        entries: list[SNMPEntry] = []
        for line in self._lines(raw):
            match = re.match(r"snmp-server\s+community\s+(\S+)(?:\s+(RO|RW))?", line, re.I)
            if match:
                entries.append(
                    SNMPEntry(kind="community", name=match.group(1), version="v2c", access=(match.group(2) or "").lower() or None)
                )
                continue
            match = re.match(r"snmp-server\s+host\s+(\S+)(?:\s+(\S+))?", line, re.I)
            if match:
                entries.append(SNMPEntry(kind="host", name=match.group(1), version="unknown", access=match.group(2)))
        return entries

    def extract_interfaces(self, raw: str, *, include_vlan_discovery: bool = True) -> list[Interface]:
        interfaces: list[Interface] = []
        current: Interface | None = None
        for line in self._lines(raw):
            match = re.match(r"interface\s+(?!vlan\b)(?:port\s+)?(.+)$", line, re.I)
            if match:
                current = Interface(name=match.group(1))
                interfaces.append(current)
                continue
            if current is None:
                continue
            match = re.match(r'description\s+"?(.+?)"?$', line, re.I)
            if match:
                current.description = match.group(1)
                continue
            if re.match(r"(?:shutdown|disable)$", line, re.I):
                current.enabled = False
                continue
            match = re.match(r"(?:switchport\s+)?(?:link-mode|mode)\s+(access|trunk|hybrid)$", line, re.I)
            if match:
                current.vlan_mode = match.group(1).lower()
                continue
            match = re.match(r"switchport\s+mode\s+(access|trunk|hybrid)$", line, re.I)
            if match:
                current.vlan_mode = match.group(1).lower()
                continue
            match = re.match(r"(?:switchport\s+access\s+vlan|untagged-port)\s+(\d+)$", line, re.I)
            if match:
                current.access_vlan = int(match.group(1))
                current.untagged_vlans = [int(match.group(1))]
                continue
            match = re.match(r"(?:switchport\s+trunk\s+allowed\s+vlan|tagged-port)\s+(.+)$", line, re.I)
            if match:
                current.tagged_vlans = self._csv_numbers(match.group(1))
                continue
            if re.search(r"port-security", line, re.I):
                current.port_security = not line.lower().startswith("no ")
        return interfaces

    def extract_routing(self, raw: str) -> list[Route]:
        routes: list[Route] = []
        for line in self._lines(raw):
            match = re.match(r"ip\s+route\s+(\S+)(?:\s+(\S+))?(?:\s+(\d+))?$", line, re.I)
            if match:
                routes.append(
                    Route(destination=match.group(1), gateway=match.group(2), metric=int(match.group(3)) if match.group(3) else None)
                )
                continue
            match = re.match(r"ip\s+default-gateway\s+(\S+)$", line, re.I)
            if match:
                routes.append(Route(destination="0.0.0.0/0", gateway=match.group(1)))
        return routes

    def extract_lldp(self, raw: str) -> LLDPConfig:
        config = LLDPConfig()
        for line in self._lines(raw):
            if re.fullmatch(r"lldp\s+enable", line, re.I):
                config.enabled = True
            elif re.fullmatch(r"(?:no\s+lldp|lldp\s+disable)", line, re.I):
                config.enabled = False
            match = re.match(r"lldp\s+timer\s+(\d+)", line, re.I)
            if match:
                config.timer = int(match.group(1))
            match = re.match(r"lldp\s+hold(?:time|-multiplier)?\s+(\d+)", line, re.I)
            if match:
                config.hold_multiplier = int(match.group(1))
        return config

    def extract_mac_table(self, raw: str) -> list[MACEntry]:
        entries: list[MACEntry] = []
        patterns = (
            r"static\s+mac\s+(\S+)\s+vlan\s+(\d+)\s+interface\s+(.+)$",
            r"mac(?:-address|\s+address-table)?\s+static\s+(\S+)\s+vlan\s+(\d+)\s+(?:interface\s+)?(.+)$",
        )
        for line in self._lines(raw):
            for pattern in patterns:
                match = re.match(pattern, line, re.I)
                if match:
                    entries.append(MACEntry(mac=match.group(1).lower(), vlan=int(match.group(2)), port=match.group(3)))
                    break
        return entries

    def extract_voice_vlan(self, raw: str) -> list[VoiceVLAN]:
        voice: dict[int, VoiceVLAN] = {}
        current_interface: str | None = None
        for line in self._lines(raw):
            match = re.match(r"interface\s+(?!vlan\b)(?:port\s+)?(.+)$", line, re.I)
            if match:
                current_interface = match.group(1)
                continue
            match = re.match(r"voice[- ]vlan\s+(\d+)(?:\s+(auto|manual))?", line, re.I)
            if match:
                vlan_id = int(match.group(1))
                item = voice.setdefault(vlan_id, VoiceVLAN(id=vlan_id, mode=(match.group(2) or "unknown").lower()))
                if current_interface and current_interface not in item.ports:
                    item.ports.append(current_interface)
        return sorted(voice.values(), key=lambda item: item.id)

    def extract_ssh(self, raw: str) -> SSHConfig:
        config = SSHConfig()
        for line in self._lines(raw):
            if re.fullmatch(r"(?:ssh|ip\s+ssh)(?:\s+server)?\s+enable", line, re.I):
                config.enabled = True
            elif re.fullmatch(r"(?:no\s+ssh|ssh(?:\s+server)?\s+disable)", line, re.I):
                config.enabled = False
            match = re.match(r"(?:ssh|ip\s+ssh)(?:\s+server)?\s+port\s+(\d+)", line, re.I)
            if match:
                config.port = int(match.group(1))
            match = re.match(r"(?:ssh|ip\s+ssh)(?:\s+server)?\s+version\s+(\S+)", line, re.I)
            if match:
                config.version = match.group(1)
            match = re.match(r"login\s+allowed-user\s+(\S+)", line, re.I)
            if match:
                config.allowed_users.append(match.group(1))
            if re.search(r"ssh.*(?:public-?key|pubkey)|public-key", line, re.I):
                config.keys_configured = "disable" not in line.lower()
            match = re.search(r"ssh.*(?:access-class|acl)\s+(\S+)", line, re.I)
            if match:
                config.acl_names.append(match.group(1))
        return config

    @staticmethod
    def extract_management_ip(raw: str) -> str | None:
        match = re.search(r"^ip\s+address\s+(\d+\.\d+\.\d+\.\d+)(?:\s+\S+)?$", raw, re.I | re.M)
        return match.group(1) if match else None
