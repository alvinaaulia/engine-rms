# Runner availability report

| Runner | Available | Can access Laravel | Can access Go | Selected | Reason |
|---|---|---|---|---|---|
| Local Docker Compose | no | local snapshot only | yes | no | Docker and Compose executables are absent |
| Hosted GitHub Actions | workflow prepared; not dispatchable | no | public remote only | no | No CLI/API credential; private Laravel checkout failed |
| WSL/Linux | no | local snapshot only | yes | no | No installed Linux distribution |
| Clean VM | no instance | not applicable | not applicable | no | Virtualization capable, but no clean VM exists |
| Remote runner | no | no | no | no | No accessible runner endpoint or credential |

Run-scoped command evidence: `runs/clean-environment/runner-audit-20260801T112319Z/command-results.json`.
