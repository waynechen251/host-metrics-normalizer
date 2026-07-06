# Documentation

本目錄說明 `host-metrics-normalizer` 對外暴露於 `/metrics` 的指標:每個指標群組的名稱、型別、Label、來源 exporter 對照,以及常用的 PromQL 查詢與告警範例。

指標一律以 `host_` 為前綴,由 `windows_exporter` 或 `node_exporter` 的原生指標正規化而來,兩個例外是:`host_normalizer_*` / `host_source_exporter_*` 是本服務自身的健康狀態指標,不經由來源 exporter 轉換;`host_gpu_*` 則是 normalizer 自行呼叫本機 OS API 採集(見 [`gpu`](metrics.gpu.md)),與 source_exporter 的抓取結果完全無關。

# Metrics

- [`normalizer`](metrics.normalizer.md) — host-metrics-normalizer 自身與來源 exporter 的健康狀態
- [`asset`](metrics.asset.md) — 由設定檔補上的資產中介資料
- [`os`](metrics.os.md) — 作業系統資訊與開機時間
- [`cpu`](metrics.cpu.md) — CPU 使用率、核心/執行緒/插槽數量、型號
- [`memory`](metrics.memory.md) — 實體記憶體與 swap/分頁檔使用量
- [`filesystem`](metrics.filesystem.md) — 檔案系統容量與使用率
- [`disk`](metrics.disk.md) — 實體磁碟 I/O 與佇列長度
- [`network`](metrics.network.md) — 網路介面流量、錯誤、連線狀態與速度
- [`gpu`](metrics.gpu.md) — GPU 裝置資訊、記憶體用量與即時使用率,由 normalizer 自行採集(Windows + Linux,溫度僅 Linux)
