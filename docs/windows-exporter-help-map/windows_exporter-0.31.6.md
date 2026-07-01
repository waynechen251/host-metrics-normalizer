# windows_exporter 0.31.6 HELP knowledge

Source: `http://127.0.0.1:9182/metrics`

Configured collectors (user-provided): `defaults, ad, adfs, cache, container, cpu_info, dfsr, dhcp, dns, exchange, filetime, hyperv, iis, logon, memory, mscluster, msmq, mssql, network, paging_file, physical_disk, process, remote_fx, scheduled_task, smtp, terminal_services, thermalzone, time, vmware`

Observed `windows_exporter_collector_success` collectors: cpu, logical_disk, memory, net, os, physical_disk, service, system

Rule: split Windows metrics by `# HELP` family name prefix, then map them to the collector sections below. Families that do not emit a `# HELP` line in this snapshot are not listed here.

## exporter (5 families)

- `windows_exporter_build_info` - A metric with a constant '1' value labeled by version, revision, branch, goversion from which windows_exporter was built, and the goos and goarch for the build.
- `windows_exporter_collector_duration_seconds` - windows_exporter: Duration of a collection.
- `windows_exporter_collector_success` - windows_exporter: Whether the collector was successful.
- `windows_exporter_collector_timeout` - windows_exporter: Whether the collector timed out.
- `windows_exporter_scrape_duration_seconds` - windows_exporter: Total scrape duration.

## cpu (14 families)

- `windows_cpu_clock_interrupts` - Total number of received and serviced clock tick interrupts
- `windows_cpu_core_frequency_mhz` - Core frequency in megahertz
- `windows_cpu_cstate_seconds` - Time spent in low-power idle state
- `windows_cpu_dpcs` - Total number of received and serviced deferred procedure calls (DPCs)
- `windows_cpu_idle_break_events` - Total number of time processor was woken from idle
- `windows_cpu_interrupts` - Total number of received and serviced hardware interrupts
- `windows_cpu_logical_processor` - Total number of logical processors
- `windows_cpu_parking_status` - Parking Status represents whether a processor is parked or not
- `windows_cpu_processor_mperf` - Processor MPerf is the number of TSC ticks incremented while executing instructions
- `windows_cpu_processor_performance` - Processor Performance is the average performance of the processor while it is executing instructions, as a percentage of the nominal performance of the processor. On some processors, Processor Performance may exceed 100%
- `windows_cpu_processor_privileged_utility` - Processor Privileged Utility represents is the amount of time the core has spent executing instructions inside the kernel
- `windows_cpu_processor_rtc` - Processor RTC represents the number of RTC ticks made since the system booted. It should consistently be 64e6, and can be used to properly derive Processor Utility Rate
- `windows_cpu_processor_utility` - Processor Utility represents is the amount of time the core spends executing instructions
- `windows_cpu_time` - Time that processor spent in different modes (dpc, idle, interrupt, privileged, user)

## logical_disk (17 families)

