"""Plugin registry and vendor detection."""

from __future__ import annotations

import importlib
import pkgutil
from typing import Dict, List, Optional

from .base import VendorPlugin


def _discover_plugins() -> Dict[str, VendorPlugin]:
    """Automatically discover vendor plugins in this package."""
    plugins: Dict[str, VendorPlugin] = {}
    package = __name__

    for _, module_name, _ in pkgutil.iter_modules(path=__path__):
        if module_name == "__init__":
            continue
        module = importlib.import_module(f".{module_name}", package=package)
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and issubclass(attr, VendorPlugin) and attr is not VendorPlugin:
                plugin = attr()  # instantiate
                plugins[plugin.name] = plugin
    return plugins


PLUGINS: Dict[str, VendorPlugin] = _discover_plugins()


def get_plugin_for_path(file_path: str) -> Optional[VendorPlugin]:
    """Select the first plugin whose match_patterns match the file_path."""
    import os
    import re

    # Normalize path for matching
    normalized = os.path.normpath(file_path)

    for plugin in PLUGINS.values():
        for pattern in plugin.match_patterns:
            # Support simple glob patterns (no recursion for now)
            if "*" in pattern:
                # Convert glob to regex
                regex_pattern = re.escape(pattern).replace(r"\*", ".*")
                if re.search(regex_pattern, normalized):
                    return plugin
            else:
                # Exact substring match
                if pattern in normalized:
                    return plugin
    return None


def get_plugin_by_name(name: str) -> Optional[VendorPlugin]:
    """Get plugin by its short name."""
    return PLUGINS.get(name)


def list_plugins() -> List[str]:
    """Return list of available plugin names."""
    return list(PLUGINS.keys())