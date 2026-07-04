# cpu metrics

這組指標涵蓋 CPU 使用率、邏輯執行緒/實體核心/插槽數量,以及 CPU 型號資訊。使用率計算方式為:所有 CPU 時間模式中,非 `idle` 的比例(`100 * (1 - idle / total)`),因此在 Windows 與 Linux 上具有一致的語意。

|||
-|-
Metric name prefix  | `host_cpu`
Source (windows_exporter) | `windows_cpu_time_total`, `windows_cpu_info_core`, `windows_cpu_info`, `windows_cpu_logical_processor`(僅 0.30.6)
Source (node_exporter)    | `node_cpu_seconds_total`, `node_cpu_info`
Always emitted?      | 依來源指標是否存在;缺少時對應的 `host_cpu_*` 指標會被跳過,不會輸出殘缺或補零的序列

## Configuration

None

## Metrics

| Name | Description | Type | Labels |
|---|---|---|---|
| `host_cpu_usage_percent` | Normalized host CPU usage percentage | gauge | `host` |
| `host_cpu_threads_total` | Normalized host logical CPU threads total | gauge | `host` |
| `host_cpu_cores_total` | Normalized host physical CPU cores total | gauge | `host` |
| `host_cpu_sockets_total` | Normalized host CPU sockets total | gauge | `host` |
| `host_cpu_info` | Normalized host CPU model information | gauge | `host`, `model`, `architecture` |

### 版本差異(windows_exporter)

`host_cpu_threads_total` 在不同 windows_exporter 版本上取值方式不同:0.30.6 優先讀取已標記為 deprecated 的 `windows_cpu_logical_processor`(或其前身 `windows_cs_logical_processors`),缺少時才退回以 `windows_cpu_time_total` 的 distinct `core` label 數量估算;0.31.6 與 0.31.7 已移除 `cs` collector,一律以 distinct `core` label 數量估算。對外輸出的 `host_cpu_threads_total` 語意一致,不受此差異影響。

### Example metric
```
host_cpu_usage_percent{host="web-01"} 23.5
host_cpu_info{host="web-01",model="Intel(R) Xeon(R) Gold 6248R CPU @ 3.00GHz",architecture="x86_64"} 1
```

## Useful queries
CPU 使用率超過 80% 的主機清單
```
host_cpu_usage_percent > 80
```

計算每個插槽平均分配到的核心數
```
host_cpu_cores_total / host_cpu_sockets_total
```

## Alerting examples
**prometheus.rules**
```yaml
- alert: HighCpuUsage
  expr: host_cpu_usage_percent > 80
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "High CPU usage (instance {{ $labels.host }})"
    description: "CPU usage has been above 80% for 10 minutes.\n  VALUE = {{ $value }}\n  LABELS: {{ $labels }}"
```
