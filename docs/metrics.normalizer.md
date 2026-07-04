# normalizer metrics

這組指標描述 host-metrics-normalizer 自身的執行狀態,以及它對來源 exporter(`windows_exporter` / `node_exporter`)最近一次抓取的健康狀況。它們是由 host-metrics-normalizer 自己產生的,不是從來源 exporter 轉換而來。

|||
-|-
Metric name prefix  | `host_normalizer`, `host_source_exporter`, `host_metrics_stale`
Source               | 由 host-metrics-normalizer 內部產生(每次 `/metrics` 被 scrape 時即時更新)
Always emitted?      | `host_normalizer_*` 與 `host_metrics_stale` 一律輸出;`host_source_exporter_*` 系列要等第一次成功偵測到來源 exporter 類型後才會出現(見下方說明)

## Configuration

- `cache.stale_after_seconds`(預設 `180`):超過這個秒數沒有成功抓取到來源 exporter,`host_metrics_stale` 會被設為 `1`。
- `source_exporter.endpoint` / `source_exporter.timeout_seconds`:決定要抓取哪個來源 exporter 端點與逾時秒數,影響 `host_source_exporter_*` 系列的 `exporter` label 內容與抓取行為。

## Metrics

| Name | Description | Type | Labels |
|---|---|---|---|
| `host_normalizer_info` | host-metrics-normalizer build info | info | `version`, `config_version` |
| `host_normalizer_up` | Whether the host-metrics-normalizer process is running | gauge | None |
| `host_normalizer_scrape_duration_seconds` | Duration of the last source exporter scrape and normalization | gauge | None |
| `host_normalizer_last_scrape_timestamp_seconds` | Unix timestamp of the last source exporter scrape attempt | gauge | None |
| `host_normalizer_last_scrape_success` | Whether the last source exporter scrape succeeded | gauge | None |
| `host_normalizer_errors_total` | Total number of normalizer errors | counter | None |
| `host_metrics_stale` | Whether the currently served metrics are stale | gauge | None |
| `host_source_exporter_info` | Detected source exporter build info | info | `exporter`, `endpoint`, `version` |
| `host_source_exporter_up` | Whether the last scrape of the source exporter succeeded | gauge | `exporter` |
| `host_source_exporter_scrape_duration_seconds` | Duration of the last source exporter scrape | gauge | `exporter` |
| `host_source_exporter_last_scrape_success` | Whether the last source exporter scrape succeeded | gauge | `exporter` |
| `host_source_exporter_errors_total` | Total number of source exporter scrape errors | counter | `exporter` |

### 關於 `exporter` label 的穩定性

在第一次成功偵測到來源 exporter 種類(`windows_exporter` 或 `node_exporter`)之前,`host_source_exporter_*` 系列完全不會輸出,避免產生一段短暫的 `exporter="unknown"` 序列殘留在 Prometheus 裡。若執行期間偵測到的 exporter 種類改變(例如切換來源主機類型),舊 label 的 gauge 會被清空、error 計數器歸零重建於新 label 上,而不是同時保留新舊兩組序列。

### Example metric
`host_metrics_stale` 只有在超過 `cache.stale_after_seconds` 沒有成功抓取時才會轉為 `1`:
```
host_metrics_stale 0
host_source_exporter_up{exporter="windows_exporter"} 1
```

## Useful queries
確認目前是否在使用降級快取(來源 exporter 已經一段時間抓不到)
```
host_metrics_stale == 1
```

計算最近一次抓取距今已過多久
```
time() - host_normalizer_last_scrape_timestamp_seconds
```

## Alerting examples
**prometheus.rules**
```yaml
- alert: HostMetricsStale
  expr: host_metrics_stale == 1
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "Host metrics are stale (instance {{ $labels.instance }})"
    description: "host-metrics-normalizer has not successfully scraped its source exporter within the configured staleness window.\n  LABELS: {{ $labels }}"

- alert: SourceExporterDown
  expr: host_source_exporter_up == 0
  for: 5m
  labels:
    severity: high
  annotations:
    summary: "Source exporter down (instance {{ $labels.instance }}, exporter {{ $labels.exporter }})"
    description: "host-metrics-normalizer cannot reach the underlying {{ $labels.exporter }} on this host.\n  LABELS: {{ $labels }}"
```
