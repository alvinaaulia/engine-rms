package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"sort"
	"strconv"
	"strings"
	"time"
)

const (
	TPRSchemaVersion      = "1.0"
	TPRMaxRules           = 500
	TPRMaxConditionDepth  = 2
	TPRMaxConditionLeaves = 50
	TPRMaxActions         = 8
	TPRMaxFormulaLength   = 1000
	TPRMaxFormulaDepth    = 32
)

type ValidationError struct {
	ErrorCode string                 `json:"error_code"`
	Path      string                 `json:"path"`
	Message   string                 `json:"message"`
	Details   map[string]interface{} `json:"details,omitempty"`
}

func (e *ValidationError) Error() string { return e.Path + ": " + e.Message }

func validationError(code, path, message string) error {
	return &ValidationError{ErrorCode: code, Path: path, Message: message}
}

type TPRRuleSet struct {
	SchemaVersion     string               `json:"schema_version"`
	RuleSetID         string               `json:"ruleset_id"`
	DefaultHitPolicy  string               `json:"default_hit_policy"`
	ComponentPolicies map[string]string    `json:"component_policies,omitempty"`
	RoundingPolicy    TPRRoundingPolicy    `json:"rounding_policy"`
	EffectivePeriod   *TPREffectivePeriod  `json:"effective_period,omitempty"`
	FieldCatalog      []TPRFieldDefinition `json:"field_catalog"`
	Rules             []TPRRule            `json:"rules"`
}

type TPRRoundingPolicy struct {
	Scale int    `json:"scale"`
	Mode  string `json:"mode"`
}

type TPREffectivePeriod struct {
	Start string `json:"start,omitempty"`
	End   string `json:"end,omitempty"`
}

type TPRFieldDefinition struct {
	Reference        TPRFieldReference `json:"reference"`
	AllowedOperators []string          `json:"allowed_operators"`
}

type TPRFieldReference struct {
	Namespace string `json:"namespace"`
	Name      string `json:"name"`
	DataType  string `json:"data_type"`
	Nullable  bool   `json:"nullable"`
}

func (f TPRFieldReference) Key() string { return f.Namespace + "." + f.Name }

type TPRRule struct {
	ID              string              `json:"id"`
	VersionID       int                 `json:"version_id,omitempty"`
	Priority        int                 `json:"priority"`
	Metadata        TPRRuleMetadata     `json:"metadata"`
	EffectivePeriod *TPREffectivePeriod `json:"effective_period,omitempty"`
	Condition       TPRConditionNode    `json:"condition"`
	Actions         []TPRAction         `json:"actions"`
	LegacyIndex     int                 `json:"legacy_index,omitempty"`
}

type TPRRuleMetadata struct {
	RuleID      int    `json:"rule_id,omitempty"`
	Version     int    `json:"version,omitempty"`
	Description string `json:"description,omitempty"`
}

// TPRConditionNode is discriminator based. Exactly the fields belonging to Kind
// are accepted by validation; NOT is intentionally not part of schema v1.0.
type TPRConditionNode struct {
	Kind     string             `json:"kind"`
	Operator string             `json:"operator,omitempty"`
	Children []TPRConditionNode `json:"children,omitempty"`
	Field    *TPRFieldReference `json:"field,omitempty"`
	Literal  *TPRTypedLiteral   `json:"literal,omitempty"`
}

type TPRTypedLiteral struct {
	Type  string      `json:"type"`
	Value interface{} `json:"value"`
}

type TPRAction struct {
	Type    string                `json:"type"`
	Target  TPRComponentReference `json:"target"`
	Formula TPRFormulaExpression  `json:"formula"`
}

type TPRComponentReference struct {
	Code string `json:"code"`
}
type TPRRateReference struct {
	Key string `json:"key"`
}

type TPRFormulaExpression struct {
	Language   string `json:"language"`
	Expression string `json:"expression"`
}

var staticFieldTypes = map[string]string{
	"employee.status": "string", "employee.contract_type": "string", "employee.has_npwp": "boolean",
	"employee.ptkp_status": "string", "employee.grade": "string", "employee.join_date": "date",
	"employee.years_of_service": "numeric", "employee.performance_score": "numeric", "employee.basic_salary": "numeric",
	"employee.annual_bonus_eligible": "boolean", "employee.thr_eligible": "boolean",
	"attendance.days_present": "numeric", "attendance.work_hours": "numeric", "attendance.work_minutes": "numeric",
	"attendance.days_absent": "numeric", "attendance.late_minutes": "numeric", "attendance.unpaid_leave_days": "numeric",
	"attendance.overtime_minutes": "numeric", "attendance.overtime_hours": "numeric",
}

