# Temporal Dependency Inventory

| Dependency | Current source | Existing temporal identity | Existing stored value | Required replay binding | Current risk |
|---|---|---|---|---|---|
| Employee/master salary | `master_salary` | row ID only; no row version | normalized employee facts and basic salary | frozen facts hash plus employee/master source identity | current salary/status/category can change |
| Employee tax profile | `profiles` | none | normalized NPWP/PTKP facts | frozen facts only; optional source row identity | current profile lookup contaminates replay |
| Presence | `presence` | mutable row IDs not retained | aggregate days/minutes | facts snapshot and hash | corrections change regenerated facts |
| Overtime | `overtime` | row IDs not retained | approved aggregate minutes | facts snapshot and hash | approval/current rows can change |
| Leave | `leave` | row IDs not retained | aggregate paid/unpaid days | facts snapshot and hash | approval/date changes affect facts |
| Work schedule | `work_schedule_settings` or config | effective date but no captured setting ID | only work-start/end/source summary | frozen derived facts; optional schedule evidence | current DB/config fallback can differ |
| Rule versions | `rule_versions` | `id`, rule ID, version, status | component source mapping and raw engine provenance only | full canonical ruleset plus exact sorted rule-version IDs | active query and definition changes/deletion |
| Salary components | `salary_components` | component row ID but not captured | normalized code/name/type in output | component-type snapshot inside ruleset/request | current active/type/name lookup changes normalization |
| Payroll rates | `payroll_rate_settings` | `rate_setting_id`, version, effective range | decimal values only | sorted resolved rate-version IDs plus values in facts | identity currently not observable |
| Company taxes | `company_taxes` | row ID, tax code, version, effective range | tax descriptors without row/version ID | sorted resolved tax-version IDs and applied snapshot | identity currently not observable |
| TPR-IR schema | Laravel/Go constants | `1.0` in live payload | not persisted on salary | `tpr_ir_schema_version` | unsupported future schema cannot be detected |
| Translator | Laravel TPR builder plus Go GRL translator source | Git commit only | not persisted | stable compatibility version and generated-GRL hash | later code may translate differently |
| Engine | Go executable/source | Git commit only | not persisted | engine compatibility version | later execution semantics may differ |
| Rounding | TPR payload and Laravel decimal helpers | scale 6 HALF_UP, then persisted scale 2 HALF_UP | not persisted as a bound policy | explicit rounding-policy object | later policy change is invisible |
| Hit/component policy | canonical TPR-IR ruleset | per payload | not persisted | ruleset snapshot/hash | replay cannot prove conflict semantics |
| Generated GRL | Go translator | none | not returned | generated GRL and SHA-256 for strict replay | strict translator equivalence untestable |
| Original output | `salary.rule_engine_result` and salary columns | salary row ID | partial normalized and raw response | immutable components, summary, provenance, response, output hash | mutable/deletable salary is not an immutable manifest |
| Actor/reason | authenticated request and audit log | audit user where available | payslip audit record | execution/replay actor and reason | correlation to execution is weak |

## Minimum capture boundary

Original execution capture must occur after facts, rate/tax identities, canonical ruleset, component types, and version metadata have been resolved, but before invoking Go. The output must be attached and hashed before locking. Salary persistence and locked manifest/output persistence must commit atomically in one database transaction.

## Snapshot-only replay boundary

Verification replay may read only the locked manifest/output, compatibility registry, and replay-control/audit tables. It may call the Go snapshot executor. It must not call fact builders or any active/effective configuration resolver.

