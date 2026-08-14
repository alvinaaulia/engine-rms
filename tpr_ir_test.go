package main

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"net/http/httptest"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
	"time"
)

func TestLaravelNormalizedPayloadIsAcceptedByGo(t *testing.T) {
	if testing.Short() {
		t.Skip("cross-language integration is excluded from the short unit suite")
	}
	laravelRoot := strings.TrimSpace(os.Getenv("LARAVEL_DIR"))
	if laravelRoot == "" {
		laravelRoot = filepath.Join("..", "papa-website-public")
	}
	laravelRoot = filepath.Clean(laravelRoot)
	if _, err := os.Stat(filepath.Join(laravelRoot, "bootstrap", "app.php")); err != nil {
		t.Skip("Laravel sibling repository is unavailable")
	}
	if _, err := exec.LookPath("php"); err != nil {
		t.Skip("PHP is unavailable")
	}
	definitions := []Rule{semanticRule("BONUS", "rates.bonus_rate", "HIGH")}
	definitions[0].Meta.RuleVersionID = 42
	definitionsJSON, _ := json.Marshal(definitions)
	factsJSON, _ := json.Marshal(semanticFacts())
	root := filepath.ToSlash(laravelRoot)
	code := fmt.Sprintf(`require '%s/vendor/autoload.php'; $app=require '%s/bootstrap/app.php'; $app->make(Illuminate\Contracts\Console\Kernel::class)->bootstrap(); $defs=json_decode('%s',true); $facts=json_decode('%s',true); echo json_encode($app->make(App\Services\TypedPayrollRuleIrService::class)->buildExecutePayload($defs,$facts,['BONUS'=>'EARNING'],'cross-language-test'));`, root, root, definitionsJSON, factsJSON)
	const integrationTimeout = 180 * time.Second
	ctx, cancel := context.WithTimeout(context.Background(), integrationTimeout)
	defer cancel()
	command := exec.CommandContext(ctx, "php", "-r", code)
	output, err := command.CombinedOutput()
	if errors.Is(ctx.Err(), context.DeadlineExceeded) {
		t.Fatalf("Laravel normalizer integration exceeded the %s deadline", integrationTimeout)
	}
	if err != nil {
		t.Fatalf("Laravel normalizer failed: %v: %s", err, output)
	}
	var request ExecuteRequest
	if err := json.Unmarshal(output, &request); err != nil {
		t.Fatalf("Laravel emitted invalid JSON: %v: %s", err, output)
	}
	response, err := ExecuteTPRRuleSet(context.Background(), request.RuleSet, request.Facts, request.ComponentTypes)
	if err != nil {
		t.Fatalf("Go rejected Laravel-normalized payload: %v", err)
	}
	if len(response.Components) != 1 || response.Components[0].Amount != 1000 || response.Components[0].SourceRuleVersionID != 42 {
		t.Fatalf("unexpected cross-language output: %#v", response.Components)
	}
}

func TestRuleExecutionTimeoutConfiguration(t *testing.T) {
	t.Run("uses a safer default for slower research machines", func(t *testing.T) {
		t.Setenv("RULE_ENGINE_EXECUTION_TIMEOUT", "")
		if got := ruleExecutionTimeout(); got != 30*time.Second {
			t.Fatalf("unexpected default timeout: %s", got)
		}
	})

	t.Run("accepts a bounded duration override", func(t *testing.T) {
		t.Setenv("RULE_ENGINE_EXECUTION_TIMEOUT", "45s")
		if got := ruleExecutionTimeout(); got != 45*time.Second {
			t.Fatalf("unexpected configured timeout: %s", got)
		}
	})

	for _, invalid := range []string{"invalid", "0s", "-1s", "3m"} {
		t.Run("rejects_"+strings.ReplaceAll(invalid, "-", "negative_"), func(t *testing.T) {
			t.Setenv("RULE_ENGINE_EXECUTION_TIMEOUT", invalid)
			if got := ruleExecutionTimeout(); got != 30*time.Second {
				t.Fatalf("invalid timeout %q produced %s", invalid, got)
			}
		})
	}
}

