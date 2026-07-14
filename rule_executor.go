package main

import (
	"encoding/json"
	"fmt"
	"regexp"
	"strings"

	"github.com/hyperjumptech/grule-rule-engine/ast"
	"github.com/hyperjumptech/grule-rule-engine/builder"
	"github.com/hyperjumptech/grule-rule-engine/engine"
	"github.com/hyperjumptech/grule-rule-engine/pkg"
)

var fieldAliases = map[string]string{
	"employee.status":                 "employee.Status",
	"employee.contract_type":          "employee.ContractType",
	"employee.grade":                  "employee.Grade",
	"employee.join_date":              "employee.JoinDate",
	"employee.has_npwp":               "employee.HasNpwp",
	"employee.ptkp_status":            "employee.PtkpStatus",
	"employee.years_of_service":       "employee.YearsOfService",
	"employee.performance_score":      "employee.PerformanceScore",
	"employee.basic_salary":           "employee.BasicSalary",
	"attendance.days_present":         "attendance.DaysPresent",
	"attendance.days_absent":          "attendance.DaysAbsent",
	"attendance.late_minutes":         "attendance.LateMinutes",
	"attendance.unpaid_leave_days":    "attendance.UnpaidLeaveDays",
	"attendance.work_hours":           "attendance.WorkHours",
	"attendance.work_minutes":         "attendance.WorkMinutes",
	"attendance.overtime_hours":       "attendance.OvertimeHours",
	"attendance.overtime_minutes":     "attendance.OvertimeMinutes",
	"rates.late_deduction_per_minute": "rates.LatePerMinute",
	"rates.unpaid_leave_per_day":      "rates.UnpaidLeavePerDay",
	"rates.overtime_per_hour":         "rates.OvertimePerHour",
	"rates.overtime_per_minute":       "rates.OvertimePerMinute",
	"rates.tax_flat_amount":           "rates.TaxFlatAmount",
	"components.basic_salary":         "components.BASIC_SALARY",
	"components.BASIC_SALARY":         "components.BASIC_SALARY",
	"components.th_r":                 "components.TH_R",
	"components.TH_R":                 "components.TH_R",
	"components.thr":                  "components.THR",
	"components.THR":                  "components.THR",
	"components.overtime_pay":         "components.OVERTIME_PAY",
	"components.OVERTIME_PAY":         "components.OVERTIME_PAY",
}

var formulaAliasReplacer = strings.NewReplacer(
	"employee.status", "employee.Status",
	"employee.contract_type", "employee.ContractType",
	"employee.grade", "employee.Grade",
	"employee.join_date", "employee.JoinDate",
	"employee.has_npwp", "employee.HasNpwp",
	"employee.ptkp_status", "employee.PtkpStatus",
	"employee.years_of_service", "employee.YearsOfService",
	"employee.performance_score", "employee.PerformanceScore",
	"employee.basic_salary", "employee.BasicSalary",
	"attendance.days_present", "attendance.DaysPresent",
	"attendance.days_absent", "attendance.DaysAbsent",
	"attendance.late_minutes", "attendance.LateMinutes",
	"attendance.unpaid_leave_days", "attendance.UnpaidLeaveDays",
	"attendance.work_hours", "attendance.WorkHours",
	"attendance.work_minutes", "attendance.WorkMinutes",
	"attendance.overtime_hours", "attendance.OvertimeHours",
	"attendance.overtime_minutes", "attendance.OvertimeMinutes",
	"rates.late_deduction_per_minute", "rates.LatePerMinute",
	"rates.unpaid_leave_per_day", "rates.UnpaidLeavePerDay",
	"rates.overtime_per_hour", "rates.OvertimePerHour",
	"rates.overtime_per_minute", "rates.OvertimePerMinute",
	"rates.tax_flat_amount", "rates.TaxFlatAmount",
	"components.basic_salary", "components.BASIC_SALARY",
	"components.th_r", "components.TH_R",
	"components.thr", "components.THR",
	"components.overtime_pay", "components.OVERTIME_PAY",
)

var dynamicEmployeeTokenPattern = regexp.MustCompile(`\bemployee\.([a-z_][a-z0-9_]*)\b`)
var dynamicAttendanceTokenPattern = regexp.MustCompile(`\battendance\.([a-z_][a-z0-9_]*)\b`)
var dynamicRateTokenPattern = regexp.MustCompile(`\brates\.([a-z_][a-z0-9_]*)\b`)
var dynamicComponentTokenPattern = regexp.MustCompile(`\bcomponents\.([A-Za-z_][A-Za-z0-9_]*)\b`)

