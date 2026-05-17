package main

import (
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
