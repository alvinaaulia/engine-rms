# Clean Run Failure

Status: **FAIL at environment metadata stage**.

Migration and Laravel environment discovery passed. `php artisan db:show` then requested an interactive Doctrine DBAL installation and waited for input, so the runner was terminated. No correctness test gate had started.

Resolution: the clean runner now uses a bounded, read-only Laravel database query for version, database name, collation, and timezone. This failed run is preserved and a new run ID is used for the retry.

