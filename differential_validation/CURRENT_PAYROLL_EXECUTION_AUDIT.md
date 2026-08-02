# Current Payroll Execution Audit

## Scope and entry point

The persisted production path starts at `SalaryController::store`. Pending-payroll previews call the same fact builder and engine service but do not persist a salary. `RuleController::execute` is a separate rule test endpoint and is not the salary persistence path.

| Stage | Source file/method | Input | Output | Versioned | Snapshot available before replay work | Replay risk |
|---|---|---|---|---|---|---|
| Authorization and request validation | `app/Http/Controllers/Api/DataMaster/SalaryController.php::store` | authenticated user, master salary ID, salary date, optional overrides/proof | validated request | no | request is not retained as a manifest | Request overrides and actor/reason cannot be reconstructed completely. |
| Payroll-period selection | `SalaryController::buildCalculationFacts`; `PayrollRuleEngineService::resolvePayrollPeriod` | salary date and current `master_salary` period | effective period | partially date-bound | dates are embedded under `facts.source` | The master salary row can later change; its row identity/version is absent. |
| Employee facts | `PayrollRuleEngineService::buildFactsFromDatabase`, `resolveEmployeeContractType`, `resolveEmployeeStatus`, `resolveEmployeeTaxProfile` | current `master_salary` and `profiles`, optional overrides | employee fact namespace | rows are not versioned | normalized values are stored in `salary.calculation_facts` | Replay through the current builder would read changed salary, contract/status, NPWP, or PTKP state. |
| Attendance facts | `collectAttendanceMetrics`, `calculateApprovedLeaveMetrics`, `WorkScheduleService::forDate` | `presence`, `overtime`, `leave`, work schedule/config | aggregated attendance and source summary | work schedule is effective-dated; attendance rows are mutable | aggregates are stored; raw row identities and schedule snapshot are not | Rebuilding facts would read corrected attendance/current schedule and change historical output. |
| Rate resolution | `resolveConfiguredPayrollRates`; `RateResolverService`; `PayrollRateSetting::usableAt` | salary date, approved/active effective rates | normalized rate values | rate rows have `rate_setting_id` and `version` | values are stored in facts; resolved IDs/versions are not | A current query can select a different row with the same key; identity cannot currently be proven from the stored salary. |
| Initial tax resolution | `resolveTaxFlatAmount`; `calculateTaxFromCompanyTaxes` | salary date, employee tax context, current active/effective tax rows | tax value and applied-tax descriptors | tax rows have ID/code/version | amount and descriptors are stored, but tax row IDs/versions are absent | Current tax rows can be changed/deactivated/deleted and historical identity is not observable. |
| Rule resolution | `loadActiveRuleDefinitions` | current ACTIVE/APPROVED rule versions, effective date, active components, active rate dependencies | sorted definitions, blocked rules, rule-version map | rule versions are explicitly versioned | component output records a source rule; canonical definition set is not persisted by `SalaryController` | `execute()` always queries ACTIVE rules and active salary components. Historical ruleset can be contaminated by current state. |
| TPR-IR normalization | `TypedPayrollRuleIrService::buildExecutePayload` | definitions, facts, component types | TPR-IR 1.0 ruleset, rounding policy, field catalog | schema constant `1.0` | payload is returned by service but omitted from persisted `rule_engine_result` | Ruleset, hit policy, component policy, field catalog, and rounding policy cannot be recovered exactly. |
| Laravel-to-Go call | `PayrollRuleEngineService::callRuleEngine` | generated execute payload | decoded Go response | no request/engine version binding | response is stored | No request ID, execution UUID, facts/ruleset hash, translator version, or engine version. |
| TPR validation | `main.go::executeRules`; `ValidateTPRRuleSet` | TPR-IR request | structured validation result or error | supports schema `1.0` | only successful response is stored | There is no temporal envelope, manifest validation, or explicit current-state-access prohibition. |
| GRL translation | `tpr_executor.go::buildTPRGRL` | canonicalized ruleset | generated GRL | implementation is source-versioned only | GRL is not returned or stored | A later translator change cannot be distinguished or replayed strictly. |
| GRULE execution | `ExecuteTPRRuleSet` | hydrated facts, generated GRL, component types | components and summary | rule provenance includes rule IDs/version IDs | raw engine response is stored | Engine compatibility version and execution hash are absent; public JSON money fields are floating-point numbers. |
| Laravel normalization | `PayrollRuleEngineService::execute` | Go response, current component map, rule-source map | components, earnings, deductions, summary, tax computation | maps rule version IDs | normalized result is stored | Component names/types are loaded from current component rows; contributor provenance is only retained inside nested engine response. |
| Salary persistence | `SalaryController::store`; `Salary::create` | normalized facts/result and optional file | live `salary` row | no immutable execution identity | facts and partial output only | There is no database transaction covering manifest/output/salary; salary can be deleted; transfer file may be written before calculation failure. |

## Current persistence contents

`salary.calculation_facts` preserves normalized employee, attendance, rate values, components, and a limited source summary. `salary.rule_engine_result` preserves normalized components/summary, tax computation, and the nested raw engine response. It does not preserve the canonical TPR-IR payload, exact ruleset, generated GRL, component-type map, version bindings, or canonical hashes.

## Rounding and numeric behavior

Laravel money normalization uses `Brick\Math\BigDecimal`; final persisted salary amounts are decimal strings at scale 2 with `HALF_UP`. TPR-IR declares scale 6 and `HALF_UP`. The Go boundary and GRULE fact structs currently use `float64`, then convert through `big.Rat` for deterministic scale-6 rounding. New temporal artifacts must use explicit decimal strings and must not introduce new floating-point money fields. The existing float boundary is a compatibility limitation to isolate and test, not evidence that arbitrary binary floats are acceptable manifest values.

## Current-state contamination points

The following lookups are forbidden during verification replay and therefore must be bypassed rather than merely date-filtered:

- `RuleVersion::where(status = ACTIVE)`;
- `SalaryComponent::where(is_active = true)` and later component-map queries;
- `PayrollRateSetting::usableAt` / `RateResolverService::currentMapForKeys`;
- `CompanyTax::where(is_active = true)`;
- `MasterSalary`, `Profile`, `Presence`, `Overtime`, and `Leave` fact reconstruction;
- `WorkScheduleService` database/config fallback;
- current translator/engine selection without compatibility binding.

## Audit conclusion

The current system has enough partial snapshots to display and audit a payslip, but not enough information to perform strict or semantically proven temporal replay. Replay must be implemented as a snapshot-only path separate from `PayrollRuleEngineService::execute`, with atomic original capture and immutable manifests.

