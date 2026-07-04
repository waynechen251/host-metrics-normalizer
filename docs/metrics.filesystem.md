# filesystem metrics

這組指標涵蓋檔案系統(Windows 邏輯磁碟區 / Linux 掛載點)的容量與使用率。同一個掛載點的容量、可用空間與使用率共用一組 `mount`/`filesystem`/`role` label,方便用 join 或單一 series 直接計算。

|||
-|-
Metric name prefix  | `host_filesystem`
Source (windows_exporter) | `windows_logical_disk_size_bytes`, `windows_logical_disk_free_bytes`, `windows_logical_disk_info`(用於補上 `filesystem` label)
Source (node_exporter)    | `node_filesystem_size_bytes`, `node_filesystem_avail_bytes`(每筆 sample 已自帶 `fstype`)
Always emitted?      | 依來源指標是否存在;`host_filesystem_usage_percent` 只在 size 與 free 兩者皆有值且 size > 0 時才會計算

## Configuration

- `normalization.filesystem_ignore_regex`:可設定一組正規表示式,符合的掛載點/磁碟區名稱不會出現在 `host_filesystem_*` 指標中(例如排除唯讀的光碟機、暫存掛載點)。

## Metrics

| Name | Description | Type | Labels |
|---|---|---|---|
| `host_filesystem_size_bytes` | Normalized host filesystem size in bytes | gauge | `host`, `mount`, `filesystem`, `role` |
| `host_filesystem_free_bytes` | Normalized host filesystem free bytes | gauge | `host`, `mount`, `filesystem`, `role` |
| `host_filesystem_usage_percent` | Normalized host filesystem usage percentage | gauge | `host`, `mount`, `filesystem`, `role` |

`role` label 只有在 `mount` 為 `C:`(Windows)或 `/`(Linux)時會自動填入 `system`,代表系統磁碟區;其餘掛載點的 `role` 為空字串。

### Example metric
```
host_filesystem_size_bytes{host="web-01",mount="/",filesystem="ext4",role="system"} 107374182400
host_filesystem_usage_percent{host="web-01",mount="/data",filesystem="xfs",role=""} 78.4
```

## Useful queries
使用率超過 90% 的檔案系統
```
host_filesystem_usage_percent > 90
```

預測系統磁碟區四天內是否會填滿
```
predict_linear(host_filesystem_free_bytes{role="system"}[6h], 4 * 24 * 3600) < 0
```

## Alerting examples
**prometheus.rules**
```yaml
- alert: DiskSpaceUsage
  expr: host_filesystem_usage_percent > 90
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "Disk space usage high ({{ $labels.host }} {{ $labels.mount }})"
    description: "Filesystem {{ $labels.mount }} is more than 90% full.\n  VALUE = {{ $value }}\n  LABELS: {{ $labels }}"

- alert: DiskWillFillInFourDays
  expr: predict_linear(host_filesystem_free_bytes[6h], 4 * 24 * 3600) < 0
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "Disk predicted to fill within four days ({{ $labels.host }} {{ $labels.mount }})"
    description: "Based on the last 6h trend, {{ $labels.mount }} is expected to run out of space within four days.\n  LABELS: {{ $labels }}"
```
