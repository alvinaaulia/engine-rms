package main

type Condition struct {
	Field    string      `json:"field"`
	Operator string      `json:"operator"`
	Value    interface{} `json:"value"`
}

type Action struct {
	Type    string `json:"type"`    // "ADD_COMPONENT"
	Code    string `json:"code"`    // contoh: "OVERTIME_PAY"
	Formula string `json:"formula"` // contoh: "attendance.OvertimeMinutes * rates.OvertimePerMinute"
}

type Rule struct {
	Conditions []Condition `json:"conditions"`
	Action     Action      `json:"action"`
}

type ExecuteRequest struct {
	Rules []Rule                 `json:"rules"`
	Facts map[string]interface{} `json:"facts"`
}

type Component struct {
	Code   string `json:"code"`
	Amount int64  `json:"amount"`
	RuleIx int    `json:"source_rule"`
}

type Summary struct {
	BasicSalary     int64 `json:"basic_salary"`
	GrossSalary     int64 `json:"gross_salary"`
	TotalDeductions int64 `json:"total_deductions"`
	NetSalary       int64 `json:"net_salary"`
}

type ExecuteResponse struct {
	Components []Component `json:"components"`
	Summary    Summary     `json:"summary"`
}

type Employee struct {
	Status         string `json:"status"`
	YearsOfService int64  `json:"years_of_service"`
	BasicSalary    int64  `json:"basic_salary"`
}

type Attendance struct {
	LateMinutes     int64 `json:"late_minutes"`
	UnpaidLeaveDays int64 `json:"unpaid_leave_days"`
	OvertimeMinutes int64 `json:"overtime_minutes"`
}

type Rates struct {
	LatePerMinute     int64 `json:"late_deduction_per_minute"`
	UnpaidLeavePerDay int64 `json:"unpaid_leave_per_day"`
	OvertimePerMinute int64 `json:"overtime_per_minute"`
	TaxFlatAmount     int64 `json:"tax_flat_amount"`
}

type Facts struct {
	Employee    Employee    `json:"employee"`
	Attendance  Attendance  `json:"attendance"`
	Rates       Rates       `json:"rates"`
}