- `windows_logical_disk_avg_read_requests_queued` - Average number of read requests that were queued for the selected disk during the sample interval (LogicalDisk.AvgDiskReadQueueLength)
- `windows_logical_disk_avg_write_requests_queued` - Average number of write requests that were queued for the selected disk during the sample interval (LogicalDisk.AvgDiskWriteQueueLength)
- `windows_logical_disk_free_bytes` - Free space in bytes, updates every 10-15 min (LogicalDisk.PercentFreeSpace)
- `windows_logical_disk_idle_seconds` - Seconds that the disk was idle (LogicalDisk.PercentIdleTime)
- `windows_logical_disk_info` - A metric with a constant '1' value labeled with logical disk information
- `windows_logical_disk_read_bytes` - The number of bytes transferred from the disk during read operations (LogicalDisk.DiskReadBytesPerSec)
- `windows_logical_disk_read_latency_seconds` - Shows the average time, in seconds, of a read operation from the disk (LogicalDisk.AvgDiskSecPerRead)
- `windows_logical_disk_read_seconds` - Seconds that the disk was busy servicing read requests (LogicalDisk.PercentDiskReadTime)
- `windows_logical_disk_read_write_latency_seconds` - Shows the time, in seconds, of the average disk transfer (LogicalDisk.AvgDiskSecPerTransfer)
- `windows_logical_disk_reads` - The number of read operations on the disk (LogicalDisk.DiskReadsPerSec)
- `windows_logical_disk_requests_queued` - The number of requests queued to the disk (LogicalDisk.CurrentDiskQueueLength)
- `windows_logical_disk_size_bytes` - Total space in bytes, updates every 10-15 min (LogicalDisk.PercentFreeSpace_Base)
- `windows_logical_disk_split_ios` - The number of I/Os to the disk were split into multiple I/Os (LogicalDisk.SplitIOPerSec)
- `windows_logical_disk_write_bytes` - The number of bytes transferred to the disk during write operations (LogicalDisk.DiskWriteBytesPerSec)
- `windows_logical_disk_write_latency_seconds` - Shows the average time, in seconds, of a write operation to the disk (LogicalDisk.AvgDiskSecPerWrite)
- `windows_logical_disk_write_seconds` - Seconds that the disk was busy servicing write requests (LogicalDisk.PercentDiskWriteTime)
- `windows_logical_disk_writes` - The number of write operations on the disk (LogicalDisk.DiskWritesPerSec)

## memory (35 families)

