package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func TestRuleHelperContainsCoversTrueAndFalseOutcomes(t *testing.T) {
	helper := RuleHelper{}
	if !helper.Contains("Permanent Employee", "employee") {
		t.Fatal("expected case-insensitive substring match")
	}
	if helper.Contains("Permanent Employee", "contractor") {
		t.Fatal("expected non-matching substring to be false")
	}
}

func TestNormalizeFieldCoversAliasesDynamicPrefixesEmptyKeysAndFallback(t *testing.T) {
	tests := map[string]string{
		"employee.status":          "employee.Status",
		"rates.custom-rate":        `rates.Value("custom_rate")`,
		"rates.___":                "",
		"attendance.custom minute": `attendance.Value("custom_minute")`,
		"attendance.___":           "",
		"components.custom_bonus":  `components.Value("custom_bonus")`,
		"components.___":           "",
		"employee.custom_label":    `employee.Text("custom_label")`,
		"employee.___":             "",
		"unknown.raw":              "",
	}

	for input, want := range tests {
		if got := normalizeField(input); got != want {
			t.Errorf("normalizeField(%q): expected %q, got %q", input, want, got)
		}
	}
}

func TestConditionValueLiteralCoversBooleanCoercionFallbackAndRegularFields(t *testing.T) {
	tests := []struct {
		name  string
		field string
		value interface{}
		want  string
	}{
		{name: "boolean true alias", field: "employee.has_npwp", value: "yes", want: "true"},
		{name: "boolean invalid fallback", field: "employee.has_npwp", value: "maybe", want: `"maybe"`},
		{name: "regular numeric", field: "attendance.days_present", value: 20, want: "20"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := conditionValueLiteral(tt.field, tt.value)
			if err != nil {
				t.Fatalf("unexpected literal error: %v", err)
			}
			if got != tt.want {
				t.Fatalf("expected %q, got %q", tt.want, got)
			}
		})
	}
}

func TestNormalizeFormulaTokenAndFormulaCoverReservedDynamicAndBlankPaths(t *testing.T) {
	tokenTests := map[string]string{
		"broken":          "broken",
		"employee.":       "employee.",
		"employee.value":  "employee.value",
		"employee.text":   "employee.text",
		"employee.bool":   "employee.bool",
		"employee.custom": `employee.Value("custom")`,
	}
	for input, want := range tokenTests {
		if got := normalizeFormulaToken("employee", input); got != want {
			t.Errorf("normalizeFormulaToken(%q): expected %q, got %q", input, want, got)
		}
	}

	if got := normalizeFormula("   "); got != "" {
		t.Fatalf("expected blank formula to remain blank, got %q", got)
	}
	formula := normalizeFormula("employee.custom_score + attendance.custom_minutes + rates.custom_rate + components.custom_component")
	for _, want := range []string{
		`employee.Value("custom_score")`,
		`attendance.Value("custom_minutes")`,
		`rates.Value("custom_rate")`,
		`components.Value("custom_component")`,
	} {
		if !strings.Contains(formula, want) {
			t.Errorf("expected normalized formula to contain %q, got %q", want, formula)
		}
	}
}

func TestGruleLiteralCoversAllTypesAndMarshalFailures(t *testing.T) {
	tests := []struct {
		name  string
		value interface{}
		want  string
	}{
		{name: "nil", value: nil, want: "nil"},
		{name: "string", value: "active", want: `"active"`},
		{name: "bool true", value: true, want: "true"},
		{name: "bool false", value: false, want: "false"},
		{name: "json number", value: json.Number("1.5"), want: "1.5"},
		{name: "float64", value: float64(2.5), want: "2.5"},
		{name: "int", value: int(3), want: "3"},
		{name: "int64", value: int64(4), want: "4"},
		{name: "slice", value: []interface{}{1, "a"}, want: `[1,"a"]`},
		{name: "map", value: map[string]interface{}{"a": 1}, want: `{"a":1}`},
		{name: "default marshal", value: struct{ A int }{A: 5}, want: `{"A":5}`},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := gruleLiteral(tt.value)
			if err != nil {
				t.Fatalf("unexpected literal error: %v", err)
			}
			if got != tt.want {
				t.Fatalf("expected %q, got %q", tt.want, got)
			}
		})
	}

	if _, err := gruleLiteral(map[string]interface{}{"bad": func() {}}); err == nil {
		t.Fatal("expected map marshal failure")
	}
	if got, err := gruleLiteral(func() {}); err != nil || !strings.Contains(got, "0x") {
		t.Fatalf("expected default marshal fallback, got %q, err=%v", got, err)
	}
}

