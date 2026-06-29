# host-metrics-normalizer

跨平台的 Prometheus 指標正規化匯出器（exporter），搭配 `windows_exporter` 或 `node_exporter` 部署在每台主機上，將不同作業系統的指標統一轉換為一致的 `host_*` schema，讓 Prometheus 與 Grafana 只需面對一套查詢邏輯。

> 本專案目前處於規格設計階段，原始碼尚未實作。完整規格請見 [.agent/spec/index.md](.agent/spec/index.md)。

## 為什麼需要它

`windows_exporter` 與 `node_exporter` 的指標名稱與 label 各自不同，導致 Grafana dashboard 與 PromQL 必須為 Windows 和 Linux 各維護一套。`host-metrics-normalizer` 並不取代這兩個 exporter，而是在本機額外抓取它們的資料、解析、正規化、補上資產（asset）中介資料後，對外只暴露一組統一的 `/metrics`：

```text
Windows Host
  ├─ windows_exporter
  └─ host-metrics-normalizer  →  http://0.0.0.0:9527/metrics

Linux Host
  ├─ node_exporter
  └─ host-metrics-normalizer  →  http://0.0.0.0:9527/metrics

Prometheus  → 只 scrape host-metrics-normalizer
Grafana     → 只查詢 host_* 指標
```

## 特色

- 統一 `host_*` metric schema，同一套 Grafana dashboard 可同時呈現 Windows 與 Linux 主機。
- 保留 Prometheus 原生 `up`，並額外暴露 `host_source_exporter_up` 偵測底層 exporter 是否健康。
- 補上資產資訊（owner、environment、location、role 等），輸出 `host_asset_info` / `host_os_info` / `host_hardware_info`。
- 背景定期 scrape 並快取，`/metrics` 不會同步阻塞；來源 exporter 故障時仍可服務並標示 `host_metrics_stale`。
- 單一 Python 服務，無需資料庫、Web UI 或 Docker，可用 NSSM（Windows）或 systemd（Linux）部署。

## 快速開始

```bash
# 從原始碼執行
python -m host_metrics_normalizer --config /path/to/config.yml
```

設定檔範例（完整版見 [02-tech-and-config.md](.agent/spec/host-metrics-normalizer/02-tech-and-config.md)）：

```yaml
server:
  listen_address: "0.0.0.0"
  listen_port: 9527

source_exporter:
  type: "windows_exporter"
  endpoint: "http://127.0.0.1:9182/metrics"

asset:
  asset_id: "ASSET-001"
  hostname: "srv-app-01"
  environment: "prod"
```

啟動後可用的端點：

| 端點 | 用途 |
|---|---|
| `/metrics` | 提供 Prometheus scrape |
| `/healthz` | 服務健康檢查 |
| `/debug/raw` | 手動排查：最近一次原始 exporter 資料（可關閉） |
| `/debug/normalized` | 手動排查：正規化後的中間資料（可關閉） |

## 文件

所有設計細節以 [.agent/spec/index.md](.agent/spec/index.md) 為唯一權威來源，包含部署架構、技術選型、metric 命名規範、mapping 規則、維運與安全考量、Grafana/告警建議、開發階段規劃等。

## 專案狀態

MVP 開發中，驗收標準與開發階段請見 [08-roadmap.md](.agent/spec/host-metrics-normalizer/08-roadmap.md)。

## 貢獻

歡迎透過 Issue / Pull Request 參與。提交變更前請先閱讀 [AGENTS.md](AGENTS.md) 與對應的規格文件，確保實作與規格一致。

## 授權

本專案採用 [MIT License](LICENSE)。
