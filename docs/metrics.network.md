# network metrics

這組指標涵蓋網路介面的流量、錯誤計數、連線狀態與協商速度,`nic` label 為介面名稱。

|||
-|-
Metric name prefix  | `host_network`
Source (windows_exporter) | `windows_net_bytes_received_total`, `windows_net_bytes_sent_total`, `windows_net_packets_received_errors_total`, `windows_net_packets_outbound_errors_total`, `windows_net_nic_operation_status`, `windows_net_current_bandwidth_bytes`
Source (node_exporter)    | `node_network_receive_bytes_total`, `node_network_transmit_bytes_total`, `node_network_receive_errs_total`, `node_network_transmit_errs_total`, `node_network_up`, `node_network_speed_bytes`
Always emitted?      | 依來源指標是否存在;`host_network_speed_bits` 在來源回報負值(代表無已知連線速度,例如 bridge 或 down 介面)時會被跳過,不輸出該介面的序列

## Configuration

- `normalization.network_ignore_regex`:可設定一組正規表示式,符合的網卡名稱不會出現在 `host_network_*` 指標中(例如排除虛擬網卡、loopback)。

## Metrics

| Name | Description | Type | Labels |
|---|---|---|---|
| `host_network_receive_bytes_total` | Normalized host network receive bytes total | counter | `host`, `nic` |
| `host_network_transmit_bytes_total` | Normalized host network transmit bytes total | counter | `host`, `nic` |
| `host_network_receive_errors_total` | Normalized host network receive errors total | counter | `host`, `nic` |
| `host_network_transmit_errors_total` | Normalized host network transmit errors total | counter | `host`, `nic` |
| `host_network_link_up` | Normalized host network interface link status | gauge | `host`, `nic` |
| `host_network_speed_bits` | Normalized host network interface speed in bits per second | gauge | `host`, `nic` |

### Example metric
```
host_network_link_up{host="web-01",nic="eth0"} 1
host_network_speed_bits{host="web-01",nic="eth0"} 1000000000
```

## Useful queries
每張網卡的即時流量(bytes/秒)
```
rate(host_network_receive_bytes_total[5m]) + rate(host_network_transmit_bytes_total[5m])
```

以連結速度換算頻寬使用率(%)
```
rate(host_network_receive_bytes_total[5m]) * 8 / host_network_speed_bits * 100
```

找出目前連線中斷(link down)的網卡
```
host_network_link_up == 0
```

## Alerting examples
**prometheus.rules**
```yaml
- alert: NetworkInterfaceDown
  expr: host_network_link_up == 0
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Network interface down ({{ $labels.host }} {{ $labels.nic }})"
    description: "Interface {{ $labels.nic }} has been reporting link down for 5 minutes.\n  LABELS: {{ $labels }}"

- alert: NetworkErrorsHigh
  expr: rate(host_network_receive_errors_total[5m]) + rate(host_network_transmit_errors_total[5m]) > 0
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "Network errors detected ({{ $labels.host }} {{ $labels.nic }})"
    description: "Interface {{ $labels.nic }} is reporting a non-zero error rate.\n  VALUE = {{ $value }}\n  LABELS: {{ $labels }}"
```
