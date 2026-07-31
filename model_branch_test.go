package main

import (
	"encoding/json"
	"math"
	"testing"
)

func TestParseDynamicFloatCoversSupportedAndRejectedTypes(t *testing.T) {
	tests := []struct {
		name  string
		input interface{}
		want  float64
		ok    bool
	}{
		{name: "bool true", input: true, want: 1, ok: true},
		{name: "bool false", input: false, want: 0, ok: true},
		{name: "float64", input: float64(1.25), want: 1.25, ok: true},
		{name: "float32", input: float32(2.5), want: 2.5, ok: true},
		{name: "int", input: int(3), want: 3, ok: true},
		{name: "int64", input: int64(4), want: 4, ok: true},
		{name: "json number", input: json.Number("5.5"), want: 5.5, ok: true},
		{name: "invalid json number", input: json.Number("bad"), ok: false},
		{name: "numeric string", input: " 6.75 ", want: 6.75, ok: true},
		{name: "invalid string", input: "not-a-number", ok: false},
		{name: "unsupported", input: struct{}{}, ok: false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, ok := parseDynamicFloat(tt.input)
			if ok != tt.ok {
				t.Fatalf("expected ok=%v, got %v", tt.ok, ok)
			}
			if ok && math.Abs(got-tt.want) > 0.000001 {
				t.Fatalf("expected %.6f, got %.6f", tt.want, got)
			}
		})
	}

	if got := parseDynamicFloatOrZero("invalid"); got != 0 {
		t.Fatalf("expected invalid numeric input to become zero, got %.2f", got)
	}
}

func TestParseDynamicTextCoversSupportedTypes(t *testing.T) {
	tests := []struct {
		name  string
		input interface{}
		want  string
	}{
		{name: "nil", input: nil, want: ""},
		{name: "string", input: "active", want: "active"},
		{name: "bool", input: true, want: "true"},
		{name: "json number", input: json.Number("7.5"), want: "7.5"},
		{name: "float64", input: float64(8.5), want: "8.5"},
		{name: "float32", input: float32(9.5), want: "9.5"},
		{name: "int", input: int(10), want: "10"},
		{name: "int64", input: int64(11), want: "11"},
		{name: "fallback", input: struct{ Code string }{Code: "A"}, want: "{A}"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := parseDynamicText(tt.input); got != tt.want {
				t.Fatalf("expected %q, got %q", tt.want, got)
			}
		})
	}
}

func TestParseDynamicBoolCoversAliasesAndRejectedValues(t *testing.T) {
	tests := []struct {
		name  string
		input interface{}
		want  bool
		ok    bool
	}{
		{name: "bool true", input: true, want: true, ok: true},
		{name: "bool false", input: false, want: false, ok: true},
		{name: "true", input: "true", want: true, ok: true},
		{name: "one", input: "1", want: true, ok: true},
		{name: "yes", input: "yes", want: true, ok: true},
		{name: "y", input: "y", want: true, ok: true},
		{name: "ya", input: "ya", want: true, ok: true},
		{name: "false", input: "false", want: false, ok: true},
		{name: "zero", input: "0", want: false, ok: true},
		{name: "no", input: "no", want: false, ok: true},
		{name: "n", input: "n", want: false, ok: true},
		{name: "tidak", input: "tidak", want: false, ok: true},
		{name: "unknown string", input: "maybe", ok: false},
		{name: "numeric true", input: 2, want: true, ok: true},
		{name: "numeric false", input: 0, want: false, ok: true},
		{name: "unsupported", input: struct{}{}, ok: false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, ok := parseDynamicBool(tt.input)
			if ok != tt.ok || (ok && got != tt.want) {
				t.Fatalf("expected (%v, %v), got (%v, %v)", tt.want, tt.ok, got, ok)
			}
		})
	}
}

func TestNormalizeDynamicFactKeyAndCollectExtraFacts(t *testing.T) {
	if got := normalizeDynamicFactKey(" __Custom-- Payroll  Value__ "); got != "custom_payroll_value" {
		t.Fatalf("unexpected normalized key %q", got)
	}

	extra := collectExtraFacts(map[string]interface{}{
		"___":        1,
		"known":      2,
		"extra":      3,
		"Custom-Key": 4,
	}, map[string]bool{"known": true})

	if len(extra) != 1 || extra["custom_key"] != 4 {
		t.Fatalf("expected only normalized custom fact, got %#v", extra)
	}
}

func TestDomainFactUnmarshalRejectsMalformedJSON(t *testing.T) {
	tests := []struct {
		name string
		run  func() error
	}{
		{name: "employee", run: func() error { return (&Employee{}).UnmarshalJSON([]byte(`{"broken":`)) }},
		{name: "attendance", run: func() error { return (&Attendance{}).UnmarshalJSON([]byte(`{"broken":`)) }},
		{name: "rates", run: func() error { return (&Rates{}).UnmarshalJSON([]byte(`{"broken":`)) }},
		{name: "components", run: func() error { return (&Components{}).UnmarshalJSON([]byte(`{"broken":`)) }},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if err := tt.run(); err == nil {
				t.Fatal("expected malformed JSON error")
			}
		})
	}
}

