package infrastructure

import future.keywords.if

# Default deny everything
default allow := false
default reason := "All checks passed"

# Allow if all infrastructure checks pass
allow if {
    input.disk_free_gb >= data.min_disk_gb
    input.cpu_load <= data.max_cpu_load
    input.mem_percent <= data.max_memory_percent
}

# Reason for disk failure
reason := msg if {
    input.disk_free_gb < data.min_disk_gb
    msg := sprintf(
        "Disk free %.1fGB is below minimum %.1fGB",
        [input.disk_free_gb, data.min_disk_gb]
    )
}

# Reason for CPU failure
reason := msg if {
    input.cpu_load > data.max_cpu_load
    msg := sprintf(
        "CPU load %.2f exceeds maximum %.2f",
        [input.cpu_load, data.max_cpu_load]
    )
}

# Reason for memory failure
reason := msg if {
    input.mem_percent > data.max_memory_percent
    msg := sprintf(
        "Memory usage %.1f%% exceeds maximum %.1f%%",
        [input.mem_percent, data.max_memory_percent]
    )
}
