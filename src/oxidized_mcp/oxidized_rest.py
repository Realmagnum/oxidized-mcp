"""Read-only client for the Oxidized inventory endpoint."""

from __future__ import annotations

import json
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .errors import OxidizedRestError


class _RejectRedirects(HTTPRedirectHandler):
    def redirect_request(self, request: Request, *args: Any, **kwargs: Any) -> Request | None:
        return None


class OxidizedRestReader:
    """Fetch only the immutable Oxidized inventory endpoint via HTTP GET."""

    def __init__(self, base_url: str, *, timeout_seconds: float, cache_ttl_seconds: int) -> None:
        self.nodes_url = f"{base_url.rstrip('/')}/nodes.json"
        self.timeout_seconds = timeout_seconds
        self.cache_ttl_seconds = cache_ttl_seconds
        self._opener = build_opener(_RejectRedirects())
        self._cached_nodes: list[dict[str, Any]] | None = None
        self._cached_at = 0.0

    def list_nodes(self) -> dict[str, Any]:
        if self._cached_nodes is None or time.monotonic() - self._cached_at >= self.cache_ttl_seconds:
            self._cached_nodes = self._fetch_nodes()
            self._cached_at = time.monotonic()
        return {"ok": True, "source": "oxidized_rest", "nodes": self._cached_nodes}

    def _fetch_nodes(self) -> list[dict[str, Any]]:
        request = Request(self.nodes_url, headers={"Accept": "application/json"}, method="GET")
        try:
            with self._opener.open(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (TimeoutError, HTTPError, URLError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise OxidizedRestError("Oxidized REST inventory is unavailable") from exc
        if not isinstance(payload, list):
            raise OxidizedRestError("Oxidized REST inventory has an invalid response")
        return [self._normalize_node(node) for node in payload if isinstance(node, dict)]

    @staticmethod
    def _normalize_node(node: dict[str, Any]) -> dict[str, Any]:
        last = node.get("last")
        result: dict[str, Any] = {
            "name": node.get("name"),
            "full_name": node.get("full_name"),
            "ip": node.get("ip"),
            "group": node.get("group"),
            "model": node.get("model"),
            "status": node.get("status"),
        }
        if isinstance(last, dict):
            result["last"] = {
                "start": last.get("start"),
                "end": last.get("end"),
                "status": last.get("status"),
                "duration_seconds": last.get("time"),
            }
        else:
            result["last"] = None
        return result
