# host-metrics-normalizer 規格書 — 03. API Endpoint

## 7. API Endpoint

### 7.1 /metrics

給 Prometheus scrape 使用。

必須輸出：

1. normalizer 自身狀態。
2. source exporter 狀態。
3. asset info。
4. 標準化後的 host metrics。

每次被存取都會即時同步抓取一次 source exporter，詳見 [06-operations.md](06-operations.md) §11.1。

### 7.2 /healthz

給人工或監控檢查 normalizer 本體狀態。

回應範例：

```json
{
  "status": "ok",
  "version": "0.1.0",
  "source_exporter_up": true,
  "last_scrape_success": true,
  "last_scrape_timestamp": 1782739527,
  "exporter": "windows_exporter",
  "exporter_version": "0.31.6",
  "os_family": "windows"
}
```

`exporter` / `exporter_version` / `os_family` 為自動偵測結果（見 [02-tech-and-config.md](02-tech-and-config.md) §6.2），尚未偵測成功前固定為 `"unknown"` / `""` / `"unknown"`。

`/healthz` 本身不會主動觸發抓取，只反映最近一次由 `/metrics` 請求觸發的抓取結果；服務啟動後若尚未有任何 `/metrics` 請求進來，會維持在上述預設值。

### 7.3 /debug/raw

人工排查用。

回傳最近一次抓到的原始 exporter metrics（`Content-Type: text/plain`）。

回應狀態：

| 情境 | 狀態碼 |
|---|---|
| `debug_enabled: false` | 404（不揭露端點存在） |
| 尚未有任何成功 scrape | 503（cache 尚無資料） |
| 已有快取資料 | 200 + 原始 exposition 文字 |

安全要求：

1. 預設可透過設定關閉。
2. 不建議暴露到非內網。
3. 不應包含敏感資訊。

### 7.4 /debug/normalized

人工排查用。

回傳 normalizer 解析後的中間資料模型。

回應狀態：

| 情境 | 狀態碼 |
|---|---|
| `debug_enabled: false` | 404（不揭露端點存在） |
| 尚未有任何成功 normalization | 503（cache 尚無資料） |
| 已有快取資料 | 200 + JSON 格式的 normalized snapshot |

normalized snapshot 至少應包含 exporter type / version / os_family、support status、host label、已產生的 normalized series 與 missing metrics 資訊。
