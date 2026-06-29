# host-metrics-normalizer 規格書 — 03. API Endpoint

## 7. API Endpoint

### 7.1 /metrics

給 Prometheus scrape 使用。

必須輸出：

1. normalizer 自身狀態。
2. source exporter 狀態。
3. asset info。
4. 標準化後的 host metrics。

### 7.2 /healthz

給人工或監控檢查 normalizer 本體狀態。

回應範例：

```json
{
  "status": "ok",
  "version": "0.1.0",
  "source_exporter_up": true,
  "last_scrape_success": true,
  "last_scrape_timestamp": 1782739527
}
```

### 7.3 /debug/raw

人工排查用。

回傳最近一次抓到的原始 exporter metrics。

安全要求：

1. 預設可透過設定關閉。
2. 不建議暴露到非內網。
3. 不應包含敏感資訊。

### 7.4 /debug/normalized

人工排查用。

回傳 normalizer 解析後的中間資料模型。