func TestLiteralValuesCoversSlicesScalarAndError(t *testing.T) {
	tests := []struct {
		name  string
		value interface{}
		want  []string
	}{
		{name: "interfaces", value: []interface{}{"A", 2}, want: []string{`"A"`, "2"}},
		{name: "strings", value: []string{"A", "B"}, want: []string{`"A"`, `"B"`}},
		{name: "float64s", value: []float64{1.5, 2.5}, want: []string{"1.5", "2.5"}},
		{name: "ints", value: []int{1, 2}, want: []string{"1", "2"}},
		{name: "scalar", value: "A", want: []string{`"A"`}},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := literalValues(tt.value)
			if err != nil {
				t.Fatalf("unexpected literalValues error: %v", err)
			}
			if strings.Join(got, ",") != strings.Join(tt.want, ",") {
				t.Fatalf("expected %#v, got %#v", tt.want, got)
			}
		})
	}

	if _, err := literalValues([]interface{}{map[string]interface{}{"bad": func() {}}}); err == nil {
		t.Fatal("expected nested literal marshal error")
	}
}

func TestBuildMembershipExpressionCoversEmptySingleMultipleAndErrorPaths(t *testing.T) {
	tests := []struct {
		name     string
		operator string
		value    interface{}
		want     string
	}{
		{name: "empty in", operator: "IN", value: []string{}, want: "false"},
		{name: "empty not in", operator: "NOT_IN", value: []string{}, want: "true"},
		{name: "single", operator: "IN", value: []string{"A"}, want: `employee.Grade == "A"`},
		{name: "multiple not in", operator: "NOT_IN", value: []string{"A", "B"}, want: `(employee.Grade != "A" && employee.Grade != "B")`},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := buildMembershipExpression("employee.Grade", tt.operator, tt.value)
			if err != nil {
				t.Fatalf("unexpected membership error: %v", err)
			}
			if got != tt.want {
				t.Fatalf("expected %q, got %q", tt.want, got)
			}
		})
	}

	if _, err := buildMembershipExpression("employee.Grade", "IN", []interface{}{map[string]interface{}{"bad": func() {}}}); err == nil {
		t.Fatal("expected membership literal error")
	}
}

