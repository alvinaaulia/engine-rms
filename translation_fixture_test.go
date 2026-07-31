package main

import (
	"context"
	"encoding/json"
	"errors"
	"os"
	"testing"
)

type translationFixture struct {
	ID              string          `json:"id"`
	Purpose         string          `json:"purpose"`
	CanonicalTPRIR  *TPRRuleSet     `json:"canonical_tpr_ir"`
	GeneratedGRL    string          `json:"generated_grl,omitempty"`
	ExecutionResult ExecuteResponse `json:"execution_result,omitempty"`
	ErrorCode       string          `json:"error_code,omitempty"`
	Expected        string          `json:"expected"`
}

func fixtureRule(code, formula, priority string, conditions interface{}, action string) Rule {
	return Rule{
		Conditions: conditions,
		Action:     Action{Type: action, Code: code, Formula: formula},
		Meta:       RuleMetadata{Priority: priority},
	}
}

func fixtureErrorCode(err error) string {
	var validation *ValidationError
	if errors.As(err, &validation) {
		return validation.ErrorCode
	}
	if err != nil {
		return "EXECUTION_ERROR"
	}
	return ""
}

func TestTranslationValidationFixtures(t *testing.T) {
	facts := semanticFacts()
	type definition struct {
		id       string
		purpose  string
		rules    []Rule
		policy   string
		mutate   func(*TPRRuleSet)
		expected string
	}
	definitions := []definition{
		{
			id: "numeric-comparison", purpose: "numeric GTE, formula precedence, and HALF_UP rounding",
			rules:    []Rule{fixtureRule("NUMERIC", "(rates.bonus_rate + 10) * 1.2345675", "NORMAL", []interface{}{map[string]interface{}{"field": "employee.performance_score", "operator": ">=", "value": 90}}, "ADD_COMPONENT")},
			expected: "SUCCESS",
		},
		{
			id: "string-comparison", purpose: "strict string EQ literal",
			rules:    []Rule{fixtureRule("STRING", "10", "NORMAL", []interface{}{map[string]interface{}{"field": "employee.status", "operator": "==", "value": "aktif"}}, "ADD_COMPONENT")},
			expected: "SUCCESS",
		},
		{
			id: "boolean-comparison", purpose: "strict boolean EQ literal",
			rules:    []Rule{fixtureRule("BOOLEAN", "20", "NORMAL", []interface{}{map[string]interface{}{"field": "employee.annual_bonus_eligible", "operator": "==", "value": true}}, "ADD_COMPONENT")},
			expected: "SUCCESS",
		},
		{
			id: "date-comparison", purpose: "date BEFORE mapping",
			rules:    []Rule{fixtureRule("DATE", "30", "NORMAL", []interface{}{map[string]interface{}{"field": "employee.join_date", "operator": "<", "value": "2021-01-01"}}, "ADD_COMPONENT")},
			expected: "SUCCESS",
		},
		{
			id: "membership", purpose: "string IN expands to safe comparisons",
			rules:    []Rule{fixtureRule("MEMBERSHIP", "40", "NORMAL", []interface{}{map[string]interface{}{"field": "employee.status", "operator": "IN", "value": []interface{}{"aktif", "tetap"}}}, "ADD_COMPONENT")},
			expected: "SUCCESS",
		},
		{
			id: "nested-condition", purpose: "nested OR containing an AND group",
			rules: []Rule{fixtureRule("NESTED", "50", "NORMAL", map[string]interface{}{"type": "OR", "rules": []interface{}{
				map[string]interface{}{"field": "employee.status", "operator": "==", "value": "nonaktif"},
				map[string]interface{}{"type": "AND", "rules": []interface{}{
					map[string]interface{}{"field": "employee.has_npwp", "operator": "==", "value": true},
					map[string]interface{}{"field": "employee.years_of_service", "operator": ">=", "value": 5},
				}},
			}}, "ADD_COMPONENT")},
			expected: "SUCCESS",
		},
		{
			id: "add-collect-sum", purpose: "two ADD candidates aggregate with multi-rule provenance",
			rules: []Rule{
				fixtureRule("AGGREGATE", "10", "HIGH", []interface{}{map[string]interface{}{"field": "employee.status", "operator": "==", "value": "aktif"}}, "ADD_COMPONENT"),
				fixtureRule("AGGREGATE", "20", "LOW", []interface{}{map[string]interface{}{"field": "employee.has_npwp", "operator": "==", "value": true}}, "ADD_COMPONENT"),
			},
			policy: "COLLECT_SUM", expected: "SUCCESS",
		},
		{
			id: "set-priority", purpose: "SET selects highest salience and preserves source rule",
			rules: []Rule{
				fixtureRule("PRIORITIZED", "100", "HIGH", []interface{}{map[string]interface{}{"field": "employee.status", "operator": "==", "value": "aktif"}}, "SET_COMPONENT"),
				fixtureRule("PRIORITIZED", "10", "LOW", []interface{}{map[string]interface{}{"field": "employee.has_npwp", "operator": "==", "value": true}}, "SET_COMPONENT"),
			},
			policy: "PRIORITY", expected: "SUCCESS",
		},
		{
			id: "first", purpose: "FIRST uses priority descending then stable rule ID",
			rules: []Rule{
				fixtureRule("FIRST_VALUE", "70", "HIGH", []interface{}{map[string]interface{}{"field": "employee.status", "operator": "==", "value": "aktif"}}, "SET_COMPONENT"),
				fixtureRule("FIRST_VALUE", "80", "LOW", []interface{}{map[string]interface{}{"field": "employee.has_npwp", "operator": "==", "value": true}}, "SET_COMPONENT"),
			},
			policy: "FIRST", expected: "SUCCESS",
		},
		{
			id: "unique-conflict", purpose: "UNIQUE rejects two matching candidates",
			rules: []Rule{
				fixtureRule("UNIQUE_VALUE", "1", "HIGH", []interface{}{map[string]interface{}{"field": "employee.status", "operator": "==", "value": "aktif"}}, "SET_COMPONENT"),
				fixtureRule("UNIQUE_VALUE", "2", "LOW", []interface{}{map[string]interface{}{"field": "employee.has_npwp", "operator": "==", "value": true}}, "SET_COMPONENT"),
			},
			policy: "UNIQUE", expected: "POTENTIAL_UNIQUE_CONFLICT",
		},
		{
			id: "invalid-formula", purpose: "formula parser rejects an incomplete expression",
			rules:    []Rule{fixtureRule("INVALID_FORMULA", "10", "NORMAL", []interface{}{map[string]interface{}{"field": "employee.status", "operator": "==", "value": "aktif"}}, "ADD_COMPONENT")},
			mutate:   func(rs *TPRRuleSet) { rs.Rules[0].Actions[0].Formula.Expression = "rates.bonus_rate +" },
			expected: "INVALID_FORMULA",
		},
		{
			id: "unknown-field", purpose: "canonical validator rejects a field absent from the catalog",
			rules:    []Rule{fixtureRule("UNKNOWN_FIELD", "10", "NORMAL", []interface{}{map[string]interface{}{"field": "employee.status", "operator": "==", "value": "aktif"}}, "ADD_COMPONENT")},
			mutate:   func(rs *TPRRuleSet) { rs.Rules[0].Condition.Children[0].Field.Name = "password" },
			expected: "UNKNOWN_FIELD",
		},
	}

	fixtures := make([]translationFixture, 0, len(definitions))
	for _, item := range definitions {
		t.Run(item.id, func(t *testing.T) {
			rs, err := AdaptLegacyPayload(item.rules, facts)
			if err != nil {
				t.Fatalf("adapter failed: %v", err)
			}
			if item.policy != "" {
				for code := range rs.ComponentPolicies {
					rs.ComponentPolicies[code] = item.policy
				}
			}
			if item.mutate != nil {
				item.mutate(rs)
			}
			grl, grlErr := buildTPRGRL(rs)
			result, executeErr := ExecuteTPRRuleSet(context.Background(), rs, facts, map[string]string{
				"NUMERIC": "EARNING", "STRING": "EARNING", "BOOLEAN": "EARNING", "DATE": "EARNING",
				"MEMBERSHIP": "EARNING", "NESTED": "EARNING", "AGGREGATE": "EARNING",
				"PRIORITIZED": "EARNING", "FIRST_VALUE": "EARNING", "UNIQUE_VALUE": "EARNING",
				"INVALID_FORMULA": "EARNING", "UNKNOWN_FIELD": "EARNING",
			})
			errorCode := fixtureErrorCode(executeErr)
			if errorCode == "" {
				errorCode = fixtureErrorCode(grlErr)
			}
			if item.expected == "SUCCESS" && (executeErr != nil || grlErr != nil) {
				t.Fatalf("expected success, got GRL=%v execution=%v", grlErr, executeErr)
			}
			if item.expected != "SUCCESS" && errorCode != item.expected {
				t.Fatalf("expected %s, got %s (%v / %v)", item.expected, errorCode, grlErr, executeErr)
			}
			fixtures = append(fixtures, translationFixture{
				ID: item.id, Purpose: item.purpose, CanonicalTPRIR: rs, GeneratedGRL: grl,
				ExecutionResult: result, ErrorCode: errorCode, Expected: item.expected,
			})
		})
	}

	if output := os.Getenv("TPR_TRANSLATION_FIXTURE_OUTPUT"); output != "" {
		encoded, err := json.MarshalIndent(map[string]interface{}{
			"schema_version": "1.0", "fixture_count": len(fixtures), "fixtures": fixtures,
		}, "", "  ")
		if err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(output, append(encoded, '\n'), 0o644); err != nil {
			t.Fatal(err)
		}
	}
}
