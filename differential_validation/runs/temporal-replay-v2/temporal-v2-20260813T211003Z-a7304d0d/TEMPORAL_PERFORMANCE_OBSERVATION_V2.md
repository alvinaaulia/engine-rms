# Temporal Performance Observation v2

This is a **controlled local performance observation**, not a production benchmark.

| Workload | Stage | Measured repeats | p50 us | p95 us | p99 us | max us | Snapshot p50 bytes | Max queries | Peak memory bytes |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| small | manifest_validation | 30 | 6140 | 15185 | 15608 | 15608 | 8280 | 0 | 78118912 |
| small | replay_execution | 30 | 20933 | 41604 | 83430 | 83430 | 8280 | 0 | 78118912 |
| small | comparator | 30 | 285 | 963 | 4493 | 4493 | 8280 | 0 | 78118912 |
| small | total | 30 | 128384 | 161849 | 213867 | 213867 | 8280 | 0 | 78118912 |
| medium | manifest_validation | 30 | 8520 | 15764 | 16226 | 16226 | 8282 | 0 | 78118912 |
| medium | replay_execution | 30 | 20815 | 33786 | 39671 | 39671 | 8282 | 0 | 78118912 |
| medium | comparator | 30 | 237 | 728 | 2520 | 2520 | 8282 | 0 | 78118912 |
| medium | total | 30 | 125959 | 170390 | 219388 | 219388 | 8282 | 0 | 78118912 |
| large | manifest_validation | 30 | 8170 | 15192 | 15769 | 15769 | 8413 | 0 | 78118912 |
| large | replay_execution | 30 | 19070 | 35300 | 36622 | 36622 | 8413 | 0 | 78118912 |
| large | comparator | 30 | 240 | 373 | 9210 | 9210 | 8413 | 0 | 78118912 |
| large | total | 30 | 124138 | 151652 | 154072 | 154072 | 8413 | 0 | 78118912 |

Manifest creation latency: `{"max": 118357, "p50": 92141, "p95": 118357, "p99": 118357, "sample_count": 10}`.

Environment: `{"available_memory_bytes": null, "canonical_timezone": "UTC", "cpu_model": "AMD A9-9425 RADEON R5, 5 COMPUTE CORES 2C+3G", "database_collation": "utf8mb4_0900_ai_ci", "database_name": "website_papa_v2_testing", "database_timezone": "SYSTEM", "go_version": "go version go1.26.5 linux/amd64", "local_timezone": "+07", "locale": ["C", "UTF-8"], "logical_cpu": 2, "mysql_server_version": "8.0.30", "observation_type": "controlled local performance observation", "os": "Linux-6.18.33.2-microsoft-standard-WSL2-x86_64-with-glibc2.43", "php_version": "8.5.4", "physical_memory_bytes": null, "python_version": "3.14.4", "storage_type": "SSD"}`
