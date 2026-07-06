from host_metrics_normalizer.gpu import windows as gpu_windows


class _FakeState:
    """Stand-in for UtilizationState: the real one drives win32pdh, which this
    test suite deliberately does not exercise (thin OS I/O layer, see gpu/windows.py
    docstring). This fake returns canned (utilization_by_phys, memory_by_phys) pairs."""

    def __init__(self, utilization: dict, memory: dict):
        self._utilization = utilization
        self._memory = memory

    def sample(self):
        return self._utilization, self._memory


def _wmi_rows(rows):
    def _query(wql: str):
        return rows

    return _query


def test_group_by_phys_sums_by_default():
    items = {
        "luid_0x0_0x1_phys_0": 10.0,
        "luid_0x0_0x2_phys_0": 5.0,
        "luid_0x0_0x3_phys_1": 3.0,
    }
    result = gpu_windows._group_by_phys(items)
    assert result == {"0": 15.0, "1": 3.0}


def test_group_by_phys_can_take_max():
    items = {
        "pid_1_phys_0_eng_0_engtype_3D": 10.0,
        "pid_1_phys_0_eng_1_engtype_Copy": 40.0,
    }
    result = gpu_windows._group_by_phys(items, aggregate=max)
    assert result == {"0": 40.0}


def test_group_by_phys_ignores_unmatched_instance_names():
    items = {"no-phys-here": 1.0}
    assert gpu_windows._group_by_phys(items) == {}


def test_extract_device_id_parses_ven_dev():
    pnp_id = r"PCI\VEN_10DE&DEV_1B81&SUBSYS_12345678&REV_A1\4&abcd"
    assert gpu_windows._extract_device_id(pnp_id) == "PCI\\VEN_10DE&DEV_1B81"


def test_extract_device_id_falls_back_to_raw_string_when_unmatched():
    assert gpu_windows._extract_device_id("not-a-pnp-id") == "not-a-pnp-id"


def test_collect_first_sample_has_no_utilization_yet():
    state = _FakeState(utilization={}, memory={"0": 1073741824.0})
    wmi_query = _wmi_rows(
        [{"Name": "NVIDIA GeForce RTX 3080", "PNPDeviceID": r"PCI\VEN_10DE&DEV_1B81\4&abcd"}]
    )

    series = gpu_windows.collect(
        "host-a", state=state, wmi_query=wmi_query, vram_reader=lambda index: 10737418240
    )
    by_name = {s.name: s for s in series}

    assert by_name["host_gpu_info"].label_dict() == {
        "host": "host-a",
        "gpu": "0",
        "name": "NVIDIA GeForce RTX 3080",
        "device_id": "PCI\\VEN_10DE&DEV_1B81",
    }
    assert by_name["host_gpu_memory_total_bytes"].value == 10737418240.0
    assert by_name["host_gpu_memory_used_bytes"].value == 1073741824.0
    assert by_name["host_gpu_memory_usage_percent"].value == 10.0
    assert "host_gpu_utilization_percent" not in by_name


def test_collect_second_sample_reports_utilization():
    state = _FakeState(utilization={"0": 42.5}, memory={"0": 1073741824.0})
    wmi_query = _wmi_rows(
        [{"Name": "NVIDIA GeForce RTX 3080", "PNPDeviceID": r"PCI\VEN_10DE&DEV_1B81\4&abcd"}]
    )

    series = gpu_windows.collect(
        "host-a", state=state, wmi_query=wmi_query, vram_reader=lambda index: 10737418240
    )
    by_name = {s.name: s for s in series}

    assert by_name["host_gpu_utilization_percent"].value == 42.5


def test_collect_no_adapters_and_no_pdh_data_returns_empty():
    state = _FakeState(utilization={}, memory={})
    series = gpu_windows.collect("host-a", state=state, wmi_query=_wmi_rows([]), vram_reader=lambda i: None)
    assert series == ()


def test_collect_pdh_phys_without_matching_wmi_adapter_still_reports_metrics():
    # A phys index seen only via PDH (e.g. a secondary/hidden adapter not enumerated
    # by Win32_VideoController) should still get its own metrics, just without a
    # friendly name -- documented best-effort limitation, not a crash.
    state = _FakeState(utilization={"1": 5.0}, memory={})
    series = gpu_windows.collect("host-a", state=state, wmi_query=_wmi_rows([]), vram_reader=lambda i: None)
    by_name = {s.name: s for s in series}
    assert by_name["host_gpu_info"].label_dict()["gpu"] == "1"
    assert by_name["host_gpu_info"].label_dict()["name"] == ""
    assert by_name["host_gpu_utilization_percent"].value == 5.0


def test_collect_wmi_query_failure_falls_back_to_pdh_only():
    def _raising_query(wql: str):
        raise RuntimeError("boom")

    state = _FakeState(utilization={"0": 7.0}, memory={})
    series = gpu_windows.collect("host-a", state=state, wmi_query=_raising_query, vram_reader=lambda i: None)
    by_name = {s.name: s for s in series}
    assert by_name["host_gpu_utilization_percent"].value == 7.0
    assert by_name["host_gpu_info"].label_dict()["name"] == ""


def test_collect_state_sample_failure_falls_back_to_wmi_only():
    class _RaisingState:
        def sample(self):
            raise RuntimeError("boom")

    wmi_query = _wmi_rows([{"Name": "Intel(R) UHD Graphics 630", "PNPDeviceID": r"PCI\VEN_8086&DEV_3E92"}])
    series = gpu_windows.collect(
        "host-a", state=_RaisingState(), wmi_query=wmi_query, vram_reader=lambda i: None
    )
    by_name = {s.name: s for s in series}
    assert by_name["host_gpu_info"].label_dict()["name"] == "Intel(R) UHD Graphics 630"
    assert "host_gpu_utilization_percent" not in by_name
