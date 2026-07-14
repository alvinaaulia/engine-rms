package main

import "strings"

type Emitter struct {
	Components []Component
}

func (e *Emitter) AddComponent(code string, amount interface{}, ruleIx int64) {
	parsedAmount, ok := normalizePayrollMoney(amount)
	if !ok {
		return
	}

	e.Components = append(e.Components, Component{
		Code:   code,
		Amount: parsedAmount,
		RuleIx: int(ruleIx),
	})
}

func (e *Emitter) SetComponent(code string, amount interface{}, ruleIx int64) {
	parsedAmount, ok := normalizePayrollMoney(amount)
	if !ok {
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
