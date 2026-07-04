# host-metrics-normalizer 規格書 — 05. Mapping 規則

## 10. Mapping 規則

### 10.1 Windows exporter mapping

Phase 3 先以 `windows_exporter 0.30.6`、`0.31.6`、`0.31.7` 的 exact version registry 為準(見 `.agents/spec/metrics-mapping/windows_exporter/` 對應版本的官方 collector 文件)。
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

以上映射已用官方 collector 文件(`.agents/spec/metrics-mapping/windows_exporter/{0.30.6,0.31.6,0.31.7}/`)與一台實機(Windows 11 Pro,windows_exporter 0.30.6,`http://127.0.0.1:9182/metrics`)的即時擷取資料交叉驗證。

### 10.2 Node exporter mapping

Phase 3 先以 `node_exporter 1.10.2` 的 exact version registry 為準(見 `.agents/spec/metrics-mapping/node_exporter/1.10.2/`)。跟 windows_exporter 一樣,normalizer 只在版本完全符合時套用 Linux mapping;未列版本先視為 unsupported,不輸出 `host_*` 正規化指標。

來源可能包含：

```text
node_cpu_seconds_total
node_cpu_info                          # cpu.info 子功能,需要 --collector.cpu.info 旗標,非預設啟用
node_memory_MemTotal_bytes
node_memory_MemAvailable_bytes
node_memory_MemFree_bytes
node_memory_SwapTotal_bytes
node_memory_SwapFree_bytes
node_os_info
node_uname_info
node_filesystem_size_bytes
node_filesystem_avail_bytes
node_disk_io_now
node_disk_read_bytes_total
node_disk_written_bytes_total          # 注意是過去式 written,不是 write
node_disk_reads_completed_total
node_disk_writes_completed_total
node_network_receive_bytes_total
node_network_transmit_bytes_total
node_network_receive_errs_total
node_network_transmit_errs_total
node_network_up
node_network_speed_bytes               # 單位是 bytes/sec,轉換時需 ×8 才是 host_network_speed_bits 宣告的 bits/sec
node_boot_time_seconds
node_exporter_build_info
```

轉換為：

```text
host_os_info
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

`host_os_info` 由三個來源合成:`os_name`/`os_version` 取自 `node_os_info`(`pretty_name`/`version_id`),`kernel_version` 取自 `node_uname_info`(`release`),`architecture` 取自 `node_exporter_build_info`(`goarch`,與 windows_exporter 同一套 goarch 慣例,不解析 uname 的 `machine`)。

`host_memory_bytes_available` 主要來源是 `node_memory_MemAvailable_bytes`(排除 root 保留區塊、語意正確的「可用」),`node_memory_MemFree_bytes` 作為 fallback——這裡是全新規劃、沒有既有部署要遷就,跟 windows_exporter 的 `free_bytes` 優先(維持既有數值基準)是不同考量,不要誤以為兩邊政策不一致。

`host_filesystem_free_bytes` 對應 `node_filesystem_avail_bytes` 不是 `node_filesystem_free_bytes`——`avail_bytes` 才是 `df` 顯示的可用空間語意。`node_filesystem_size_bytes`/`avail_bytes` 本身就帶 `fstype` label,不像 windows_exporter 需要額外 join 一個 `*_info` family。

`host_cpu_threads_total` 直接從 `node_cpu_seconds_total` 的 `cpu` label 相異值數量推導——`cpu` collector 預設啟用,不需要像 windows_exporter 那樣多層 fallback。

`host_cpu_cores_total`/`host_cpu_sockets_total`/`host_cpu_info` 依賴 `node_cpu_info`(`cpu.info` 子功能,需要額外的 `--collector.cpu.info` 旗標,非預設啟用),實務上經常缺席,屬預期常態,會反映在 `missing_metrics`,與 windows_exporter 的 `cpu_info` collector 同樣性質。

`host_network_link_up` 直接讀 `node_network_up`(值已經是 0/1),不需要像 windows_exporter 的 `nic_operation_status` 那樣解析狀態字串。

Counter 類指標(`node_cpu_seconds_total`、`node_disk_*_total`、`node_network_*_total`)一樣要用「帶 `_total` 的官方名稱」與「去掉後綴的裸名稱」雙名稱 fallback 查找,原因與 windows_exporter 相同(`prometheus_client` parser 對 counter 類型會去除 family name 的 `_total` 後綴,是 parser 層級行為、不分 exporter)。

`node_network_speed_bytes` 若介面沒有協商到速度(常見於 bridge、down 狀態的介面),核心會透過 sysfs 回報 `-1`,node_exporter 原樣透傳成負的 bytes/sec;mapping 會過濾負值,該介面直接不輸出 `host_network_speed_bits`(不是缺席整個 family,只是該筆 sample 略過)。這是拿內部真實 Linux 主機(有大量 Docker bridge/veth 介面)實測後才發現的落差,`node_cpu_info` 因為未啟用 `--collector.cpu.info` 而缺席則完全符合預期。

以上映射已用 node_exporter 專案自己的 end-to-end 測試黃金輸出(`.agents/spec/metrics-mapping/node_exporter/1.10.2/e2e-output-linux.txt`)與本機 clone 的 Go 原始碼(`collector/*.go`)交叉驗證;`node_uname_info`/`node_filesystem_*`/`node_memory_MemAvailable_bytes`/network rx-tx 的 sample 數值因為 node_exporter 自己的 e2e 測試腳本刻意停用或濾除而無法從這份輸出核對到實際數值(collector 名稱與 labels 已改查 Go 原始碼確認),等使用者拿內部真實 Linux 主機實測後再校正。

### 10.3 Rate 類指標處理

MVP 一律輸出 normalized counter，讓 Grafana / Prometheus 用 `rate()`、`irate()` 或 recording rule 自行計算速率。

例如：

```text
host_network_receive_bytes_total
host_network_transmit_bytes_total
```

`host_cpu_usage_percent` 與 `host_memory_usage_percent` 仍以 gauge 直接輸出；它們不是 counter-rate 轉換的結果。
