package main

type Emitter struct {
	Components []Component
}

func (e *Emitter) AddComponent(code string, amount int64, ruleIx int64) {
	e.Components = append(e.Components, Component{
		Code:   code,
		Amount: amount,
		RuleIx: int(ruleIx),
	})
}