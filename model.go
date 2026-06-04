package main

import (
	"encoding/json"
	"fmt"
	"strconv"
	"strings"
)

type Condition struct {
	Field    string      `json:"field"`
	Operator string      `json:"operator"`
	Value    interface{} `json:"value"`
}

type Action struct {
	Type    string `json:"type"`
	Code    string `json:"code"`
	Formula string `json:"formula"`
}

type Rule struct {
	Conditions interface{} `json:"conditions"`
	Action     Action      `json:"action"`
}

type ExecuteRequest struct {
	Rules []Rule                 `json:"rules"`
	Facts map[string]interface{} `json:"facts"`
}

type Component struct {
	Code   string  `json:"code"`
	Amount float64 `json:"amount"`
	RuleIx int     `json:"source_rule"`
}

type Summary struct {
	BasicSalary     float64 `json:"basic_salary"`
	GrossSalary     float64 `json:"gross_salary"`
	TotalDeductions float64 `json:"total_deductions"`
	NetSalary       float64 `json:"net_salary"`
}

type ExecuteResponse struct {
	Components []Component `json:"components"`
	Summary    Summary     `json:"summary"`
}

type Employee struct {
	Status           string  `json:"status"`
	ContractType     string  `json:"contract_type"`
	Grade            string  `json:"grade"`
	JoinDate         string  `json:"join_date"`
	HasNpwp          bool    `json:"has_npwp"`
	PtkpStatus       string  `json:"ptkp_status"`
	YearsOfService   int64   `json:"years_of_service"`
	PerformanceScore int64   `json:"performance_score"`
	BasicSalary      float64 `json:"basic_salary"`
	Extra            map[string]interface{}
}

type Attendance struct {
	DaysPresent     float64 `json:"days_present"`
	DaysAbsent      float64 `json:"days_absent"`
	LateMinutes     float64 `json:"late_minutes"`
	UnpaidLeaveDays float64 `json:"unpaid_leave_days"`
	WorkHours       float64 `json:"work_hours"`
	WorkMinutes     float64 `json:"work_minutes"`
	OvertimeHours   float64 `json:"overtime_hours"`
	OvertimeMinutes float64 `json:"overtime_minutes"`
	Extra           map[string]float64
}

type Rates struct {
	LatePerMinute     float64 `json:"late_deduction_per_minute"`
	UnpaidLeavePerDay float64 `json:"unpaid_leave_per_day"`
	OvertimePerHour   float64 `json:"overtime_per_hour"`
	OvertimePerMinute float64 `json:"overtime_per_minute"`
	TaxFlatAmount     float64 `json:"tax_flat_amount"`
	Extra             map[string]float64
}

func (e *Employee) UnmarshalJSON(data []byte) error {
	type employeeAlias Employee
	var alias employeeAlias
	if err := json.Unmarshal(data, &alias); err != nil {
		return err
	}

	var raw map[string]interface{}
	if err := json.Unmarshal(data, &raw); err != nil {
		return err
	}

	*e = Employee(alias)
	e.Extra = collectExtraFacts(raw, map[string]bool{
		"status":            true,
		"contract_type":     true,
		"grade":             true,
		"join_date":         true,
		"has_npwp":          true,
		"ptkp_status":       true,
		"years_of_service":  true,
		"performance_score": true,
		"basic_salary":      true,
	})

	return nil
}

func (e Employee) Text(key string) string {
	switch normalizeDynamicFactKey(key) {
	case "status":
		return e.Status
	case "contract_type":
		return e.ContractType
	case "grade":
		return e.Grade
	case "join_date":
		return e.JoinDate
	case "has_npwp":
		return strconv.FormatBool(e.HasNpwp)
	case "ptkp_status":
		return e.PtkpStatus
	case "years_of_service":
		return strconv.FormatInt(e.YearsOfService, 10)
	case "performance_score":
		return strconv.FormatInt(e.PerformanceScore, 10)
	case "basic_salary":
		return strconv.FormatFloat(e.BasicSalary, 'f', -1, 64)
	default:
		if e.Extra == nil {
			return ""
		}
		return parseDynamicText(e.Extra[normalizeDynamicFactKey(key)])
	}
}