type RuleHelper struct{}

func (RuleHelper) Contains(value interface{}, expected interface{}) bool {
	return strings.Contains(
		strings.ToLower(fmt.Sprint(value)),
		strings.ToLower(fmt.Sprint(expected)),
	)
}

func normalizeField(field string) string {
	field = strings.TrimSpace(field)
	if mapped, ok := fieldAliases[field]; ok {
		return mapped
	}
	if strings.HasPrefix(field, "rates.") {
		rateKey := strings.TrimPrefix(field, "rates.")
		if normalizeDynamicFactKey(rateKey) != "" {
			return fmt.Sprintf("rates.Value(%q)", normalizeDynamicFactKey(rateKey))
		}
	}
	if strings.HasPrefix(field, "attendance.") {
		attendanceKey := strings.TrimPrefix(field, "attendance.")
		if normalizeDynamicFactKey(attendanceKey) != "" {
			return fmt.Sprintf("attendance.Value(%q)", normalizeDynamicFactKey(attendanceKey))
		}
	}
	if strings.HasPrefix(field, "components.") {
		componentKey := strings.TrimPrefix(field, "components.")
		if normalizeDynamicFactKey(componentKey) != "" {
			return fmt.Sprintf("components.Value(%q)", normalizeDynamicFactKey(componentKey))
		}
	}
	if strings.HasPrefix(field, "employee.") {
		employeeKey := strings.TrimPrefix(field, "employee.")
		if normalizeDynamicFactKey(employeeKey) != "" {
			return fmt.Sprintf("employee.Text(%q)", normalizeDynamicFactKey(employeeKey))
		}
	}
	return field
}

func isBooleanConditionField(field string) bool {
	switch strings.ToLower(strings.TrimSpace(field)) {
	case "employee.has_npwp":
		return true
	default:
		return false
	}
}

func conditionValueLiteral(field string, value interface{}) (string, error) {
	if isBooleanConditionField(field) {
		if parsed, ok := parseDynamicBool(value); ok {
			return gruleLiteral(parsed)
		}
	}

	return gruleLiteral(value)
}

func normalizeFormulaToken(prefix string, token string) string {
	parts := strings.SplitN(token, ".", 2)
	if len(parts) != 2 {
		return token
	}

	key := normalizeDynamicFactKey(parts[1])
	if key == "" || key == "value" || key == "text" || key == "bool" {
		return token
	}

	return fmt.Sprintf("%s.Value(%q)", prefix, key)
}

func normalizeFormula(formula string) string {
	normalized := strings.TrimSpace(formula)
	if normalized == "" {
		return normalized
	}
	normalized = formulaAliasReplacer.Replace(normalized)
	normalized = dynamicEmployeeTokenPattern.ReplaceAllStringFunc(normalized, func(token string) string {
		return normalizeFormulaToken("employee", token)
	})
	normalized = dynamicAttendanceTokenPattern.ReplaceAllStringFunc(normalized, func(token string) string {
		return normalizeFormulaToken("attendance", token)
	})
	normalized = dynamicRateTokenPattern.ReplaceAllStringFunc(normalized, func(token string) string {
		return normalizeFormulaToken("rates", token)
	})
	normalized = dynamicComponentTokenPattern.ReplaceAllStringFunc(normalized, func(token string) string {
		return normalizeFormulaToken("components", token)
	})
	return normalized
}

func gruleLiteral(v interface{}) (string, error) {
	switch x := v.(type) {
	case nil:
		return "nil", nil
	case string:
		b, err := json.Marshal(x)
		if err != nil {
			return "", err
		}
		return string(b), nil
	case bool:
		if x {
			return "true", nil
		}
		return "false", nil
	case json.Number:
		return x.String(), nil
	case float64:
		return fmt.Sprintf("%v", x), nil
	case int:
		return fmt.Sprintf("%d", x), nil
	case int64:
		return fmt.Sprintf("%d", x), nil
	case []interface{}, map[string]interface{}:
		b, err := json.Marshal(x)
		if err != nil {
			return "", err
		}
		return string(b), nil
	default:
		b, err := json.Marshal(x)
		if err == nil {
			return string(b), nil
		}
		return fmt.Sprintf("%v", x), nil
	}
}

