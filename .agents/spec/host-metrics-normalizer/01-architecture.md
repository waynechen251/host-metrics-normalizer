# host-metrics-normalizer 規格書 — 01. 部署架構與目錄結構

## 4. 部署架構

### 4.1 每台主機部署一組

```text
Windows Host
  ├─ windows_exporter
  └─ host-metrics-normalizer
        ├─ scrape http://127.0.0.1:9182/metrics
        ├─ normalize windows_* metrics
        ├─ enrich asset metadata
        └─ expose http://0.0.0.0:9527/metrics

Linux Host
  ├─ node_exporter
  └─ host-metrics-normalizer
        ├─ scrape http://127.0.0.1:9100/metrics
        ├─ normalize node_* metrics
        ├─ enrich asset metadata
        └─ expose http://0.0.0.0:9527/metrics
```

### 4.2 Prometheus scrape

Prometheus 不直接 scrape `windows_exporter` / `node_exporter`，改為 scrape 每台主機的 `host-metrics-normalizer`。

```text
Prometheus
  └─ scrape host-metrics-normalizer:9527/metrics

Grafana
  └─ query Prometheus with host_* metrics
```

### 4.3 up 偵測模型

Prometheus 原生：

```promql
up{job="host-metrics-normalizer"}
```

代表該主機的 `host-metrics-normalizer` 是否可連線。

Normalizer 自行輸出：

```text
host_source_exporter_up{exporter="windows_exporter"} 1
host_source_exporter_up{exporter="node_exporter"} 1
```

代表 normalizer 是否成功抓到本機底層 exporter。

判斷方式：

| 狀態 | 意義 |
|---|---|
| `up = 0` | 主機斷線、normalizer 掛掉、防火牆阻擋或 Prometheus 無法連線 |
| `up = 1` 且 `host_source_exporter_up = 0` | normalizer 活著，但本機 windows/node exporter 異常 |
| `up = 1` 且 `host_source_exporter_up = 1` | normalizer 與底層 exporter 都正常 |
| `host_metrics_stale = 1` | normalizer 有 cache，但資料已過期 |

`host_metrics_stale` 是逐請求即時計算的（見 [06-operations.md](06-operations.md) §11.1）：只要有一次 `/metrics` 請求剛好抓取成功，該次回應就會立刻變回 0，不需要等待任何背景排程。

## 19. 專案目錄建議

```text
host-metrics-normalizer/
  README.md
  AGENTS.md
  pyproject.toml
  .agents/
    spec/
      index.md
      host-metrics-normalizer/
        00-overview.md
        01-architecture.md
        02-tech-and-config.md
        03-api-endpoints.md
        04-metrics-schema.md
        05-mapping-rules.md
        06-operations.md
        07-observability.md
        08-roadmap.md
  configs/
    config.example.yml
  scripts/
    install-windows-nssm.ps1
    install-linux-systemd.sh
  systemd/
    host-metrics-normalizer.service
  src/
    host_metrics_normalizer/
      __init__.py
      main.py
      config.py
      server.py
      scraper.py
      parser/
        __init__.py
        prometheus_text.py
        node_exporter.py
        windows_exporter.py
      normalizer/
        __init__.py
        cpu.py
        memory.py
        filesystem.py
        network.py
        os_info.py
      metrics.py
      cache.py
      logging_config.py
  tests/
    fixtures/
      node_exporter.metrics
      windows_exporter.metrics
    test_config.py
    test_node_exporter_parser.py
    test_windows_exporter_parser.py
    test_normalized_metrics.py
  docs/
    metrics-schema.md
    deployment.md
    grafana.md
```
