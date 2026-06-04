package main

import (
	"encoding/json"
	"math"
	"strings"
	"testing"
)

func TestWB01OperatorMapNormalizesEquals(t *testing.T) {
	if got := operatorMap("="); got != "==" {
		t.Fatalf("expected ==, got %q", got)
	}
}

func TestWB02GruleLiteralEscapesStringWithJSONMarshal(t *testing.T) {
	got, err := gruleLiteral("PERMANENT")
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if got != `"PERMANENT"` {
		t.Fatalf("expected quoted GRL string literal, got %s", got)
	}
}

func TestWB03GruleLiteralAcceptsFloat64FromJSONDecode(t *testing.T) {
	var decoded interface{}
	if err := json.Unmarshal([]byte(`5`), &decoded); err != nil {
		t.Fatalf("expected JSON decode to succeed, got %v", err)
	}

	got, err := gruleLiteral(decoded)
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if got != "5" {
		t.Fatalf("expected 5, got %s", got)
	}
}

func TestWB04BuildMultiGRLRejectsEmptyFormula(t *testing.T) {
	rules := []Rule{{
		Conditions: []interface{}{map[string]interface{}{
			"field":    "employee.status",
			"operator": "=",
			"value":    "active",
		}},
		Action: Action{
			Type:    "ADD_COMPONENT",
			Code:    "OVERTIME_PAY",
			Formula: "",
		},
	}}

	_, err := buildMultiGRL(rules)
	if err == nil {
		t.Fatal("expected error for empty formula")
	}
	if !strings.Contains(err.Error(), "rule 0 action.formula is empty") {
		t.Fatalf("unexpected error: %v", err)
	}
}

func TestWB05BuildMultiGRLGeneratesThreeRulesWithRetract(t *testing.T) {
	rules := []Rule{
		wbRule("OVERTIME_PAY", "attendance.overtime_minutes * rates.overtime_per_minute"),
		wbRule("LATE_DEDUCTION", "attendance.late_minutes * rates.late_deduction_per_minute"),
		wbRule("TAX_DEDUCTION", "rates.tax_flat_amount"),
	}

	grl, err := buildMultiGRL(rules)
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	for _, fragment := range []string{
		"rule Rule_0",
		"rule Rule_1",
		"rule Rule_2",
		`Retract("Rule_0")`,
		`Retract("Rule_1")`,
		`Retract("Rule_2")`,
	} {
		if !strings.Contains(grl, fragment) {
			t.Fatalf("expected generated GRL to contain %q, got %s", fragment, grl)
		}
	}
}

func TestWB06ExecuteAllRulesFailsWhenAttendanceFactsMissing(t *testing.T) {
	facts := wbFacts()
	delete(facts, "attendance")

	_, err := executeAllRules([]Rule{wbRule("OVERTIME_PAY", "100")}, facts)
	if err == nil {
		t.Fatal("expected missing attendance error")
	}
	if !strings.Contains(err.Error(), "facts.attendance not found") {
		t.Fatalf("unexpected error: %v", err)
	}
}

func TestWB07ExecuteAllRulesHydratesFactsAndDerivesFallbackRates(t *testing.T) {
	facts := wbFacts()
	facts["attendance"].(map[string]interface{})["overtime_hours"] = 0
	facts["attendance"].(map[string]interface{})["overtime_minutes"] = 120
	facts["rates"].(map[string]interface{})["overtime_per_hour"] = 0
	facts["rates"].(map[string]interface{})["overtime_per_minute"] = 2000

	rules := []Rule{{
		Conditions: []interface{}{map[string]interface{}{
			"field":    "attendance.overtime_hours",
			"operator": ">",
			"value":    0,
		}},
		Action: Action{
			Type:    "ADD_COMPONENT",
			Code:    "OVERTIME_PAY",
			Formula: "attendance.overtime_hours * rates.overtime_per_hour",
		},
	}}

	resp, err := executeAllRules(rules, facts)
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}
	if len(resp.Components) != 1 {
		t.Fatalf("expected one derived overtime component, got %d", len(resp.Components))
	}
	if diff := math.Abs(resp.Components[0].Amount - 240000); diff > 0.0001 {
		t.Fatalf("expected derived amount 240000, got %.4f", resp.Components[0].Amount)
	}
}

func TestWB08GRLTrueCaseAddsComponent(t *testing.T) {
	resp, err := executeAllRules([]Rule{wbRule("OVERTIME_PAY", "attendance.overtime_minutes * rates.overtime_per_minute")}, wbFacts())
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if len(resp.Components) != 1 {
		t.Fatalf("expected one component, got %d", len(resp.Components))
	}
	if resp.Components[0].Code != "OVERTIME_PAY" {
		t.Fatalf("expected OVERTIME_PAY, got %s", resp.Components[0].Code)
	}
	if resp.Components[0].RuleIx != 0 {
		t.Fatalf("expected source rule 0, got %d", resp.Components[0].RuleIx)
	}
	if diff := math.Abs(resp.Components[0].Amount - 240000); diff > 0.0001 {
		t.Fatalf("expected amount 240000, got %.4f", resp.Components[0].Amount)
	}
}

