"""Vendor plugin discovery and deterministic detection."""

from __future__ import annotations

import importlib
import pkgutil

from ..errors import VendorDetectionError
from ..models import VendorDetection
from .base import VendorPlugin


class PluginRegistry:
    def __init__(self, plugins: list[VendorPlugin] | None = None) -> None:
        self.plugins = plugins or self._discover()
        names = [plugin.name for plugin in self.plugins]
        if len(names) != len(set(names)):
            raise RuntimeError("Vendor plugin names must be unique")

    @staticmethod
    def _discover() -> list[VendorPlugin]:
        discovered: list[VendorPlugin] = []
        for module in pkgutil.iter_modules(__path__):
            if module.name in {"base"}:
                continue
            imported = importlib.import_module(f"{__name__}.{module.name}")
            for value in vars(imported).values():
                if isinstance(value, type) and issubclass(value, VendorPlugin) and value is not VendorPlugin:
                    if value.__module__ == imported.__name__:
                        discovered.append(value())
        return sorted(discovered, key=lambda plugin: plugin.name)

    def detect(self, relative_path: str, raw: str | None = None) -> tuple[VendorPlugin, VendorDetection]:
        path_matches = [(plugin, detection) for plugin in self.plugins if (detection := plugin.detect_path(relative_path))]
        if len(path_matches) == 1:
            return path_matches[0]
        if raw is not None:
            content_matches = [(plugin, detection) for plugin in self.plugins if (detection := plugin.detect_content(raw))]
            if len(content_matches) == 1:
                return content_matches[0]
            if len(content_matches) > 1:
                raise VendorDetectionError(
                    "Multiple vendor plugins matched config content",
                    details={"relative_path": relative_path, "vendors": [plugin.name for plugin, _ in content_matches]},
                )
        if len(path_matches) > 1:
            raise VendorDetectionError(
                "Multiple vendor plugins matched config path",
                details={"relative_path": relative_path, "vendors": [plugin.name for plugin, _ in path_matches]},
            )
        raise VendorDetectionError(
            "No vendor plugin recognized the config",
            details={"relative_path": relative_path, "available_vendors": self.names()},
        )

    def get(self, name: str) -> VendorPlugin:
        for plugin in self.plugins:
            if plugin.name == name.casefold():
                return plugin
        raise VendorDetectionError("Unknown vendor filter", details={"vendor": name, "available_vendors": self.names()})

    def names(self) -> list[str]:
        return [plugin.name for plugin in self.plugins]


__all__ = ["PluginRegistry", "VendorPlugin"]
