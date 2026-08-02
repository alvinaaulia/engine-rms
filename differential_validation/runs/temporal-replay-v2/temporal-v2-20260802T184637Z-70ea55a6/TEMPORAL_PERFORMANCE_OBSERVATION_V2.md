# Temporal Performance Observation v2

This is a **controlled local performance observation**, not a production benchmark.

| Workload | Stage | Measured repeats | p50 us | p95 us | p99 us | max us | Snapshot p50 bytes | Max queries | Peak memory bytes |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| small | manifest_validation | 30 | 5974 | 8830 | 9131 | 9131 | 8280 | 0 | 71303168 |
| small | replay_execution | 30 | 14543 | 53921 | 58106 | 58106 | 8280 | 0 | 71303168 |
| small | comparator | 30 | 255 | 328 | 562 | 562 | 8280 | 0 | 71303168 |
| small | total | 30 | 62388 | 106746 | 106886 | 106886 | 8280 | 0 | 71303168 |
| medium | manifest_validation | 30 | 4604 | 8539 | 9325 | 9325 | 8282 | 0 | 71303168 |
| medium | replay_execution | 30 | 17092 | 65876 | 70063 | 70063 | 8282 | 0 | 71303168 |
| medium | comparator | 30 | 253 | 306 | 335 | 335 | 8282 | 0 | 71303168 |
| medium | total | 30 | 62500 | 112300 | 138152 | 138152 | 8282 | 0 | 71303168 |
| large | manifest_validation | 30 | 4772 | 8807 | 9250 | 9250 | 8413 | 0 | 71303168 |
| large | replay_execution | 30 | 33816 | 162587 | 303469 | 303469 | 8413 | 0 | 71303168 |
| large | comparator | 30 | 247 | 717 | 2496 | 2496 | 8413 | 0 | 71303168 |
| large | total | 30 | 82703 | 243276 | 351804 | 351804 | 8413 | 0 | 71303168 |

Manifest creation latency: `{"max": 75402, "p50": 34030, "p95": 75402, "p99": 75402, "sample_count": 10}`.

Environment: `{"available_memory_bytes": 2312007680, "canonical_timezone": "UTC", "cpu_model": "AMD A9-9425 RADEON R5, 5 COMPUTE CORES 2C+3G", "database_collation": "utf8mb4_0900_ai_ci", "database_name": "website_papa_v2_testing", "database_timezone": "SYSTEM", "go_version": "go version go1.26.2 windows/amd64", "local_timezone": "SE Asia Standard Time", "locale": ["English_United States", "1252"], "logical_cpu": 2, "mysql_server_version": "8.0.30", "observation_type": "controlled local performance observation", "os": "Windows-10-10.0.19045-SP0", "php_version": "8.4.20", "physical_memory_bytes": 7481974784, "python_version": "3.14.4", "storage_type": "HDD"}`
