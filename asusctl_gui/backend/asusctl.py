"""Read-only capability discovery and validated calls to the installed asusctl CLI."""
from dataclasses import dataclass, field
from pathlib import Path
import os
import re
import subprocess


class AsusctlError(Exception):
    """A hardware operation failed or returned an unrecognised response."""


def _clean(output: str) -> str:
    # Some asusctl releases log D-Bus handshakes even with RUST_LOG=error.
    return "\n".join(line for line in output.splitlines()
                     if not re.match(r"^\[(?:INFO|DEBUG|TRACE)\b", line)).strip()


def _run(*args: str, timeout: int = 10) -> str:
    try:
        result = subprocess.run(["asusctl", *args], capture_output=True, text=True,
                                timeout=timeout,
                                env={**os.environ, "LC_ALL": "C", "RUST_LOG": "error"})
    except FileNotFoundError as exc:
        raise AsusctlError("asusctl não encontrado. Instale o pacote asusctl.") from exc
    except subprocess.TimeoutExpired as exc:
        raise AsusctlError("O asusd demorou demais para responder.") from exc
    except OSError as exc:
        raise AsusctlError(str(exc)) from exc
    out, err = _clean(result.stdout), _clean(result.stderr)
    combined = "\n".join(filter(None, (out, err)))
    # Upstream can return status zero for missing interfaces and D-Bus errors.
    failure = re.search(r"(?im)^(?:error\b|\[ERROR\b|could not connect|missing arg|"
                        r"no .+ interface found|did not find any interface)", combined)
    # `info` may append "No aura interface found" after reporting valid platform data.
    if args and args[0] == "info" and "Supported Core Functions:" in out:
        failure = re.search(r"(?im)^(?:error\b|\[ERROR\b)", combined)
    if result.returncode != 0 or failure:
        raise AsusctlError(combined or f"asusctl encerrou com código {result.returncode}.")
    return out


def _read(path: Path) -> str:
    try:
        return path.read_text().strip()
    except OSError:
        return ""


@dataclass
class SystemInfo:
    asusctl_version: str = ""
    product_family: str = ""
    product_name: str = ""
    board_name: str = ""
    kernel: str = ""
    supported_interfaces: list[str] = field(default_factory=list)
    platform_properties: list[str] = field(default_factory=list)
    has_profiles: bool = False
    has_battery_limit: bool = False
    has_keyboard: bool = False
    has_fan_curves: bool = False
    has_aura: bool = False
    has_armoury: bool = False
    daemon_available: bool = False
    error: str = ""
    raw: str = ""


def get_system_info() -> SystemInfo:
    dmi = Path("/sys/class/dmi/id")
    info = SystemInfo(product_family=_read(dmi / "product_family"),
                      product_name=_read(dmi / "product_name"),
                      board_name=_read(dmi / "board_name"), kernel=os.uname().release)
    try:
        raw = _run("info", "--show-supported")
        info.raw = raw
        if "Supported Core Functions:" not in raw:
            raise AsusctlError("O asusd não informou os recursos disponíveis.")
        info.daemon_available = True
        version = re.search(r"(?:asusctl v|Software version:\s*)([^\s]+)", raw)
        if version:
            info.asusctl_version = version.group(1)
        info.supported_interfaces = re.findall(r'"((?:xyz\.ljones|org\.asuslinux)\.[^"\n]+)"', raw)
        props = re.search(r"Supported Platform Properties:\s*\[([^]]*)\]", raw, re.S)
        if props:
            info.platform_properties = re.findall(r"\b[A-Z][A-Za-z0-9]+\b", props.group(1))
        names = {name.rsplit(".", 1)[-1] for name in info.supported_interfaces}
        info.has_profiles = "ThrottlePolicy" in info.platform_properties
        info.has_battery_limit = "ChargeControlEndThreshold" in info.platform_properties
        info.has_aura = "Aura" in names
        info.has_fan_curves = "FanCurves" in names
        info.has_armoury = "AsusArmoury" in names
    except AsusctlError as exc:
        info.error = str(exc)
    # Independent of asusd/Aura: Vivobook exposes asus::kbd_backlight to UPower.
    try:
        from .keyboard import get_brightness
        info.has_keyboard = get_brightness()[1] > 0
    except AsusctlError:
        pass
    return info


VALID_PROFILES = ("Quiet", "Balanced", "Performance")


def get_profiles() -> dict:
    available = [line.strip() for line in _run("profile", "list").splitlines()
                 if line.strip() in VALID_PROFILES]
    if not available:
        raise AsusctlError("Nenhum perfil de energia foi informado pelo asusd.")
    out = _run("profile", "get")
    active = re.search(r"Active profile:\s*(\w+)", out)
    if not active or active.group(1) not in available:
        raise AsusctlError("Não foi possível identificar o perfil ativo.")
    result = {"available": available, "active": active.group(1), "ac": "", "battery": ""}
    for key, label in (("ac", "AC profile"), ("battery", "Battery profile")):
        match = re.search(rf"{label}\s*:?\s*(\w+)", out)
        if match and match.group(1) in available:
            result[key] = match.group(1)
    return result


def set_profile(profile_name: str, source: str = "") -> None:
    if profile_name not in VALID_PROFILES or source not in ("", "ac", "battery"):
        raise AsusctlError("Perfil de energia inválido.")
    options = [f"--{source}"] if source else []
    _run("profile", "set", *options, profile_name)


def get_battery_limit() -> int:
    out = _run("battery", "info")
    match = re.search(r"(?:charge limit|charge_control_end_threshold)\s*:\s*(\d+)\s*%?", out, re.I)
    if not match or not 20 <= int(match.group(1)) <= 100:
        raise AsusctlError("O asusd não informou um limite de carga válido.")
    return int(match.group(1))


def set_battery_limit(limit: int) -> None:
    if type(limit) is not int or not 20 <= limit <= 100:
        raise AsusctlError("O limite deve ser um inteiro entre 20 e 100%.")
    _run("battery", "limit", str(limit))


def battery_oneshot() -> None:
    _run("battery", "oneshot")


def get_battery_status() -> dict:
    for path in sorted(Path("/sys/class/power_supply").glob("*")):
        if _read(path / "type") != "Battery" or _read(path / "present") == "0":
            continue
        capacity = _read(path / "capacity")
        return {"capacity": int(capacity) if capacity.isdigit() else None,
                "status": _read(path / "status")}
    return {"capacity": None, "status": ""}
