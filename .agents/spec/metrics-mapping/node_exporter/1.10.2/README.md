# node_exporter 1.10.2 metrics-mapping 參考資料

來源:`https://github.com/prometheus/node_exporter`,tag `v1.10.2`(commit `654f19dee6a0c41de78a8d6d870e8c742cdb43b9`)。

## 跟 windows_exporter 資料夾的差異

node_exporter 官方**沒有**像 `windows_exporter/docs/collector.*.md` 那種逐 collector、含指標名稱/type/labels 的說明文件。node_exporter 的文件慣例不同:

- 根目錄 `README.md` 只有 collector 層級的表格(名稱/描述/支援的 OS),沒有指標層級細節。
- 每個指標真正的名稱、HELP 文字、type、labels 寫死在 Go 原始碼裡(`collector/*.go`,例如 `collector/cpu_linux.go`、`collector/meminfo_linux.go`,用 `prometheus.NewDesc(...)` 定義)。

因此本目錄改放 **`e2e-output-linux.txt`** 作為權威參考——這是 node_exporter 專案自己的 end-to-end 測試 fixture(`collector/fixtures/e2e-output.txt`),用固定的 `/proc`、`/sys` 假資料跑過預設(以及 e2e 測試額外開啟)的 collector 後,產生的完整、真實、帶 `# HELP`/`# TYPE`/labels 的 `/metrics` 輸出。效果類似 windows_exporter 那份逐 collector 文件裡的 "Example metric" 區塊,但涵蓋範圍是全部 collector 一次到位。

若需要確認某個指標更細節的語意(例如某個 label 實際代表什麼、哪些欄位在特定核心版本才有),回頭查本機 clone 的 `D:\repositories\prometheus\node_exporter\collector\*.go` 原始碼(依指標名稱找對應的 `*_linux.go` 檔案)。

本專案的 `detect.py` 把 `node_exporter_build_info` 寫死對應 `os_family="linux"`,所以只取 Linux 版的 e2e 輸出,不需要 `e2e-output-darwin.txt` 等其他平台的版本。

## Collector 預設啟用狀態(節錄自根目錄 README.md「## Collectors」,僅列 Linux 相關)

`missing_metrics` 出現下列「Disabled by default」collector 的指標時屬於正常情況(比照 windows_exporter 的 `cpu_info`/`pagefile` collector)。

### Enabled by default