func TestTPRHTTPTrustBoundary(t *testing.T) {
	t.Run("method", func(t *testing.T) {
		rec := httptest.NewRecorder()
		executeRules(rec, httptest.NewRequest(http.MethodGet, "/execute", nil))
		if rec.Code != http.StatusMethodNotAllowed {
			t.Fatalf("got %d", rec.Code)
		}
	})
	t.Run("oversize", func(t *testing.T) {
		rec := httptest.NewRecorder()
		body := append([]byte(`{"rules":[],"facts":{},"component_types":{},"padding":"`), bytes.Repeat([]byte("x"), int(maxExecuteRequestBytes)+1)...)
		body = append(body, []byte(`"}`)...)
		executeRules(rec, httptest.NewRequest(http.MethodPost, "/execute", bytes.NewReader(body)))
		if rec.Code != http.StatusRequestEntityTooLarge {
			t.Fatalf("got %d", rec.Code)
		}
	})
	t.Run("unknown top-level property", func(t *testing.T) {
		rec := httptest.NewRecorder()
		executeRules(rec, httptest.NewRequest(http.MethodPost, "/execute", strings.NewReader(`{"unknown":true}`)))
		if rec.Code != http.StatusBadRequest {
			t.Fatalf("got %d", rec.Code)
		}
	})
	t.Run("trailing JSON", func(t *testing.T) {
		rec := httptest.NewRecorder()
		executeRules(rec, httptest.NewRequest(http.MethodPost, "/execute", strings.NewReader(`{} {}`)))
		if rec.Code != http.StatusBadRequest {
			t.Fatalf("got %d", rec.Code)
		}
	})
}

func TestHealthEndpoint(t *testing.T) {
	t.Run("ready", func(t *testing.T) {
		rec := httptest.NewRecorder()
		health(rec, httptest.NewRequest(http.MethodGet, "/health", nil))
		if rec.Code != http.StatusOK {
			t.Fatalf("got status %d", rec.Code)
		}
		if !strings.Contains(rec.Body.String(), `"status":"ready"`) {
			t.Fatalf("unexpected body %q", rec.Body.String())
		}
	})
	t.Run("method rejected", func(t *testing.T) {
		rec := httptest.NewRecorder()
		health(rec, httptest.NewRequest(http.MethodPost, "/health", nil))
		if rec.Code != http.StatusMethodNotAllowed {
			t.Fatalf("got status %d", rec.Code)
		}
	})
}

func TestInternalServiceAuthentication(t *testing.T) {
	t.Setenv("RULE_ENGINE_INTERNAL_TOKEN", "research-test-token")
	handler := requireInternalToken(executeRules)

	t.Run("missing token is rejected", func(t *testing.T) {
		recorder := httptest.NewRecorder()
		handler(recorder, httptest.NewRequest(http.MethodPost, "/execute", strings.NewReader(`{}`)))
		if recorder.Code != http.StatusUnauthorized {
			t.Fatalf("got status %d", recorder.Code)
		}
	})

	t.Run("valid token reaches endpoint", func(t *testing.T) {
		recorder := httptest.NewRecorder()
		request := httptest.NewRequest(http.MethodGet, "/execute", nil)
		request.Header.Set(internalTokenHeader, "research-test-token")
		handler(recorder, request)
		if recorder.Code != http.StatusMethodNotAllowed {
			t.Fatalf("got status %d", recorder.Code)
		}
	})
}

