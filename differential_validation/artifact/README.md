# Reproducible differential-validation artifact

This bundle is assembled from Git-tracked Laravel and Go sources. Its top level contains `laravel/`, `engine-rms/`, `differential-validation/`, `docker/`, `scripts/`, and `runs/`. Copy `.env.example` to `.env`, then run `make clean-validate`. This builds the clean images without cache and invokes the validation runner.

The primary route builds Go from source and does not depend on a Windows executable. Docker Compose is provided as an optional clean-environment route; record its actual outcome rather than assuming success.