| Collector | Description |
|---|---|
| arp | Exposes ARP statistics from `/proc/net/arp`. |
| bcache | Exposes bcache statistics from `/sys/fs/bcache/`. |
| bonding | Exposes the number of configured and active slaves of Linux bonding interfaces. |
| btrfs | Exposes btrfs statistics |
| conntrack | Shows conntrack statistics (does nothing if no `/proc/sys/net/netfilter/` present). |
| cpu | Exposes CPU statistics |
| cpufreq | Exposes CPU frequency statistics |
| diskstats | Exposes disk I/O statistics. |
| dmi | Expose Desktop Management Interface (DMI) info from `/sys/class/dmi/id/` |
| edac | Exposes error detection and correction statistics. |
| entropy | Exposes available entropy. |
| fibrechannel | Exposes fibre channel information and statistics from `/sys/class/fc_host/`. |
| filefd | Exposes file descriptor statistics from `/proc/sys/fs/file-nr`. |
| filesystem | Exposes filesystem statistics, such as disk space used. |
| hwmon | Expose hardware monitoring and sensor data from `/sys/class/hwmon/`. |
| infiniband | Exposes network statistics specific to InfiniBand and Intel OmniPath configurations. |
| ipvs | Exposes IPVS status from `/proc/net/ip_vs` and stats from `/proc/net/ip_vs_stats`. |
| loadavg | Exposes load average. |
| mdadm | Exposes statistics about devices in `/proc/mdstat` (does nothing if no `/proc/mdstat` present). |
| meminfo | Exposes memory statistics. |
| netclass | Exposes network interface info from `/sys/class/net/` |
| netdev | Exposes network interface statistics such as bytes transferred. |
| netstat | Exposes network statistics from `/proc/net/netstat`. This is the same information as `netstat -s`. |
| nfs | Exposes NFS client statistics from `/proc/net/rpc/nfs`. This is the same information as `nfsstat -c`. |
| nfsd | Exposes NFS kernel server statistics from `/proc/net/rpc/nfsd`. This is the same information as `nfsstat -s`. |
| nvme | Exposes NVMe info from `/sys/class/nvme/` |
| os | Expose OS release info from `/etc/os-release` or `/usr/lib/os-release` (`_any_` OS) |
| powersupplyclass | Exposes Power Supply statistics from `/sys/class/power_supply` |
| pressure | Exposes pressure stall statistics from `/proc/pressure/`. (kernel 4.20+ and/or CONFIG_PSI) |
| rapl | Exposes various statistics from `/sys/class/powercap`. |
| schedstat | Exposes task scheduler statistics from `/proc/schedstat`. |
| selinux | Exposes SELinux statistics. |
| sockstat | Exposes various statistics from `/proc/net/sockstat`. |
| softnet | Exposes statistics from `/proc/net/softnet_stat`. |
| stat | Exposes various statistics from `/proc/stat`. This includes boot time, forks and interrupts. |
| tapestats | Exposes statistics from `/sys/class/scsi_tape`. |
| textfile | Exposes statistics read from local disk (`--collector.textfile.directory`, `_any_` OS). |
| thermal_zone | Exposes thermal zone & cooling device statistics from `/sys/class/thermal`. |
| time | Exposes the current system time. (`_any_` OS) |
| timex | Exposes selected adjtimex(2) system call stats. |
| udp_queues | Exposes UDP total lengths of the rx_queue and tx_queue from `/proc/net/udp` and `/proc/net/udp6`. |
| uname | Exposes system information as provided by the uname system call. |
| vmstat | Exposes statistics from `/proc/vmstat`. |
| watchdog | Exposes statistics from `/sys/class/watchdog` |
| xfs | Exposes XFS runtime statistics. (kernel 4.4+) |
| zfs | Exposes ZFS performance statistics. |

### Disabled by default

| Collector | Description |
|---|---|
| buddyinfo | Exposes statistics of memory fragments as reported by /proc/buddyinfo. |
| cgroups | A summary of the number of active and enabled cgroups |
| cpu_vulnerabilities | Exposes CPU vulnerability information from sysfs. |
| drm | Expose GPU metrics using sysfs / DRM (`amdgpu` driver only). |
| drbd | Exposes Distributed Replicated Block Device statistics (to version 8.4) |
| ethtool | Exposes network interface information and network driver statistics equivalent to `ethtool`, `ethtool -S`, and `ethtool -i`. |
| interrupts | Exposes detailed interrupts statistics. |
| ksmd | Exposes kernel and system statistics from `/sys/kernel/mm/ksm`. |
| lnstat | Exposes stats from `/proc/net/stat/`. |
| logind | Exposes session counts from logind. |
| meminfo_numa | Exposes memory statistics from `/sys/devices/system/node/node[0-9]*/meminfo`, `numastat`. |
| mountstats | Exposes filesystem statistics from `/proc/self/mountstats`. Detailed NFS client statistics. |
| network_route | Exposes the routing table as metrics |
| pcidevice | Exposes pci devices' information including their link status and parent devices. |
| perf | Exposes perf based metrics (kernel-configuration-dependent). |
| processes | Exposes aggregate process statistics from `/proc`. |
| qdisc | Exposes queuing discipline statistics |
| slabinfo | Exposes slab statistics from `/proc/slabinfo`. |
| softirqs | Exposes detailed softirq statistics from `/proc/softirqs`. |
| sysctl | Expose sysctl values from `/proc/sys`. |
| swap | Expose swap information from `/proc/swaps`. |
| systemd | Exposes service and system status from systemd. |
| tcpstat | Exposes TCP connection status information from `/proc/net/tcp` and `/proc/net/tcp6`. |
| wifi | Exposes WiFi device and station statistics. |
| xfrm | Exposes statistics from `/proc/net/xfrm_stat` |
| zoneinfo | Exposes NUMA memory zone metrics. |

### Deprecated

| Collector | Description |
|---|---|
| ntp | Exposes local NTP daemon health. (`_any_` OS) |
| runit | Exposes service status from runit. (`_any_` OS) |
| supervisord | Exposes service status from supervisord. (`_any_` OS) |