func TestBuildConditionExpressionCoversEmptyInvalidLeafAndGroupPaths(t *testing.T) {
	leaf := map[string]interface{}{
		"field":    "employee.status",
		"operator": "==",
		"value":    "active",
	}

	tests := []struct {
		name    string
		node    interface{}
		want    string
		wantErr string
	}{
		{name: "nil", node: nil, want: ""},
		{name: "empty list", node: []interface{}{}, want: ""},
		{name: "single nonempty child", node: []interface{}{nil, leaf}, want: `employee.Status == "active"`},
		{name: "empty group", node: map[string]interface{}{"type": "AND", "rules": []interface{}{nil}}, want: ""},
		{name: "single child group", node: map[string]interface{}{"type": "AND", "rules": []interface{}{leaf}}, want: `employee.Status == "active"`},
		{name: "or group", node: map[string]interface{}{"type": "OR", "rules": []interface{}{leaf, map[string]interface{}{"field": "employee.grade", "operator": "==", "value": "A"}}}, want: `(employee.Status == "active" || employee.Grade == "A")`},
		{name: "rules not array", node: map[string]interface{}{"rules": "bad"}, wantErr: "rules must be an array"},
		{name: "missing field", node: map[string]interface{}{"operator": "=="}, wantErr: "field and operator"},
		{name: "missing operator", node: map[string]interface{}{"field": "employee.status"}, wantErr: "field and operator"},
		{name: "empty field", node: map[string]interface{}{"field": " ", "operator": "==", "value": "x"}, wantErr: "field is empty"},
		{name: "unsupported node", node: 123, wantErr: "unsupported condition node type"},
		{name: "unsupported child", node: []interface{}{123}, wantErr: "unsupported condition node type"},
		{name: "unsupported group child", node: map[string]interface{}{"type": "AND", "rules": []interface{}{123}}, wantErr: "unsupported condition node type"},
		{name: "contains", node: map[string]interface{}{"field": "employee.status", "operator": "CONTAINS", "value": "act"}, want: `helper.Contains(employee.Status, "act")`},
		{name: "boolean", node: map[string]interface{}{"field": "employee.has_npwp", "operator": "==", "value": "yes"}, want: "employee.HasNpwp == true"},
		{name: "membership", node: map[string]interface{}{"field": "employee.grade", "operator": "IN", "value": []string{"A"}}, want: `employee.Grade == "A"`},
		{name: "contains marshal error", node: map[string]interface{}{"field": "employee.status", "operator": "CONTAINS", "value": map[string]interface{}{"bad": func() {}}}, wantErr: "unsupported type"},
		{name: "regular literal marshal error", node: map[string]interface{}{"field": "employee.status", "operator": "==", "value": map[string]interface{}{"bad": func() {}}}, wantErr: "unsupported type"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := buildConditionExpression(tt.node)
			if tt.wantErr != "" {
				if err == nil || !strings.Contains(err.Error(), tt.wantErr) {
					t.Fatalf("expected error containing %q, got %v", tt.wantErr, err)
				}
				return
			}
			if err != nil {
				t.Fatalf("unexpected condition error: %v", err)
			}
			if got != tt.want {
				t.Fatalf("expected %q, got %q", tt.want, got)
			}
		})
	}
}

func TestBuildMultiGRLCoversSkippedAndInvalidConditions(t *testing.T) {
	grl, err := buildMultiGRL([]Rule{{Conditions: nil, Action: Action{Formula: "100"}}})
	if err != nil || grl != "" {
		t.Fatalf("expected empty condition rule to be skipped, got %q, err=%v", grl, err)
	}

	_, err = buildMultiGRL([]Rule{{Conditions: 123, Action: Action{Formula: "100"}}})
	if err == nil || !strings.Contains(err.Error(), "invalid conditions") {
		t.Fatalf("expected wrapped invalid condition error, got %v", err)
	}
}

func TestExecuteAllRulesCoversMissingAndUnmarshalErrorPaths(t *testing.T) {
	rules := []Rule{wbRule("BONUS", "100")}

	missingCases := []struct {
		name string
		key  string
	}{
		{name: "employee", key: "employee"},
		{name: "attendance", key: "attendance"},
		{name: "rates", key: "rates"},
	}
	for _, tt := range missingCases {
		t.Run("missing "+tt.name, func(t *testing.T) {
			facts := wbFacts()
			delete(facts, tt.key)
			if _, err := executeAllRules(rules, facts); err == nil || !strings.Contains(err.Error(), "facts."+tt.key+" not found") {
				t.Fatalf("expected missing %s error, got %v", tt.key, err)
			}
		})
	}

	invalidCases := []struct {
		name string
		key  string
	}{
		{name: "employee", key: "employee"},
		{name: "attendance", key: "attendance"},
		{name: "rates", key: "rates"},
		{name: "components", key: "components"},
	}
	for _, tt := range invalidCases {
		t.Run("invalid "+tt.name, func(t *testing.T) {
			facts := wbFacts()
			facts[tt.key] = func() {}
			if _, err := executeAllRules(rules, facts); err == nil {
				t.Fatalf("expected %s marshal error", tt.key)
			}
		})
	}
}

