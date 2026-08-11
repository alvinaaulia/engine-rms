# Time Provenance Specification

The runner records canonical UTC `started_at` before deriving `temporal-v2-YYYYMMDDTHHMMSSZ-<short-hash>`. All artifacts use that run ID. Validators reject a mismatched/future run ID, mixed IDs, or `finished_at < started_at`. Local timezone is metadata only.