- `windows_memory_available_bytes` - The amount of physical memory immediately available for allocation to a process or for system use. It is equal to the sum of memory assigned to the standby (cached), free and zero page lists (AvailableBytes)
- `windows_memory_cache_bytes` - (CacheBytes)
- `windows_memory_cache_bytes_peak` - (CacheBytesPeak)
- `windows_memory_cache_faults` - Number of faults which occur when a page sought in the file system cache is not found there and must be retrieved from elsewhere in memory (soft fault) or from disk (hard fault) (Cache Faults/sec)
- `windows_memory_commit_limit` - (CommitLimit)
- `windows_memory_committed_bytes` - (CommittedBytes)
- `windows_memory_demand_zero_faults` - The number of zeroed pages required to satisfy faults. Zeroed pages, pages emptied of previously stored data and filled with zeros, are a security feature of Windows that prevent processes from seeing data stored by earlier processes that used the memory space (Demand Zero Faults/sec)
- `windows_memory_free_and_zero_page_list_bytes` - The amount of physical memory, in bytes, that is assigned to the free and zero page lists. This memory does not contain cached data. It is immediately available for allocation to a process or for system use (FreeAndZeroPageListBytes)
- `windows_memory_free_system_page_table_entries` - (FreeSystemPageTableEntries)
- `windows_memory_modified_page_list_bytes` - The amount of physical memory, in bytes, that is assigned to the modified page list. This memory contains cached data and code that is not actively in use by processes, the system and the system cache (ModifiedPageListBytes)
- `windows_memory_page_faults` - Overall rate at which faulted pages are handled by the processor (Page Faults/sec)
- `windows_memory_physical_free_bytes` - The amount of physical memory currently available, in bytes. This is the amount of physical memory that can be immediately reused without having to write its contents to disk first. It is the sum of the size of the standby, free, and zero lists.
- `windows_memory_physical_total_bytes` - The amount of actual physical memory, in bytes.
- `windows_memory_pool_nonpaged_allocs_total` - The number of calls to allocate space in the nonpaged pool. The nonpaged pool is an area of system memory area for objects that cannot be written to disk, and must remain in physical memory as long as they are allocated (PoolNonpagedAllocs)
- `windows_memory_pool_nonpaged_bytes` - Number of bytes in the non-paged pool, an area of the system virtual memory that is used for objects that cannot be written to disk, but must remain in physical memory as long as they are allocated (PoolNonpagedBytes)
- `windows_memory_pool_paged_allocs` - Number of calls to allocate space in the paged pool, regardless of the amount of space allocated in each call (PoolPagedAllocs)
- `windows_memory_pool_paged_bytes` - (PoolPagedBytes)
- `windows_memory_pool_paged_resident_bytes` - The size, in bytes, of the portion of the paged pool that is currently resident and active in physical memory. The paged pool is an area of the system virtual memory that is used for objects that can be written to disk when they are not being used (PoolPagedResidentBytes)
- `windows_memory_process_memory_limit_bytes` - The size of the user-mode portion of the virtual address space of the calling process, in bytes. This value depends on the type of process, the type of processor, and the configuration of the operating system.
- `windows_memory_standby_cache_core_bytes` - The amount of physical memory, in bytes, that is assigned to the core standby cache page lists. This memory contains cached data and code that is not actively in use by processes, the system and the system cache (StandbyCacheCoreBytes)
- `windows_memory_standby_cache_normal_priority_bytes` - The amount of physical memory, in bytes, that is assigned to the normal priority standby cache page lists. This memory contains cached data and code that is not actively in use by processes, the system and the system cache (StandbyCacheNormalPriorityBytes)
- `windows_memory_standby_cache_reserve_bytes` - The amount of physical memory, in bytes, that is assigned to the reserve standby cache page lists. This memory contains cached data and code that is not actively in use by processes, the system and the system cache (StandbyCacheReserveBytes)
- `windows_memory_swap_page_operations` - Total number of swap page read and writes (PagesPerSec)
- `windows_memory_swap_page_reads` - Number of disk page reads (a single read operation reading several pages is still only counted once) (PageReadsPerSec)
- `windows_memory_swap_page_writes` - Number of disk page writes (a single write operation writing several pages is still only counted once) (PageWritesPerSec)
- `windows_memory_swap_pages_read` - Number of pages read across all page reads (ie counting all pages read even if they are read in a single operation) (PagesInputPerSec)
- `windows_memory_swap_pages_written` - Number of pages written across all page writes (ie counting all pages written even if they are written in a single operation) (PagesOutputPerSec)
- `windows_memory_system_cache_resident_bytes` - The size, in bytes, of the portion of the system file cache which is currently resident and active in physical memory (SystemCacheResidentBytes)
- `windows_memory_system_code_resident_bytes` - The size, in bytes, of the pageable operating system code that is currently resident and active in physical memory (SystemCodeResidentBytes)
- `windows_memory_system_code_total_bytes` - The size, in bytes, of the pageable operating system code currently mapped into the system virtual address space (SystemCodeTotalBytes)
- `windows_memory_system_driver_resident_bytes` - The size, in bytes, of the pageable physical memory being used by device drivers. It is the working set (physical memory area) of the drivers (SystemDriverResidentBytes)
- `windows_memory_system_driver_total_bytes` - The size, in bytes, of the pageable virtual memory currently being used by device drivers. Pageable memory can be written to disk when it is not being used (SystemDriverTotalBytes)
- `windows_memory_transition_faults` - Number of faults rate at which page faults are resolved by recovering pages that were being used by another process sharing the page, or were on the modified page list or the standby list, or were being written to disk at the time of the page fault (TransitionFaultsPerSec)
- `windows_memory_transition_pages_repurposed` - Transition Pages RePurposed is the rate at which the number of transition cache pages were reused for a different purpose (TransitionPagesRePurposedPerSec)
- `windows_memory_write_copies` - The number of page faults caused by attempting to write that were satisfied by copying the page from elsewhere in physical memory (WriteCopiesPerSec)

## net (16 families)

- `windows_net_bytes` - (Network.BytesTotalPerSec)
- `windows_net_bytes_received` - (Network.BytesReceivedPerSec)
- `windows_net_bytes_sent` - (Network.BytesSentPerSec)
- `windows_net_current_bandwidth_bytes` - (Network.CurrentBandwidth)
- `windows_net_nic_address_info` - A metric with a constant '1' value labeled with the network interface's address information.
- `windows_net_nic_info` - A metric with a constant '1' value labeled with the network interface's general information.
- `windows_net_nic_operation_status` - The operational status for the interface as defined in RFC 2863 as IfOperStatus.
- `windows_net_output_queue_length_packets` - (Network.OutputQueueLength)
- `windows_net_packets` - (Network.PacketsPerSec)
- `windows_net_packets_outbound_discarded` - (Network.PacketsOutboundDiscarded)
- `windows_net_packets_outbound_errors` - (Network.PacketsOutboundErrors)
- `windows_net_packets_received` - (Network.PacketsReceivedPerSec)
- `windows_net_packets_received_discarded` - (Network.PacketsReceivedDiscarded)
- `windows_net_packets_received_errors` - (Network.PacketsReceivedErrors)
- `windows_net_packets_received_unknown` - (Network.PacketsReceivedUnknown)
- `windows_net_packets_sent` - (Network.PacketsSentPerSec)

