# gpu metrics

這組指標涵蓋 GPU 裝置資訊、記憶體用量、即時使用率,以及(僅 Linux)溫度。**與 windows_exporter/node_exporter 完全無關**:normalizer 自行呼叫本機作業系統原生 API 採集(Windows:WMI + Performance Counters;Linux:sysfs),不依賴任何來源 exporter 的 collector 是否啟用、是否支援,即使 source_exporter 抓取失敗,`host_gpu_*` 仍會照常輸出。

|||
-|-
Metric name prefix  | `host_gpu`
Source (Windows)     | WMI `Win32_VideoController`(裝置名稱/ID)、registry `HardwareInformation.qwMemorySize`(顯存總量)、Performance Counters `GPU Adapter Memory`/`GPU Engine`(即時用量/使用率)——皆為 OS 標準介面,任何廠商的驅動都適用,不呼叫任何廠商 SDK
Source (Linux)        | sysfs `/sys/class/drm/card*/device/`(裝置 ID、記憶體、使用率)、`/sys/class/hwmon/`(溫度)、本機 `pci.ids` 資料庫(裝置名稱,找不到則退回 hex ID)
Always emitted?      | `host_gpu_info` 只要偵測到至少一顆 GPU 就會輸出;其餘指標視該平台/驅動是否提供對應資料而定,見下方〈已知限制〉
Configuration         | `gpu.enabled`(預設 `true`),設為 `false` 完全停用本機 GPU 採集

## Configuration
```yaml
gpu:
  enabled: true
```

## Metrics

| Name | Description | Type | Labels |
|---|---|---|---|
| `host_gpu_info` | Normalized GPU device information | gauge | `host`, `gpu`, `name`, `device_id` |
| `host_gpu_memory_total_bytes` | Normalized host GPU dedicated video memory total in bytes | gauge | `host`, `gpu` |
| `host_gpu_memory_used_bytes` | Normalized host GPU dedicated memory usage in bytes | gauge | `host`, `gpu` |
| `host_gpu_memory_usage_percent` | Normalized host GPU memory usage percentage | gauge | `host`, `gpu` |
| `host_gpu_utilization_percent` | Normalized host GPU utilization percentage | gauge | `host`, `gpu` |
| `host_gpu_temperature_celsius` | Normalized host GPU temperature in degrees Celsius | gauge | `host`, `gpu`(**僅 Linux**) |

`gpu` label 是主機上第幾顆 GPU 的穩定索引(例如 `"0"`、`"1"`),不是廠商編號。

### 已知限制

- **`host_gpu_temperature_celsius` 僅 Linux**:Windows 沒有任何廠商中立的標準 API 可取得 GPU 溫度(需要 NVAPI/ADLX 這類廠商 SDK),Phase 1 刻意不整合廠商 SDK,因此 Windows 主機完全不會輸出這個指標。
- **不含功耗**:兩個平台的標準介面都不可靠或不存在,目前未實作。
- **Windows 使用率首次請求會缺席**:`host_gpu_utilization_percent` 由 Performance Counters 的兩次取樣差值計算而來(與 windows_exporter 自身讀取這組計數器的方式相同),程序啟動後第一次 `/metrics` 或 `/debug/gpu` 請求還沒有前一筆樣本可比較,該次會缺少這個指標,從第二次請求起才會出現。
- **Linux 使用率/顯存目前實質只有 AMD 有**:`/sys/class/drm/card*/device/gpu_busy_percent`、`mem_info_vram_total`、`mem_info_vram_used` 這幾個 sysfs 檔案只有 `amdgpu`(AMD)驅動有實作;NVIDIA 專有驅動完全不會填這些檔案,因此 NVIDIA 顯卡在 Linux 上目前只有 `host_gpu_info` 與(若驅動有註冊 hwmon)`host_gpu_temperature_celsius`,沒有使用率/顯存資料——這是驅動生態的限制,不是 normalizer 的 bug。未來若要補齊,需要在 Phase 2 整合廠商 SDK(NVML)。
- **多 GPU 主機的裝置對應是盡力而為**:Windows 上 `host_gpu_info` 的名稱/裝置 ID 來自 WMI `Win32_VideoController`,而使用率/顯存來自 Performance Counters 的原生 `phys` 索引,兩者只以「列舉順序」對應,沒有精確的介面卡層級關聯(WMI 不提供 LUID)。單一 GPU 主機不受影響;多 GPU(尤其筆電內顯/獨顯混合)主機的 `gpu` 標籤與名稱對應可能不精確,建議在正式導入前於實機用 `/debug/gpu` 核對。

### Example metric
```
host_gpu_info{host="gpu-01",gpu="0",name="NVIDIA GeForce RTX 3080",device_id="10de:1b81"} 1
host_gpu_memory_usage_percent{host="gpu-01",gpu="0"} 20.0
host_gpu_utilization_percent{host="gpu-01",gpu="0"} 42.5
```

## Useful queries
GPU 使用率超過 90% 的裝置
```
host_gpu_utilization_percent > 90
```

GPU 記憶體使用率超過 90% 的裝置
```
host_gpu_memory_usage_percent > 90
```

## Alerting examples
**prometheus.rules**
```yaml
- alert: HighGpuUtilization
  expr: host_gpu_utilization_percent > 90
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "High GPU utilization ({{ $labels.host }} gpu {{ $labels.gpu }})"
    description: "GPU utilization has been above 90% for 10 minutes.\n  VALUE = {{ $value }}\n  LABELS: {{ $labels }}"

- alert: HighGpuMemoryUsage
  expr: host_gpu_memory_usage_percent > 90
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "High GPU memory usage ({{ $labels.host }} gpu {{ $labels.gpu }})"
    description: "GPU dedicated memory usage has been above 90% for 10 minutes.\n  VALUE = {{ $value }}\n  LABELS: {{ $labels }}"
```
