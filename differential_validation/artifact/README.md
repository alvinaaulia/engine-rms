# Reproducible differential-validation artifact

This bundle is assembled from Git-tracked Laravel and Go sources. Its top level contains `laravel/`, `engine-rms/`, `differential-validation/`, and `runs/`. Install Laravel dependencies with `composer install`, copy `.env.example` to `.env`, configure the isolated testing database, then run `make validate-differential`.

The primary route builds Go from source and does not depend on a Windows executable. Docker Compose is provided as an optional clean-environment route; record its actual outcome rather than assuming success.