func FuzzExecuteHTTPTrustBoundary(f *testing.F) {
	for _, seed := range []string{
		`{}`,
		`{"schema_version":"1.0"}`,
		`{"unknown":true}`,
		`not-json`,
	} {
		f.Add(seed)
	}

	f.Fuzz(func(t *testing.T, body string) {
		// Keep fuzz cases below the endpoint's documented transport limit so a
		// fuzz worker cannot turn one generated string into unbounded memory use.
		if len(body) > int(maxExecuteRequestBytes)+1024 {
			t.Skip()
		}
		recorder := httptest.NewRecorder()
		executeRules(recorder, httptest.NewRequest(http.MethodPost, "/execute", strings.NewReader(body)))
		if recorder.Code < 200 || recorder.Code > 599 {
			t.Fatalf("invalid HTTP status %d", recorder.Code)
		}
	})
}

func BenchmarkRuleEngineScale(b *testing.B) {
	for _, count := range []int{1, 10, 50} {
		b.Run(fmt.Sprintf("rules_%d", count), func(b *testing.B) {
			rules := make([]Rule, count)
			for index := range rules {
				rules[index] = semanticRule(fmt.Sprintf("BENCH_%03d", index), "rates.bonus_rate", "NORMAL")
			}
			ruleSet := adaptedRuleSet(b, rules)
			componentTypes := make(map[string]string, count)
			for index := range rules {
				componentTypes[fmt.Sprintf("BENCH_%03d", index)] = "EARNING"
			}
			b.ReportAllocs()
			b.ResetTimer()
			for iteration := 0; iteration < b.N; iteration++ {
				if _, err := ExecuteTPRRuleSet(context.Background(), ruleSet, semanticFacts(), componentTypes); err != nil {
					b.Fatal(err)
				}
			}
		})
	}
}

func semanticFacts() map[string]interface{} {
	return map[string]interface{}{
		"employee":   map[string]interface{}{"status": "aktif", "contract_type": "karyawan_tetap", "has_npwp": true, "ptkp_status": "TK/0", "grade": "A", "join_date": "2020-01-01", "years_of_service": 6.0, "performance_score": 90.0, "basic_salary": "5000000.00", "annual_bonus_eligible": true, "thr_eligible": true},
		"attendance": map[string]interface{}{"days_present": 20.0, "work_hours": 160.0, "work_minutes": 9600.0, "days_absent": 0.0, "late_minutes": 5.0, "unpaid_leave_days": 0.0, "overtime_minutes": 60.0, "overtime_hours": 1.0},
		"rates":      map[string]interface{}{"bonus_rate": "1000.00", "tax_flat_amount": "0", "overtime_per_hour": "60000", "overtime_per_minute": "1000", "late_deduction_per_minute": "1000", "unpaid_leave_per_day": "100000"},
		"components": map[string]interface{}{"BASIC_SALARY": "5000000.00"},
	}
}

func semanticRule(code, formula string, priority string) Rule {
	return Rule{Conditions: []interface{}{map[string]interface{}{"field": "employee.status", "operator": "==", "value": "aktif"}}, Action: Action{Type: "ADD_COMPONENT", Code: code, Formula: formula}, Meta: RuleMetadata{Priority: priority}}
}

func adaptedRuleSet(t testing.TB, rules []Rule) *TPRRuleSet {
	t.Helper()
	rs, err := AdaptLegacyPayload(rules, semanticFacts())
	if err != nil {
		t.Fatalf("adapt failed: %v", err)
	}
	return rs
}

