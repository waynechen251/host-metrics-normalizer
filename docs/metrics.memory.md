# memory metrics

這組指標涵蓋實體記憶體與 swap/分頁檔的容量與使用率。Windows 的分頁檔(pagefile)與 Linux 的 swap 分割區在語意上對應,統一輸出為 `host_memory_swap_*`。

|||
-|-
Metric name prefix  | `host_memory`
Source (windows_exporter) | `windows_memory_physical_total_bytes`, `windows_memory_physical_free_bytes`(或 `windows_memory_available_bytes`), `windows_pagefile_limit_bytes`, `windows_pagefile_free_bytes`
Source (node_exporter)    | `node_memory_MemTotal_bytes`, `node_memory_MemAvailable_bytes`(或 `node_memory_MemFree_bytes`), `node_memory_SwapTotal_bytes`, `node_memory_SwapFree_bytes`
Always emitted?      | 依來源指標是否存在;`host_memory_swap_bytes_total` 為 `0` 時不計算 `host_memory_swap_usage_percent`(避免除以零)

## Configuration

None

## Metrics

| Name | Description | Type | Labels |
|---|---|---|---|
| `host_memory_bytes_total` | Normalized host physical memory total in bytes | gauge | `host` |
| `host_memory_bytes_available` | Normalized host physical memory available in bytes | gauge | `host` |
| `host_memory_usage_percent` | Normalized host memory usage percentage | gauge | `host` |
| `host_memory_swap_bytes_total` | Normalized host swap/pagefile total in bytes | gauge | `host` |
| `host_memory_swap_usage_percent` | Normalized host swap/pagefile usage percentage | gauge | `host` |

### Example metric
```
host_memory_bytes_total{host="web-01"} 17179869184
host_memory_usage_percent{host="web-01"} 61.2
```

## Useful queries
記憶體使用率超過 90% 的主機
```
host_memory_usage_percent > 90
```

換算成 GiB 顯示可用記憶體
```
host_memory_bytes_available / 1024 / 1024 / 1024
```

## Alerting examples
**prometheus.rules**
```yaml
- alert: HighMemoryUsage
  expr: host_memory_usage_percent > 90
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "High memory usage (instance {{ $labels.host }})"
    description: "Memory usage has been above 90% for 10 minutes.\n  VALUE = {{ $value }}\n  LABELS: {{ $labels }}"

- alert: HighSwapUsage
  expr: host_memory_swap_usage_percent > 50
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "High swap/pagefile usage (instance {{ $labels.host }})"
    description: "Swap or pagefile usage has been above 50% for 10 minutes, indicating memory pressure.\n  VALUE = {{ $value }}\n  LABELS: {{ $labels }}"
```
