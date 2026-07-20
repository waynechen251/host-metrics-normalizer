from __future__ import annotations

import logging
from dataclasses import dataclass

from ._util import warn_once

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class NvidiaDevice:
    """Vendor-neutral data collected from an NVIDIA driver through NVML."""

    device_id: str
    name: str
    uuid: str
    memory_total_bytes: int | None
    memory_used_bytes: int | None
    utilization_percent: float | None
    temperature_celsius: float | None
    power_watts: float | None


def collect() -> tuple[NvidiaDevice, ...]:
    """Collect NVIDIA telemetry through NVIDIA's maintained Python NVML binding.

    The binding dynamically loads the NVML library supplied by an installed NVIDIA
    driver.  Hosts without the binding, an NVIDIA driver, or an NVIDIA GPU simply
    return no NVIDIA devices and continue through the generic OS collector.
    """
    try:
        import pynvml
    except ImportError:
        return ()

    try:
        pynvml.nvmlInit()
        count = pynvml.nvmlDeviceGetCount()
        return tuple(_read_device(pynvml, index) for index in range(count))
    except Exception:
        warn_once(
            logger,
            "nvml-collect",
            "NVIDIA NVML collection failed; using OS GPU fallbacks where available",
            exc_info=True,
        )
        return ()


def _read_device(pynvml, index: int) -> NvidiaDevice:
    handle = pynvml.nvmlDeviceGetHandleByIndex(index)
    name = _decode(pynvml.nvmlDeviceGetName(handle))
    uuid = _decode(pynvml.nvmlDeviceGetUUID(handle))
    device_id = _device_id(pynvml, handle, uuid, index)
    memory = _optional(lambda: pynvml.nvmlDeviceGetMemoryInfo(handle))
    utilization = _optional(lambda: pynvml.nvmlDeviceGetUtilizationRates(handle))
    temperature = _optional(lambda: pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU))
    power_milliwatts = _optional(lambda: pynvml.nvmlDeviceGetPowerUsage(handle))
    return NvidiaDevice(
        device_id=device_id,
        name=name or "NVIDIA GPU",
        uuid=uuid,
        memory_total_bytes=int(memory.total) if memory is not None else None,
        memory_used_bytes=int(memory.used) if memory is not None else None,
        utilization_percent=float(utilization.gpu) if utilization is not None else None,
        temperature_celsius=float(temperature) if temperature is not None else None,
        power_watts=float(power_milliwatts) / 1000.0 if power_milliwatts is not None else None,
    )


def _device_id(pynvml, handle, uuid: str, index: int) -> str:
    pci = _optional(lambda: pynvml.nvmlDeviceGetPciInfo(handle))
    pci_device_id = getattr(pci, "pciDeviceId", None) if pci is not None else None
    if pci_device_id is not None:
        value = int(pci_device_id)
        return f"{value & 0xffff:04x}:{value >> 16:04x}"
    return f"nvidia:{uuid.lower()}" if uuid else f"nvidia:{index}"


def _optional(operation):
    try:
        return operation()
    except Exception:
        return None


def _decode(value: object) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)