func TestTPRSchemaAndTrustBoundaryValidation(t *testing.T) {
	rs := adaptedRuleSet(t, []Rule{semanticRule("BONUS", "rates.bonus_rate", "NORMAL")})
	t.Run("valid", func(t *testing.T) {
		if err := ValidateTPRRuleSet(rs, semanticFacts()); err != nil {
			t.Fatal(err)
		}
	})
	t.Run("missing schema", func(t *testing.T) {
		copy := *rs
		copy.SchemaVersion = ""
		assertValidationCode(t, ValidateTPRRuleSet(&copy, semanticFacts()), "MISSING_SCHEMA_VERSION")
	})
	t.Run("unsupported schema", func(t *testing.T) {
		copy := *rs
		copy.SchemaVersion = "2.0"
		assertValidationCode(t, ValidateTPRRuleSet(&copy, semanticFacts()), "UNSUPPORTED_SCHEMA_VERSION")
	})
	t.Run("unknown field", func(t *testing.T) {
		copy := cloneRuleSet(t, rs)
		copy.Rules[0].Condition.Children[0].Field.Name = "password"
		assertValidationCode(t, ValidateTPRRuleSet(copy, semanticFacts()), "UNKNOWN_FIELD")
	})
	t.Run("wrong literal type", func(t *testing.T) {
		copy := cloneRuleSet(t, rs)
		leaf := &copy.Rules[0].Condition.Children[0]
		leaf.Literal.Type = "numeric"
		leaf.Literal.Value = 1.0
		assertValidationCode(t, ValidateTPRRuleSet(copy, semanticFacts()), "INVALID_LITERAL_TYPE")
	})
	t.Run("invalid formula fact type", func(t *testing.T) {
		facts := semanticFacts()
		facts["rates"].(map[string]interface{})["bonus_rate"] = "not-a-number"
		assertValidationCode(t, ValidateTPRRuleSet(rs, facts), "INVALID_FACT_TYPE")
	})
	t.Run("unknown namespace", func(t *testing.T) {
		copy := cloneRuleSet(t, rs)
		copy.FieldCatalog[0].Reference.Namespace = "system"
		assertValidationCode(t, ValidateTPRRuleSet(copy, semanticFacts()), "UNKNOWN_NAMESPACE")
	})
}

func TestTPRConditionSemanticsAndLimits(t *testing.T) {
	rule := semanticRule("BONUS", "100", "NORMAL")
	rule.Conditions = map[string]interface{}{"type": "OR", "rules": []interface{}{
		map[string]interface{}{"field": "employee.status", "operator": "==", "value": "tidak-aktif"},
		map[string]interface{}{"type": "AND", "rules": []interface{}{
			map[string]interface{}{"field": "employee.has_npwp", "operator": "==", "value": true},
			map[string]interface{}{"field": "employee.years_of_service", "operator": ">=", "value": 5},
		}},
	}}
	resp, err := executeAllRules([]Rule{rule}, semanticFacts())
	if err != nil {
		t.Fatal(err)
	}
	if len(resp.Components) != 1 || resp.Components[0].Amount != 100 {
		t.Fatalf("unexpected nested condition output: %#v", resp.Components)
	}
	bad := rule
	bad.Conditions = map[string]interface{}{"type": "AND", "rules": []interface{}{}}
	if _, err := AdaptLegacyPayload([]Rule{bad}, semanticFacts()); err == nil {
		t.Fatal("empty group must fail")
	}
	missing := semanticFacts()
	delete(missing["employee"].(map[string]interface{}), "status")
	if _, err := AdaptLegacyPayload([]Rule{rule}, missing); err == nil {
		t.Fatal("missing required condition fact must fail")
	}
	unicodeRule := semanticRule("UNICODE", "10", "NORMAL")
	unicodeRule.Conditions = []interface{}{map[string]interface{}{"field": "employee.grade", "operator": "CONTAINS", "value": "å"}}
	facts := semanticFacts()
	facts["employee"].(map[string]interface{})["grade"] = "Ångström"
	resp, err = executeAllRules([]Rule{unicodeRule}, facts)
	if err != nil || len(resp.Components) != 1 {
		t.Fatalf("Unicode contains failed: %#v %v", resp, err)
	}
	membership := semanticRule("MEMBER", "1", "NORMAL")
	membership.Conditions = []interface{}{map[string]interface{}{"field": "employee.status", "operator": "IN", "value": []interface{}{"aktif", "tetap"}}}
	if result, err := executeAllRules([]Rule{membership}, semanticFacts()); err != nil || len(result.Components) != 1 {
		t.Fatalf("membership failed: %#v %v", result, err)
	}
	eligibility := semanticRule("ELIGIBLE", "1", "NORMAL")
	eligibility.Conditions = []interface{}{
		map[string]interface{}{"field": "employee.annual_bonus_eligible", "operator": "==", "value": true},
		map[string]interface{}{"field": "employee.thr_eligible", "operator": "==", "value": true},
	}
	if result, err := executeAllRules([]Rule{eligibility}, semanticFacts()); err != nil || len(result.Components) != 1 {
		t.Fatalf("eligibility flags failed: %#v %v", result, err)
	}
	many := make([]interface{}, TPRMaxConditionLeaves+1)
	for i := range many {
		many[i] = map[string]interface{}{"field": "employee.status", "operator": "==", "value": "aktif"}
	}
	tooMany := semanticRule("LIMIT", "1", "NORMAL")
	tooMany.Conditions = many
	if _, err := AdaptLegacyPayload([]Rule{tooMany}, semanticFacts()); err == nil {
		t.Fatal("leaf limit must be enforced")
	}
}

