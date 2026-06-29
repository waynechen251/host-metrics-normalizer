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

後續若需要更容易打包單一執行檔，可評估：

```text
PyInstaller
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

Windows：

```text
C:\Program Files\host-metrics-normalizer\config.yml
```

Linux：

```text
/etc/host-metrics-normalizer/config.yml
```

### 6.1 config.yml 範例

```yaml
server:
  listen_address: "0.0.0.0"
  listen_port: 9527
  metrics_path: "/metrics"
  health_path: "/healthz"
  debug_enabled: true

source_exporter:
  type: "windows_exporter"
  endpoint: "http://127.0.0.1:9182/metrics"
  timeout_seconds: 3
  expected_version: "0.30.6"

cache:
  enabled: true
  ttl_seconds: 60
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

### 6.2 source_exporter.type 支援值

MVP 支援：

```text
windows_exporter
node_exporter
```

後續可擴充：

```text
custom
telegraf
nsclient
```
