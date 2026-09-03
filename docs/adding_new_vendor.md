# Guide: Adding a new vendor plugin

## Overview

Adding a new vendor to oxidized-mcp involves:
1. Collecting real config samples (2-3 different models)
2. Creating a plugin file in `src/plugins/<vendor>.py`
3. Writing tests in `tests/test_<vendor>.py`
4. Registering the plugin (automatic — no manual edit needed)

## Step-by-step

### 1. Collect config samples

Place real config files in `tests/fixtures/<vendor>/`. Use real device configs,
not synthetic strings. Minimum 2 models per vendor.

```
tests/fixtures/<vendor>/
├── model-a.cfg
└── model-b.cfg
```

### 2. Create the plugin

Copy the stub pattern from `src/plugins/base.py`:

```python
from .base import VendorPlugin
from ..models import VLAN, ACL, NTPEntry, SNMPEntry, Interface, Route, LLDPConfig, MACEntry, VoiceVLAN, SSHConfig, SearchHit


class NewVendorPlugin(VendorPlugin):
    name = "newvendor"
    match_patterns = [
        "newvendor/",
        "model-prefix-",
    ]

    def parse_config(self, raw: str) -> dict:
        # parse raw config into normalized dict
        ...

    def extract_vlans(self, raw: str) -> list[VLAN]:
        ...

    def extract_acls(self, raw: str) -> list[ACL]:
        ...

    def extract_ntp(self, raw: str) -> list[NTPEntry]:
        ...

    def extract_snmp(self, raw: str) -> list[SNMPEntry]:
        ...

    def extract_interfaces(self, raw: str) -> list[Interface]:
        ...

    def extract_routing(self, raw: str) -> list[Route]:
        ...

    def extract_lldp(self, raw: str) -> LLDPConfig:
        ...

    def extract_mac_table(self, raw: str) -> list[MACEntry]:
        ...

    def extract_voice_vlan(self, raw: str) -> list[VoiceVLAN]:
        ...

    def extract_ssh(self, raw: str) -> SSHConfig:
        ...

    def search(self, raw: str, entity: str, value: str) -> list[SearchHit]:
        ...
```

### 3. Write tests

Create `tests/test_<vendor>.py` with tests for each entity type. Use real fixtures.

### 4. Register

No manual registration needed — `src/plugins/__init__.py` auto-discovers
all `VendorPlugin` subclasses in the package.

## Normalization rules

- All extracted entities must use the same Pydantic models (see `src/models.py`)
- VLAN: `id` (int), `name` (str), `tagged_ports` (list[str]), `untagged_ports` (list[str])
- ACL: `name`, `direction`, `bound_ports`, `rules[]`
- NTP: `address`, `source`, `version`
- SNMP: `community`, `version`, `access_hosts`, `trap_receivers`
- Interface: `name`, `description`, `status`, `vlan_mode`, `access_vlan`, `tagged_vlans`, `port_security`, `speed`
- LLDP: `enabled`, `timer`, `hold_multiplier`, `ports{}`, `neighbors[]`
- MAC: `vlan`, `mac`, `port`, `type`
- VoiceVLAN: `id`, `mode`, `ports`, `priority`, `lldp_enabled`
- SSH: `enabled`, `port`, `version`, `permit_root_login`, `allowed_users`, `allowed_acls`, `pubkey_auth`

## Vendor detection priority

1. Path-based: `match_patterns` are matched against the relative path
2. Content-based: if no path match, scan the config content for vendor-specific patterns

## Vendor candidates

| Vendor | Format | Notes |
|--------|--------|-------|
| Cisco IOS/IOS-XE | Flat CLI | Reference syntax, widely used |
| Huawei VRP | Flat CLI | Common in operator networks |
| Juniper Junos | Hierarchical | Requires parser adaptation |
| MikroTik RouterOS | /export format | Different from classic CLI |