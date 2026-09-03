from __future__ import annotations

import os
import sys

import pytest
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


@pytest.mark.anyio
async def test_real_stdio_initialize_list_and_call(oxidized_repo) -> None:
    env = {
        **os.environ,
        "OXIDIZED_CONFIG_PATH": str(oxidized_repo),
        "MCP_STALE_HOURS": "24",
    }
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "oxidized_mcp.server"],
        env=env,
    )
    async with stdio_client(parameters) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = {tool.name for tool in tools.tools}
            assert "search_across_devices" in names
            response = await session.call_tool(
                "search_across_devices",
                {"entity": "vlan", "value": "100"},
            )
            assert not response.is_error
            assert response.structured_content["ok"] is True
            assert len(response.structured_content["hits"]) == 6
