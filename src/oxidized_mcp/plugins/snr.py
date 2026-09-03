"""SNR configuration plugin."""

from .base import ClassicCLIPlugin


class SNRPlugin(ClassicCLIPlugin):
    name = "snr"
    path_patterns = ("/snr/", "snr/", "snr-s")
    content_patterns = (
        r"^hostname\s+snr-",
        r"^no\s+service\s+password-encryption",
        r"^interface\s+ethernet\s+1/0/",
    )
