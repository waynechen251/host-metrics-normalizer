# os metrics

這組指標描述主機的作業系統資訊與開機時間,將 Windows 與 Linux 的來源指標統一成同一個 schema,不論主機是哪個平台,PromQL 都能用同一組指標名稱查詢。

|||
-|-
Metric name prefix  | `host_os`, `host_uptime`
Source (windows_exporter) | `windows_os_info`, `windows_exporter_build_info`, `windows_system_boot_time_timestamp`
Source (node_exporter)    | `node_os_info`, `node_uname_info`, `node_exporter_build_info`, `node_boot_time_seconds`
Always emitted?      | `host_os_info` 一律輸出(缺少來源資訊時對應 label 留空字串);`host_uptime_seconds` 需要來源的開機時間指標存在才會輸出

## Configuration

None

## Metrics

| Name | Description | Type | Labels |
|---|---|---|---|
| `host_os_info` | Detected host operating system information | gauge | `host`, `os_family`, `os_name`, `os_version`, `kernel_version`, `architecture` |
| `host_uptime_seconds` | Normalized host uptime in seconds | gauge | `host` |

`os_family` 固定為 `windows` 或 `linux`(依偵測到的來源 exporter 類型決定,而非讀取來源指標的欄位)。`architecture` 由來源 exporter 的 `goarch`(build info)正規化而來,例如 `amd64` → `x86_64`、`aarch64`/`arm64` → `aarch64`。

### Example metric
```
host_os_info{host="web-01",os_family="linux",os_name="Ubuntu 22.04.4 LTS",os_version="22.04",kernel_version="5.15.0-105-generic",architecture="x86_64"} 1
host_uptime_seconds{host="web-01"} 1382445
```

## Useful queries
以天為單位顯示主機開機時間
```
host_uptime_seconds / 86400
```

依作業系統家族分組統計主機數量
```
count by (os_family) (host_os_info)
```

## Alerting examples
**prometheus.rules**
```yaml
- alert: HostRecentlyRebooted
  expr: host_uptime_seconds < 600
  labels:
    severity: info
  annotations:
    summary: "Host recently rebooted (instance {{ $labels.host }})"
    description: "Uptime is less than 10 minutes, the host may have just restarted.\n  VALUE = {{ $value }}\n  LABELS: {{ $labels }}"
```
