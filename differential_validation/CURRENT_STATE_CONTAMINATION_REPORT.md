# Current-State Contamination Report

## Guarded sources

During the snapshot execution window, a Laravel database listener records queries and rejects references to live salary/master salary, users/profiles, attendance, overtime, leave, schedules, rules/rule versions, component maps, payroll rates, and company taxes.

The replay service loads and verifies its manifest before enabling the guard. While the guard is active it performs only the HTTP call to Go. Go has no application-database integration and receives facts, ruleset, component types, hashes, versions, and policies entirely in the request envelope.

## Result

The unit/integration suite verifies a query count of zero. In the full temporal experiment, all 808 measured supported replay attempts and seven mutation-wave sentinel replays completed with zero forbidden lookups. Current rule, rate, tax, employee, rounding, rule-availability, and compatibility mutations changed current execution signatures while the historical sentinel hash remained unchanged.

The listener is an application-layer control; production database grants should additionally restrict a dedicated replay worker to read immutable source artifacts and write replay-control tables only.