## os (2 families)

- `windows_os_hostname` - Labelled system hostname information as provided by ComputerSystem.DNSHostName and ComputerSystem.Domain
- `windows_os_info` - Contains full product name & version in labels. Note that the "major_version" for Windows 11 is "10"; a build number greater than 22000 represents Windows 11.

## physical_disk (12 families)

- `windows_physical_disk_idle_seconds` - Seconds that the disk was idle (PhysicalDisk.PercentIdleTime)
- `windows_physical_disk_read_bytes` - The number of bytes transferred from the disk during read operations (PhysicalDisk.DiskReadBytesPerSec)
- `windows_physical_disk_read_latency_seconds` - Shows the average time, in seconds, of a read operation from the disk (PhysicalDisk.AvgDiskSecPerRead)
- `windows_physical_disk_read_seconds` - Seconds that the disk was busy servicing read requests (PhysicalDisk.PercentDiskReadTime)
- `windows_physical_disk_read_write_latency_seconds` - Shows the time, in seconds, of the average disk transfer (PhysicalDisk.AvgDiskSecPerTransfer)
- `windows_physical_disk_reads` - The number of read operations on the disk (PhysicalDisk.DiskReadsPerSec)
- `windows_physical_disk_requests_queued` - The number of requests queued to the disk (PhysicalDisk.CurrentDiskQueueLength)
- `windows_physical_disk_split_ios` - The number of I/Os to the disk were split into multiple I/Os (PhysicalDisk.SplitIOPerSec)
- `windows_physical_disk_write_bytes` - The number of bytes transferred to the disk during write operations (PhysicalDisk.DiskWriteBytesPerSec)
- `windows_physical_disk_write_latency_seconds` - Shows the average time, in seconds, of a write operation to the disk (PhysicalDisk.AvgDiskSecPerWrite)
- `windows_physical_disk_write_seconds` - Seconds that the disk was busy servicing write requests (PhysicalDisk.PercentDiskWriteTime)
- `windows_physical_disk_writes` - The number of write operations on the disk (PhysicalDisk.DiskWritesPerSec)

## service (4 families)

- `windows_service_info` - A metric with a constant '1' value labeled with service information
- `windows_service_process` - Process of started service. The value is the creation time of the process as a unix timestamp.
- `windows_service_start_mode` - The start mode of the service (StartMode)
- `windows_service_state` - The state of the service (State)

## system (8 families)

- `windows_system_boot_time_timestamp` - Unix timestamp of system boot time
- `windows_system_context_switches` - Total number of context switches (WMI source: PerfOS_System.ContextSwitchesPersec)
- `windows_system_exception_dispatches` - Total number of exceptions dispatched (WMI source: PerfOS_System.ExceptionDispatchesPersec)
- `windows_system_processes` - Current number of processes (WMI source: PerfOS_System.Processes)
- `windows_system_processes_limit` - Maximum number of processes.
- `windows_system_processor_queue_length` - Length of processor queue (WMI source: PerfOS_System.ProcessorQueueLength)
- `windows_system_system_calls` - Total number of system calls (WMI source: PerfOS_System.SystemCallsPersec)
- `windows_system_threads` - Current number of threads (WMI source: PerfOS_System.Threads)

## Not observed in this snapshot

The following configured collectors did not emit any `# HELP` lines in the current scrape and are therefore omitted from this knowledge file:

`ad`, `adfs`, `cache`, `container`, `cpu_info`, `dfsr`, `dhcp`, `dns`, `exchange`, `filetime`, `hyperv`, `iis`, `logon`, `mscluster`, `msmq`, `mssql`, `paging_file`, `remote_fx`, `scheduled_task`, `smtp`, `terminal_services`, `thermalzone`, `time`, `vmware`