func TestTPRFormulaASTRejectsUnsafeInputAndRoundsMoney(t *testing.T) {
	catalog := map[string]TPRFieldReference{}
	for _, item := range fieldCatalogFromFacts(semanticFacts()) {
		catalog[item.Reference.Key()] = item.Reference
	}
	valid := []string{"0.1 + 0.2", "1 / 3", "-2.5", "(rates.bonus_rate + 10) * 2"}
	for _, formula := range valid {
		if _, err := parseFormula(formula, catalog); err != nil {
			t.Errorf("valid formula %q rejected: %v", formula, err)
		}
	}
	invalid := []string{"unknown.value + 1", "1 / 0", "1; Retract(\"x\")", "max(1,2)", strings.Repeat("(", TPRMaxFormulaDepth+1) + "1" + strings.Repeat(")", TPRMaxFormulaDepth+1)}
	for _, formula := range invalid {
		if _, err := parseFormula(formula, catalog); err == nil {
			t.Errorf("unsafe formula %q accepted", formula)
		}
	}
	monetaryCases := []struct {
		formula  string
		expected float64
	}{
		{"0.1 + 0.2", 0.3}, {"1 / 3", 0.333333}, {"2.5", 2.5}, {"10.5", 10.5},
		{"-2.5", -2.5}, {"1.2345675", 1.234568}, {"999999999999", 999999999999},
	}
	for _, item := range monetaryCases {
		resp, err := executeAllRules([]Rule{semanticRule("DECIMAL", item.formula, "NORMAL")}, semanticFacts())
		if err != nil {
			t.Fatalf("formula %s failed: %v", item.formula, err)
		}
		if resp.Components[0].Amount != item.expected {
			t.Fatalf("formula %s: expected %.6f, got %.12f", item.formula, item.expected, resp.Components[0].Amount)
		}
	}
	zeroFacts := semanticFacts()
	zeroFacts["rates"].(map[string]interface{})["bonus_rate"] = "0"
	if _, err := executeAllRules([]Rule{semanticRule("ZERO", "1 / rates.bonus_rate", "NORMAL")}, zeroFacts); err == nil {
		t.Fatal("dynamic division by zero must fail")
	}
}

