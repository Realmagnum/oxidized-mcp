from __future__ import annotations

import json
from email.message import Message
from urllib.error import HTTPError

import pytest

from oxidized_mcp.errors import OxidizedRestError
from oxidized_mcp.oxidized_rest import OxidizedRestReader


class _Response:
    def __init__(self, payload: object) -> None:
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode()


def test_nodes_reader_only_gets_inventory_and_excludes_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    reader = OxidizedRestReader("http://127.0.0.1:8888", timeout_seconds=1, cache_ttl_seconds=30)
    seen = {}

    def fake_open(request, timeout):
        seen["method"] = request.method
        seen["url"] = request.full_url
        seen["timeout"] = timeout
        return _Response(
            [
                {
                    "name": "sw-10.90.90.43",
                    "full_name": "sw-10.90.90.43",
                    "ip": "10.90.90.43",
                    "group": "default",
                    "model": "DlinkNextGen",
                    "status": "no_connection",
                    "vars": {"password": "must-not-leak"},
                    "last": {"start": "2026-09-03 19:57:01 UTC", "end": "2026-09-03 19:57:41 UTC", "status": "no_connection", "time": 40.0},
                }
            ]
        )

    monkeypatch.setattr(reader._opener, "open", fake_open)
    result = reader.list_nodes()
    assert seen == {"method": "GET", "url": "http://127.0.0.1:8888/nodes.json", "timeout": 1}
    assert result["nodes"][0]["last"]["duration_seconds"] == 40.0
    assert "vars" not in result["nodes"][0]


def test_nodes_reader_rejects_http_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    reader = OxidizedRestReader("http://127.0.0.1:8888", timeout_seconds=1, cache_ttl_seconds=30)

    def fake_open(request, timeout):
        raise HTTPError(request.full_url, 500, "error", Message(), None)

    monkeypatch.setattr(reader._opener, "open", fake_open)
    with pytest.raises(OxidizedRestError, match="unavailable"):
        reader.list_nodes()
