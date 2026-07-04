# host-metrics-normalizer 規格書 — 06. 維運：快取、失敗處理、安全、Logging

## 11. Cache 與失敗處理

### 11.1 Scrape 行為

`/metrics` 被存取時，normalizer 即時同步抓一次 source exporter，並在同一個請求內完成「抓取 → 偵測 exporter 類型/版本 → 正規化 → 寫回 cache → 更新 metrics/health」整個流程，才產生回應。

沒有背景輪詢執行緒，也沒有固定抓取間隔；`/metrics` 的請求時機本身就是抓取時機，語意與 windows_exporter/node_exporter 本身「被 scrape 才收集」的模型一致，這樣才不會讓 normalizer 這層失去「中間層」應有的即時性。

建議：

1. 多個併發的 `/metrics` 請求須序列化執行「抓取 → 正規化 → 寫回 cache → render」整段（例如用單一 lock），避免同時對 source exporter 發出多個抓取，也避免 metrics registry 在多執行緒寫入時出現不一致的中間狀態。不需要讓多個併發請求共享同一次抓取結果——各自完整跑一次即可，實作複雜度不必超過這個需求。
2. `/metrics` 回傳「這次請求觸發的抓取」的標準化結果；若這次抓取失敗，回退到上一次成功的標準化結果（見 §11.3）。
3. 若上一次成功結果距今超過 `stale_after_seconds`，輸出 `host_metrics_stale 1`。
4. `/debug/raw`、`/debug/normalized` 維持只讀 cache（見 [03-api-endpoints.md](03-api-endpoints.md) §7.3、§7.4），不會因為被存取而觸發新的抓取。

### 11.2 Timeout

每次抓 source exporter 必須有 timeout。

預設：

```text
3 seconds
```

### 11.3 Partial failure

若 source exporter 失敗：

1. `host_source_exporter_up = 0`
2. `host_source_exporter_last_scrape_success = 0`
3. `host_source_exporter_errors_total += 1`
4. 若 cache 未過期，仍輸出上次成功資料並標示 `host_metrics_stale`（cache 指的是上一次即時抓取成功時寫入的標準化結果）
5. 若無 cache，至少輸出 normalizer 與 source exporter 狀態 metrics

## 15. 安全考量

1. 預設只允許內網 scrape。
2. `/debug/raw` 與 `/debug/normalized` 預設可關閉。
3. 不在 metrics label 中輸出密碼、token、完整錯誤堆疊。
4. 不暴露 source exporter 原始 endpoint 到非必要網段。
5. normalizer 不應需要系統管理員權限才能運作，除非後續加入本機硬體深度盤點。
6. 若未來加入 WMI / dmidecode / smartctl，權限需求需獨立文件化。

## 16. Logging

預設輸出 stdout/stderr（行為風格類似 Go exporter），方便 systemd 與服務包裝器（service wrapper）擷取；檔案 log 為可選功能。

建議輸出一般文字 log 或 JSON log。

Windows：

```text
C:\ProgramData\host-metrics-normalizer\logs\normalizer.log
```

Linux：

```text
/var/log/host-metrics-normalizer/normalizer.log
```

必要 log：

1. service start / stop
2. config loaded
3. source exporter scrape success / fail
4. parse error
5. normalization error
6. metrics stale
7. unexpected exception
