# host-metrics-normalizer 規格書 — 08. 開發階段與 MVP 驗收

## 17. 開發階段規劃

### Phase 0: 專案骨架

1. 建立 repo。
2. 建立 Python package。
3. 建立 config loader。
4. 建立 HTTP server。
5. 建立 `/healthz`。
6. 建立 `/metrics` 空骨架。

### Phase 1: Source exporter scrape

1. 支援抓 `source_exporter.endpoint`。
2. 支援 timeout。
3. 支援 source exporter up/down。
4. 支援 raw metrics cache。
5. 支援 `/debug/raw`。

### Phase 2: Node exporter parser

1. 解析 Linux CPU。
2. 解析 Linux memory。
3. 解析 Linux filesystem。
4. 解析 Linux network。
5. 解析 Linux uptime。

### Phase 3: Windows exporter parser

1. 建立 Windows exact-version mapping registry。
2. 解析 Windows CPU。
3. 解析 Windows memory。
4. 解析 Windows logical disk。
5. 解析 Windows network。
6. 解析 Windows uptime。

### Phase 4: Normalized metrics output

1. 輸出 `host_*` metrics。
2. 補 asset labels。
3. 支援 stale 狀態。
4. 支援 debug normalized endpoint。

### Phase 5: 打包與部署

1. ~~Windows zip package。~~ 已提前實作：PyInstaller onefile 打包（`packaging/windows/`），產出單一 `host-metrics-normalizer.exe`，未指定 `--config` 時預設讀取 exe 同目錄的 `config.yml`（見 [02-tech-and-config.md](02-tech-and-config.md) §6）。
2. NSSM install script。
3. Linux tarball。
4. systemd unit file。
5. 範例 config。
6. Prometheus scrape 範例。

### Phase 6: Grafana dashboard

1. 建立 host overview dashboard。
2. 建立 resource dashboard。
3. 建立 source exporter health panel。
4. 建立 normalizer health panel。

### Phase 7: 硬體與資產強化

1. Windows WMI / CIM inventory。
2. Linux dmidecode inventory。
3. smartctl disk health。
4. NIC speed 與 link status。
5. VM / hypervisor detection。

## 18. MVP 驗收標準

MVP 必須達成：

1. Windows 主機可部署。
2. Linux 主機可部署。
3. 可讀取 YAML 設定檔。
4. 可抓 localhost 的 windows_exporter 或 node_exporter。
5. 可輸出 `host_normalizer_*`。
6. 可輸出 `host_source_exporter_*`。
7. 可輸出 `host_asset_info`。
8. 可輸出 CPU / memory / filesystem / network / uptime 的標準化 metrics。
9. Prometheus 可正常 scrape。
10. Grafana 可用同一套 `host_*` 查詢顯示 Windows 與 Linux。

## 21. AgentCLI 初始任務建議

給 AgentCLI 的第一批任務可以拆成：

1. 根據本規格建立 Python 專案骨架。
2. 實作 config loader。
3. 實作 source exporter scraper。
4. 實作 `/healthz` 與 `/metrics`。
5. 建立 parser fixture 測試資料。
6. 先支援 node_exporter 最小解析。
7. 再支援 windows_exporter 最小解析。
8. 建立 Prometheus scrape 範例。
9. 建立 Grafana MVP dashboard JSON。
