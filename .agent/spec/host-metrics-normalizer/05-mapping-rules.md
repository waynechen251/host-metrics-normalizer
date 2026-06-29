# host-metrics-normalizer 規格書 — 05. Mapping 規則

## 10. Mapping 規則

### 10.1 Windows exporter mapping

來源可能包含：

```text
windows_cpu_time_total
windows_cs_logical_processors
windows_cs_physical_memory_bytes
windows_os_info
windows_logical_disk_size_bytes
windows_logical_disk_free_bytes
windows_net_bytes_received_total
windows_net_bytes_sent_total
windows_system_system_up_time
```

轉換為：

```text
host_cpu_usage_percent
host_cpu_threads_total
host_memory_bytes_total
host_os_info
host_filesystem_size_bytes
host_filesystem_free_bytes
host_network_receive_bytes_per_second
host_network_transmit_bytes_per_second
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
host_network_receive_bytes_per_second
host_network_transmit_bytes_per_second
host_uptime_seconds
```

### 10.3 Rate 類指標處理

對於 counter 類來源，例如 network bytes、disk bytes、CPU seconds，建議有兩種模式。

MVP 模式：

1. normalizer 輸出 normalized counter。
2. Grafana / Prometheus 用 `rate()` 計算。

例如：

```text
host_network_receive_bytes_total
host_network_transmit_bytes_total
```

進階模式：

1. normalizer 自行 cache 前後兩次值。
2. 直接輸出 per_second gauge。

建議 MVP 優先採用 counter，避免 normalizer 重啟後 rate 計算不準。
