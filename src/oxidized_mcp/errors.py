"""Stable application errors exposed through MCP tools."""

from __future__ import annotations

from typing import Any


class OxidizedMCPError(RuntimeError):
    """Base error with a stable machine-readable code."""

    code = "operation_failed"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.details = details or {}


class RepositoryError(OxidizedMCPError):
    code = "repository_error"


class ConfigDateError(RepositoryError):
    code = "config_date_unavailable"


class DeviceNotFoundError(OxidizedMCPError):
    code = "device_not_found"


class VendorDetectionError(OxidizedMCPError):
    code = "vendor_not_detected"


class QueryValidationError(OxidizedMCPError):
    code = "invalid_query"
