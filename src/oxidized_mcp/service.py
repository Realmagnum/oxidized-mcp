"""Application service implementing Oxidized configuration use cases."""

from __future__ import annotations

import difflib
import re
from typing import Any

from .cache import ParsedConfigCache
from .errors import DeviceNotFoundError, QueryValidationError, VendorDetectionError
from .git_reader import ConfigFile, GitReader
from .models import DeviceConfig, DeviceRecord, RawSearchHit, SearchHit, SearchOperator
from .plugins import PluginRegistry

_SECRET_PATTERNS = (
    re.compile(r"(?i)^(\s*(?:snmp-server\s+community)\s+)\S+(.*)$"),
    re.compile(r"(?i)^(\s*(?:password|enable\s+password|secret|community)\s+)\S+(.*)$"),
    re.compile(r"(?i)^(\s*(?:tacacs|radius).*?(?:key|secret)\s+)\S+(.*)$"),
    re.compile(r"(?i)^(\s*username\s+\S+.*?(?:password|secret)\s+)\S+(.*)$"),
)


class OxidizedService:
    def __init__(
        self,
        reader: GitReader,
        registry: PluginRegistry,
        *,
        cache_ttl_seconds: int = 300,
        stale_threshold_hours: float = 24.0,
        max_search_results: int = 100,
        redact_secrets_by_default: bool = True,
    ) -> None:
        self.reader = reader
        self.registry = registry
        self.cache = ParsedConfigCache[DeviceConfig](cache_ttl_seconds)
        self.stale_threshold_hours = stale_threshold_hours
        self.max_search_results = max_search_results
        self.redact_secrets_by_default = redact_secrets_by_default

    def _config_files(self) -> list[ConfigFile]:
        return self.reader.list_configs()

    def _find(self, hostname: str) -> ConfigFile:
        matches = [item for item in self._config_files() if item.hostname.casefold() == hostname.casefold()]
        if len(matches) == 1:
            return matches[0]
        names = [item.hostname for item in self._config_files()]
        raise DeviceNotFoundError(
            f"Device {hostname!r} was not found",
            details={"similar": difflib.get_close_matches(hostname, names, n=5, cutoff=0.35)},
        )

    def _detect(self, config_file: ConfigFile, raw: str | None = None):
        return self.registry.detect(config_file.relative_path, raw)

    def _parse(self, config_file: ConfigFile) -> tuple[DeviceConfig, str, Any, str]:
        cached = self.cache.get(config_file.relative_path, mtime_ns=config_file.mtime_ns, size=config_file.size)
        raw = self.reader.read_config(config_file)
        plugin, detection = self._detect(config_file, raw)
        if cached is None:
            cached = plugin.parse_config(raw)
            self.cache.set(
                config_file.relative_path,
                cached,
                mtime_ns=config_file.mtime_ns,
                size=config_file.size,
            )
        return cached, plugin.name, detection, raw

    def _record(self, config_file: ConfigFile, vendor: str, detection: Any, raw: str) -> DeviceRecord:
        freshness = self.reader.freshness(config_file.relative_path, stale_threshold_hours=self.stale_threshold_hours)
        plugin = self.registry.get(vendor)
        return DeviceRecord(
            hostname=config_file.hostname,
            vendor=vendor,
            group=config_file.group,
            ip=getattr(plugin, "extract_management_ip", lambda _raw: None)(raw),
            relative_path=config_file.relative_path,
            config_date=freshness.config_date,
            config_age_hours=round(freshness.age_hours, 2),
            stale_warning=freshness.stale,
            detection=detection,
        )

    @staticmethod
    def _dump(value: Any) -> Any:
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json")
        if isinstance(value, list):
            return [OxidizedService._dump(item) for item in value]
        return value

    def list_devices(self, vendor: str | None = None, group: str | None = None) -> dict[str, Any]:
        if vendor:
            self.registry.get(vendor)
        devices: list[dict[str, Any]] = []
        unrecognized: list[dict[str, str]] = []
        for config_file in self._config_files():
            if group and config_file.group != group:
                continue
            raw = self.reader.read_config(config_file)
            try:
                plugin, detection = self._detect(config_file, raw)
            except VendorDetectionError as exc:
                unrecognized.append({"hostname": config_file.hostname, "relative_path": config_file.relative_path, "error": str(exc)})
                continue
            if vendor and plugin.name != vendor.casefold():
                continue
            devices.append(self._record(config_file, plugin.name, detection, raw).model_dump(mode="json"))
        return {"ok": True, "devices": devices, "unrecognized": unrecognized}

    def get_device_config(self, hostname: str, include_secrets: bool = False) -> dict[str, Any]:
        config_file = self._find(hostname)
        raw = self.reader.read_config(config_file)
        plugin, detection = self._detect(config_file, raw)
        record = self._record(config_file, plugin.name, detection, raw)
        should_redact = self.redact_secrets_by_default and not include_secrets
        return {
            "ok": True,
            **record.model_dump(mode="json"),
            "secrets_redacted": should_redact,
            "config": self.redact(raw) if should_redact else raw,
        }

    def get_device_freshness(self, hostname: str) -> dict[str, Any]:
        config_file = self._find(hostname)
        raw = self.reader.read_config(config_file)
        plugin, detection = self._detect(config_file, raw)
        return {"ok": True, **self._record(config_file, plugin.name, detection, raw).model_dump(mode="json")}

    def get_entity(self, hostname: str, entity: str) -> dict[str, Any]:
        field_map = {
            "vlans": "vlans",
            "acls": "acls",
            "ntp": "ntp",
            "snmp": "snmp",
            "interfaces": "interfaces",
            "routing": "routes",
            "lldp": "lldp",
            "mac_table": "mac_table",
            "voice_vlan": "voice_vlans",
            "ssh": "ssh",
        }
        if entity not in field_map:
            raise QueryValidationError("Unknown entity", details={"entity": entity})
        config_file = self._find(hostname)
        parsed, vendor, detection, raw = self._parse(config_file)
        record = self._record(config_file, vendor, detection, raw)
        return {
            "ok": True,
            **record.model_dump(mode="json"),
            entity: self._dump(getattr(parsed, field_map[entity])),
        }

    def search_across_devices(
        self,
        entity: str,
        value: str | None = None,
        vendor: str | None = None,
        operator: str = "equals",
    ) -> dict[str, Any]:
        try:
            op = SearchOperator(operator)
        except ValueError as exc:
            raise QueryValidationError(
                "Unknown search operator", details={"operator": operator, "allowed": [item.value for item in SearchOperator]}
            ) from exc
        if op in {SearchOperator.EQUALS, SearchOperator.CONTAINS} and (value is None or value == ""):
            raise QueryValidationError("value is required for equals/contains searches")
        if vendor:
            self.registry.get(vendor)
        hits: list[SearchHit] = []
        for config_file in self._config_files():
            try:
                parsed, detected_vendor, detection, raw = self._parse(config_file)
            except VendorDetectionError:
                continue
            if vendor and detected_vendor != vendor.casefold():
                continue
            record = self._record(config_file, detected_vendor, detection, raw)
            entity_hits = self._search_entity(parsed, entity, value, op)
            for found_value, location, details in entity_hits:
                hits.append(
                    SearchHit(
                        hostname=record.hostname,
                        vendor=record.vendor,
                        config_date=record.config_date,
                        config_age_hours=record.config_age_hours,
                        stale_warning=record.stale_warning,
                        entity=entity,
                        value=found_value,
                        location=location,
                        details=details,
                    )
                )
                if len(hits) >= self.max_search_results:
                    return {"ok": True, "hits": [item.model_dump(mode="json") for item in hits], "truncated": True}
        return {"ok": True, "hits": [item.model_dump(mode="json") for item in hits], "truncated": False}

    def _search_entity(
        self,
        config: DeviceConfig,
        entity: str,
        value: str | None,
        operator: SearchOperator,
    ) -> list[tuple[Any, str | None, dict[str, Any]]]:
        collections: dict[str, list[Any]] = {
            "vlan": config.vlans,
            "acl": config.acls,
            "ntp": config.ntp,
            "snmp": config.snmp,
            "interface": config.interfaces,
            "route": config.routes,
            "lldp": [config.lldp] if config.lldp.enabled else [],
            "mac": config.mac_table,
            "voice_vlan": config.voice_vlans,
            "ssh": [config.ssh] if config.ssh.enabled else [],
        }
        if entity not in collections:
            raise QueryValidationError("Unknown search entity", details={"entity": entity, "allowed": sorted(collections)})
        items = collections[entity]
        if operator is SearchOperator.ABSENT:
            return [(False, None, {})] if not items else []
        if operator is SearchOperator.PRESENT:
            return [(True, None, {"count": len(items)})] if items else []
        if operator is SearchOperator.UNRESTRICTED:
            if entity != "ssh":
                raise QueryValidationError("unrestricted operator is only valid for ssh")
            return [(True, None, config.ssh.model_dump(mode="json"))] if config.ssh.unrestricted else []
        needle = str(value).casefold()
        results: list[tuple[Any, str | None, dict[str, Any]]] = []
        for item in items:
            dumped = item.model_dump(mode="json")
            candidates = self._entity_candidates(entity, dumped)
            matched = any(
                str(candidate).casefold() == needle if operator is SearchOperator.EQUALS else needle in str(candidate).casefold()
                for candidate in candidates
                if candidate is not None
            )
            if matched:
                location = dumped.get("name") or dumped.get("port") or dumped.get("address")
                primary = candidates[0] if candidates else value
                results.append((primary, str(location) if location else None, dumped))
        return results

    @staticmethod
    def _entity_candidates(entity: str, item: dict[str, Any]) -> list[Any]:
        keys = {
            "vlan": ["id", "name", "tagged_ports", "untagged_ports"],
            "acl": ["name", "direction", "bound_ports", "rules"],
            "ntp": ["address", "source"],
            "snmp": ["name", "kind", "version", "allowed_hosts"],
            "interface": ["name", "description", "access_vlan", "tagged_vlans"],
            "route": ["destination", "gateway"],
            "lldp": ["enabled", "enabled_ports"],
            "mac": ["mac", "vlan", "port"],
            "voice_vlan": ["id", "mode", "ports"],
            "ssh": ["enabled", "version", "port", "allowed_users", "acl_names"],
        }[entity]
        values: list[Any] = []
        for key in keys:
            current = item.get(key)
            if isinstance(current, list):
                values.extend(current)
            else:
                values.append(current)
        return values

    def raw_search(self, regex: str, vendor: str | None = None, max_results: int | None = None) -> dict[str, Any]:
        limit = min(max_results or self.max_search_results, self.max_search_results)
        if limit < 1:
            raise QueryValidationError("max_results must be positive")
        if vendor:
            self.registry.get(vendor)
        configs = {item.relative_path: item for item in self._config_files()}
        hits: list[RawSearchHit] = []
        for match in self.reader.grep(regex, max_results=self.max_search_results * 3):
            config_file = configs.get(match.relative_path)
            if config_file is None:
                continue
            raw = self.reader.read_config(config_file)
            try:
                plugin, detection = self._detect(config_file, raw)
            except VendorDetectionError:
                continue
            if vendor and plugin.name != vendor.casefold():
                continue
            record = self._record(config_file, plugin.name, detection, raw)
            hits.append(
                RawSearchHit(
                    hostname=record.hostname,
                    vendor=record.vendor,
                    relative_path=config_file.relative_path,
                    line_number=match.line_number,
                    content=match.content,
                    config_date=record.config_date,
                    config_age_hours=record.config_age_hours,
                    stale_warning=record.stale_warning,
                )
            )
            if len(hits) >= limit:
                break
        return {"ok": True, "hits": [item.model_dump(mode="json") for item in hits], "truncated": len(hits) >= limit}

    def validate_repository(self) -> dict[str, Any]:
        status = self.reader.status()
        recognized = 0
        unrecognized: list[dict[str, Any]] = []
        for config_file in self._config_files():
            raw = self.reader.read_config(config_file)
            try:
                plugin, detection = self._detect(config_file, raw)
                self.reader.freshness(config_file.relative_path, stale_threshold_hours=self.stale_threshold_hours)
                recognized += 1
            except Exception as exc:  # report every bad config without aborting repository diagnostics
                unrecognized.append({"relative_path": config_file.relative_path, "error": str(exc)})
        return {"ok": not unrecognized, **status, "recognized": recognized, "problems": unrecognized, "vendors": self.registry.names()}

    @staticmethod
    def redact(raw: str) -> str:
        redacted: list[str] = []
        for line in raw.splitlines():
            replaced = line
            for pattern in _SECRET_PATTERNS:
                match = pattern.match(line)
                if match:
                    replaced = f"{match.group(1)}***REDACTED***{match.group(2)}"
                    break
            redacted.append(replaced)
        return "\n".join(redacted)
