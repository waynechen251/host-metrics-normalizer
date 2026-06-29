# host-metrics-normalizer 規格書 — 07. 可觀測性：Prometheus、Grafana、告警

## 12. Prometheus 設定範例

```yaml
scrape_configs:
  - job_name: "host-metrics-normalizer"
    scrape_interval: 30s
    scrape_timeout: 10s
    static_configs:
      - targets:
          - "10.40.1.11:9527"
          - "10.40.1.12:9527"
          - "10.40.1.13:9527"
```

## 13. Grafana Dashboard 設計

### 13.1 Dashboard 目標

一頁通吃 Windows 與 Linux。

主要區塊：

1. Host Overview
2. Asset / Inventory
3. CPU
4. Memory
5. Filesystem
6. Disk I/O
7. Network
8. Exporter Health
9. Normalizer Health

### 13.2 建議 Variables

```text
$environment
$role
$location
$host
```

### 13.3 查詢範例

主機是否在線：

```promql
up{job="host-metrics-normalizer"}
```

底層 exporter 是否正常：

```promql
host_source_exporter_up
```

CPU：

```promql
host_cpu_usage_percent{host="$host"}
```

Memory：

```promql
host_memory_usage_percent{host="$host"}
```

Filesystem：

```promql
host_filesystem_usage_percent{host="$host"}
```

Network：

```promql
rate(host_network_receive_bytes_total{host="$host"}[5m])
rate(host_network_transmit_bytes_total{host="$host"}[5m])
```

## 14. 告警建議

### 14.1 Normalizer down

```promql
up{job="host-metrics-normalizer"} == 0
```

意義：

1. 主機斷線。
2. normalizer 服務掛掉。
3. 防火牆或網路問題。

### 14.2 Source exporter down

```promql
host_source_exporter_up == 0
```

意義：

1. windows_exporter / node_exporter 掛掉。
2. localhost port 錯誤。
3. exporter 版本或 config 異常。

### 14.3 Data stale

```promql
host_metrics_stale == 1
```

意義：

1. normalizer 仍在線，但資料過舊。
2. source exporter 可能不穩。

### 14.4 Host resource alerts

CPU：

```promql
host_cpu_usage_percent > 90
```

Memory：

```promql
host_memory_usage_percent > 90
```

Filesystem：

```promql
host_filesystem_usage_percent > 90
```
