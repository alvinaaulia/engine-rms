package main

import (
	"encoding/json"
	"fmt"
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
	"employee.years_of_service":       "employee.YearsOfService",
	"employee.basic_salary":           "employee.BasicSalary",
	"attendance.days_present":         "attendance.DaysPresent",
	"attendance.days_absent":          "attendance.DaysAbsent",
	"attendance.late_minutes":         "attendance.LateMinutes",
	"attendance.unpaid_leave_days":    "attendance.UnpaidLeaveDays",
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
	"employee.years_of_service", "employee.YearsOfService",
	"employee.basic_salary", "employee.BasicSalary",
	"attendance.days_present", "attendance.DaysPresent",
	"attendance.days_absent", "attendance.DaysAbsent",
	"attendance.late_minutes", "attendance.LateMinutes",
	"attendance.unpaid_leave_days", "attendance.UnpaidLeaveDays",
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

func normalizeField(field string) string {
	field = strings.TrimSpace(field)
	if mapped, ok := fieldAliases[field]; ok {
		return mapped
	}
	return field
}

func normalizeFormula(formula string) string {
	normalized := strings.TrimSpace(formula)
	if normalized == "" {
		return normalized
	}
	return formulaAliasReplacer.Replace(normalized)
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

		field := normalizeField(strings.TrimSpace(fmt.Sprintf("%v", fieldRaw)))
		if field == "" {
			return "", fmt.Errorf("leaf condition field is empty")
		}

		operator := operatorMap(strings.ToUpper(strings.TrimSpace(fmt.Sprintf("%v", operatorRaw))))
		value, err := gruleLiteral(n["value"])
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

		formula := normalizeFormula(rule.Action.Formula)
		if formula == "" {
			return "", fmt.Errorf("rule %d action.formula is empty", i)
		}

		sb.WriteString(fmt.Sprintf(`
rule %s "payroll" {
	when
		%s
	then
		out.AddComponent(%s, %s, %d);
		Retract("%s");
}
`, ruleName, conditionExpr, codeLit, formula, i, ruleName))
	}

	return sb.String(), nil
}

func executeAllRules(rules []Rule, facts map[string]interface{}) (ExecuteResponse, error) {
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

	summary := calculateSummary(emp, out.Components)

	return ExecuteResponse{
		Components: out.Components,
		Summary:    summary,
	}, nil
}
