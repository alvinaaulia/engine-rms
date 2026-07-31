# Payroll Domain Dictionary

The inventory is derived from Laravel validation/services, migrations/models, active database records audited on 2026-08-01, TPR-IR documentation, and Go fact models. No new payroll component code is introduced.

| Elemen | Kode/Field | Tipe | Sumber | Formula/Aturan | Batas penting |
|---|---|---|---|---|---|
| Employee fact | `employee.status` | string | Laravel/Go static catalog | Rule eligibility/status | `tetap`, `freelancer`, `nonaktif`; nonaktif excludes TAX_FLAT |
| Employee fact | `employee.contract_type` | string | Laravel/Go static catalog | Context fact | `karyawan_tetap`, `freelancer` |
| Employee fact | `employee.has_npwp` | boolean | Laravel/Go static catalog | Tax context | strict boolean |
| Employee fact | `employee.ptkp_status` | string | Laravel/Go static catalog | Tax context | synthetic values use `TK/0`, `K/1` |
| Employee fact | `employee.grade` | string | Laravel/Go static catalog | Grade context | string operators |
| Employee fact | `employee.join_date` | date | Laravel/Go static catalog | Service/date conditions | canonical `YYYY-MM-DD` |
| Employee fact | `employee.years_of_service` | numeric | Laravel/Go static catalog | Service context | zero and positive boundary |
| Employee fact | `employee.performance_score` | numeric | active rules 4–6 | Select performance bonus band | 69/70/71, 79/80/81, 89/90/91 |
| Employee fact | `employee.basic_salary` | numeric decimal | active formulas | Base for bonus/THR and summary | zero, 1, high, and six-decimal values |
| Employee fact | `employee.annual_bonus_eligible` | boolean | active rule 7 | Enables annual bonus | strict true/false |
| Employee fact | `employee.thr_eligible` | boolean | active rule 8 | Enables THR | strict true/false |
| Attendance fact | `attendance.days_present` | numeric | static catalog | Context/attendance | zero and normal periods |
| Attendance fact | `attendance.work_minutes` | numeric | static catalog | Context | non-negative |
| Attendance fact | `attendance.work_hours` | numeric | static catalog | Context | six-decimal wire value |
| Attendance fact | `attendance.days_absent` | numeric | active rules 9, 12 | Absence deduction / perfect-attendance guard | 0/1 and positive |
| Attendance fact | `attendance.late_minutes` | numeric | active rules 9, 11 | Late deduction / attendance guard | 0/1 and positive |
| Attendance fact | `attendance.unpaid_leave_days` | numeric | active rules 9, 10 | Unpaid leave deduction / attendance guard | 0/1 and positive |
| Attendance fact | `attendance.overtime_minutes` | numeric | active rule 3 | Overtime calculation | 0/1/59/60/61 and positive |
| Attendance fact | `attendance.overtime_hours` | numeric | static catalog | Equivalent context | derived minute/60 when needed |
| Rate | `absence_deduction_per_day` | numeric decimal | active rate | days absent × rate | default `100000.000000` |
| Rate | `annual_bonus_factor` | numeric decimal | active rate | basic salary × factor | default `1.000000` |
| Rate | `attendance_incentive` | numeric decimal | active rate | fixed amount | default `150000.000000` |
| Rate | `late_deduction_per_minute` | numeric decimal | active rate | late minutes × rate | default `1000.000000` |
| Rate | `lembur_freelancer` | numeric decimal | active rate | supported rate, no active rule producer in audited set | `3000.000000`, effective 2026-07-12 to 2026-08-01 |
| Rate | `overtime_per_minute` | numeric decimal | active rate | overtime minutes × rate | default `2000.000000` |
| Rate | `performance_bonus_70_79` | numeric decimal | active rate | basic salary × rate | `0.050000` |
| Rate | `performance_bonus_80_89` | numeric decimal | active rate | basic salary × rate | `0.100000` |
| Rate | `performance_bonus_90_ke_atas` | numeric decimal | active rate | basic salary × rate | `0.200000` |
| Rate/tax | `tax_flat_amount` | numeric decimal | active TAX_FLAT rule | fixed deduction | audited fallback `0`; corpus variants include decimal/positive values |
| Rate | `thr_factor` | numeric decimal | active rate | basic salary × factor | default `1.000000` |
| Rate | `unpaid_leave_per_day` | numeric decimal | active rate | unpaid days × rate | default `100000.000000` |
| Input component | `BASIC_SALARY` | EARNING/base | facts components | starting salary | defaults to employee basic salary in Go hydration |
| Output component | `ABSENCE_DEDUCTION` | DEDUCTION, non-taxable | active component/rule 12 | absent days × rate | only permanent, days > 0 |
| Output component | `ANNUAL_BONUS` | EARNING, taxable | active component/rule 7 | basic salary × annual factor | permanent and eligible |
| Output component | `ATTENDANCE_INCENTIVE` | EARNING, taxable | active component/rule 9 | fixed attendance rate | permanent; absent/unpaid/late all zero |
| Output component | `CMP_LEMBUR_FREELANCER` | EARNING, non-taxable | active component | no active rule in audited set | inventory-only, no fabricated producer |
| Output component | `LATE_DEDUCTION` | DEDUCTION, non-taxable | active component/rule 11 | late minutes × rate | permanent, late > 0 |
| Output component | `OVERTIME_PAY` | EARNING, taxable | active component/rule 3 | overtime minutes × rate | permanent, overtime > 0 |
| Output component | `PERFORMANCE_BONUS` | EARNING, taxable | active component/rules 4–6 | banded salary factor | 70–79, 80–89, ≥90 |
| Output component | `TAX_FLAT` | DEDUCTION | active component/rule 1 | fixed tax rate value | any status except nonaktif |
| Output component | `THR` | EARNING, taxable | active component/rule 8 | basic salary × THR factor | permanent and eligible |
| Output component | `UNPAID_LEAVE_DEDUCTION` | DEDUCTION, non-taxable | active component/rule 10 | unpaid days × rate | permanent, unpaid days > 0 |

## Operators and policies

- Numeric: EQ, NEQ, GT, GTE, LT, LTE, IN, NOT_IN.
- String: EQ, NEQ, CONTAINS, IN, NOT_IN.
- Boolean: EQ, NEQ.
- Date: EQ, NEQ, BEFORE, AFTER, ON_OR_BEFORE, ON_OR_AFTER, IN, NOT_IN.
- Active rules use EQ/NEQ/GT/GTE/LTE; translator fixtures cover the broader supported matrix.
- Active priorities: LOW for TAX_FLAT, NORMAL for rules 3–12.
- Active action type: ADD_COMPONENT; inferred canonical policy: COLLECT_SUM.
- Default canonical hit policy: PRIORITY. Translator fixtures additionally validate FIRST and UNIQUE.
- Effective periods: TAX_FLAT unbounded; rules 3–12 start 2026-01-01 with no end date.
- Monetary policy: six-decimal HALF_UP at candidate, aggregate, and summary; two-decimal reporting presentation.

## Defaults and exclusions

Missing required facts are rejected; they are not silently defaulted at the canonical trust boundary. Only `components.BASIC_SALARY` has a Go hydration fallback to `employee.basic_salary`. Paid-leave and general allowance fields are not active in the audited rule set and are therefore not fabricated in this corpus.
