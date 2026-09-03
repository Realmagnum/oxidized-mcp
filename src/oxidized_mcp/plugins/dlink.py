"""D-Link configuration plugin."""

from .base import ClassicCLIPlugin


class DLinkPlugin(ClassicCLIPlugin):
    name = "dlink"
    path_patterns = ("/dlink/", "dlink/", "des-", "dgs-")
    content_patterns = (
        r"^create\s+vlan\s+\d+",
        r"^interface\s+port\s+\d+",
        r"^config\s+ports\s+",
    )