func TestExecuteAllRulesDerivesMinutesMinuteRateAndBasicSalaryFallback(t *testing.T) {
	facts := wbFacts()
	facts["attendance"].(map[string]interface{})["overtime_hours"] = 2
	facts["attendance"].(map[string]interface{})["overtime_minutes"] = 0
	facts["rates"].(map[string]interface{})["overtime_per_hour"] = 120000
	facts["rates"].(map[string]interface{})["overtime_per_minute"] = 0
	delete(facts, "components")

	rule := Rule{
		Conditions: []interface{}{map[string]interface{}{
			"field":    "attendance.overtime_minutes",
			"operator": ">",
			"value":    0,
		}},
		Action: Action{Type: "ADD_COMPONENT", Code: "OVERTIME_PAY", Formula: "attendance.overtime_minutes * rates.overtime_per_minute"},
	}

	resp, err := executeAllRules([]Rule{rule}, facts)
	if err != nil {
		t.Fatalf("unexpected execution error: %v", err)
	}
	if len(resp.Components) != 1 || resp.Components[0].Amount != 240000 {
		t.Fatalf("expected derived overtime amount 240000, got %#v", resp.Components)
	}
}

func TestExecuteAllRulesReturnsGRLBuildError(t *testing.T) {
	rule := wbRule("BROKEN", "(")
	if _, err := executeAllRules([]Rule{rule}, wbFacts()); err == nil || !strings.Contains(err.Error(), "build rule error") {
		t.Fatalf("expected GRL build error, got %v", err)
	}
}

func TestExecuteAllRulesCoversZeroOvertimeRatesAndDefinitionError(t *testing.T) {
	facts := wbFacts()
	facts["rates"].(map[string]interface{})["overtime_per_hour"] = 0
	facts["rates"].(map[string]interface{})["overtime_per_minute"] = 0

	if _, err := executeAllRules([]Rule{wbRule("BONUS", "100")}, facts); err != nil {
		t.Fatalf("expected zero overtime rates to remain valid, got %v", err)
	}

	if _, err := executeAllRules([]Rule{wbRule("BROKEN", "")}, wbFacts()); err == nil || !strings.Contains(err.Error(), "action.formula is empty") {
		t.Fatalf("expected empty formula definition error, got %v", err)
	}
}

func TestExecuteRulesHTTPHandlerCoversBadRequestExecutionErrorAndSuccess(t *testing.T) {
	t.Run("invalid JSON", func(t *testing.T) {
		recorder := httptest.NewRecorder()
		request := httptest.NewRequest(http.MethodPost, "/execute", strings.NewReader(`{"rules":`))
		executeRules(recorder, request)
		if recorder.Code != http.StatusBadRequest {
			t.Fatalf("expected 400, got %d: %s", recorder.Code, recorder.Body.String())
		}
	})

	t.Run("execution error", func(t *testing.T) {
		body := []byte(`{"rules":[],"facts":{}}`)
		recorder := httptest.NewRecorder()
		request := httptest.NewRequest(http.MethodPost, "/execute", bytes.NewReader(body))
		executeRules(recorder, request)
		if recorder.Code != http.StatusInternalServerError {
			t.Fatalf("expected 500, got %d: %s", recorder.Code, recorder.Body.String())
		}
	})

	t.Run("success", func(t *testing.T) {
		requestPayload := ExecuteRequest{
			Rules:          []Rule{wbRule("OVERTIME_PAY", "attendance.overtime_minutes * rates.overtime_per_minute")},
			Facts:          wbFacts(),
			ComponentTypes: map[string]string{"OVERTIME_PAY": "EARNING"},
		}
		body, err := json.Marshal(requestPayload)
		if err != nil {
			t.Fatalf("unexpected request marshal error: %v", err)
		}

		recorder := httptest.NewRecorder()
		request := httptest.NewRequest(http.MethodPost, "/execute", bytes.NewReader(body))
		executeRules(recorder, request)
		if recorder.Code != http.StatusOK {
			t.Fatalf("expected 200, got %d: %s", recorder.Code, recorder.Body.String())
		}

		var response ExecuteResponse
		if err := json.Unmarshal(recorder.Body.Bytes(), &response); err != nil {
			t.Fatalf("expected valid response JSON, got %v", err)
		}
		if len(response.Components) != 1 || response.Components[0].Code != "OVERTIME_PAY" {
			t.Fatalf("unexpected response %#v", response)
		}
	})
}
