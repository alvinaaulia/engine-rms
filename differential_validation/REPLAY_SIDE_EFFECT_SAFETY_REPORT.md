# Replay Side-Effect Safety Report

Verification replay writes only replay control data: run lifecycle, differences, and append-only audit logs. It does not call salary creation/update, attendance mutation, configuration activation, or manifest update operations.

Controls:

1. Locked manifest and output model guards reject update/delete through normal Eloquent paths.
2. Integrity validation happens before a replay-run row is created.
3. The Go request is built only from a locked manifest.
4. A database query listener guards the external replay execution window.
5. API routes require authenticated HRD/director roles and a manifest policy.
6. Original salary plus manifest/output capture is one database transaction; an incomplete capture rolls back.

Tests verify locked immutability, rejection before run creation, unchanged salary counts, and zero guarded query count. The 408-case experiment hashes all live salary rows before and after 815 supported replays (808 measured repeats plus seven mutation sentinels); both hashes are identical and the side-effect violation count is zero.

Correction replay remains intentionally unsupported.

