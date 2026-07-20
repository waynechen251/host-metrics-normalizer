# host-metrics-normalizer 規格書 — 04. Metric 命名與清單

## 8. Metric 命名規範

所有標準化後的指標使用 `host_` prefix。

內部狀態使用：

```text
host_normalizer_*
host_source_exporter_*
```

資產資料使用：

```text
host_asset_info
host_os_info
host_hardware_info
```

### 8.1 Label 命名規範

建議共用 labels：

```text
host
asset_id
os_family
role
environment
location
owner
```

避免使用高基數或高變動 label：

1. 不要把時間戳放 label。
2. 不要把錯誤完整訊息放 label。
3. 不要把即時數值放 label。
4. 不要把完整檔案路徑大量放 label，除非已經過濾。

## 9. 必要 Metrics 規格

### 9.1 Normalizer 本體

```text
host_normalizer_info{version="0.1.0", config_version="manual"} 1
host_normalizer_up 1
host_normalizer_scrape_duration_seconds 0.123
host_normalizer_last_scrape_timestamp_seconds 1782739527
host_normalizer_last_scrape_success 1
host_normalizer_errors_total 0
host_metrics_stale 0
```

### 9.2 Source Exporter

```text
host_source_exporter_info{
  exporter="windows_exporter",
  endpoint="http://127.0.0.1:9182/metrics",
  version="0.30.6"
} 1

host_source_exporter_up{exporter="windows_exporter"} 1
host_source_exporter_scrape_duration_seconds{exporter="windows_exporter"} 0.082
host_source_exporter_last_scrape_success{exporter="windows_exporter"} 1
host_source_exporter_errors_total{exporter="windows_exporter"} 0
```

Linux 範例：

```text
host_source_exporter_info{
  exporter="node_exporter",
  endpoint="http://127.0.0.1:9100/metrics",
  version="1.8.2"
} 1
```

`exporter` 與 `version` 來自自動偵測（見 [02-tech-and-config.md](02-tech-and-config.md) §6.2），非人工配置。在第一次成功偵測到 exporter 類型之前，**不輸出**任何帶 `exporter` label 的 `host_source_exporter_*` 系列，避免 Prometheus 殘留 `exporter="unknown"` 的過渡 time series。

### 9.3 Asset Info

```text
host_asset_info{
  host="srv-app-01",
  asset_id="ASSET-001",
  display_name="App Server 01",
  owner="infra",
  environment="prod",
  location="office-3f",
  role="app-server",
  criticality="medium",
  managed_by="wayne"
} 1
```

### 9.4 OS Info

```text
host_os_info{
  host="srv-app-01",
  os_family="windows",
  os_name="Windows 10 Pro",
  os_version="22H2",
  kernel_version="10.0.19045",
  architecture="x86_64"
} 1
```

Linux：

```text
host_os_info{
  host="srv-docker-01",
  os_family="linux",
  os_name="Ubuntu",
  os_version="22.04",
  kernel_version="5.15.0-xx-generic",
  architecture="x86_64"
} 1
```

### 9.5 Hardware Info

```text
host_hardware_info{
  host="srv-app-01",
  manufacturer="Dell Inc.",
  model="OptiPlex 7080",
  serial="ABC123",
  virtualized="false",
  hypervisor="none"
} 1
```

虛擬機：

```text
host_hardware_info{
  host="vm-app-01",
  manufacturer="VMware, Inc.",
  model="VMware Virtual Platform",
  serial="unknown",
  virtualized="true",
  hypervisor="vmware"
} 1
```

### 9.6 CPU

```text
host_cpu_info{
  host="srv-app-01",
  model="Intel(R) Core(TM) i7-14700",
  architecture="x86_64"
} 1

host_cpu_cores_total{host="srv-app-01"} 20
host_cpu_threads_total{host="srv-app-01"} 28
host_cpu_sockets_total{host="srv-app-01"} 1
host_cpu_usage_percent{host="srv-app-01"} 37.5
```

### 9.7 Memory

```text
host_memory_bytes_total{host="srv-app-01"} 137438953472
host_memory_bytes_available{host="srv-app-01"} 68719476736
host_memory_usage_percent{host="srv-app-01"} 50.0
host_memory_swap_bytes_total{host="srv-app-01"} 17179869184
host_memory_swap_usage_percent{host="srv-app-01"} 5.0
```

### 9.8 Filesystem / Disk

