package main

import (
	"context"
	"encoding/json"
	"fmt"
	"sort"
	"strings"
	"time"

	"github.com/hyperjumptech/grule-rule-engine/ast"
	"github.com/hyperjumptech/grule-rule-engine/builder"
	"github.com/hyperjumptech/grule-rule-engine/engine"
	"github.com/hyperjumptech/grule-rule-engine/pkg"
)

type TPRCandidate struct {
	ActionType    string
	Code          string
	Amount        float64
	Priority      int
	RuleID        string
	RuleVersionID int
	LegacyIndex   int
}

type CandidateCollector struct {
	Candidates    []TPRCandidate
	InvalidAmount bool
}

func (c *CandidateCollector) Emit(actionType, code string, amount interface{}, priority int64, ruleID string, ruleVersionID int64, legacyIndex int64) {
	parsed, ok := normalizePayrollMoney(amount)
	if !ok {
		c.InvalidAmount = true
		return
	}
	c.Candidates = append(c.Candidates, TPRCandidate{ActionType: actionType, Code: strings.ToUpper(strings.TrimSpace(code)), Amount: parsed, Priority: int(priority), RuleID: ruleID, RuleVersionID: int(ruleVersionID), LegacyIndex: int(legacyIndex)})
}

func buildTPRGRL(rs *TPRRuleSet) (string, error) {
	copySet := *rs
	copySet.Rules = append([]TPRRule(nil), rs.Rules...)
	canonicalizeRuleSet(&copySet)
	catalog := map[string]TPRFieldReference{}
	for _, f := range copySet.FieldCatalog {
		catalog[f.Reference.Key()] = f.Reference
	}
	var sb strings.Builder
	for i, r := range copySet.Rules {
		condition, err := emitConditionGRL(r.Condition)
		if err != nil {
			return "", err
		}
		for j, a := range r.Actions {
			astNode, err := parseFormula(a.Formula.Expression, catalog)
			if err != nil {
				return "", err
			}
			formula, err := emitFormulaGRL(astNode)
			if err != nil {
				return "", err
			}
			name := fmt.Sprintf("TPR_%x_%d", shaPrefix(r.ID), j)
			actionLit, _ := gruleLiteral(a.Type)
			codeLit, _ := gruleLiteral(a.Target.Code)
			ruleLit, _ := gruleLiteral(r.ID)
			sb.WriteString(fmt.Sprintf("\nrule %s \"TPR-IR 1.0\" salience %d {\nwhen\n\t%s\nthen\n\tout.Emit(%s, %s, %s, %d, %s, %d, %d);\n\tRetract(\"%s\");\n}\n", name, r.Priority, condition, actionLit, codeLit, formula, r.Priority, ruleLit, r.VersionID, r.LegacyIndex, name))
			_ = i
		}
	}
	return sb.String(), nil
}

func shaPrefix(value string) uint64 {
	var result uint64 = 1469598103934665603
	for i := 0; i < len(value); i++ {
		result ^= uint64(value[i])
		result *= 1099511628211
	}
	return result
}

func emitConditionGRL(node TPRConditionNode) (string, error) {
	if node.Kind == "group" {
		parts := make([]string, 0, len(node.Children))
		for _, child := range node.Children {
			expr, err := emitConditionGRL(child)
			if err != nil {
				return "", err
			}
			parts = append(parts, expr)
		}
		separator := " && "
		if node.Operator == "OR" {
			separator = " || "
		}
		return "(" + strings.Join(parts, separator) + ")", nil
	}
	field, err := safeGRLField(node.Field.Key())
	if err != nil {
		return "", err
	}
	values := literalSlice(node.Literal.Value)
	if node.Operator == "IN" || node.Operator == "NOT_IN" {
		parts := make([]string, 0, len(values))
		comparison := " == "
		separator := " || "
		if node.Operator == "NOT_IN" {
			comparison = " != "
			separator = " && "
		}
		for _, v := range values {
			lit, err := strictGRLLiteral(v, node.Field.DataType)
			if err != nil {
				return "", err
			}
			parts = append(parts, field+comparison+lit)
		}
		return "(" + strings.Join(parts, separator) + ")", nil
	}
	lit, err := strictGRLLiteral(node.Literal.Value, node.Field.DataType)
	if err != nil {
		return "", err
	}
	switch node.Operator {
	case "CONTAINS":
		return fmt.Sprintf("helper.Contains(%s, %s)", field, lit), nil
	}
	op := map[string]string{"EQ": "==", "NEQ": "!=", "GT": ">", "GTE": ">=", "LT": "<", "LTE": "<=", "BEFORE": "<", "AFTER": ">", "ON_OR_BEFORE": "<=", "ON_OR_AFTER": ">="}[node.Operator]
	if op == "" {
		return "", validationError("INVALID_OPERATOR_FOR_TYPE", "condition.operator", "operator has no GRL mapping")
	}
	return field + " " + op + " " + lit, nil
}