func TestTPRHitPoliciesAndConflictMatrix(t *testing.T) {
	rules := []Rule{semanticRule("BONUS", "40", "HIGH"), semanticRule("BONUS", "60", "LOW")}
	resp, err := executeAllRules(rules, semanticFacts())
	if err != nil {
		t.Fatal(err)
	}
	if len(resp.Components) != 1 || resp.Components[0].Amount != 100 {
		t.Fatalf("COLLECT_SUM failed: %#v", resp.Components)
	}
	mixed := append([]Rule(nil), rules...)
	mixed[0].Action.Type = "SET_COMPONENT"
	if _, err := AdaptLegacyPayload(mixed, semanticFacts()); err == nil {
		t.Fatal("SET+ADD must be rejected")
	}
	setRules := append([]Rule(nil), rules...)
	for i := range setRules {
		setRules[i].Action.Type = "SET_COMPONENT"
	}
	rs, err := AdaptLegacyPayload(setRules, semanticFacts())
	if err != nil {
		t.Fatal(err)
	}
	resp, err = ExecuteTPRRuleSet(context.Background(), rs, semanticFacts(), map[string]string{"BONUS": "EARNING"})
	if err != nil || resp.Components[0].Amount != 40 {
		t.Fatalf("PRIORITY failed: %#v %v", resp.Components, err)
	}
	first := cloneRuleSet(t, rs)
	first.ComponentPolicies["BONUS"] = "FIRST"
	first.Rules[0].Priority = 50
	first.Rules[1].Priority = 50
	if err := ValidateTPRRuleSet(first, semanticFacts()); err != nil {
		t.Fatal(err)
	}
	resp, err = ExecuteTPRRuleSet(context.Background(), first, semanticFacts(), map[string]string{"BONUS": "EARNING"})
	if err != nil || len(resp.Components) != 1 {
		t.Fatalf("FIRST failed: %#v %v", resp.Components, err)
	}
	tie := cloneRuleSet(t, rs)
	tie.Rules[0].Priority = 50
	tie.Rules[1].Priority = 50
	assertValidationCode(t, ValidateTPRRuleSet(tie, semanticFacts()), "PRIORITY_TIE")
	unique := cloneRuleSet(t, rs)
	unique.ComponentPolicies["BONUS"] = "UNIQUE"
	assertValidationCode(t, ValidateTPRRuleSet(unique, semanticFacts()), "POTENTIAL_UNIQUE_CONFLICT")
	dupA := semanticRule("DUP", "10", "NORMAL")
	dupA.Conditions = []interface{}{map[string]interface{}{"field": "employee.status", "operator": "==", "value": "aktif"}, map[string]interface{}{"field": "employee.has_npwp", "operator": "==", "value": true}}
	dupB := dupA
	dupB.Conditions = []interface{}{map[string]interface{}{"field": "employee.has_npwp", "operator": "==", "value": true}, map[string]interface{}{"field": "employee.status", "operator": "==", "value": "aktif"}}
	if _, err := AdaptLegacyPayload([]Rule{dupA, dupB}, semanticFacts()); err == nil {
		t.Fatal("semantic duplicate with permuted AND children must fail")
	}
}

