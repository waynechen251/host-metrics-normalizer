# host-metrics-normalizer 規格書 — 00. 專案總覽

## 1. 專案定位

`host-metrics-normalizer` 是一套部署在每台主機上的跨平台 Prometheus metrics 標準化代理。

它不取代 `windows_exporter` 或 `node_exporter` 的底層採集能力，而是綁定本機既有 exporter，負責抓取原始 metrics、解析、標準化、補上資產資訊，最後對 Prometheus 提供一組統一的 `/metrics`。

目標是讓 Grafana 只需要查詢 `host_*` 指標，就能同時呈現 Windows 與 Linux 主機資訊，不再需要為 `windows_*` 與 `node_*` 各自維護兩套 dashboard 或複雜 PromQL。

## 2. 核心目標

1. 每台主機只對 Prometheus 暴露一組標準化 metrics。
2. Windows 與 Linux 主機輸出同一套 `host_*` metric schema。
3. 保留 Prometheus 原生 `up` 偵測能力。
4. 保留底層 `windows_exporter` / `node_exporter` 狀態偵測能力。
5. 補上資產資訊，例如用途、位置、負責人、環境、主機類型。
6. 將 OS 差異、exporter 差異、版本差異封裝在 normalizer 內部。
7. 降低 Grafana dashboard 與 PromQL 維護成本。
8. 可逐步上線，不影響既有 exporter 部署與服務。

## 3. 非目標

1. 不取代 `windows_exporter`。
2. 不取代 `node_exporter`。
3. 不做完整 ITSM / CMDB 系統。
4. 不做 GLPI / OCS Inventory 等資產管理平台。
5. 不直接負責告警通知。
6. 不直接儲存長期歷史資料。
7. 不在 MVP 階段實作遠端集中式管理。

## 20. 後續可擴充方向

1. 支援中央管理主機清單。
2. 支援 asset metadata 從 Git repo / YAML inventory 載入。
3. 支援自動偵測 OS 與 source exporter type。
4. 支援 Windows Event Log 基礎健康摘要。
5. 支援 Linux systemd service 狀態摘要。
6. 支援 Docker service inventory。
7. 支援 VMware Workstation VM inventory。
8. 支援 ESXi API inventory。
9. 支援輸出 JSON API 給內部資產頁。
10. 支援產生 Grafana dashboard JSON。

## 22. 命名總結

專案名稱：

```text
host-metrics-normalizer
```

主要輸出 prefix：

```text
host_
```

核心概念：

```text
source exporter -> normalize -> enrich -> expose unified metrics
```

一句話描述：

```text
Cross-platform host metrics normalization layer for Prometheus and Grafana.
```
