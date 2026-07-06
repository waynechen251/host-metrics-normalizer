from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

from ..normalized import NormalizedSeries

logger = logging.getLogger(__name__)

_DEFAULT_SYSFS_ROOT = "/sys"
_DEFAULT_PCI_IDS_PATHS: tuple[str, ...] = (
    "/usr/share/hwdata/pci.ids",
    "/usr/share/misc/pci.ids",
)
# hwmon `name` file -> the PCI vendor hex ID that driver belongs to. Used to
# best-effort correlate a hwmon temperature sensor back to a DRM GPU card by
# vendor + relative position, since there is no direct standard sysfs link
# guaranteed to be readable/resolvable in every deployment.
_DRIVER_TO_VENDOR_HEX = {
    "amdgpu": "1002",
    "nvidia": "10de",
    "i915": "8086",
    "xe": "8086",
}


def collect(
    host: str,
    *,
    sysfs_root: str | Path = _DEFAULT_SYSFS_ROOT,
    pci_ids_paths: tuple[str, ...] = _DEFAULT_PCI_IDS_PATHS,
) -> tuple[NormalizedSeries, ...]:
    root = Path(sysfs_root)
    drm_dir = root / "class" / "drm"
    if not drm_dir.is_dir():
        return ()

    pci_ids = _load_pci_ids(tuple(pci_ids_paths))
    temps_by_vendor = _hwmon_temperatures_by_vendor(root)
    temp_cursor: dict[str, int] = {}

    series: list[NormalizedSeries] = []
    for index, device_dir in enumerate(_iter_gpu_device_dirs(drm_dir)):
        gpu = str(index)
        vendor_hex = _normalize_hex(_read_text(device_dir / "vendor"))
        device_hex = _normalize_hex(_read_text(device_dir / "device"))
        if not vendor_hex or not device_hex:
            continue

        name = pci_ids.get((vendor_hex, device_hex)) or f"{vendor_hex}:{device_hex}"
        series.append(
            NormalizedSeries.from_mapping(
                "host_gpu_info",
                1.0,
                {"host": host, "gpu": gpu, "name": name, "device_id": f"{vendor_hex}:{device_hex}"},
            )
        )

        total = _read_int(device_dir / "mem_info_vram_total")
        used = _read_int(device_dir / "mem_info_vram_used")
        if total is not None:
            series.append(
                NormalizedSeries.from_mapping(
                    "host_gpu_memory_total_bytes", float(total), {"host": host, "gpu": gpu}
                )
            )
        if used is not None:
            series.append(
                NormalizedSeries.from_mapping(
                    "host_gpu_memory_used_bytes", float(used), {"host": host, "gpu": gpu}
                )
            )
        if total is not None and used is not None and total > 0:
            usage = max(0.0, min(100.0, 100.0 * used / total))
            series.append(
                NormalizedSeries.from_mapping(
                    "host_gpu_memory_usage_percent", usage, {"host": host, "gpu": gpu}
                )
            )

        busy = _read_int(device_dir / "gpu_busy_percent")
        if busy is not None:
            series.append(
                NormalizedSeries.from_mapping(
                    "host_gpu_utilization_percent", float(busy), {"host": host, "gpu": gpu}
                )
            )

        temps = temps_by_vendor.get(vendor_hex)
        if temps:
            position = temp_cursor.get(vendor_hex, 0)
            temp_cursor[vendor_hex] = position + 1
            if position < len(temps):
                series.append(
                    NormalizedSeries.from_mapping(
                        "host_gpu_temperature_celsius", temps[position], {"host": host, "gpu": gpu}
                    )
                )

    return tuple(series)


def _iter_gpu_device_dirs(drm_dir: Path) -> list[Path]:
    cards: list[tuple[int, Path]] = []
    try:
        entries = list(drm_dir.iterdir())
    except OSError:
        return []
    for entry in entries:
        name = entry.name
        # Only bare "cardN" nodes are GPU devices; "cardN-<connector>" (display
        # outputs) and "renderD*"/"controlD*" (render/control nodes) are not.
        if not name.startswith("card"):
            continue
        suffix = name[len("card"):]
        if not suffix.isdigit():
            continue
        device_dir = entry / "device"
        if not device_dir.is_dir():
            continue
        cards.append((int(suffix), device_dir))
    cards.sort(key=lambda item: item[0])
    return [device_dir for _, device_dir in cards]


def _hwmon_temperatures_by_vendor(root: Path) -> dict[str, list[float]]:
    hwmon_root = root / "class" / "hwmon"
    result: dict[str, list[tuple[int, float]]] = {}
    try:
        entries = list(hwmon_root.iterdir())
    except OSError:
        return {}
    for entry in entries:
        name = entry.name
        if not name.startswith("hwmon"):
            continue
        suffix = name[len("hwmon"):]
        if not suffix.isdigit():
            continue
        driver_name = _read_text(entry / "name")
        vendor_hex = _DRIVER_TO_VENDOR_HEX.get(driver_name)
        if vendor_hex is None:
            continue
        temp_millideg = _read_int(entry / "temp1_input")
        if temp_millideg is None:
            continue
        result.setdefault(vendor_hex, []).append((int(suffix), temp_millideg / 1000.0))

    return {
        vendor_hex: [temp for _, temp in sorted(readings, key=lambda item: item[0])]
        for vendor_hex, readings in result.items()
    }


@lru_cache(maxsize=4)
def _load_pci_ids(paths: tuple[str, ...]) -> dict[tuple[str, str], str]:
    for path_str in paths:
        path = Path(path_str)
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        return _parse_pci_ids(text)
    return {}


def _parse_pci_ids(text: str) -> dict[tuple[str, str], str]:
    mapping: dict[tuple[str, str], str] = {}
    current_vendor: str | None = None
    for line in text.splitlines():
        if not line or line.startswith("#"):
            continue
        if line.startswith("\t\t"):
            continue  # subsystem entries: not needed for device naming
        if line.startswith("\t"):
            if current_vendor is None or len(line) < 6:
                continue
            device_hex = line[1:5].lower()
            device_name = line[5:].strip()
            mapping[(current_vendor, device_hex)] = device_name
            continue
        if line[:2].lower().startswith("c ") or len(line) < 6:
            # "C xx  <class name>" marks the start of the device-class list,
            # which follows the vendor/device list in pci.ids.
            break
        current_vendor = line[:4].lower()
    return mapping


def _normalize_hex(value: str) -> str:
    value = value.strip().lower()
    if value.startswith("0x"):
        value = value[2:]
    return value


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _read_int(path: Path) -> int | None:
    text = _read_text(path)
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None