func literalValues(value interface{}) ([]string, error) {
	rawValues := []interface{}{}

	switch typed := value.(type) {
	case []interface{}:
		rawValues = typed
	case []string:
		for _, item := range typed {
			rawValues = append(rawValues, item)
		}
	case []float64:
		for _, item := range typed {
			rawValues = append(rawValues, item)
		}
	case []int:
		for _, item := range typed {
			rawValues = append(rawValues, item)
		}
	default:
		rawValues = append(rawValues, typed)
	}

	values := make([]string, 0, len(rawValues))
	for _, rawValue := range rawValues {
		literal, err := gruleLiteral(rawValue)
		if err != nil {
			return nil, err
		}
		values = append(values, literal)
	}

	return values, nil
}

func buildMembershipExpression(field string, operator string, value interface{}) (string, error) {
	values, err := literalValues(value)
	if err != nil {
		return "", err
	}

	if len(values) == 0 {
		if operator == "NOT_IN" {
			return "true", nil
		}
		return "false", nil
	}

	parts := make([]string, 0, len(values))
	comparator := "=="
	separator := " || "

	if operator == "NOT_IN" {
		comparator = "!="
		separator = " && "
	}

	for _, literal := range values {
		parts = append(parts, fmt.Sprintf("%s %s %s", field, comparator, literal))
	}

	if len(parts) == 1 {
		return parts[0], nil
	}

	return "(" + strings.Join(parts, separator) + ")", nil
}

func buildConditionExpression(node interface{}) (string, error) {
	switch n := node.(type) {
	case nil:
		return "", nil
	case []interface{}:
		parts := make([]string, 0, len(n))
		for _, child := range n {
			expr, err := buildConditionExpression(child)
			if err != nil {
				return "", err
			}
			if strings.TrimSpace(expr) != "" {
				parts = append(parts, expr)
			}
		}

		if len(parts) == 0 {
			return "", nil
		}
		if len(parts) == 1 {
			return parts[0], nil
		}

		return "(" + strings.Join(parts, " && ") + ")", nil
	case map[string]interface{}:
		if rawRules, ok := n["rules"]; ok {
			children, ok := rawRules.([]interface{})
			if !ok {
				return "", fmt.Errorf("rules must be an array")
			}

			groupType := strings.ToUpper(strings.TrimSpace(fmt.Sprintf("%v", n["type"])))
			if groupType != "OR" {
				groupType = "AND"
			}

			separator := " && "
			if groupType == "OR" {
				separator = " || "
			}

			parts := make([]string, 0, len(children))
			for _, child := range children {
				expr, err := buildConditionExpression(child)
				if err != nil {
					return "", err
				}
				if strings.TrimSpace(expr) != "" {
					parts = append(parts, expr)
				}
			}

			if len(parts) == 0 {
				return "", nil
			}
			if len(parts) == 1 {
				return parts[0], nil
			}

			return "(" + strings.Join(parts, separator) + ")", nil
		}

		fieldRaw, hasField := n["field"]
		operatorRaw, hasOperator := n["operator"]
		if !hasField || !hasOperator {
			return "", fmt.Errorf("leaf condition must contain field and operator")
		}

		rawField := strings.TrimSpace(fmt.Sprintf("%v", fieldRaw))
		field := normalizeField(rawField)
		if field == "" {
			return "", fmt.Errorf("leaf condition field is empty")
		}

		operatorKey := strings.ToUpper(strings.TrimSpace(fmt.Sprintf("%v", operatorRaw)))
		switch operatorKey {
		case "IN", "NOT_IN":
			return buildMembershipExpression(field, operatorKey, n["value"])
		case "CONTAINS":
			value, err := conditionValueLiteral(rawField, n["value"])
			if err != nil {
				return "", err
			}
			return fmt.Sprintf("helper.Contains(%s, %s)", field, value), nil
		}

		operator := operatorMap(operatorKey)
		value, err := conditionValueLiteral(rawField, n["value"])
		if err != nil {
			return "", err
		}

		return fmt.Sprintf("%s %s %s", field, operator, value), nil
	default:
		return "", fmt.Errorf("unsupported condition node type %T", node)
	}
}

func buildMultiGRL(rules []Rule) (string, error) {
	var sb strings.Builder

	for i, rule := range rules {
		conditionExpr, err := buildConditionExpression(rule.Conditions)
		if err != nil {
			return "", fmt.Errorf("rule %d invalid conditions: %w", i, err)
		}

		if strings.TrimSpace(conditionExpr) == "" {
			continue
		}

		ruleName := fmt.Sprintf("Rule_%d", i)

		codeLit, err := gruleLiteral(rule.Action.Code)
		if err != nil {
			return "", err
		}
		actionTypeLit, err := gruleLiteral(rule.Action.Type)
		if err != nil {
			return "", err
		}

		formula := normalizeFormula(rule.Action.Formula)
		if formula == "" {
			return "", fmt.Errorf("rule %d action.formula is empty", i)
		}

		sb.WriteString(fmt.Sprintf(`
rule %s "payroll" {
	when
		%s
then
		out.ApplyComponent(%s, %s, %s, %d);
		Retract("%s");
}
`, ruleName, conditionExpr, actionTypeLit, codeLit, formula, i, ruleName))
	}

	return sb.String(), nil
}

