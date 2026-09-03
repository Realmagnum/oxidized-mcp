# OpenCode integration

Install the project in a dedicated virtual environment and configure it as a local stdio MCP server.

```bash
cd /path/to/oxidized-mcp
python3 -m venv .venv
. .venv/bin/activate
python -m pip install .
OXIDIZED_CONFIG_PATH=/srv/oxidized/configs oxidized-mcp --check
```

Example configuration shape:

```json
{
  "mcp": {
    "oxidized": {
      "type": "local",
      "command": ["/path/to/oxidized-mcp/.venv/bin/oxidized-mcp"],
      "environment": {
        "OXIDIZED_CONFIG_PATH": "/srv/oxidized/configs",
        "MCP_REDACT_SECRETS": "true"
      }
    }
  }
}
```

Use the exact key names required by the installed OpenCode version; the server-side contract is stdio plus `OXIDIZED_CONFIG_PATH`.
