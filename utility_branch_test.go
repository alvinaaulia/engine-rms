package main

import (
	"encoding/json"
	"math"
	"testing"
)

func TestPayrollDecimalFromInterfaceCoversSupportedAndRejectedTypes(t *testing.T) {
	tests := []struct {
		name  string
		input interface{}
		want  float64
		ok    bool
	}{
		{name: "float64", input: float64(1.25), want: 1.25, ok: true},
		{name: "float64 nan", input: math.NaN(), ok: false},
		{name: "float64 infinity", input: math.Inf(1), ok: false},
		{name: "float32", input: float32(2.5), want: 2.5, ok: true},
		{name: "float32 nan", input: float32(math.NaN()), ok: false},
		{name: "float32 infinity", input: float32(math.Inf(1)), ok: false},
		{name: "int", input: int(3), want: 3, ok: true},
		{name: "int8", input: int8(4), want: 4, ok: true},
		{name: "int16", input: int16(5), want: 5, ok: true},
		{name: "int32", input: int32(6), want: 6, ok: true},
		{name: "int64", input: int64(7), want: 7, ok: true},
		{name: "uint", input: uint(8), want: 8, ok: true},
		{name: "uint8", input: uint8(9), want: 9, ok: true},
		{name: "uint16", input: uint16(10), want: 10, ok: true},
		{name: "uint32", input: uint32(11), want: 11, ok: true},
		{name: "uint64", input: uint64(12), want: 12, ok: true},
		{name: "json number", input: json.Number("13.5"), want: 13.5, ok: true},
		{name: "string", input: "14.75", want: 14.75, ok: true},
		{name: "empty string", input: "  ", ok: false},
		{name: "invalid string", input: "invalid", ok: false},
		{name: "unsupported", input: struct{}{}, ok: false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, ok := payrollDecimalFromInterface(tt.input)
			if ok != tt.ok {
				t.Fatalf("expected ok=%v, got %v", tt.ok, ok)
			}
			if ok && math.Abs(got.Float64()-tt.want) > 0.000001 {
				t.Fatalf("expected %.6f, got %.6f", tt.want, got.Float64())
			}
		})
	}
}

func TestPayrollDecimalFallbackAndRoundingBranches(t *testing.T) {
	if got := payrollDecimalFromFloat(math.NaN()).Float64(); got != 0 {
		t.Fatalf("expected invalid float to become zero, got %.2f", got)
	}

	if got := (payrollDecimal{}).Rounded(2).Float64(); got != 0 {
		t.Fatalf("expected nil decimal rounding to become zero, got %.2f", got)
	}
	if got := (payrollDecimal{}).Float64(); got != 0 {
		t.Fatalf("expected nil decimal float conversion to become zero, got %.2f", got)
	}

	tests := []struct {
		name  string
		input string
		want  float64
	}{
		{name: "exact", input: "1.25", want: 1.25},
		{name: "below half", input: "1.2345674", want: 1.234567},
		{name: "positive half up", input: "1.2345675", want: 1.234568},
		{name: "negative half away from zero", input: "-1.2345675", want: -1.234568},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			value, ok := payrollDecimalFromString(tt.input)
			if !ok {
				t.Fatalf("expected %q to parse", tt.input)
			}
			if got := value.Rounded(payrollMoneyScale).Float64(); math.Abs(got-tt.want) > 0.0000001 {
				t.Fatalf("expected %.6f, got %.6f", tt.want, got)
			}
		})
	}

	if _, ok := normalizePayrollMoney(struct{}{}); ok {
		t.Fatal("expected unsupported money input to be rejected")
	}
	if got, ok := normalizePayrollMoney("12.3456789"); !ok || math.Abs(got-12.345679) > 0.0000001 {
		t.Fatalf("expected normalized rounded money, got %.6f, ok=%v", got, ok)
	}
}

func TestOperatorMapCoversEverySupportedAndFallbackOperator(t *testing.T) {
	tests := map[string]string{
		"=":        "==",
		"==":       "==",
		"!=":       "!=",
		">":        ">",
		">=":       ">=",
		"<":        "<",
		"<=":       "<=",
		"IN":       "in",
		"NOT_IN":   "not in",
		"CONTAINS": "contains",
		"UNKNOWN":  "UNKNOWN",
	}

	for input, want := range tests {
		if got := operatorMap(input); got != want {
			t.Errorf("operatorMap(%q): expected %q, got %q", input, want, got)
		}
	}
}

func TestEmitterCoversInvalidSetAddReplaceAndAppendPaths(t *testing.T) {
	emitter := &Emitter{}
	emitter.AddComponent("INVALID", struct{}{}, 1)
	if len(emitter.Components) != 0 {
		t.Fatal("invalid ADD amount must not append a component")
	}

	emitter.SetComponent("INVALID", struct{}{}, 1)
	if len(emitter.Components) != 0 {
		t.Fatal("invalid SET amount must not append a component")
	}

	emitter.Components = []Component{
		{Code: "OTHER", Amount: 10, RuleIx: 1},
		{Code: "TARGET", Amount: 20, RuleIx: 2},
	}
	emitter.SetComponent("TARGET", "30.5", 3)
	if len(emitter.Components) != 2 || emitter.Components[1].Amount != 30.5 || emitter.Components[1].RuleIx != 3 {
		t.Fatalf("expected second component to be replaced, got %#v", emitter.Components)
	}

	emitter.SetComponent("NEW", 40, 4)
	if len(emitter.Components) != 3 || emitter.Components[2].Code != "NEW" {
		t.Fatalf("expected missing SET target to be appended, got %#v", emitter.Components)
	}

	emitter.ApplyComponent(" set ", "NEW", 50, 5)
	if emitter.Components[2].Amount != 50 {
		t.Fatalf("expected SET alias to replace NEW, got %#v", emitter.Components[2])
	}
	emitter.ApplyComponent("ADD_COMPONENT", "BONUS", 60, 6)
	if len(emitter.Components) != 4 || emitter.Components[3].Code != "BONUS" {
		t.Fatalf("expected default action to add BONUS, got %#v", emitter.Components)
	}
}

func TestCalculatorCoversBasicSalaryAliasesBlankUnknownAndCaseInsensitiveTypes(t *testing.T) {
	components := []Component{
		{Code: "BASIC_SALARY", Amount: 999999},
		{Code: "gaji_pokok", Amount: 999999},
		{Code: " BONUS ", Amount: 100},
		{Code: "DEDUCTION", Amount: 25},
		{Code: "UNKNOWN", Amount: 500},
		{Code: "", Amount: 700},
	}
	types := map[string]string{
		" basic_salary ": "earning",
		"GAJI_POKOK":     "EARNING",
		"bonus":          " EARNING ",
		"deduction":      "deduction",
	}

	summary := calculateSummary(Employee{BasicSalary: 1000}, components, types)
	if summary.BasicSalary != 1000 || summary.GrossSalary != 1100 || summary.TotalDeductions != 25 || summary.NetSalary != 1075 {
		t.Fatalf("unexpected summary %#v", summary)
	}

	if got := componentTypeForCode(types, ""); got != "" {
		t.Fatalf("expected blank component code to have no type, got %q", got)
	}
	if got := componentTypeForCode(types, "missing"); got != "" {
		t.Fatalf("expected unknown component code to have no type, got %q", got)
	}
	if !isBasicSalaryComponent("BASIC_SALARY") || !isBasicSalaryComponent(" gaji_pokok ") || isBasicSalaryComponent("BONUS") {
		t.Fatal("unexpected basic salary component classification")
	}
}