func TestWB09GRLFalseCaseDoesNotAddComponent(t *testing.T) {
	facts := wbFacts()
	facts["attendance"].(map[string]interface{})["overtime_minutes"] = 0
	facts["attendance"].(map[string]interface{})["overtime_hours"] = 0

	resp, err := executeAllRules([]Rule{wbRule("OVERTIME_PAY", "attendance.overtime_minutes * rates.overtime_per_minute")}, facts)
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if len(resp.Components) != 0 {
		t.Fatalf("expected no components, got %d", len(resp.Components))
	}
}

func TestWB10BuildMultiGRLIncludesRetractForAlwaysTrueRuleLoopSafety(t *testing.T) {
	rules := []Rule{{
		Conditions: []interface{}{map[string]interface{}{
			"field":    "employee.status",
			"operator": "==",
			"value":    "active",
		}},
		Action: Action{
			Type:    "ADD_COMPONENT",
			Code:    "BONUS",
			Formula: "100",
		},
	}}

	grl, err := buildMultiGRL(rules)
	if err != nil {
		t.Fatalf("expected no GRL build error, got %v", err)
	}
	if !strings.Contains(grl, `Retract("Rule_0")`) {
		t.Fatalf("expected Retract loop-safety instruction, got %s", grl)
	}

	resp, err := executeAllRules(rules, wbFacts())
	if err != nil {
		t.Fatalf("expected no execution error, got %v", err)
	}
	if len(resp.Components) != 1 {
		t.Fatalf("expected execution to finish with one component, got %d", len(resp.Components))
	}
}

func TestWB11ExecuteAllRulesReturnsTypeMismatchErrorForDecimalInt64Fact(t *testing.T) {
	facts := wbFacts()
	facts["employee"].(map[string]interface{})["years_of_service"] = 1.5

	_, err := executeAllRules([]Rule{wbRule("BONUS", "100")}, facts)
	if err == nil {
		t.Fatal("expected numeric type mismatch error")
	}
	if !strings.Contains(strings.ToLower(err.Error()), "cannot unmarshal number 1.5") {
		t.Fatalf("unexpected error: %v", err)
	}
}

func TestWB12CalculateSummaryCombinesEarningsAndDeductions(t *testing.T) {
	summary := calculateSummary(Employee{BasicSalary: 1000000}, []Component{
		{Code: "OVERTIME_PAY", Amount: 200000},
		{Code: "LATE_DEDUCTION", Amount: 10000},
		{Code: "TAX_DEDUCTION", Amount: 50000},
	})

	if summary.GrossSalary != 1200000 {
		t.Fatalf("expected gross 1200000, got %.2f", summary.GrossSalary)
	}
	if summary.TotalDeductions != 60000 {
		t.Fatalf("expected deductions 60000, got %.2f", summary.TotalDeductions)
	}
	if summary.NetSalary != 1140000 {
		t.Fatalf("expected net 1140000, got %.2f", summary.NetSalary)
	}
}

func wbRule(code string, formula string) Rule {
	return Rule{
		Conditions: []interface{}{map[string]interface{}{
			"field":    "attendance.overtime_minutes",
			"operator": ">",
			"value":    0,
		}},
		Action: Action{
			Type:    "ADD_COMPONENT",
			Code:    code,
			Formula: formula,
		},
	}
}

func wbFacts() map[string]interface{} {
	return map[string]interface{}{
		"employee": map[string]interface{}{
			"status":            "active",
			"contract_type":     "permanent",
			"grade":             "A1",
			"join_date":         "2024-01-01",
			"years_of_service":  2,
			"performance_score": 90,
			"basic_salary":      1000000,
		},
		"attendance": map[string]interface{}{
			"days_present":      20,
			"days_absent":       2,
			"late_minutes":      0,
			"unpaid_leave_days": 0,
			"overtime_hours":    2,
			"overtime_minutes":  120,
		},
		"rates": map[string]interface{}{
			"late_deduction_per_minute": 1000,
			"unpaid_leave_per_day":      100000,
			"overtime_per_hour":         120000,
			"overtime_per_minute":       2000,
			"tax_flat_amount":           50000,
		},
		"components": map[string]interface{}{
			"BASIC_SALARY": 1000000,
			"OVERTIME_PAY": 0,
			"TH_R":         0,
			"THR":          0,
		},
	}
}