func literalSlice(value interface{}) []interface{} {
	if values, ok := value.([]interface{}); ok {
		return values
	}
	return []interface{}{value}
}
func strictGRLLiteral(value interface{}, dataType string) (string, error) {
	switch dataType {
	case "numeric", "string", "date", "boolean":
		return gruleLiteral(value)
	}
	return "", validationError("INVALID_LITERAL_TYPE", "literal", "unsupported literal type")
}

func ExecuteTPRRuleSet(ctx context.Context, rs *TPRRuleSet, facts map[string]interface{}, componentTypes map[string]string) (ExecuteResponse, error) {
	if err := ValidateTPRRuleSet(rs, facts); err != nil {
		return ExecuteResponse{}, err
	}
	if len(componentTypes) > 0 {
		for i, rule := range rs.Rules {
			for j, action := range rule.Actions {
				if componentTypeForCode(componentTypes, action.Target.Code) == "" {
					return ExecuteResponse{}, validationError("INVALID_COMPONENT", fmt.Sprintf("ruleset.rules[%d].actions[%d].target.code", i, j), "target component is absent from component_types")
				}
			}
		}
	}
	canonicalizeRuleSet(rs)
	emp, att, rates, comps, err := hydrateFacts(facts)
	if err != nil {
		return ExecuteResponse{}, err
	}
	grl, err := buildTPRGRL(rs)
	if err != nil {
		return ExecuteResponse{}, err
	}
	dataContext := ast.NewDataContext()
	out := &CandidateCollector{Candidates: []TPRCandidate{}}
	for key, value := range map[string]interface{}{"employee": emp, "attendance": att, "rates": rates, "components": comps, "helper": RuleHelper{}, "out": out} {
		if err := dataContext.Add(key, value); err != nil {
			return ExecuteResponse{}, err
		}
	}
	library := ast.NewKnowledgeLibrary()
	ruleBuilder := builder.NewRuleBuilder(library)
	if err := ruleBuilder.BuildRuleFromResource("TPR", "1.0", pkg.NewBytesResource([]byte(grl))); err != nil {
		return ExecuteResponse{}, fmt.Errorf("build rule error: %w", err)
	}
	kb, err := library.NewKnowledgeBaseInstance("TPR", "1.0")
	if err != nil {
		return ExecuteResponse{}, err
	}
	gruleEngine := engine.NewGruleEngine()
	gruleEngine.MaxCycle = uint64(len(rs.Rules)*TPRMaxActions + 1)
	if ctx == nil {
		ctx = context.Background()
	}
	if _, ok := ctx.Deadline(); !ok {
		var cancel context.CancelFunc
		ctx, cancel = context.WithTimeout(ctx, 5*time.Second)
		defer cancel()
	}
	if err := gruleEngine.ExecuteWithContext(ctx, dataContext, kb); err != nil {
		return ExecuteResponse{}, fmt.Errorf("execute error: %w", err)
	}
	if out.InvalidAmount {
		return ExecuteResponse{}, validationError("INVALID_FORMULA_RESULT", "ruleset.rules", "formula produced NaN, infinity, overflow, or a non-numeric value")
	}
	components, err := resolveCandidates(rs, out.Candidates)
	if err != nil {
		return ExecuteResponse{}, err
	}
	return ExecuteResponse{Components: components, Summary: calculateSummary(emp, components, componentTypes)}, nil
}

