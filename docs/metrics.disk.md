# disk metrics

這組指標涵蓋實體磁碟(在 Windows 上對應 Physical Disk,在 Linux 上對應 block device)的 I/O 吞吐量、操作次數與佇列長度,`disk` label 為磁碟識別碼(Windows 為磁碟編號,Linux 為裝置名稱如 `sda`)。

|||
-|-
Metric name prefix  | `host_disk`
Source (windows_exporter) | `windows_physical_disk_requests_queued`, `windows_physical_disk_read_bytes_total`, `windows_physical_disk_write_bytes_total`, `windows_physical_disk_reads_total`, `windows_physical_disk_writes_total`
Source (node_exporter)    | `node_disk_io_now`, `node_disk_read_bytes_total`, `node_disk_written_bytes_total`, `node_disk_reads_completed_total`, `node_disk_writes_completed_total`
Always emitted?      | 依來源指標是否存在;缺少時對應的 `host_disk_*` 指標會被跳過

## Configuration

None

## Metrics

| Name | Description | Type | Labels |
|---|---|---|---|
| `host_disk_queue_length` | Normalized host physical disk queue length | gauge | `host`, `disk` |
| `host_disk_read_bytes_total` | Normalized host physical disk read bytes total | counter | `host`, `disk` |
| `host_disk_write_bytes_total` | Normalized host physical disk write bytes total | counter | `host`, `disk` |
| `host_disk_reads_total` | Normalized host physical disk read operations total | counter | `host`, `disk` |
| `host_disk_writes_total` | Normalized host physical disk write operations total | counter | `host`, `disk` |

### Example metric
```
host_disk_read_bytes_total{host="web-01",disk="0"} 48213762048
host_disk_queue_length{host="web-01",disk="0"} 1.2
```

## Useful queries
計算每顆磁碟的讀寫吞吐量(bytes/秒)
```
rate(host_disk_read_bytes_total[5m]) + rate(host_disk_write_bytes_total[5m])
```

計算每顆磁碟的 IOPS
```
rate(host_disk_reads_total[5m]) + rate(host_disk_writes_total[5m])
```

## Alerting examples
**prometheus.rules**
```yaml
- alert: HighDiskQueueLength
  expr: host_disk_queue_length > 2
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "High disk queue length ({{ $labels.host }} disk {{ $labels.disk }})"
    description: "Disk queue length has been above 2 for 10 minutes, indicating the disk may be a bottleneck.\n  VALUE = {{ $value }}\n  LABELS: {{ $labels }}"
```
