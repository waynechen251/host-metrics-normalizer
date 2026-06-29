# 規格文件索引

本檔案是 `.agent/spec/` 下所有規格文件的總索引與唯一入口。

## host-metrics-normalizer

`host-metrics-normalizer` 專案的規格依主題拆分如下：

| 檔案 | 內容 |
|---|---|
| [00-overview.md](host-metrics-normalizer/00-overview.md) | 專案定位、核心目標、非目標、後續可擴充方向、命名總結 |
| [01-architecture.md](host-metrics-normalizer/01-architecture.md) | 部署架構、up 偵測模型、專案目錄建議 |
| [02-tech-and-config.md](host-metrics-normalizer/02-tech-and-config.md) | 技術選型建議、設定檔規格（config.yml 範例） |
| [03-api-endpoints.md](host-metrics-normalizer/03-api-endpoints.md) | `/metrics`、`/healthz`、`/debug/raw`、`/debug/normalized` |
| [04-metrics-schema.md](host-metrics-normalizer/04-metrics-schema.md) | Metric 命名規範、必要 Metrics 規格 |
| [05-mapping-rules.md](host-metrics-normalizer/05-mapping-rules.md) | windows_exporter / node_exporter mapping 規則 |
| [06-operations.md](host-metrics-normalizer/06-operations.md) | Cache 與失敗處理、安全考量、Logging |
| [07-observability.md](host-metrics-normalizer/07-observability.md) | Prometheus 設定範例、Grafana Dashboard 設計、告警建議 |
| [08-roadmap.md](host-metrics-normalizer/08-roadmap.md) | 開發階段規劃、MVP 驗收標準、AgentCLI 初始任務建議 |

## 新增其他規格文件

未來新增其他專案或功能的規格時，於 `.agent/spec/` 下新增對應子目錄（例如 `other-feature/`），並在本檔案補上對應的章節與連結即可，不需更動既有規格文件。
