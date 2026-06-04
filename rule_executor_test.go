package main

import (
	"math"
	"strings"
	"testing"
)

func TestBuildConditionExpressionSupportsNestedGroups(t *testing.T) {
	node := map[string]interface{}{
		"type": "AND",
		"rules": []interface{}{
			map[string]interface{}{
				"field":    "employee.status",
				"operator": "==",
				"value":    "active",
			},
			map[string]interface{}{
				"type": "OR",
				"rules": []interface{}{
					map[string]interface{}{
						"field":    "attendance.overtime_minutes",
						"operator": ">",
						"value":    0,
					},
					map[string]interface{}{
						"field":    "attendance.late_minutes",
						"operator": ">",
						"value":    0,
					},
				},
			},
		},
	}

	expression, err := buildConditionExpression(node)
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if !strings.Contains(expression, "employee.Status == \"active\"") {
		t.Fatalf("expected employee status predicate in expression, got %s", expression)
	}

	if !strings.Contains(expression, "attendance.OvertimeMinutes > 0") {
		t.Fatalf("expected overtime predicate in expression, got %s", expression)
	}

	if !strings.Contains(expression, "attendance.LateMinutes > 0") {
		t.Fatalf("expected late predicate in expression, got %s", expression)
	}

	if !strings.Contains(expression, "||") {
		t.Fatalf("expected OR operator in expression, got %s", expression)
	}
}

func TestBuildMultiGRLUsesEveryCondition(t *testing.T) {
	rules := []Rule{
		{
			Conditions: []interface{}{
				map[string]interface{}{
					"field":    "employee.status",
					"operator": "==",
					"value":    "active",
				},
				map[string]interface{}{
					"field":    "attendance.overtime_minutes",
					"operator": ">",
					"value":    0,
				},
			},
			Action: Action{
				Type:    "ADD_COMPONENT",
				Code:    "OVERTIME_PAY",
				Formula: "attendance.overtime_minutes * rates.overtime_per_minute",
			},
		},
	}

	grl, err := buildMultiGRL(rules)
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if !strings.Contains(grl, "employee.Status == \"active\"") {
		t.Fatalf("expected employee status condition in generated GRL, got %s", grl)
	}

	if !strings.Contains(grl, "attendance.OvertimeMinutes > 0") {
		t.Fatalf("expected overtime condition in generated GRL, got %s", grl)
	}

	if !strings.Contains(grl, "&&") {
		t.Fatalf("expected AND operator in generated GRL, got %s", grl)
	}
}

func TestBuildMultiGRLMapsPerformanceScoreAlias(t *testing.T) {
	rules := []Rule{
		{
			Conditions: []interface{}{
				map[string]interface{}{
					"field":    "employee.performance_score",
					"operator": ">=",
					"value":    80,
				},
			},
			Action: Action{
				Type:    "SET_COMPONENT",
				Code:    "BONUS",
				Formula: "employee.performance_score * 1000",
			},
		},
	}

	grl, err := buildMultiGRL(rules)
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if !strings.Contains(grl, "employee.PerformanceScore >= 80") {
		t.Fatalf("expected performance_score condition alias in generated GRL, got %s", grl)
	}

	if !strings.Contains(grl, "employee.PerformanceScore * 1000") {
		t.Fatalf("expected performance_score formula alias in generated GRL, got %s", grl)
	}
}

func TestExecuteAllRulesSupportsDivisionFormula(t *testing.T) {
	rules := []Rule{
		{
			Conditions: []interface{}{
				map[string]interface{}{
					"field":    "employee.status",
					"operator": "==",
					"value":    "active",
				},
			},
			Action: Action{
				Type:    "ADD_COMPONENT",
				Code:    "DIV_CASE",
				Formula: "components.BASIC_SALARY / 22",
			},
		},
	}

	resp, err := executeAllRules(rules, baseFactsForExecutionTests())
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if len(resp.Components) != 1 {
		t.Fatalf("expected one component, got %d", len(resp.Components))
	}

	expected := 1000000.0 / 22.0
	if math.Abs(resp.Components[0].Amount-expected) > 0.0001 {
		t.Fatalf("expected division result %.6f, got %.6f", expected, resp.Components[0].Amount)
	}
}

