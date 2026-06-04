package main

import (
	"encoding/json"
	"math"
	"strconv"
	"strings"
)

type Emitter struct {
	Components []Component
}

func (e *Emitter) AddComponent(code string, amount interface{}, ruleIx int64) {
	parsedAmount, ok := parseNumericAmount(amount)
	if !ok || math.IsNaN(parsedAmount) || math.IsInf(parsedAmount, 0) {
		return
	}

	e.Components = append(e.Components, Component{
		Code:   code,
		Amount: parsedAmount,
		RuleIx: int(ruleIx),
	})
}

func (e *Emitter) SetComponent(code string, amount interface{}, ruleIx int64) {
	parsedAmount, ok := parseNumericAmount(amount)
	if !ok || math.IsNaN(parsedAmount) || math.IsInf(parsedAmount, 0) {
		return
	}

	for index, component := range e.Components {
		if component.Code != code {
			continue
		}

		e.Components[index] = Component{
			Code:   code,
			Amount: parsedAmount,
			RuleIx: int(ruleIx),
		}
		return
	}

	e.Components = append(e.Components, Component{
		Code:   code,
		Amount: parsedAmount,
		RuleIx: int(ruleIx),
	})
}

func (e *Emitter) ApplyComponent(actionType string, code string, amount interface{}, ruleIx int64) {
	switch strings.ToUpper(strings.TrimSpace(actionType)) {
	case "SET_COMPONENT", "SET":
		e.SetComponent(code, amount, ruleIx)
	default:
		e.AddComponent(code, amount, ruleIx)
	}
}

func parseNumericAmount(value interface{}) (float64, bool) {
	switch v := value.(type) {
	case float64:
		return v, true
	case float32:
		return float64(v), true
	case int:
		return float64(v), true
	case int8:
		return float64(v), true
	case int16:
		return float64(v), true
	case int32:
		return float64(v), true
	case int64:
		return float64(v), true
	case uint:
		return float64(v), true
	case uint8:
		return float64(v), true
	case uint16:
		return float64(v), true
	case uint32:
		return float64(v), true
	case uint64:
		return float64(v), true
	case json.Number:
		parsed, err := v.Float64()
		return parsed, err == nil
	case string:
		parsed, err := strconv.ParseFloat(v, 64)
		return parsed, err == nil
	default:
		return 0, false
	}
}
