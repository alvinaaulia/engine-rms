# Code change report V4

- Added a native WSL clean-validation path, source cloning, dependency isolation, readiness gates, raw-log capture, and run finalization.
- Made frozen JSON bytes reproducible across Windows and Linux and added canonical-JSON regression coverage.
- Added the Go `/health` readiness endpoint and validation.
- Required PHP GD for the Laravel suite and improved failure reporting.
- Corrected the Laravel tax effective-date comparison to use the business calendar date; its targeted regression tests passed before the clean run and the full clean Laravel suite subsequently passed.
- Preserved four failed WSL attempts as failure evidence instead of rewriting them as successful runs.
- Frozen policy, corpus, and expected results were not changed to manufacture a pass. Domain validation remains pending and temporal replay was not started.

Executed source: engine/validation `069581549fadaa8f74281722592c5bfa68ae4053`; Laravel `269c6a656804c9ef11078539d65850f93a23f577`.
