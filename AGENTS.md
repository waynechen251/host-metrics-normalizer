# AGENTS.md

## 專案背景

本專案為 `host-metrics-normalizer`，一個以 Python 撰寫、跨平台的 Prometheus 指標正規化匯出器（exporter），與 `windows_exporter` 或 `node_exporter` 並行部署在每台主機上。

完整專案規格請見：

```text
.agent/spec/index.md
```

所有專案設計細節（部署架構、端點、設定檔格式、metric 命名與清單、開發階段、目錄結構、MVP 驗收標準等）一律以該索引下連結的規格文件為唯一權威來源，本檔案不重複描述。

## 規格文件管理規則

所有專案規格文件（spec）統一由 `.agent/` 目錄管理，禁止散落於其他位置。

```text
.agent/
  spec/
    index.md                          <- 規格文件總索引
    host-metrics-normalizer/          <- 本專案規格，依主題拆分為多個檔案
      00-overview.md
      01-architecture.md
      02-tech-and-config.md
      03-api-endpoints.md
      04-metrics-schema.md
      05-mapping-rules.md
      06-operations.md
      07-observability.md
      08-roadmap.md
```

規則如下：

- 新增或修改規格文件時，一律放在 `.agent/spec/` 之下，不要另開新的規格目錄。
- 新增其他專案或功能的規格時，於 `.agent/spec/` 下新增對應子目錄，並在 `index.md` 補上連結，不要把新規格塞進既有子目錄。
- 規格文件以外的一般文件（如部署說明、Grafana 使用說明）仍放在 `docs/`，不算規格文件。
- 若實作與規格文件不一致，應先更新 `.agent/spec/` 中對應的規格文件並與使用者確認，再進行程式碼變更，而不是讓程式碼與規格各自為政。
- 進行任何架構或行為變更前，必須先讀取 `.agent/spec/index.md` 並查閱對應的規格文件。

## 行為總則

- 動工前先讀規格文件，確保理解現有設計再開始實作或修改。
- 不要設計超出規格需求的抽象、功能或設定選項；規格沒提到的需求先回去確認規格，而不是自行擴充。
- 解析（parsing）邏輯應優先採用結構化方式，避免使用脆弱的全文字 regex 抓取數值，細節以規格文件中的技術選型為準。

## 實作語言限制

只能使用 Python。

除非使用者明確要求，不要引入 Go、.NET、Java、Node.js 或其他執行環境相依套件。

## 測試要求

需為解析與正規化邏輯加上測試。

若專案已有對應的測試工具，請使用該工具；若尚無工具，優先使用：

```bash
python -m pytest
```

不要悄悄略過測試。若測試無法執行，必須說明原因。

## 相容性規則

本專案用於 SRE/DevOps 在混合 Windows/Linux 環境中的實際營運，優先重視可靠性與可維護性，而非炫技式的抽象設計。

避免隨意變更 metric 名稱。指標 schema 的穩定性很重要，因為 Grafana 儀表板與告警規則都會依賴它。

若必須進行破壞性的指標變更，請務必記錄在 `docs/metrics-schema.md` 中。

## 安全規則

不要在 labels、日誌、debug 端點或指標中暴露機密資訊。

不要將原始的例外（exception）追蹤資訊放入指標的 label 中。

除非有明確要求，不需加入身分驗證，但 debug 端點仍須可設定（可關閉）。

預設假設此服務僅在受信任的內部網路中使用。

## Non-Goals

不應建構：

- CMDB
- ITSM 系統
- 完整的盤點 Web Portal
- 告警通知系統
- Prometheus 的替代品
- windows_exporter 的替代品
- node_exporter 的替代品
- 中央管理伺服器

本正規化器是一個輕量級的單機指標轉譯層。
