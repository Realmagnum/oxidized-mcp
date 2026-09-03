# Changelog

## [0.2.0] - 2026-09-03

### Changed

- Replaced the non-runnable bootstrap with an installable `oxidized_mcp` package.
- Added dependency-injected MCP composition root based on the proven `mcp-switch-server` pattern.
- Implemented read-only Git repository access, mandatory freshness metadata, plugin discovery and three vendor plugins.
- Added normalized structured search, bounded raw search and parsed config caching.
- Replaced skip-based placeholder tests with executable unit and MCP registry tests.

### Security

- Added default redaction for likely SNMP/password/TACACS/RADIUS secrets.
- Added path containment and Git subprocess timeouts.
- Added a rootless multi-stage Docker image.
- Included the required Git runtime and scoped `safe.directory` handling for read-only bind mounts.

### Documentation

- Kept `SPEC.md` byte-for-byte unchanged.
- Added `IMPROVEMENTS.md` for extensions beyond the original specification.
- Added `docs/REASSESSMENT.md` describing reusable decisions from `mcp-switch-server`.