func hydrateFacts(facts map[string]interface{}) (Employee, Attendance, Rates, Components, error) {
	must := func(key string) (interface{}, error) {
		v, ok := facts[key]
		if !ok {
			return nil, validationError("MISSING_REQUIRED_FACT", "facts."+key, "facts."+key+" not found")
		}
		return v, nil
	}
	employeeObj, err := must("employee")
	if err != nil {
		return Employee{}, Attendance{}, Rates{}, Components{}, err
	}
	attendanceObj, err := must("attendance")
	if err != nil {
		return Employee{}, Attendance{}, Rates{}, Components{}, err
	}
	ratesObj, err := must("rates")
	if err != nil {
		return Employee{}, Attendance{}, Rates{}, Components{}, err
	}
	toStruct := func(src, dst interface{}) error {
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
		return emp, att, rates, comps, err
	}
	if err := toStruct(attendanceObj, &att); err != nil {
		return emp, att, rates, comps, err
	}
	if err := toStruct(ratesObj, &rates); err != nil {
		return emp, att, rates, comps, err
	}
	if raw, ok := facts["components"]; ok {
		if err := toStruct(raw, &comps); err != nil {
			return emp, att, rates, comps, err
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
	return emp, att, rates, comps, nil
}

func resolveCandidates(rs *TPRRuleSet, candidates []TPRCandidate) ([]Component, error) {
	byCode := map[string][]TPRCandidate{}
	for _, c := range candidates {
		byCode[c.Code] = append(byCode[c.Code], c)
	}
	codes := make([]string, 0, len(byCode))
	for code := range byCode {
		codes = append(codes, code)
	}
	sort.Strings(codes)
	result := []Component{}
	for _, code := range codes {
		items := byCode[code]
		sort.SliceStable(items, func(i, j int) bool {
			if items[i].Priority != items[j].Priority {
				return items[i].Priority > items[j].Priority
			}
			return items[i].RuleID < items[j].RuleID
		})
		policy := rs.ComponentPolicies[code]
		if policy == "" {
			policy = rs.DefaultHitPolicy
		}
		switch policy {
		case "UNIQUE":
			if len(items) != 1 {
				return nil, validationError("UNIQUE_HIT_CONFLICT", "components."+code, "UNIQUE produced more than one matching candidate")
			}
			result = append(result, componentFromCandidate(items[0]))
		case "FIRST":
			result = append(result, componentFromCandidate(items[0]))
		case "PRIORITY":
			if len(items) > 1 && items[0].Priority == items[1].Priority {
				return nil, validationError("PRIORITY_TIE", "components."+code, "matching candidates have equal priority")
			}
			result = append(result, componentFromCandidate(items[0]))
		case "COLLECT_SUM":
			sum := zeroPayrollDecimal()
			ids := []string{}
			versions := []int{}
			for _, item := range items {
				if item.ActionType != "ADD_COMPONENT" {
					return nil, validationError("MIXED_ACTION_CONFLICT", "components."+code, "COLLECT_SUM received a non-ADD action")
				}
				sum = sum.Add(payrollDecimalFromFloat(item.Amount))
				ids = append(ids, item.RuleID)
				if item.RuleVersionID > 0 {
					versions = append(versions, item.RuleVersionID)
				}
			}
			first := items[0]
			result = append(result, Component{Code: code, Amount: sum.Rounded(payrollMoneyScale).Float64(), RuleIx: first.LegacyIndex, SourceRuleID: first.RuleID, SourceRuleVersionID: first.RuleVersionID, SourceRuleIDs: ids, SourceRuleVersionIDs: versions})
		}
	}
	return result, nil
}

func componentFromCandidate(c TPRCandidate) Component {
	return Component{Code: c.Code, Amount: c.Amount, RuleIx: c.LegacyIndex, SourceRuleID: c.RuleID, SourceRuleVersionID: c.RuleVersionID, SourceRuleIDs: []string{c.RuleID}, SourceRuleVersionIDs: func() []int {
		if c.RuleVersionID > 0 {
			return []int{c.RuleVersionID}
		}
		return nil
	}()}
}
