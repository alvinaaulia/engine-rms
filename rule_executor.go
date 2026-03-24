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
	default:
		return fmt.Sprintf("%v", x), nil
	}
}


func buildMultiGRL(rules []Rule) (string, error) {
	var sb strings.Builder

	for i, rule := range rules {
		if len(rule.Conditions) == 0 {
			continue
		}
		cond := rule.Conditions[0]

		field := normalizeField(cond.Field)
		op := operatorMap(cond.Operator)
		val, err := gruleLiteral(cond.Value)
		if err != nil {
			return "", err
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
		%s %s %s
	then
		out.AddComponent(%s, %s, %d);
		Retract("%s");
}
`, ruleName, field, op, val, codeLit, formula, i, ruleName))
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
