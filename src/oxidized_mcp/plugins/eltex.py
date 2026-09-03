"""ELTEX MES configuration plugin."""

from .base import ClassicCLIPlugin


class EltexPlugin(ClassicCLIPlugin):
    name = "eltex"
    path_patterns = ("/eltex/", "eltex/", "mes-")
    content_patterns = (
        r"^hostname\s+mes-",
        r"^boot\s+system\s+image-",
        r"^system\s+unit-type\s+",
    )
