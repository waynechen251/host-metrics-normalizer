# host-metrics-normalizer 規格書 — 05. Mapping 規則

## 10. Mapping 規則

### 10.1 Windows exporter mapping

Phase 3 先以 `windows_exporter 0.30.6`、`0.31.6`、`0.31.7` 的 exact version registry 為準(見 `.agent/spec/metrics-mapping/windows_exporter/` 對應版本的官方 collector 文件)。
normalizer 只在版本完全符合時套用 Windows mapping；未列版本先視為 unsupported，不輸出 `host_*` 正規化指標。

`windows_cpu_time_total`/`windows_net_bytes_received_total`/`windows_net_bytes_sent_total` 等 counter 類指標，經 `prometheus_client` parser 解析後 family name 會被去掉 `_total` 後綴（已用實際安裝的 library 驗證過），因此程式碼一律用「帶 `_total` 的官方名稱」與「去掉後綴的裸名稱」雙名稱 fallback 查找。

來源可能包含：

```text
windows_cpu_time_total
windows_cpu_logical_processor
windows_cs_logical_processors          # 0.30.6 起已標示 deprecated，由 windows_cpu_logical_processor 取代；0.31.6/0.31.7 已移除
windows_cpu_info                       # cpu_info collector，非預設啟用
windows_cpu_info_core                  # cpu_info collector，非預設啟用
windows_memory_physical_total_bytes
windows_memory_physical_free_bytes
windows_memory_available_bytes
windows_pagefile_limit_bytes
windows_pagefile_free_bytes
windows_os_info
windows_logical_disk_size_bytes
windows_logical_disk_free_bytes
windows_logical_disk_info              # 用於 join 出 volume 對應的 filesystem(size_bytes/free_bytes 本身不帶 filesystem label)
windows_physical_disk_requests_queued
windows_physical_disk_read_bytes_total
windows_physical_disk_write_bytes_total
windows_physical_disk_reads_total
windows_physical_disk_writes_total
windows_net_bytes_received_total
windows_net_bytes_sent_total
windows_net_packets_received_errors_total
windows_net_packets_outbound_errors_total
windows_net_nic_operation_status
windows_net_current_bandwidth_bytes    # 單位是 bytes/sec，轉換時需 ×8 才是 host_network_speed_bits 宣告的 bits/sec
windows_system_boot_time_timestamp
```

轉換為：

```text
host_cpu_usage_percent
host_cpu_threads_total
host_cpu_cores_total
host_cpu_sockets_total
host_cpu_info
host_memory_bytes_total
host_memory_bytes_available
host_memory_usage_percent
host_memory_swap_bytes_total
host_memory_swap_usage_percent
host_os_info
host_filesystem_size_bytes
host_filesystem_free_bytes
host_filesystem_usage_percent
host_disk_queue_length
host_disk_read_bytes_total
host_disk_write_bytes_total
host_disk_reads_total
host_disk_writes_total
host_network_receive_bytes_total
host_network_transmit_bytes_total
host_network_receive_errors_total
host_network_transmit_errors_total
host_network_link_up
host_network_speed_bits
host_uptime_seconds
```

`host_memory_bytes_available` 主要來源是 `windows_memory_physical_free_bytes`(嚴格未用記憶體),`windows_memory_available_bytes`(含可回收 standby cache 的「可用」記憶體)作為 fallback——維持既有部署的回報數值基準,不因為指標改名而變更語意。

`host_cpu_threads_total` 依序嘗試:`windows_cpu_logical_processor` → `windows_cs_logical_processors`(僅 0.30.6 需要) → 從 `windows_cpu_time_total` 的 `core` label 相異值數量推導(所有版本皆適用的最終備援)。

`host_cpu_cores_total`/`host_cpu_sockets_total`/`host_cpu_info` 依賴非預設啟用的 `cpu_info` collector,實務上經常缺席,屬預期常態,會反映在 `missing_metrics`。`host_memory_swap_*` 依賴 `pagefile` collector,雖文件標示預設啟用,但實測發現不一定會輸出,同樣視為常態缺席。`host_network_link_up` 依賴 `windows_net_nic_operation_status`,實測也不一定存在。

以上映射已用官方 collector 文件(`.agent/spec/metrics-mapping/windows_exporter/{0.30.6,0.31.6,0.31.7}/`)與一台實機(Windows 11 Pro,windows_exporter 0.30.6,`http://127.0.0.1:9182/metrics`)的即時擷取資料交叉驗證。

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