func TestTPRDeterminismCanonicalizationAndMetamorphicRelations(t *testing.T) {
	a := semanticRule("A", "rates.bonus_rate", "NORMAL")
	b := semanticRule("B", "200", "HIGH")
	rs1 := adaptedRuleSet(t, []Rule{a, b})
	rs2 := adaptedRuleSet(t, []Rule{b, a})
	h1, _ := CanonicalIRHash(*rs1)
	h2, _ := CanonicalIRHash(*rs2)
	if h1 != h2 {
		t.Fatalf("permutation changed canonical hash: %s != %s", h1, h2)
	}
	metadataOnly := cloneRuleSet(t, rs1)
	metadataOnly.Rules[0].Metadata.Description = "non-execution text"
	metadataHash, _ := CanonicalIRHash(*metadataOnly)
	if metadataHash != h1 {
		t.Fatal("non-execution metadata changed semantic hash")
	}
	g1, err := buildTPRGRL(rs1)
	if err != nil {
		t.Fatal(err)
	}
	roundTrip := cloneRuleSet(t, rs1)
	g2, err := buildTPRGRL(roundTrip)
	if err != nil || g1 != g2 {
		t.Fatal("same IR did not produce identical GRL")
	}
	r1, err := ExecuteTPRRuleSet(context.Background(), rs1, semanticFacts(), map[string]string{"A": "EARNING", "B": "EARNING"})
	if err != nil {
		t.Fatal(err)
	}
	r2, err := ExecuteTPRRuleSet(context.Background(), rs2, semanticFacts(), map[string]string{"A": "EARNING", "B": "EARNING"})
	if err != nil {
		t.Fatal(err)
	}
	if !sameSemanticComponents(r1.Components, r2.Components) {
		t.Fatalf("rule permutation changed output: %#v %#v", r1.Components, r2.Components)
	}
	falseRule := semanticRule("IGNORED", "999", "HIGH")
	falseRule.Conditions = []interface{}{map[string]interface{}{"field": "employee.status", "operator": "==", "value": "never"}}
	r3, err := executeAllRules([]Rule{a, b, falseRule}, semanticFacts())
	if err != nil {
		t.Fatal(err)
	}
	if !sameAmountsByCode(r1.Components, r3.Components) {
		t.Fatalf("always-false rule changed output: %#v %#v", r1.Components, r3.Components)
	}
	equivalent1, err := executeAllRules([]Rule{semanticRule("EQ", "1 + 2", "NORMAL")}, semanticFacts())
	if err != nil {
		t.Fatal(err)
	}
	equivalent2, err := executeAllRules([]Rule{semanticRule("EQ", "3", "NORMAL")}, semanticFacts())
	if err != nil || equivalent1.Components[0].Amount != equivalent2.Components[0].Amount {
		t.Fatal("equivalent arithmetic changed output")
	}
	split, err := executeAllRules([]Rule{semanticRule("SPLIT", "40", "NORMAL"), semanticRule("SPLIT", "60", "HIGH")}, semanticFacts())
	if err != nil || split.Components[0].Amount != 100 {
		t.Fatal("split ADD relation failed")
	}
	lowFacts := semanticFacts()
	highFacts := semanticFacts()
	lowFacts["rates"].(map[string]interface{})["bonus_rate"] = "1000"
	highFacts["rates"].(map[string]interface{})["bonus_rate"] = "2000"
	low, err := executeAllRules([]Rule{a}, lowFacts)
	if err != nil {
		t.Fatal(err)
	}
	high, err := executeAllRules([]Rule{a}, highFacts)
	if err != nil || high.Components[0].Amount < low.Components[0].Amount {
		t.Fatal("monotonic positive rate relation failed")
	}
}

func assertValidationCode(t *testing.T, err error, code string) {
	t.Helper()
	if err == nil {
		t.Fatalf("expected %s", code)
	}
	ve, ok := err.(*ValidationError)
	if !ok || ve.ErrorCode != code {
		t.Fatalf("expected %s, got %T %v", code, err, err)
	}
}
func cloneRuleSet(t *testing.T, rs *TPRRuleSet) *TPRRuleSet {
	t.Helper()
	b, err := json.Marshal(rs)
	if err != nil {
		t.Fatal(err)
	}
	var copy TPRRuleSet
	if err := json.Unmarshal(b, &copy); err != nil {
		t.Fatal(err)
	}
	return &copy
}
func sameSemanticComponents(a, b []Component) bool {
	normalize := func(values []Component) map[string]struct {
		amount float64
		source string
	} {
		m := map[string]struct {
			amount float64
			source string
		}{}
		for _, v := range values {
			m[v.Code] = struct {
				amount float64
				source string
			}{v.Amount, v.SourceRuleID}
		}
		return m
	}
	return reflect.DeepEqual(normalize(a), normalize(b))
}
func sameAmountsByCode(a, b []Component) bool {
	m := func(v []Component) map[string]float64 {
		x := map[string]float64{}
		for _, c := range v {
			x[c.Code] = c.Amount
		}
		return x
	}
	return reflect.DeepEqual(m(a), m(b))
}
