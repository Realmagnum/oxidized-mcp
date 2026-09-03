# Backlog

## Required before production acceptance

- [ ] Replace synthetic fixtures with sanitized real Oxidized backups for at least two models per D-Link, ELTEX and SNR.
- [ ] Add golden normalized JSON snapshots for every sanitized fixture.
- [ ] Extend grammar patterns for observed firmware/model differences.
- [ ] Benchmark all acceptance queries against a copy of the ~100-device repository and record p50/p95 latency.

## Phase 2

- [ ] `get_config_history`
- [ ] `diff_configs`
- [ ] `find_recent_changes`
- [ ] Revision-aware parsing and cache keys

## Optional

- [ ] Add a configurable redaction policy file for site-specific secret syntaxes.
- [ ] Add compact compliance/profile tools for NTP, SNMP and SSH posture.