func TestEmployeeUnmarshalAndAccessorsCoverKnownDynamicAndMissingFacts(t *testing.T) {
	var employee Employee
	err := json.Unmarshal([]byte(`{
		"status":"active",
		"contract_type":"permanent",
		"grade":"A1",
		"join_date":"2024-01-01",
		"has_npwp":"yes",
		"ptkp_status":"K/0",
		"years_of_service":"2.5",
		"performance_score":90,
		"basic_salary":1000000,
		"custom_text":123,
		"custom_number":"42.5",
		"custom_bool":"tidak",
		"custom_true":"yes",
		"invalid_number":"bad"
	}`), &employee)
	if err != nil {
		t.Fatalf("unexpected employee decode error: %v", err)
	}

	textCases := map[string]string{
		"status":            "active",
		"contract_type":     "permanent",
		"grade":             "A1",
		"join_date":         "2024-01-01",
		"has_npwp":          "true",
		"ptkp_status":       "K/0",
		"years_of_service":  "2.5",
		"performance_score": "90",
		"basic_salary":      "1000000",
		"custom_text":       "123",
	}
	for key, want := range textCases {
		if got := employee.Text(key); got != want {
			t.Errorf("Text(%q): expected %q, got %q", key, want, got)
		}
	}

	valueCases := map[string]float64{
		"has_npwp":          1,
		"years_of_service":  2.5,
		"performance_score": 90,
		"basic_salary":      1000000,
		"custom_number":     42.5,
		"invalid_number":    0,
	}
	for key, want := range valueCases {
		if got := employee.Value(key); got != want {
			t.Errorf("Value(%q): expected %.2f, got %.2f", key, want, got)
		}
	}

	if !employee.Bool("has_npwp") {
		t.Error("expected has_npwp to be true")
	}
	if employee.Bool("custom_bool") {
		t.Error("expected custom_bool to be false")
	}
	if !employee.Bool("custom_true") {
		t.Error("expected custom_true to be true")
	}
	if employee.Bool("invalid_number") {
		t.Error("expected invalid boolean fact to be false")
	}

	employee.HasNpwp = false
	if employee.Value("has_npwp") != 0 {
		t.Error("expected false has_npwp to map to zero")
	}

	empty := Employee{}
	if empty.Text("unknown") != "" || empty.Value("unknown") != 0 || empty.Bool("unknown") {
		t.Error("expected missing employee extras to return zero values")
	}
}

func TestAttendanceUnmarshalAndValueCoverKnownDynamicAndRejectedFacts(t *testing.T) {
	var attendance Attendance
	err := json.Unmarshal([]byte(`{
		"days_present":20,
		"days_absent":2,
		"late_minutes":15,
		"unpaid_leave_days":1,
		"work_hours":160,
		"work_minutes":9600,
		"overtime_hours":2,
		"overtime_minutes":120,
		"bonus-hours":"2.5",
		"bad_extra":"bad",
		"___":99
	}`), &attendance)
	if err != nil {
		t.Fatalf("unexpected attendance decode error: %v", err)
	}

	wants := map[string]float64{
		"days_present":      20,
		"days_absent":       2,
		"late_minutes":      15,
		"unpaid_leave_days": 1,
		"work_hours":        160,
		"work_minutes":      9600,
		"overtime_hours":    2,
		"overtime_minutes":  120,
		"bonus_hours":       2.5,
		"bad_extra":         0,
	}
	for key, want := range wants {
		if got := attendance.Value(key); got != want {
			t.Errorf("Value(%q): expected %.2f, got %.2f", key, want, got)
		}
	}

	if (Attendance{}).Value("unknown") != 0 {
		t.Error("expected missing attendance extra to be zero")
	}
}

func TestRatesUnmarshalAndValueCoverKnownDynamicAndRejectedFacts(t *testing.T) {
	var rates Rates
	err := json.Unmarshal([]byte(`{
		"late_deduction_per_minute":1000,
		"unpaid_leave_per_day":100000,
		"overtime_per_hour":120000,
		"overtime_per_minute":2000,
		"tax_flat_amount":50000,
		"meal-rate":"25000",
		"bad_extra":"bad",
		"___":99
	}`), &rates)
	if err != nil {
		t.Fatalf("unexpected rates decode error: %v", err)
	}

	wants := map[string]float64{
		"late_deduction_per_minute": 1000,
		"unpaid_leave_per_day":      100000,
		"overtime_per_hour":         120000,
		"overtime_per_minute":       2000,
		"tax_flat_amount":           50000,
		"meal_rate":                 25000,
		"bad_extra":                 0,
	}
	for key, want := range wants {
		if got := rates.Value(key); got != want {
			t.Errorf("Value(%q): expected %.2f, got %.2f", key, want, got)
		}
	}

	if (Rates{}).Value("unknown") != 0 {
		t.Error("expected missing rate extra to be zero")
	}
}

func TestComponentsUnmarshalAndValueCoverAliasesDynamicAndMissingFacts(t *testing.T) {
	var components Components
	err := json.Unmarshal([]byte(`{
		"basic_salary":1000000,
		"th_r":100000,
		"thr":200000,
		"overtime_pay":300000,
		"custom-component":"400000",
		"bad_extra":"bad",
		"___":99
	}`), &components)
	if err != nil {
		t.Fatalf("unexpected components decode error: %v", err)
	}

	wants := map[string]float64{
		"basic_salary":     1000000,
		"th_r":             100000,
		"thr":              200000,
		"overtime_pay":     300000,
		"custom_component": 400000,
		"bad_extra":        0,
	}
	for key, want := range wants {
		if got := components.Value(key); got != want {
			t.Errorf("Value(%q): expected %.2f, got %.2f", key, want, got)
		}
	}

	if firstPresentValue(map[string]interface{}{"second": 2}, "first", "second") != 2 {
		t.Error("expected second alias to be selected")
	}
	if firstPresentValue(map[string]interface{}{}, "missing") != nil {
		t.Error("expected missing aliases to return nil")
	}
	if (Components{}).Value("unknown") != 0 {
		t.Error("expected missing component extra to be zero")
	}
}