func TestExecuteAllRulesSupportsDecimalFormula(t *testing.T) {
	rules := []Rule{
		{
			Conditions: []interface{}{
				map[string]interface{}{
					"field":    "employee.status",
					"operator": "==",
					"value":    "active",
				},
			},
			Action: Action{
				Type:    "ADD_COMPONENT",
				Code:    "DEC_CASE",
				Formula: "attendance.overtime_minutes * 1.5",
			},
		},
	}

	resp, err := executeAllRules(rules, baseFactsForExecutionTests())
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if len(resp.Components) != 1 {
		t.Fatalf("expected one component, got %d", len(resp.Components))
	}

	expected := 120.0 * 1.5
	if math.Abs(resp.Components[0].Amount-expected) > 0.0001 {
		t.Fatalf("expected decimal result %.6f, got %.6f", expected, resp.Components[0].Amount)
	}
}

func TestExecuteAllRulesSupportsDynamicRateFormula(t *testing.T) {
	rules := []Rule{
		{
			Conditions: map[string]interface{}{
				"type": "AND",
				"rules": []interface{}{
					map[string]interface{}{
						"field":    "employee.status",
						"operator": "==",
						"value":    "active",
					},
					map[string]interface{}{
						"field":    "attendance.overtime_hours",
						"operator": ">=",
						"value":    2,
					},
				},
			},
			Action: Action{
				Type:    "SET_COMPONENT",
				Code:    "CMP_LEMBUR_FREELANCE",
				Formula: "attendance.overtime_hours * rates.overtime_pay_for_freelancer",
			},
		},
	}
	facts := baseFactsForExecutionTests()
	facts["rates"].(map[string]interface{})["overtime_pay_for_freelancer"] = 5000

	resp, err := executeAllRules(rules, facts)
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if len(resp.Components) != 1 {
		t.Fatalf("expected one component, got %d", len(resp.Components))
	}

	expected := 2.0 * 5000.0
	if math.Abs(resp.Components[0].Amount-expected) > 0.0001 {
		t.Fatalf("expected dynamic rate amount %.6f, got %.6f", expected, resp.Components[0].Amount)
	}
}

func TestBuildConditionExpressionSupportsDynamicRateField(t *testing.T) {
	node := map[string]interface{}{
		"field":    "rates.overtime_pay_for_freelancer",
		"operator": ">",
		"value":    0,
	}

	expression, err := buildConditionExpression(node)
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if !strings.Contains(expression, `rates.Value("overtime_pay_for_freelancer") > 0`) {
		t.Fatalf("expected dynamic rate condition in expression, got %s", expression)
	}
}

func TestExecuteAllRulesSupportsInAndNotInOperators(t *testing.T) {
	rules := []Rule{
		{
			Conditions: map[string]interface{}{
				"type": "AND",
				"rules": []interface{}{
					map[string]interface{}{
						"field":    "employee.status",
						"operator": "IN",
						"value":    []interface{}{"active", "tetap"},
					},
					map[string]interface{}{
						"field":    "employee.grade",
						"operator": "NOT_IN",
						"value":    []interface{}{"B9", "C9"},
					},
				},
			},
			Action: Action{
				Type:    "ADD_COMPONENT",
				Code:    "MEMBERSHIP_BONUS",
				Formula: "100",
			},
		},
	}

	resp, err := executeAllRules(rules, baseFactsForExecutionTests())
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if len(resp.Components) != 1 {
		t.Fatalf("expected one component, got %d", len(resp.Components))
	}
	if resp.Components[0].Code != "MEMBERSHIP_BONUS" {
		t.Fatalf("expected MEMBERSHIP_BONUS, got %s", resp.Components[0].Code)
	}
}

func TestExecuteAllRulesSupportsContainsOperator(t *testing.T) {
	rules := []Rule{
		{
			Conditions: []interface{}{
				map[string]interface{}{
					"field":    "employee.contract_type",
					"operator": "CONTAINS",
					"value":    "perman",
				},
			},
			Action: Action{
				Type:    "ADD_COMPONENT",
				Code:    "CONTAINS_BONUS",
				Formula: "50",
			},
		},
	}

	resp, err := executeAllRules(rules, baseFactsForExecutionTests())
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if len(resp.Components) != 1 {
		t.Fatalf("expected one component, got %d", len(resp.Components))
	}
}

