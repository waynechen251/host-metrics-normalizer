import sys
from types import SimpleNamespace

from host_metrics_normalizer.gpu import nvidia


class _FakeNvml:
    NVML_TEMPERATURE_GPU = 0

    @staticmethod
    def nvmlInit():
        return None

    @staticmethod
    def nvmlDeviceGetCount():
        return 1

    @staticmethod
    def nvmlDeviceGetHandleByIndex(index):
        assert index == 0
        return "gpu-0"

    @staticmethod
    def nvmlDeviceGetName(handle):
        return b"NVIDIA GeForce RTX 3080"

    @staticmethod
    def nvmlDeviceGetUUID(handle):
        return b"GPU-123"

    @staticmethod
    def nvmlDeviceGetPciInfo(handle):
        return SimpleNamespace(pciDeviceId=0x1B8110DE)

    @staticmethod
    def nvmlDeviceGetMemoryInfo(handle):
        return SimpleNamespace(total=10_737_418_240, used=2_147_483_648)

    @staticmethod
    def nvmlDeviceGetUtilizationRates(handle):
        return SimpleNamespace(gpu=42)

    @staticmethod
    def nvmlDeviceGetTemperature(handle, sensor):
        return 65

    @staticmethod
    def nvmlDeviceGetPowerUsage(handle):
        return 250_000


def test_collect_reads_nvidia_driver_metrics(monkeypatch):
    monkeypatch.setitem(sys.modules, "pynvml", _FakeNvml)

    devices = nvidia.collect()

    assert devices == (
        nvidia.NvidiaDevice(
            device_id="10de:1b81",
            name="NVIDIA GeForce RTX 3080",
            uuid="GPU-123",
            memory_total_bytes=10_737_418_240,
            memory_used_bytes=2_147_483_648,
            utilization_percent=42.0,
            temperature_celsius=65.0,
            power_watts=250.0,
        ),
    )


def test_collect_without_binding_is_a_non_failing_fallback(monkeypatch):
    monkeypatch.setitem(sys.modules, "pynvml", None)

    assert nvidia.collect() == ()
