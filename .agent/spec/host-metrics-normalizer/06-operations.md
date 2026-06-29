# host-metrics-normalizer 規格書 — 06. 維運：快取、失敗處理、安全、Logging

## 11. Cache 與失敗處理

### 11.1 Scrape 行為

Prometheus scrape normalizer 時，normalizer 不應每次都即時同步抓 source exporter。

建議：

1. background worker 定期抓 source exporter。
2. `/metrics` 回傳最近一次成功標準化結果。
3. 若資料超過 `stale_after_seconds`，輸出 `host_metrics_stale 1`。

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
4. 若 cache 未過期，仍輸出上次成功資料並標示 `host_metrics_stale`
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
