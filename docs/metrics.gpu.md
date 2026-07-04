# gpu metrics

這組指標涵蓋 GPU 裝置資訊、專用顯示記憶體用量,以及引擎忙碌時間。**目前只支援 Windows**:node_exporter 官方沒有內建的 GPU collector(只有 AMD 專用、預設停用的 `drm` collector,且未涵蓋一般 GPU 使用率/記憶體語意),因此 Linux 主機上不會有任何 `host_gpu_*` 系列。

|||
-|-
Metric name prefix  | `host_gpu`
Source (windows_exporter) | `windows_gpu_info`, `windows_gpu_dedicated_video_memory_size_bytes`, `windows_gpu_adapter_memory_dedicated_bytes`, `windows_gpu_engine_time_seconds`(windows_exporter **0.31.6 / 0.31.7** 限定,且來源 `gpu` collector 需手動啟用:`--collectors.enabled=gpu`)
Source (node_exporter)    | 無(node_exporter 官方無對應來源)
Always emitted?      | 否。0.30.6 沒有 `gpu` collector;0.31.6/0.31.7 若主機未啟用 `gpu` collector 或沒有實體 GPU,也會完全不輸出這組指標

## Configuration

None(來源 `gpu` collector 是否啟用由 windows_exporter 端的 `--collectors.enabled` 設定決定,與本專案的設定檔無關)

## Metrics

| Name | Description | Type | Labels |
|---|---|---|---|
| `host_gpu_info` | Normalized GPU device information | gauge | `host`, `gpu`, `name`, `device_id` |
| `host_gpu_memory_total_bytes` | Normalized host GPU dedicated video memory total in bytes | gauge | `host`, `gpu` |
| `host_gpu_memory_used_bytes` | Normalized host GPU dedicated memory usage in bytes | gauge | `host`, `gpu` |
| `host_gpu_memory_usage_percent` | Normalized host GPU memory usage percentage | gauge | `host`, `gpu` |
| `host_gpu_engine_seconds_total` | Normalized host GPU engine busy time total in seconds | counter | `host`, `gpu`, `engtype` |

`gpu` label 對應來源 `windows_gpu_info` 的 `phys`(實體 GPU 索引,例如 `"0"`)。`host_gpu_engine_seconds_total` 已跨來源的 `process_id`(處理程序)與 `eng`(引擎實例索引)加總,只保留 `engtype`(引擎類型,例如 `3D`、`Copy`、`VideoDecode`)這個維度,不提供逐行程明細——與本專案其餘 `host_*` 指標一律是主機層級聚合的風格一致。

### 已知限制

- 不含 GPU 溫度(來源完全沒有這項資料,需要 `nvidia-smi`/DCGM 等廠商專用 exporter)。
- 不含使用率百分比:`windows_gpu_engine_time_seconds` 是純累積 counter,沒有像 CPU 的 idle/total 基準值可以在單次 scrape 內算出瞬間使用率,因此比照 disk/network 群組的政策,只輸出原始 counter,交給 PromQL `rate()` 換算。

### Example metric
```
host_gpu_info{host="gpu-01",gpu="0",name="NVIDIA GeForce RTX 3080",device_id="PCI\\VEN_10DE&DEV_1B81"} 1
host_gpu_memory_usage_percent{host="gpu-01",gpu="0"} 20.0
```

## Useful queries
用 `rate()` 換算 GPU 3D 引擎使用率(%)
```
rate(host_gpu_engine_seconds_total{engtype="3D"}[1m]) * 100
```

GPU 記憶體使用率超過 90% 的裝置
```
host_gpu_memory_usage_percent > 90
```

## Alerting examples
**prometheus.rules**
```yaml
- alert: HighGpuUtilization
  expr: rate(host_gpu_engine_seconds_total{engtype="3D"}[5m]) * 100 > 90
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "High GPU utilization ({{ $labels.host }} gpu {{ $labels.gpu }})"
    description: "GPU 3D engine utilization has been above 90% for 10 minutes.\n  VALUE = {{ $value }}\n  LABELS: {{ $labels }}"

- alert: HighGpuMemoryUsage
  expr: host_gpu_memory_usage_percent > 90
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "High GPU memory usage ({{ $labels.host }} gpu {{ $labels.gpu }})"
    description: "GPU dedicated memory usage has been above 90% for 10 minutes.\n  VALUE = {{ $value }}\n  LABELS: {{ $labels }}"
```