func allowedOperators(dataType string) []string {
	switch dataType {
	case "numeric":
		return []string{"EQ", "NEQ", "GT", "GTE", "LT", "LTE", "IN", "NOT_IN"}
	case "date":
		return []string{"EQ", "NEQ", "BEFORE", "AFTER", "ON_OR_BEFORE", "ON_OR_AFTER", "IN", "NOT_IN"}
	case "boolean":
		return []string{"EQ", "NEQ"}
	case "string":
		return []string{"EQ", "NEQ", "CONTAINS", "IN", "NOT_IN"}
	default:
		return nil
	}
}

func priorityValue(value string) int {
	switch strings.ToUpper(strings.TrimSpace(value)) {
	case "HIGH":
		return 100
	case "LOW":
		return 10
	default:
		return 50
	}
}

func normalizeLegacyOperator(op string, dataType string) string {
	switch strings.ToUpper(strings.TrimSpace(op)) {
	case "=", "==":
		return "EQ"
	case "!=":
		return "NEQ"
	case ">":
		if dataType == "date" {
			return "AFTER"
		}
		return "GT"
	case ">=":
		if dataType == "date" {
			return "ON_OR_AFTER"
		}
		return "GTE"
	case "<":
		if dataType == "date" {
			return "BEFORE"
		}
		return "LT"
	case "<=":
		if dataType == "date" {
			return "ON_OR_BEFORE"
		}
		return "LTE"
	default:
		return strings.ToUpper(strings.TrimSpace(op))
	}
}

