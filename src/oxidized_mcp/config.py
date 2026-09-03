"""Validated runtime settings."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Settings(BaseModel):
    """Runtime configuration loaded from environment variables."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    repository_path: Path = Path("/srv/oxidized/configs")
    cache_ttl_seconds: Annotated[int, Field(ge=1, le=3600)] = 300
    stale_threshold_hours: Annotated[float, Field(gt=0, le=8760)] = 24.0
    git_timeout_seconds: Annotated[float, Field(gt=0, le=60)] = 5.0
    max_search_results: Annotated[int, Field(ge=1, le=1000)] = 100
    max_regex_length: Annotated[int, Field(ge=16, le=4096)] = 512
    redact_secrets_by_default: bool = True
    oxidized_rest_enabled: bool = False
    oxidized_rest_base_url: str = "http://127.0.0.1:8888"
    oxidized_rest_timeout_seconds: Annotated[float, Field(ge=0.5, le=10)] = 3.0
    oxidized_rest_cache_ttl_seconds: Annotated[int, Field(ge=5, le=300)] = 30

    @field_validator("repository_path", mode="before")
    @classmethod
    def expand_repository_path(cls, value: object) -> Path:
        return Path(str(value)).expanduser()

    @field_validator("oxidized_rest_base_url")
    @classmethod
    def require_loopback_oxidized_rest(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "::1"} or parsed.path not in {"", "/"}:
            raise ValueError("Oxidized REST endpoint must be an HTTP loopback base URL")
        return value.rstrip("/")

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            repository_path=os.getenv("OXIDIZED_CONFIG_PATH", "/srv/oxidized/configs"),
            cache_ttl_seconds=os.getenv("MCP_CACHE_TTL", "300"),
            stale_threshold_hours=os.getenv("MCP_STALE_HOURS", "24"),
            git_timeout_seconds=os.getenv("MCP_GIT_TIMEOUT", "5"),
            max_search_results=os.getenv("MCP_MAX_RESULTS", "100"),
            max_regex_length=os.getenv("MCP_MAX_REGEX_LENGTH", "512"),
            redact_secrets_by_default=os.getenv("MCP_REDACT_SECRETS", "true").lower() not in {"0", "false", "no"},
            oxidized_rest_enabled=os.getenv("OXIDIZED_REST_ENABLED", "false").lower() in {"1", "true", "yes"},
            oxidized_rest_base_url=os.getenv("OXIDIZED_REST_BASE_URL", "http://127.0.0.1:8888"),
            oxidized_rest_timeout_seconds=os.getenv("OXIDIZED_REST_TIMEOUT", "3"),
            oxidized_rest_cache_ttl_seconds=os.getenv("OXIDIZED_REST_CACHE_TTL", "30"),
        )
