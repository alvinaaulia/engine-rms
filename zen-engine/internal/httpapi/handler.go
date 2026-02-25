package httpapi

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"time"

	"rule-engine-zen/internal/engine"
	"rule-engine-zen/internal/types"
	"rule-engine-zen/internal/version"
)

type Handler struct {
	zen     *engine.ZenEngine
	version version.Provider
}

func NewHandler(zenEngine *engine.ZenEngine, vp version.Provider) *Handler {
	return &Handler{zen: zenEngine, version: vp}
}

func (h *Handler) Routes(mux *http.ServeMux) {
	// Samakan path ini dengan yang dipanggil Laravel (0 perubahan)
	mux.HandleFunc("/execute", h.Execute)
	mux.HandleFunc("/healthz", func(w http.ResponseWriter, r *http.Request) { w.WriteHeader(http.StatusOK) })
}

func (h *Handler) Execute(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := context.WithTimeout(r.Context(), 10*time.Second)
	defer cancel()

	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req types.ExecuteRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "invalid json body", http.StatusBadRequest)
		return
	}
	if req.Facts == nil {
		req.Facts = map[string]any{}
	}

	ver, err := h.version.ActiveVersion(ctx)
	if err != nil {
		http.Error(w, "failed to get active version", http.StatusInternalServerError)
		return
	}

	decisionKey := fmt.Sprintf("payroll_v%d.jdm.json", ver)

	zenOut, err := h.zen.Evaluate(ctx, decisionKey, req.Facts)
	if err != nil {
		http.Error(w, err.Error(), http.StatusUnprocessableEntity)
		return
	}

	components, err := mapComponents(zenOut)
	if err != nil {
		http.Error(w, "invalid decision output components", http.StatusInternalServerError)
		return
	}

	summary := calculateSummary(components) // stub: sesuaikan agar sama dengan sistem lama

	resp := types.ExecuteResponse{
		Components: components,
		Summary:    summary,
	}

	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(resp)
}

func mapComponents(zenOut map[string]any) ([]types.Component, error) {
	// Ekspektasi output dari JDM: {"components":[{"code":"X","amount":123}, ...]}
	raw, ok := zenOut["components"]
	if !ok {
		// Kalau JDM output kamu beda, ubah mapper ini
		return []types.Component{}, nil
	}

	arr, ok := raw.([]any)
	if !ok {
		return nil, fmt.Errorf("components is not array")
	}

	out := make([]types.Component, 0, len(arr))
	for _, item := range arr {
		m, ok := item.(map[string]any)
		if !ok {
			return nil, fmt.Errorf("component item not object")
		}
		code, _ := m["code"].(string)

		// amount bisa float64 (default json decode), int, dll
		var amount int64
		switch v := m["amount"].(type) {
		case float64:
			amount = int64(v)
		case int:
			amount = int64(v)
		case int64:
			amount = v
		default:
			amount = 0
		}

		out = append(out, types.Component{Code: code, Amount: amount})
	}
	return out, nil
}

func calculateSummary(components []types.Component) types.Summary {
	// TODO: copy logika summary yang sekarang (agar match 100%)
	var gross int64
	for _, c := range components {
		// contoh sederhana: jumlahkan semua amount sebagai gross
		gross += c.Amount
	}
	return types.Summary{
		Gross: gross,
		Deduction: 0,
		Net:   gross,
	}
}
