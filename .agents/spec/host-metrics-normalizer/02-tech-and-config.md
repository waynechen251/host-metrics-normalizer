# host-metrics-normalizer 規格書 — 02. 技術選型與設定檔

## 5. 技術選型建議

### 5.1 MVP 建議語言

建議使用 Python。

原因：

1. Windows / Linux 都可部署。
2. 公司環境較可能有人能維護。
3. `prometheus_client` 可快速建立 `/metrics`。
4. 可用現成 parser 處理 Prometheus exposition format。
5. 方便後續整合 WMI、CIM、PowerShell、Linux shell command。

建議套件：

```text
prometheus_client
requests
PyYAML
prometheus_client.parser
psutil
```

Metrics 解析應優先使用結構化解析（例如 `prometheus_client.parser`），避免使用脆弱的全文字 regex 抓取數值。

Windows 已提供 PyInstaller onefile 打包（見 `packaging/windows/`），可產出單一 `host-metrics-normalizer.exe`，不需另外安裝 Python 環境。後續若需要其他打包方式，可評估：

```text
Nuitka
.NET
Go
```

### 5.2 服務型態

Windows：

1. 優先使用 NSSM 註冊成 Windows Service。
2. 後續可改寫為原生 Windows Service。

Linux：

1. 使用 systemd service。
2. 設定 `Restart=always`。

## 6. 設定檔規格

設定檔建議使用 YAML。

預設路徑：

以原始碼或 pip 套件執行（`python -m host_metrics_normalizer`）：

Windows：

```text
C:\Program Files\host-metrics-normalizer\config.yml
```

Linux：

```text
/etc/host-metrics-normalizer/config.yml
```

以打包後的 Windows exe 執行（`host-metrics-normalizer.exe`，未指定 `--config` 時）：

```text
<exe 所在目錄>\config.yml
```

即執行檔與設定檔放同一目錄即可，不需安裝到 `C:\Program Files`。`--config` 明確指定時優先於以上所有預設值。

### 6.1 config.yml 範例

```yaml
server:
  listen_address: "0.0.0.0"
  listen_port: 9527
  metrics_path: "/metrics"
  health_path: "/healthz"
  debug_enabled: true

source_exporter:
  endpoint: "http://127.0.0.1:9182/metrics"
  timeout_seconds: 3

cache:
  enabled: true
  stale_after_seconds: 180

asset:
  asset_id: "ASSET-001"
  hostname: "srv-app-01"
  display_name: "App Server 01"
  owner: "infra"
  environment: "prod"
  location: "office-3f"
  role: "app-server"
  criticality: "medium"
  managed_by: "wayne"
  note: "VMware Workstation host"

labels:
  site: "hq"
  team: "infra"
  platform_group: "legacy-pc"

normalization:
  filesystem_ignore_regex:
    - "^/run"
    - "^/sys"
    - "^/proc"
    - "^tmpfs"
  network_ignore_regex:
    - "^Loopback"
    - "^lo$"
    - "^vEthernet"
    - "^docker"
    - "^br-"
```

### 6.2 source_exporter 類型自動偵測

`source_exporter` 不需配置 `type`。normalizer 抓到 raw metrics 後，從中尋找 exporter 自帶的 `*_build_info` 來判定來源類型、版本與作業系統：

```text
windows_exporter_build_info{...,goos="windows",version="0.31.6"} 1  -> type=windows_exporter, os_family=windows
node_exporter_build_info{...,goos="linux",version="1.8.2"} 1        -> type=node_exporter,    os_family=linux
```

MVP 支援自動辨識：

```text
windows_exporter
node_exporter
```

兩者皆未偵測到時，type 標示為 `unknown`，normalizer 仍記錄 `host_source_exporter_up`，但無法套用 mapping 規則進行正規化（待後續 Phase）。

後續可擴充偵測的類型：

```text
custom
telegraf
nsclient
```
