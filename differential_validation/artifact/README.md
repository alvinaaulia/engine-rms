# Reproducible differential-validation artifact

This bundle is assembled from Git-tracked Laravel and Go sources. Install Laravel dependencies with `composer install`, copy `engine-rms/differential_validation/.env.example`, configure the isolated testing database, then run `make -C engine-rms/differential_validation differential-validation`.

The primary route builds Go from source and does not depend on a Windows executable. Docker Compose is provided as an optional clean-environment route; record its actual outcome rather than assuming success.

