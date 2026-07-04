# host-metrics-normalizer

![Version](https://img.shields.io/badge/version-0.1.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-lightgrey)

跨平台的 Prometheus 指標正規化匯出器（exporter），搭配 [`windows_exporter`](https://github.com/prometheus-community/windows_exporter) 或 [`node_exporter`](https://github.com/prometheus/node_exporter) 部署在每台主機上，將不同作業系統的指標統一轉換為一致的 `host_*` schema，讓 Prometheus 與 Grafana 只需面對一套查詢邏輯。

## 為什麼需要它

[`windows_exporter`](https://github.com/prometheus-community/windows_exporter) 與 [`node_exporter`](https://github.com/prometheus/node_exporter) 的指標名稱與 label 各自不同，導致 Grafana dashboard 與 PromQL 必須為 Windows 和 Linux 各維護一套。`host-metrics-normalizer` 並不取代這兩個 exporter，而是在本機額外抓取它們的資料、解析、正規化、補上資產（asset）中介資料後，對外只暴露一組統一的 `/metrics`：

```text
Windows Host
  ├─ windows_exporter         →  http://127.0.0.1:9182/metrics
  └─ host-metrics-normalizer  →  http://0.0.0.0:9527/metrics

Linux Host
  ├─ node_exporter            →  http://127.0.0.1:9100/metrics
  └─ host-metrics-normalizer  →  http://0.0.0.0:9527/metrics

Prometheus  → 只 scrape host-metrics-normalizer
Grafana     → 只查詢 host_* 指標
```

## 特色

- 統一 `host_*` metric schema，同一套 Grafana dashboard 可同時呈現 Windows 與 Linux 主機。
- 保留 Prometheus 原生 `up`，並額外暴露 `host_source_exporter_up` 偵測底層 exporter 是否健康。
- 補上資產資訊（owner、environment、location、role 等），輸出 `host_asset_info` / `host_os_info` / `host_hardware_info`。
- `/metrics` 被存取時即時同步抓取本機來源 exporter，語意與 `windows_exporter`/`node_exporter` 本身「被 scrape 才收集」的模型一致；來源 exporter 故障時仍可服務上一次成功資料並標示 `host_metrics_stale`。
- 單一 Python 服務，無需資料庫、Web UI 或 Docker，可自行包裝為系統服務（Windows 用 NSSM、Linux 用 systemd）常駐執行。

## 安裝

目前僅提供原始碼安裝，尚未發佈 PyPI 套件。需要 Python 3.9 以上版本。

```bash
git clone https://github.com/waynechen251/host-metrics-normalizer.git
cd host-metrics-normalizer
pip install .
```

安裝完成後即可使用 `host-metrics-normalizer` 指令。

### Windows 獨立執行檔（選用）

若不想在目標主機安裝 Python，可在建置環境本機透過 [`packaging/windows/build.ps1`](packaging/windows/build.ps1) 用 PyInstaller 打包出單一執行檔：

```powershell
./packaging/windows/build.ps1
```

會產出 `dist/host-metrics-normalizer.exe` 與 `dist/config.example.yml`。目前沒有預先建置好的 Release 可下載，需要自行建置。

## 快速開始

```bash
# 1. 複製設定檔範例並依環境調整
cp configs/config.example.yml config.yml

# 2. 至少確認/修改 source_exporter.endpoint 與 asset.* 欄位

# 3. 啟動服務
host-metrics-normalizer --config ./config.yml

# 從原始碼檢出、尚未安裝時，也可以改用：
python -m host_metrics_normalizer --config ./config.yml
```

查看版本：`host-metrics-normalizer --version`

## 設定

設定檔為單一 YAML 檔案，完整可用欄位請參考 [`configs/config.example.yml`](configs/config.example.yml)。主要區塊：

| 區塊 | 用途 |
|---|---|
| `server` | 監聽位址/連接埠、`/metrics` 與 `/healthz` 路徑、是否開放 debug 端點 |
| `source_exporter` | 來源 `windows_exporter` / `node_exporter` 的 endpoint 與逾時秒數 |
| `cache` | 即時抓取失敗時的降級快取行為（多久沒有成功抓取視為 stale） |
| `asset` | 補充到 `host_asset_info` 的資產中介資料（owner、environment、location 等） |
| `labels` | 額外附加到輸出指標上的自訂 label |
| `normalization` | 正規化時要忽略的檔案系統/網卡名稱規則 |

## 端點

啟動後可用的端點（路徑可透過 `server.metrics_path` / `server.health_path` 調整）：

| 端點 | 用途 |
|---|---|
| `/metrics` | 提供 Prometheus scrape |
| `/healthz` | 服務健康檢查（JSON） |
| `/debug/raw` | 手動排查：最近一次原始 exporter 資料 |
| `/debug/normalized` | 手動排查：正規化後的中間資料 |

`/debug/*` 兩個端點受 `server.debug_enabled` 控制，關閉時回傳 404；根路徑 `/` 會 302 導向 `/metrics`。

## 指標

完整的 `host_*` 指標清單（名稱、型別、Label、來源對照、PromQL 查詢與告警範例）請參考 [`docs/`](docs/README.md)。

## 部署為系統服務

本專案不隨附安裝腳本，以下是常見的自行包裝方式：

**Linux (systemd)**

```ini
# /etc/systemd/system/host-metrics-normalizer.service
[Unit]
Description=host-metrics-normalizer
After=network.target

[Service]
ExecStart=/usr/local/bin/host-metrics-normalizer --config /etc/host-metrics-normalizer/config.yml
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

**Windows (NSSM)**

```powershell
nssm install host-metrics-normalizer "C:\Path\To\host-metrics-normalizer.exe" "--config C:\Path\To\config.yml"
```

## 專案狀態

目前為早期開發階段（pre-1.0），介面與 metric 命名仍可能調整。詳細開發階段規劃可參考 [`08-roadmap.md`](.agents/spec/host-metrics-normalizer/08-roadmap.md)。

## 開發與貢獻

歡迎透過 Issue / Pull Request 參與。

```bash
pip install -e .[dev]
python -m pytest
```

送出 PR 前請確保測試通過。若你是使用 AI coding agent 協助開發，可參考 [AGENTS.md](AGENTS.md) 的 agent 專用規則；本專案的完整設計規格則位於 [`.agents/spec/`](.agents/spec/index.md)。

## 授權

本專案採用 [MIT License](LICENSE)。
