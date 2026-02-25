package types

// ExecuteRequest adalah body yang dikirim Laravel.
// Biasanya: {"facts": {...}} atau langsung {...}. Sesuaikan.
type ExecuteRequest struct {
	Facts map[string]any `json:"facts"`
}

// Component output untuk Laravel (samakan dengan yang lama)
type Component struct {
	Code   string `json:"code"`
	Amount int64  `json:"amount"`
	// Opsional: RuleID, Desc, etc
}

// Summary output untuk Laravel (samakan dengan yang lama)
type Summary struct {
	Gross int64 `json:"gross"`
	Deduction int64 `json:"deduction"`
	Net   int64 `json:"net"`
}

// ExecuteResponse adalah response final yang diterima Laravel.
type ExecuteResponse struct {
	Components []Component `json:"components"`
	Summary    Summary     `json:"summary"`
}
