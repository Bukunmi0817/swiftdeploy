package canary

import future.keywords.if

# Default deny everything
default allow := false
default reason := "All checks passed"

# Allow if canary health checks pass
allow if {
    input.error_rate_percent <= data.max_error_rate_percent
    input.p99_latency_ms <= data.max_p99_latency_ms
}

# Reason for error rate failure
reason := msg if {
    input.error_rate_percent > data.max_error_rate_percent
    msg := sprintf(
        "Error rate %.2f%% exceeds maximum %.2f%%",
        [input.error_rate_percent, data.max_error_rate_percent]
    )
}

# Reason for latency failure
reason := msg if {
    input.p99_latency_ms > data.max_p99_latency_ms
    msg := sprintf(
        "P99 latency %.0fms exceeds maximum %.0fms",
        [input.p99_latency_ms, data.max_p99_latency_ms]
    )
}