func fieldCatalogFromFacts(facts map[string]interface{}) []TPRFieldDefinition {
	types := map[string]string{}
	for key, typ := range staticFieldTypes {
		types[key] = typ
	}
	for _, ns := range []string{"rates", "components"} {
		if values, ok := facts[ns].(map[string]interface{}); ok {
			for name := range values {
				types[ns+"."+name] = "numeric"
			}
		}
	}
	keys := make([]string, 0, len(types))
	for key := range types {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	result := make([]TPRFieldDefinition, 0, len(keys))
	for _, key := range keys {
		parts := strings.SplitN(key, ".", 2)
		ref := TPRFieldReference{Namespace: parts[0], Name: parts[1], DataType: types[key], Nullable: false}
		result = append(result, TPRFieldDefinition{Reference: ref, AllowedOperators: allowedOperators(types[key])})
	}
	return result
}

func AdaptLegacyPayload(rules []Rule, facts map[string]interface{}) (*TPRRuleSet, error) {
	catalog := fieldCatalogFromFacts(facts)
	catalogMap := map[string]TPRFieldReference{}
	for _, item := range catalog {
		catalogMap[item.Reference.Key()] = item.Reference
	}
	tprRules := make([]TPRRule, 0, len(rules))
	actionTypes := map[string]map[string]bool{}
	for index, legacy := range rules {
		condition, err := adaptLegacyCondition(legacy.Conditions, catalogMap, 0, fmt.Sprintf("rules[%d].conditions", index))
		if err != nil {
			return nil, err
		}
		code := strings.ToUpper(strings.TrimSpace(legacy.Action.Code))
		if code == "" {
			return nil, validationError("INVALID_COMPONENT", fmt.Sprintf("rules[%d].action.code", index), "component code is required")
		}
		actionType := strings.ToUpper(strings.TrimSpace(legacy.Action.Type))
		if actionType == "SET" {
			actionType = "SET_COMPONENT"
		}
		if actionType == "ADD" || actionType == "" {
			actionType = "ADD_COMPONENT"
		}
		if actionType != "SET_COMPONENT" && actionType != "ADD_COMPONENT" {
			return nil, validationError("INVALID_ACTION", fmt.Sprintf("rules[%d].action.type", index), "unsupported action type")
		}
		if strings.TrimSpace(legacy.Action.Formula) == "" {
			return nil, validationError("EMPTY_FORMULA", fmt.Sprintf("rules[%d].action.formula", index), fmt.Sprintf("rule %d action.formula is empty", index))
		}
		if _, err := parseFormula(legacy.Action.Formula, catalogMap); err != nil {
			return nil, validationError("INVALID_FORMULA", fmt.Sprintf("rules[%d].action.formula", index), "build rule error: "+err.Error())
		}
		id := legacyRuleID(legacy)
		tprRules = append(tprRules, TPRRule{
			ID: id, VersionID: legacy.Meta.RuleVersionID, Priority: priorityValue(legacy.Meta.Priority), LegacyIndex: index,
			Metadata:        TPRRuleMetadata{RuleID: legacy.Meta.RuleID, Version: legacy.Meta.Version},
			EffectivePeriod: legacyEffectivePeriod(legacy.Meta), Condition: condition,
			Actions: []TPRAction{{Type: actionType, Target: TPRComponentReference{Code: code}, Formula: TPRFormulaExpression{Language: "TPR-EXPR-1.0", Expression: strings.TrimSpace(legacy.Action.Formula)}}},
		})
		if actionTypes[code] == nil {
			actionTypes[code] = map[string]bool{}
		}
		actionTypes[code][actionType] = true
	}
	policies := map[string]string{}
	for code, types := range actionTypes {
		if len(types) > 1 {
			return nil, validationError("MIXED_ACTION_CONFLICT", "rules", "SET_COMPONENT and ADD_COMPONENT cannot target the same component")
		}
		if types["ADD_COMPONENT"] {
			policies[code] = "COLLECT_SUM"
		} else {
			policies[code] = "PRIORITY"
		}
	}
	rs := &TPRRuleSet{SchemaVersion: TPRSchemaVersion, RuleSetID: "legacy-adapter", DefaultHitPolicy: "PRIORITY", ComponentPolicies: policies, RoundingPolicy: TPRRoundingPolicy{Scale: int(payrollMoneyScale), Mode: "HALF_UP"}, FieldCatalog: catalog, Rules: tprRules}
	if err := ValidateTPRRuleSet(rs, facts); err != nil {
		return nil, err
	}
	canonicalizeRuleSet(rs)
	return rs, nil
}

func legacyRuleID(rule Rule) string {
	if rule.Meta.RuleVersionID > 0 {
		return "rule-version-" + strconv.Itoa(rule.Meta.RuleVersionID)
	}
	copyRule := rule
	copyRule.Meta = RuleMetadata{}
	b, _ := json.Marshal(copyRule)
	sum := sha256.Sum256(b)
	return "legacy-" + hex.EncodeToString(sum[:8])
}

func legacyEffectivePeriod(meta RuleMetadata) *TPREffectivePeriod {
	if meta.EffectiveDate == "" && meta.EndDate == "" {
		return nil
	}
	return &TPREffectivePeriod{Start: meta.EffectiveDate, End: meta.EndDate}
}

func adaptLegacyCondition(node interface{}, catalog map[string]TPRFieldReference, depth int, path string) (TPRConditionNode, error) {
	if depth > TPRMaxConditionDepth {
		return TPRConditionNode{}, validationError("MAX_CONDITION_DEPTH", path, "condition depth exceeds limit")
	}
	switch n := node.(type) {
	case []interface{}:
		if len(n) == 0 {
			return TPRConditionNode{}, validationError("EMPTY_CONDITION_GROUP", path, "condition group cannot be empty")
		}
		children := make([]TPRConditionNode, 0, len(n))
		for i, child := range n {
			c, err := adaptLegacyCondition(child, catalog, depth+1, fmt.Sprintf("%s[%d]", path, i))
			if err != nil {
				return TPRConditionNode{}, err
			}
			children = append(children, c)
		}
		return TPRConditionNode{Kind: "group", Operator: "AND", Children: children}, nil
	case map[string]interface{}:
		if raw, ok := n["rules"]; ok {
			items, ok := raw.([]interface{})
			if !ok || len(items) == 0 {
				return TPRConditionNode{}, validationError("EMPTY_CONDITION_GROUP", path+".rules", "condition group must contain children")
			}
			op := strings.ToUpper(strings.TrimSpace(fmt.Sprint(n["type"])))
			if op == "" {
				op = "AND"
			}
			if op != "AND" && op != "OR" {
				return TPRConditionNode{}, validationError("INVALID_GROUP_OPERATOR", path+".type", "only AND and OR are supported")
			}
			children := make([]TPRConditionNode, 0, len(items))
			for i, item := range items {
				c, err := adaptLegacyCondition(item, catalog, depth+1, fmt.Sprintf("%s.rules[%d]", path, i))
				if err != nil {
					return TPRConditionNode{}, err
				}
				children = append(children, c)
			}
			return TPRConditionNode{Kind: "group", Operator: op, Children: children}, nil
		}
		fieldKey := strings.TrimSpace(fmt.Sprint(n["field"]))
		ref, ok := catalog[fieldKey]
		if !ok {
			return TPRConditionNode{}, validationError("UNKNOWN_FIELD", path+".field", "field is not present in the TPR field catalog")
		}
		op := normalizeLegacyOperator(fmt.Sprint(n["operator"]), ref.DataType)
		if !containsString(allowedOperators(ref.DataType), op) {
			return TPRConditionNode{}, validationError("INVALID_OPERATOR_FOR_TYPE", path+".operator", "operator is not valid for field type")
		}
		value, exists := n["value"]
		if !exists {
			return TPRConditionNode{}, validationError("MISSING_LITERAL", path+".value", "condition literal is required")
		}
		literal, err := adaptTypedLiteral(value, ref.DataType, op, path+".value")
		if err != nil {
			return TPRConditionNode{}, err
		}
		return TPRConditionNode{Kind: "leaf", Operator: op, Field: &ref, Literal: &literal}, nil
	default:
		return TPRConditionNode{}, validationError("INVALID_CONDITION_NODE", path, "condition must be an object or array")
	}
}

func adaptTypedLiteral(value interface{}, dataType, op, path string) (TPRTypedLiteral, error) {
	list := op == "IN" || op == "NOT_IN"
	if list {
		values, ok := value.([]interface{})
		if !ok || len(values) == 0 {
			return TPRTypedLiteral{}, validationError("INVALID_LITERAL_TYPE", path, "membership requires a non-empty array")
		}
		normalized := make([]interface{}, 0, len(values))
		for i, v := range values {
			scalar, err := strictScalar(v, dataType, fmt.Sprintf("%s[%d]", path, i), true)
			if err != nil {
				return TPRTypedLiteral{}, err
			}
			normalized = append(normalized, scalar)
		}
		return TPRTypedLiteral{Type: "array<" + dataType + ">", Value: normalized}, nil
	}
	scalar, err := strictScalar(value, dataType, path, true)
	if err != nil {
		return TPRTypedLiteral{}, err
	}
	return TPRTypedLiteral{Type: dataType, Value: scalar}, nil
}

func strictScalar(value interface{}, dataType, path string, legacy bool) (interface{}, error) {
	switch dataType {
	case "numeric":
		if n, ok := value.(json.Number); ok {
			if _, err := n.Float64(); err == nil {
				return n, nil
			}
		}
		switch v := value.(type) {
		case float64:
			return v, nil
		case float32:
			return float64(v), nil
		case int:
			return float64(v), nil
		case int8:
			return float64(v), nil
		case int16:
			return float64(v), nil
		case int32:
			return float64(v), nil
		case int64:
			return float64(v), nil
		case uint:
			return float64(v), nil
		case uint8:
			return float64(v), nil
		case uint16:
			return float64(v), nil
		case uint32:
			return float64(v), nil
		case uint64:
			return float64(v), nil
		case string:
			if legacy {
				n, err := strconv.ParseFloat(strings.TrimSpace(v), 64)
				if err == nil {
					return n, nil
				}
			}
		}
	case "boolean":
		if v, ok := value.(bool); ok {
			return v, nil
		}
		if legacy {
			if v, ok := parseDynamicBool(value); ok {
				return v, nil
			}
		}
	case "string":
		if v, ok := value.(string); ok {
			return v, nil
		}
	case "date":
		if v, ok := value.(string); ok {
			if _, err := time.Parse("2006-01-02", v); err == nil {
				return v, nil
			}
		}
	}
	return nil, validationError("INVALID_LITERAL_TYPE", path, "literal does not match declared field type")
}

func containsString(values []string, target string) bool {
	for _, v := range values {
		if v == target {
			return true
		}
	}
	return false
}

func withValidationPath(err error, path string) error {
	if ve, ok := err.(*ValidationError); ok {
		copy := *ve
		copy.Path = path
		return &copy
	}
	return validationError("INVALID_FORMULA", path, err.Error())
}

func ValidateTPRRuleSet(rs *TPRRuleSet, facts map[string]interface{}) error {
	if rs == nil {
		return validationError("MISSING_RULESET", "ruleset", "ruleset is required")
	}
	if rs.SchemaVersion == "" {
		return validationError("MISSING_SCHEMA_VERSION", "ruleset.schema_version", "schema_version is required")
	}
	if rs.SchemaVersion != TPRSchemaVersion {
		return validationError("UNSUPPORTED_SCHEMA_VERSION", "ruleset.schema_version", "only TPR-IR 1.0 is supported")
	}
	if len(rs.Rules) == 0 || len(rs.Rules) > TPRMaxRules {
		return validationError("INVALID_RULE_COUNT", "ruleset.rules", "ruleset must contain 1..500 rules")
	}
	if !containsInt([]int{2, int(payrollMoneyScale)}, rs.RoundingPolicy.Scale) || rs.RoundingPolicy.Mode != "HALF_UP" {
		return validationError("INVALID_ROUNDING_POLICY", "ruleset.rounding_policy", "TPR-IR 1.0 supports scale 2 or 6 with HALF_UP")
	}
	if !containsString([]string{"UNIQUE", "FIRST", "PRIORITY", "COLLECT_SUM"}, rs.DefaultHitPolicy) {
		return validationError("INVALID_HIT_POLICY", "ruleset.default_hit_policy", "unsupported hit policy")
	}
	if err := validateEffectivePeriod(rs.EffectivePeriod, "ruleset.effective_period"); err != nil {
		return err
	}
	catalog := map[string]TPRFieldReference{}
	ops := map[string][]string{}
	for i, item := range rs.FieldCatalog {
		key := item.Reference.Key()
		if key == "." || item.Reference.Nullable {
			return validationError("INVALID_FIELD_DEFINITION", fmt.Sprintf("ruleset.field_catalog[%d]", i), "field reference is invalid or nullable is unsupported in v1.0")
		}
		if _, exists := catalog[key]; exists {
			return validationError("DUPLICATE_FIELD", fmt.Sprintf("ruleset.field_catalog[%d]", i), "duplicate field")
		}
		if item.Reference.DataType != "numeric" && item.Reference.DataType != "string" && item.Reference.DataType != "boolean" && item.Reference.DataType != "date" {
			return validationError("INVALID_FIELD_TYPE", fmt.Sprintf("ruleset.field_catalog[%d]", i), "unsupported field type")
		}
		if !containsString([]string{"employee", "attendance", "rates", "components"}, item.Reference.Namespace) {
			return validationError("UNKNOWN_NAMESPACE", fmt.Sprintf("ruleset.field_catalog[%d].reference.namespace", i), "namespace is not allowed")
		}
		if item.Reference.Namespace == "employee" || item.Reference.Namespace == "attendance" {
			expected, ok := staticFieldTypes[key]
			if !ok {
				return validationError("UNKNOWN_FIELD", fmt.Sprintf("ruleset.field_catalog[%d].reference", i), "static field is not allowed")
			}
			if expected != item.Reference.DataType {
				return validationError("FIELD_TYPE_MISMATCH", fmt.Sprintf("ruleset.field_catalog[%d].reference.data_type", i), "static field type is fixed")
			}
		}
		if (item.Reference.Namespace == "rates" || item.Reference.Namespace == "components") && item.Reference.DataType != "numeric" {
			return validationError("FIELD_TYPE_MISMATCH", fmt.Sprintf("ruleset.field_catalog[%d].reference.data_type", i), "rate and component fields are numeric")
		}
		canonicalOps := allowedOperators(item.Reference.DataType)
		if !sameStringSet(item.AllowedOperators, canonicalOps) {
			return validationError("INVALID_OPERATOR_CATALOG", fmt.Sprintf("ruleset.field_catalog[%d].allowed_operators", i), "allowed operators must equal the canonical type contract")
		}
		catalog[key] = item.Reference
		ops[key] = item.AllowedOperators
	}
	seen := map[string]bool{}
	seenSemantics := map[string]bool{}
	leaves := 0
	for i := range rs.Rules {
		r := &rs.Rules[i]
		path := fmt.Sprintf("ruleset.rules[%d]", i)
		if r.ID == "" || seen[r.ID] {
			return validationError("DUPLICATE_RULE", path+".id", "rule id is empty or duplicated")
		}
		seen[r.ID] = true
		semanticFingerprint, err := canonicalRuleSemanticFingerprint(*r)
		if err != nil {
			return validationError("INVALID_RULE", path, "rule cannot be canonicalized")
		}
		if seenSemantics[semanticFingerprint] {
			return validationError("DUPLICATE_RULE", path, "semantically duplicate rule")
		}
		seenSemantics[semanticFingerprint] = true
		if r.Priority < 0 || r.Priority > 1000 {
			return validationError("INVALID_PRIORITY", path+".priority", "priority must be between 0 and 1000")
		}
		if err := validateEffectivePeriod(r.EffectivePeriod, path+".effective_period"); err != nil {
			return err
		}
		if len(r.Actions) == 0 || len(r.Actions) > TPRMaxActions {
			return validationError("INVALID_ACTION_COUNT", path+".actions", "rule must have 1..8 actions")
		}
		count, err := validateConditionNode(r.Condition, catalog, ops, 0, path+".condition", facts, rs.RuleSetID == "legacy-adapter")
		if err != nil {
			return err
		}
		leaves += count
		if count > TPRMaxConditionLeaves {
			return validationError("MAX_CONDITION_LEAVES", path+".condition", "too many condition leaves")
		}
		actionFingerprints := map[string]bool{}
		for j, a := range r.Actions {
			ap := fmt.Sprintf("%s.actions[%d]", path, j)
			if a.Type != "SET_COMPONENT" && a.Type != "ADD_COMPONENT" {
				return validationError("INVALID_ACTION", ap+".type", "unsupported action")
			}
			a.Target.Code = strings.ToUpper(strings.TrimSpace(a.Target.Code))
			if a.Target.Code == "" {
				return validationError("INVALID_COMPONENT", ap+".target.code", "component code is required")
			}
			if a.Formula.Language != "TPR-EXPR-1.0" {
				return validationError("INVALID_FORMULA_LANGUAGE", ap+".formula.language", "unsupported formula language")
			}
			formulaAST, err := parseFormula(a.Formula.Expression, catalog)
			if err != nil {
				return withValidationPath(err, ap+".formula.expression")
			}
			for _, identifier := range formulaFieldIdentifiers(formulaAST) {
				fact, ok := factValue(facts, identifier)
				if !ok {
					return validationError("MISSING_REQUIRED_FACT", ap+".formula.expression", "formula references a missing fact")
				}
				declared := catalog[identifier]
				// Formula identifiers are numeric by grammar/catalog validation. They
				// still require runtime type validation even when the same field is
				// absent from every condition node.
				if err := validateFormulaFactRuntimeType(fact, declared.DataType, ap+".formula.expression"); err != nil {
					return validationError("INVALID_FACT_TYPE", ap+".formula.expression", "formula fact value does not match its declared field type")
				}
			}
			fingerprint := a.Type + "|" + a.Target.Code + "|" + a.Formula.Expression
			if actionFingerprints[fingerprint] {
				return validationError("DUPLICATE_ACTION", ap, "duplicate action in the same rule")
			}
			actionFingerprints[fingerprint] = true
		}
	}
	_ = leaves
	return validateConflicts(rs)
}

func containsInt(values []int, target int) bool {
	for _, value := range values {
		if value == target {
			return true
		}
	}
	return false
}

func canonicalRuleSemanticFingerprint(rule TPRRule) (string, error) {
	canonicalizeCondition(&rule.Condition)
	sort.SliceStable(rule.Actions, func(i, j int) bool {
		left, _ := json.Marshal(rule.Actions[i])
		right, _ := json.Marshal(rule.Actions[j])
		return string(left) < string(right)
	})
	payload := struct {
		Priority        int                 `json:"priority"`
		EffectivePeriod *TPREffectivePeriod `json:"effective_period,omitempty"`
		Condition       TPRConditionNode    `json:"condition"`
		Actions         []TPRAction         `json:"actions"`
	}{rule.Priority, rule.EffectivePeriod, rule.Condition, rule.Actions}
	b, err := json.Marshal(payload)
	if err != nil {
		return "", err
	}
	sum := sha256.Sum256(b)
	return hex.EncodeToString(sum[:]), nil
}

func validateEffectivePeriod(period *TPREffectivePeriod, path string) error {
	if period == nil {
		return nil
	}
	var start, end time.Time
	var err error
	if period.Start != "" {
		start, err = time.Parse("2006-01-02", period.Start)
		if err != nil {
			return validationError("INVALID_EFFECTIVE_PERIOD", path+".start", "date must be YYYY-MM-DD")
		}
	}
	if period.End != "" {
		end, err = time.Parse("2006-01-02", period.End)
		if err != nil {
			return validationError("INVALID_EFFECTIVE_PERIOD", path+".end", "date must be YYYY-MM-DD")
		}
	}
	if !start.IsZero() && !end.IsZero() && end.Before(start) {
		return validationError("INVALID_EFFECTIVE_PERIOD", path, "end must not precede start")
	}
	return nil
}

func formulaFieldIdentifiers(node *formulaNode) []string {
	seen := map[string]bool{}
	var walk func(*formulaNode)
	walk = func(n *formulaNode) {
		if n == nil {
			return
		}
		if n.kind == "field" {
			seen[n.value] = true
		}
		walk(n.left)
		walk(n.right)
	}
	walk(node)
	result := make([]string, 0, len(seen))
	for key := range seen {
		result = append(result, key)
	}
	sort.Strings(result)
	return result
}

func validateConditionNode(node TPRConditionNode, catalog map[string]TPRFieldReference, ops map[string][]string, depth int, path string, facts map[string]interface{}, legacyFacts bool) (int, error) {
	if depth > TPRMaxConditionDepth {
		return 0, validationError("MAX_CONDITION_DEPTH", path, "condition depth exceeds limit")
	}
	if node.Kind == "group" {
		if node.Operator != "AND" && node.Operator != "OR" {
			return 0, validationError("INVALID_GROUP_OPERATOR", path+".operator", "only AND and OR are supported")
		}
		if len(node.Children) == 0 {
			return 0, validationError("EMPTY_CONDITION_GROUP", path+".children", "group cannot be empty")
		}
		n := 0
		for i, c := range node.Children {
			x, err := validateConditionNode(c, catalog, ops, depth+1, fmt.Sprintf("%s.children[%d]", path, i), facts, legacyFacts)
			if err != nil {
				return 0, err
			}
			n += x
		}
		return n, nil
	}
	if node.Kind != "leaf" || node.Field == nil || node.Literal == nil {
		return 0, validationError("INVALID_CONDITION_NODE", path, "condition discriminator or fields are invalid")
	}
	key := node.Field.Key()
	declared, ok := catalog[key]
	if !ok {
		return 0, validationError("UNKNOWN_FIELD", path+".field", "field is not in catalog")
	}
	if declared != *node.Field {
		return 0, validationError("FIELD_TYPE_MISMATCH", path+".field", "field declaration differs from catalog")
	}
	if !containsString(ops[key], node.Operator) || !containsString(allowedOperators(declared.DataType), node.Operator) {
		return 0, validationError("INVALID_OPERATOR_FOR_TYPE", path+".operator", "operator is invalid for field type")
	}
	expected := declared.DataType
	if node.Operator == "IN" || node.Operator == "NOT_IN" {
		expected = "array<" + expected + ">"
	}
	if node.Literal.Type != expected {
		return 0, validationError("INVALID_LITERAL_TYPE", path+".literal.type", "literal type does not match operator and field")
	}
	if err := validateCanonicalLiteral(node.Literal.Value, declared.DataType, node.Operator, path+".literal.value"); err != nil {
		return 0, err
	}
	fact, ok := factValue(facts, key)
	if !ok {
		return 0, validationError("MISSING_REQUIRED_FACT", path+".field", "required fact is missing")
	}
	// Monetary/numeric facts intentionally use canonical decimal strings on the
	// wire so PHP BigDecimal values are not rounded through binary JSON floats.
	// This is an explicit representation rule, not implicit literal coercion.
	factAllowsDecimalString := legacyFacts || declared.DataType == "numeric"
	if _, err := strictScalar(fact, declared.DataType, path+".field", factAllowsDecimalString); err != nil {
		return 0, validationError("INVALID_FACT_TYPE", path+".field", "fact value does not match declared field type")
	}
	return 1, nil
}

func factValue(facts map[string]interface{}, key string) (interface{}, bool) {
	parts := strings.SplitN(key, ".", 2)
	ns, ok := facts[parts[0]].(map[string]interface{})
	if !ok {
		return nil, false
	}
	value, ok := ns[parts[1]]
	return value, ok
}

func validateCanonicalLiteral(value interface{}, dataType, op, path string) error {
	if op == "IN" || op == "NOT_IN" {
		values, ok := value.([]interface{})
		if !ok || len(values) == 0 {
			return validationError("INVALID_LITERAL_TYPE", path, "membership requires a non-empty array")
		}
		for i, item := range values {
			if _, err := strictScalar(item, dataType, fmt.Sprintf("%s[%d]", path, i), false); err != nil {
				return err
			}
		}
		return nil
	}
	_, err := strictScalar(value, dataType, path, false)
	return err
}

func sameStringSet(left, right []string) bool {
	if len(left) != len(right) {
		return false
	}
	seen := map[string]bool{}
	for _, value := range left {
		seen[value] = true
	}
	for _, value := range right {
		if !seen[value] {
			return false
		}
	}
	return true
}

func validateConflicts(rs *TPRRuleSet) error {
	type entry struct {
		action   string
		priority int
		rule     string
	}
	byCode := map[string][]entry{}
	for _, r := range rs.Rules {
		for _, a := range r.Actions {
			code := strings.ToUpper(strings.TrimSpace(a.Target.Code))
			byCode[code] = append(byCode[code], entry{a.Type, r.Priority, r.ID})
		}
	}
	for code, policy := range rs.ComponentPolicies {
		if !containsString([]string{"UNIQUE", "FIRST", "PRIORITY", "COLLECT_SUM"}, policy) {
			return validationError("INVALID_HIT_POLICY", "ruleset.component_policies."+code, "unsupported hit policy")
		}
		if _, ok := byCode[code]; !ok {
			return validationError("UNKNOWN_COMPONENT_POLICY", "ruleset.component_policies."+code, "policy has no target producer")
		}
	}
	for code, entries := range byCode {
		policy := rs.ComponentPolicies[code]
		if policy == "" {
			policy = rs.DefaultHitPolicy
		}
		types := map[string]bool{}
		priorities := map[int]bool{}
		for _, e := range entries {
			types[e.action] = true
			if policy == "PRIORITY" && priorities[e.priority] {
				return validationError("PRIORITY_TIE", "ruleset.component_policies."+code, "PRIORITY requires unique priority per target")
			}
			priorities[e.priority] = true
		}
		if len(types) > 1 {
			return validationError("MIXED_ACTION_CONFLICT", "ruleset.component_policies."+code, "SET and ADD cannot be mixed")
		}
		if policy == "COLLECT_SUM" && types["SET_COMPONENT"] {
			return validationError("INVALID_HIT_POLICY_FOR_ACTION", "ruleset.component_policies."+code, "COLLECT_SUM accepts ADD_COMPONENT only")
		}
		if policy == "UNIQUE" && len(entries) > 1 {
			return validationError("POTENTIAL_UNIQUE_CONFLICT", "ruleset.component_policies."+code, "UNIQUE requires one potential producer per target")
		}
	}
	return nil
}

func canonicalizeRuleSet(rs *TPRRuleSet) {
	for i := range rs.Rules {
		canonicalizeCondition(&rs.Rules[i].Condition)
	}
	sort.SliceStable(rs.FieldCatalog, func(i, j int) bool { return rs.FieldCatalog[i].Reference.Key() < rs.FieldCatalog[j].Reference.Key() })
	sort.SliceStable(rs.Rules, func(i, j int) bool {
		if rs.Rules[i].Priority != rs.Rules[j].Priority {
			return rs.Rules[i].Priority > rs.Rules[j].Priority
		}
		return rs.Rules[i].ID < rs.Rules[j].ID
	})
}

func canonicalizeCondition(n *TPRConditionNode) {
	for i := range n.Children {
		canonicalizeCondition(&n.Children[i])
	}
	if n.Kind == "group" {
		sort.SliceStable(n.Children, func(i, j int) bool {
			a, _ := json.Marshal(n.Children[i])
			b, _ := json.Marshal(n.Children[j])
			return string(a) < string(b)
		})
	}
}

func CanonicalIRHash(rs TPRRuleSet) (string, error) {
	// Compatibility indices and descriptions do not participate in executable
	// semantics and therefore cannot change the semantic identity.
	for i := range rs.Rules {
		rs.Rules[i].LegacyIndex = 0
		rs.Rules[i].Metadata.Description = ""
	}
	canonicalizeRuleSet(&rs)
	b, err := json.Marshal(rs)
	if err != nil {
		return "", err
	}
	sum := sha256.Sum256(b)
	return hex.EncodeToString(sum[:]), nil
}
