"""
asusctl.py
──────────
Subprocess wrapper around the `asusctl` CLI.

All public functions return plain Python dicts/values and raise
AsusctlError on failure.  Long-running calls should be dispatched
from a GLib thread pool; these functions themselves are synchronous.
"""

import re
import subprocess
import shutil
from dataclasses import dataclass, field
from typing import Optional


# ─── Exception ────────────────────────────────────────────────────────────────

class AsusctlError(Exception):
    """Raised when asusctl exits with a non-zero status or returns unexpected output."""


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _run(*args: str, timeout: int = 10) -> str:
    """Run `asusctl <args>` and return stdout as a stripped string."""
    cmd = ["asusctl", *args]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        # asusd writes some errors to stdout; check explicitly
        combined = result.stdout + result.stderr
        if result.returncode != 0 and "Error" in combined:
            raise AsusctlError(combined.strip())
        return result.stdout.strip()
    except FileNotFoundError:
        raise AsusctlError("asusctl not found — is asusctl installed?")
    except subprocess.TimeoutExpired:
        raise AsusctlError(f"asusctl timed out running: {' '.join(cmd)}")


def _run_raw(*args: str) -> tuple[int, str, str]:
    """Run asusctl and return (returncode, stdout, stderr)."""
    cmd = ["asusctl", *args]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except FileNotFoundError:
        return 1, "", "asusctl not found"
    except subprocess.TimeoutExpired:
        return 1, "", "timeout"


# ─── System / Feature info ────────────────────────────────────────────────────

@dataclass
class SystemInfo:
    asusctl_version: str = ""
    product_family: str = ""
    board_name: str = ""
    supported_interfaces: list[str] = field(default_factory=list)
    platform_properties: list[str] = field(default_factory=list)
    has_fan_curves: bool = False
    has_aura: bool = False
    has_backlight: bool = False
    has_armoury: bool = False
    has_platform: bool = False
    raw: str = ""


def get_system_info() -> SystemInfo:
    """Parse `asusctl info` output into a SystemInfo struct."""
    _, raw, _ = _run_raw("info", "--show-supported")
    info = SystemInfo(raw=raw)

    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("asusctl v"):
            info.asusctl_version = line.replace("asusctl v", "").strip()
        elif "Software version:" in line:
            info.asusctl_version = line.split(":", 1)[1].strip()
        elif "Product family:" in line:
            info.product_family = line.split(":", 1)[1].strip()
        elif "Board name:" in line:
            info.board_name = line.split(":", 1)[1].strip()
        elif '"xyz.ljones.' in line or '"org.asuslinux.' in line:
            iface = line.strip().strip('",')
            info.supported_interfaces.append(iface)

    # Detect feature availability by probing
    rc, out, _ = _run_raw("fan-curve", "--mod-profile", "balanced")
    info.has_fan_curves = rc == 0 and "Error" not in out

    rc, _, _ = _run_raw("aura", "effect")
    info.has_aura = rc == 0

    rc, out, _ = _run_raw("backlight", "--help")
    info.has_backlight = rc == 0 and "screenpad" in out

    info.has_armoury = "xyz.ljones.AsusArmoury" in " ".join(info.supported_interfaces)
    info.has_platform = "xyz.ljones.Platform" in " ".join(info.supported_interfaces)

    return info


# ─── Profiles ─────────────────────────────────────────────────────────────────

VALID_PROFILES = ("Quiet", "Balanced", "Performance")


def get_profiles() -> dict:
    """Return {'available': [...], 'active': str, 'ac': str, 'battery': str}."""
    result = {
        "available": list(VALID_PROFILES),
        "active": "Balanced",
        "ac": "",
        "battery": "",
    }
    try:
        out = _run("profile", "list")
        lines = [l.strip() for l in out.splitlines() if l.strip()]

        available = []
        for line in lines:
            if line in VALID_PROFILES:
                available.append(line)
            elif line.startswith("Active profile:"):
                result["active"] = line.split(":", 1)[1].strip()
            elif line.startswith("AC profile"):
                result["ac"] = line.split(None, 2)[-1].strip()
            elif line.startswith("Battery profile"):
                result["battery"] = line.split(None, 2)[-1].strip()

        if available:
            result["available"] = available

        # Also fetch active separately for reliability
        out2 = _run("profile", "get")
        for line in out2.splitlines():
            line = line.strip()
            if line.startswith("Active profile:"):
                result["active"] = line.split(":", 1)[1].strip()
            elif line.startswith("AC profile"):
                result["ac"] = line.split(None, 2)[-1].strip()
            elif line.startswith("Battery profile"):
                result["battery"] = line.split(None, 2)[-1].strip()

    except AsusctlError:
        pass

    return result


