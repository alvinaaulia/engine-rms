# Runner availability report V4

| Runner | Availability | Selected | Result | Evidence |
|---|---|---|---|---|
| WSL 2 native Ubuntu | Available | Yes | PASS | `runs/clean-environment/wsl-clean-20260802T090158Z/environment.json` |
| Docker Compose | Intentionally not used | No | NOT_APPLICABLE | `runs/clean-environment/wsl-clean-20260802T090158Z/image-digests.json` |
| Hosted/remote runner | Not required for this closure | No | NOT_SELECTED | local commit-pinned source was available |

The selected runner was WSL 2 with an isolated workload: new commit-pinned source clones, a new Python virtual environment, isolated dependency caches, and a freshly recreated dedicated test schema. The Ubuntu base distribution and Windows MySQL server already existed; this was not a newly provisioned VM.