```text
host_filesystem_size_bytes{host="srv-app-01", mount="C:", filesystem="NTFS", role="system"} 512110190592
host_filesystem_free_bytes{host="srv-app-01", mount="C:", filesystem="NTFS", role="system"} 120034123776
host_filesystem_usage_percent{host="srv-app-01", mount="C:", filesystem="NTFS", role="system"} 76.5
```

Linux：

```text
host_filesystem_size_bytes{host="srv-docker-01", mount="/", filesystem="ext4", role="system"} 107374182400
host_filesystem_free_bytes{host="srv-docker-01", mount="/", filesystem="ext4", role="system"} 53687091200
host_filesystem_usage_percent{host="srv-docker-01", mount="/", filesystem="ext4", role="system"} 50.0
```

Disk I/O(counter，速率交給 Prometheus `rate()`/`irate()` 計算，與 §9.9 network 指標的政策一致)：

```text
host_disk_read_bytes_total{host="srv-app-01", disk="0"} 123456789
host_disk_write_bytes_total{host="srv-app-01", disk="0"} 987654321
host_disk_reads_total{host="srv-app-01", disk="0"} 4242
host_disk_writes_total{host="srv-app-01", disk="0"} 1337
host_disk_queue_length{host="srv-app-01", disk="0"} 0.2
```

### 9.9 Network

```text
host_network_receive_bytes_total{host="srv-app-01", nic="Ethernet"} 123456
host_network_transmit_bytes_total{host="srv-app-01", nic="Ethernet"} 654321
host_network_receive_errors_total{host="srv-app-01", nic="Ethernet"} 0
host_network_transmit_errors_total{host="srv-app-01", nic="Ethernet"} 0
host_network_link_up{host="srv-app-01", nic="Ethernet"} 1
host_network_speed_bits{host="srv-app-01", nic="Ethernet"} 1000000000
```

### 9.10 Uptime

```text
host_uptime_seconds{host="srv-app-01"} 1234567
```

### 9.11 GPU

與 §9.1–§9.10 不同：`host_gpu_*` **不是**由來源 exporter 的指標正規化而來，而是 normalizer 自行採集。本機會自動選擇可用的 OS 與廠商介面（Windows：WMI/PDH，Linux：DRM/sysfs；NVIDIA：NVML），完全獨立於 `source_exporter` 是否抓取成功。Grafana 僅查詢 `host_gpu_*`，不得依 OS、廠商或採集 backend 分支。

```text
host_gpu_collection_up{host="srv-app-01"} 1
host_gpu_devices_total{host="srv-app-01"} 1
host_gpu_info{host="srv-app-01", gpu="0", vendor="nvidia", name="NVIDIA GeForce RTX 3080", device_id="10de:1b81"} 1
host_gpu_memory_total_bytes{host="srv-app-01", gpu="0"} 10737418240
host_gpu_memory_used_bytes{host="srv-app-01", gpu="0"} 2147483648
host_gpu_memory_usage_percent{host="srv-app-01", gpu="0"} 20.0
host_gpu_utilization_percent{host="srv-app-01", gpu="0"} 42.5
host_gpu_temperature_celsius{host="srv-app-01", gpu="0"} 65.0
host_gpu_metric_available{host="srv-app-01", gpu="0", metric="power"} 0
```

必要的 fleet 狀態指標：

| Metric | Labels | 語意 |
|---|---|---|
| `host_gpu_collection_up` | `host` | 本次 GPU 採集是否成功執行；沒有 GPU 時仍為 `1` |
| `host_gpu_devices_total` | `host` | 偵測到的 GPU 數量 |
| `host_gpu_collection_errors_total` | `host` | GPU 採集失敗累計次數 |
| `host_gpu_scrape_duration_seconds` | `host` | 本次 GPU 採集耗時 |
| `host_gpu_metric_available` | `host`,`gpu`,`metric` | 固定能力集合（`utilization`、`memory`、`temperature`、`power`）是否可取得；Grafana 顯示 `N/A`，不得補為 0 |

`host_gpu_info` 的 `vendor` 固定為 `nvidia`、`amd`、`intel` 或 `unknown`；`device_id` 一律為小寫 PCI `vendor:device` 格式。所有動態 GPU 指標只有 `host`,`gpu` labels，不加 OS、廠商與 backend labels。

`host_gpu_memory_*` 只表示 dedicated/device-local memory；內顯或不提供 dedicated memory 的裝置不輸出該值，並以 `host_gpu_metric_available{metric="memory"} 0` 表示。`gpu.enabled`（預設 `true`）控制整組採集。