func executeAllRules(rules []Rule, facts map[string]interface{}) (ExecuteResponse, error) {
	return executeAllRulesWithComponentTypes(rules, facts, nil)
}

func executeAllRulesWithComponentTypes(rules []Rule, facts map[string]interface{}, componentTypes map[string]string) (ExecuteResponse, error) {
	must := func(key string) (interface{}, error) {
		v, ok := facts[key]
		if !ok {
			return nil, fmt.Errorf("facts.%s not found", key)
		}
		return v, nil
	}

	employeeObj, err := must("employee")
	if err != nil {
		return ExecuteResponse{}, err
	}
	attendanceObj, err := must("attendance")
	if err != nil {
		return ExecuteResponse{}, err
	}
	ratesObj, err := must("rates")
	if err != nil {
		return ExecuteResponse{}, err
	}

	toStruct := func(src interface{}, dst interface{}) error {
		b, e := json.Marshal(src)
		if e != nil {
			return e
		}

		dec := json.NewDecoder(strings.NewReader(string(b)))
		dec.UseNumber()

		return dec.Decode(dst)
	}

	var emp Employee
	var att Attendance
	var rates Rates
	comps := Components{}

	if err := toStruct(employeeObj, &emp); err != nil {
		return ExecuteResponse{}, err
	}
	if err := toStruct(attendanceObj, &att); err != nil {
		return ExecuteResponse{}, err
	}
	if err := toStruct(ratesObj, &rates); err != nil {
		return ExecuteResponse{}, err
	}
	if rawComponents, ok := facts["components"]; ok {
		if err := toStruct(rawComponents, &comps); err != nil {
			return ExecuteResponse{}, err
		}
	}

	if att.OvertimeHours == 0 && att.OvertimeMinutes > 0 {
		att.OvertimeHours = att.OvertimeMinutes / 60
	}
	if att.OvertimeMinutes == 0 && att.OvertimeHours > 0 {
		att.OvertimeMinutes = att.OvertimeHours * 60
	}
	if rates.OvertimePerHour == 0 && rates.OvertimePerMinute > 0 {
		rates.OvertimePerHour = rates.OvertimePerMinute * 60
	}
	if rates.OvertimePerMinute == 0 && rates.OvertimePerHour > 0 {
		rates.OvertimePerMinute = rates.OvertimePerHour / 60
	}
	if comps.BASIC_SALARY == 0 {
		comps.BASIC_SALARY = emp.BasicSalary
	}

	grl, err := buildMultiGRL(rules)
	if err != nil {
		return ExecuteResponse{}, err
	}

	dataContext := ast.NewDataContext()
	out := &Emitter{Components: []Component{}}

	_ = dataContext.Add("employee", emp)
	_ = dataContext.Add("attendance", att)
	_ = dataContext.Add("rates", rates)
	_ = dataContext.Add("components", comps)
	_ = dataContext.Add("helper", RuleHelper{})
	_ = dataContext.Add("out", out)

	knowledgeLibrary := ast.NewKnowledgeLibrary()
	ruleBuilder := builder.NewRuleBuilder(knowledgeLibrary)

	if err := ruleBuilder.BuildRuleFromResource(
		"Payroll",
		"0.0.1",
		pkg.NewBytesResource([]byte(grl)),
	); err != nil {
		return ExecuteResponse{}, fmt.Errorf("build rule error: %w", err)
	}

	knowledgeBase, err := knowledgeLibrary.NewKnowledgeBaseInstance("Payroll", "0.0.1")
	if err != nil {
		return ExecuteResponse{}, err
	}

	gruleEngine := engine.NewGruleEngine()
	if err := gruleEngine.Execute(dataContext, knowledgeBase); err != nil {
		return ExecuteResponse{}, fmt.Errorf("execute error: %w", err)
	}

	summary := calculateSummary(emp, out.Components, componentTypes)

	return ExecuteResponse{
		Components: out.Components,
		Summary:    summary,
	}, nil
}
