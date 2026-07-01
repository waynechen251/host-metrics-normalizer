# host-metrics-normalizer 規格書 — 05. Mapping 規則

## 10. Mapping 規則

### 10.1 Windows exporter mapping

Phase 3 先以 `windows_exporter 0.31.6` 的 exact version registry 為準。
normalizer 只在版本完全符合時套用 Windows mapping；未列版本先視為 unsupported，不輸出 `host_*` 正規化指標。

來源可能包含：

```text
windows_cpu_time_total
windows_cs_logical_processors
windows_cs_physical_memory_bytes
windows_memory_physical_total_bytes
windows_memory_physical_available_bytes
windows_os_info
windows_logical_disk_size_bytes
windows_logical_disk_free_bytes
windows_net_bytes_received_total
windows_net_bytes_sent_total
windows_system_boot_time_timestamp
windows_system_system_up_time
```

轉換為：

```text
host_cpu_usage_percent
host_cpu_threads_total
host_memory_bytes_total
host_memory_bytes_available
host_os_info
host_filesystem_size_bytes
host_filesystem_free_bytes
host_network_receive_bytes_total
host_network_transmit_bytes_total
host_uptime_seconds
```

### 10.2 Node exporter mapping

來源可能包含：

```text
node_cpu_seconds_total
node_memory_MemTotal_bytes
node_memory_MemAvailable_bytes
node_uname_info
node_filesystem_size_bytes
node_filesystem_free_bytes
node_network_receive_bytes_total
node_network_transmit_bytes_total
node_boot_time_seconds
```

轉換為：

```text
host_cpu_usage_percent
host_memory_bytes_total
host_memory_bytes_available
host_os_info
host_filesystem_size_bytes
host_filesystem_free_bytes
host_network_receive_bytes_total
host_network_transmit_bytes_total
host_uptime_seconds
```

### 10.3 Rate 類指標處理

MVP 一律輸出 normalized counter，讓 Grafana / Prometheus 用 `rate()`、`irate()` 或 recording rule 自行計算速率。

例如：

```text
host_network_receive_bytes_total
host_network_transmit_bytes_total
```

`host_cpu_usage_percent` 與 `host_memory_usage_percent` 仍以 gauge 直接輸出；它們不是 counter-rate 轉換的結果。
