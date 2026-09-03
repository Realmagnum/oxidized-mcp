# Security

## Operational boundary

`oxidized-mcp` is a local read-only stdio server. It reads a mounted Oxidized Git working tree and never connects to network devices. Do not expose it as an unauthenticated HTTP service.

## Configuration confidentiality

Network backups commonly contain SNMP communities, password hashes, TACACS/RADIUS keys and management addressing. Full config output is redacted by default. Use `include_secrets=true` only for an explicit, controlled need and remember that the result enters the AI agent context.

Redaction is defense-in-depth, not a guarantee for every vendor syntax. Add site-specific patterns before production if backups contain additional secret formats.

## Filesystem and process controls

- Mount the Oxidized repository read-only.
- The Docker image runs as UID 10001 and supports `--read-only`.
- Config paths are resolved and checked against repository containment.
- Git runs with a fixed executable, argument vector, no shell and a bounded timeout.
- Raw regex length and result count are bounded.

## Reporting

Do not attach real device configurations, credentials, addressing plans or unredacted MCP responses to public issues. Use sanitized fixtures for bug reports.
