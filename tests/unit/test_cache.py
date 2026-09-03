from oxidized_mcp.cache import ParsedConfigCache


def test_cache_invalidates_on_file_change() -> None:
    cache = ParsedConfigCache[str](300)
    cache.set("switch", "parsed", mtime_ns=1, size=10)
    assert cache.get("switch", mtime_ns=1, size=10) == "parsed"
    assert cache.get("switch", mtime_ns=2, size=10) is None


def test_cache_clear() -> None:
    cache = ParsedConfigCache[str](300)
    cache.set("switch", "parsed", mtime_ns=1, size=10)
    cache.clear()
    assert len(cache) == 0