func TestExecuteAllRulesSupportsAttendanceWorkHours(t *testing.T) {
	rules := []Rule{
		{
			Conditions: []interface{}{
				map[string]interface{}{
					"field":    "attendance.work_hours",
					"operator": ">=",
					"value":    8,
				},
			},
			Action: Action{
				Type:    "ADD_COMPONENT",
				Code:    "WORK_HOURS_ALLOWANCE",
				Formula: "attendance.work_hours * 1000",
			},
		},
	}
	facts := baseFactsForExecutionTests()
	facts["attendance"].(map[string]interface{})["work_hours"] = 8

	resp, err := executeAllRules(rules, facts)
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if len(resp.Components) != 1 {
		t.Fatalf("expected one component, got %d", len(resp.Components))
	}
	if math.Abs(resp.Components[0].Amount-8000) > 0.0001 {
		t.Fatalf("expected work hours amount 8000, got %.6f", resp.Components[0].Amount)
	}
}

func TestExecuteAllRulesSupportsDynamicComponentFormula(t *testing.T) {
	rules := []Rule{
		{
			Conditions: []interface{}{
				map[string]interface{}{
					"field":    "employee.status",
					"operator": "==",
					"value":    "active",
				},
			},
			Action: Action{
				Type:    "ADD_COMPONENT",
				Code:    "CUSTOM_COMPONENT_DOUBLE",
				Formula: "components.CMP_CUSTOM * 2",
			},
		},
	}
	facts := baseFactsForExecutionTests()
	facts["components"].(map[string]interface{})["CMP_CUSTOM"] = 12500

	resp, err := executeAllRules(rules, facts)
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if len(resp.Components) != 1 {
		t.Fatalf("expected one component, got %d", len(resp.Components))
	}
	if math.Abs(resp.Components[0].Amount-25000) > 0.0001 {
		t.Fatalf("expected custom component amount 25000, got %.6f", resp.Components[0].Amount)
	}
}

func TestExecuteAllRulesSupportsEmployeeTaxContext(t *testing.T) {
	rules := []Rule{
		{
			Conditions: map[string]interface{}{
				"type": "AND",
				"rules": []interface{}{
					map[string]interface{}{
						"field":    "employee.has_npwp",
						"operator": "==",
						"value":    true,
					},
					map[string]interface{}{
						"field":    "employee.ptkp_status",
						"operator": "==",
						"value":    "K0",
					},
				},
			},
			Action: Action{
				Type:    "ADD_COMPONENT",
				Code:    "TAX_CONTEXT_MATCH",
				Formula: "100",
			},
		},
	}
	facts := baseFactsForExecutionTests()
	facts["employee"].(map[string]interface{})["has_npwp"] = true
	facts["employee"].(map[string]interface{})["ptkp_status"] = "K0"

	resp, err := executeAllRules(rules, facts)
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if len(resp.Components) != 1 {
		t.Fatalf("expected one component, got %d", len(resp.Components))
	}
}

func TestEmitterSetComponentReplacesExistingComponent(t *testing.T) {
	emitter := &Emitter{}

	emitter.ApplyComponent("ADD_COMPONENT", "BONUS", 100, 0)
	emitter.ApplyComponent("SET_COMPONENT", "BONUS", 200, 1)

	if len(emitter.Components) != 1 {
		t.Fatalf("expected one component after SET replacement, got %d", len(emitter.Components))
	}
	if emitter.Components[0].Amount != 200 {
		t.Fatalf("expected replaced amount 200, got %.2f", emitter.Components[0].Amount)
	}
	if emitter.Components[0].RuleIx != 1 {
		t.Fatalf("expected source rule 1, got %d", emitter.Components[0].RuleIx)
	}
}

func TestCalculateSummaryClassifiesCustomComponents(t *testing.T) {
	summary := calculateSummary(Employee{BasicSalary: 1000000}, []Component{
		{Code: "CMP_LEMBUR_FREELANCE", Amount: 20000},
		{Code: "CMP_CUTI_TANPA_DIBAYAR", Amount: 50000},
	})

	if summary.GrossSalary != 1020000 {
		t.Fatalf("expected gross 1020000, got %.2f", summary.GrossSalary)
	}
	if summary.TotalDeductions != 50000 {
		t.Fatalf("expected deductions 50000, got %.2f", summary.TotalDeductions)
	}
	if summary.NetSalary != 970000 {
		t.Fatalf("expected net 970000, got %.2f", summary.NetSalary)
	}
}

func baseFactsForExecutionTests() map[string]interface{} {
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
			"tax_flat_amount":           0,
		},
		"components": map[string]interface{}{
			"BASIC_SALARY": 1000000,
			"OVERTIME_PAY": 0,
			"TH_R":         0,
			"THR":          0,
		},
	}
}
