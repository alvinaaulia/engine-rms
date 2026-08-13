# Temporal Performance Observation v2

This is a **controlled local performance observation**, not a production benchmark.

| Workload | Stage | Measured repeats | p50 us | p95 us | p99 us | max us | Snapshot p50 bytes | Max queries | Peak memory bytes |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| small | manifest_validation | 30 | 4607 | 9587 | 15466 | 15466 | 8280 | 0 | 77594624 |
| small | replay_execution | 30 | 13674 | 27289 | 76609 | 76609 | 8280 | 0 | 77594624 |
| small | comparator | 30 | 255 | 334 | 352 | 352 | 8280 | 0 | 77594624 |
| small | total | 30 | 58995 | 86338 | 161399 | 161399 | 8280 | 0 | 77594624 |
| medium | manifest_validation | 30 | 3883 | 9882 | 12798 | 12798 | 8282 | 0 | 77594624 |
| medium | replay_execution | 30 | 14314 | 33488 | 40267 | 40267 | 8282 | 0 | 77594624 |
| medium | comparator | 30 | 256 | 1212 | 1353 | 1353 | 8282 | 0 | 77594624 |
| medium | total | 30 | 60785 | 88069 | 89997 | 89997 | 8282 | 0 | 77594624 |
| large | manifest_validation | 30 | 5010 | 9307 | 9728 | 9728 | 8413 | 0 | 79691776 |
| large | replay_execution | 30 | 13261 | 17493 | 27898 | 27898 | 8413 | 0 | 79691776 |
| large | comparator | 30 | 259 | 4156 | 4999 | 4999 | 8413 | 0 | 79691776 |
| large | total | 30 | 57705 | 120093 | 215382 | 215382 | 8413 | 0 | 79691776 |

Manifest creation latency: `{"max": 66121, "p50": 37400, "p95": 66121, "p99": 66121, "sample_count": 10}`.

Environment: `{"available_memory_bytes": 3014029312, "canonical_timezone": "UTC", "cpu_model": "AMD A9-9425 RADEON R5, 5 COMPUTE CORES 2C+3G", "database_collation": "utf8mb4_0900_ai_ci", "database_name": "website_papa_v2_testing", "database_timezone": "SYSTEM", "go_version": "go version go1.26.5 windows/amd64", "local_timezone": "SE Asia Standard Time", "locale": ["English_United States", "1252"], "logical_cpu": 2, "mysql_server_version": "8.0.30", "observation_type": "controlled local performance observation", "os": "Windows-10-10.0.19045-SP0", "php_version": "8.4.20", "physical_memory_bytes": 7481974784, "python_version": "3.14.4", "storage_type": "SSD"}`