func (e Employee) Value(key string) float64 {
	switch normalizeDynamicFactKey(key) {
	case "has_npwp":
		if e.HasNpwp {
			return 1
		}
		return 0
	case "years_of_service":
		return float64(e.YearsOfService)
	case "performance_score":
		return float64(e.PerformanceScore)
	case "basic_salary":
		return e.BasicSalary
	default:
		if e.Extra == nil {
			return 0
		}
		parsed, ok := parseDynamicFloat(e.Extra[normalizeDynamicFactKey(key)])
		if !ok {
			return 0
		}
		return parsed
	}
}

func (e Employee) Bool(key string) bool {
	switch normalizeDynamicFactKey(key) {
	case "has_npwp":
		return e.HasNpwp
	default:
		if e.Extra == nil {
			return false
		}
		parsed, ok := parseDynamicBool(e.Extra[normalizeDynamicFactKey(key)])
		return ok && parsed
	}
}

func (a *Attendance) UnmarshalJSON(data []byte) error {
	type attendanceAlias Attendance
	var alias attendanceAlias
	if err := json.Unmarshal(data, &alias); err != nil {
		return err
	}

	var raw map[string]interface{}
	if err := json.Unmarshal(data, &raw); err != nil {
		return err
	}

	*a = Attendance(alias)
	a.Extra = map[string]float64{}

	knownKeys := map[string]bool{
		"days_present":      true,
		"days_absent":       true,
		"late_minutes":      true,
		"unpaid_leave_days": true,
		"work_hours":        true,
		"work_minutes":      true,
		"overtime_hours":    true,
		"overtime_minutes":  true,
	}

	for key, value := range raw {
		normalizedKey := normalizeDynamicFactKey(key)
		if normalizedKey == "" || knownKeys[normalizedKey] {
			continue
		}

		parsed, ok := parseDynamicFloat(value)
		if ok {
			a.Extra[normalizedKey] = parsed
		}
	}

	return nil
}

func (a Attendance) Value(key string) float64 {
	switch normalizeDynamicFactKey(key) {
	case "days_present":
		return a.DaysPresent
	case "days_absent":
		return a.DaysAbsent
	case "late_minutes":
		return a.LateMinutes
	case "unpaid_leave_days":
		return a.UnpaidLeaveDays
	case "work_hours":
		return a.WorkHours
	case "work_minutes":
		return a.WorkMinutes
	case "overtime_hours":
		return a.OvertimeHours
	case "overtime_minutes":
		return a.OvertimeMinutes
	default:
		if a.Extra == nil {
			return 0
		}
		return a.Extra[normalizeDynamicFactKey(key)]
	}
}

func (r *Rates) UnmarshalJSON(data []byte) error {
	type ratesAlias Rates
	var alias ratesAlias
	if err := json.Unmarshal(data, &alias); err != nil {
		return err
	}

	var raw map[string]interface{}
	if err := json.Unmarshal(data, &raw); err != nil {
		return err
	}

	*r = Rates(alias)
	r.Extra = map[string]float64{}

	knownKeys := map[string]bool{
		"late_deduction_per_minute": true,
		"unpaid_leave_per_day":      true,
		"overtime_per_hour":         true,
		"overtime_per_minute":       true,
		"tax_flat_amount":           true,
	}

	for key, value := range raw {
		normalizedKey := normalizeDynamicFactKey(key)
		if normalizedKey == "" || knownKeys[normalizedKey] {
			continue
		}

		parsed, ok := parseDynamicFloat(value)
		if ok {
			r.Extra[normalizedKey] = parsed
		}
	}

	return nil
}

func (r Rates) Value(key string) float64 {
	switch normalizeDynamicFactKey(key) {
	case "late_deduction_per_minute":
		return r.LatePerMinute
	case "unpaid_leave_per_day":
		return r.UnpaidLeavePerDay
	case "overtime_per_hour":
		return r.OvertimePerHour
	case "overtime_per_minute":
		return r.OvertimePerMinute
	case "tax_flat_amount":
		return r.TaxFlatAmount
	default:
		if r.Extra == nil {
			return 0
		}
		return r.Extra[normalizeDynamicFactKey(key)]
	}
}

