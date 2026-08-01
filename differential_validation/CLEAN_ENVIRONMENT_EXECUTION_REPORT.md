
# Clean-environment execution report

Status: `NOT_EXECUTED`. Exit code: `None`. Missing dependencies: docker, docker compose.

The intended method is `fresh Docker build without cache` with `docker compose build --no-cache && docker compose run --rm differential-validation`. No build log, container version, runtime timestamps, or peak-memory value is fabricated. Docker was not available on this host, so clean-environment reproduction is not a PASS.
