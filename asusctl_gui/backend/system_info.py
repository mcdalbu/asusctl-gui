"""
system_info.py
──────────────
Singleton that probes asusctl/asusd on startup and caches the results.
Used by all pages to decide which controls to show.
"""

from __future__ import annotations
from .asusctl import SystemInfo, get_system_info


_cached: SystemInfo | None = None


def load() -> SystemInfo:
    """Probe system (once) and return cached SystemInfo."""
    global _cached
    if _cached is None:
        _cached = get_system_info()
    return _cached


def reload() -> SystemInfo:
    """Force re-probe of system capabilities."""
    global _cached
    _cached = None
    return load()
