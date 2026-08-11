# Temporal Performance Observation v2

This is a **controlled local performance observation**, not a production benchmark.

| Workload | Stage | Measured repeats | p50 us | p95 us | p99 us | max us | Snapshot p50 bytes | Max queries | Peak memory bytes |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| small | manifest_validation | 30 | 4611 | 13556 | 14939 | 14939 | 8280 | 0 | 73400320 |
| small | replay_execution | 30 | 15989 | 31439 | 48736 | 48736 | 8280 | 0 | 73400320 |
| small | comparator | 30 | 192 | 322 | 707 | 707 | 8280 | 0 | 73400320 |
| small | total | 30 | 83454 | 328637 | 330785 | 330785 | 8280 | 0 | 73400320 |
| medium | manifest_validation | 30 | 6224 | 10740 | 15173 | 15173 | 8282 | 0 | 73400320 |
| medium | replay_execution | 30 | 17461 | 27495 | 53685 | 53685 | 8282 | 0 | 73400320 |
| medium | comparator | 30 | 252 | 1126 | 3146 | 3146 | 8282 | 0 | 73400320 |
| medium | total | 30 | 89524 | 138766 | 6552468 | 6552468 | 8282 | 0 | 73400320 |
| large | manifest_validation | 30 | 4760 | 9250 | 12168 | 12168 | 8413 | 0 | 73400320 |
| large | replay_execution | 30 | 15032 | 31533 | 84225 | 84225 | 8413 | 0 | 73400320 |
| large | comparator | 30 | 213 | 669 | 1279 | 1279 | 8413 | 0 | 73400320 |
| large | total | 30 | 77676 | 101331 | 149140 | 149140 | 8413 | 0 | 73400320 |

Manifest creation latency: `{"max": 1820456, "p50": 72915, "p95": 1820456, "p99": 1820456, "sample_count": 10}`.

Environment: `{"available_memory_bytes": null, "canonical_timezone": "UTC", "cpu_model": "NOT_OBSERVABLE", "database_collation": "utf8mb4_0900_ai_ci", "database_name": "website_papa_v2_temporal_v2_wsl_testing", "database_timezone": "SYSTEM", "go_version": "go version go1.25.6 linux/amd64", "local_timezone": "WIB", "locale": ["C", "UTF-8"], "logical_cpu": 2, "mysql_server_version": "8.0.30", "observation_type": "controlled local performance observation", "os": "Linux-6.18.33.2-microsoft-standard-WSL2-x86_64-with-glibc2.43", "php_version": "8.5.4", "physical_memory_bytes": null, "python_version": "3.14.4", "storage_type": "NOT_OBSERVABLE"}`