def set_profile(profile_name: str) -> None:
    """Set the active throttle policy. Raises AsusctlError on failure."""
    _run("profile", "set", profile_name)


def next_profile() -> str:
    """Toggle to the next profile and return the new active profile name."""
    _run("profile", "next")
    info = get_profiles()
    return info.get("active", "")


# ─── Battery ──────────────────────────────────────────────────────────────────

def get_battery_limit() -> int:
    """Return the current battery charge limit (20–100)."""
    try:
        out = _run("battery", "info")
        m = re.search(r"(\d+)\s*%", out)
        if m:
            return int(m.group(1))
    except AsusctlError:
        pass
    return 100


def set_battery_limit(limit: int) -> None:
    """Set battery charge limit. limit must be 20–100."""
    limit = max(20, min(100, int(limit)))
    _run("battery", "limit", str(limit))


def battery_oneshot(percent: Optional[int] = None) -> None:
    """Enable one-shot full charge (optionally to a given percent)."""
    if percent is not None:
        _run("battery", "oneshot", str(percent))
    else:
        _run("battery", "oneshot")


# ─── Armoury (firmware attributes) ───────────────────────────────────────────

def get_armoury_attributes() -> dict[str, dict]:
    """
    Parse `asusctl armoury list` into a dict of attribute_name → info.
    Example: {'charge_mode': {'current': '0', 'choices': ['0','1','2']}}
    """
    attrs: dict[str, dict] = {}
    try:
        out = _run("armoury", "list")
        current_attr: Optional[str] = None
        for line in out.splitlines():
            line = line.strip()
            if not line:
                current_attr = None
                continue
            if line.endswith(":"):
                current_attr = line[:-1]
                attrs[current_attr] = {}
            elif current_attr and line.startswith("current:"):
                # e.g. "current: [(0),1,2]"
                raw = line.split(":", 1)[1].strip()
                # Extract all numbers; the one in () is current
                current_match = re.search(r"\((\d+)\)", raw)
                all_vals = re.findall(r"\d+", raw)
                attrs[current_attr]["choices"] = all_vals
                attrs[current_attr]["current"] = (
                    current_match.group(1) if current_match else (all_vals[0] if all_vals else "0")
                )
    except AsusctlError:
        pass
    return attrs


def set_armoury_attribute(name: str, value: str) -> None:
    """Set a firmware attribute via asusctl armoury set."""
    _run("armoury", "set", name, value)


def get_armoury_attribute(name: str) -> str:
    """Get a firmware attribute value."""
    try:
        out = _run("armoury", "get", name)
        lines = [l.strip() for l in out.splitlines() if l.strip()]
        if lines:
            return lines[-1]
    except AsusctlError:
        pass
    return ""


# ─── Charge mode labels ───────────────────────────────────────────────────────

CHARGE_MODE_LABELS = {
    "0": "Full Capacity",
    "1": "Balanced",
    "2": "Maximum Lifespan",
}


# ─── Fan curves ───────────────────────────────────────────────────────────────

def set_aura_effect(effect: str) -> None:
    """Set the keyboard aura effect."""
    _run("aura", "effect", effect)


def get_fan_curve(profile: str, fan: str) -> Optional[list[tuple[int, int]]]:
    """
    Return fan curve as list of (temp_c, pct) tuples.
    Returns None if not supported.
    """
    try:
        rc, out, err = _run_raw("fan-curve", "--mod-profile", profile, "--fan", fan)
        if rc != 0 or "Error" in (out + err):
            return None
        # Parse "30c:1%,49c:2%,..." style
        points = []
        for token in out.split(","):
            token = token.strip()
            m = re.match(r"(\d+)c:(\d+)%?", token)
            if m:
                points.append((int(m.group(1)), int(m.group(2))))
        return points if points else None
    except Exception:
        return None


def set_fan_curve(profile: str, fan: str, points: list[tuple[int, int]]) -> None:
    """Set fan curve for a profile/fan from list of (temp_c, pct) tuples."""
    data = ",".join(f"{t}c:{p}%" for t, p in points)
    _run("fan-curve", "--mod-profile", profile, "--fan", fan, "--data", data)
