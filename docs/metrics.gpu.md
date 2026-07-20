# gpu metrics

這組指標供混合 Windows/Linux、NVIDIA/AMD/Intel fleet 使用。**與 windows_exporter/node_exporter 完全無關**：normalizer 自行偵測可用的本機 GPU 介面，Grafana 永遠只查 `host_gpu_*`，不需要依 OS、廠商或採集 backend 分支。

|||
-|-
Metric name prefix  | `host_gpu`
Source (Windows)     | WMI/PDH generic fallback；NVIDIA 優先使用 driver 提供的 NVML
Source (Linux)        | DRM/sysfs generic fallback；NVIDIA 優先使用 NVML
Always emitted?      | `host_gpu_collection_up`、`host_gpu_devices_total` 永遠輸出；`host_gpu_info` 只要偵測到裝置就輸出；感測值以 `host_gpu_metric_available` 宣告是否可用
Configuration         | `gpu.enabled`(預設 `true`),設為 `false` 完全停用本機 GPU 採集

## Configuration
```yaml
gpu:
  enabled: true
```

## Metrics

| Name | Description | Type | Labels |
|---|---|---|---|
| `host_gpu_collection_up` | GPU 採集是否成功；沒有 GPU 時仍為 1 | gauge | `host` |
| `host_gpu_devices_total` | 偵測到的 GPU 數量 | gauge | `host` |
| `host_gpu_collection_errors_total` | GPU 採集失敗累計次數 | counter | `host` |
| `host_gpu_scrape_duration_seconds` | GPU 採集耗時 | gauge | `host` |
| `host_gpu_info` | Normalized GPU device information | gauge | `host`, `gpu`, `vendor`, `name`, `device_id` |
| `host_gpu_memory_total_bytes` | Normalized host GPU dedicated video memory total in bytes | gauge | `host`, `gpu` |
| `host_gpu_memory_used_bytes` | Normalized host GPU dedicated memory usage in bytes | gauge | `host`, `gpu` |
| `host_gpu_memory_usage_percent` | Normalized host GPU memory usage percentage | gauge | `host`, `gpu` |
| `host_gpu_utilization_percent` | Normalized host GPU utilization percentage | gauge | `host`, `gpu` |
| `host_gpu_temperature_celsius` | Normalized host GPU temperature in degrees Celsius | gauge | `host`, `gpu` |
| `host_gpu_power_watts` | Normalized host GPU power draw in watts | gauge | `host`, `gpu` |
| `host_gpu_metric_available` | 感測值是否可用（`utilization`、`memory`、`temperature`、`power`） | gauge | `host`, `gpu`, `metric` |

`gpu` label 是主機上 GPU 的索引；`vendor` 固定為 `nvidia`、`amd`、`intel` 或 `unknown`。`device_id` 一律採小寫 PCI `vendor:device` 格式。動態 metrics 只使用 `host`,`gpu`，避免 dashboard 依廠商或 OS 分支。

### 已知限制

- **能力缺席是正常資料**：不支援或無權限讀取某感測值時，對應 dynamic series 缺席，並輸出 `host_gpu_metric_available{metric="..."} 0`。Grafana 必須顯示 `N/A`，不得當作 0。
- **NVIDIA 優先 NVML**：NVIDIA driver 可提供 NVML 時，使用率、顯存、溫度與功耗會覆蓋 generic fallback，適用 Windows/Linux。
- **AMD / Intel enrichment 尚未完成**：AMD/Linux 仍可由 amdgpu sysfs 取得顯存、使用率與溫度；AMD/Windows、Intel 的進階溫度/功耗仍待 ADLX / Level Zero backend。
- **Windows 使用率首次請求會缺席**:`host_gpu_utilization_percent` 由 Performance Counters 的兩次取樣差值計算而來(與 windows_exporter 自身讀取這組計數器的方式相同),程序啟動後第一次 `/metrics` 或 `/debug/gpu` 請求還沒有前一筆樣本可比較,該次會缺少這個指標,從第二次請求起才會出現。
- **Windows generic fallback 的多 GPU 對應仍是盡力而為**：NVIDIA 有 NVML 時以 PCI ID 合併而不受此限；AMD/Intel Windows 的精確 LUID 對應待後續 backend 完成。

### Example metric
```
host_gpu_collection_up{host="gpu-01"} 1
host_gpu_devices_total{host="gpu-01"} 1
host_gpu_info{host="gpu-01",gpu="0",vendor="nvidia",name="NVIDIA GeForce RTX 3080",device_id="10de:1b81"} 1
host_gpu_memory_usage_percent{host="gpu-01",gpu="0"} 20.0
host_gpu_utilization_percent{host="gpu-01",gpu="0"} 42.5
host_gpu_metric_available{host="gpu-01",gpu="0",metric="power"} 1
```

## Useful queries
GPU 使用率超過 90% 的裝置
```
host_gpu_utilization_percent > 90
```

GPU 記憶體使用率超過 90% 的裝置
```
host_gpu_memory_usage_percent > 90
```

## Alerting examples
**prometheus.rules**
```yaml
- alert: HighGpuUtilization
  expr: host_gpu_utilization_percent > 90
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "High GPU utilization ({{ $labels.host }} gpu {{ $labels.gpu }})"
    description: "GPU utilization has been above 90% for 10 minutes.\n  VALUE = {{ $value }}\n  LABELS: {{ $labels }}"

- alert: HighGpuMemoryUsage
  expr: host_gpu_memory_usage_percent > 90
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "High GPU memory usage ({{ $labels.host }} gpu {{ $labels.gpu }})"
    description: "GPU dedicated memory usage has been above 90% for 10 minutes.\n  VALUE = {{ $value }}\n  LABELS: {{ $labels }}"
```
