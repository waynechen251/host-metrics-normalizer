# asset metrics

`host_asset_info` 是唯一不從來源 exporter 讀取資料的「主機」指標:它的 label 值完全來自設定檔 `asset.*` 區塊,用來補上 CMDB 等級的中介資料(owner、environment、location 等),讓 Grafana 可以依這些維度篩選、分組主機。

|||
-|-
Metric name prefix  | `host_asset`
Source               | 設定檔 `asset.*` 區塊(見 [`configs/config.example.yml`](../configs/config.example.yml)),非來自 windows_exporter/node_exporter
Always emitted?      | Yes(即使所有欄位皆為空字串,仍會輸出一筆值為 `1` 的序列)

## Configuration

`asset.*` 的每個欄位都會被帶入對應的 label:

| 設定欄位(`AssetConfig`) | 對應 label | 說明 |
|---|---|---|
| `asset_id` | `asset_id` | 資產編號 |
| `hostname` | (影響 `host` label,見下方說明) | 若有填寫則覆蓋自動偵測的主機名稱 |
| `display_name` | `display_name` | 顯示名稱 |
| `owner` | `owner` | 負責人/團隊 |
| `environment` | `environment` | 環境(如 production / staging) |
| `location` | `location` | 機房/地區 |
| `role` | `role` | 主機用途角色 |
| `criticality` | `criticality` | 重要程度 |
| `managed_by` | `managed_by` | 維運單位 |
| `note` | (不輸出至指標) | 僅供設定檔內部備註使用 |

`host` label 的值:若 `asset.hostname` 有設定則直接採用,否則退回作業系統回報的 `socket.gethostname()`。

## Metrics

| Name | Description | Type | Labels |
|---|---|---|---|
| `host_asset_info` | Static host asset metadata | gauge | `host`, `asset_id`, `display_name`, `owner`, `environment`, `location`, `role`, `criticality`, `managed_by` |

### Example metric
```
host_asset_info{host="web-01",asset_id="AST-1024",display_name="Web Server 01",owner="platform-team",environment="production",location="tw-north-1",role="web",criticality="high",managed_by="ops"} 1
```

## Useful queries
依 `environment` 與 `owner` join 其他 `host_*` 指標,做跨環境的分組統計
```
sum by (environment) (host_cpu_usage_percent * on(host) group_left(environment) host_asset_info)
```

列出所有 `criticality="high"` 的主機
```
host_asset_info{criticality="high"}
```

## Alerting examples
**prometheus.rules**
```yaml
- alert: CriticalHostMemoryUsage
  expr: host_memory_usage_percent * on(host) group_left(criticality, owner) host_asset_info{criticality="high"} > 90
  for: 10m
  labels:
    severity: critical
  annotations:
    summary: "High memory usage on a critical host ({{ $labels.host }})"
    description: "Memory usage is above 90% on a criticality=high host owned by {{ $labels.owner }}.\n  VALUE = {{ $value }}\n  LABELS: {{ $labels }}"
```