func normalizeDynamicFactKey(key string) string {
	normalized := strings.TrimSpace(strings.ToLower(key))
	normalized = strings.ReplaceAll(normalized, "-", "_")
	normalized = strings.ReplaceAll(normalized, " ", "_")
	normalized = strings.Trim(normalized, "_")

	for strings.Contains(normalized, "__") {
		normalized = strings.ReplaceAll(normalized, "__", "_")
	}

	return normalized
}

func parseDynamicFloat(value interface{}) (float64, bool) {
	switch typed := value.(type) {
	case bool:
		if typed {
			return 1, true
		}
		return 0, true
	case float64:
		return typed, true
	case float32:
		return float64(typed), true
	case int:
		return float64(typed), true
	case int64:
		return float64(typed), true
	case json.Number:
		parsed, err := typed.Float64()
		return parsed, err == nil
	case string:
		parsed, err := strconv.ParseFloat(strings.TrimSpace(typed), 64)
		return parsed, err == nil
	default:
		return 0, false
	}
}

func parseDynamicText(value interface{}) string {
	switch typed := value.(type) {
	case nil:
		return ""
	case string:
		return typed
	case bool:
		return strconv.FormatBool(typed)
	case json.Number:
		return typed.String()
	case float64:
		return strconv.FormatFloat(typed, 'f', -1, 64)
	case float32:
		return strconv.FormatFloat(float64(typed), 'f', -1, 64)
	case int:
		return strconv.Itoa(typed)
	case int64:
		return strconv.FormatInt(typed, 10)
	default:
		return fmt.Sprint(typed)
	}
}

func parseDynamicBool(value interface{}) (bool, bool) {
	switch typed := value.(type) {
	case bool:
		return typed, true
	case string:
		normalized := strings.ToLower(strings.TrimSpace(typed))
		switch normalized {
		case "true", "1", "yes", "y", "ya":
			return true, true
		case "false", "0", "no", "n", "tidak":
			return false, true
		default:
			return false, false
		}
	default:
		parsed, ok := parseDynamicFloat(value)
		if !ok {
			return false, false
		}
		return parsed != 0, true
	}
}

func collectExtraFacts(raw map[string]interface{}, knownKeys map[string]bool) map[string]interface{} {
	extra := map[string]interface{}{}

	for key, value := range raw {
		normalizedKey := normalizeDynamicFactKey(key)
		if normalizedKey == "" || knownKeys[normalizedKey] || normalizedKey == "extra" {
			continue
		}

		extra[normalizedKey] = value
	}

	return extra
}

type Components struct {
	BASIC_SALARY float64 `json:"BASIC_SALARY"`
	TH_R         float64 `json:"TH_R"`
	THR          float64 `json:"THR"`
	OVERTIME_PAY float64 `json:"OVERTIME_PAY"`
	Extra        map[string]float64
}

func (c *Components) UnmarshalJSON(data []byte) error {
	type componentsAlias Components
	var alias componentsAlias
	if err := json.Unmarshal(data, &alias); err != nil {
		return err
	}

	var raw map[string]interface{}
	if err := json.Unmarshal(data, &raw); err != nil {
		return err
	}

	*c = Components(alias)
	c.Extra = map[string]float64{}

	knownKeys := map[string]bool{
		"basic_salary": true,
		"th_r":         true,
		"thr":          true,
		"overtime_pay": true,
	}

	for key, value := range raw {
		normalizedKey := normalizeDynamicFactKey(key)
		if normalizedKey == "" || knownKeys[normalizedKey] {
			continue
		}

		parsed, ok := parseDynamicFloat(value)
		if ok {
			c.Extra[normalizedKey] = parsed
		}
	}

	return nil
}

func (c Components) Value(key string) float64 {
	switch normalizeDynamicFactKey(key) {
	case "basic_salary":
		return c.BASIC_SALARY
	case "th_r":
		return c.TH_R
	case "thr":
		return c.THR
	case "overtime_pay":
		return c.OVERTIME_PAY
	default:
		if c.Extra == nil {
			return 0
		}
		return c.Extra[normalizeDynamicFactKey(key)]
	}
}

type Facts struct {
	Employee   Employee   `json:"employee"`
	Attendance Attendance `json:"attendance"`
	Rates      Rates      `json:"rates"`
	Components Components `json:"components"`
}
