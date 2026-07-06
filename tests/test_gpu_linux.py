from host_metrics_normalizer.gpu import linux as gpu_linux

PCI_IDS_SAMPLE = """\
# comment line
1002  Advanced Micro Devices, Inc. [AMD/ATI]
\t73df  Navi 10 [Radeon RX 5700 XT]
8086  Intel Corporation
\t3e92  UHD Graphics 630
C 00  Unclassified device
\t00  Non-VGA unclassified device
"""


def _write(path, content: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_collect_returns_empty_when_no_drm_directory(tmp_path):
    series = gpu_linux.collect("host-a", sysfs_root=tmp_path)
    assert series == ()


def test_amd_card_with_full_sysfs_data(tmp_path):
    device_dir = tmp_path / "class" / "drm" / "card0" / "device"
    _write(device_dir / "vendor", "0x1002\n")
    _write(device_dir / "device", "0x73df\n")
    _write(device_dir / "mem_info_vram_total", "8589934592\n")
    _write(device_dir / "mem_info_vram_used", "1073741824\n")
    _write(device_dir / "gpu_busy_percent", "42\n")

    hwmon_dir = tmp_path / "class" / "hwmon" / "hwmon0"
    _write(hwmon_dir / "name", "amdgpu\n")
    _write(hwmon_dir / "temp1_input", "65000\n")

    pci_ids_path = tmp_path / "pci.ids"
    _write(pci_ids_path, PCI_IDS_SAMPLE)

    series = gpu_linux.collect(
        "host-a", sysfs_root=tmp_path, pci_ids_paths=(str(pci_ids_path),)
    )
    by_name = {s.name: s for s in series}

    assert by_name["host_gpu_info"].label_dict() == {
        "host": "host-a",
        "gpu": "0",
        "name": "Navi 10 [Radeon RX 5700 XT]",
        "device_id": "1002:73df",
    }
    assert by_name["host_gpu_memory_total_bytes"].value == 8589934592.0
    assert by_name["host_gpu_memory_used_bytes"].value == 1073741824.0
    assert by_name["host_gpu_memory_usage_percent"].value == 12.5
    assert by_name["host_gpu_utilization_percent"].value == 42.0
    assert by_name["host_gpu_temperature_celsius"].value == 65.0


def test_nvidia_card_only_has_info_and_temperature(tmp_path):
    # NVIDIA's proprietary driver does not populate gpu_busy_percent/mem_info_vram_*
    # under the standard DRM sysfs path -- this is an expected, documented gap for
    # Phase 1 (OS-native-only collection), not a bug.
    device_dir = tmp_path / "class" / "drm" / "card0" / "device"
    _write(device_dir / "vendor", "0x10de\n")
    _write(device_dir / "device", "0x1b81\n")

    hwmon_dir = tmp_path / "class" / "hwmon" / "hwmon0"
    _write(hwmon_dir / "name", "nvidia\n")
    _write(hwmon_dir / "temp1_input", "55000\n")

    series = gpu_linux.collect("host-a", sysfs_root=tmp_path, pci_ids_paths=())
    by_name = {s.name: s for s in series}

    assert by_name["host_gpu_info"].label_dict()["device_id"] == "10de:1b81"
    assert by_name["host_gpu_info"].label_dict()["name"] == "10de:1b81"
    assert "host_gpu_memory_total_bytes" not in by_name
    assert "host_gpu_memory_used_bytes" not in by_name
    assert "host_gpu_utilization_percent" not in by_name
    assert by_name["host_gpu_temperature_celsius"].value == 55.0


def test_render_and_control_nodes_are_excluded(tmp_path):
    drm_dir = tmp_path / "class" / "drm"
    _write(drm_dir / "card0" / "device" / "vendor", "0x1002\n")
    _write(drm_dir / "card0" / "device" / "device", "0x73df\n")
    # These must never be treated as separate GPU devices.
    _write(drm_dir / "card0-DP-1" / "device" / "vendor", "0x1002\n")
    _write(drm_dir / "renderD128" / "device" / "vendor", "0x1002\n")
    _write(drm_dir / "controlD64" / "device" / "vendor", "0x1002\n")

    series = gpu_linux.collect("host-a", sysfs_root=tmp_path, pci_ids_paths=())
    info_series = [s for s in series if s.name == "host_gpu_info"]
    assert len(info_series) == 1
    assert info_series[0].label_dict()["gpu"] == "0"


def test_missing_pci_ids_falls_back_to_hex_id(tmp_path):
    device_dir = tmp_path / "class" / "drm" / "card0" / "device"
    _write(device_dir / "vendor", "0x1002\n")
    _write(device_dir / "device", "0x73df\n")

    series = gpu_linux.collect(
        "host-a", sysfs_root=tmp_path, pci_ids_paths=(str(tmp_path / "does-not-exist.ids"),)
    )
    by_name = {s.name: s for s in series}
    assert by_name["host_gpu_info"].label_dict()["name"] == "1002:73df"


def test_malformed_numeric_file_is_ignored_not_raised(tmp_path):
    device_dir = tmp_path / "class" / "drm" / "card0" / "device"
    _write(device_dir / "vendor", "0x1002\n")
    _write(device_dir / "device", "0x73df\n")
    _write(device_dir / "gpu_busy_percent", "not-a-number\n")

    series = gpu_linux.collect("host-a", sysfs_root=tmp_path, pci_ids_paths=())
    assert "host_gpu_utilization_percent" not in {s.name for s in series}


def test_device_without_vendor_or_device_file_is_skipped(tmp_path):
    device_dir = tmp_path / "class" / "drm" / "card0" / "device"
    device_dir.mkdir(parents=True)

    series = gpu_linux.collect("host-a", sysfs_root=tmp_path, pci_ids_paths=())
    assert series == ()


def test_multiple_cards_use_stable_index_order(tmp_path):
    drm_dir = tmp_path / "class" / "drm"
    _write(drm_dir / "card1" / "device" / "vendor", "0x1002\n")
    _write(drm_dir / "card1" / "device" / "device", "0xaaaa\n")
    _write(drm_dir / "card0" / "device" / "vendor", "0x8086\n")
    _write(drm_dir / "card0" / "device" / "device", "0xbbbb\n")

    series = gpu_linux.collect("host-a", sysfs_root=tmp_path, pci_ids_paths=())
    info_series = sorted(
        (s for s in series if s.name == "host_gpu_info"), key=lambda s: s.label_dict()["gpu"]
    )
    assert [s.label_dict()["gpu"] for s in info_series] == ["0", "1"]
    assert info_series[0].label_dict()["device_id"] == "8086:bbbb"
    assert info_series[1].label_dict()["device_id"] == "1002:aaaa"
